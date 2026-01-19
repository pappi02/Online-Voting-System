"""
Election models for iVote Systems
Implements complete election management with candidates, positions, and voting constraints
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import Q
import uuid

User = get_user_model()


class Election(models.Model):
    """
    Main Election model representing a complete election event
    """
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ]
    
    ELECTION_TYPE_CHOICES = [
        ('general', 'General Election'),
        ('primary', 'Primary Election'),
        ('referendum', 'Referendum'),
        ('recall', 'Recall Election'),
        ('special', 'Special Election'),
    ]
    
    id = models.CharField(max_length=32, primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, unique=True, help_text="Election title/name")
    description = models.TextField(blank=True, help_text="Detailed election description")
    election_type = models.CharField(max_length=20, choices=ELECTION_TYPE_CHOICES, default='general')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Election dates and times
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    scheduled_start = models.DateTimeField(help_text="When voting begins")
    scheduled_end = models.DateTimeField(help_text="When voting ends")
    
    # Voter eligibility
    eligible_voters = models.ManyToManyField(
        'accounts.VoterProfile',
        related_name='eligible_elections',
        blank=True,
        help_text="Voters eligible to participate in this election"
    )
    allow_all_eligible = models.BooleanField(
        default=True,
        help_text="If True, all verified voters can participate"
    )
    
    # Election settings
    allow_multiple_candidates = models.BooleanField(
        default=True,
        help_text="Allow voters to select multiple candidates"
    )
    results_visible_before_close = models.BooleanField(
        default=False,
        help_text="Show results before election closes"
    )
    require_voter_authentication = models.BooleanField(
        default=True,
        help_text="Require voter to be logged in"
    )
    
    # Admin info
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='elections_created',
        null=True,
        blank=True,
    )
    modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='elections_modified'
    )
    
    class Meta:
        db_table = 'election'
        ordering = ['-scheduled_start']
        indexes = [
            models.Index(fields=['status', 'scheduled_start']),
            models.Index(fields=['created_by', 'status']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    def is_active(self):
        """Check if election is currently active for voting"""
        now = timezone.now()
        return (
            self.status == 'active' and
            self.scheduled_start <= now <= self.scheduled_end
        )
    
    def is_upcoming(self):
        """Check if election is scheduled but not yet started"""
        return self.status in ['scheduled', 'active'] and timezone.now() < self.scheduled_start
    
    def is_closed(self):
        """Check if election voting period has ended"""
        return self.status == 'closed' or (self.status == 'active' and timezone.now() > self.scheduled_end)
    
    def get_voter_count(self):
        """Get count of eligible voters"""
        if self.allow_all_eligible:
            from accounts.voter_models import VoterProfile
            return VoterProfile.objects.filter(is_eligible=True).count()
        return self.eligible_voters.count()
    
    def get_vote_count(self):
        """Get total votes cast"""
        return Vote.objects.filter(election=self).count()
    
    def get_participation_rate(self):
        """Get voter participation percentage"""
        voter_count = self.get_voter_count()
        if voter_count == 0:
            return 0
        vote_count = self.get_vote_count()
        return round((vote_count / voter_count) * 100, 2)


class Position(models.Model):
    """
    Positions/Offices to be filled in an election
    Example: President, Vice President, Senator, etc.
    """
    
    id = models.CharField(max_length=32, primary_key=True, default=uuid.uuid4, editable=False)
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='positions')
    title = models.CharField(max_length=255, help_text="Position title (e.g., President, Senator)")
    description = models.TextField(blank=True, help_text="Position description and responsibilities")
    
    # Voting constraints
    seats_available = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Number of seats/winners for this position"
    )
    candidates_per_voter = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Max candidates a voter can select for this position"
    )
    
    # Ordering
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Display order in ballot"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'election_position'
        ordering = ['display_order', 'created_at']
        unique_together = [['election', 'title']]
        indexes = [
            models.Index(fields=['election', 'display_order']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.election.title}"
    
    def get_candidates(self):
        """Get all candidates for this position"""
        return self.candidates.filter(status='approved')
    
    def get_candidate_count(self):
        """Get count of approved candidates"""
        return self.get_candidates().count()
    
    def get_top_candidates(self):
        """Get top candidates by vote count"""
        from voting.models import Vote
        candidates = self.get_candidates().annotate(
            vote_count=models.Count('votes')
        ).order_by('-vote_count')
        return candidates[:self.seats_available]


class Candidate(models.Model):
    """
    Candidate running for a position in an election
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ]
    
    id = models.CharField(max_length=32, primary_key=True, default=uuid.uuid4, editable=False)
    position = models.ForeignKey(Position, on_delete=models.CASCADE, related_name='candidates')
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='candidacies'
    )
    
    # Candidate information
    full_name = models.CharField(max_length=255)
    biography = models.TextField(blank=True, help_text="Candidate biography and platform")
    party_affiliation = models.CharField(max_length=100, blank=True)
    website_url = models.URLField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    
    # Candidate documents
    resume = models.FileField(
        upload_to='candidates/resumes/%Y/%m/',
        null=True,
        blank=True,
        help_text="Candidate resume/CV"
    )
    
    # Status and approval
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approval_notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='candidates_approved'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'election_candidate'
        ordering = ['created_at']
        unique_together = [['position', 'user']]  # One candidacy per user per position
        indexes = [
            models.Index(fields=['position', 'status']),
            models.Index(fields=['user', 'status']),
        ]
    
    def __str__(self):
        return f"{self.full_name} - {self.position.title}"
    
    def get_vote_count(self):
        """Get votes received for this candidate"""
        from voting.models import Vote
        return Vote.objects.filter(candidate=self).count()
    
    def approve(self, approved_by, notes=''):
        """Approve candidate"""
        self.status = 'approved'
        self.approved_by = approved_by
        self.approved_at = timezone.now()
        self.approval_notes = notes
        self.save(update_fields=['status', 'approved_by', 'approved_at', 'approval_notes'])
    
    def reject(self, approved_by, notes=''):
        """Reject candidate"""
        self.status = 'rejected'
        self.approved_by = approved_by
        self.approval_notes = notes
        self.save(update_fields=['status', 'approved_by', 'approval_notes'])
    
    def withdraw(self):
        """Withdraw from candidacy"""
        self.status = 'withdrawn'
        self.save(update_fields=['status'])


