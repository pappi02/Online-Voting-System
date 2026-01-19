"""
Comprehensive Audit Models
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
import json

User = get_user_model()


class AuditLog(models.Model):
    """
    Comprehensive audit logging for all system actions
    """
    
    # Action types
    ACTION_LOGIN = 'login'
    ACTION_LOGOUT = 'logout'
    ACTION_LOGIN_FAILED = 'login_failed'
    ACTION_PASSWORD_CHANGE = 'password_change'
    ACTION_PASSWORD_RESET = 'password_reset'
    ACTION_PROFILE_UPDATE = 'profile_update'
    ACTION_VOTE_CAST = 'vote_cast'
    ACTION_VOTE_VERIFIED = 'vote_verified'
    ACTION_ELECTION_CREATED = 'election_created'
    ACTION_ELECTION_UPDATED = 'election_updated'
    ACTION_ELECTION_DELETED = 'election_deleted'
    ACTION_CANDIDATE_ADDED = 'candidate_added'
    ACTION_CANDIDATE_REMOVED = 'candidate_removed'
    ACTION_RESULT_PUBLISHED = 'result_published'
    ACTION_USER_REGISTERED = 'user_registered'
    ACTION_USER_APPROVED = 'user_approved'
    ACTION_USER_REJECTED = 'user_rejected'
    ACTION_DOCUMENT_UPLOADED = 'document_uploaded'
    ACTION_DOCUMENT_VERIFIED = 'document_verified'
    ACTION_DOCUMENT_REJECTED = 'document_rejected'
    ACTION_2FA_ENABLED = '2fa_enabled'
    ACTION_2FA_DISABLED = '2fa_disabled'
    ACTION_SUSPICIOUS_ACTIVITY = 'suspicious_activity'
    ACTION_API_ACCESS = 'api_access'
    ACTION_PERMISSION_DENIED = 'permission_denied'
    
    ACTION_CHOICES = [
        (ACTION_LOGIN, 'Login'),
        (ACTION_LOGOUT, 'Logout'),
        (ACTION_LOGIN_FAILED, 'Login Failed'),
        (ACTION_PASSWORD_CHANGE, 'Password Change'),
        (ACTION_PASSWORD_RESET, 'Password Reset'),
        (ACTION_PROFILE_UPDATE, 'Profile Update'),
        (ACTION_VOTE_CAST, 'Vote Cast'),
        (ACTION_VOTE_VERIFIED, 'Vote Verified'),
        (ACTION_ELECTION_CREATED, 'Election Created'),
        (ACTION_ELECTION_UPDATED, 'Election Updated'),
        (ACTION_ELECTION_DELETED, 'Election Deleted'),
        (ACTION_CANDIDATE_ADDED, 'Candidate Added'),
        (ACTION_CANDIDATE_REMOVED, 'Candidate Removed'),
        (ACTION_RESULT_PUBLISHED, 'Result Published'),
        (ACTION_USER_REGISTERED, 'User Registered'),
        (ACTION_USER_APPROVED, 'User Approved'),
        (ACTION_USER_REJECTED, 'User Rejected'),
        (ACTION_DOCUMENT_UPLOADED, 'Document Uploaded'),
        (ACTION_DOCUMENT_VERIFIED, 'Document Verified'),
        (ACTION_DOCUMENT_REJECTED, 'Document Rejected'),
        (ACTION_2FA_ENABLED, '2FA Enabled'),
        (ACTION_2FA_DISABLED, '2FA Disabled'),
        (ACTION_SUSPICIOUS_ACTIVITY, 'Suspicious Activity'),
        (ACTION_API_ACCESS, 'API Access'),
        (ACTION_PERMISSION_DENIED, 'Permission Denied'),
    ]
    
    # Severity levels
    SEVERITY_INFO = 'info'
    SEVERITY_WARNING = 'warning'
    SEVERITY_ERROR = 'error'
    SEVERITY_CRITICAL = 'critical'
    
    SEVERITY_CHOICES = [
        (SEVERITY_INFO, 'Info'),
        (SEVERITY_WARNING, 'Warning'),
        (SEVERITY_ERROR, 'Error'),
        (SEVERITY_CRITICAL, 'Critical'),
    ]
    
    # Fields
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='system_audit_logs'
    )
    
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default=SEVERITY_INFO
    )
    
    # Request info
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_method = models.CharField(max_length=10, blank=True)
    request_path = models.CharField(max_length=255, blank=True)
    
    # Object tracking (generic relation)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Additional data
    details = models.JSONField(default=dict, blank=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    # Metadata
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['severity', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"
    
    @classmethod
    def log_action(cls, action, user=None, request=None, **kwargs):
        """
        Create audit log entry
        
        Usage:
            AuditLog.log_action(
                action=AuditLog.ACTION_LOGIN,
                user=user,
                request=request,
                details={'method': '2fa'}
            )
        """
        log_data = {
            'action': action,
            'user': user,
        }
        
        if request:
            log_data.update({
                'ip_address': cls._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
                'request_method': request.method,
                'request_path': request.path,
                'session_key': request.session.session_key if hasattr(request, 'session') else '',
            })
        
        # Merge additional kwargs
        log_data.update(kwargs)
        
        return cls.objects.create(**log_data)
    
    @staticmethod
    def _get_client_ip(request):
        """Get client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityEvent(models.Model):
    """
    Security-specific events and suspicious activities
    """
    
    EVENT_BRUTE_FORCE = 'brute_force'
    EVENT_MULTIPLE_FAILURES = 'multiple_failures'
    EVENT_UNUSUAL_LOCATION = 'unusual_location'
    EVENT_UNUSUAL_TIME = 'unusual_time'
    EVENT_SUSPICIOUS_PATTERN = 'suspicious_pattern'
    EVENT_ACCOUNT_LOCKOUT = 'account_lockout'
    EVENT_PRIVILEGE_ESCALATION = 'privilege_escalation'
    EVENT_DATA_EXFILTRATION = 'data_exfiltration'
    
    EVENT_CHOICES = [
        (EVENT_BRUTE_FORCE, 'Brute Force Attempt'),
        (EVENT_MULTIPLE_FAILURES, 'Multiple Login Failures'),
        (EVENT_UNUSUAL_LOCATION, 'Unusual Location'),
        (EVENT_UNUSUAL_TIME, 'Unusual Time'),
        (EVENT_SUSPICIOUS_PATTERN, 'Suspicious Pattern'),
        (EVENT_ACCOUNT_LOCKOUT, 'Account Lockout'),
        (EVENT_PRIVILEGE_ESCALATION, 'Privilege Escalation Attempt'),
        (EVENT_DATA_EXFILTRATION, 'Possible Data Exfiltration'),
    ]
    
    STATUS_OPEN = 'open'
    STATUS_INVESTIGATING = 'investigating'
    STATUS_RESOLVED = 'resolved'
    STATUS_FALSE_POSITIVE = 'false_positive'
    
    STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_INVESTIGATING, 'Investigating'),
        (STATUS_RESOLVED, 'Resolved'),
        (STATUS_FALSE_POSITIVE, 'False Positive'),
    ]
    
    event_type = models.CharField(max_length=50, choices=EVENT_CHOICES)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_events'
    )
    
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    
    description = models.TextField()
    details = models.JSONField(default=dict)
    
    risk_score = models.IntegerField(default=0)  # 0-100
    auto_blocked = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_security_events'
    )
    resolution_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', 'status']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['risk_score', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.ip_address} - {self.created_at}"
    
    @classmethod
    def create_event(cls, event_type, ip_address, description, **kwargs):
        """
        Create security event
        
        Usage:
            SecurityEvent.create_event(
                event_type=SecurityEvent.EVENT_BRUTE_FORCE,
                ip_address='192.168.1.1',
                description='5 failed login attempts in 2 minutes',
                user=user,
                risk_score=75
            )
        """
        return cls.objects.create(
            event_type=event_type,
            ip_address=ip_address,
            description=description,
            **kwargs
        )
    
    def resolve(self, resolved_by, notes=''):
        """Mark security event as resolved"""
        self.status = self.STATUS_RESOLVED
        self.resolved_at = timezone.now()
        self.resolved_by = resolved_by
        self.resolution_notes = notes
        self.save()


