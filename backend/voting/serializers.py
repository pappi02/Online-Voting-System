"""
Voting serializers for iVote Systems
Handles vote casting, verification, and results
"""

from rest_framework import serializers
from django.utils import timezone
from django.db import transaction

from .models import Vote, VoteAudit, VoteVerification
from elections.models import Election, Position, Candidate
from accounts.models import VoterProfile


class CandidateVoteSerializer(serializers.Serializer):
    """
    Serializer for selecting candidates in a position
    """
    position_id = serializers.UUIDField()
    candidate_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=0,
        help_text="List of candidate IDs to vote for"
    )


class CastVoteSerializer(serializers.Serializer):
    """
    Serializer for casting a vote
    """
    election_id = serializers.UUIDField()
    votes = CandidateVoteSerializer(many=True)
    
    def validate_election_id(self, value):
        """Validate election exists and is accepting votes"""
        try:
            election = Election.objects.get(id=value)
        except Election.DoesNotExist:
            raise serializers.ValidationError("Election not found")
        
        # Check if voting is open
        if election.status != 'ongoing':
            raise serializers.ValidationError(
                f"Election is not open for voting (status: {election.status})"
            )
        
        # Check schedule
        now = timezone.now()
        schedule = getattr(election, 'schedule', None)
        if schedule:
            if schedule.voting_starts > now:
                raise serializers.ValidationError(
                    f"Voting has not started yet (starts: {schedule.voting_starts})"
                )
            if schedule.voting_ends < now:
                raise serializers.ValidationError(
                    f"Voting has ended (ended: {schedule.voting_ends})"
                )
        
        return value
    
    def validate(self, data):
        """Validate entire vote"""
        election_id = data.get('election_id')
        votes = data.get('votes', [])
        
        # Get election
        try:
            election = Election.objects.get(id=election_id)
        except Election.DoesNotExist:
            raise serializers.ValidationError("Election not found")
        
        # Check voter eligibility
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required")
        
        # Get voter profile
        try:
            voter_profile = request.user.voter_profile
        except VoterProfile.DoesNotExist:
            raise serializers.ValidationError("Voter profile not found")
        
        # Check if voter is eligible for this election
        from elections.models import ElectionVoter
        try:
            election_voter = ElectionVoter.objects.get(
                election=election,
                voter=voter_profile
            )
            if election_voter.status not in ['invited', 'eligible']:
                raise serializers.ValidationError(
                    f"Cannot vote: status is {election_voter.status}"
                )
        except ElectionVoter.DoesNotExist:
            raise serializers.ValidationError("Not eligible to vote in this election")
        
        # Validate vote data structure
        position_votes = {}
        for vote in votes:
            position_id = vote['position_id']
            candidate_ids = vote['candidate_ids']
            
            # Check position exists in election
            try:
                position = election.positions.get(id=position_id)
            except Position.DoesNotExist:
                raise serializers.ValidationError(
                    f"Position {position_id} not found in election"
                )
            
            # Validate number of candidates
            if len(candidate_ids) > position.candidates_per_voter:
                raise serializers.ValidationError(
                    f"Too many candidates for position '{position.title}'. "
                    f"Maximum: {position.candidates_per_voter}"
                )
            
            # Validate candidates exist and are approved
            for candidate_id in candidate_ids:
                try:
                    candidate = position.candidates.get(
                        id=candidate_id,
                        status='approved'
                    )
                except Candidate.DoesNotExist:
                    raise serializers.ValidationError(
                        f"Invalid candidate {candidate_id} for position '{position.title}'"
                    )
            
            position_votes[str(position_id)] = [str(cid) for cid in candidate_ids]
        
        data['position_votes'] = position_votes
        data['election'] = election
        data['voter_profile'] = voter_profile
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        """Cast the vote"""
        election = validated_data['election']
        voter_profile = validated_data['voter_profile']
        position_votes = validated_data['position_votes']
        
        # Get request context
        request = self.context.get('request')
        ip_address = None
        user_agent = None
        if request:
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Cast vote
        vote, verification_code = Vote.cast_vote(
            election=election,
            voter_profile=voter_profile,
            position_votes=position_votes,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Audit log
        VoteAudit.log_action(
            action='vote_cast',
            election=election,
            vote=vote,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                'position_count': len(position_votes),
                'voter_hash': vote.voter_hash
            }
        )
        
        # Send real-time notifications
        try:
            from .realtime import election_notifier, dashboard_updater
            
            # Notify election group
            election_notifier.notify_vote_cast(str(election.id))
            
            # Update dashboard
            dashboard_updater.notify_new_vote(str(election.id), election.title)
        except Exception:
            # Don't fail vote if notification fails
            pass
        
        return {
            'vote_id': vote.id,
            'verification_code': verification_code,
            'election': election.title,
            'cast_at': vote.cast_at,
            'message': 'Vote cast successfully'
        }


