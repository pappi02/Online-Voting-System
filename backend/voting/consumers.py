"""
WebSocket consumers for real-time voting updates
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone

from elections.models import Election
from .models import Vote
from .analytics import VoteAnalytics

User = get_user_model()


class ElectionConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time election updates
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.election_id = self.scope['url_route']['kwargs']['election_id']
        self.election_group_name = f'election_{self.election_id}'
        
        # Join election group
        await self.channel_layer.group_add(
            self.election_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial election stats
        stats = await self.get_election_stats()
        await self.send(text_data=json.dumps({
            'type': 'initial_stats',
            'data': stats
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        await self.channel_layer.group_discard(
            self.election_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'request_stats':
            # Client requesting updated stats
            stats = await self.get_election_stats()
            await self.send(text_data=json.dumps({
                'type': 'stats_update',
                'data': stats
            }))
    
    async def vote_cast(self, event):
        """Handle vote cast event"""
        await self.send(text_data=json.dumps({
            'type': 'vote_cast',
            'data': event['data']
        }))
    
    async def stats_update(self, event):
        """Handle stats update event"""
        await self.send(text_data=json.dumps({
            'type': 'stats_update',
            'data': event['data']
        }))
    
    async def election_status_change(self, event):
        """Handle election status change"""
        await self.send(text_data=json.dumps({
            'type': 'status_change',
            'data': event['data']
        }))
    
    @database_sync_to_async
    def get_election_stats(self):
        """Get current election statistics"""
        try:
            election = Election.objects.get(id=self.election_id)
            analytics = VoteAnalytics(election)
            
            return {
                'election_id': str(election.id),
                'title': election.title,
                'status': election.status,
                'total_votes': analytics.get_total_votes(),
                'eligible_voters': analytics.get_eligible_voters(),
                'turnout_percentage': analytics.get_turnout_percentage(),
                'last_updated': timezone.now().isoformat()
            }
        except Election.DoesNotExist:
            return {'error': 'Election not found'}


class DashboardConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for admin dashboard real-time updates
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        user = self.scope.get('user')
        
        # Only allow authenticated users
        if not user or not user.is_authenticated:
            await self.close()
            return
        
        # Only allow staff/admin
        if not (await self.is_staff(user)):
            await self.close()
            return
        
        self.dashboard_group = 'dashboard_updates'
        
        await self.channel_layer.group_add(
            self.dashboard_group,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial dashboard stats
        stats = await self.get_dashboard_stats()
        await self.send(text_data=json.dumps({
            'type': 'initial_stats',
            'data': stats
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        await self.channel_layer.group_discard(
            self.dashboard_group,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'request_stats':
            stats = await self.get_dashboard_stats()
            await self.send(text_data=json.dumps({
                'type': 'stats_update',
                'data': stats
            }))
    
    async def dashboard_update(self, event):
        """Handle dashboard update event"""
        await self.send(text_data=json.dumps({
            'type': 'update',
            'data': event['data']
        }))
    
    async def alert(self, event):
        """Handle alert event"""
        await self.send(text_data=json.dumps({
            'type': 'alert',
            'data': event['data']
        }))
    
    @database_sync_to_async
    def is_staff(self, user):
        """Check if user is staff"""
        return user.is_staff or user.is_admin()
    
    @database_sync_to_async
    def get_dashboard_stats(self):
        """Get dashboard statistics"""
        # Active elections
        active_count = Election.objects.filter(status='ongoing').count()
        
        # Today's votes
        today = timezone.now().date()
        votes_today = Vote.objects.filter(cast_at__date=today).count()
        
        # Upcoming elections
        upcoming_count = Election.objects.filter(
            status='scheduled',
            scheduled_start__gt=timezone.now()
        ).count()
        
        return {
            'active_elections': active_count,
            'votes_today': votes_today,
            'upcoming_elections': upcoming_count,
            'last_updated': timezone.now().isoformat()
        }


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for user notifications
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        user = self.scope.get('user')
        
        if not user or not user.is_authenticated:
            await self.close()
            return
        
        self.user_id = str(user.id)
        self.notification_group = f'user_{self.user_id}_notifications'
        
        await self.channel_layer.group_add(
            self.notification_group,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        await self.channel_layer.group_discard(
            self.notification_group,
            self.channel_name
        )
    
    async def notification(self, event):
        """Handle notification event"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': event['data']
        }))
    
    async def alert(self, event):
        """Handle alert event"""
        await self.send(text_data=json.dumps({
            'type': 'alert',
            'data': event['data']
        }))


class BroadcastConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for system-wide broadcasts
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        user = self.scope.get('user')
        
        if not user or not user.is_authenticated:
            await self.close()
            return
        
        self.broadcast_group = 'system_broadcasts'
        
        await self.channel_layer.group_add(
            self.broadcast_group,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        await self.channel_layer.group_discard(
            self.broadcast_group,
            self.channel_name
        )
    
    async def broadcast(self, event):
        """Handle broadcast event"""
        await self.send(text_data=json.dumps({
            'type': 'broadcast',
            'data': event['data']
        }))
    
    async def announcement(self, event):
        """Handle announcement event"""
        await self.send(text_data=json.dumps({
            'type': 'announcement',
            'data': event['data']
        }))


__all__ = [
    'ElectionConsumer',
    'DashboardConsumer',
    'NotificationConsumer',
    'BroadcastConsumer'
]
