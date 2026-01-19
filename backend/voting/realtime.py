"""
Real-time notification system
"""

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from typing import Dict, List, Optional
import json

from django.contrib.auth import get_user_model

User = get_user_model()


class NotificationService:
    """
    Service for sending real-time notifications via WebSocket
    """
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
    
    def send_user_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: str = 'info',
        data: Optional[Dict] = None
    ):
        """
        Send notification to specific user
        
        Args:
            user_id: User UUID
            title: Notification title
            message: Notification message
            notification_type: Type (info, success, warning, error)
            data: Additional data
        """
        group_name = f'user_{user_id}_notifications'
        
        payload = {
            'title': title,
            'message': message,
            'type': notification_type,
            'timestamp': timezone.now().isoformat(),
            'data': data or {}
        }
        
        async_to_sync(self.channel_layer.group_send)(
            group_name,
            {
                'type': 'notification',
                'data': payload
            }
        )
    
    def send_alert(
        self,
        user_id: str,
        title: str,
        message: str,
        severity: str = 'medium',
        action_url: Optional[str] = None
    ):
        """
        Send alert to specific user
        
        Args:
            user_id: User UUID
            title: Alert title
            message: Alert message
            severity: Alert severity (low, medium, high, critical)
            action_url: Optional action URL
        """
        group_name = f'user_{user_id}_notifications'
        
        payload = {
            'title': title,
            'message': message,
            'severity': severity,
            'action_url': action_url,
            'timestamp': timezone.now().isoformat()
        }
        
        async_to_sync(self.channel_layer.group_send)(
            group_name,
            {
                'type': 'alert',
                'data': payload
            }
        )
    
    def broadcast_system_message(
        self,
        title: str,
        message: str,
        broadcast_type: str = 'announcement',
        priority: str = 'normal'
    ):
        """
        Broadcast message to all connected users
        
        Args:
            title: Broadcast title
            message: Broadcast message
            broadcast_type: Type (announcement, maintenance, emergency)
            priority: Priority level (low, normal, high)
        """
        payload = {
            'title': title,
            'message': message,
            'broadcast_type': broadcast_type,
            'priority': priority,
            'timestamp': timezone.now().isoformat()
        }
        
        async_to_sync(self.channel_layer.group_send)(
            'system_broadcasts',
            {
                'type': 'broadcast' if broadcast_type != 'announcement' else 'announcement',
                'data': payload
            }
        )
    
    def notify_election_voters(
        self,
        election_id: str,
        title: str,
        message: str,
        voter_ids: Optional[List[str]] = None
    ):
        """
        Notify all voters in an election
        
        Args:
            election_id: Election UUID
            title: Notification title
            message: Notification message
            voter_ids: Optional list of specific voter IDs
        """
        from elections.models import Election, ElectionVoter
        
        try:
            election = Election.objects.get(id=election_id)
            
            # Get voters
            if voter_ids:
                voters = User.objects.filter(id__in=voter_ids)
            else:
                election_voters = ElectionVoter.objects.filter(
                    election=election
                ).select_related('voter')
                voters = [ev.voter for ev in election_voters]
            
            # Send notification to each voter
            for voter in voters:
                self.send_user_notification(
                    user_id=str(voter.id),
                    title=title,
                    message=message,
                    notification_type='info',
                    data={'election_id': str(election_id)}
                )
        
        except Election.DoesNotExist:
            pass