class VoteVerificationSerializer(serializers.Serializer):
    """
    Serializer for vote verification
    """
    verification_code = serializers.CharField(
        max_length=20,
        min_length=12,
        help_text="Verification code from vote receipt"
    )
    
    def validate_verification_code(self, value):
        """Clean and validate code format"""
        # Remove spaces and hyphens
        clean = value.replace('-', '').replace(' ', '').upper()
        if len(clean) != 12:
            raise serializers.ValidationError("Invalid verification code format")
        return clean
    
    def create(self, validated_data):
        """Verify the vote"""
        verification_code = validated_data['verification_code']
        
        # Get IP from request
        request = self.context.get('request')
        ip_address = None
        if request:
            ip_address = request.META.get('REMOTE_ADDR')
        
        # Attempt verification
        success, vote, message = VoteVerification.attempt_verification(
            verification_code,
            ip_address
        )
        
        result = {
            'success': success,
            'message': message
        }
        
        if success and vote:
            result.update({
                'election': vote.election.title,
                'cast_at': vote.cast_at,
                'verified_at': vote.verified_at
            })
        
        return result


class VoteStatusSerializer(serializers.Serializer):
    """
    Serializer for checking vote status in an election
    """
    election_id = serializers.UUIDField()
    
    def validate_election_id(self, value):
        """Validate election exists"""
        try:
            election = Election.objects.get(id=value)
        except Election.DoesNotExist:
            raise serializers.ValidationError("Election not found")
        return value


class VoteReceiptSerializer(serializers.Serializer):
    """
    Serializer for vote receipt display
    """
    verification_code = serializers.CharField(read_only=True)
    election = serializers.CharField(read_only=True)
    cast_at = serializers.DateTimeField(read_only=True)
    message = serializers.CharField(read_only=True)
    
    instructions = serializers.SerializerMethodField()
    
    def get_instructions(self, obj):
        return (
            "Save this verification code to verify your vote later. "
            "Your vote is encrypted and anonymous - this code is the only way "
            "to confirm your vote was recorded."
        )


class VoteAuditSerializer(serializers.ModelSerializer):
    """
    Serializer for vote audit logs (admin only)
    """
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    election_title = serializers.CharField(source='election.title', read_only=True)
    performed_by_email = serializers.CharField(
        source='performed_by.email',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = VoteAudit
        fields = [
            'id', 'action', 'action_display', 'election', 'election_title',
            'vote', 'performed_by', 'performed_by_email', 'details',
            'ip_address', 'timestamp'
        ]
        read_only_fields = fields


class AdminVoteDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for vote details (admin only - includes decryption)
    """
    election_title = serializers.CharField(source='election.title', read_only=True)
    decrypted_vote = serializers.SerializerMethodField()
    audit_logs = VoteAuditSerializer(many=True, read_only=True)
    
    class Meta:
        model = Vote
        fields = [
            'id', 'election', 'election_title', 'voter_hash',
            'cast_at', 'verified_at', 'verification_code',
            'ip_address', 'decrypted_vote', 'audit_logs'
        ]
        read_only_fields = fields
    
    def get_decrypted_vote(self, obj):
        """
        Decrypt vote data (admin only)
        """
        request = self.context.get('request')
        
        # Only allow admin to decrypt
        if not request or not request.user or not request.user.is_staff:
            return None
        
        try:
            # Log decryption
            VoteAudit.log_action(
                action='vote_decrypted',
                election=obj.election,
                vote=obj,
                performed_by=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            # Decrypt
            vote_data = obj.decrypt_vote_data()
            
            # Add candidate details
            detailed_vote = {}
            for position_id, candidate_ids in vote_data.items():
                try:
                    position = Position.objects.get(id=position_id)
                    candidates = []
                    for candidate_id in candidate_ids:
                        try:
                            candidate = Candidate.objects.get(id=candidate_id)
                            candidates.append({
                                'id': str(candidate.id),
                                'name': candidate.name,
                                'party': candidate.party
                            })
                        except Candidate.DoesNotExist:
                            candidates.append({
                                'id': candidate_id,
                                'name': 'Unknown',
                                'party': 'N/A'
                            })
                    
                    detailed_vote[position.title] = candidates
                except Position.DoesNotExist:
                    detailed_vote[position_id] = candidate_ids
            
            return detailed_vote
        
        except Exception as e:
            return {'error': str(e)}


class ElectionResultsSerializer(serializers.Serializer):
    """
    Serializer for election results
    """
    election_id = serializers.UUIDField()
    election_title = serializers.CharField(read_only=True)
    total_votes = serializers.IntegerField(read_only=True)
    positions = serializers.ListField(read_only=True)
    generated_at = serializers.DateTimeField(read_only=True)


__all__ = [
    'CastVoteSerializer',
    'VoteVerificationSerializer',
    'VoteStatusSerializer',
    'VoteReceiptSerializer',
    'VoteAuditSerializer',
    'AdminVoteDetailSerializer',
    'ElectionResultsSerializer',
]