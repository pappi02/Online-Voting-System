# Email Configuration Guide

## Overview

The Online Voting System uses a sophisticated email configuration system that supports multiple email providers and environments. All email credentials are stored in a separate configuration folder for better security and organization.

## Directory Structure

```
backend/
├── config/                           # Email configuration directory
│   ├── __init__.py                  # Package init
│   ├── email_loader.py              # Email configuration loader
│   ├── .env.email                   # Email credentials (DO NOT COMMIT)
│   ├── .env.email.example           # Email credentials template
│   └── .gitignore                   # Protects credentials from git
├── accounts/
│   ├── email_config.py              # Email sending utilities
│   ├── notification_service.py      # Notification management
│   └── management/
│       └── commands/
│           ├── test_email.py        # Test email configuration
│           └── configure_email.py   # Interactive email setup
└── templates/
    └── emails/                      # Email templates
        ├── voter_registration_confirmation.html
        ├── document_verified.html
        └── ...
```

## Supported Email Providers

### 1. **Gmail** (Recommended for Development)
- **Host**: smtp.gmail.com
- **Port**: 587
- **TLS**: Yes
- **Requirements**: App Password (not regular password)
- **Setup Guide**: https://myaccount.google.com/apppasswords

### 2. **Outlook/Office 365**
- **Host**: smtp-mail.outlook.com
- **Port**: 587
- **TLS**: Yes
- **Requirements**: Regular account password

### 3. **SendGrid** (Recommended for Production)
- **Host**: smtp.sendgrid.net
- **Port**: 587
- **TLS**: Yes
- **Requirements**: SendGrid API Key
- **Benefits**: High deliverability, analytics, IP warming

### 4. **Mailgun**
- **Host**: smtp.mailgun.org
- **Port**: 587
- **TLS**: Yes
- **Requirements**: Mailgun credentials

### 5. **Custom SMTP**
- Configure any SMTP provider
- Supports TLS/SSL
- Flexible configuration

### 6. **Console Backend** (Development Only)
- Prints emails to console
- No real emails sent
- Perfect for development

## Quick Setup

### Method 1: Interactive Configuration (Recommended)

```bash
# Run interactive setup wizard
python manage.py configure_email

# Follow the prompts to:
# 1. Select email provider
# 2. Enter credentials
# 3. Configure settings
```

### Method 2: Manual Configuration

1. **Copy the example file:**
   ```bash
   cp config/.env.email.example config/.env.email
   ```

2. **Edit config/.env.email:**
   ```env
   # Choose your provider
   EMAIL_PROVIDER=gmail
   
   # Gmail credentials
   GMAIL_EMAIL_HOST=smtp.gmail.com
   GMAIL_EMAIL_PORT=587
   GMAIL_EMAIL_USE_TLS=True
   GMAIL_EMAIL_HOST_USER=your-email@gmail.com
   GMAIL_EMAIL_HOST_PASSWORD=your-app-password
   
   # Email addresses
   DEFAULT_FROM_EMAIL=noreply@ivotesystems.com
   SUPPORT_EMAIL=support@ivotesystems.com
   
   # Features
   EMAIL_DEVELOPMENT_MODE=False
   EMAIL_NOTIFICATION_ENABLED=True
   ```

3. **Test your configuration:**
   ```bash
   python manage.py test_email your-email@example.com
   ```

## Configuration Details

### Email Provider Settings

#### Gmail Configuration
```env
EMAIL_PROVIDER=gmail
GMAIL_EMAIL_HOST=smtp.gmail.com
GMAIL_EMAIL_PORT=587
GMAIL_EMAIL_USE_TLS=True
GMAIL_EMAIL_HOST_USER=your-email@gmail.com
GMAIL_EMAIL_HOST_PASSWORD=your-16-char-app-password
```

**Getting Gmail App Password:**
1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" and your device
3. Copy the 16-character password
4. Use this instead of your regular password

#### SendGrid Configuration (Production)
```env
EMAIL_PROVIDER=sendgrid
SENDGRID_EMAIL_HOST=smtp.sendgrid.net
SENDGRID_EMAIL_PORT=587
SENDGRID_EMAIL_USE_TLS=True
SENDGRID_EMAIL_HOST_USER=apikey
SENDGRID_EMAIL_HOST_PASSWORD=SG.your_sendgrid_api_key
```

### Email Features

```env
# Enable/disable email notifications
EMAIL_NOTIFICATION_ENABLED=True

# Require email verification for voters
EMAIL_VERIFICATION_REQUIRED=True

# Days until verification deadline
EMAIL_VERIFICATION_DEADLINE_DAYS=14

# Days before deadline to send reminder
EMAIL_REMINDER_DAYS_BEFORE=7

# Development mode (uses console backend)
EMAIL_DEVELOPMENT_MODE=False
```

## Testing Email Configuration

### Basic Test
```bash
# Check configuration validity
python manage.py test_email --check-only
```

### Send Test Email
```bash
# Send test email to verify it works
python manage.py test_email your-email@example.com
```

### Output Example
```
=== Email Configuration Test ===

Current Email Configuration:
  Backend: django.core.mail.backends.smtp.EmailBackend
  Provider: gmail
  Host: smtp.gmail.com
  Port: 587
  User: noreply@ivotesystems.com
  From Email: noreply@ivotesystems.com

Validating Configuration:
  ✓ Email configuration is valid

Testing Connection:
  ✓ Email connection successful

Sending Test Email to user@example.com:
  ✓ Test email sent successfully to user@example.com
  Check your inbox!

=== Email Configuration Test Complete ===
```

## Email Templates

