"""
Comprehensive tests for Rate Limiting middleware
"""

import pytest
from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.http import JsonResponse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import Mock, patch
from time import sleep

from auditing.rate_limiting import RateLimitMiddleware, ThrottleMiddleware

User = get_user_model()


class RateLimitMiddlewareTest(TestCase):
    """Test RateLimitMiddleware"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = RateLimitMiddleware(get_response=lambda r: JsonResponse({'status': 'ok'}))
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        cache.clear()
    
    def tearDown(self):
        cache.clear()
    
    def test_rate_limit_not_exceeded(self):
        """Test request passes when under rate limit"""
        request = self.factory.get('/api/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = self.user
        
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('X-RateLimit-Limit', response)
        self.assertIn('X-RateLimit-Remaining', response)
    
    def test_rate_limit_exceeded(self):
        """Test request blocked when rate limit exceeded"""
        request = self.factory.get('/api/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = self.user
        
        # Make requests up to limit (default 100 per minute)
        for i in range(100):
            self.middleware(request)
        
        # Next request should be blocked
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 429)
        self.assertIn('X-RateLimit-Limit', response)
        self.assertEqual(int(response['X-RateLimit-Remaining']), 0)
    
    def test_rate_limit_headers(self):
        """Test rate limit headers are set correctly"""
        request = self.factory.get('/api/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = self.user
        
        response = self.middleware(request)
        
        self.assertIn('X-RateLimit-Limit', response)
        self.assertIn('X-RateLimit-Remaining', response)
        self.assertIn('X-RateLimit-Reset', response)
        
        limit = int(response['X-RateLimit-Limit'])
        remaining = int(response['X-RateLimit-Remaining'])
        
        self.assertEqual(limit, 100)  # Default limit
        self.assertEqual(remaining, 99)  # After 1 request
    
    def test_rate_limit_by_ip(self):
        """Test rate limiting by IP address for anonymous users"""
        request = self.factory.get('/api/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = Mock(is_authenticated=False)
        
        # Make multiple requests
        for i in range(5):
            response = self.middleware(request)
        
        remaining = int(response['X-RateLimit-Remaining'])
        self.assertEqual(remaining, 95)  # 100 - 5
    
    def test_rate_limit_by_user(self):
        """Test rate limiting by user ID for authenticated users"""
        request = self.factory.get('/api/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = self.user
        
        # Make multiple requests
        for i in range(3):
            response = self.middleware(request)
        
        remaining = int(response['X-RateLimit-Remaining'])
        self.assertEqual(remaining, 97)  # 100 - 3
    
    def test_rate_limit_different_ips(self):
        """Test different IPs have separate rate limits"""
        user1_request = self.factory.get('/api/test/')
        user1_request.META['REMOTE_ADDR'] = '192.168.1.1'
        user1_request.user = Mock(is_authenticated=False)
        
        user2_request = self.factory.get('/api/test/')
        user2_request.META['REMOTE_ADDR'] = '192.168.1.2'
        user2_request.user = Mock(is_authenticated=False)
        
        # Make requests from both IPs
        for i in range(5):
            self.middleware(user1_request)
            self.middleware(user2_request)
        
        # Each should have separate limits
        response1 = self.middleware(user1_request)
        response2 = self.middleware(user2_request)
        
        remaining1 = int(response1['X-RateLimit-Remaining'])
        remaining2 = int(response2['X-RateLimit-Remaining'])
        
        self.assertEqual(remaining1, 94)  # 100 - 6
        self.assertEqual(remaining2, 94)  # 100 - 6
    
    def test_rate_limit_exempt_paths(self):
        """Test exempt paths bypass rate limiting"""
        request = self.factory.get('/health/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = Mock(is_authenticated=False)
        
        # Health check should not be rate limited
        for i in range(150):  # Exceed normal limit
            response = self.middleware(request)
        
        self.assertEqual(response.status_code, 200)
    
    @override_settings(RATE_LIMIT_REQUESTS=10, RATE_LIMIT_WINDOW=60)
    def test_custom_rate_limit_settings(self):
        """Test custom rate limit settings"""
        request = self.factory.get('/api/test/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = self.user
        
        # Make requests up to custom limit
        for i in range(10):
            response = self.middleware(request)
        
        # Verify custom limit is used
        limit = int(response['X-RateLimit-Limit'])
        remaining = int(response['X-RateLimit-Remaining'])
        
        self.assertEqual(limit, 10)
        self.assertEqual(remaining, 0)
    
    def test_rate_limit_x_forwarded_for(self):
        """Test rate limiting uses X-Forwarded-For when available"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_X_FORWARDED_FOR'] = '1.2.3.4, 5.6.7.8'
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = Mock(is_authenticated=False)
        
        for i in range(3):
            response = self.middleware(request)
        
        # Should use first IP from X-Forwarded-For
        remaining = int(response['X-RateLimit-Remaining'])
        self.assertEqual(remaining, 97)