class LoginAttempt(models.Model):
    """
    Track all login attempts for security monitoring
    """
    
    username = models.CharField(max_length=150, db_index=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    success = models.BooleanField(default=False)
    failure_reason = models.CharField(max_length=100, blank=True)
    
    ip_address = models.GenericIPAddressField(db_index=True)
    user_agent = models.TextField(blank=True)
    
    # 2FA info
    two_factor_required = models.BooleanField(default=False)
    two_factor_success = models.BooleanField(null=True, blank=True)
    
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['username', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
            models.Index(fields=['success', '-timestamp']),
        ]
    
    def __str__(self):
        status = 'SUCCESS' if self.success else 'FAILED'
        return f"{self.username} - {status} - {self.timestamp}"
    
    @classmethod
    def log_attempt(cls, username, success, request=None, **kwargs):
        """
        Log login attempt
        
        Usage:
            LoginAttempt.log_attempt(
                username='user@example.com',
                success=True,
                request=request,
                two_factor_required=True
            )
        """
        log_data = {
            'username': username,
            'success': success,
        }
        
        if request:
            log_data.update({
                'ip_address': cls._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
            })
        
        log_data.update(kwargs)
        
        return cls.objects.create(**log_data)
    
    @staticmethod
    def _get_client_ip(request):
        """Get client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @classmethod
    def get_failed_attempts(cls, username=None, ip_address=None, minutes=10):
        """
        Get recent failed attempts
        
        Usage:
            # By username
            failed = LoginAttempt.get_failed_attempts(username='user@example.com', minutes=5)
            
            # By IP
            failed = LoginAttempt.get_failed_attempts(ip_address='192.168.1.1', minutes=10)
        """
        from datetime import timedelta
        
        threshold = timezone.now() - timedelta(minutes=minutes)
        query = cls.objects.filter(
            success=False,
            timestamp__gte=threshold
        )
        
        if username:
            query = query.filter(username=username)
        
        if ip_address:
            query = query.filter(ip_address=ip_address)
        
        return query.count()


__all__ = ['AuditLog', 'SecurityEvent', 'LoginAttempt']
