# PHASE 1: AUTHENTICATION & SECURITY FOUNDATION
## Detailed Implementation Guide

**Timeline**: 2 weeks (Weeks 4-5)  
**Status**: Ready to Start  
**Date**: January 15, 2026

---

## 📋 Overview

Phase 1 builds the core authentication and security foundation that all other features depend on. This includes user management, JWT tokens, OTP verification, and role-based access control.

---

## 🎯 Objectives

1. ✅ Implement secure user authentication system
2. ✅ Add multi-factor authentication (OTP)
3. ✅ Enforce strong password policies
4. ✅ Implement JWT token management
5. ✅ Add rate limiting & brute-force protection
6. ✅ Create responsive login/register UI
7. ✅ Protect routes with permission guards

---

## 📌 Task Breakdown

### BACKEND TASKS

#### 1.1 Enhanced User Model with RBAC
**File**: `backend/accounts/models.py`

**Requirements**:
- Extend Django User with custom fields
- Add roles: Admin, Voter, Observer
- Add status: Pending, Verified, Approved, Rejected, Blocked
- Add security tracking: last_login, failed_attempts, locked_until
- Add audit fields: created_at, updated_at

**Key Fields**:
```python
User:
  - email (unique)
  - full_name
  - phone_number
  - id_number (institution ID)
  - role (choices: Admin, Voter, Observer)
  - status (choices: Pending, Verified, Approved, Rejected, Blocked)
  - is_active
  - is_verified_email
  - is_verified_phone
  - last_login
  - failed_login_attempts
  - locked_until
  - created_at
  - updated_at

Role (abstract):
  - permissions (M2M)
  - description

Permission (abstract):
  - codename
  - description
```

**Estimated Time**: 4 hours

---

#### 1.2 JWT Token Generation & Refresh
**File**: `backend/accounts/views.py` + `backend/accounts/serializers.py`

**Requirements**:
- Configure SimpleJWT with custom settings
- Create login endpoint (POST /auth/login/)
- Create token refresh endpoint (POST /auth/refresh/)
- Create logout endpoint (POST /auth/logout/)
- Implement token blacklist on logout

**Endpoints**:
```
POST /api/auth/login/
  Input: email, password, remember_me
  Output: access_token, refresh_token, user_data

POST /api/auth/refresh/
  Input: refresh_token
  Output: access_token

POST /api/auth/logout/
  Input: refresh_token
  Output: success message

GET /api/auth/profile/
  Output: current user profile
```

**Estimated Time**: 6 hours

---

#### 1.3 OTP Generation & Verification
**File**: `backend/accounts/models.py` + `backend/accounts/views.py`

**Requirements**:
- Create OTP model (code, email/phone, expires_at, used_at, attempts)
- Implement Twilio SMS or email-based OTP
- Create OTP generation endpoint (POST /auth/send-otp/)
- Create OTP verification endpoint (POST /auth/verify-otp/)
- Add resend logic with rate limiting (3 attempts per 5 minutes)

**OTP Model**:
```python
OTP:
  - user (FK)
  - code (6 digits)
  - method (email/sms)
  - expires_at
  - used_at
  - attempts (max 5)
  - created_at
```

**Estimated Time**: 5 hours

---

#### 1.4 Password Security (Argon2)
**File**: `backend/accounts/serializers.py` + settings

**Requirements**:
- Configure Argon2 password hashing
- Implement strong password validation
- Create password change endpoint (POST /auth/change-password/)
- Create password reset endpoint (POST /auth/reset-password/)
- Add password history (prevent reuse)

