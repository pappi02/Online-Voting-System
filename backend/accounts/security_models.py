"""
Two-Factor Authentication (2FA) Models
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import pyotp
import qrcode
from io import BytesIO
import base64
from datetime import timedelta

User = get_user_model()


class TwoFactorAuth(models.Model):
    """
    Model for managing 2FA settings
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='two_factor_auth'
    )
    secret_key = models.CharField(
        max_length=32,
        help_text="TOTP secret key"
    )
    is_enabled = models.BooleanField(
        default=False,
        help_text="Whether 2FA is enabled"
    )
    backup_codes = models.JSONField(
        default=list,
        help_text="Backup codes for account recovery"
    )
    enabled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When 2FA was enabled"
    )
    last_used = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time 2FA was used"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Two-Factor Authentication"
        verbose_name_plural = "Two-Factor Authentications"
    
    def __str__(self):
        return f"2FA for {self.user.email}"
    
    @classmethod
    def generate_secret_key(cls):
        """Generate a new TOTP secret key"""
        return pyotp.random_base32()
    
    def get_totp_uri(self):
        """Get provisioning URI for QR code"""
        totp = pyotp.TOTP(self.secret_key)
        return totp.provisioning_uri(
            name=self.user.email,
            issuer_name="iVote Systems"
        )
    
    def generate_qr_code(self):
        """Generate QR code for TOTP setup"""
        uri = self.get_totp_uri()
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Convert to base64 for easy display
        img_str = base64.b64encode(buffer.read()).decode()
        return f"data:image/png;base64,{img_str}"
    
    def verify_token(self, token):
        """Verify TOTP token"""
        totp = pyotp.TOTP(self.secret_key)
        is_valid = totp.verify(token, valid_window=1)
        
        if is_valid:
            self.last_used = timezone.now()
            self.save(update_fields=['last_used'])
        
        return is_valid
    
    def generate_backup_codes(self, count=10):
        """Generate backup codes"""
        import secrets
        codes = [secrets.token_hex(4).upper() for _ in range(count)]
        self.backup_codes = codes
        self.save(update_fields=['backup_codes'])
        return codes
    
    def verify_backup_code(self, code):
        """Verify and consume backup code"""
        code = code.upper().replace('-', '').replace(' ', '')
        
        if code in self.backup_codes:
            self.backup_codes.remove(code)
            self.save(update_fields=['backup_codes'])
            return True
        
        return False
    
    def enable(self):
        """Enable 2FA"""
        self.is_enabled = True
        self.enabled_at = timezone.now()
        self.save(update_fields=['is_enabled', 'enabled_at'])
    
    def disable(self):
        """Disable 2FA"""
        self.is_enabled = False
        self.save(update_fields=['is_enabled'])


class TwoFactorAuthLog(models.Model):
    """
    Audit log for 2FA attempts
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='two_factor_logs'
    )
    action = models.CharField(
        max_length=50,
        choices=[
            ('setup_initiated', 'Setup Initiated'),
            ('setup_completed', 'Setup Completed'),
            ('enabled', 'Enabled'),
            ('disabled', 'Disabled'),
            ('token_verified', 'Token Verified'),
            ('token_failed', 'Token Failed'),
            ('backup_used', 'Backup Code Used'),
            ('backup_failed', 'Backup Code Failed'),
        ]
    )
    success = models.BooleanField(default=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "2FA Log"
        verbose_name_plural = "2FA Logs"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.action} - {self.timestamp}"
    
    @classmethod
    def log_action(cls, user, action, success=True, ip_address=None, user_agent=None, details=None):
        """Create a log entry"""
        return cls.objects.create(
            user=user,
            action=action,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent or '',
            details=details or {}
        )


class SecurityQuestion(models.Model):
    """
    Security questions for account recovery
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='security_questions'
    )
    question = models.CharField(max_length=200)
    answer_hash = models.CharField(
        max_length=128,
        help_text="Hashed answer"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Security Question"
        verbose_name_plural = "Security Questions"
        unique_together = [['user', 'question']]
    
    def __str__(self):
        return f"{self.user.email} - {self.question}"
    
    def set_answer(self, answer):
        """Hash and set the answer"""
        from django.contrib.auth.hashers import make_password
        self.answer_hash = make_password(answer.lower().strip())
    
    def check_answer(self, answer):
        """Verify the answer"""
        from django.contrib.auth.hashers import check_password
        return check_password(answer.lower().strip(), self.answer_hash)


class TrustedDevice(models.Model):
    """
    Trusted devices for 2FA bypass
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='trusted_devices'
    )
    device_id = models.CharField(
        max_length=64,
        unique=True,
        help_text="Unique device identifier"
    )
    device_name = models.CharField(
        max_length=200,
        help_text="User-friendly device name"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    trusted_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(
        help_text="When trust expires (30 days default)"
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Trusted Device"
        verbose_name_plural = "Trusted Devices"
        ordering = ['-trusted_at']
        indexes = [
            models.Index(fields=['user', '-trusted_at']),
            models.Index(fields=['device_id']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.device_name}"
    
    @classmethod
    def create_trusted_device(cls, user, device_id, device_name, ip_address=None, user_agent=None, days=30):
        """Create a new trusted device"""
        expires_at = timezone.now() + timedelta(days=days)
        
        return cls.objects.create(
            user=user,
            device_id=device_id,
            device_name=device_name,
            ip_address=ip_address,
            user_agent=user_agent or '',
            expires_at=expires_at
        )
    
    def is_valid(self):
        """Check if device is still trusted"""
        return self.is_active and self.expires_at > timezone.now()
    
    def revoke(self):
        """Revoke trust for this device"""
        self.is_active = False
        self.save(update_fields=['is_active'])


__all__ = [
    'TwoFactorAuth',
    'TwoFactorAuthLog',
    'SecurityQuestion',
    'TrustedDevice'
]
