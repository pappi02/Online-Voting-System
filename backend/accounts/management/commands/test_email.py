"""
Management command to test email configuration
Usage: python manage.py test_email <recipient_email>
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from accounts.email_config import (
    test_email_configuration,
    send_test_email,
    EMAIL_BACKEND,
    EMAIL_HOST,
    EMAIL_PORT,
    EMAIL_HOST_USER,
    DEFAULT_FROM_EMAIL
)
from config.email_loader import validate_email_config, get_email_provider


class Command(BaseCommand):
    help = 'Test email configuration and optionally send a test email'

    def add_arguments(self, parser):
        parser.add_argument(
            'recipient',
            nargs='?',
            type=str,
            help='Email address to send test email to (optional)'
        )
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='Only check configuration without sending email'
        )

    def handle(self, *args, **options):
        recipient = options.get('recipient')
        check_only = options.get('check_only')

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Email Configuration Test ===\n'))

        # Display current configuration
        self.stdout.write(self.style.MIGRATE_LABEL('Current Email Configuration:'))
        self.stdout.write(f'  Backend: {EMAIL_BACKEND}')
        self.stdout.write(f'  Provider: {get_email_provider()}')
        self.stdout.write(f'  Host: {EMAIL_HOST or "(not set)"}')
        self.stdout.write(f'  Port: {EMAIL_PORT}')
        self.stdout.write(f'  User: {EMAIL_HOST_USER or "(not set)"}')
        self.stdout.write(f'  From Email: {DEFAULT_FROM_EMAIL}')
        self.stdout.write('')

        # Validate configuration
        self.stdout.write(self.style.MIGRATE_LABEL('Validating Configuration:'))
        is_valid, message = validate_email_config()
        
        if is_valid:
            self.stdout.write(self.style.SUCCESS(f'  ✓ {message}'))
        else:
            self.stdout.write(self.style.ERROR(f'  ✗ {message}'))
            raise CommandError('Email configuration is invalid')

        # Test connection (only if not console backend)
        if 'console' not in EMAIL_BACKEND.lower():
            self.stdout.write('\n' + self.style.MIGRATE_LABEL('Testing Connection:'))
            success, message = test_email_configuration()
            
            if success:
                self.stdout.write(self.style.SUCCESS(f'  ✓ {message}'))
            else:
                self.stdout.write(self.style.ERROR(f'  ✗ {message}'))
                raise CommandError('Email connection test failed')
        else:
            self.stdout.write('\n' + self.style.WARNING('  ⓘ Console backend detected - skipping connection test'))

        # Send test email if recipient provided
        if recipient and not check_only:
            self.stdout.write('\n' + self.style.MIGRATE_LABEL(f'Sending Test Email to {recipient}:'))
            success, message = send_test_email(recipient)
            
            if success:
                self.stdout.write(self.style.SUCCESS(f'  ✓ {message}'))
                self.stdout.write(self.style.SUCCESS('\n  Check your inbox!'))
            else:
                self.stdout.write(self.style.ERROR(f'  ✗ {message}'))
                raise CommandError('Failed to send test email')
        elif check_only:
            self.stdout.write('\n' + self.style.WARNING('  ⓘ Skipping test email (--check-only specified)'))
        else:
            self.stdout.write('\n' + self.style.WARNING('  ⓘ No recipient specified - skipping test email'))
            self.stdout.write('     Usage: python manage.py test_email <email@example.com>')

        self.stdout.write('\n' + self.style.SUCCESS('=== Email Configuration Test Complete ===\n'))
