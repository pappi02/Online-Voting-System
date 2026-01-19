"""
Phase 6: Real-Time Features & WebSocket Tests
Tests for WebSocket consumers, notifications, and real-time updates
"""

import pytest
import json
from channels.testing import WebsocketCommunicator
from channels.routing import URLRouter
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status

from elections.models import Election, Position, Candidate, ElectionVoter
from accounts.models import VoterProfile
from voting.models import Vote
from voting.consumers import (
    ElectionConsumer, DashboardConsumer,
    NotificationConsumer, BroadcastConsumer
)
from voting.realtime import (
    NotificationService, ElectionEventNotifier,
    DashboardUpdater
)

User = get_user_model()


@pytest.mark.django_db
class TestElectionConsumer(TestCase):
    """Test ElectionConsumer WebSocket"""
    
    def setUp(self):
        """Set up test data"""
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            status='approved',
            role='admin'
        )
        
        self.election = Election.objects.create(
            title='Test Election',
            description='Test Description',
            election_type='general',
            status='ongoing',
            scheduled_start=timezone.now() - timedelta(hours=1),
            scheduled_end=timezone.now() + timedelta(hours=2),
            created_by=self.admin,
            modified_by=self.admin
        )
    
    async def test_consumer_connection(self):
        """Test WebSocket connection to election"""
        from channels.testing import WebsocketCommunicator
        from voting.routing import websocket_urlpatterns
        from channels.routing import URLRouter
        
        application = URLRouter(websocket_urlpatterns)
        
        communicator = WebsocketCommunicator(
            application,
            f"/ws/election/{self.election.id}/"
        )
        
        connected, subprotocol = await communicator.connect()
        assert connected
        
        # Should receive initial stats
        response = await communicator.receive_json_from()
        assert response['type'] == 'initial_stats'
        assert 'data' in response
        
        await communicator.disconnect()


@pytest.mark.django_db
class TestNotificationService(TestCase):
    """Test NotificationService functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='user@test.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            status='approved',
            role='voter'
        )
        
        self.service = NotificationService()
    
    def test_send_user_notification(self):
        """Test sending notification to user"""
        # Should not raise exception
        self.service.send_user_notification(
            user_id=str(self.user.id),
            title='Test Notification',
            message='This is a test',
            notification_type='info'
        )
    
    def test_send_alert(self):
        """Test sending alert to user"""
        self.service.send_alert(
            user_id=str(self.user.id),
            title='Test Alert',
            message='This is an alert',
            severity='high',
            action_url='/action'
        )
    
    def test_broadcast_system_message(self):
        """Test broadcasting system message"""
        self.service.broadcast_system_message(
            title='System Message',
            message='This is a broadcast',
            broadcast_type='announcement',
            priority='normal'
        )


@pytest.mark.django_db
class TestElectionEventNotifier(TestCase):
    """Test ElectionEventNotifier functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            status='approved',
            role='admin'
        )
        
        self.voter = User.objects.create_user(
            email='voter@test.com',
            password='testpass123',
            first_name='Voter',
            last_name='Test',
            status='approved',
            role='voter'
        )
        
        VoterProfile.objects.create(
            user=self.voter,
            date_of_birth=timezone.now().date() - timedelta(days=365*25)
        )
        
        self.election = Election.objects.create(
            title='Test Election',
            description='Test Description',
            election_type='general',
            status='ongoing',
            scheduled_start=timezone.now() - timedelta(hours=1),
            scheduled_end=timezone.now() + timedelta(hours=2),
            created_by=self.admin,
            modified_by=self.admin
        )
        
        ElectionVoter.objects.create(
            election=self.election,
            voter=self.voter,
            status='eligible'
        )
        
        self.notifier = ElectionEventNotifier()
    
    def test_notify_vote_cast(self):
        """Test notification when vote is cast"""
        # Should not raise exception
        self.notifier.notify_vote_cast(str(self.election.id))
    
    def test_notify_election_status_change(self):
        """Test notification on status change"""
        self.notifier.notify_election_status_change(
            str(self.election.id),
            'scheduled',
            'ongoing'
        )
    
    def test_notify_results_published(self):
        """Test notification when results published"""
        self.notifier.notify_results_published(str(self.election.id))
    
    def test_send_dashboard_alert(self):
        """Test sending dashboard alert"""
        self.notifier.send_dashboard_alert(
            'Test Alert',
            'This is a test alert',
            'warning'
        )


