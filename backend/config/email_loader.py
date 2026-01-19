"""
Email configuration loader
Loads email credentials from main backend/.env file
"""

import os
from pathlib import Path
from decouple import config

# Email configuration is loaded from the main .env file
# All credentials should be in /backend/.env


def get_email_provider():
    """Get configured email provider"""
    # Determine provider from EMAIL_HOST
    host = config('EMAIL_HOST', default='')
    
    if 'gmail' in host:
        return 'gmail'
    elif 'outlook' in host or 'office365' in host:
        return 'outlook'
    elif 'sendgrid' in host:
        return 'sendgrid'
    elif 'mailgun' in host:
        return 'mailgun'
    else:
        return 'custom'


def get_email_backend():
    """Get Django email backend from settings"""
    return config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')


def get_email_settings():
    """
    Get email settings from main .env file
    
    Returns:
        dict: Email configuration settings
    """
    settings = {
        'EMAIL_BACKEND': config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend'),
        'EMAIL_HOST': config('EMAIL_HOST', default='smtp.gmail.com'),
        'EMAIL_PORT': int(config('EMAIL_PORT', default='587')),
        'EMAIL_USE_TLS': config('EMAIL_USE_TLS', default='True', cast=bool),
        'EMAIL_USE_SSL': config('EMAIL_USE_SSL', default='False', cast=bool),
        'EMAIL_HOST_USER': config('EMAIL_HOST_USER', default=''),
        'EMAIL_HOST_PASSWORD': config('EMAIL_HOST_PASSWORD', default=''),
        'DEFAULT_FROM_EMAIL': config('DEFAULT_FROM_EMAIL', default='noreply@ivotesystems.com'),
        'DEFAULT_FROM_NAME': config('DEFAULT_FROM_NAME', default='iVote Systems'),
        'SUPPORT_EMAIL': config('SUPPORT_EMAIL', default='support@ivotesystems.com'),
        'ADMIN_EMAIL': config('ADMIN_EMAIL', default='admin@ivotesystems.com'),
        'EMAIL_NOTIFICATION_ENABLED': config('EMAIL_NOTIFICATION_ENABLED', default='True', cast=bool),
        'EMAIL_VERIFICATION_REQUIRED': config('EMAIL_VERIFICATION_REQUIRED', default='True', cast=bool),
        'EMAIL_VERIFICATION_DEADLINE_DAYS': int(config('EMAIL_VERIFICATION_DEADLINE_DAYS', default='14')),
        'EMAIL_REMINDER_DAYS_BEFORE': int(config('EMAIL_REMINDER_DAYS_BEFORE', default='7')),
        'EMAIL_TIMEOUT': int(config('EMAIL_TIMEOUT', default='30')),
        'EMAIL_MAX_RETRIES': int(config('EMAIL_MAX_RETRIES', default='3')),
        'EMAIL_RETRY_DELAY_SECONDS': int(config('EMAIL_RETRY_DELAY_SECONDS', default='5')),
    }
    
    return settings


def validate_email_config():
    """
    Validate email configuration
    
    Returns:
        tuple: (is_valid, error_message)
    """
    settings = get_email_settings()
    backend = settings['EMAIL_BACKEND']
    
    # If console backend, it's valid for development
    if 'console' in backend.lower():
        return True, "Email configured for development mode (console backend)"
    
    # Validate SMTP settings for production backends
    if not settings['EMAIL_HOST']:
        return False, "EMAIL_HOST is not configured"
    
    if not settings['EMAIL_HOST_USER']:
        return False, "EMAIL_HOST_USER is not configured"
    
    if not settings['EMAIL_HOST_PASSWORD']:
        return False, "EMAIL_HOST_PASSWORD is not configured"
    
    if not settings['DEFAULT_FROM_EMAIL']:
        return False, "DEFAULT_FROM_EMAIL is not configured"
    
    return True, "Email configuration is valid"


def test_email_connection():
    """
    Test email connection
    
    Returns:
        tuple: (success, message)
    """
    from django.core.mail import get_connection
    
    try:
        connection = get_connection()
        connection.open()
        connection.close()
        return True, "Email connection successful"
    except Exception as e:
        return False, f"Email connection failed: {str(e)}"