class ElectionEventNotifier:
    """
    Specialized notifier for election events
    """
    
    def __init__(self):
        self.notification_service = NotificationService()
        self.channel_layer = get_channel_layer()
    
    def notify_vote_cast(self, election_id: str, anonymous: bool = True):
        """
        Notify election group that a vote was cast
        
        Args:
            election_id: Election UUID
            anonymous: Whether to keep notification anonymous
        """
        from .analytics import VoteAnalytics
        from elections.models import Election
        
        try:
            election = Election.objects.get(id=election_id)
            analytics = VoteAnalytics(election)
            
            stats = {
                'election_id': str(election_id),
                'total_votes': analytics.get_total_votes(),
                'turnout_percentage': analytics.get_turnout_percentage(),
                'timestamp': timezone.now().isoformat()
            }
            
            async_to_sync(self.channel_layer.group_send)(
                f'election_{election_id}',
                {
                    'type': 'vote_cast',
                    'data': stats
                }
            )
        
        except Election.DoesNotExist:
            pass
    
    def notify_election_status_change(
        self,
        election_id: str,
        old_status: str,
        new_status: str
    ):
        """
        Notify about election status change
        
        Args:
            election_id: Election UUID
            old_status: Previous status
            new_status: New status
        """
        from elections.models import Election
        
        try:
            election = Election.objects.get(id=election_id)
            
            payload = {
                'election_id': str(election_id),
                'election_title': election.title,
                'old_status': old_status,
                'new_status': new_status,
                'timestamp': timezone.now().isoformat()
            }
            
            # Notify election-specific group
            async_to_sync(self.channel_layer.group_send)(
                f'election_{election_id}',
                {
                    'type': 'election_status_change',
                    'data': payload
                }
            )
            
            # Notify dashboard
            async_to_sync(self.channel_layer.group_send)(
                'dashboard_updates',
                {
                    'type': 'dashboard_update',
                    'data': {
                        'event': 'election_status_change',
                        'election_id': str(election_id),
                        'election_title': election.title,
                        'new_status': new_status
                    }
                }
            )
            
            # Notify voters if election started or ended
            if new_status == 'ongoing':
                self.notification_service.notify_election_voters(
                    election_id,
                    'Election Started',
                    f'The election "{election.title}" is now open for voting!'
                )
            elif new_status == 'completed':
                self.notification_service.notify_election_voters(
                    election_id,
                    'Election Ended',
                    f'The election "{election.title}" has ended. Results will be published soon.'
                )
        
        except Election.DoesNotExist:
            pass
    
    def notify_results_published(self, election_id: str):
        """
        Notify when election results are published
        
        Args:
            election_id: Election UUID
        """
        from elections.models import Election
        
        try:
            election = Election.objects.get(id=election_id)
            
            # Notify voters
            self.notification_service.notify_election_voters(
                election_id,
                'Results Published',
                f'Results for "{election.title}" are now available!'
            )
            
            # Broadcast to dashboard
            async_to_sync(self.channel_layer.group_send)(
                'dashboard_updates',
                {
                    'type': 'dashboard_update',
                    'data': {
                        'event': 'results_published',
                        'election_id': str(election_id),
                        'election_title': election.title
                    }
                }
            )
        
        except Election.DoesNotExist:
            pass
    
    def send_dashboard_alert(
        self,
        title: str,
        message: str,
        severity: str = 'info'
    ):
        """
        Send alert to dashboard
        
        Args:
            title: Alert title
            message: Alert message
            severity: Severity level
        """
        payload = {
            'title': title,
            'message': message,
            'severity': severity,
            'timestamp': timezone.now().isoformat()
        }
        
        async_to_sync(self.channel_layer.group_send)(
            'dashboard_updates',
            {
                'type': 'alert',
                'data': payload
            }
        )


class DashboardUpdater:
    """
    Service for updating admin dashboard in real-time
    """
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
    
    def send_stats_update(self, stats: Dict):
        """
        Send statistics update to dashboard
        
        Args:
            stats: Statistics dictionary
        """
        async_to_sync(self.channel_layer.group_send)(
            'dashboard_updates',
            {
                'type': 'dashboard_update',
                'data': {
                    'event': 'stats_update',
                    'stats': stats,
                    'timestamp': timezone.now().isoformat()
                }
            }
        )
    
    def notify_new_vote(self, election_id: str, election_title: str):
        """
        Notify dashboard of new vote
        
        Args:
            election_id: Election UUID
            election_title: Election title
        """
        async_to_sync(self.channel_layer.group_send)(
            'dashboard_updates',
            {
                'type': 'dashboard_update',
                'data': {
                    'event': 'new_vote',
                    'election_id': str(election_id),
                    'election_title': election_title,
                    'timestamp': timezone.now().isoformat()
                }
            }
        )
    
    def notify_new_voter_registration(self, count: int = 1):
        """
        Notify dashboard of new voter registration
        
        Args:
            count: Number of new registrations
        """
        async_to_sync(self.channel_layer.group_send)(
            'dashboard_updates',
            {
                'type': 'dashboard_update',
                'data': {
                    'event': 'new_voter_registration',
                    'count': count,
                    'timestamp': timezone.now().isoformat()
                }
            }
        )


# Singleton instances
notification_service = NotificationService()
election_notifier = ElectionEventNotifier()
dashboard_updater = DashboardUpdater()


__all__ = [
    'NotificationService',
    'ElectionEventNotifier',
    'DashboardUpdater',
    'notification_service',
    'election_notifier',
    'dashboard_updater'
]
