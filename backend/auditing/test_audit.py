"""
Comprehensive tests for Audit Logging system
"""

import pytest
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import timedelta
from django.utils import timezone

from auditing.audit_models import AuditLog, SecurityEvent, LoginAttempt

User = get_user_model()


class AuditLogModelTest(TestCase):
    """Test AuditLog model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.factory = RequestFactory()
    
    def test_create_audit_log(self):
        """Test creating audit log entry"""
        log = AuditLog.objects.create(
            user=self.user,
            action=AuditLog.ACTION_LOGIN,
            severity=AuditLog.SEVERITY_INFO,
            ip_address='192.168.1.1',
            success=True
        )
        
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, AuditLog.ACTION_LOGIN)
        self.assertEqual(log.severity, AuditLog.SEVERITY_INFO)
        self.assertTrue(log.success)
    
    def test_log_action_helper(self):
        """Test log_action class method"""
        request = self.factory.post('/api/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Agent'
        
        log = AuditLog.log_action(
            action=AuditLog.ACTION_LOGIN,
            user=self.user,
            request=request,
            details={'method': '2fa'}
        )
        
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, AuditLog.ACTION_LOGIN)
        self.assertEqual(log.ip_address, '192.168.1.1')
        self.assertEqual(log.user_agent, 'Test Agent')
        self.assertEqual(log.request_method, 'POST')
        self.assertEqual(log.request_path, '/api/test/')
        self.assertEqual(log.details['method'], '2fa')
    
    def test_log_action_with_x_forwarded_for(self):
        """Test IP extraction from X-Forwarded-For header"""
        request = self.factory.post('/api/test/')
        request.META['HTTP_X_FORWARDED_FOR'] = '1.2.3.4, 5.6.7.8'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        log = AuditLog.log_action(
            action=AuditLog.ACTION_LOGIN,
            user=self.user,
            request=request
        )
        
        # Should use first IP from X-Forwarded-For
        self.assertEqual(log.ip_address, '1.2.3.4')
    
    def test_audit_log_severity_levels(self):
        """Test different severity levels"""
        severities = [
            AuditLog.SEVERITY_INFO,
            AuditLog.SEVERITY_WARNING,
            AuditLog.SEVERITY_ERROR,
            AuditLog.SEVERITY_CRITICAL
        ]
        
        for severity in severities:
            log = AuditLog.objects.create(
                user=self.user,
                action=AuditLog.ACTION_LOGIN,
                severity=severity
            )
            self.assertEqual(log.severity, severity)
    
    def test_audit_log_all_actions(self):
        """Test all action types can be logged"""
        actions = [
            AuditLog.ACTION_LOGIN,
            AuditLog.ACTION_LOGOUT,
            AuditLog.ACTION_PASSWORD_CHANGE,
            AuditLog.ACTION_VOTE_CAST,
            AuditLog.ACTION_ELECTION_CREATED,
            AuditLog.ACTION_2FA_ENABLED,
            AuditLog.ACTION_SUSPICIOUS_ACTIVITY,
        ]
        
        for action in actions:
            log = AuditLog.objects.create(
                user=self.user,
                action=action
            )
            self.assertEqual(log.action, action)
    
    def test_audit_log_ordering(self):
        """Test logs are ordered by timestamp descending"""
        # Create logs with different timestamps
        for i in range(3):
            AuditLog.objects.create(
                user=self.user,
                action=AuditLog.ACTION_LOGIN,
                timestamp=timezone.now() - timedelta(hours=i)
            )
        
        logs = AuditLog.objects.all()
        
        # Should be ordered newest first
        self.assertGreater(logs[0].timestamp, logs[1].timestamp)
        self.assertGreater(logs[1].timestamp, logs[2].timestamp)


class SecurityEventModelTest(TestCase):
    """Test SecurityEvent model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_security_event(self):
        """Test creating security event"""
        event = SecurityEvent.objects.create(
            event_type=SecurityEvent.EVENT_BRUTE_FORCE,
            status=SecurityEvent.STATUS_OPEN,
            ip_address='1.2.3.4',
            description='5 failed login attempts',
            risk_score=75
        )
        
        self.assertEqual(event.event_type, SecurityEvent.EVENT_BRUTE_FORCE)
        self.assertEqual(event.status, SecurityEvent.STATUS_OPEN)
        self.assertEqual(event.risk_score, 75)
        self.assertFalse(event.auto_blocked)
    
    def test_create_event_helper(self):
        """Test create_event class method"""
        event = SecurityEvent.create_event(
            event_type=SecurityEvent.EVENT_UNUSUAL_LOCATION,
            ip_address='1.2.3.4',
            description='Login from new location',
            user=self.user,
            risk_score=40
        )
        
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.event_type, SecurityEvent.EVENT_UNUSUAL_LOCATION)
        self.assertEqual(event.risk_score, 40)
        self.assertEqual(event.status, SecurityEvent.STATUS_OPEN)
    
    def test_resolve_security_event(self):
        """Test resolving security event"""
        admin = User.objects.create_user(
            email='admin@example.com',
            password='adminpass',
            is_staff=True
        )
        
        event = SecurityEvent.objects.create(
            event_type=SecurityEvent.EVENT_SUSPICIOUS_PATTERN,
            ip_address='1.2.3.4',
            description='Suspicious activity detected',
            risk_score=60
        )
        
        event.resolve(resolved_by=admin, notes='False positive')
        
        self.assertEqual(event.status, SecurityEvent.STATUS_RESOLVED)
        self.assertEqual(event.resolved_by, admin)
        self.assertEqual(event.resolution_notes, 'False positive')
        self.assertIsNotNone(event.resolved_at)
    
    def test_security_event_all_types(self):
        """Test all event types"""
        event_types = [
            SecurityEvent.EVENT_BRUTE_FORCE,
            SecurityEvent.EVENT_MULTIPLE_FAILURES,
            SecurityEvent.EVENT_UNUSUAL_LOCATION,
            SecurityEvent.EVENT_UNUSUAL_TIME,
            SecurityEvent.EVENT_SUSPICIOUS_PATTERN,
            SecurityEvent.EVENT_ACCOUNT_LOCKOUT,
        ]
        
        for event_type in event_types:
            event = SecurityEvent.objects.create(
                event_type=event_type,
                ip_address='1.2.3.4',
                description=f'Test {event_type}',
                risk_score=50
            )
            self.assertEqual(event.event_type, event_type)
    
    def test_security_event_risk_scores(self):
        """Test risk score ranges"""
        # Low risk
        low_event = SecurityEvent.objects.create(
            event_type=SecurityEvent.EVENT_UNUSUAL_TIME,
            ip_address='1.2.3.4',
            description='Login at 3 AM',
            risk_score=20
        )
        self.assertLess(low_event.risk_score, 30)
        
        # High risk
        high_event = SecurityEvent.objects.create(
            event_type=SecurityEvent.EVENT_BRUTE_FORCE,
            ip_address='1.2.3.4',
            description='Multiple failed attempts',
            risk_score=80
        )
        self.assertGreater(high_event.risk_score, 70)


