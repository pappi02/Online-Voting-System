"""
Analytics serializers for results and statistics
"""

from rest_framework import serializers
from django.utils import timezone

from elections.models import Election, Position, Candidate


class CandidateResultSerializer(serializers.Serializer):
    """Serializer for individual candidate results"""
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    party = serializers.CharField(read_only=True)
    photo_url = serializers.URLField(read_only=True, allow_null=True)
    votes = serializers.IntegerField(read_only=True)
    percentage = serializers.FloatField(read_only=True)
    rank = serializers.IntegerField(read_only=True, required=False)


class PositionResultSerializer(serializers.Serializer):
    """Serializer for position-level results"""
    position_id = serializers.UUIDField(read_only=True)
    position_title = serializers.CharField(read_only=True)
    candidates_per_voter = serializers.IntegerField(read_only=True)
    total_votes = serializers.IntegerField(read_only=True)
    participation_rate = serializers.FloatField(read_only=True)
    candidates = CandidateResultSerializer(many=True, read_only=True)
    winner = CandidateResultSerializer(read_only=True, allow_null=True)


class ElectionSummarySerializer(serializers.Serializer):
    """Serializer for election summary statistics"""
    election_id = serializers.UUIDField(read_only=True)
    election_title = serializers.CharField(read_only=True)
    election_type = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    scheduled_start = serializers.DateTimeField(read_only=True)
    scheduled_end = serializers.DateTimeField(read_only=True)
    total_votes = serializers.IntegerField(read_only=True)
    verified_votes = serializers.IntegerField(read_only=True)
    eligible_voters = serializers.IntegerField(read_only=True)
    turnout_percentage = serializers.FloatField(read_only=True)
    verification_rate = serializers.FloatField(read_only=True)
    positions_count = serializers.IntegerField(read_only=True)
    candidates_count = serializers.IntegerField(read_only=True)


class HourlyVoteSerializer(serializers.Serializer):
    """Serializer for hourly vote distribution"""
    hour = serializers.IntegerField(read_only=True)
    votes = serializers.IntegerField(read_only=True)


class DailyVoteSerializer(serializers.Serializer):
    """Serializer for daily vote distribution"""
    date = serializers.DateField(read_only=True)
    votes = serializers.IntegerField(read_only=True)


class TurnoutAnalysisSerializer(serializers.Serializer):
    """Serializer for turnout analysis"""
    by_hour = HourlyVoteSerializer(many=True, read_only=True)
    by_day = DailyVoteSerializer(many=True, read_only=True)


class AuditActionSerializer(serializers.Serializer):
    """Serializer for audit action counts"""
    action = serializers.CharField(read_only=True)
    count = serializers.IntegerField(read_only=True)


class AuditStatisticsSerializer(serializers.Serializer):
    """Serializer for audit statistics"""
    total_audits = serializers.IntegerField(read_only=True)
    actions = AuditActionSerializer(many=True, read_only=True)
    first_action = serializers.DateTimeField(read_only=True, allow_null=True)
    last_action = serializers.DateTimeField(read_only=True, allow_null=True)


class CompleteReportSerializer(serializers.Serializer):
    """Serializer for complete analytics report"""
    summary = ElectionSummarySerializer(read_only=True)
    positions = PositionResultSerializer(many=True, read_only=True)
    turnout = TurnoutAnalysisSerializer(read_only=True)
    audit = AuditStatisticsSerializer(read_only=True)
    generated_at = serializers.DateTimeField(read_only=True)


class TurnoutTrendSerializer(serializers.Serializer):
    """Serializer for turnout trend data"""
    timestamp = serializers.DateTimeField(read_only=True)
    cumulative_votes = serializers.IntegerField(read_only=True)
    hours_elapsed = serializers.FloatField(read_only=True)


class PeakVotingTimeSerializer(serializers.Serializer):
    """Serializer for peak voting periods"""
    hour = serializers.IntegerField(read_only=True)
    votes = serializers.IntegerField(read_only=True)
    period = serializers.CharField(read_only=True)


class ParticipationGapSerializer(serializers.Serializer):
    """Serializer for participation gap analysis"""
    eligible_not_voted = serializers.IntegerField(read_only=True)
    voted = serializers.IntegerField(read_only=True)
    participation_rate = serializers.FloatField(read_only=True)


class ElectionComparisonSerializer(serializers.Serializer):
    """Serializer for election comparison"""
    election_id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    total_votes = serializers.IntegerField(read_only=True)
    eligible_voters = serializers.IntegerField(read_only=True)
    turnout_percentage = serializers.FloatField(read_only=True)
    positions_count = serializers.IntegerField(read_only=True)
    scheduled_start = serializers.DateTimeField(read_only=True)
    scheduled_end = serializers.DateTimeField(read_only=True)


class HistoricalTrendSerializer(serializers.Serializer):
    """Serializer for historical election trends"""
    election_id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    date = serializers.DateTimeField(read_only=True)
    turnout = serializers.FloatField(read_only=True)
    total_votes = serializers.IntegerField(read_only=True)


class ExportRequestSerializer(serializers.Serializer):
    """Serializer for export requests"""
    format = serializers.ChoiceField(
        choices=['csv', 'excel', 'pdf', 'json'],
        required=True,
        help_text="Export format (csv, excel, pdf, or json)"
    )
    election_id = serializers.UUIDField(
        required=True,
        help_text="Election ID to export"
    )
    
    def validate_election_id(self, value):
        """Validate election exists"""
        try:
            Election.objects.get(id=value)
        except Election.DoesNotExist:
            raise serializers.ValidationError("Election not found")
        return value


class VisualizationDataSerializer(serializers.Serializer):
    """Serializer for visualization data"""
    chart_type = serializers.ChoiceField(
        choices=['bar', 'pie', 'line', 'area'],
        read_only=True
    )
    title = serializers.CharField(read_only=True)
    labels = serializers.ListField(read_only=True)
    datasets = serializers.ListField(read_only=True)
    colors = serializers.ListField(read_only=True, required=False)


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard quick stats"""
    active_elections = serializers.IntegerField(read_only=True)
    total_votes_today = serializers.IntegerField(read_only=True)
    total_voters = serializers.IntegerField(read_only=True)
    average_turnout = serializers.FloatField(read_only=True)
    elections_this_month = serializers.IntegerField(read_only=True)
    pending_results = serializers.IntegerField(read_only=True)


class RealTimeStatsSerializer(serializers.Serializer):
    """Serializer for real-time election statistics"""
    election_id = serializers.UUIDField(read_only=True)
    current_votes = serializers.IntegerField(read_only=True)
    eligible_voters = serializers.IntegerField(read_only=True)
    current_turnout = serializers.FloatField(read_only=True)
    votes_last_hour = serializers.IntegerField(read_only=True)
    estimated_final_turnout = serializers.FloatField(read_only=True, allow_null=True)
    time_remaining = serializers.CharField(read_only=True, allow_null=True)
    last_updated = serializers.DateTimeField(read_only=True)


__all__ = [
    'CandidateResultSerializer',
    'PositionResultSerializer',
    'ElectionSummarySerializer',
    'HourlyVoteSerializer',
    'DailyVoteSerializer',
    'TurnoutAnalysisSerializer',
    'AuditStatisticsSerializer',
    'CompleteReportSerializer',
    'TurnoutTrendSerializer',
    'PeakVotingTimeSerializer',
    'ParticipationGapSerializer',
    'ElectionComparisonSerializer',
    'HistoricalTrendSerializer',
    'ExportRequestSerializer',
    'VisualizationDataSerializer',
    'DashboardStatsSerializer',
    'RealTimeStatsSerializer',
]
