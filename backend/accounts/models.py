"""
User and Account models for iVote Systems (iVS)
Implements role-based access control with secure authentication
"""

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import EmailValidator, RegexValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid
import logging

logger = logging.getLogger(__name__)


class CustomUserManager(BaseUserManager):
    """Custom user manager for handling user creation with email"""
    
    def create_user(self, email, password, **extra_fields):
        """Create and save a regular user"""
        if not email:
            raise ValueError(_('Email is required'))
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        logger.info(f"User created: {email}")
        return user
    
    def create_superuser(self, email, password, **extra_fields):
        """Create and save a superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('status', 'approved')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True'))
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model with role-based access control
    Replaces Django's default User model
    """
    
    ROLE_CHOICES = (
        ('admin', _('Administrator')),
        ('election_officer', _('Election Officer')),
        ('voter', _('Voter')),
        ('observer', _('Observer')),
    )
    
    STATUS_CHOICES = (
        ('pending', _('Pending Approval')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('blocked', _('Blocked')),
        ('inactive', _('Inactive')),
    )
    
    # Override username - use email instead
    username = None
    
    # Basic info
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()],
        help_text='User email address (must be unique)'
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    
    # Phone number with validation
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message='Phone number must be valid (9-15 digits)'
    )
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        null=True
    )
    
    # Role and Status
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='voter',
        help_text='User role in the system'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text='Account approval status'
    )
    
    # Identity verification
    national_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        help_text='National ID or student ID'
    )
    id_verified = models.BooleanField(
        default=False,
        help_text='Whether national ID has been verified'
    )
    
    # Multi-factor authentication
    mfa_enabled = models.BooleanField(
        default=False,
        help_text='Whether two-factor authentication is enabled'
    )
    mfa_method = models.CharField(
        max_length=20,
        choices=(
            ('sms', 'SMS'),
            ('email', 'Email'),
            ('authenticator', 'Authenticator App'),
        ),
        blank=True,
        null=True
    )
    
    # Voting status
    has_voted = models.BooleanField(
        default=False,
        help_text='Whether user has participated in any election'
    )
    
    # Timestamps and metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)
    last_password_change = models.DateTimeField(null=True, blank=True)
    
    # Additional metadata
    institution = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Institution/Organization name'
    )
    department = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Department/Faculty'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether account is active'
    )
    
    # Password security
    failed_login_attempts = models.IntegerField(
        default=0,
        help_text='Number of failed login attempts'
    )
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Account locked until this time (brute force protection)'
    )
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"
    
    def is_admin(self):
        """Check if user is an administrator"""
        return self.role == 'admin' or self.is_superuser
    
    def is_voter(self):
        """Check if user is a voter"""
        return self.role == 'voter' and self.status == 'approved'
    
    def is_election_officer(self):
        """Check if user is an election officer"""
        return self.role == 'election_officer' and self.status == 'approved'
    
    def can_vote(self):
        """Determine if user is eligible to vote"""
        return (
            self.is_voter() and
            self.is_active and
            self.id_verified and
            not self.is_locked_out()
        )
    
    def is_locked_out(self):
        """Check if account is locked due to failed attempts"""
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False
    
    def record_failed_login(self):
        """Record a failed login attempt"""
        self.failed_login_attempts += 1
        
        # Lock account after 5 failed attempts for 30 minutes
        if self.failed_login_attempts >= 5:
            from django.utils import timezone as tz
            self.locked_until = tz.now() + timezone.timedelta(minutes=30)
            logger.warning(f"Account locked: {self.email} after {self.failed_login_attempts} failed attempts")
        
        self.save()
    
    def reset_login_attempts(self):
        """Reset failed login attempts on successful login"""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login = timezone.now()
        self.save()
    
    def update_password_change_time(self):
        """Update password change timestamp"""
        self.last_password_change = timezone.now()
        self.save()


