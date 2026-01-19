# Email System Architecture

## Overview Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Email Configuration Flow                      │
└─────────────────────────────────────────────────────────────────┘

1. Configuration Setup
   ┌──────────────────────────────────────────────┐
   │  python manage.py configure_email            │
   │  (Interactive Wizard)                        │
   └────────────────┬─────────────────────────────┘
                    │
                    ▼
   ┌──────────────────────────────────────────────┐
   │  config/.env.email (Credentials File)        │
   │  • EMAIL_PROVIDER=gmail                      │
   │  • GMAIL_EMAIL_HOST_USER=...                 │
   │  • GMAIL_EMAIL_HOST_PASSWORD=...             │
   │  • DEFAULT_FROM_EMAIL=...                    │
   └────────────────┬─────────────────────────────┘
                    │
                    ▼

2. Configuration Loading
   ┌──────────────────────────────────────────────┐
   │  config/email_loader.py                      │
   │  • get_email_settings()                      │
   │  • validate_email_config()                   │
   │  • test_email_connection()                   │
   └────────────────┬─────────────────────────────┘
                    │
                    ▼
   ┌──────────────────────────────────────────────┐
   │  ivs_backend/settings.py                     │
   │  • EMAIL_BACKEND                             │
   │  • EMAIL_HOST                                │
   │  • EMAIL_PORT                                │
   │  • EMAIL_HOST_USER                           │
   └────────────────┬─────────────────────────────┘
                    │
                    ▼

3. Email Sending
   ┌──────────────────────────────────────────────┐
   │  accounts/email_config.py                    │
   │  • send_html_email()                         │
   │  • send_notification_email()                 │
   │  • Retry logic                               │
   │  • Validation                                │
   └────────────────┬─────────────────────────────┘
                    │
                    ▼
   ┌──────────────────────────────────────────────┐
   │  accounts/notification_service.py            │
   │  • send_registration_confirmation()          │
   │  • send_document_verified()                  │
   │  • _log_notification()                       │
   └────────────────┬─────────────────────────────┘
                    │
                    ▼
   ┌──────────────────────────────────────────────┐
   │  SMTP Provider (Gmail/SendGrid/etc.)         │
   │  → Email delivered to recipient              │
   └──────────────────────────────────────────────┘
```

## Provider Support Matrix

```
┌──────────────┬────────────┬───────────┬──────────────┬─────────────┐
│   Provider   │ Development│ Production│   Port/TLS   │ Setup Time  │
├──────────────┼────────────┼───────────┼──────────────┼─────────────┤
│   Console    │     ✅     │     ❌    │     N/A      │   Instant   │
│   Gmail      │     ✅     │     ⚠️    │  587 / TLS   │  5 minutes  │
│   Outlook    │     ✅     │     ⚠️    │  587 / TLS   │  5 minutes  │
│  SendGrid    │     ✅     │     ✅    │  587 / TLS   │  10 minutes │
│  Mailgun     │     ✅     │     ✅    │  587 / TLS   │  10 minutes │
│   Custom     │     ✅     │     ✅    │  Custom      │  Varies     │
└──────────────┴────────────┴───────────┴──────────────┴─────────────┘

Legend:
✅ Recommended    ⚠️ Limited (rate limits)    ❌ Not suitable
```

## Email Flow Sequence

```
User Action → Notification Service → Email Config → SMTP Provider → Recipient

Example: Voter Registration Flow

┌──────────┐     ┌──────────────┐     ┌────────────┐     ┌──────────┐
│  Voter   │────▶│   Django     │────▶│   Email    │────▶│  Gmail   │
│ Registers│     │   Backend    │     │   System   │     │   SMTP   │
└──────────┘     └──────────────┘     └────────────┘     └──────────┘
                        │                     │                 │
                        │ 1. Create User      │                 │
                        │ 2. Generate Token   │                 │
                        │                     │                 │
                        ▼                     │                 │
              notification_service            │                 │
                  .send_registration_         │                 │
                   confirmation(user)         │                 │
                        │                     │                 │
                        ▼                     │                 │
                  send_notification_email     │                 │
                   (user, 'voter_reg...', )   │                 │
                        │                     │                 │
                        ├────────────────────▶│                 │
                        │  Template Context   │                 │
                        │  User Data         │                 │
                        │                     │                 │
                        │                     ▼                 │
                        │           Render HTML Template       │
                        │           Validate Email             │
                        │           Apply Retry Logic          │
                        │                     │                 │
                        │                     ├────────────────▶│
                        │                     │  SMTP Send      │
                        │                     │                 │
                        │◀────────────────────┤                 │
                        │    Success/Error    │                 │
                        │                     │                 ▼
                        ▼                     │           ┌──────────┐
                  Log Notification           │           │  Voter   │
                  Return Success             │           │  Inbox   │
                                             │           └──────────┘
