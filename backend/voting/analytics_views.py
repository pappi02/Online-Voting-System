"""
Analytics API views for election results and statistics
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta

from elections.models import Election, ElectionVoter
from accounts.permissions import IsSystemAdmin, IsElectionOfficial
from .models import Vote
from .analytics import VoteAnalytics, TurnoutAnalytics, ComparisonAnalytics
from .analytics_serializers import (
    CompleteReportSerializer, ElectionSummarySerializer,
    PositionResultSerializer, TurnoutTrendSerializer,
    PeakVotingTimeSerializer, ParticipationGapSerializer,
    ElectionComparisonSerializer, HistoricalTrendSerializer,
    VisualizationDataSerializer, DashboardStatsSerializer,
    RealTimeStatsSerializer
)
from .exports import CSVExporter, ExcelExporter, PDFExporter, JSONExporter


class AnalyticsViewSet(viewsets.ViewSet):
    """
    ViewSet for election analytics and statistics
    """
    
    def get_permissions(self):
        """Permission based on action"""
        if self.action in ['public_results', 'public_summary']:
            return [permissions.AllowAny()]
        elif self.action in ['dashboard', 'real_time_stats']:
            return [permissions.IsAuthenticated()]
        else:
            return [permissions.IsAuthenticated(), IsElectionOfficial()]
    
    @action(detail=True, methods=['get'])
    def complete_report(self, request, pk=None):
        """
        Get complete analytics report for an election
        
        GET /api/analytics/{election_id}/complete_report/
        """
        election = get_object_or_404(Election, pk=pk)
        
        # Check permissions
        if election.status not in ['completed', 'results_published']:
            if not (request.user.is_staff or request.user.is_admin()):
                return Response(
                    {'error': 'Results not yet available'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        analytics = VoteAnalytics(election)
        report = analytics.get_complete_report()
        
        serializer = CompleteReportSerializer(report)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """
        Get election summary statistics
        
        GET /api/analytics/{election_id}/summary/
        """
        election = get_object_or_404(Election, pk=pk)
        
        analytics = VoteAnalytics(election)
        summary = analytics.get_summary_statistics()
        
        serializer = ElectionSummarySerializer(summary)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def position_results(self, request, pk=None):
        """
        Get detailed results for each position
        
        GET /api/analytics/{election_id}/position_results/
        """
        election = get_object_or_404(Election, pk=pk)
        
        # Check permissions for unpublished results
        if election.status not in ['completed', 'results_published']:
            if not (request.user.is_authenticated and 
                   (request.user.is_staff or request.user.is_admin())):
                return Response(
                    {'error': 'Results not yet available'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        analytics = VoteAnalytics(election)
        positions = analytics.get_position_statistics()
        
        serializer = PositionResultSerializer(positions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def turnout_trend(self, request, pk=None):
        """
        Get turnout trend over time
        
        GET /api/analytics/{election_id}/turnout_trend/
        """
        election = get_object_or_404(Election, pk=pk)
        
        trend = TurnoutAnalytics.get_turnout_trend(election)
        serializer = TurnoutTrendSerializer(trend, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def peak_times(self, request, pk=None):
        """
        Get peak voting times
        
        GET /api/analytics/{election_id}/peak_times/
        """
        election = get_object_or_404(Election, pk=pk)
        
        peaks = TurnoutAnalytics.get_peak_voting_times(election)
        serializer = PeakVotingTimeSerializer(peaks, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def participation_gaps(self, request, pk=None):
        """
        Get participation gap analysis
        
        GET /api/analytics/{election_id}/participation_gaps/
        """
        election = get_object_or_404(Election, pk=pk)
        
        gaps = TurnoutAnalytics.get_participation_gaps(election)
        serializer = ParticipationGapSerializer(gaps)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def compare_elections(self, request):
        """
        Compare multiple elections
        
        POST /api/analytics/compare_elections/
        {
            "election_ids": ["uuid1", "uuid2", "uuid3"]
        }
        """
        election_ids = request.data.get('election_ids', [])
        
        if not election_ids:
            return Response(
                {'error': 'election_ids required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        comparisons = ComparisonAnalytics.compare_elections(election_ids)
        serializer = ElectionComparisonSerializer(comparisons, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def historical_trends(self, request):
        """
        Get historical election trends
        
        GET /api/analytics/historical_trends/?type=general&limit=10
        """
        election_type = request.query_params.get('type')
        limit = int(request.query_params.get('limit', 10))
        
        trends = ComparisonAnalytics.get_historical_trends(election_type, limit)
        serializer = HistoricalTrendSerializer(trends, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def visualization_data(self, request, pk=None):
        """
        Get data formatted for charts/visualization
        
        GET /api/analytics/{election_id}/visualization_data/?type=bar
        """
        election = get_object_or_404(Election, pk=pk)
        chart_type = request.query_params.get('type', 'bar')
        
        analytics = VoteAnalytics(election)
        positions = analytics.get_position_statistics()
        
        # Format for visualization
        visualizations = []
        
        for position in positions:
            vis_data = {
                'chart_type': chart_type,
                'title': position['position_title'],
                'labels': [c['name'] for c in position['candidates']],
                'datasets': [{
                    'label': 'Votes',
                    'data': [c['votes'] for c in position['candidates']]
                }],
                'colors': self._generate_colors(len(position['candidates']))
            }
            visualizations.append(vis_data)
        
        serializer = VisualizationDataSerializer(visualizations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def dashboard(self, request):
        """
        Get dashboard statistics
        
        GET /api/analytics/dashboard/
        """
        # Active elections
        active_elections = Election.objects.filter(
            status='ongoing'
        ).count()
        
        # Votes today
        today = timezone.now().date()
        votes_today = Vote.objects.filter(
            cast_at__date=today
        ).count()
        
        # Total voters
        total_voters = ElectionVoter.objects.filter(
            status='voted'
        ).values('voter').distinct().count()
        
        # Average turnout (completed elections)
        completed = Election.objects.filter(
            status__in=['completed', 'results_published']
        )
        turnouts = []
        for election in completed:
            analytics = VoteAnalytics(election)
            turnouts.append(analytics.get_turnout_percentage())
        
        avg_turnout = sum(turnouts) / len(turnouts) if turnouts else 0
        
        # Elections this month
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0)
        elections_this_month = Election.objects.filter(
            scheduled_start__gte=month_start
        ).count()
        
        # Pending results
        pending_results = Election.objects.filter(
            status='completed'
        ).count()
        
        stats = {
            'active_elections': active_elections,
            'total_votes_today': votes_today,
            'total_voters': total_voters,
            'average_turnout': round(avg_turnout, 2),
            'elections_this_month': elections_this_month,
            'pending_results': pending_results
        }
        
        serializer = DashboardStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def real_time_stats(self, request, pk=None):
        """
        Get real-time statistics for ongoing election
        
        GET /api/analytics/{election_id}/real_time_stats/
        """
        election = get_object_or_404(Election, pk=pk)
        
        if election.status != 'ongoing':
            return Response(
                {'error': 'Election is not ongoing'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        analytics = VoteAnalytics(election)
        
        # Votes in last hour
        one_hour_ago = timezone.now() - timedelta(hours=1)
        votes_last_hour = Vote.objects.filter(
            election=election,
            cast_at__gte=one_hour_ago
        ).count()
        
        # Time remaining
        time_remaining = None
        if election.scheduled_end:
            remaining = election.scheduled_end - timezone.now()
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            time_remaining = f"{hours}h {minutes}m"
        
        # Estimated final turnout (simple projection)
        current_turnout = analytics.get_turnout_percentage()
        estimated_final = None
        if election.scheduled_start and election.scheduled_end:
            total_duration = (election.scheduled_end - election.scheduled_start).total_seconds()
            elapsed = (timezone.now() - election.scheduled_start).total_seconds()
            if elapsed > 0 and total_duration > 0:
                progress = elapsed / total_duration
                if progress > 0:
                    estimated_final = round(current_turnout / progress, 2)
        
        stats = {
            'election_id': election.id,
            'current_votes': analytics.get_total_votes(),
            'eligible_voters': analytics.get_eligible_voters(),
            'current_turnout': current_turnout,
            'votes_last_hour': votes_last_hour,
            'estimated_final_turnout': estimated_final,
            'time_remaining': time_remaining,
            'last_updated': timezone.now()
        }
        
        serializer = RealTimeStatsSerializer(stats)
        return Response(serializer.data)
    
    def _generate_colors(self, count):
        """Generate color palette for charts"""
        colors = [
            '#366092', '#4CAF50', '#FFC107', '#F44336', '#9C27B0',
            '#00BCD4', '#FF5722', '#607D8B', '#8BC34A', '#FF9800'
        ]
        return colors[:count]


class ExportViewSet(viewsets.ViewSet):
    """
    ViewSet for exporting election results
    """
    
    permission_classes = [permissions.IsAuthenticated, IsElectionOfficial]
    
    @action(detail=True, methods=['get'])
    def csv(self, request, pk=None):
        """
        Export results as CSV
        
        GET /api/exports/{election_id}/csv/
        """
        election = get_object_or_404(Election, pk=pk)
        return CSVExporter.export_results(election)
    
    @action(detail=True, methods=['get'])
    def excel(self, request, pk=None):
        """
        Export results as Excel
        
        GET /api/exports/{election_id}/excel/
        """
        election = get_object_or_404(Election, pk=pk)
        return ExcelExporter.export_results(election)
    
    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """
        Export results as PDF
        
        GET /api/exports/{election_id}/pdf/
        """
        election = get_object_or_404(Election, pk=pk)
        return PDFExporter.export_results(election)
    
    @action(detail=True, methods=['get'])
    def json(self, request, pk=None):
        """
        Export complete report as JSON
        
        GET /api/exports/{election_id}/json/
        """
        election = get_object_or_404(Election, pk=pk)
        return JSONExporter.export_complete_report(election)
    
    @action(detail=True, methods=['get'])
    def turnout_csv(self, request, pk=None):
        """
        Export turnout analysis as CSV
        
        GET /api/exports/{election_id}/turnout_csv/
        """
        election = get_object_or_404(Election, pk=pk)
        return CSVExporter.export_turnout(election)


__all__ = [
    'AnalyticsViewSet',
    'ExportViewSet'
]
