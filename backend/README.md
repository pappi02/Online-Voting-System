# iVote Systems - Backend API

**Django REST Framework powered secure voting backend**

---

## 📋 Overview

The iVS Backend is a production-ready Django application providing:
- Secure user authentication & authorization (JWT + OTP)
- Election management & voting operations
- Encrypted vote storage & cryptographic vote tallying
- Real-time updates via WebSocket
- Comprehensive audit logging
- Role-based access control

---

## 🚀 Quick Start

### Prerequisites
```bash
Python 3.10+
PostgreSQL 13+
pip (Python package manager)
```

### Installation

1. **Navigate to backend directory**
```bash
cd backend
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Setup environment**
```bash
cp .env.example .env
# Edit .env with your database credentials and settings
```

5. **Setup email configuration**
```bash
# Interactive setup (recommended)
python manage.py configure_email

# Or manual setup
cp config/.env.email.example config/.env.email
# Edit config/.env.email with your email credentials

# Test email configuration
python manage.py test_email --check-only
```

6. **Initialize database**
```bash
python manage.py migrate
python manage.py createsuperuser  # Create admin user
```

7. **Create test data (optional)**
```bash
python manage.py seed_data
```

8. **Run development server**
```bash
python manage.py runserver
```

The API will be available at: `http://localhost:8000`  
Swagger documentation: `http://localhost:8000/api/schema/swagger/`

---

## 📁 Project Structure

```
backend/
├── ivs_backend/              # Main Django project config
│   ├── settings.py          # Security & app configuration
│   ├── urls.py              # Main URL routing
│   ├── asgi.py              # WebSocket/Async config
│   └── wsgi.py              # Production WSGI
│
├── accounts/                # User Authentication
│   ├── models.py            # User, Role, Permission models
│   ├── views.py             # Auth views & viewsets
│   ├── serializers.py       # User serialization
│   ├── permissions.py       # Custom permission classes
│   └── urls.py              # Auth endpoints
│
├── elections/               # Election Management
│   ├── models.py            # Election, Candidate models
│   ├── views.py             # Election viewsets
│   ├── serializers.py       # Election serialization
│   └── urls.py              # Election endpoints
│
├── voting/                  # Vote Casting & Encryption
│   ├── models.py            # Vote, EncryptedVote models
│   ├── views.py             # Voting operations
│   ├── serializers.py       # Vote serialization
│   ├── encryption.py        # AES-256 encryption utils
│   ├── validators.py        # Vote validation logic
│   └── urls.py              # Voting endpoints
│
├── auditing/                # Audit Logging
│   ├── models.py            # AuditLog model
│   ├── views.py             # Audit log views
│   ├── serializers.py       # Audit log serialization
│   ├── middleware.py        # Request/response logging
│   └── urls.py              # Audit endpoints
│
├── manage.py                # Django CLI
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
└── README.md               # This file
```

---

## 🔑 API Endpoints Overview

### Authentication
```
POST   /api/auth/register/          Register new voter
POST   /api/auth/login/             Login with credentials
POST   /api/auth/verify-otp/        Verify OTP
POST   /api/auth/refresh-token/     Refresh JWT token
POST   /api/auth/logout/            Logout & invalidate token
GET    /api/auth/profile/           Get current user profile
```

### Elections
```
GET    /api/elections/              List all elections
GET    /api/elections/<id>/         Get election details
POST   /api/elections/              Create election (admin only)
PUT    /api/elections/<id>/         Update election (admin only)
DELETE /api/elections/<id>/         Delete election (admin only)
POST   /api/elections/<id>/activate/ Open voting
POST   /api/elections/<id>/close/   Close voting
GET    /api/elections/<id>/results/ Get election results
```

### Voting
```
GET    /api/voting/candidates/      List candidates
POST   /api/voting/vote/            Cast vote (encrypted)
GET    /api/voting/vote-status/     Check if user voted
GET    /api/voting/results/         Get live results (aggregated)
```

