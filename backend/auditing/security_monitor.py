"""
Security Monitoring Service
"""

from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from .audit_models import AuditLog, SecurityEvent, LoginAttempt
import logging

logger = logging.getLogger(__name__)


class SecurityMonitor:
    """
    Monitor and detect suspicious security activities
    """
    
    # Thresholds
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_ATTEMPT_WINDOW = 10  # minutes
    
    MAX_FAILED_2FA = 3
    TFA_ATTEMPT_WINDOW = 5  # minutes
    
    MAX_API_CALLS = 100
    API_RATE_WINDOW = 60  # seconds
    
    UNUSUAL_TIME_THRESHOLD = 3  # 3 AM - 6 AM considered unusual
    
    @classmethod
    def check_brute_force(cls, username=None, ip_address=None):
        """
        Check for brute force attack
        
        Returns:
            dict: {
                'is_suspicious': bool,
                'failed_attempts': int,
                'should_block': bool
            }
        """
        failed_attempts = LoginAttempt.get_failed_attempts(
            username=username,
            ip_address=ip_address,
            minutes=cls.LOGIN_ATTEMPT_WINDOW
        )
        
        is_suspicious = failed_attempts >= cls.MAX_LOGIN_ATTEMPTS
        should_block = failed_attempts >= cls.MAX_LOGIN_ATTEMPTS
        
        if is_suspicious:
            # Create security event
            SecurityEvent.create_event(
                event_type=SecurityEvent.EVENT_BRUTE_FORCE,
                ip_address=ip_address,
                description=f'{failed_attempts} failed login attempts in {cls.LOGIN_ATTEMPT_WINDOW} minutes',
                details={
                    'username': username,
                    'failed_attempts': failed_attempts,
                    'window_minutes': cls.LOGIN_ATTEMPT_WINDOW
                },
                risk_score=min(failed_attempts * 15, 100),
                auto_blocked=should_block
            )
            
            logger.warning(
                f'Brute force detected: {username or "unknown"} from {ip_address} '
                f'({failed_attempts} attempts)'
            )
        
        return {
            'is_suspicious': is_suspicious,
            'failed_attempts': failed_attempts,
            'should_block': should_block
        }
    
    @classmethod
    def check_rate_limit(cls, user_id, action, max_attempts=None, window=None):
        """
        Check rate limit for specific action
        
        Args:
            user_id: User ID
            action: Action type (e.g., 'vote', 'api_call')
            max_attempts: Maximum attempts allowed
            window: Time window in seconds
        
        Returns:
            dict: {
                'allowed': bool,
                'current_count': int,
                'limit': int,
                'reset_in': int (seconds)
            }
        """
        max_attempts = max_attempts or cls.MAX_API_CALLS
        window = window or cls.API_RATE_WINDOW
        
        cache_key = f'rate_limit:{user_id}:{action}'
        
        current_count = cache.get(cache_key, 0)
        
        if current_count >= max_attempts:
            # Log security event
            SecurityEvent.create_event(
                event_type=SecurityEvent.EVENT_SUSPICIOUS_PATTERN,
                ip_address='0.0.0.0',  # Would get from request
                description=f'Rate limit exceeded for action: {action}',
                details={
                    'user_id': user_id,
                    'action': action,
                    'attempts': current_count,
                    'limit': max_attempts
                },
                risk_score=60
            )
            
            return {
                'allowed': False,
                'current_count': current_count,
                'limit': max_attempts,
                'reset_in': cache.ttl(cache_key)
            }
        
        # Increment counter
        if current_count == 0:
            cache.set(cache_key, 1, window)
        else:
            cache.incr(cache_key)
        
        return {
            'allowed': True,
            'current_count': current_count + 1,
            'limit': max_attempts,
            'reset_in': cache.ttl(cache_key)
        }
    
    @classmethod
    def check_unusual_location(cls, user, ip_address):
        """
        Check for login from unusual location
        
        Args:
            user: User instance
            ip_address: IP address
        
        Returns:
            dict: {
                'is_unusual': bool,
                'previous_ips': list,
                'risk_score': int
            }
        """
        # Get user's previous IPs
        previous_attempts = LoginAttempt.objects.filter(
            user=user,
            success=True
        ).values_list('ip_address', flat=True).distinct()[:10]
        
        previous_ips = list(previous_attempts)
        is_unusual = ip_address not in previous_ips and len(previous_ips) > 0
        
        if is_unusual:
            # Calculate risk score based on how different the location is
            risk_score = 40  # Base risk for new location
            
            # Create security event
            SecurityEvent.create_event(
                event_type=SecurityEvent.EVENT_UNUSUAL_LOCATION,
                ip_address=ip_address,
                description=f'Login from new location: {ip_address}',
                user=user,
                details={
                    'new_ip': ip_address,
                    'previous_ips': previous_ips
                },
                risk_score=risk_score
            )
            
            logger.info(
                f'Unusual location detected for user {user.email}: '
                f'{ip_address} (previous: {previous_ips})'
            )
        
        return {
            'is_unusual': is_unusual,
            'previous_ips': previous_ips,
            'risk_score': 40 if is_unusual else 0
        }
    
    @classmethod
    def check_unusual_time(cls, user):
        """
        Check for login at unusual time
        
        Args:
            user: User instance
        
        Returns:
            dict: {
                'is_unusual': bool,
                'hour': int,
                'risk_score': int
            }
        """
        now = timezone.now()
        hour = now.hour
        
        # Consider 3 AM - 6 AM as unusual
        is_unusual = cls.UNUSUAL_TIME_THRESHOLD <= hour < 6
        
        if is_unusual:
            SecurityEvent.create_event(
                event_type=SecurityEvent.EVENT_UNUSUAL_TIME,
                ip_address='0.0.0.0',
                description=f'Login at unusual time: {hour}:00',
                user=user,
                details={
                    'hour': hour,
                    'timestamp': now.isoformat()
                },
                risk_score=20
            )
            
            logger.info(
                f'Unusual time login detected for user {user.email}: '
                f'{hour}:00'
            )
        
        return {
            'is_unusual': is_unusual,
            'hour': hour,
            'risk_score': 20 if is_unusual else 0
        }
    
    @classmethod
    def analyze_login_risk(cls, user, ip_address):
        """
        Comprehensive login risk analysis
        
        Args:
            user: User instance
            ip_address: IP address
        
        Returns:
            dict: {
                'total_risk_score': int (0-100),
                'factors': dict,
                'should_require_additional_verification': bool
            }
        """
        factors = {}
        total_risk = 0
        
        # Check brute force
        brute_force = cls.check_brute_force(
            username=user.email,
            ip_address=ip_address
        )
        factors['brute_force'] = brute_force
        if brute_force['is_suspicious']:
            total_risk += 50
        
        # Check unusual location
        location = cls.check_unusual_location(user, ip_address)
        factors['location'] = location
        total_risk += location['risk_score']
        
        # Check unusual time
        time = cls.check_unusual_time(user)
        factors['time'] = time
        total_risk += time['risk_score']
        
        # Cap at 100
        total_risk = min(total_risk, 100)
        
        # Require additional verification if risk > 60
        require_additional = total_risk > 60
        
        if require_additional:
            logger.warning(
                f'High risk login detected for {user.email}: '
                f'Risk score {total_risk}'
            )
        
        return {
            'total_risk_score': total_risk,
            'factors': factors,
            'should_require_additional_verification': require_additional
        }
    
    @classmethod
    def check_suspicious_patterns(cls, user, action_type, details=None):
        """
        Check for suspicious patterns in user behavior
        
        Args:
            user: User instance
            action_type: Type of action
            details: Additional details
        
        Returns:
            dict: {
                'is_suspicious': bool,
                'patterns': list,
                'risk_score': int
            }
        """
        patterns = []
        risk_score = 0
        
        # Check for rapid successive actions
        recent_actions = AuditLog.objects.filter(
            user=user,
            action=action_type,
            timestamp__gte=timezone.now() - timedelta(minutes=1)
        ).count()
        
        if recent_actions > 10:
            patterns.append('rapid_actions')
            risk_score += 30
        
        # Check for unusual access patterns
        if action_type == AuditLog.ACTION_API_ACCESS:
            api_calls = AuditLog.objects.filter(
                user=user,
                action=AuditLog.ACTION_API_ACCESS,
                timestamp__gte=timezone.now() - timedelta(hours=1)
            ).count()
            
            if api_calls > 1000:
                patterns.append('excessive_api_usage')
                risk_score += 40
        
        is_suspicious = risk_score > 50
        
        if is_suspicious:
            SecurityEvent.create_event(
                event_type=SecurityEvent.EVENT_SUSPICIOUS_PATTERN,
                ip_address='0.0.0.0',
                description=f'Suspicious pattern detected: {", ".join(patterns)}',
                user=user,
                details={
                    'action_type': action_type,
                    'patterns': patterns,
                    'details': details or {}
                },
                risk_score=risk_score
            )
        
        return {
            'is_suspicious': is_suspicious,
            'patterns': patterns,
            'risk_score': risk_score
        }
    
    @classmethod
    def get_user_risk_profile(cls, user):
        """
        Get comprehensive risk profile for user
        
        Args:
            user: User instance
        
        Returns:
            dict: Risk profile with various metrics
        """
        # Recent security events
        recent_events = SecurityEvent.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timedelta(days=30)
        )
        
        # Failed login attempts
        failed_logins = LoginAttempt.objects.filter(
            user=user,
            success=False,
            timestamp__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Suspicious activities
        suspicious_activities = recent_events.filter(
            event_type__in=[
                SecurityEvent.EVENT_SUSPICIOUS_PATTERN,
                SecurityEvent.EVENT_BRUTE_FORCE
            ]
        ).count()
        
        # Calculate overall risk score
        base_risk = 0
        
        if failed_logins > 3:
            base_risk += 20
        
        if suspicious_activities > 0:
            base_risk += suspicious_activities * 10
        
        open_events = recent_events.filter(status=SecurityEvent.STATUS_OPEN).count()
        if open_events > 0:
            base_risk += open_events * 15
        
        risk_score = min(base_risk, 100)
        
        # Determine risk level
        if risk_score < 30:
            risk_level = 'low'
        elif risk_score < 60:
            risk_level = 'medium'
        elif risk_score < 80:
            risk_level = 'high'
        else:
            risk_level = 'critical'
        
        return {
            'user_id': user.id,
            'email': user.email,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'failed_logins_7d': failed_logins,
            'suspicious_activities_30d': suspicious_activities,
            'open_security_events': open_events,
            'total_security_events_30d': recent_events.count()
        }


__all__ = ['SecurityMonitor']
