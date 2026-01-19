"""
Comprehensive tests for Security Monitoring system
"""

import pytest
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from unittest.mock import Mock, patch

from auditing.security_monitor import SecurityMonitor
from auditing.audit_models import AuditLog, SecurityEvent, LoginAttempt

User = get_user_model()


class SecurityMonitorTest(TestCase):
    """Test SecurityMonitor class"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.monitor = SecurityMonitor()
        self.factory = RequestFactory()
    
    def test_check_brute_force_safe(self):
        """Test brute force check with safe activity"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Create 2 failed attempts (below threshold)
        for i in range(2):
            LoginAttempt.log_attempt(
                username='test@example.com',
                success=False,
                request=request
            )
        
        is_brute_force, data = self.monitor.check_brute_force(
            username='test@example.com',
            ip_address='192.168.1.1'
        )
        
        self.assertFalse(is_brute_force)
        self.assertIn('failed_attempts', data)
        self.assertEqual(data['failed_attempts'], 2)
    
    def test_check_brute_force_detected(self):
        """Test brute force detection"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Create 5 failed attempts (at threshold)
        for i in range(5):
            LoginAttempt.log_attempt(
                username='test@example.com',
                success=False,
                request=request
            )
        
        is_brute_force, data = self.monitor.check_brute_force(
            username='test@example.com',
            ip_address='192.168.1.1'
        )
        
        self.assertTrue(is_brute_force)
        self.assertEqual(data['failed_attempts'], 5)
        
        # Verify security event was created
        event = SecurityEvent.objects.filter(
            event_type=SecurityEvent.EVENT_BRUTE_FORCE
        ).first()
        
        self.assertIsNotNone(event)
        self.assertEqual(event.ip_address, '192.168.1.1')
        self.assertGreater(event.risk_score, 70)
    
    def test_check_brute_force_time_window(self):
        """Test brute force check respects time window"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Create old failed attempts (outside 15 min window)
        for i in range(3):
            attempt = LoginAttempt.log_attempt(
                username='test@example.com',
                success=False,
                request=request
            )
            attempt.timestamp = timezone.now() - timedelta(minutes=20)
            attempt.save()
        
        # Create recent failed attempts (inside window)
        for i in range(2):
            LoginAttempt.log_attempt(
                username='test@example.com',
                success=False,
                request=request
            )
        
        is_brute_force, data = self.monitor.check_brute_force(
            username='test@example.com',
            ip_address='192.168.1.1'
        )
        
        # Should only count recent attempts
        self.assertFalse(is_brute_force)
        self.assertEqual(data['failed_attempts'], 2)
    
    def test_calculate_risk_score_low(self):
        """Test low risk score calculation"""
        # No failed attempts, no security events
        risk_score = self.monitor.calculate_risk_score(
            user=self.user,
            ip_address='192.168.1.1'
        )
        
        self.assertLessEqual(risk_score, 20)
    
    def test_calculate_risk_score_medium(self):
        """Test medium risk score calculation"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Create 2 failed attempts
        for i in range(2):
            LoginAttempt.log_attempt(
                username='test@example.com',
                success=False,
                request=request
            )
        
        risk_score = self.monitor.calculate_risk_score(
            user=self.user,
            ip_address='192.168.1.1'
        )
        
        self.assertGreater(risk_score, 20)
        self.assertLess(risk_score, 70)
    
    def test_calculate_risk_score_high(self):
        """Test high risk score calculation"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Create many failed attempts
        for i in range(5):
            LoginAttempt.log_attempt(
                username='test@example.com',
                success=False,
                request=request
            )
        
        # Create security events
        SecurityEvent.objects.create(
            event_type=SecurityEvent.EVENT_BRUTE_FORCE,
            user=self.user,
            ip_address='192.168.1.1',
            description='Brute force detected',
            risk_score=80
        )
        
        risk_score = self.monitor.calculate_risk_score(
            user=self.user,
            ip_address='192.168.1.1'
        )
        
        self.assertGreaterEqual(risk_score, 70)
    
    def test_check_unusual_location_new_location(self):
        """Test unusual location detection for new location"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '1.2.3.4'
        
        # User has logged in from different IP before
        previous_request = self.factory.post('/api/auth/login/')
        previous_request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        LoginAttempt.log_attempt(
            username='test@example.com',
            success=True,
            request=previous_request,
            user=self.user
        )
        
        is_unusual, data = self.monitor.check_unusual_location(
            user=self.user,
            ip_address='1.2.3.4'
        )
        
        self.assertTrue(is_unusual)
        self.assertIn('previous_ips', data)
        self.assertIn('192.168.1.1', data['previous_ips'])
    
    def test_check_unusual_location_known_location(self):
        """Test no alert for known location"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # User has logged in from this IP before
        LoginAttempt.log_attempt(
            username='test@example.com',
            success=True,
            request=request,
            user=self.user
        )
        
        is_unusual, data = self.monitor.check_unusual_location(
            user=self.user,
            ip_address='192.168.1.1'
        )
        
        self.assertFalse(is_unusual)
    
    def test_check_unusual_time_normal_hours(self):
        """Test no alert for normal hours"""
        # Create login during normal hours (8 AM - 10 PM)
        with patch('django.utils.timezone.now') as mock_now:
            mock_time = timezone.now().replace(hour=14, minute=30)  # 2:30 PM
            mock_now.return_value = mock_time
            
            is_unusual, data = self.monitor.check_unusual_time(user=self.user)
        
        self.assertFalse(is_unusual)
    
    def test_check_unusual_time_late_night(self):
        """Test alert for unusual hours"""
        # Create login during unusual hours (3 AM)
        with patch('django.utils.timezone.now') as mock_now:
            mock_time = timezone.now().replace(hour=3, minute=0)
            mock_now.return_value = mock_time
            
            is_unusual, data = self.monitor.check_unusual_time(user=self.user)
        
        self.assertTrue(is_unusual)
        self.assertEqual(data['hour'], 3)
        self.assertIn('message', data)
    
    def test_detect_suspicious_pattern_rapid_requests(self):
        """Test detection of rapid requests pattern"""
        request = self.factory.post('/api/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Create many logs in short time
        for i in range(20):
            AuditLog.log_action(
                action=AuditLog.ACTION_LOGIN,
                user=self.user,
                request=request
            )
        
        is_suspicious, data = self.monitor.detect_suspicious_pattern(
            user=self.user,
            ip_address='192.168.1.1'
        )
        
        self.assertTrue(is_suspicious)
        self.assertIn('patterns', data)
    
    def test_detect_suspicious_pattern_multiple_failures(self):
        """Test detection of multiple failures pattern"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Create failed attempts
        for i in range(10):
            LoginAttempt.log_attempt(
                username='test@example.com',
                success=False,
                request=request
            )
        
        is_suspicious, data = self.monitor.detect_suspicious_pattern(
            user=self.user,
            ip_address='192.168.1.1'
        )
        
        self.assertTrue(is_suspicious)
        self.assertIn('patterns', data)
        self.assertIn('multiple_failed_logins', data['patterns'])
    
    def test_get_security_summary_clean(self):
        """Test security summary for clean account"""
        summary = self.monitor.get_security_summary(user=self.user)
        
        self.assertIn('risk_level', summary)
        self.assertIn('recent_events', summary)
        self.assertIn('failed_login_attempts', summary)
        self.assertIn('recommendations', summary)
        
        self.assertEqual(summary['risk_level'], 'low')
        self.assertEqual(summary['recent_events'], 0)
    
    def test_get_security_summary_with_activity(self):
        """Test security summary with security activity"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Create failed attempts
        for i in range(3):
            LoginAttempt.log_attempt(
                username='test@example.com',
                success=False,
                request=request
            )
        
        # Create security event
        SecurityEvent.objects.create(
            event_type=SecurityEvent.EVENT_MULTIPLE_FAILURES,
            user=self.user,
            ip_address='192.168.1.1',
            description='Multiple failures',
            risk_score=50
        )
        
        summary = self.monitor.get_security_summary(user=self.user)
        
        self.assertIn('risk_level', summary)
        self.assertGreater(summary['recent_events'], 0)
        self.assertGreater(summary['failed_login_attempts'], 0)
    
    def test_monitor_login_attempt_safe(self):
        """Test monitoring safe login attempt"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Test Agent'
        
        result = self.monitor.monitor_login_attempt(
            user=self.user,
            success=True,
            request=request
        )
        
        self.assertIn('risk_score', result)
        self.assertIn('checks', result)
        self.assertIn('should_block', result)
        self.assertFalse(result['should_block'])
    
    def test_monitor_login_attempt_suspicious(self):
        """Test monitoring suspicious login attempt"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '1.2.3.4'
        request.META['HTTP_USER_AGENT'] = 'Test Agent'
        
        # Create history of failed attempts
        for i in range(5):
            LoginAttempt.log_attempt(
                username='test@example.com',
                success=False,
                request=request
            )
        
        result = self.monitor.monitor_login_attempt(
            user=self.user,
            success=False,
            request=request
        )
        
        self.assertIn('risk_score', result)
        self.assertIn('checks', result)
        self.assertGreater(result['risk_score'], 50)
    
    def test_should_block_user_clean_account(self):
        """Test should_block_user for clean account"""
        should_block, reason = self.monitor.should_block_user(
            user=self.user,
            ip_address='192.168.1.1'
        )
        
        self.assertFalse(should_block)
        self.assertIsNone(reason)
    
    def test_should_block_user_high_risk(self):
        """Test should_block_user for high risk account"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Create many failed attempts
        for i in range(10):
            LoginAttempt.log_attempt(
                username='test@example.com',
                success=False,
                request=request
            )
        
        # Create high-risk security event
        SecurityEvent.objects.create(
            event_type=SecurityEvent.EVENT_BRUTE_FORCE,
            user=self.user,
            ip_address='192.168.1.1',
            description='Brute force attack',
            risk_score=90,
            auto_blocked=True
        )
        
        should_block, reason = self.monitor.should_block_user(
            user=self.user,
            ip_address='192.168.1.1'
        )
        
        self.assertTrue(should_block)
        self.assertIsNotNone(reason)
    
    def test_get_user_activity_summary(self):
        """Test getting user activity summary"""
        request = self.factory.post('/api/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Create various activities
        AuditLog.log_action(
            action=AuditLog.ACTION_LOGIN,
            user=self.user,
            request=request
        )
        AuditLog.log_action(
            action=AuditLog.ACTION_VOTE_CAST,
            user=self.user,
            request=request
        )
        
        summary = self.monitor.get_user_activity_summary(
            user=self.user,
            days=7
        )
        
        self.assertIn('total_actions', summary)
        self.assertIn('action_breakdown', summary)
        self.assertIn('unique_ips', summary)
        self.assertGreater(summary['total_actions'], 0)
    
    def test_cleanup_old_events(self):
        """Test cleanup of old security events"""
        # Create old resolved event (should be deleted)
        old_event = SecurityEvent.objects.create(
            event_type=SecurityEvent.EVENT_BRUTE_FORCE,
            status=SecurityEvent.STATUS_RESOLVED,
            ip_address='1.2.3.4',
            description='Old event',
            risk_score=75
        )
        old_event.timestamp = timezone.now() - timedelta(days=40)
        old_event.save()
        
        # Create recent event (should be kept)
        recent_event = SecurityEvent.objects.create(
            event_type=SecurityEvent.EVENT_BRUTE_FORCE,
            status=SecurityEvent.STATUS_OPEN,
            ip_address='1.2.3.4',
            description='Recent event',
            risk_score=75
        )
        
        # Run cleanup
        deleted_count = self.monitor.cleanup_old_events(days=30)
        
        self.assertEqual(deleted_count, 1)
        
        # Verify only recent event remains
        self.assertFalse(
            SecurityEvent.objects.filter(id=old_event.id).exists()
        )
        self.assertTrue(
            SecurityEvent.objects.filter(id=recent_event.id).exists()
        )


class SecurityMonitorIntegrationTest(TestCase):
    """Integration tests for SecurityMonitor"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.monitor = SecurityMonitor()
        self.factory = RequestFactory()
    
    def test_complete_attack_scenario(self):
        """Test complete brute force attack scenario"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '1.2.3.4'
        request.META['HTTP_USER_AGENT'] = 'AttackBot/1.0'
        
        # Simulate brute force attack
        for i in range(10):
            # Monitor each attempt
            result = self.monitor.monitor_login_attempt(
                user=self.user,
                success=False,
                request=request
            )
            
            # Log the attempt
            LoginAttempt.log_attempt(
                username='test@example.com',
                success=False,
                request=request
            )
        
        # Check if user should be blocked
        should_block, reason = self.monitor.should_block_user(
            user=self.user,
            ip_address='1.2.3.4'
        )
        
        self.assertTrue(should_block)
        
        # Verify security events were created
        events = SecurityEvent.objects.filter(
            event_type=SecurityEvent.EVENT_BRUTE_FORCE,
            ip_address='1.2.3.4'
        )
        
        self.assertGreater(events.count(), 0)
    
    def test_legitimate_user_not_blocked(self):
        """Test legitimate user is not blocked"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Simulate normal usage (successful logins)
        for i in range(5):
            result = self.monitor.monitor_login_attempt(
                user=self.user,
                success=True,
                request=request
            )
            
            LoginAttempt.log_attempt(
                username='test@example.com',
                success=True,
                request=request,
                user=self.user
            )
        
        should_block, reason = self.monitor.should_block_user(
            user=self.user,
            ip_address='192.168.1.1'
        )
        
        self.assertFalse(should_block)
        
        # Verify risk score is low
        risk_score = self.monitor.calculate_risk_score(
            user=self.user,
            ip_address='192.168.1.1'
        )
        
        self.assertLess(risk_score, 30)


# Run tests with: python manage.py test auditing.test_monitoring
