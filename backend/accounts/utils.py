"""
Utility functions for authentication and security
Includes OTP generation, email/SMS sending, and security helpers
"""

import random
import string
import secrets
import logging
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from decouple import config

logger = logging.getLogger(__name__)


def generate_otp_code(length=6):
    """
    Generate a secure random OTP code
    
    Args:
        length (int): Length of OTP code (default: 6)
    
    Returns:
        str: Random OTP code
    """
    digits = string.digits
    return ''.join(secrets.choice(digits) for _ in range(length))


def create_otp_for_user(user, purpose='login', method='email', expiry_minutes=10):
    """
    Create and save an OTP verification record for a user
    
    Args:
        user: User instance
        purpose (str): Purpose of OTP (login, registration, password_reset, etc.)
        method (str): Delivery method (email or sms)
        expiry_minutes (int): OTP validity period in minutes
    
    Returns:
        OTPVerification: Created OTP instance
    """
    from .models import OTPVerification
    
    # Generate OTP code
    otp_code = generate_otp_code()
    
    # Determine contact info based on method
    contact_info = user.email if method == 'email' else user.phone_number
    
    # Create OTP record
    otp = OTPVerification.objects.create(
        user=user,
        otp_code=otp_code,
        method=method,
        purpose=purpose,
        contact_info=contact_info,
        expires_at=timezone.now() + timedelta(minutes=expiry_minutes)
    )
    
    logger.info(f"OTP created for {user.email} - Purpose: {purpose}, Method: {method}")
    return otp


def send_otp_email(user, otp_code, purpose='login'):
    """
    Send OTP code via email
    
    Args:
        user: User instance
        otp_code (str): OTP code to send
        purpose (str): Purpose of OTP
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    subject_map = {
        'login': 'iVote Systems - Login Verification Code',
        'registration': 'iVote Systems - Registration Verification Code',
        'password_reset': 'iVote Systems - Password Reset Code',
        'account_recovery': 'iVote Systems - Account Recovery Code',
    }
    
    subject = subject_map.get(purpose, 'iVote Systems - Verification Code')
    
    message = f"""
    Hello {user.first_name},
    
    Your verification code for {purpose.replace('_', ' ')} is:
    
    {otp_code}
    
    This code will expire in 10 minutes.
    
    If you didn't request this code, please ignore this email or contact support.
    
    Best regards,
    iVote Systems Team
    """
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=config('EMAIL_HOST_USER', default='noreply@ivotesystems.com'),
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(f"OTP email sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP email to {user.email}: {str(e)}")
        return False


def send_otp_sms(user, otp_code, purpose='login'):
    """
    Send OTP code via SMS
    
    Args:
        user: User instance
        otp_code (str): OTP code to send
        purpose (str): Purpose of OTP
    
    Returns:
        bool: True if SMS sent successfully, False otherwise
    
    Note:
        This is a placeholder. In production, integrate with SMS provider
        like Twilio, AWS SNS, or Africa's Talking
    """
    # TODO: Integrate with SMS provider
    # For now, log the OTP (only for development!)
    logger.warning(f"SMS OTP for {user.phone_number}: {otp_code} (Purpose: {purpose})")
    logger.warning("SMS sending not implemented - integrate with SMS provider")
    
    # Placeholder return
    return True


def verify_otp(user, otp_code, purpose='login'):
    """
    Verify an OTP code for a user
    
    Args:
        user: User instance
        otp_code (str): OTP code to verify
        purpose (str): Purpose of OTP
    
    Returns:
        tuple: (success: bool, message: str)
    """
    from .models import OTPVerification
    
    try:
        # Get the most recent valid OTP for this user and purpose
        otp = OTPVerification.objects.filter(
            user=user,
            purpose=purpose,
            is_used=False
        ).order_by('-created_at').first()
        
        if not otp:
            return False, "No valid OTP found. Please request a new one."
        
        # Check if OTP is expired
        if not otp.is_valid():
            return False, "OTP has expired. Please request a new one."
        
        # Verify the code
        if otp.verify(otp_code):
            return True, "OTP verified successfully"
        else:
            return False, f"Invalid OTP code. {3 - otp.attempts} attempts remaining."
    
    except Exception as e:
        logger.error(f"Error verifying OTP for {user.email}: {str(e)}")
        return False, "An error occurred during verification"


def get_client_ip(request):
    """
    Get client IP address from request
    
    Args:
        request: Django request object
    
    Returns:
        str: Client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """
    Get user agent string from request
    
    Args:
        request: Django request object
    
    Returns:
        str: User agent string
    """
    return request.META.get('HTTP_USER_AGENT', '')


def log_audit_event(user, action, description='', request=None, details=None):
    """
    Log a user audit event
    
    Args:
        user: User instance
        action (str): Action type (login, logout, password_change, etc.)
        description (str): Event description
        request: Django request object (optional)
        details (dict): Additional details (optional)
    
    Returns:
        UserAuditLog: Created audit log instance
    """
    from .models import UserAuditLog
    
    ip_address = get_client_ip(request) if request else None
    user_agent = get_user_agent(request) if request else ''
    
    audit_log = UserAuditLog.objects.create(
        user=user,
        action=action,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details or {}
    )
    
    logger.info(f"Audit log created: {user.email} - {action}")
    return audit_log


def check_rate_limit(user, action='login', max_attempts=5, window_minutes=15):
    """
    Check if user has exceeded rate limit for an action
    
    Args:
        user: User instance
        action (str): Action to check
        max_attempts (int): Maximum attempts allowed
        window_minutes (int): Time window in minutes
    
    Returns:
        tuple: (allowed: bool, remaining: int, reset_time: datetime)
    """
    from .models import UserAuditLog
    
    window_start = timezone.now() - timedelta(minutes=window_minutes)
    
    attempt_count = UserAuditLog.objects.filter(
        user=user,
        action=action,
        timestamp__gte=window_start
    ).count()
    
    allowed = attempt_count < max_attempts
    remaining = max(0, max_attempts - attempt_count)
    reset_time = window_start + timedelta(minutes=window_minutes)
    
    return allowed, remaining, reset_time


def generate_secure_token(length=32):
    """
    Generate a secure random token
    
    Args:
        length (int): Length of token in bytes
    
    Returns:
        str: Secure random token (hex)
    """
    return secrets.token_hex(length)
