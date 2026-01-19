"""
Real-time features API views
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Count
from django.shortcuts import get_object_or_404

from elections.models import Election
from accounts.permissions import IsSystemAdmin, IsElectionOfficial
from .realtime import notification_service, election_notifier, dashboard_updater
from rest_framework import serializers


class BroadcastSerializer(serializers.Serializer):
    """Serializer for broadcast messages"""
    title = serializers.CharField(max_length=200)
    message = serializers.CharField()
    broadcast_type = serializers.ChoiceField(
        choices=['announcement', 'maintenance', 'emergency'],
        default='announcement'
    )
    priority = serializers.ChoiceField(
        choices=['low', 'normal', 'high'],
        default='normal'
    )


class NotificationSerializer(serializers.Serializer):
    """Serializer for user notifications"""
    user_id = serializers.UUIDField()
    title = serializers.CharField(max_length=200)
    message = serializers.CharField()
    notification_type = serializers.ChoiceField(
        choices=['info', 'success', 'warning', 'error'],
        default='info'
    )


class ElectionNotificationSerializer(serializers.Serializer):
    """Serializer for election-wide notifications"""
    election_id = serializers.UUIDField()
    title = serializers.CharField(max_length=200)
    message = serializers.CharField()
    voter_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True
    )


class RealTimeViewSet(viewsets.ViewSet):
    """
    ViewSet for real-time features and broadcasting
    """
    
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    
    @action(detail=False, methods=['post'])
    def broadcast(self, request):
        """
        Send system-wide broadcast
        
        POST /api/realtime/broadcast/
        {
            "title": "System Maintenance",
            "message": "System will be down for maintenance at 10 PM",
            "broadcast_type": "maintenance",
            "priority": "high"
        }
        """
        serializer = BroadcastSerializer(data=request.data)
        
        if serializer.is_valid():
            notification_service.broadcast_system_message(
                title=serializer.validated_data['title'],
                message=serializer.validated_data['message'],
                broadcast_type=serializer.validated_data['broadcast_type'],
                priority=serializer.validated_data['priority']
            )
            
            return Response({
                'success': True,
                'message': 'Broadcast sent successfully'
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def notify_user(self, request):
        """
        Send notification to specific user
        
        POST /api/realtime/notify_user/
        {
            "user_id": "uuid",
            "title": "Important Update",
            "message": "Your profile has been updated",
            "notification_type": "info"
        }
        """
        serializer = NotificationSerializer(data=request.data)
        
        if serializer.is_valid():
            notification_service.send_user_notification(
                user_id=str(serializer.validated_data['user_id']),
                title=serializer.validated_data['title'],
                message=serializer.validated_data['message'],
                notification_type=serializer.validated_data['notification_type']
            )
            
            return Response({
                'success': True,
                'message': 'Notification sent successfully'
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def notify_election(self, request):
        """
        Send notification to all voters in an election
        
        POST /api/realtime/notify_election/
        {
            "election_id": "uuid",
            "title": "Election Update",
            "message": "Voting has been extended by 2 hours",
            "voter_ids": ["uuid1", "uuid2"]  // optional
        }
        """
        serializer = ElectionNotificationSerializer(data=request.data)
        
        if serializer.is_valid():
            notification_service.notify_election_voters(
                election_id=str(serializer.validated_data['election_id']),
                title=serializer.validated_data['title'],
                message=serializer.validated_data['message'],
                voter_ids=[str(vid) for vid in serializer.validated_data.get('voter_ids', [])]
            )
            
            return Response({
                'success': True,
                'message': 'Notifications sent to election voters'
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def publish_results(self, request, pk=None):
        """
        Publish election results and notify voters
        
        POST /api/realtime/{election_id}/publish_results/
        """
        election = get_object_or_404(Election, pk=pk)
        
        # Update election status
        old_status = election.status
        election.status = 'results_published'
        election.save()
        
        # Notify about status change
        election_notifier.notify_election_status_change(
            str(election.id),
            old_status,
            'results_published'
        )
        
        # Notify about published results
        election_notifier.notify_results_published(str(election.id))
        
        return Response({
            'success': True,
            'message': 'Results published and voters notified'
        })
    
    @action(detail=True, methods=['post'])
    def update_election_status(self, request, pk=None):
        """
        Update election status and broadcast change
        
        POST /api/realtime/{election_id}/update_election_status/
        {
            "status": "ongoing"
        }
        """
        election = get_object_or_404(Election, pk=pk)
        new_status = request.data.get('status')
        
        if not new_status:
            return Response(
                {'error': 'Status required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valid_statuses = ['draft', 'scheduled', 'ongoing', 'paused', 'completed', 'cancelled', 'results_published']
        if new_status not in valid_statuses:
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_status = election.status
        election.status = new_status
        election.save()
        
        # Notify about status change
        election_notifier.notify_election_status_change(
            str(election.id),
            old_status,
            new_status
        )
        
        return Response({
            'success': True,
            'old_status': old_status,
            'new_status': new_status,
            'message': 'Election status updated and notifications sent'
        })
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """
        Get real-time dashboard statistics
        
        GET /api/realtime/dashboard_stats/
        """
        from .models import Vote
        from accounts.models import VoterProfile
        
        # Active elections
        active_elections = Election.objects.filter(status='ongoing').count()
        
        # Today's votes
        today = timezone.now().date()
        votes_today = Vote.objects.filter(cast_at__date=today).count()
        
        # Total registered voters
        total_voters = VoterProfile.objects.filter(user__status='approved').count()
        
        # Upcoming elections
        upcoming = Election.objects.filter(
            status='scheduled',
            scheduled_start__gt=timezone.now()
        ).count()
        
        # Recent elections
        recent = Election.objects.filter(
            status__in=['completed', 'results_published']
        ).order_by('-scheduled_end')[:5]
        
        stats = {
            'active_elections': active_elections,
            'votes_today': votes_today,
            'total_voters': total_voters,
            'upcoming_elections': upcoming,
            'recent_elections': [
                {
                    'id': str(e.id),
                    'title': e.title,
                    'status': e.status,
                    'end_date': e.scheduled_end
                }
                for e in recent
            ],
            'timestamp': timezone.now().isoformat()
        }
        
        return Response(stats)


__all__ = [
    'RealTimeViewSet',
    'BroadcastSerializer',
    'NotificationSerializer',
    'ElectionNotificationSerializer'
]