class ElectionVoter(models.Model):
    """
    Tracks which voters have participated in which elections
    Prevents double voting and enables participation tracking
    """
    
    STATUS_CHOICES = [
        ('eligible', 'Eligible'),
        ('voted', 'Voted'),
        ('abstained', 'Abstained'),
        ('ineligible', 'Ineligible'),
    ]
    
    id = models.CharField(max_length=32, primary_key=True, default=uuid.uuid4, editable=False)
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='election_voters')
    voter = models.ForeignKey('accounts.VoterProfile', on_delete=models.CASCADE, related_name='election_votes')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='eligible')
    
    # Voting tracking
    voted_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'election_voter'
        unique_together = [['election', 'voter']]
        ordering = ['-voted_at', '-created_at']
        indexes = [
            models.Index(fields=['election', 'status']),
            models.Index(fields=['voter', 'voted_at']),
        ]
    
    def __str__(self):
        return f"{self.voter.user.email} - {self.election.title} ({self.status})"
    
    def mark_voted(self, ip_address=None, user_agent=None):
        """Mark voter as having voted"""
        self.status = 'voted'
        self.voted_at = timezone.now()
        if ip_address:
            self.ip_address = ip_address
        if user_agent:
            self.user_agent = user_agent
        self.save(update_fields=['status', 'voted_at', 'ip_address', 'user_agent'])


class ElectionSchedule(models.Model):
    """
    Manages election timeline and state transitions
    Allows scheduling of election state changes
    """
    
    ACTION_CHOICES = [
        ('start', 'Start Election'),
        ('pause', 'Pause Election'),
        ('resume', 'Resume Election'),
        ('close', 'Close Election'),
        ('cancel', 'Cancel Election'),
    ]
    
    id = models.CharField(max_length=32, primary_key=True, default=uuid.uuid4, editable=False)
    election = models.OneToOneField(Election, on_delete=models.CASCADE, related_name='schedule')
    
    # Current state
    current_state = models.CharField(
        max_length=20,
        choices=Election.STATUS_CHOICES,
        default='draft'
    )
    
    # Scheduled actions
    pending_action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        null=True,
        blank=True
    )
    pending_action_time = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'election_schedule'
    
    def __str__(self):
        return f"{self.election.title} - {self.current_state}"
    
    def schedule_action(self, action, scheduled_time):
        """Schedule an election state change"""
        self.pending_action = action
        self.pending_action_time = scheduled_time
        self.save(update_fields=['pending_action', 'pending_action_time'])
    
    def execute_pending_action(self):
        """Execute the pending scheduled action if it's time"""
        if not self.pending_action or not self.pending_action_time:
            return False
        
        if timezone.now() < self.pending_action_time:
            return False
        
        # Map actions to election states
        action_map = {
            'start': 'active',
            'pause': 'paused',
            'resume': 'active',
            'close': 'closed',
            'cancel': 'cancelled',
        }
        
        new_state = action_map.get(self.pending_action)
        if new_state:
            self.election.status = new_state
            self.election.save(update_fields=['status'])
            self.current_state = new_state
            self.pending_action = None
            self.pending_action_time = None
            self.save(update_fields=['current_state', 'pending_action', 'pending_action_time'])
            return True
        
        return False


class ElectionInvite(models.Model):
    """
    Tracks candidate invitations and registrations
    """
    
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
    ]
    
    id = models.CharField(max_length=32, primary_key=True, default=uuid.uuid4, editable=False)
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='invites')
    position = models.ForeignKey(Position, on_delete=models.CASCADE, related_name='invites', null=True, blank=True)
    
    recipient_email = models.EmailField(null=True, blank=True)
    recipient_name = models.CharField(max_length=255, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    accepted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accepted_invites'
    )
    
    # Timestamps
    sent_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'election_invite'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['election', 'status']),
            models.Index(fields=['recipient_email', 'status']),
        ]
    
    def __str__(self):
        return f"Invite to {self.recipient_email} - {self.position.title}"
    
    def is_expired(self):
        """Check if invite has expired"""
        return timezone.now() > self.expires_at or self.status == 'expired'
    
    def accept(self, user):
        """Mark invite as accepted"""
        self.status = 'accepted'
        self.accepted_by = user
        self.accepted_at = timezone.now()
        self.save(update_fields=['status', 'accepted_by', 'accepted_at'])


__all__ = [
    'Election',
    'Position',
    'Candidate',
    'ElectionVoter',
    'ElectionSchedule',
    'ElectionInvite',
]
