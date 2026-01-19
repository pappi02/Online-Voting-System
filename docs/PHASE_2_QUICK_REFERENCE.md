# Phase 2 Implementation Quick Reference

## File Structure

```
/backend/accounts/
├── voter_models.py              # 4 voter-related models
├── voter_serializers.py         # 6+ API serializers
├── voter_views.py               # 6+ viewset classes
├── email_config.py              # Email utilities & configuration
├── notification_service.py      # NotificationService class
├── signals.py                   # Django signals for automation
├── admin.py                     # 5 admin classes (updated)
├── models.py                    # NotificationLog model (added)
├── apps.py                      # Signal registration (updated)
└── migrations/
    ├── 0002_*.py               # Phase 2.1-2.4 models
    └── 0003_notificationlog.py # Phase 2.5 model

/backend/templates/emails/
├── voter_registration_confirmation.html
├── document_upload_confirmation.html
├── document_verification_pending.html
├── document_verified.html
├── document_rejected.html
├── voter_eligible.html
├── voter_ineligible.html
├── voter_approved.html
├── voter_rejected.html
└── verification_deadline_reminder.html

/backend/ivs_backend/
└── settings.py                 # Email configuration (updated)

/docs/
├── PHASE_2_COMPLETE.md
├── PHASE_2_5_NOTIFICATIONS_COMPLETE.md
└── PHASE_2_SUMMARY.md
```

## Key Classes & Models

### VoterProfile
```python
class VoterProfile(models.Model):
    user = OneToOneField(User)  # Link to user account
    date_of_birth = DateField()
    gender = CharField(choices=[...])
    address_fields = CharField()  # Multiple address fields
    occupation = CharField()
    verification_status = CharField(choices=[pending, under_review, verified, rejected, suspended])
    is_eligible = BooleanField()
    ineligibility_reason = TextField()
    verified_by = ForeignKey(User, null=True)
    verified_at = DateTimeField(null=True)
```

### VoterDocument
```python
class VoterDocument(models.Model):
    voter = ForeignKey(VoterProfile)
    document_type = CharField(choices=[national_id, passport, driver_license, other])
    document_number = CharField()
    issuing_country = CharField()
    issue_date = DateField()
    expiry_date = DateField()
    document_file = FileField()
    file_size = IntegerField()
    verification_status = CharField(choices=[pending, verified, rejected, expired])
    verification_notes = TextField()
    verified_by = ForeignKey(User, null=True)
    verified_at = DateTimeField(null=True)
    # Unique constraint: (voter_id, document_type)
```

### NotificationLog
```python
class NotificationLog(models.Model):
    user = ForeignKey(User)
    notification_type = CharField(choices=[...10 types...])
    recipient_email = EmailField()
    subject = CharField()
    status = CharField(choices=[sent, failed, pending])
    sent_at = DateTimeField(null=True)
    created_at = DateTimeField(auto_now_add=True)
    error_message = TextField(null=True)
    
    def mark_sent(self): ...
    def mark_failed(self, error): ...
```

## API Usage Examples

### Register New Voter
```python
POST /voter/register/
{
    "email": "voter@example.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "1990-01-15",
    "gender": "M",
    "street_address": "123 Main St",
    "city": "Springfield",
    "state_province": "IL",
    "postal_code": "62701",
    "country": "USA"
}
```

### Upload Document
```python
POST /voter/documents/
Content-Type: multipart/form-data

document_type: national_id
document_number: ABC123456789
issuing_country: USA
issue_date: 2015-05-10
expiry_date: 2035-05-10
document_file: [binary file]
```

### Check Eligibility
```python
GET /voter/profile/check_eligibility/
# Returns eligibility status and any issues
```

### Admin: Approve Voter
```python
POST /verification/approve_voter/
{
    "voter_id": "uuid-here",
    "notes": "Profile verified successfully"
}
```

### Get Notification History
```python
GET /verification-logs/?voter_id=uuid-here
```

## Django Admin URLs

| URL | Purpose |
|-----|---------|
| `/admin/accounts/user/` | User management |
| `/admin/accounts/voterprofile/` | Voter profiles & eligibility |
| `/admin/accounts/voterdocument/` | Document verification workflow |
| `/admin/accounts/eligibilityrule/` | Eligibility rule management |
| `/admin/accounts/verificationlog/` | Verification audit trail |
| `/admin/accounts/notificationlog/` | Email notification history |

## Notification Service Usage

### Send Email (Manual)
```python
from accounts.notification_service import NotificationService

NotificationService.send_voter_eligible(user=user_obj)
NotificationService.send_document_verified(
    user=voter_user,
    document_type='national_id',
    verified_by=admin_user.get_full_name()
)
```

### Check Notification History
```python
from accounts.notification_service import NotificationService

history = NotificationService.get_notification_history(
    user=voter_user,
    notification_type='document_verified',
    limit=10
)
```

## Settings Configuration

### Email Backend
```python
# Development (Console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Production (Gmail)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

### Voter Settings
```python
VOTER_MIN_AGE = 18
EMAIL_VERIFICATION_DEADLINE_DAYS = 14
EMAIL_REMINDER_DAYS_BEFORE = 7
```

## Database Queries

### Find Pending Voters
```python
from accounts.voter_models import VoterProfile

pending = VoterProfile.objects.filter(
    verification_status='pending'
).select_related('user', 'verified_by')
```

### Check Document Status
```python
from accounts.voter_models import VoterDocument

documents = VoterDocument.objects.filter(
    voter=profile,
    verification_status='pending'
).order_by('-uploaded_at')
```

### Get Notification Failures
```python
from accounts.models import NotificationLog

failed = NotificationLog.objects.filter(
    status='failed',
    created_at__gte=timezone.now() - timedelta(days=1)
)
```

## Signal Integration

### Automatic Notifications
```python
# When user registers - voter_registration_confirmation sent automatically
user = User.objects.create_user(email='new@example.com', password='pass')

# When document uploaded - document_upload_confirmation sent automatically
VoterDocument.objects.create(voter=profile, ...)

# When document verified - document_verified sent automatically
doc.verification_status = 'verified'
doc.save(update_fields=['verification_status'])
```

### Manual Trigger
```python
from accounts.signals import send_voter_approval_notification

send_voter_approval_notification(
    voter_profile=profile,
    approved=True,
    approved_by=admin_user
)
```

## Testing Checklist

- [ ] Test voter registration endpoint
- [ ] Test document upload with file validation
- [ ] Test eligibility checking
- [ ] Test admin approval/rejection workflow
- [ ] Test email notifications (check console/inbox)
- [ ] Test notification log tracking
- [ ] Verify database integrity
- [ ] Check admin interface functionality
- [ ] Test permission restrictions (IsAuthenticated, IsAdmin)
- [ ] Validate error handling

## Common Issues & Solutions

### Email Not Sending
**Issue**: Emails not being sent in production
**Solution**: 
- Check EMAIL_BACKEND setting
- Verify SMTP credentials
- Check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD
- Look at NotificationLog table for failed records

### Document Upload Fails
**Issue**: File upload returns 400 error
**Solution**:
- Check file size (max 5MB)
- Verify file type (PDF, JPG, PNG only)
- Ensure document_file field in request body

### Signals Not Firing
**Issue**: Notifications not triggered after actions
**Solution**:
- Verify signals.py imported in apps.py ready()
- Check AccountsConfig.ready() is calling import
- Ensure signal decorators are correct

## Next Steps: Phase 3

Phase 3 will implement:
1. Election model and admin
2. Candidate registration
3. Election scheduling
4. Ballot generation
5. Election state management

The voter registration/verification foundation is now complete and ready to support election features.
