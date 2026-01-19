"""
Voting models for iVote Systems
Implements encrypted vote storage with verification codes
"""

from django.db import models
from django.utils import timezone
from django.core.validators import MinLengthValidator
import uuid
import json

from elections.models import Election, Position, Candidate
from accounts.models import VoterProfile
from .encryption import vote_encryptor, verification_generator


class Vote(models.Model):
    """
    Encrypted vote record - anonymous and secure
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Election context (not voter identity)
    election = models.ForeignKey(
        Election,
        on_delete=models.PROTECT,
        related_name='votes',
        help_text="Election this vote belongs to"
    )
    
    # Encrypted vote data
    encrypted_vote = models.TextField(
        help_text="AES-256 encrypted vote data"
    )
    encryption_iv = models.CharField(
        max_length=255,
        help_text="Initialization vector for encryption"
    )
    
    # Anonymous voter hash (prevents double voting)
    voter_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="One-way hash of voter ID (for duplicate prevention)"
    )
    
    # Vote metadata (anonymous)
    cast_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When vote was cast"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address for audit (optional)"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="Browser info for audit"
    )
    
    # Verification
    verification_code = models.CharField(
        max_length=15,
        unique=True,
        db_index=True,
        help_text="Unique code for vote verification"
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When voter verified their vote"
    )
    
    class Meta:
        db_table = 'vote'
        ordering = ['-cast_at']
        indexes = [
            models.Index(fields=['election', 'cast_at']),
            models.Index(fields=['voter_hash', 'election']),
            models.Index(fields=['verification_code']),
        ]
        # Prevent duplicate votes: one hash per election
        constraints = [
            models.UniqueConstraint(
                fields=['voter_hash', 'election'],
                name='unique_vote_per_election'
            )
        ]
    
    def __str__(self):
        return f"Vote {self.verification_code} in {self.election.title}"
    
    @classmethod
    def cast_vote(cls, election, voter_profile, position_votes, ip_address=None, user_agent=None):
        """
        Cast an encrypted vote
        
        Args:
            election: Election instance
            voter_profile: VoterProfile instance
            position_votes: Dict of {position_id: [candidate_id, ...]}
            ip_address: Optional IP address
            user_agent: Optional user agent string
        
        Returns:
            Tuple of (Vote instance, verification_code)
        
        Raises:
            ValueError: If vote is invalid or duplicate
        """
        from elections.models import ElectionVoter
        
        # Create voter hash
        voter_hash = vote_encryptor.hash_voter_id(
            str(voter_profile.id),
            str(election.id)
        )
        
        # Check for duplicate vote
        if cls.objects.filter(voter_hash=voter_hash, election=election).exists():
            raise ValueError("Vote already cast for this election")
        
        # Validate and prepare vote data
        vote_data = cls._prepare_vote_data(election, position_votes)
        
        # Encrypt vote
        encrypted_vote, iv = vote_encryptor.encrypt_vote(json.dumps(vote_data))
        
        # Create vote record
        vote = cls.objects.create(
            election=election,
            encrypted_vote=encrypted_vote,
            encryption_iv=iv,
            voter_hash=voter_hash,
            ip_address=ip_address,
            user_agent=user_agent,
            verification_code=''  # Temporary
        )
        
        # Generate verification code
        verification_code = verification_generator.generate_code(
            str(vote.id),
            vote.cast_at.isoformat()
        )
        vote.verification_code = verification_code
        vote.save(update_fields=['verification_code'])
        
        # Update ElectionVoter status
        election_voter, created = ElectionVoter.objects.get_or_create(
            election=election,
            voter=voter_profile,
            defaults={'status': 'voted'}
        )
        if not created:
            election_voter.mark_voted(ip_address, user_agent)
        
        return vote, verification_code
    
    @staticmethod
    def _prepare_vote_data(election, position_votes):
        """
        Validate and prepare vote data for encryption
        
        Args:
            election: Election instance
            position_votes: Dict of {position_id: [candidate_id, ...]}
        
        Returns:
            Dict of validated vote data
        
        Raises:
            ValueError: If vote data is invalid
        """
        validated_data = {}
        
        for position_id, candidate_ids in position_votes.items():
            # Get position
            try:
                position = election.positions.get(id=position_id)
            except Position.DoesNotExist:
                raise ValueError(f"Position {position_id} not found in election")
            
            # Validate number of selections
            if len(candidate_ids) > position.candidates_per_voter:
                raise ValueError(
                    f"Too many candidates selected for {position.title}. "
                    f"Maximum: {position.candidates_per_voter}"
                )
            
            # Validate candidates
            valid_candidate_ids = []
            for candidate_id in candidate_ids:
                try:
                    candidate = position.candidates.get(
                        id=candidate_id,
                        status='approved'
                    )
                    valid_candidate_ids.append(str(candidate.id))
                except Candidate.DoesNotExist:
                    raise ValueError(f"Invalid candidate: {candidate_id}")
            
            validated_data[str(position_id)] = valid_candidate_ids
        
        return validated_data
    
    def decrypt_vote_data(self):
        """
        Decrypt and return vote data (admin only)
        
        Returns:
            Dict of position_id: [candidate_id, ...]
        """
        decrypted = vote_encryptor.decrypt_vote(
            self.encrypted_vote,
            self.encryption_iv
        )
        return json.loads(decrypted)
    
    def verify(self):
        """Mark vote as verified by voter"""
        if not self.verified_at:
            self.verified_at = timezone.now()
            self.save(update_fields=['verified_at'])
        return True
    
    def get_vote_summary(self):
        """
        Get vote summary without revealing voter identity
        """
        return {
            'verification_code': self.verification_code,
            'election': self.election.title,
            'cast_at': self.cast_at,
            'verified': self.verified_at is not None,
        }


class VoteAudit(models.Model):
    """
    Immutable audit log for voting operations
    """
    
    ACTION_CHOICES = [
        ('vote_cast', 'Vote Cast'),
        ('vote_verified', 'Vote Verified'),
        ('vote_viewed', 'Vote Viewed (Admin)'),
        ('vote_decrypted', 'Vote Decrypted (Admin)'),
        ('election_opened', 'Election Opened for Voting'),
        ('election_closed', 'Election Closed'),
        ('results_generated', 'Results Generated'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Audit information
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True)
    election = models.ForeignKey(
        Election,
        on_delete=models.PROTECT,
        related_name='audit_logs',
        null=True,
        blank=True
    )
    vote = models.ForeignKey(
        Vote,
        on_delete=models.SET_NULL,
        related_name='audit_logs',
        null=True,
        blank=True
    )
    
    # Who performed the action (null for anonymous votes)
    performed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vote_audit_logs'
    )
    
    # Context
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context about the action"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Timestamp (immutable)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'vote_audit'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['election', 'action']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} at {self.timestamp}"
    
    @classmethod
    def log_action(cls, action, election=None, vote=None, performed_by=None, 
                   details=None, ip_address=None, user_agent=None):
        """
        Create an audit log entry
        
        Args:
            action: Action type from ACTION_CHOICES
            election: Optional election instance
            vote: Optional vote instance
            performed_by: Optional user who performed action
            details: Optional dict of additional details
            ip_address: Optional IP address
            user_agent: Optional user agent string
        
        Returns:
            VoteAudit instance
        """
        return cls.objects.create(
            action=action,
            election=election,
            vote=vote,
            performed_by=performed_by,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent
        )


class VoteVerification(models.Model):
    """
    Vote verification attempts tracking
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    verification_code = models.CharField(
        max_length=15,
        db_index=True,
        validators=[MinLengthValidator(12)]
    )
    
    vote = models.ForeignKey(
        Vote,
        on_delete=models.CASCADE,
        related_name='verification_attempts',
        null=True,
        blank=True
    )
    
    # Verification details
    verified = models.BooleanField(default=False)
    attempted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'vote_verification'
        ordering = ['-attempted_at']
        indexes = [
            models.Index(fields=['verification_code', 'attempted_at']),
        ]
    
    def __str__(self):
        status = "Success" if self.verified else "Failed"
        return f"Verification {status}: {self.verification_code}"
    
    @classmethod
    def attempt_verification(cls, verification_code, ip_address=None):
        """
        Attempt to verify a vote
        
        Args:
            verification_code: Verification code to check
            ip_address: Optional IP address
        
        Returns:
            Tuple of (success: bool, vote: Vote or None, message: str)
        """
        # Clean code
        clean_code = verification_code.replace('-', '').replace(' ', '').upper()
        
        # Format properly
        if len(clean_code) == 12:
            formatted_code = f"{clean_code[0:3]}-{clean_code[3:6]}-{clean_code[6:9]}-{clean_code[9:12]}"
        else:
            # Invalid format
            cls.objects.create(
                verification_code=verification_code,
                verified=False,
                ip_address=ip_address
            )
            return False, None, "Invalid verification code format"
        
        # Look up vote
        try:
            vote = Vote.objects.get(verification_code=formatted_code)
            
            # Mark as verified
            vote.verify()
            
            # Log verification attempt
            cls.objects.create(
                verification_code=formatted_code,
                vote=vote,
                verified=True,
                ip_address=ip_address
            )
            
            # Audit log
            VoteAudit.log_action(
                action='vote_verified',
                election=vote.election,
                vote=vote,
                ip_address=ip_address
            )
            
            return True, vote, "Vote verified successfully"
        
        except Vote.DoesNotExist:
            # Log failed attempt
            cls.objects.create(
                verification_code=formatted_code,
                verified=False,
                ip_address=ip_address
            )
            return False, None, "Verification code not found"


__all__ = [
    'Vote',
    'VoteAudit',
    'VoteVerification',
]
