"""
Comprehensive tests for Session Management system
"""

import pytest
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.utils import timezone
from datetime import timedelta
from unittest.mock import Mock, patch
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from auditing.session_management import SessionManager
from auditing.audit_models import AuditLog

User = get_user_model()


class SessionManagerTest(TestCase):
    """Test SessionManager class"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.manager = SessionManager()
        self.factory = RequestFactory()
    
    def test_create_session(self):
        """Test creating a new session"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Agent'
        
        session_key = self.manager.create_session(
            user=self.user,
            request=request
        )
        
        self.assertIsNotNone(session_key)
        self.assertTrue(self.manager.is_valid_session(session_key, self.user))
    
    def test_create_session_with_metadata(self):
        """Test session metadata is stored"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        
        session_key = self.manager.create_session(
            user=self.user,
            request=request,
            remember_me=True
        )
        
        metadata = self.manager.get_session_metadata(session_key)
        
        self.assertEqual(metadata['user_id'], self.user.id)
        self.assertEqual(metadata['ip_address'], '192.168.1.1')
        self.assertEqual(metadata['user_agent'], 'Mozilla/5.0')
        self.assertTrue(metadata['remember_me'])
    
    def test_validate_session_valid(self):
        """Test validating a valid session"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        session_key = self.manager.create_session(
            user=self.user,
            request=request
        )
        
        is_valid = self.manager.is_valid_session(session_key, self.user)
        
        self.assertTrue(is_valid)
    
    def test_validate_session_invalid_key(self):
        """Test validating with invalid session key"""
        is_valid = self.manager.is_valid_session('invalid_key', self.user)
        
        self.assertFalse(is_valid)
    
    def test_validate_session_wrong_user(self):
        """Test session validation fails for wrong user"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        session_key = self.manager.create_session(
            user=self.user,
            request=request
        )
        
        other_user = User.objects.create_user(
            email='other@example.com',
            password='pass123'
        )
        
        is_valid = self.manager.is_valid_session(session_key, other_user)
        
        self.assertFalse(is_valid)
    
    def test_validate_session_expired(self):
        """Test expired session is invalid"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        session_key = self.manager.create_session(
            user=self.user,
            request=request
        )
        
        # Manually expire the session
        session = Session.objects.get(session_key=session_key)
        session.expire_date = timezone.now() - timedelta(hours=1)
        session.save()
        
        is_valid = self.manager.is_valid_session(session_key, self.user)
        
        self.assertFalse(is_valid)
    
    def test_invalidate_session(self):
        """Test invalidating a session"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        session_key = self.manager.create_session(
            user=self.user,
            request=request
        )
        
        # Invalidate the session
        self.manager.invalidate_session(session_key)
        
        # Session should no longer be valid
        is_valid = self.manager.is_valid_session(session_key, self.user)
        self.assertFalse(is_valid)
    
    def test_invalidate_all_user_sessions(self):
        """Test invalidating all sessions for a user"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Create multiple sessions
        session1 = self.manager.create_session(user=self.user, request=request)
        session2 = self.manager.create_session(user=self.user, request=request)
        session3 = self.manager.create_session(user=self.user, request=request)
        
        # Invalidate all sessions
        count = self.manager.invalidate_all_user_sessions(self.user)
        
        self.assertEqual(count, 3)
        
        # All sessions should be invalid
        self.assertFalse(self.manager.is_valid_session(session1, self.user))
        self.assertFalse(self.manager.is_valid_session(session2, self.user))
        self.assertFalse(self.manager.is_valid_session(session3, self.user))
    
    def test_get_user_sessions(self):
        """Test getting all sessions for a user"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Create sessions
        session1 = self.manager.create_session(user=self.user, request=request)
        session2 = self.manager.create_session(user=self.user, request=request)
        
        sessions = self.manager.get_user_sessions(self.user)
        
        self.assertEqual(len(sessions), 2)
    
    def test_session_remember_me_duration(self):
        """Test session duration with remember_me"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Create session with remember_me=True
        session_key = self.manager.create_session(
            user=self.user,
            request=request,
            remember_me=True
        )
        
        session = Session.objects.get(session_key=session_key)
        
        # Session should expire in 30 days (remember_me duration)
        time_until_expiry = session.expire_date - timezone.now()
        
        self.assertGreater(time_until_expiry.days, 25)  # Should be close to 30 days
    
    def test_session_default_duration(self):
        """Test default session duration"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Create session without remember_me
        session_key = self.manager.create_session(
            user=self.user,
            request=request,
            remember_me=False
        )
        
        session = Session.objects.get(session_key=session_key)
        
        # Session should expire in ~24 hours (default)
        time_until_expiry = session.expire_date - timezone.now()
        
        self.assertLess(time_until_expiry.days, 2)  # Less than 2 days
        self.assertGreater(time_until_expiry.hours, 20)  # More than 20 hours
    
    def test_check_concurrent_sessions_allowed(self):
        """Test concurrent sessions under limit"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Create 2 sessions (under limit of 5)
        self.manager.create_session(user=self.user, request=request)
        self.manager.create_session(user=self.user, request=request)
        
        can_create, count = self.manager.check_concurrent_sessions(
            user=self.user,
            max_sessions=5
        )
        
        self.assertTrue(can_create)
        self.assertEqual(count, 2)
    
    def test_check_concurrent_sessions_limit_reached(self):
        """Test concurrent sessions limit enforcement"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Create 5 sessions (at limit)
        for i in range(5):
            self.manager.create_session(user=self.user, request=request)
        
        can_create, count = self.manager.check_concurrent_sessions(
            user=self.user,
            max_sessions=5
        )
        
        self.assertFalse(can_create)
        self.assertEqual(count, 5)
    
    def test_revoke_oldest_sessions(self):
        """Test revoking oldest sessions when limit exceeded"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Create sessions with delays to ensure different timestamps
        sessions = []
        for i in range(5):
            session_key = self.manager.create_session(user=self.user, request=request)
            sessions.append(session_key)
            import time
            time.sleep(0.01)  # Small delay
        
        # Revoke 2 oldest sessions
        revoked_count = self.manager.revoke_oldest_sessions(
            user=self.user,
            keep_count=3
        )
        
        self.assertEqual(revoked_count, 2)
        
        # Verify oldest 2 sessions are invalid
        self.assertFalse(self.manager.is_valid_session(sessions[0], self.user))
        self.assertFalse(self.manager.is_valid_session(sessions[1], self.user))
        
        # Verify newest 3 sessions are still valid
        self.assertTrue(self.manager.is_valid_session(sessions[2], self.user))
        self.assertTrue(self.manager.is_valid_session(sessions[3], self.user))
        self.assertTrue(self.manager.is_valid_session(sessions[4], self.user))
    
    def test_session_activity_tracking(self):
        """Test tracking session activity"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        session_key = self.manager.create_session(user=self.user, request=request)
        
        # Get initial metadata
        initial_metadata = self.manager.get_session_metadata(session_key)
        initial_last_activity = initial_metadata['last_activity']
        
        # Update activity
        import time
        time.sleep(0.1)
        
        self.manager.update_session_activity(session_key)
        
        # Get updated metadata
        updated_metadata = self.manager.get_session_metadata(session_key)
        updated_last_activity = updated_metadata['last_activity']
        
        self.assertGreater(updated_last_activity, initial_last_activity)
    
    def test_session_ip_validation(self):
        """Test session IP address validation"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        session_key = self.manager.create_session(user=self.user, request=request)
        
        # Validate with correct IP
        is_valid = self.manager.validate_session_ip(
            session_key=session_key,
            ip_address='192.168.1.1'
        )
        self.assertTrue(is_valid)
        
        # Validate with wrong IP
        is_valid = self.manager.validate_session_ip(
            session_key=session_key,
            ip_address='1.2.3.4'
        )
        self.assertFalse(is_valid)
    
    def test_session_user_agent_validation(self):
        """Test session user agent validation"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        
        session_key = self.manager.create_session(user=self.user, request=request)
        
        # Validate with correct user agent
        is_valid = self.manager.validate_session_user_agent(
            session_key=session_key,
            user_agent='Mozilla/5.0'
        )
        self.assertTrue(is_valid)
        
        # Validate with wrong user agent
        is_valid = self.manager.validate_session_user_agent(
            session_key=session_key,
            user_agent='AttackBot/1.0'
        )
        self.assertFalse(is_valid)
    
    def test_cleanup_expired_sessions(self):
        """Test cleanup of expired sessions"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Create sessions
        session1 = self.manager.create_session(user=self.user, request=request)
        session2 = self.manager.create_session(user=self.user, request=request)
        
        # Manually expire one session
        session = Session.objects.get(session_key=session1)
        session.expire_date = timezone.now() - timedelta(hours=1)
        session.save()
        
        # Cleanup expired sessions
        deleted_count = self.manager.cleanup_expired_sessions()
        
        self.assertEqual(deleted_count, 1)
        
        # Verify expired session is gone
        self.assertFalse(Session.objects.filter(session_key=session1).exists())
        
        # Verify active session remains
        self.assertTrue(Session.objects.filter(session_key=session2).exists())
    
    def test_get_session_info(self):
        """Test getting comprehensive session info"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Agent'
        
        session_key = self.manager.create_session(user=self.user, request=request)
        
        info = self.manager.get_session_info(session_key)
        
        self.assertIsNotNone(info)
        self.assertEqual(info['user_id'], self.user.id)
        self.assertEqual(info['ip_address'], '192.168.1.1')
        self.assertEqual(info['user_agent'], 'Test Agent')
        self.assertIn('created_at', info)
        self.assertIn('last_activity', info)
        self.assertIn('expires_at', info)


class SessionManagementAPITest(APITestCase):
    """Test Session Management API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.manager = SessionManager()
    
    def test_list_active_sessions(self):
        """Test listing user's active sessions"""
        self.client.force_authenticate(user=self.user)
        
        # Create sessions
        factory = RequestFactory()
        request = factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        self.manager.create_session(user=self.user, request=request)
        self.manager.create_session(user=self.user, request=request)
        
        response = self.client.get('/api/auditing/sessions/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)
    
    def test_revoke_session(self):
        """Test revoking a specific session"""
        factory = RequestFactory()
        request = factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        session_key = self.manager.create_session(user=self.user, request=request)
        
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f'/api/auditing/sessions/{session_key}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify session is invalid
        self.assertFalse(self.manager.is_valid_session(session_key, self.user))
    
    def test_revoke_all_sessions(self):
        """Test revoking all user sessions"""
        factory = RequestFactory()
        request = factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Create sessions
        session1 = self.manager.create_session(user=self.user, request=request)
        session2 = self.manager.create_session(user=self.user, request=request)
        
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/auditing/sessions/revoke_all/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify all sessions are invalid
        self.assertFalse(self.manager.is_valid_session(session1, self.user))
        self.assertFalse(self.manager.is_valid_session(session2, self.user))
    
    def test_get_current_session(self):
        """Test getting current session info"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/api/auditing/sessions/current/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('session_key', response.data)
    
    def test_cannot_revoke_other_user_session(self):
        """Test user cannot revoke another user's session"""
        factory = RequestFactory()
        request = factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        other_user = User.objects.create_user(
            email='other@example.com',
            password='pass123'
        )
        
        other_session = self.manager.create_session(user=other_user, request=request)
        
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f'/api/auditing/sessions/{other_session}/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SessionSecurityTest(TestCase):
    """Test session security features"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.manager = SessionManager()
        self.factory = RequestFactory()
    
    def test_session_hijacking_detection_ip(self):
        """Test detection of session hijacking via IP change"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        session_key = self.manager.create_session(user=self.user, request=request)
        
        # Try to use session from different IP
        is_valid = self.manager.validate_session_ip(
            session_key=session_key,
            ip_address='1.2.3.4'
        )
        
        self.assertFalse(is_valid)
    
    def test_session_hijacking_detection_user_agent(self):
        """Test detection of session hijacking via user agent change"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        
        session_key = self.manager.create_session(user=self.user, request=request)
        
        # Try to use session with different user agent
        is_valid = self.manager.validate_session_user_agent(
            session_key=session_key,
            user_agent='AttackBot/1.0'
        )
        
        self.assertFalse(is_valid)
    
    def test_session_fixation_prevention(self):
        """Test session fixation prevention (new session key on login)"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Create first session
        session1 = self.manager.create_session(user=self.user, request=request)
        
        # Create second session (should be different)
        session2 = self.manager.create_session(user=self.user, request=request)
        
        self.assertNotEqual(session1, session2)
    
    def test_audit_logging_on_session_events(self):
        """Test audit logs are created for session events"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        initial_log_count = AuditLog.objects.count()
        
        # Create session
        session_key = self.manager.create_session(user=self.user, request=request)
        
        # Invalidate session
        self.manager.invalidate_session(session_key)
        
        # Verify logs were created
        final_log_count = AuditLog.objects.count()
        self.assertGreater(final_log_count, initial_log_count)


# Run tests with: python manage.py test auditing.test_sessions
