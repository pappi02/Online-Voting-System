"""
Advanced Session Management
"""

from django.contrib.sessions.models import Session
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
import hashlib
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class SessionManager:
    """
    Advanced session management with security features
    """
    
    # Session limits
    MAX_CONCURRENT_SESSIONS = 3
    SESSION_TIMEOUT = 3600  # 1 hour in seconds
    ABSOLUTE_SESSION_TIMEOUT = 43200  # 12 hours in seconds
    
    @classmethod
    def create_session(cls, user, request):
        """
        Create new session with security tracking
        
        Args:
            user: User instance
            request: HTTP request
        
        Returns:
            str: Session key
        """
        # Get device fingerprint
        device_fingerprint = cls._get_device_fingerprint(request)
        
        # Check concurrent sessions
        cls._enforce_session_limit(user)
        
        # Store session metadata
        session_key = request.session.session_key
        
        if session_key:
            cls._store_session_metadata(
                session_key=session_key,
                user=user,
                device_fingerprint=device_fingerprint,
                ip_address=cls._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
        
        logger.info(f'Session created for user {user.email}: {session_key}')
        
        return session_key
    
    @classmethod
    def validate_session(cls, session_key, request):
        """
        Validate session security
        
        Args:
            session_key: Session key
            request: HTTP request
        
        Returns:
            dict: Validation result
        """
        # Get session metadata
        metadata = cls._get_session_metadata(session_key)
        
        if not metadata:
            return {
                'valid': False,
                'reason': 'session_not_found'
            }
        
        # Check session timeout
        last_activity = metadata.get('last_activity')
        if last_activity:
            last_activity_time = timezone.datetime.fromisoformat(last_activity)
            if timezone.now() - last_activity_time > timedelta(seconds=cls.SESSION_TIMEOUT):
                cls.invalidate_session(session_key)
                return {
                    'valid': False,
                    'reason': 'session_timeout'
                }
        
        # Check absolute timeout
        created_at = metadata.get('created_at')
        if created_at:
            created_time = timezone.datetime.fromisoformat(created_at)
            if timezone.now() - created_time > timedelta(seconds=cls.ABSOLUTE_SESSION_TIMEOUT):
                cls.invalidate_session(session_key)
                return {
                    'valid': False,
                    'reason': 'absolute_timeout'
                }
        
        # Verify device fingerprint
        current_fingerprint = cls._get_device_fingerprint(request)
        stored_fingerprint = metadata.get('device_fingerprint')
        
        if stored_fingerprint and current_fingerprint != stored_fingerprint:
            logger.warning(
                f'Session hijacking suspected: {session_key} - '
                f'Fingerprint mismatch'
            )
            cls.invalidate_session(session_key)
            return {
                'valid': False,
                'reason': 'fingerprint_mismatch'
            }
        
        # Verify IP address (optional, can be too strict)
        # current_ip = cls._get_client_ip(request)
        # stored_ip = metadata.get('ip_address')
        # if stored_ip and current_ip != stored_ip:
        #     # IP changed - could be legitimate (mobile network)
        #     pass
        
        # Update last activity
        cls._update_session_activity(session_key)
        
        return {
            'valid': True,
            'metadata': metadata
        }
    
    @classmethod
    def invalidate_session(cls, session_key):
        """
        Invalidate session
        
        Args:
            session_key: Session key to invalidate
        """
        try:
            session = Session.objects.get(session_key=session_key)
            session.delete()
        except Session.DoesNotExist:
            pass
        
        # Remove metadata
        cls._delete_session_metadata(session_key)
        
        logger.info(f'Session invalidated: {session_key}')
    
    @classmethod
    def invalidate_user_sessions(cls, user, exclude_session=None):
        """
        Invalidate all sessions for a user
        
        Args:
            user: User instance
            exclude_session: Session key to exclude (current session)
        """
        # Get all user sessions
        sessions = cls.get_user_sessions(user)
        
        for session_key in sessions:
            if exclude_session and session_key == exclude_session:
                continue
            
            cls.invalidate_session(session_key)
        
        logger.info(f'All sessions invalidated for user {user.email}')
    
    @classmethod
    def get_user_sessions(cls, user):
        """
        Get all active sessions for a user
        
        Args:
            user: User instance
        
        Returns:
            list: List of session keys
        """
        # Look up sessions in cache
        cache_key = f'user_sessions:{user.id}'
        sessions = cache.get(cache_key, [])
        
        # Verify sessions still exist
        valid_sessions = []
        for session_key in sessions:
            try:
                Session.objects.get(session_key=session_key)
                valid_sessions.append(session_key)
            except Session.DoesNotExist:
                pass
        
        # Update cache
        if valid_sessions != sessions:
            cache.set(cache_key, valid_sessions, 86400)  # 24 hours
        
        return valid_sessions
    
    @classmethod
    def _enforce_session_limit(cls, user):
        """
        Enforce maximum concurrent sessions limit
        
        Args:
            user: User instance
        """
        sessions = cls.get_user_sessions(user)
        
        if len(sessions) >= cls.MAX_CONCURRENT_SESSIONS:
            # Remove oldest session
            oldest_session = sessions[0]
            cls.invalidate_session(oldest_session)
            
            logger.info(
                f'Session limit reached for user {user.email}. '
                f'Removed oldest session: {oldest_session}'
            )
    
    @classmethod
    def _store_session_metadata(cls, session_key, user, device_fingerprint,
                                  ip_address, user_agent):
        """
        Store session metadata in cache
        
        Args:
            session_key: Session key
            user: User instance
            device_fingerprint: Device fingerprint
            ip_address: IP address
            user_agent: User agent string
        """
        metadata = {
            'user_id': user.id,
            'user_email': user.email,
            'device_fingerprint': device_fingerprint,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'created_at': timezone.now().isoformat(),
            'last_activity': timezone.now().isoformat()
        }
        
        # Store in cache
        cache_key = f'session_metadata:{session_key}'
        cache.set(cache_key, metadata, cls.ABSOLUTE_SESSION_TIMEOUT)
        
        # Add to user's session list
        user_sessions_key = f'user_sessions:{user.id}'
        sessions = cache.get(user_sessions_key, [])
        if session_key not in sessions:
            sessions.append(session_key)
            cache.set(user_sessions_key, sessions, 86400)  # 24 hours
    
    @classmethod
    def _get_session_metadata(cls, session_key):
        """
        Get session metadata from cache
        
        Args:
            session_key: Session key
        
        Returns:
            dict: Session metadata or None
        """
        cache_key = f'session_metadata:{session_key}'
        return cache.get(cache_key)
    
    @classmethod
    def _update_session_activity(cls, session_key):
        """
        Update session last activity time
        
        Args:
            session_key: Session key
        """
        metadata = cls._get_session_metadata(session_key)
        
        if metadata:
            metadata['last_activity'] = timezone.now().isoformat()
            cache_key = f'session_metadata:{session_key}'
            cache.set(cache_key, metadata, cls.ABSOLUTE_SESSION_TIMEOUT)
    
    @classmethod
    def _delete_session_metadata(cls, session_key):
        """
        Delete session metadata from cache
        
        Args:
            session_key: Session key
        """
        cache_key = f'session_metadata:{session_key}'
        cache.delete(cache_key)
    
    @classmethod
    def _get_device_fingerprint(cls, request):
        """
        Generate device fingerprint from request
        
        Args:
            request: HTTP request
        
        Returns:
            str: Device fingerprint (SHA256 hash)
        """
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
        
        # Combine headers to create fingerprint
        fingerprint_data = f'{user_agent}|{accept_language}|{accept_encoding}'
        
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()
    
    @classmethod
    def _get_client_ip(cls, request):
        """Get client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @classmethod
    def get_session_info(cls, session_key):
        """
        Get detailed session information
        
        Args:
            session_key: Session key
        
        Returns:
            dict: Session information
        """
        metadata = cls._get_session_metadata(session_key)
        
        if not metadata:
            return None
        
        # Calculate session age
        created_at = timezone.datetime.fromisoformat(metadata['created_at'])
        last_activity = timezone.datetime.fromisoformat(metadata['last_activity'])
        
        age = (timezone.now() - created_at).total_seconds()
        idle_time = (timezone.now() - last_activity).total_seconds()
        
        return {
            'session_key': session_key,
            'user_id': metadata['user_id'],
            'user_email': metadata['user_email'],
            'ip_address': metadata['ip_address'],
            'user_agent': metadata['user_agent'],
            'created_at': metadata['created_at'],
            'last_activity': metadata['last_activity'],
            'age_seconds': int(age),
            'idle_seconds': int(idle_time),
            'expires_in': cls.ABSOLUTE_SESSION_TIMEOUT - int(age)
        }


class SessionMiddleware:
    """
    Middleware to manage sessions with security features
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Validate session if user is authenticated
        if request.user.is_authenticated:
            session_key = request.session.session_key
            
            if session_key:
                validation = SessionManager.validate_session(session_key, request)
                
                if not validation['valid']:
                    # Session invalid - log out user
                    from django.contrib.auth import logout
                    logout(request)
                    
                    logger.warning(
                        f'Invalid session detected: {session_key} - '
                        f'Reason: {validation["reason"]}'
                    )
        
        response = self.get_response(request)
        return response


__all__ = ['SessionManager', 'SessionMiddleware']