**Password Rules**:
- Minimum 12 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 digit
- At least 1 special character (@, #, $, %, etc.)

**Estimated Time**: 4 hours

---

#### 1.5 Rate Limiting & Brute-Force Protection
**File**: `backend/accounts/views.py` + middleware

**Requirements**:
- Implement rate limiting on auth endpoints (5 attempts per 15 minutes)
- Lock account after 5 failed login attempts (15-minute lockout)
- Add IP-based rate limiting
- Create blacklist for suspicious IPs
- Add CAPTCHA on repeated failed attempts

**Rules**:
- Login attempts: 5 per 15 minutes
- OTP verification: 5 per 5 minutes
- Password reset: 3 per hour
- IP block: After 10 failed attempts in 1 hour

**Estimated Time**: 5 hours

---

#### 1.6 Session Management & Timeout
**File**: `backend/ivs_backend/settings.py` + middleware

**Requirements**:
- Configure Redis for session store
- Implement 15-minute inactivity timeout
- Create session refresh logic
- Implement concurrent session limiting (1 per user)
- Add logout on password change

**Configuration**:
```python
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 900  # 15 minutes
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
```

**Estimated Time**: 4 hours

---

### FRONTEND TASKS

#### 1.7 Login & Register Pages
**Files**: `frontend/src/pages/LoginPage.tsx`, `frontend/src/pages/RegisterPage.tsx`

**Requirements**:
- Create LoginPage component with form validation
- Create RegisterPage with multi-step form
- Implement client-side form validation
- Add error handling & user feedback
- Add password strength indicator on register

**LoginPage**:
- Email input
- Password input
- Remember me checkbox
- Login button
- Forgot password link
- Register link

**RegisterPage** (Multi-step):
- Step 1: Personal Info (Full name, Email, Phone)
- Step 2: ID verification (Institution ID, Document upload)
- Step 3: Password setup (with strength indicator)
- Step 4: OTP verification
- Review & Confirm

**Estimated Time**: 8 hours

---

#### 1.8 OTP Verification Modal
**File**: `frontend/src/components/Auth/OTPModal.tsx`

**Requirements**:
- Create OTP input component (6 digit input)
- Implement auto-focus between inputs
- Add resend countdown timer (60 seconds)
- Add error handling for invalid OTP
- Show remaining attempts

**Features**:
- 6-digit input boxes (auto-advance)
- Resend button (disabled until timer expires)
- Error messages
- Success confirmation

**Estimated Time**: 4 hours

---

#### 1.9 JWT Token Storage & Auto-Refresh
**File**: `frontend/src/utils/tokenManager.ts` + `frontend/src/services/api.ts`

**Requirements**:
- Implement secure token storage (localStorage for now, httpOnly cookie later)
- Create axios interceptor for token refresh
- Auto-refresh access token before expiry
- Handle token expiry & redirect to login
- Persist refresh token securely

**Token Manager**:
```typescript
interface TokenData {
  access_token: string
  refresh_token: string
  expires_in: number
}

// Functions
- saveToken(tokenData)
- getAccessToken()
- getRefreshToken()
- isTokenExpired()
- clearTokens()
```

**Estimated Time**: 3 hours

---

#### 1.10 Protected Routes & Permission Guards
**File**: `frontend/src/components/PrivateRoute.tsx` + `frontend/src/hooks/useAuth.ts`

**Requirements**:
- Create PrivateRoute HOC for protected routes
- Implement role-based route access
- Create useAuth custom hook for auth state
- Add permission checking on components
- Implement route guards for admin/voter

**PrivateRoute**:
- Check authentication
- Check authorization (role-based)
- Redirect unauthorized users
- Show loading state

**Estimated Time**: 3 hours

---

## 📊 Implementation Timeline

```
Week 4 (Jan 15-22):
├─ Mon-Tue: Backend tasks 1.1-1.4 (User model, JWT, OTP, Passwords)
├─ Wed-Thu: Backend tasks 1.5-1.6 (Rate limiting, Session mgmt)
├─ Fri: Testing & debugging backend
│
Week 5 (Jan 22-29):
├─ Mon-Tue: Frontend tasks 1.7-1.9 (Login, Register, Token mgmt)
├─ Wed-Thu: Frontend tasks 1.10 + Integration testing
├─ Fri: Bug fixes & documentation
│
Outcomes:
✓ Fully functional authentication system
✓ Multi-factor OTP verification
✓ Secure session management
✓ Professional login/register UI
✓ API documentation
✓ Test coverage > 80%
```

---

## 🔐 Security Checklist

- [ ] Password hashing with Argon2
- [ ] JWT tokens with proper expiry
- [ ] OTP implementation (email/SMS)
- [ ] Rate limiting configured
- [ ] Brute-force protection active
- [ ] CSRF protection enabled
- [ ] CORS properly configured
- [ ] Secure cookie settings
- [ ] Session timeout enforced
- [ ] Password validation rules
- [ ] Input sanitization
- [ ] Error messages don't leak data
- [ ] Token refresh logic tested
- [ ] Concurrent session limiting
- [ ] Logout clears all sessions

---

## 📚 Key Files & Their Purpose

### Backend Models
```python
# User model with roles
accounts/models/user.py
accounts/models/role.py
accounts/models/otp.py
accounts/models/token_blacklist.py
```

### Backend Views
```python
# Authentication endpoints
accounts/views/auth.py          # Login, Register, Logout
accounts/views/password.py       # Password change, reset
accounts/views/otp.py            # OTP send, verify
accounts/views/profile.py        # Get/update profile
```

### Backend Serializers
```python
# Data validation & serialization
accounts/serializers/user.py
accounts/serializers/auth.py
accounts/serializers/otp.py
```

### Frontend Components
```typescript
// Auth components
components/Auth/LoginForm.tsx
components/Auth/RegisterForm.tsx
components/Auth/OTPModal.tsx
components/PrivateRoute.tsx

// Pages
pages/LoginPage.tsx
pages/RegisterPage.tsx

// Services
services/authService.ts
services/api.ts (axios instance)

// Hooks
hooks/useAuth.ts
hooks/useForm.ts

// Context
context/AuthContext.tsx
```

---

## 🧪 Testing Strategy

### Backend Tests (pytest)
```bash
# User model tests
pytest accounts/tests/test_models.py -v

# Authentication views tests
pytest accounts/tests/test_auth_views.py -v

# OTP system tests
pytest accounts/tests/test_otp.py -v

# Rate limiting tests
pytest accounts/tests/test_rate_limiting.py -v

# Token tests
pytest accounts/tests/test_jwt.py -v
```

### Frontend Tests (Jest)
```bash
# Login component tests
npm test -- Auth/LoginForm.test.tsx

# Register component tests
npm test -- Auth/RegisterForm.test.tsx

# Protected route tests
npm test -- PrivateRoute.test.tsx

# Auth hook tests
npm test -- hooks/useAuth.test.tsx
```

### Integration Tests
```bash
# End-to-end auth flow
npm run cypress -- run --spec "e2e/auth.cy.ts"
```

---

## 🚀 Getting Started

### Backend Setup
```bash
cd backend
python manage.py makemigrations accounts
python manage.py migrate
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Frontend Setup
```bash
cd frontend
npm install
npm start
# Opens http://localhost:3000
```

### Test the Flow
1. Register as voter at `/register`
2. Enter OTP from email/SMS
3. Login with credentials
4. Verify JWT token in browser console
5. Access protected routes

---

## 📖 Dependencies for Phase 1

### Backend
```
djangorestframework-simplejwt==5.3.0
django-ratelimit==4.1.0
cryptography==41.0.0
```

### Frontend
```
axios==1.5.0
crypto-js==4.1.1
```

---

## 💡 Best Practices

1. **Never store sensitive data in localStorage** - Use httpOnly cookies in production
2. **Always validate on server** - Client-side validation is only for UX
3. **Use HTTPS only** - All auth endpoints must use TLS 1.3
4. **Implement CSRF tokens** - Prevent cross-site request forgery
5. **Log security events** - Track login attempts, failures, etc.
6. **Hash passwords with Argon2** - Modern, secure hashing algorithm
7. **Implement rate limiting** - Prevent brute-force attacks
8. **Use short-lived tokens** - 15 minutes for access, 7 days for refresh
9. **Implement token rotation** - Refresh tokens regularly
10. **Clear sensitive data** - Remove tokens on logout

---

## 📝 Documentation to Generate

After Phase 1 completion, generate:
- [ ] API authentication documentation
- [ ] User registration flow diagram
- [ ] Login sequence diagram
- [ ] JWT token lifecycle diagram
- [ ] Security requirements document
- [ ] Testing report

---

## ✅ Phase 1 Completion Criteria

- [ ] All 10 tasks completed
- [ ] Unit test coverage > 80%
- [ ] All security checks passed
- [ ] No hardcoded secrets
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] Documentation complete
- [ ] Code review approved
- [ ] Manual testing passed
- [ ] Ready for Phase 2

---

## 🎯 What's Comes After Phase 1

**Phase 2**: Voter Registration Module
- Voter profile management
- Email & phone verification
- Eligibility checking
- Admin approval workflow
- Voter status tracking

---

## 📞 Support & Questions

During Phase 1 implementation:
- Refer to Django/DRF documentation for backend questions
- Check React docs for frontend questions
- Review security best practices in comments
- Run tests frequently
- Ask for clarification before proceeding

---

**Ready to start Phase 1?**  
Run: `cd backend && python manage.py runserver` to begin!

---

**Generated**: January 15, 2026  
**Status**: Ready for Implementation  
**Estimated Duration**: 2 weeks
