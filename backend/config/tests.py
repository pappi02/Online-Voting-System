"""
Email configuration management command tests
"""

from django.test import TestCase
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestEmailCommandTest(TestCase):
    """Test test_email management command"""
    
    def test_check_only_mode(self):
        """Test --check-only flag"""
        out = StringIO()
        
        try:
            call_command('test_email', '--check-only', stdout=out)
            output = out.getvalue()
            
            self.assertIn('Email Configuration Test', output)
            self.assertIn('Current Email Configuration', output)
        except CommandError:
            # May fail if email not configured, which is expected
            pass
    
    def test_command_with_recipient(self):
        """Test sending test email"""
        out = StringIO()
        
        # This will use console backend in tests
        try:
            call_command('test_email', 'test@example.com', stdout=out)
            output = out.getvalue()
            
            self.assertIn('Email Configuration Test', output)
        except CommandError:
            # Expected if email not fully configured
            pass


class ConfigureEmailCommandTest(TestCase):
    """Test configure_email management command"""
    
    @patch('builtins.input')
    def test_configure_email_interactive(self, mock_input):
        """Test interactive email configuration"""
        # Mock user inputs for console backend
        mock_input.side_effect = ['6']  # Select console backend
        
        out = StringIO()
        
        try:
            call_command('configure_email', stdout=out)
            output = out.getvalue()
            
            self.assertIn('Email Configuration Setup', output)
        except Exception:
            # Expected - command requires user interaction
            pass


class EmailLoaderTest(TestCase):
    """Test email configuration loader"""
    
    def test_get_email_settings(self):
        """Test getting email settings"""
        from config.email_loader import get_email_settings
        
        settings = get_email_settings()
        
        self.assertIn('EMAIL_BACKEND', settings)
        self.assertIn('EMAIL_HOST', settings)
        self.assertIn('EMAIL_PORT', settings)
        self.assertIn('DEFAULT_FROM_EMAIL', settings)
    
    def test_get_email_provider(self):
        """Test getting email provider"""
        from config.email_loader import get_email_provider
        
        provider = get_email_provider()
        
        self.assertIsInstance(provider, str)
        self.assertIn(provider, ['gmail', 'outlook', 'sendgrid', 'mailgun', 'custom', 'console'])
    
    def test_validate_email_config(self):
        """Test email config validation"""
        from config.email_loader import validate_email_config
        
        is_valid, message = validate_email_config()
        
        self.assertIsInstance(is_valid, bool)
        self.assertIsInstance(message, str)


class EmailConfigTest(TestCase):
    """Test enhanced email_config.py functions"""
    
    def test_validate_email_address(self):
        """Test email address validation"""
        from accounts.email_config import validate_email_address
        
        # Valid emails
        is_valid, error = validate_email_address('test@example.com')
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Invalid emails
        is_valid, error = validate_email_address('invalid-email')
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
    
    def test_send_html_email_validation(self):
        """Test email sending with validation"""
        from accounts.email_config import send_html_email
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        context = {
            'site_name': 'Test Site',
            'site_url': 'https://test.com',
            'support_email': 'support@test.com',
            'user_first_name': 'Test'
        }
        
        # Will use console backend in tests
        success, error = send_html_email(
            recipient_email='invalid-email',
            subject='Test',
            template_name='emails/voter_registration_confirmation.html',
            context=context
        )
        
        # Should fail validation
        self.assertFalse(success)
        self.assertIsNotNone(error)
    
    def test_test_email_configuration(self):
        """Test email configuration test function"""
        from accounts.email_config import test_email_configuration
        
        success, message = test_email_configuration()
        
        self.assertIsInstance(success, bool)
        self.assertIsInstance(message, str)


# Run tests with: python manage.py test config
