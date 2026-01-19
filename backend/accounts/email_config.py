"""
Email configuration and settings for voter notifications
Enhanced with retry logic, validation, and better error handling
"""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
import logging
import time

logger = logging.getLogger(__name__)

# Email configuration (loaded from settings)
EMAIL_BACKEND = getattr(settings, 'EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = getattr(settings, 'EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = getattr(settings, 'EMAIL_PORT', 587)
EMAIL_HOST_USER = getattr(settings, 'EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = getattr(settings, 'EMAIL_USE_TLS', True)
DEFAULT_FROM_EMAIL = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@ivotesystems.com')
DEFAULT_FROM_NAME = getattr(settings, 'DEFAULT_FROM_NAME', 'iVote Systems')

# Email retry configuration
EMAIL_MAX_RETRIES = getattr(settings, 'EMAIL_MAX_RETRIES', 3)
EMAIL_RETRY_DELAY = getattr(settings, 'EMAIL_RETRY_DELAY_SECONDS', 5)

# Email templates mapping
EMAIL_TEMPLATES = {
    'voter_registration_confirmation': {
        'subject': 'Welcome to Online Voting System - Email Verification',
        'template': 'emails/voter_registration_confirmation.html',
        'description': 'Sent to new voter after registration'
    },
    'document_upload_confirmation': {
        'subject': 'Document Upload Received',
        'template': 'emails/document_upload_confirmation.html',
        'description': 'Sent after document upload'
    },
    'document_verification_pending': {
        'subject': 'Your Document is Under Review',
        'template': 'emails/document_verification_pending.html',
        'description': 'Sent when document enters verification queue'
    },
    'document_verified': {
        'subject': 'Your Document Has Been Verified',
        'template': 'emails/document_verified.html',
        'description': 'Sent when document is verified'
    },
    'document_rejected': {
        'subject': 'Document Verification Unsuccessful',
        'template': 'emails/document_rejected.html',
        'description': 'Sent when document is rejected'
    },
    'voter_eligible': {
        'subject': 'You Are Eligible to Vote',
        'template': 'emails/voter_eligible.html',
        'description': 'Sent when voter becomes eligible'
    },
    'voter_ineligible': {
        'subject': 'Voter Eligibility Status Update',
        'template': 'emails/voter_ineligible.html',
        'description': 'Sent when voter is marked ineligible'
    },
    'voter_approved': {
        'subject': 'Your Voter Registration Has Been Approved',
        'template': 'emails/voter_approved.html',
        'description': 'Sent when voter registration is approved'
    },
    'voter_rejected': {
        'subject': 'Your Voter Registration Has Been Rejected',
        'template': 'emails/voter_rejected.html',
        'description': 'Sent when voter registration is rejected'
    },
    'verification_deadline_reminder': {
        'subject': 'Action Required: Complete Your Voter Verification',
        'template': 'emails/verification_deadline_reminder.html',
        'description': 'Sent as reminder for incomplete verification'
    },
}

# Email context defaults
def get_base_email_context(user):
    """Get base context data for all emails"""
    return {
        'site_name': 'Online Voting System',
        'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://voting.example.com',
        'support_email': settings.SUPPORT_EMAIL if hasattr(settings, 'SUPPORT_EMAIL') else 'support@voting.example.com',
        'user_first_name': user.first_name or user.email.split('@')[0],
        'user_email': user.email,
    }


def validate_email_address(email):
    """
    Validate email address format
    
    Args:
        email: Email address to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        validate_email(email)
        return True, None
    except ValidationError as e:
        return False, str(e)


def send_html_email(recipient_email, subject, template_name, context, from_email=None, max_retries=None):
    """
    Send HTML email with both text and HTML versions
    Enhanced with validation, retry logic, and better error handling
    
    Args:
        recipient_email: Email address of recipient
        subject: Email subject line
        template_name: Path to email template
        context: Dictionary of context variables for template
        from_email: Sender email (defaults to DEFAULT_FROM_EMAIL)
        max_retries: Maximum retry attempts (defaults to EMAIL_MAX_RETRIES)
    
    Returns:
        tuple: (success, error_message)
    """
    # Validate recipient email
    is_valid, error = validate_email_address(recipient_email)
    if not is_valid:
        logger.error(f"Invalid email address: {recipient_email} - {error}")
        return False, f"Invalid email address: {error}"
    
    max_retries = max_retries or EMAIL_MAX_RETRIES
    from_email = from_email or f"{DEFAULT_FROM_NAME} <{DEFAULT_FROM_EMAIL}>"
    
    for attempt in range(max_retries):
        try:
            # Render HTML template
            html_content = render_to_string(template_name, context)
            
            # Create plain text version
            plain_text = f"""
{subject}

This is an HTML email. Please view it in an email client that supports HTML.

Visit {context.get('site_url', 'https://ivotesystems.com')} for more information.

---
{context.get('site_name', 'iVote Systems')}
{context.get('support_email', 'support@ivotesystems.com')}
            """.strip()
            
            # Create email with HTML and text versions
            email = EmailMultiAlternatives(
                subject=subject,
                body=plain_text,
                from_email=from_email,
                to=[recipient_email],
                headers={
                    'X-Priority': '1',
                    'X-MSMail-Priority': 'High',
                    'Importance': 'High'
                }
            )
            email.attach_alternative(html_content, "text/html")
            
            # Send email
            email.send(fail_silently=False)
            
            logger.info(f"Email sent successfully to {recipient_email}: {subject}")
            return True, None
            
        except ConnectionError as e:
            logger.warning(f"Email connection error (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(EMAIL_RETRY_DELAY)
            else:
                logger.error(f"Failed to send email to {recipient_email} after {max_retries} attempts: {str(e)}")
                return False, f"Connection error: {str(e)}"
                
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
            return False, str(e)
    
    return False, "Maximum retry attempts exceeded"


def send_notification_email(user, notification_type, context=None):
    """
    Send notification email based on type
    Enhanced with validation and better error handling
    
    Args:
        user: User object
        notification_type: Key from EMAIL_TEMPLATES
        context: Additional context variables
    
    Returns:
        tuple: (success, error_message)
    """
    if notification_type not in EMAIL_TEMPLATES:
        error_msg = f"Unknown notification type: {notification_type}"
        logger.error(error_msg)
        return False, error_msg
    
    if not user.email:
        error_msg = f"User {user.id} has no email address"
        logger.error(error_msg)
        return False, error_msg
    
    template_config = EMAIL_TEMPLATES[notification_type]
    
    # Build context
    email_context = get_base_email_context(user)
    if context:
        email_context.update(context)
    
    # Send email
    success, error = send_html_email(
        recipient_email=user.email,
        subject=template_config['subject'],
        template_name=template_config['template'],
        context=email_context
    )
    
    return success, error


def test_email_configuration():
    """
    Test email configuration
    
    Returns:
        tuple: (success, message)
    """
    try:
        connection = get_connection()
        connection.open()
        connection.close()
        
        logger.info("Email configuration test successful")
        return True, "Email configuration is valid and connection successful"
        
    except Exception as e:
        logger.error(f"Email configuration test failed: {str(e)}")
        return False, f"Email configuration test failed: {str(e)}"


def send_test_email(recipient_email):
    """
    Send a test email to verify configuration
    
    Args:
        recipient_email: Email address to send test email to
    
    Returns:
        tuple: (success, message)
    """
    context = {
        'site_name': 'iVote Systems',
        'site_url': getattr(settings, 'SITE_URL', 'https://ivotesystems.com'),
        'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@ivotesystems.com'),
    }
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Test Email</title>
    </head>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>Email Configuration Test</h2>
        <p>This is a test email from {{ site_name }}.</p>
        <p>If you received this email, your email configuration is working correctly!</p>
        <hr>
        <p style="color: #666; font-size: 12px;">
            This is an automated test email from {{ site_name }}<br>
            Visit: <a href="{{ site_url }}">{{ site_url }}</a><br>
            Support: {{ support_email }}
        </p>
    </body>
    </html>
    """
    
    try:
        from django.template import Template, Context
        template = Template(html_content)
        rendered_html = template.render(Context(context))
        
        email = EmailMultiAlternatives(
            subject='Email Configuration Test - iVote Systems',
            body='This is a test email. Please view in HTML format.',
            from_email=f"{DEFAULT_FROM_NAME} <{DEFAULT_FROM_EMAIL}>",
            to=[recipient_email]
        )
        email.attach_alternative(rendered_html, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"Test email sent successfully to {recipient_email}")
        return True, f"Test email sent successfully to {recipient_email}"
        
    except Exception as e:
        logger.error(f"Failed to send test email: {str(e)}")
        return False, f"Failed to send test email: {str(e)}"
