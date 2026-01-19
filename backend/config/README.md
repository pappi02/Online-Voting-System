# Email Configuration Directory

This directory contains email-related configuration files for the Online Voting System.

## Files

### `.env.email`
**Status:** 🔒 Confidential - NOT committed to version control

Contains actual email credentials and configuration. Create this file by copying `.env.email.example` and filling in your credentials.

```bash
cp .env.email.example .env.email
# Edit .env.email with your credentials
```

### `.env.email.example`
**Status:** ✅ Template - Safe to commit

Example email configuration file showing all available options. Use this as a template to create your `.env.email` file.

### `email_loader.py`
**Status:** ✅ Code - Safe to commit

Python module that loads email configuration from `.env.email` and provides it to Django settings.

**Functions:**
- `get_email_settings()` - Returns complete email configuration
- `get_email_provider()` - Returns configured provider name
- `validate_email_config()` - Validates configuration
- `test_email_connection()` - Tests SMTP connection

### `.gitignore`
**Status:** ✅ Protection - Safe to commit

Ensures sensitive credential files are never committed to version control.

## Quick Start

### Option 1: Interactive Setup (Recommended)
```bash
cd /workspaces/Online-Voting-System/backend
python manage.py configure_email
```

### Option 2: Manual Setup
```bash
# Copy example file
cp .env.email.example .env.email

# Edit with your credentials
nano .env.email

# Test configuration
python manage.py test_email --check-only

# Send test email
python manage.py test_email your-email@example.com
```

## Supported Providers

- **Gmail** - Recommended for development
- **Outlook/Office 365** - Microsoft email
- **SendGrid** - Recommended for production
- **Mailgun** - Alternative production option
- **Custom SMTP** - Any SMTP provider
- **Console** - Development only (no real emails)

## Security Notes

⚠️ **NEVER commit `.env.email` to version control**

✅ The `.gitignore` file protects this directory

✅ All credential files are excluded from git

✅ Use environment variables in production

## Documentation

Full documentation available in:
- `/docs/EMAIL_CONFIGURATION.md` - Complete email setup guide
- `/docs/QUICKSTART.md` - Quick start guide

## Support

For help with email configuration:
1. Read `/docs/EMAIL_CONFIGURATION.md`
2. Run `python manage.py test_email --check-only`
3. Check logs: `tail -f logs/django.log`
4. Contact: support@ivotesystems.com
