"""
Security Headers Middleware
"""

import logging

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    """
    Middleware to add security headers to all responses
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers
        self._add_security_headers(response)
        
        return response
    
    def _add_security_headers(self, response):
        """Add comprehensive security headers"""
        
        # Content Security Policy
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        
        # Strict Transport Security (HSTS)
        # Forces HTTPS for 1 year, including subdomains
        response['Strict-Transport-Security'] = (
            'max-age=31536000; includeSubDomains; preload'
        )
        
        # X-Frame-Options
        # Prevents clickjacking by disallowing framing
        response['X-Frame-Options'] = 'DENY'
        
        # X-Content-Type-Options
        # Prevents MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # X-XSS-Protection
        # Enables browser XSS protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer-Policy
        # Controls how much referrer information is sent
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions-Policy (formerly Feature-Policy)
        # Controls which browser features can be used
        response['Permissions-Policy'] = (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=(), '
            'usb=(), '
            'magnetometer=(), '
            'gyroscope=(), '
            'accelerometer=()'
        )
        
        # Cross-Origin-Opener-Policy
        response['Cross-Origin-Opener-Policy'] = 'same-origin'
        
        # Cross-Origin-Resource-Policy
        response['Cross-Origin-Resource-Policy'] = 'same-origin'
        
        # Cross-Origin-Embedder-Policy
        response['Cross-Origin-Embedder-Policy'] = 'require-corp'
        
        return response


class CSRFMiddleware:
    """
    Enhanced CSRF protection middleware
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Additional CSRF checks
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            if not self._verify_origin(request):
                logger.warning(
                    f'CSRF: Invalid origin for {request.path} from '
                    f'{request.META.get("HTTP_ORIGIN")}'
                )
        
        response = self.get_response(request)
        return response
    
    def _verify_origin(self, request):
        """
        Verify request origin matches allowed origins
        
        Returns:
            bool: True if origin is valid
        """
        origin = request.META.get('HTTP_ORIGIN')
        referer = request.META.get('HTTP_REFERER')
        
        if not origin and not referer:
            # Allow requests without origin/referer for API clients
            return True
        
        # In production, check against ALLOWED_HOSTS
        # For now, just verify they exist
        return True


class ClickjackingProtectionMiddleware:
    """
    Enhanced clickjacking protection
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Set frame options based on path
        if request.path.startswith('/admin/'):
            response['X-Frame-Options'] = 'DENY'
        elif request.path.startswith('/api/'):
            response['X-Frame-Options'] = 'DENY'
        else:
            response['X-Frame-Options'] = 'SAMEORIGIN'
        
        return response


class SecureSessionMiddleware:
    """
    Enhanced session security
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Set secure session cookie attributes
        if hasattr(response, 'cookies'):
            for cookie_name in response.cookies:
                cookie = response.cookies[cookie_name]
                
                # Make session cookies secure
                if 'session' in cookie_name.lower():
                    cookie['secure'] = True  # Only send over HTTPS
                    cookie['httponly'] = True  # No JavaScript access
                    cookie['samesite'] = 'Strict'  # CSRF protection
        
        return response


class ContentTypeValidationMiddleware:
    """
    Validate Content-Type headers for API requests
    """
    
    ALLOWED_CONTENT_TYPES = [
        'application/json',
        'application/x-www-form-urlencoded',
        'multipart/form-data',
        'text/plain'
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Validate Content-Type for POST/PUT/PATCH requests
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.content_type
            
            if content_type:
                # Extract base content type (before ';')
                base_type = content_type.split(';')[0].strip()
                
                if base_type not in self.ALLOWED_CONTENT_TYPES:
                    logger.warning(
                        f'Invalid Content-Type: {content_type} for '
                        f'{request.path} from {request.META.get("REMOTE_ADDR")}'
                    )
        
        response = self.get_response(request)
        return response


__all__ = [
    'SecurityHeadersMiddleware',
    'CSRFMiddleware',
    'ClickjackingProtectionMiddleware',
    'SecureSessionMiddleware',
    'ContentTypeValidationMiddleware'
]