### Admin
```
GET    /api/admin/voters/           List all voters
POST   /api/admin/voters/<id>/approve/  Approve voter
POST   /api/admin/voters/<id>/reject/   Reject voter
GET    /api/admin/dashboard/        Admin statistics
GET    /api/admin/audit-logs/       View audit logs
```

---

## 🔐 Security Features

### Encryption
- **Votes**: AES-256 encryption at rest
- **Transport**: TLS 1.3 for all API calls
- **Sensitive data**: Encrypted in database

### Authentication
- **JWT**: Token-based authentication
- **OTP**: One-time password verification
- **MFA**: Multi-factor authentication support
- **Session**: Auto-logout after 15 minutes inactivity

### Authorization
- **RBAC**: Role-based access control (Admin, Voter, Observer)
- **Permissions**: Granular endpoint permissions
- **Audit**: All actions logged with user context

### Attack Prevention
- **Rate Limiting**: Prevent brute-force attacks
- **CSRF Protection**: Cross-site request forgery prevention
- **SQL Injection**: ORM-based queries prevent injection
- **XSS Protection**: Input sanitization & output encoding

---

## 📦 Key Dependencies

```
Django==4.2.x              # Web framework
djangorestframework==3.14.x # REST API
djangorestframework-simplejwt # JWT auth
django-filter==23.x        # Query filtering
django-cors-headers==4.x   # CORS support
django-cryptography==4.x   # Encryption
psycopg2-binary==2.9.x    # PostgreSQL driver
celery==5.3.x              # Async tasks
redis==5.x                 # Caching
python-decouple==3.x       # .env configuration
Pillow==10.x               # Image processing
```

---

## 🧪 Testing

### Run all tests
```bash
pytest -v
```

### Run specific test
```bash
pytest accounts/tests/test_auth.py::TestUserRegistration -v
```

### With coverage report
```bash
pytest --cov=. --cov-report=html
```

### Run specific test type
```bash
pytest -k "unit"      # Unit tests only
pytest -k "integration" # Integration tests only
```

---

## 📊 Database Schema

### Key Tables
- **auth_user**: User accounts with roles
- **elections_election**: Election configuration
- **elections_candidate**: Candidates for elections
- **voting_vote**: Encrypted votes (voter_id, election_id, encrypted_vote)
- **auditing_auditlog**: All system actions (append-only)

### ER Diagram
```
User (1) ──────── (∞) Vote
User (1) ──────── (∞) AuditLog
Election (1) ──────── (∞) Vote
Election (1) ──────── (∞) Candidate
Candidate (1) ──────── (∞) Vote
```

---

## ⚙️ Configuration

### Environment Variables

```env
# Django Settings
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=ivs_voting_db
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Email (for OTP)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# JWT
JWT_ACCESS_TOKEN_LIFETIME=900  # 15 minutes
JWT_REFRESH_TOKEN_LIFETIME=604800  # 7 days

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://yourdomain.com

# Encryption
ENCRYPTION_KEY=your-encryption-key-here
```

---

## 🚀 Deployment

### Production Checklist
- [ ] Set `DEBUG=False` in production
- [ ] Use strong `SECRET_KEY`
- [ ] Configure HTTPS/TLS
- [ ] Setup PostgreSQL with backups
- [ ] Configure Redis for caching/sessions
- [ ] Setup Celery for async tasks
- [ ] Configure email service (Gmail, SendGrid, etc.)
- [ ] Setup monitoring & logging
- [ ] Run security checks (bandit, safety)
- [ ] Load test with realistic traffic

### Docker Deployment
```bash
docker build -t ivs-backend .
docker run -p 8000:8000 --env-file .env ivs-backend
```

---

## 📚 Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8949)
- [OWASP Security Guidelines](https://owasp.org/)

---

## 🐛 Troubleshooting

### Port already in use
```bash
# Find process using port 8000
lsof -i :8000
# Kill process
kill -9 <PID>
```

### Database connection error
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Reset migrations
python manage.py migrate zero
python manage.py migrate
```

### Import errors
```bash
# Reinstall packages
pip install --force-reinstall -r requirements.txt
```

---

**Version**: 0.1.0  
**Last Updated**: January 15, 2026