class LoginAttemptModelTest(TestCase):
    """Test LoginAttempt model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.factory = RequestFactory()
    
    def test_log_successful_attempt(self):
        """Test logging successful login attempt"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Agent'
        
        attempt = LoginAttempt.log_attempt(
            username='test@example.com',
            success=True,
            request=request,
            user=self.user
        )
        
        self.assertEqual(attempt.username, 'test@example.com')
        self.assertTrue(attempt.success)
        self.assertEqual(attempt.user, self.user)
        self.assertEqual(attempt.ip_address, '192.168.1.1')
    
    def test_log_failed_attempt(self):
        """Test logging failed login attempt"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        attempt = LoginAttempt.log_attempt(
            username='test@example.com',
            success=False,
            request=request,
            failure_reason='Invalid password'
        )
        
        self.assertFalse(attempt.success)
        self.assertEqual(attempt.failure_reason, 'Invalid password')
    
    def test_log_2fa_attempt(self):
        """Test logging login with 2FA"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        attempt = LoginAttempt.log_attempt(
            username='test@example.com',
            success=True,
            request=request,
            user=self.user,
            two_factor_required=True,
            two_factor_success=True
        )
        
        self.assertTrue(attempt.two_factor_required)
        self.assertTrue(attempt.two_factor_success)
    
    def test_get_failed_attempts_by_username(self):
        """Test getting failed attempts by username"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Create failed attempts
        for i in range(5):
            LoginAttempt.log_attempt(
                username='test@example.com',
                success=False,
                request=request
            )
        
        # Create successful attempt (should not count)
        LoginAttempt.log_attempt(
            username='test@example.com',
            success=True,
            request=request
        )
        
        count = LoginAttempt.get_failed_attempts(
            username='test@example.com',
            minutes=10
        )
        
        self.assertEqual(count, 5)
    
    def test_get_failed_attempts_by_ip(self):
        """Test getting failed attempts by IP"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '1.2.3.4'
        
        # Create failed attempts from same IP
        for i in range(3):
            LoginAttempt.log_attempt(
                username=f'user{i}@example.com',
                success=False,
                request=request
            )
        
        count = LoginAttempt.get_failed_attempts(
            ip_address='1.2.3.4',
            minutes=10
        )
        
        self.assertEqual(count, 3)
    
    def test_failed_attempts_time_window(self):
        """Test failed attempts time window"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Create old failed attempt (outside window)
        old_attempt = LoginAttempt.log_attempt(
            username='test@example.com',
            success=False,
            request=request
        )
        old_attempt.timestamp = timezone.now() - timedelta(minutes=15)
        old_attempt.save()
        
        # Create recent failed attempt (inside window)
        LoginAttempt.log_attempt(
            username='test@example.com',
            success=False,
            request=request
        )
        
        # Should only count recent attempt
        count = LoginAttempt.get_failed_attempts(
            username='test@example.com',
            minutes=10
        )
        
        self.assertEqual(count, 1)


class AuditLogAPITest(APITestCase):
    """Test Audit Log API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.admin = User.objects.create_user(
            email='admin@example.com',
            password='adminpass',
            is_staff=True
        )
    
    def test_list_audit_logs_user(self):
        """Test user can see their own logs"""
        # Create logs for user
        for i in range(3):
            AuditLog.objects.create(
                user=self.user,
                action=AuditLog.ACTION_LOGIN
            )
        
        # Create logs for another user
        other_user = User.objects.create_user(
            email='other@example.com',
            password='pass123'
        )
        AuditLog.objects.create(
            user=other_user,
            action=AuditLog.ACTION_LOGIN
        )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/auditing/logs/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
    
    def test_list_audit_logs_admin(self):
        """Test admin can see all logs"""
        # Create logs for different users
        for i in range(5):
            user = User.objects.create_user(
                email=f'user{i}@example.com',
                password='pass123'
            )
            AuditLog.objects.create(
                user=user,
                action=AuditLog.ACTION_LOGIN
            )
        
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/auditing/logs/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 5)
    
    def test_filter_logs_by_action(self):
        """Test filtering logs by action"""
        AuditLog.objects.create(
            user=self.user,
            action=AuditLog.ACTION_LOGIN
        )
        AuditLog.objects.create(
            user=self.user,
            action=AuditLog.ACTION_LOGOUT
        )
        AuditLog.objects.create(
            user=self.user,
            action=AuditLog.ACTION_LOGIN
        )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/auditing/logs/?action={AuditLog.ACTION_LOGIN}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_filter_logs_by_severity(self):
        """Test filtering logs by severity"""
        AuditLog.objects.create(
            user=self.user,
            action=AuditLog.ACTION_LOGIN,
            severity=AuditLog.SEVERITY_INFO
        )
        AuditLog.objects.create(
            user=self.user,
            action=AuditLog.ACTION_SUSPICIOUS_ACTIVITY,
            severity=AuditLog.SEVERITY_WARNING
        )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/auditing/logs/?severity={AuditLog.SEVERITY_WARNING}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['severity'], AuditLog.SEVERITY_WARNING)
    
    def test_filter_logs_by_date_range(self):
        """Test filtering logs by date range"""
        # Create old log
        old_log = AuditLog.objects.create(
            user=self.user,
            action=AuditLog.ACTION_LOGIN
        )
        old_log.timestamp = timezone.now() - timedelta(days=10)
        old_log.save()
        
        # Create recent log
        AuditLog.objects.create(
            user=self.user,
            action=AuditLog.ACTION_LOGIN
        )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/auditing/logs/?days=7')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_audit_log_summary(self):
        """Test getting audit log summary"""
        # Create logs with different actions
        AuditLog.objects.create(
            user=self.user,
            action=AuditLog.ACTION_LOGIN,
            severity=AuditLog.SEVERITY_INFO
        )
        AuditLog.objects.create(
            user=self.user,
            action=AuditLog.ACTION_LOGIN,
            severity=AuditLog.SEVERITY_INFO
        )
        AuditLog.objects.create(
            user=self.user,
            action=AuditLog.ACTION_LOGOUT,
            severity=AuditLog.SEVERITY_INFO
        )
        AuditLog.objects.create(
            user=self.user,
            action=AuditLog.ACTION_SUSPICIOUS_ACTIVITY,
            severity=AuditLog.SEVERITY_WARNING
        )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/auditing/logs/summary/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_events', response.data)
        self.assertIn('action_counts', response.data)
        self.assertIn('severity_counts', response.data)
        
        self.assertEqual(response.data['total_events'], 4)
        self.assertEqual(response.data['action_counts'][AuditLog.ACTION_LOGIN], 2)
        self.assertEqual(response.data['severity_counts']['warning'], 1)


