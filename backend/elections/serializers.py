"""
Election app serializers
Handles serialization and validation of election models
"""

from rest_framework import serializers
from django.utils import timezone
from django.db import transaction, models
from django.db.models import Q
from .models import (
    Election, Position, Candidate, ElectionVoter,
    ElectionSchedule, ElectionInvite
)
from accounts.models import VoterProfile, User


class ElectionListSerializer(serializers.ModelSerializer):
    """Simplified election serializer for list views"""
    
    position_count = serializers.SerializerMethodField()
    candidate_count = serializers.SerializerMethodField()
    voter_count = serializers.SerializerMethodField()
    vote_count = serializers.SerializerMethodField()
    participation_rate = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    is_upcoming = serializers.SerializerMethodField()
    is_closed = serializers.SerializerMethodField()
    
    class Meta:
        model = Election
        fields = [
            'id', 'title', 'election_type', 'status',
            'scheduled_start', 'scheduled_end',
            'position_count', 'candidate_count', 'voter_count',
            'vote_count', 'participation_rate',
            'is_active', 'is_upcoming', 'is_closed', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_position_count(self, obj):
        return obj.positions.count()
    
    def get_candidate_count(self, obj):
        from django.db.models import Count, Sum
        result = obj.positions.annotate(
            cand_count=Count('candidates', filter=Q(candidates__status='approved'))
        ).aggregate(total=Sum('cand_count'))
        return result['total'] or 0
    
    def get_voter_count(self, obj):
        return obj.get_voter_count()
    
    def get_vote_count(self, obj):
        return obj.get_vote_count()
    
    def get_participation_rate(self, obj):
        return obj.get_participation_rate()
    
    def get_is_active(self, obj):
        return obj.is_active()
    
    def get_is_upcoming(self, obj):
        return obj.is_upcoming()
    
    def get_is_closed(self, obj):
        return obj.is_closed()


class ElectionDetailSerializer(serializers.ModelSerializer):
    """Detailed election serializer with all information"""
    
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    modified_by_name = serializers.CharField(source='modified_by.get_full_name', read_only=True, allow_null=True)
    positions = serializers.SerializerMethodField()
    position_count = serializers.SerializerMethodField()
    voter_count = serializers.SerializerMethodField()
    vote_count = serializers.SerializerMethodField()
    participation_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = Election
        fields = [
            'id', 'title', 'description', 'election_type', 'status',
            'scheduled_start', 'scheduled_end',
            'allow_all_eligible', 'allow_multiple_candidates',
            'results_visible_before_close', 'require_voter_authentication',
            'created_by', 'created_by_name', 'modified_by', 'modified_by_name',
            'positions', 'position_count', 'voter_count', 'vote_count',
            'participation_rate', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
    
    def get_positions(self, obj):
        positions = obj.positions.all()
        return PositionListSerializer(positions, many=True).data
    
    def get_position_count(self, obj):
        return obj.positions.count()
    
    def get_voter_count(self, obj):
        return obj.get_voter_count()
    
    def get_vote_count(self, obj):
        return obj.get_vote_count()
    
    def get_participation_rate(self, obj):
        return obj.get_participation_rate()
    
    def validate_scheduled_end(self, value):
        """Ensure end date is after start date"""
        if self.initial_data.get('scheduled_start'):
            start = self.initial_data['scheduled_start']
            if value <= start:
                raise serializers.ValidationError("End date must be after start date")
        return value


class ElectionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating elections"""
    
    class Meta:
        model = Election
        fields = [
            'title', 'description', 'election_type',
            'scheduled_start', 'scheduled_end',
            'allow_all_eligible', 'allow_multiple_candidates',
            'results_visible_before_close', 'require_voter_authentication'
        ]
    
    def validate_title(self, value):
        """Ensure title is unique"""
        if Election.objects.filter(title__iexact=value).exists():
            raise serializers.ValidationError("An election with this title already exists")
        return value
    
    def validate_scheduled_end(self, value):
        """Ensure end date is after start date"""
        start = self.initial_data.get('scheduled_start')
        if start and value <= start:
            raise serializers.ValidationError("End date must be after start date")
        return value
    
    def validate_scheduled_start(self, value):
        """Ensure start date is in the future"""
        if value <= timezone.now():
            raise serializers.ValidationError("Start date must be in the future")
        return value
    
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['created_by'] = user
        election = Election.objects.create(**validated_data)
        
        # Create schedule
        ElectionSchedule.objects.create(election=election, current_state='draft')
        
        return election


class PositionListSerializer(serializers.ModelSerializer):
    """Simplified position serializer for list views"""
    
    candidate_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Position
        fields = ['id', 'title', 'description', 'seats_available', 'candidates_per_voter', 'candidate_count', 'display_order']
        read_only_fields = ['id']
    
    def get_candidate_count(self, obj):
        return obj.get_candidate_count()


class PositionDetailSerializer(serializers.ModelSerializer):
    """Detailed position serializer with candidates"""
    
    election_id = serializers.CharField(source='election.id', read_only=True)
    candidates = serializers.SerializerMethodField()
    candidate_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Position
        fields = [
            'id', 'election_id', 'title', 'description',
            'seats_available', 'candidates_per_voter', 'display_order',
            'candidates', 'candidate_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_candidates(self, obj):
        candidates = obj.get_candidates()
        return CandidateListSerializer(candidates, many=True).data
    
    def get_candidate_count(self, obj):
        return obj.get_candidate_count()
    
    def validate_candidates_per_voter(self, value):
        """Ensure candidates_per_voter doesn't exceed seats_available"""
        seats = self.initial_data.get('seats_available', self.instance.seats_available if self.instance else 1)
        if value > seats:
            raise serializers.ValidationError("Candidates per voter cannot exceed seats available")
        return value


class PositionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating positions"""
    
    class Meta:
        model = Position
        fields = ['title', 'description', 'seats_available', 'candidates_per_voter', 'display_order']
    
    def validate_candidates_per_voter(self, value):
        seats = self.initial_data.get('seats_available', 1)
        if value > seats:
            raise serializers.ValidationError("Candidates per voter cannot exceed seats available")
        return value


class CandidateListSerializer(serializers.ModelSerializer):
    """Simplified candidate serializer for list views"""
    
    position_title = serializers.CharField(source='position.title', read_only=True)
    vote_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Candidate
        fields = ['id', 'full_name', 'party_affiliation', 'position_title', 'status', 'vote_count', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_vote_count(self, obj):
        return obj.get_vote_count()


class CandidateDetailSerializer(serializers.ModelSerializer):
    """Detailed candidate serializer"""
    
    position_id = serializers.CharField(source='position.id', read_only=True)
    position_title = serializers.CharField(source='position.title', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True, allow_null=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True, allow_null=True)
    vote_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Candidate
        fields = [
            'id', 'position_id', 'position_title', 'user_email',
            'full_name', 'biography', 'party_affiliation',
            'website_url', 'email', 'phone',
            'status', 'approval_notes', 'approved_by_name', 'approved_at',
            'vote_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user_email', 'created_at', 'updated_at']


class CandidateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating candidates"""
    
    class Meta:
        model = Candidate
        fields = [
            'full_name', 'biography', 'party_affiliation',
            'website_url', 'email', 'phone', 'resume'
        ]
    
    def create(self, validated_data):
        position_id = self.context['view'].kwargs.get('position_id')
        position = Position.objects.get(id=position_id)
        
        # If user is authenticated, use their account
        user = self.context['request'].user if self.context['request'].user.is_authenticated else None
        
        validated_data['position'] = position
        if user and not user.is_anonymous:
            validated_data['user'] = user
        
        return Candidate.objects.create(**validated_data)


class CandidateApprovalSerializer(serializers.ModelSerializer):
    """Serializer for approving/rejecting candidates"""
    
    class Meta:
        model = Candidate
        fields = ['status', 'approval_notes']
    
    def validate_status(self, value):
        """Ensure valid status transition"""
        if value not in ['approved', 'rejected']:
            raise serializers.ValidationError("Status must be 'approved' or 'rejected'")
        return value
    
    def update(self, instance, validated_data):
        status = validated_data.get('status', instance.status)
        notes = validated_data.get('approval_notes', instance.approval_notes)
        user = self.context['request'].user
        
        if status == 'approved':
            instance.approve(user, notes)
        elif status == 'rejected':
            instance.reject(user, notes)
        
        return instance


class ElectionVoterSerializer(serializers.ModelSerializer):
    """Serializer for election voter tracking"""
    
    voter_email = serializers.CharField(source='voter.user.email', read_only=True)
    election_title = serializers.CharField(source='election.title', read_only=True)
    
    class Meta:
        model = ElectionVoter
        fields = ['id', 'election_title', 'voter_email', 'status', 'voted_at', 'created_at']
        read_only_fields = fields


class ElectionScheduleSerializer(serializers.ModelSerializer):
    """Serializer for election scheduling"""
    
    election_title = serializers.CharField(source='election.title', read_only=True)
    
    class Meta:
        model = ElectionSchedule
        fields = ['id', 'election_title', 'current_state', 'pending_action', 'pending_action_time']
        read_only_fields = ['id', 'current_state']
    
    def validate_pending_action_time(self, value):
        """Ensure action time is in the future"""
        if value <= timezone.now():
            raise serializers.ValidationError("Action time must be in the future")
        return value


class ElectionInviteSerializer(serializers.ModelSerializer):
    """Serializer for candidate invitations"""
    
    election_title = serializers.CharField(source='election.title', read_only=True)
    position_title = serializers.CharField(source='position.title', read_only=True)
    
    class Meta:
        model = ElectionInvite
        fields = [
            'id', 'election_title', 'position_title',
            'recipient_email', 'recipient_name', 'status',
            'sent_at', 'accepted_at', 'expires_at'
        ]
        read_only_fields = ['id', 'sent_at', 'accepted_at']
    
    def validate_expires_at(self, value):
        """Ensure expiration is in the future"""
        if value <= timezone.now():
            raise serializers.ValidationError("Expiration date must be in the future")
        return value


class ElectionInviteCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating candidate invitations"""
    
    class Meta:
        model = ElectionInvite
        fields = ['recipient_email', 'recipient_name', 'expires_at']
    
    def create(self, validated_data):
        election_id = self.context['view'].kwargs.get('election_id')
        position_id = self.context['view'].kwargs.get('position_id')
        
        election = Election.objects.get(id=election_id)
        position = Position.objects.get(id=position_id)
        
        validated_data['election'] = election
        validated_data['position'] = position
        
        return ElectionInvite.objects.create(**validated_data)


__all__ = [
    'ElectionListSerializer',
    'ElectionDetailSerializer',
    'ElectionCreateSerializer',
    'PositionListSerializer',
    'PositionDetailSerializer',
    'PositionCreateSerializer',
    'CandidateListSerializer',
    'CandidateDetailSerializer',
    'CandidateCreateSerializer',
    'CandidateApprovalSerializer',
    'ElectionVoterSerializer',
    'ElectionScheduleSerializer',
    'ElectionInviteSerializer',
    'ElectionInviteCreateSerializer',
]