@pytest.mark.django_db
class TestDashboardUpdater(TestCase):
    """Test DashboardUpdater functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.updater = DashboardUpdater()
    
    def test_send_stats_update(self):
        """Test sending stats update"""
        stats = {
            'active_elections': 5,
            'votes_today': 100,
            'total_voters': 500
        }
        
        self.updater.send_stats_update(stats)
    
    def test_notify_new_vote(self):
        """Test notification for new vote"""
        self.updater.notify_new_vote(
            'election-uuid',
            'Test Election'
        )
    
    def test_notify_new_voter_registration(self):
        """Test notification for new voter registration"""
        self.updater.notify_new_voter_registration(count=3)


@pytest.mark.django_db
class TestRealTimeAPI(TestCase):
    """Test Real-Time API endpoints"""
    
    def setUp(self):
        """Set up test environment"""
        self.client = APIClient()
        
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            status='approved',
            role='admin'
        )
        self.admin.is_staff = True
        self.admin.save()
        
        self.voter = User.objects.create_user(
            email='voter@test.com',
            password='testpass123',
            first_name='Voter',
            last_name='Test',
            status='approved',
            role='voter'
        )
        
        VoterProfile.objects.create(
            user=self.voter,
            date_of_birth=timezone.now().date() - timedelta(days=365*25)
        )
        
        self.election = Election.objects.create(
            title='Test Election',
            description='Test Description',
            election_type='general',
            status='scheduled',
            scheduled_start=timezone.now() + timedelta(hours=1),
            scheduled_end=timezone.now() + timedelta(hours=4),
            created_by=self.admin,
            modified_by=self.admin
        )
    
    def test_broadcast_endpoint(self):
        """Test system broadcast endpoint"""
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.post(
            '/api/voting/realtime/broadcast/',
            {
                'title': 'System Maintenance',
                'message': 'System will be down at 10 PM',
                'broadcast_type': 'maintenance',
                'priority': 'high'
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
    
    def test_notify_user_endpoint(self):
        """Test user notification endpoint"""
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.post(
            '/api/voting/realtime/notify_user/',
            {
                'user_id': str(self.voter.id),
                'title': 'Test Notification',
                'message': 'This is a test',
                'notification_type': 'info'
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
    
    def test_notify_election_endpoint(self):
        """Test election notification endpoint"""
        self.client.force_authenticate(user=self.admin)
        
        ElectionVoter.objects.create(
            election=self.election,
            voter=self.voter,
            status='eligible'
        )
        
        response = self.client.post(
            '/api/voting/realtime/notify_election/',
            {
                'election_id': str(self.election.id),
                'title': 'Election Update',
                'message': 'Voting time extended'
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
    
    def test_update_election_status_endpoint(self):
        """Test election status update endpoint"""
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.post(
            f'/api/voting/realtime/{self.election.id}/update_election_status/',
            {'status': 'ongoing'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['new_status'], 'ongoing')
        
        # Verify election status changed
        self.election.refresh_from_db()
        self.assertEqual(self.election.status, 'ongoing')
    
    def test_publish_results_endpoint(self):
        """Test publish results endpoint"""
        self.client.force_authenticate(user=self.admin)
        
        self.election.status = 'completed'
        self.election.save()
        
        response = self.client.post(
            f'/api/voting/realtime/{self.election.id}/publish_results/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify election status changed
        self.election.refresh_from_db()
        self.assertEqual(self.election.status, 'results_published')
    
    def test_dashboard_stats_endpoint(self):
        """Test dashboard stats endpoint"""
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.get('/api/voting/realtime/dashboard_stats/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('active_elections', response.data)
        self.assertIn('votes_today', response.data)
        self.assertIn('total_voters', response.data)
    
    def test_unauthorized_access(self):
        """Test that non-admin cannot access endpoints"""
        self.client.force_authenticate(user=self.voter)
        
        response = self.client.post(
            '/api/voting/realtime/broadcast/',
            {
                'title': 'Test',
                'message': 'Test',
                'broadcast_type': 'announcement',
                'priority': 'normal'
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
class TestRealTimeIntegration(TestCase):
    """Test integration of real-time features with voting"""
    
    def setUp(self):
        """Set up test environment"""
        self.client = APIClient()
        
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            status='approved',
            role='admin'
        )
        
        self.voter = User.objects.create_user(
            email='voter@test.com',
            password='testpass123',
            first_name='Voter',
            last_name='Test',
            status='approved',
            role='voter'
        )
        
        VoterProfile.objects.create(
            user=self.voter,
            date_of_birth=timezone.now().date() - timedelta(days=365*25)
        )
        
        self.election = Election.objects.create(
            title='Test Election',
            description='Test Description',
            election_type='general',
            status='ongoing',
            scheduled_start=timezone.now() - timedelta(hours=1),
            scheduled_end=timezone.now() + timedelta(hours=2),
            created_by=self.admin,
            modified_by=self.admin
        )
        
        self.position = Position.objects.create(
            election=self.election,
            title='President',
            description='President position',
            seats_available=1,
            candidates_per_voter=1,
            display_order=1
        )
        
        self.candidate = Candidate.objects.create(
            position=self.position,
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            status='approved',
            display_order=1
        )
        
        ElectionVoter.objects.create(
            election=self.election,
            voter=self.voter,
            status='eligible'
        )
    
    def test_vote_triggers_notification(self):
        """Test that casting a vote triggers real-time notification"""
        self.client.force_authenticate(user=self.voter)
        
        vote_data = {
            'election_id': str(self.election.id),
            'votes': [
                {
                    'position_id': str(self.position.id),
                    'candidate_ids': [str(self.candidate.id)]
                }
            ]
        }
        
        response = self.client.post(
            '/api/voting/votes/cast_vote/',
            vote_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Vote should have been cast
        self.assertEqual(Vote.objects.count(), 1)
        
        # Real-time notification should have been triggered
        # (we can't easily test the actual WebSocket notification in unit tests)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