class SecurityEventAPITest(APITestCase):
    """Test Security Event API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email='admin@example.com',
            password='adminpass',
            is_staff=True,
            is_superuser=True
        )
    
    def test_list_security_events(self):
        """Test listing security events (admin only)"""
        # Create events
        for i in range(3):
            SecurityEvent.objects.create(
                event_type=SecurityEvent.EVENT_BRUTE_FORCE,
                ip_address='1.2.3.4',
                description=f'Event {i}',
                risk_score=75
            )
        
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/auditing/security-events/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
    
    def test_list_security_events_non_admin(self):
        """Test non-admin cannot list security events"""
        user = User.objects.create_user(
            email='user@example.com',
            password='pass123'
        )
        
        self.client.force_authenticate(user=user)
        response = self.client.get('/api/auditing/security-events/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_filter_events_by_status(self):
        """Test filtering events by status"""
        SecurityEvent.objects.create(
            event_type=SecurityEvent.EVENT_BRUTE_FORCE,
            status=SecurityEvent.STATUS_OPEN,
            ip_address='1.2.3.4',
            description='Open event',
            risk_score=75
        )
        SecurityEvent.objects.create(
            event_type=SecurityEvent.EVENT_BRUTE_FORCE,
            status=SecurityEvent.STATUS_RESOLVED,
            ip_address='1.2.3.4',
            description='Resolved event',
            risk_score=75
        )
        
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(
            f'/api/auditing/security-events/?status={SecurityEvent.STATUS_OPEN}'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['status'], SecurityEvent.STATUS_OPEN)
    
    def test_resolve_security_event(self):
        """Test resolving security event"""
        event = SecurityEvent.objects.create(
            event_type=SecurityEvent.EVENT_SUSPICIOUS_PATTERN,
            ip_address='1.2.3.4',
            description='Suspicious activity',
            risk_score=60
        )
        
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f'/api/auditing/security-events/{event.id}/resolve/',
            {'notes': 'False positive - legitimate user'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify event is resolved
        event.refresh_from_db()
        self.assertEqual(event.status, SecurityEvent.STATUS_RESOLVED)
        self.assertEqual(event.resolved_by, self.admin)
        self.assertIsNotNone(event.resolved_at)
    
    def test_security_events_dashboard(self):
        """Test security events dashboard"""
        # Create events
        SecurityEvent.objects.create(
            event_type=SecurityEvent.EVENT_BRUTE_FORCE,
            status=SecurityEvent.STATUS_OPEN,
            ip_address='1.2.3.4',
            description='Brute force',
            risk_score=80
        )
        SecurityEvent.objects.create(
            event_type=SecurityEvent.EVENT_UNUSUAL_LOCATION,
            status=SecurityEvent.STATUS_OPEN,
            ip_address='1.2.3.4',
            description='Unusual location',
            risk_score=40
        )
        
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/auditing/security-events/dashboard/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('open_events', response.data)
        self.assertIn('high_risk_events', response.data)
        self.assertIn('event_type_counts', response.data)
        
        self.assertEqual(response.data['open_events'], 2)
        self.assertEqual(response.data['high_risk_events'], 1)  # risk_score >= 70


# Run tests with: python manage.py test auditing.test_audit