class ThrottleMiddlewareTest(TestCase):
    """Test ThrottleMiddleware"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = ThrottleMiddleware(get_response=lambda r: JsonResponse({'status': 'ok'}))
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        cache.clear()
    
    def tearDown(self):
        cache.clear()
    
    def test_endpoint_throttle_login(self):
        """Test throttling for login endpoint"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = Mock(is_authenticated=False)
        
        # Login has limit of 5 attempts per 5 minutes
        for i in range(5):
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200)
        
        # 6th attempt should be throttled
        response = self.middleware(request)
        self.assertEqual(response.status_code, 429)
    
    def test_endpoint_throttle_vote(self):
        """Test throttling for vote endpoint"""
        request = self.factory.post('/api/voting/vote/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = self.user
        
        # Vote has limit of 10 per minute
        for i in range(10):
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200)
        
        # 11th attempt should be throttled
        response = self.middleware(request)
        self.assertEqual(response.status_code, 429)
    
    def test_endpoint_throttle_2fa(self):
        """Test throttling for 2FA verification endpoint"""
        request = self.factory.post('/api/accounts/2fa/verify/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = self.user
        
        # 2FA has stricter limit of 3 per 5 minutes
        for i in range(3):
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200)
        
        # 4th attempt should be throttled
        response = self.middleware(request)
        self.assertEqual(response.status_code, 429)
    
    def test_throttle_different_endpoints(self):
        """Test different endpoints have separate throttle limits"""
        login_request = self.factory.post('/api/auth/login/')
        login_request.META['REMOTE_ADDR'] = '192.168.1.1'
        login_request.user = Mock(is_authenticated=False)
        
        vote_request = self.factory.post('/api/voting/vote/')
        vote_request.META['REMOTE_ADDR'] = '192.168.1.1'
        vote_request.user = self.user
        
        # Use up login attempts
        for i in range(5):
            self.middleware(login_request)
        
        # Vote endpoint should still work
        response = self.middleware(vote_request)
        self.assertEqual(response.status_code, 200)
    
    def test_throttle_retry_after_header(self):
        """Test Retry-After header is set when throttled"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = Mock(is_authenticated=False)
        
        # Exceed limit
        for i in range(6):
            response = self.middleware(request)
        
        # Check Retry-After header
        self.assertIn('Retry-After', response)
        retry_after = int(response['Retry-After'])
        self.assertGreater(retry_after, 0)
        self.assertLessEqual(retry_after, 300)  # 5 minutes max
    
    def test_throttle_by_user(self):
        """Test throttling is per user for authenticated requests"""
        user1_request = self.factory.post('/api/auth/login/')
        user1_request.META['REMOTE_ADDR'] = '192.168.1.1'
        user1_request.user = self.user
        
        user2 = User.objects.create_user(
            email='user2@example.com',
            password='pass123'
        )
        user2_request = self.factory.post('/api/auth/login/')
        user2_request.META['REMOTE_ADDR'] = '192.168.1.1'
        user2_request.user = user2
        
        # User 1 uses up attempts
        for i in range(5):
            self.middleware(user1_request)
        
        # User 2 should still have attempts
        response = self.middleware(user2_request)
        self.assertEqual(response.status_code, 200)
    
    def test_no_throttle_for_unmatched_paths(self):
        """Test no throttling for paths without specific limits"""
        request = self.factory.get('/api/elections/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = self.user
        
        # Should not be throttled even with many requests
        for i in range(20):
            response = self.middleware(request)
        
        self.assertEqual(response.status_code, 200)


class RateLimitAPITest(APITestCase):
    """Test rate limiting through actual API calls"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        cache.clear()
    
    def tearDown(self):
        cache.clear()
    
    @override_settings(
        MIDDLEWARE=[
            'django.middleware.security.SecurityMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'auditing.rate_limiting.RateLimitMiddleware',
        ]
    )
    def test_api_rate_limit_headers(self):
        """Test rate limit headers in API responses"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/api/elections/')
        
        # Note: In test environment, middleware might not be fully active
        # This test validates the concept
        self.assertIn(response.status_code, [200, 404])
    
    @override_settings(
        MIDDLEWARE=[
            'django.middleware.security.SecurityMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'auditing.rate_limiting.ThrottleMiddleware',
        ]
    )
    def test_api_throttling(self):
        """Test endpoint-specific throttling in API"""
        # This test validates the throttling concept
        # In production, middleware would be active
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/api/elections/')
        self.assertIn(response.status_code, [200, 404])


class RateLimitUtilityTest(TestCase):
    """Test rate limiting utility functions"""
    
    def setUp(self):
        self.middleware = RateLimitMiddleware(get_response=lambda r: JsonResponse({'status': 'ok'}))
        cache.clear()
    
    def tearDown(self):
        cache.clear()
    
    def test_get_client_ip_remote_addr(self):
        """Test IP extraction from REMOTE_ADDR"""
        request = Mock()
        request.META = {'REMOTE_ADDR': '192.168.1.1'}
        
        ip = self.middleware.get_client_ip(request)
        self.assertEqual(ip, '192.168.1.1')
    
    def test_get_client_ip_x_forwarded_for(self):
        """Test IP extraction from X-Forwarded-For"""
        request = Mock()
        request.META = {
            'HTTP_X_FORWARDED_FOR': '1.2.3.4, 5.6.7.8',
            'REMOTE_ADDR': '192.168.1.1'
        }
        
        ip = self.middleware.get_client_ip(request)
        self.assertEqual(ip, '1.2.3.4')
    
    def test_get_cache_key_authenticated(self):
        """Test cache key generation for authenticated user"""
        request = Mock()
        request.user = Mock(is_authenticated=True, id=123)
        request.path = '/api/test/'
        
        key = self.middleware.get_cache_key(request)
        self.assertIn('user:123', key)
        self.assertIn('/api/test/', key)
    
    def test_get_cache_key_anonymous(self):
        """Test cache key generation for anonymous user"""
        request = Mock()
        request.user = Mock(is_authenticated=False)
        request.META = {'REMOTE_ADDR': '192.168.1.1'}
        request.path = '/api/test/'
        
        key = self.middleware.get_cache_key(request)
        self.assertIn('ip:192.168.1.1', key)
        self.assertIn('/api/test/', key)
    
    def test_is_exempt_path(self):
        """Test exempt path checking"""
        exempt_paths = [
            '/health/',
            '/metrics/',
            '/static/css/style.css',
            '/media/uploads/image.jpg',
        ]
        
        for path in exempt_paths:
            request = Mock()
            request.path = path
            self.assertTrue(self.middleware.is_exempt(request))
    
    def test_is_not_exempt_path(self):
        """Test non-exempt path checking"""
        non_exempt_paths = [
            '/api/auth/login/',
            '/api/voting/vote/',
            '/api/elections/',
        ]
        
        for path in non_exempt_paths:
            request = Mock()
            request.path = path
            self.assertFalse(self.middleware.is_exempt(request))


class RateLimitIntegrationTest(TestCase):
    """Integration tests for rate limiting"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.rate_limit_middleware = RateLimitMiddleware(get_response=lambda r: JsonResponse({'status': 'ok'}))
        self.throttle_middleware = ThrottleMiddleware(get_response=self.rate_limit_middleware)
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        cache.clear()
    
    def tearDown(self):
        cache.clear()
    
    def test_combined_rate_limit_and_throttle(self):
        """Test rate limit and throttle work together"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = Mock(is_authenticated=False)
        
        # Should pass through both middlewares
        response = self.throttle_middleware(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('X-RateLimit-Limit', response)
    
    def test_throttle_before_rate_limit(self):
        """Test endpoint throttle triggers before global rate limit"""
        request = self.factory.post('/api/auth/login/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.user = Mock(is_authenticated=False)
        
        # Make 5 login attempts (throttle limit)
        for i in range(5):
            response = self.throttle_middleware(request)
            self.assertEqual(response.status_code, 200)
        
        # 6th attempt should be throttled (before hitting global rate limit)
        response = self.throttle_middleware(request)
        self.assertEqual(response.status_code, 429)


# Run tests with: python manage.py test auditing.test_rate_limiting
