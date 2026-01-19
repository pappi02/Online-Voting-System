# iVote Systems - Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### Prerequisites
- Python 3.12+
- pip & virtualenv
- Git

### Step 1: Clone & Setup Environment

```bash
# Navigate to project
cd /workspaces/Online-Voting-System

# Activate virtual environment (already created)
source .venv/bin/activate

# Install dependencies (if needed)
cd backend
pip install -r requirements.txt
```

### Step 2: Database Setup

```bash
# Run migrations (already done)
python manage.py migrate

# Create superuser (already created)
python create_superuser.py
```

**Superuser Credentials:**
- Email: `admin@ivotesystems.com`
- Password: `Admin@12345`

### Step 3: Start Development Server

```bash
# Start Django server
python manage.py runserver
```

Server will start at: **http://localhost:8000**

### Step 4: Test the API

Open a new terminal:

```bash
cd backend
python test_api.py
```

---

## 📚 API Endpoints

### Base URL
```
http://localhost:8000/api/v1/accounts
```

### Authentication

#### 1. Register User
```bash
POST /auth/register/
Content-Type: application/json

{
  "email": "voter@example.com",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+254712345678",
  "national_id": "12345678",
  "institution": "University of Tech",
  "department": "Computer Science"
}
```

#### 2. Login
```bash
POST /auth/login/
Content-Type: application/json

{
  "email": "admin@ivotesystems.com",
  "password": "Admin@12345"
}
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

#### 3. Refresh Token
```bash
POST /auth/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Profile Management

#### 4. Get Profile
```bash
GET /profile/me/
Authorization: Bearer <access_token>
```

#### 5. Update Profile
```bash
PATCH /profile/update_profile/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "first_name": "John",
  "last_name": "Smith",
  "phone_number": "+254712345678"
}
```

#### 6. Change Password
```bash
POST /profile/change_password/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "old_password": "OldPass123!",
  "new_password": "NewPass123!",
  "new_password_confirm": "NewPass123!"
}
```

### OTP Verification

#### 7. Send OTP
```bash
POST /otp/send/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "method": "email",
  "purpose": "login"
}
```

#### 8. Verify OTP
```bash
POST /otp/verify/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "otp_code": "123456",
  "purpose": "login"
}
```

### Multi-Factor Authentication

#### 9. Enable MFA
```bash
POST /profile/enable_mfa/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "method": "email"
}
```

#### 10. Disable MFA
```bash
POST /profile/disable_mfa/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "password": "YourPassword123!"
}
```

---

## 🔍 Testing with cURL

### Example: Login and Get Profile

```bash
# 1. Login to get token
curl -X POST http://localhost:8000/api/v1/accounts/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@ivotesystems.com",
    "password": "Admin@12345"
  }'

# 2. Use the access token from response
export TOKEN="<paste_access_token_here>"

# 3. Get profile
curl -X GET http://localhost:8000/api/v1/accounts/profile/me/ \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🎨 Admin Interface

Access Django Admin at: **http://localhost:8000/admin/**

Login with superuser credentials:
- Username: `admin@ivotesystems.com`
- Password: `Admin@12345`

**Features:**
- User management with beautiful badges
- OTP verification records
- Audit logs
- Advanced filtering and search

---

## 📖 API Documentation

Interactive API documentation available at:

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

---

## 🐛 Troubleshooting

### Server won't start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill process if needed
kill -9 <PID>

# Try a different port
python manage.py runserver 8001
```

### Database errors
```bash
# Delete database and start fresh
rm db.sqlite3
rm -rf accounts/migrations/0001_*

# Recreate migrations
python manage.py makemigrations
python manage.py migrate

# Recreate superuser
python create_superuser.py
```

### Module not found errors
```bash
# Ensure virtual environment is activated
source ../.venv/bin/activate

# Reinstall requirements
pip install -r requirements.txt
```

---

## 🔐 User Roles & Permissions

### Admin (`admin`)
- Full system access
- User management
- Election management
- View all audit logs

### Election Officer (`election_officer`)
- Create and manage elections
- View election results
- Manage candidates
- Cannot manage users

### Voter (`voter`)
- Participate in elections
- View own profile
- Update profile information
- View own audit logs

### Observer (`observer`)
- Read-only access
- View elections and results
- Cannot vote
- Cannot modify data

---

## 📊 User Status Flow

```
Registration → Pending → Admin Review → Approved
                                      ↓
                                   Rejected
                                      ↓
                                   Blocked (for violations)
```

**Statuses:**
- `pending` - Just registered, awaiting admin approval
- `approved` - Active, can use system
- `rejected` - Application denied
- `blocked` - Account suspended
- `inactive` - Dormant account

---

## 🔒 Security Features

### Implemented
✅ JWT authentication with 15-min tokens  
✅ Account lockout after 5 failed attempts  
✅ OTP two-factor authentication  
✅ Rate limiting on OTP requests  
✅ Password strength validation (12+ chars)  
✅ Audit logging for all actions  
✅ CORS and CSRF protection  

### In Development
🔄 Password reset via email  
🔄 SMS OTP delivery  
🔄 Session timeout management  

---

## 📝 Example User Registration Flow

1. User submits registration form
2. Account created with `status=pending`
3. Email verification sent
4. Admin reviews and approves
5. User can now login
6. OTP sent on first login (if MFA enabled)
7. User verifies OTP
8. Access granted

---

## 🎯 Next Steps

After testing Phase 1, proceed with:

1. **Frontend Development** (Phase 2)
   - React app setup
   - Login/Register pages
   - User dashboard

2. **Election Management** (Phase 3)
   - Election CRUD operations
   - Candidate management
   - Voting periods

3. **Voting System** (Phase 4)
   - Cast vote functionality
   - Cryptographic ballot handling
   - Result tallying

---

## 📞 Support

For issues or questions:
- Check [PHASE_1_COMPLETE.md](PHASE_1_COMPLETE.md) for detailed docs
- Review [PHASE_1_IMPLEMENTATION_GUIDE.md](PHASE_1_IMPLEMENTATION_GUIDE.md)
- Check audit logs in Django admin

---

**Happy Coding! 🚀**
