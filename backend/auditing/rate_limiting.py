"""
Enhanced Rate Limiting Middleware
"""

from django.core.cache import cache
from django.http import JsonResponse
from rest_framework import status
from auditing.audit_models import AuditLog
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """
    Enhanced rate limiting middleware with different limits for different endpoints
    """
    
    # Rate limits (requests per time window)
    RATE_LIMITS = {
        # Authentication endpoints
        '/api/accounts/login/': (5, 300),  # 5 requests per 5 minutes
        '/api/accounts/register/': (3, 3600),  # 3 requests per hour
        '/api/accounts/password/reset/': (3, 3600),  # 3 requests per hour
        '/api/accounts/2fa/verify/': (5, 300),  # 5 requests per 5 minutes
        
        # Voting endpoints
        '/api/voting/vote/': (1, 60),  # 1 request per minute
        '/api/voting/verify/': (10, 60),  # 10 requests per minute
        
        # API endpoints
        '/api/': (100, 60),  # 100 requests per minute (default for API)
        
        # Admin endpoints
        '/api/admin/': (50, 60),  # 50 requests per minute
    }
    
    # IP-based global limits
    GLOBAL_IP_LIMIT = (200, 60)  # 200 requests per minute per IP
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check rate limits before processing request
        if not self._check_rate_limit(request):
            return JsonResponse(
                {
                    'error': 'Rate limit exceeded',
                    'message': 'Too many requests. Please try again later.'
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        response = self.get_response(request)
        return response
    
    def _check_rate_limit(self, request):
        """
        Check if request is within rate limits
        
        Returns:
            bool: True if allowed, False if rate limit exceeded
        """
        # Skip rate limiting for certain methods
        if request.method in ['OPTIONS', 'HEAD']:
            return True
        
        # Get client IP
        ip_address = self._get_client_ip(request)
        
        # Check global IP limit first
        if not self._check_limit(f'global_ip:{ip_address}', *self.GLOBAL_IP_LIMIT):
            logger.warning(f'Global rate limit exceeded for IP: {ip_address}')
            self._log_rate_limit_exceeded(request, 'global_ip')
            return False
        
        # Check specific endpoint limits
        path = request.path
        
        # Find matching rate limit
        limit_key = None
        max_requests = None
        window = None
        
        for endpoint_pattern, (max_req, win) in self.RATE_LIMITS.items():
            if path.startswith(endpoint_pattern):
                limit_key = endpoint_pattern
                max_requests = max_req
                window = win
                break
        
        # If no specific limit found, use default API limit
        if limit_key is None and path.startswith('/api/'):
            limit_key = '/api/'
            max_requests, window = self.RATE_LIMITS['/api/']
        
        # Check endpoint-specific limit
        if limit_key:
            # Use IP + path as key for endpoint-specific limits
            cache_key = f'rate_limit:{ip_address}:{limit_key}'
            
            if not self._check_limit(cache_key, max_requests, window):
                logger.warning(
                    f'Rate limit exceeded for {ip_address} on {limit_key}'
                )
                self._log_rate_limit_exceeded(request, limit_key)
                return False
        
        # If user is authenticated, also check user-based limits
        if request.user and request.user.is_authenticated:
            user_cache_key = f'rate_limit:user:{request.user.id}:{path}'
            
            if not self._check_limit(user_cache_key, 1000, 3600):  # 1000 per hour
                logger.warning(
                    f'User rate limit exceeded for user {request.user.id}'
                )
                self._log_rate_limit_exceeded(request, 'user')
                return False
        
        return True
    
    def _check_limit(self, cache_key, max_requests, window):
        """
        Check if limit is exceeded
        
        Args:
            cache_key: Cache key
            max_requests: Maximum requests allowed
            window: Time window in seconds
        
        Returns:
            bool: True if within limit, False if exceeded
        """
        current = cache.get(cache_key, 0)
        
        if current >= max_requests:
            return False
        
        # Increment counter
        if current == 0:
            cache.set(cache_key, 1, window)
        else:
            cache.incr(cache_key)
        
        return True
    
    def _get_client_ip(self, request):
        """Get client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _log_rate_limit_exceeded(self, request, limit_type):
        """Log rate limit exceeded event"""
        AuditLog.log_action(
            action='rate_limit_exceeded',
            user=request.user if request.user.is_authenticated else None,
            request=request,
            severity=AuditLog.SEVERITY_WARNING,
            details={
                'limit_type': limit_type,
                'path': request.path,
                'method': request.method
            }
        )


class ThrottleMiddleware:
    """
    Adaptive throttling middleware that adjusts limits based on system load
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check system load and adjust throttling
        system_load = self._get_system_load()
        
        if system_load > 0.8:  # 80% load
            # Apply stricter throttling
            if not self._apply_throttle(request, factor=0.5):
                return JsonResponse(
                    {
                        'error': 'System overloaded',
                        'message': 'Please try again in a few moments.'
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
        
        response = self.get_response(request)
        return response
    
    def _get_system_load(self):
        """
        Get current system load
        
        Returns:
            float: Load factor (0-1)
        """
        # This is a simplified version
        # In production, you would check actual system metrics
        cache_key = 'system_load'
        load = cache.get(cache_key, 0.0)
        return load
    
    def _apply_throttle(self, request, factor=1.0):
        """
        Apply throttling based on factor
        
        Args:
            request: HTTP request
            factor: Throttle factor (0-1, where 0.5 means half the normal rate)
        
        Returns:
            bool: True if allowed, False if throttled
        """
        ip_address = self._get_client_ip(request)
        cache_key = f'throttle:{ip_address}'
        
        # Adjust max requests based on factor
        max_requests = int(10 * factor)
        window = 10  # 10 seconds
        
        current = cache.get(cache_key, 0)
        
        if current >= max_requests:
            return False
        
        if current == 0:
            cache.set(cache_key, 1, window)
        else:
            cache.incr(cache_key)
        
        return True
    
    def _get_client_ip(self, request):
        """Get client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


__all__ = ['RateLimitMiddleware', 'ThrottleMiddleware']