All email templates are in `backend/templates/emails/`:

### Available Templates

1. **voter_registration_confirmation.html**
   - Sent when user registers
   - Contains welcome message and verification link

2. **document_upload_confirmation.html**
   - Sent when voter uploads document
   - Confirms receipt and next steps

3. **document_verified.html**
   - Sent when document is approved
   - Notifies voter of eligibility

4. **document_rejected.html**
   - Sent when document is rejected
   - Explains reason and how to resubmit

5. **voter_eligible.html**
   - Sent when voter becomes eligible
   - Explains voting rights

6. **voter_approved.html**
   - Sent when registration is approved
   - Contains important voting information

7. **verification_deadline_reminder.html**
   - Sent before deadline expires
   - Urges completion of verification

### Template Context Variables

All templates have access to:
- `site_name`: "Online Voting System"
- `site_url`: System URL
- `support_email`: Support contact
- `user_first_name`: Recipient's first name
- `user_email`: Recipient's email

## Programmatic Usage

### Sending Notification Emails

```python
from accounts.email_config import send_notification_email

# Send registration confirmation
success, error = send_notification_email(
    user=user,
    notification_type='voter_registration_confirmation'
)

if success:
    print("Email sent successfully")
else:
    print(f"Failed to send email: {error}")
```

### Sending Custom Emails

```python
from accounts.email_config import send_html_email

context = {
    'site_name': 'iVote Systems',
    'site_url': 'https://ivoting.com',
    'support_email': 'support@ivoting.com',
    'custom_data': 'Hello World'
}

success, error = send_html_email(
    recipient_email='user@example.com',
    subject='Custom Email Subject',
    template_name='emails/custom_template.html',
    context=context
)
```

### Testing Email Connection

```python
from accounts.email_config import test_email_configuration

success, message = test_email_configuration()
print(message)
```

## Security Best Practices

### 1. **Credential Protection**
- ✅ Store credentials in `config/.env.email`
- ✅ Never commit `.env.email` to git
- ✅ Use `.env.email.example` for documentation
- ✅ Use environment variables in production

### 2. **Email Provider Security**
- ✅ Use App Passwords for Gmail (not regular password)
- ✅ Use API keys for SendGrid/Mailgun
- ✅ Enable 2FA on email accounts
- ✅ Rotate credentials regularly

### 3. **Rate Limiting**
- ✅ Implement sending limits
- ✅ Use queues for bulk emails
- ✅ Monitor sending patterns

### 4. **Production Deployment**
```env
# Use professional email provider
EMAIL_PROVIDER=sendgrid

# Disable development mode
EMAIL_DEVELOPMENT_MODE=False

# Use verified domain
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

## Troubleshooting

### Issue: Authentication Failed

**Solution:**
1. Gmail: Use App Password, not regular password
2. Verify credentials are correct
3. Check if 2FA is enabled
4. Test with `python manage.py test_email --check-only`

### Issue: Connection Timeout

**Solution:**
1. Check firewall/network settings
2. Verify port 587 is open
3. Try port 465 with SSL
4. Check if ISP blocks SMTP

### Issue: Emails Not Received

**Solution:**
1. Check spam/junk folder
2. Verify recipient email is correct
3. Check email logs: `tail -f logs/django.log`
4. Verify sender domain reputation

### Issue: "Console Backend" in Production

**Solution:**
```env
# Change in config/.env.email
EMAIL_DEVELOPMENT_MODE=False
```

## Migration from Old Configuration

### Old Way (settings.py)
```python
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'exposed@credentials.com'  # Insecure!
```

### New Way (config/.env.email)
```env
EMAIL_PROVIDER=gmail
GMAIL_EMAIL_HOST=smtp.gmail.com
GMAIL_EMAIL_HOST_USER=secure@credentials.com  # Protected!
```

**Migration Steps:**
1. Run `python manage.py configure_email`
2. Enter your existing credentials
3. Test with `python manage.py test_email`
4. Remove old email settings from `.env`

## API Reference

### Functions in `email_config.py`

#### `send_html_email(recipient_email, subject, template_name, context, from_email=None, max_retries=None)`
Send HTML email with retry logic.

**Returns:** `(success: bool, error_message: str)`

#### `send_notification_email(user, notification_type, context=None)`
Send predefined notification email.

**Returns:** `(success: bool, error_message: str)`

#### `test_email_configuration()`
Test SMTP connection.

**Returns:** `(success: bool, message: str)`

#### `send_test_email(recipient_email)`
Send test email to verify configuration.

**Returns:** `(success: bool, message: str)`

### Functions in `config/email_loader.py`

#### `get_email_settings()`
Get complete email configuration.

**Returns:** `dict` of email settings

#### `get_email_provider()`
Get configured email provider name.

**Returns:** `str` (gmail, outlook, sendgrid, etc.)

#### `validate_email_config()`
Validate email configuration.

**Returns:** `(is_valid: bool, message: str)`

## Support

### Need Help?

1. **Check logs:**
   ```bash
   tail -f logs/django.log
   ```

2. **Test configuration:**
   ```bash
   python manage.py test_email --check-only
   ```

3. **View example:**
   ```bash
   cat config/.env.email.example
   ```

4. **Contact support:**
   - Email: support@ivotesystems.com
   - Docs: /docs/EMAIL_CONFIGURATION.md

## Next Steps

1. ✅ Configure email provider
2. ✅ Test email sending
3. ✅ Customize email templates
4. ✅ Set up monitoring
5. ✅ Review security settings

---

**Last Updated:** January 15, 2026  
**Version:** 2.0  
**Author:** iVote Systems Team