class OTPVerification(models.Model):
    """
    One-Time Password (OTP) model for multi-factor authentication
    Supports both SMS and Email delivery
    """
    
    METHOD_CHOICES = (
        ('sms', 'SMS'),
        ('email', 'Email'),
    )
    
    PURPOSE_CHOICES = (
        ('login', 'Login Verification'),
        ('registration', 'Registration Verification'),
        ('password_reset', 'Password Reset'),
        ('account_recovery', 'Account Recovery'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='otp_verifications'
    )
    otp_code = models.CharField(max_length=6)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES)
    
    contact_info = models.CharField(
        max_length=255,
        help_text='Email or phone number OTP was sent to'
    )
    
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    
    attempts = models.IntegerField(
        default=0,
        help_text='Number of verification attempts'
    )
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        db_table = 'otp_verification'
        verbose_name = _('OTP Verification')
        verbose_name_plural = _('OTP Verifications')
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['is_used']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"OTP for {self.user.email} ({self.get_purpose_display()})"
    
    def is_valid(self):
        """Check if OTP is still valid (not expired and not used)"""
        from django.utils import timezone as tz
        return (
            not self.is_used and
            tz.now() < self.expires_at and
            self.attempts < 3
        )
    
    def verify(self, otp_code):
        """Verify the OTP code"""
        from django.utils import timezone as tz
        
        if not self.is_valid():
            self.attempts += 1
            self.save()
            return False
        
        if self.otp_code == otp_code:
            self.is_used = True
            self.verified_at = tz.now()
            self.save()
            logger.info(f"OTP verified for {self.user.email}")
            return True
        else:
            self.attempts += 1
            self.save()
            logger.warning(f"Failed OTP verification for {self.user.email} (attempt {self.attempts})")
            return False
    
    def mark_expired(self):
        """Manually mark OTP as expired"""
        self.expires_at = timezone.now()
        self.save()


class UserAuditLog(models.Model):
    """
    Audit log for user account activities
    Tracks all important user account events for security
    """
    
    ACTION_CHOICES = (
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('password_change', 'Password Changed'),
        ('password_reset', 'Password Reset'),
        ('mfa_enabled', 'MFA Enabled'),
        ('mfa_disabled', 'MFA Disabled'),
        ('email_verified', 'Email Verified'),
        ('phone_verified', 'Phone Verified'),
        ('id_verified', 'ID Verified'),
        ('profile_updated', 'Profile Updated'),
        ('account_locked', 'Account Locked'),
        ('account_unlocked', 'Account Unlocked'),
        ('status_changed', 'Status Changed'),
        ('role_changed', 'Role Changed'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    details = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'user_audit_log'
        verbose_name = _('User Audit Log')
        verbose_name_plural = _('User Audit Logs')
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user.email} - {self.get_action_display()} ({self.timestamp})"


class NotificationLog(models.Model):
    """Log of all notifications sent to users"""
    
    NOTIFICATION_TYPES = [
        ('voter_registration_confirmation', 'Voter Registration Confirmation'),
        ('document_upload_confirmation', 'Document Upload Confirmation'),
        ('document_verification_pending', 'Document Verification Pending'),
        ('document_verified', 'Document Verified'),
        ('document_rejected', 'Document Rejected'),
        ('voter_eligible', 'Voter Eligible'),
        ('voter_ineligible', 'Voter Ineligible'),
        ('voter_approved', 'Voter Approved'),
        ('voter_rejected', 'Voter Rejected'),
        ('verification_deadline_reminder', 'Verification Deadline Reminder'),
    ]
    
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ]
    
    id = models.CharField(max_length=64, primary_key=True, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'notification_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id', 'created_at']),
            models.Index(fields=['notification_type', 'status']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} to {self.recipient_email}"
    
    def mark_sent(self):
        """Mark notification as successfully sent"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])
    
    def mark_failed(self, error_message):
        """Mark notification as failed with error details"""
        self.status = 'failed'
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message'])


# Import voter-related models
from accounts.voter_models import (
    VoterProfile, VoterDocument, EligibilityRule, VerificationLog
)

# Import security models
from accounts.security_models import (
    TwoFactorAuth, TwoFactorAuthLog, SecurityQuestion, TrustedDevice
)

__all__ = [
    'User', 'OTPVerification', 'UserAuditLog', 'NotificationLog',
    'VoterProfile', 'VoterDocument', 'EligibilityRule', 'VerificationLog',
    'TwoFactorAuth', 'TwoFactorAuthLog', 'SecurityQuestion', 'TrustedDevice'
]
