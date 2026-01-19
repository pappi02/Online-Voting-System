"""
Configuration package for credentials and settings
"""

from .email_loader import (
    get_email_settings,
    get_email_provider,
    get_email_backend,
    validate_email_config,
    test_email_connection
)

__all__ = [
    'get_email_settings',
    'get_email_provider',
    'get_email_backend',
    'validate_email_config',
    'test_email_connection',
]