```

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────┐
│                   Email Send Attempt                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  Validate Email?     │
          └──────┬───────────────┘
                 │
         Yes ────┤──── No → Return (False, "Invalid email")
                 │
                 ▼
          ┌──────────────────────┐
          │  Attempt Send        │
          │  (Try 1 of 3)        │
          └──────┬───────────────┘
                 │
         Success ┤ Failure
                 │     │
                 │     ▼
                 │  ┌──────────────────┐
                 │  │  Wait 5 seconds  │
                 │  └────┬─────────────┘
                 │       │
                 │       ▼
                 │  ┌──────────────────┐
                 │  │  Attempt Send    │
                 │  │  (Try 2 of 3)    │
                 │  └────┬─────────────┘
                 │       │
                 │Success┤ Failure
                 │       │     │
                 │       │     ▼
                 │       │  (Retry 3...)
                 │       │
                 ▼       ▼
          ┌──────────────────────┐
          │  Log Result          │
          │  Update Database     │
          │  Return Status       │
          └──────────────────────┘
```

## Component Interaction

```
┌────────────────────────────────────────────────────────────┐
│                     Component Layers                        │
└────────────────────────────────────────────────────────────┘

Layer 1: Configuration
   ┌────────────────────────────────────┐
   │  config/.env.email                 │  ← User Credentials
   └────────────────┬───────────────────┘
                    │
Layer 2: Loader
   ┌────────────────▼───────────────────┐
   │  config/email_loader.py            │  ← Validation & Loading
   └────────────────┬───────────────────┘
                    │
Layer 3: Settings
   ┌────────────────▼───────────────────┐
   │  ivs_backend/settings.py           │  ← Django Config
   └────────────────┬───────────────────┘
                    │
Layer 4: Email Utilities
   ┌────────────────▼───────────────────┐
   │  accounts/email_config.py          │  ← Send Functions
   └────────────────┬───────────────────┘
                    │
Layer 5: Business Logic
   ┌────────────────▼───────────────────┐
   │  accounts/notification_service.py  │  ← App Logic
   └────────────────┬───────────────────┘
                    │
Layer 6: Views/API
   ┌────────────────▼───────────────────┐
   │  accounts/views.py                 │  ← API Endpoints
   │  accounts/voter_views.py           │
   └────────────────────────────────────┘
```

## Testing Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Testing Layers                        │
└─────────────────────────────────────────────────────────┘

Unit Tests
   ├── config/tests.py
   │   ├── EmailLoaderTest
   │   ├── EmailConfigTest
   │   └── ValidationTest
   │
   └── accounts/test_email.py (if created)
       ├── EmailSendingTest
       ├── NotificationServiceTest
       └── RetryLogicTest

Management Commands
   ├── python manage.py test_email
   │   ├── Configuration validation
   │   ├── Connection testing
   │   └── Test email sending
   │
   └── python manage.py configure_email
       └── Interactive configuration

Integration Tests
   └── Full email flow testing
       ├── User registration → Email sent
       ├── Document verification → Email sent
       └── Election notification → Email sent
```

## Deployment Architecture

```
Development Environment
┌─────────────────────────────────────┐
│  Developer Machine                  │
│  ├── Console Backend               │
│  │   └── Prints to terminal        │
│  └── config/.env.email              │
│      └── EMAIL_DEVELOPMENT_MODE=True│
└─────────────────────────────────────┘

Staging Environment
┌─────────────────────────────────────┐
│  Staging Server                     │
│  ├── Gmail SMTP                     │
│  │   └── Limited sending           │
│  └── config/.env.email              │
│      └── EMAIL_PROVIDER=gmail      │
└─────────────────────────────────────┘

Production Environment
┌─────────────────────────────────────┐
│  Production Server                  │
│  ├── SendGrid/Mailgun              │
│  │   ├── High deliverability       │
│  │   ├── Analytics dashboard       │
│  │   └── IP reputation management  │
│  └── Environment Variables          │
│      └── Loaded from secrets mgmt  │
└─────────────────────────────────────┘
```

## Security Model

```
┌─────────────────────────────────────────────────────────┐
│                    Security Layers                       │
└─────────────────────────────────────────────────────────┘

Layer 1: File System
   ├── config/.env.email          (File permissions: 600)
   ├── .gitignore                 (Excludes credentials)
   └── config/.gitignore          (Double protection)

Layer 2: Configuration
   ├── Provider-specific settings
   ├── TLS/SSL enforcement
   └── Timeout settings

Layer 3: Application
   ├── Email validation
   ├── Rate limiting
   ├── Retry logic
   └── Error logging (sanitized)

Layer 4: Transport
   ├── TLS 1.2+
   ├── SMTP authentication
   └── Encrypted connections

Layer 5: Provider
   ├── SPF records
   ├── DKIM signing
   ├── DMARC policies
   └── Bounce handling
```

---

**Diagram Version:** 1.0  
**Last Updated:** January 15, 2026  
**Format:** ASCII Art + Markdown
