# Phase 7 Quick Reference - Security & Audit System

## Two-Factor Authentication (2FA)

### Setup Flow
1. **Initiate**: `POST /api/accounts/2fa/setup/` → Get QR code
2. **Verify**: `POST /api/accounts/2fa/verify/` + token → Enable 2FA
3. **Status**: `GET /api/accounts/2fa/status/` → Check if enabled

### Login with 2FA
1. Login returns `requires_2fa: true`
2. Submit token: `POST /api/accounts/2fa/verify/` + token
3. Receive JWT tokens

### Backup Codes
- Generated on 2FA enable (10 codes)
- One-time use
- Regenerate: `POST /api/accounts/2fa/regenerate_backup_codes/`

### Trusted Devices
- 30-day trust period
- Device ID: SHA256(IP + User-Agent)
- Revoke: `DELETE /api/accounts/trusted-devices/{id}/`

## Security Monitoring

### Risk Scoring
- **0-30**: Low risk (normal)
- **31-60**: Medium risk (monitor)
- **61-80**: High risk (alert)
- **81-100**: Critical risk (block)

### Brute Force Detection
- Threshold: 5 failed attempts in 10 minutes
- Action: Auto-block + security event created

### Unusual Activity Detection
- Unusual location (new IP)
- Unusual time (3 AM - 6 AM)
- Rapid actions (10+ in 1 minute)
- Excessive API usage (1000+ per hour)

## Rate Limits

### Endpoint Limits
```
/api/accounts/login/         5 per 5 min
/api/accounts/register/      3 per hour
/api/accounts/2fa/verify/    5 per 5 min
/api/voting/vote/            1 per minute
/api/* (default)             100 per minute
```

### Global Limits
- **Per IP**: 200 requests per minute
- **Per User**: 1000 requests per hour

### Response
```json
429 Too Many Requests
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Please try again later."
}
```

## Audit Logging

### Action Types
**Auth**: login, logout, password_change
**Voting**: vote_cast, vote_verified
**Elections**: created, updated, deleted
**Security**: 2fa_enabled, suspicious_activity

### Severity Levels
- **info**: Normal operations
- **warning**: Suspicious activity
- **error**: Failed operations
- **critical**: Security incidents

### Query Logs
```bash
GET /api/auditing/logs/?action=login&days=7
GET /api/auditing/logs/summary/
```

## Session Management

### Session Limits
- **Max Concurrent**: 3 sessions per user
- **Idle Timeout**: 1 hour
- **Absolute Timeout**: 12 hours

### Session Actions
```bash
GET  /api/auditing/sessions/active_sessions/
POST /api/auditing/sessions/invalidate_session/
POST /api/auditing/sessions/invalidate_all/
```

### Session Info
```json
{
  "session_key": "abc123...",
  "ip_address": "192.168.1.1",
  "age_seconds": 7200,
  "idle_seconds": 120,
  "expires_in": 36000,
  "is_current": true
}
```

## Security Headers

### Headers Applied
- **CSP**: Content-Security-Policy
- **HSTS**: Strict-Transport-Security (1 year)
- **X-Frame-Options**: DENY
- **X-Content-Type-Options**: nosniff
- **X-XSS-Protection**: 1; mode=block
- **Referrer-Policy**: strict-origin-when-cross-origin
- **Permissions-Policy**: Restricted features

## Security Events

### Event Types
- **brute_force**: Multiple failed logins
- **unusual_location**: New IP address
- **unusual_time**: Login at odd hours
- **suspicious_pattern**: Rapid actions
- **account_lockout**: Too many failures

### Event Status
- **open**: Needs investigation
- **investigating**: Under review
- **resolved**: Handled
- **false_positive**: Not a threat

### Dashboard (Admin)
```bash
GET /api/auditing/security-events/dashboard/
```

Returns:
- Open events count
- High-risk events count
- Event type breakdown
- Recent events list

## Common Code Patterns

### Log Audit Event
```python
from auditing.audit_models import AuditLog

AuditLog.log_action(
    action=AuditLog.ACTION_LOGIN,
    user=user,
    request=request,
    success=True,
    details={'method': '2fa'}
)
```

### Create Security Event
```python
from auditing.audit_models import SecurityEvent

SecurityEvent.create_event(
    event_type=SecurityEvent.EVENT_BRUTE_FORCE,
    ip_address='192.168.1.1',
    description='5 failed login attempts',
    user=user,
    risk_score=75
)
```

### Check Brute Force
```python
from auditing.security_monitor import SecurityMonitor

result = SecurityMonitor.check_brute_force(
    username='user@example.com',
    ip_address='192.168.1.1'
)

if result['should_block']:
    # Block the user/IP
    pass
```

### Validate Session
```python
from auditing.session_management import SessionManager

validation = SessionManager.validate_session(
    session_key,
    request
)

if not validation['valid']:
    # Log out user
    logout(request)
```

## Testing Checklist

### 2FA Testing
- [ ] Setup flow works
- [ ] QR code generates correctly
- [ ] Token verification succeeds
- [ ] Backup codes work
- [ ] Device trust works
- [ ] Disable flow works

### Security Testing
- [ ] Brute force detection triggers
- [ ] Rate limiting works
- [ ] Session timeouts work
- [ ] Security headers present
- [ ] Audit logs created

### API Testing
- [ ] All endpoints accessible
- [ ] Permissions enforced
- [ ] Error handling works
- [ ] Documentation accurate

## Troubleshooting

### 2FA Not Working
1. Check secret key generated
2. Verify TOTP time sync
3. Check token window (±30s)
4. Review 2FA logs

### Rate Limit Issues
1. Check Redis connection
2. Verify cache settings
3. Review rate limit thresholds
4. Check IP detection

### Session Problems
1. Check session timeout settings
2. Verify device fingerprinting
3. Review session metadata
4. Check concurrent session limit

### Audit Log Issues
1. Check database connection
2. Verify log creation
3. Review indexes
4. Check retention settings

## Security Recommendations

### For Production
1. **Enable HTTPS only**
2. **Configure Redis for sessions**
3. **Set up log rotation**
4. **Monitor security events daily**
5. **Review rate limits based on usage**
6. **Enable email alerts for critical events**
7. **Backup audit logs regularly**
8. **Review and clean old logs**

### For Users
1. **Enable 2FA immediately**
2. **Save backup codes securely**
3. **Review active sessions regularly**
4. **Use trusted devices**
5. **Report suspicious activity**

### For Admins
1. **Monitor security dashboard**
2. **Review open security events**
3. **Analyze brute force attempts**
4. **Check unusual activity patterns**
5. **Maintain audit log retention**

## Performance Tips

### Database
- Audit logs: Add index on timestamp
- Login attempts: Clean old records (30 days)
- Security events: Archive resolved (1 year)

### Caching
- Rate limits: Use Redis
- Session metadata: Cache for 1 hour
- User sessions list: Cache for 24 hours

### Queries
- Use pagination for audit logs
- Limit results to 100 by default
- Filter before ordering
- Use select_related for foreign keys

## Monitoring Commands

### Check Active Sessions
```bash
GET /api/auditing/sessions/active_sessions/
```

### View Recent Security Events
```bash
GET /api/auditing/security-events/?status=open
```

### Get Login Attempts
```bash
GET /api/auditing/monitor/login_attempts/?days=1
```

### Check User Risk Profile
```bash
GET /api/auditing/monitor/risk_profile/
```

### Audit Log Summary
```bash
GET /api/auditing/logs/summary/?days=7
```

## Integration Guide

### Add 2FA to Login Flow
```python
# 1. Check if user has 2FA enabled
if user.twofactorauth.is_enabled:
    # 2. Check if device is trusted
    device_id = get_device_id(request)
    if not is_device_trusted(user, device_id):
        # 3. Require 2FA token
        return Response({'requires_2fa': True})

# 4. Validate 2FA token
if not user.twofactorauth.verify_token(token):
    return Response({'error': 'Invalid token'})

# 5. Create trusted device if requested
if trust_device:
    TrustedDevice.create_trusted_device(user, request)
```

### Add Audit Logging to View
```python
from auditing.audit_models import AuditLog

class MyView(APIView):
    def post(self, request):
        # Your logic here
        result = do_something()
        
        # Log the action
        AuditLog.log_action(
            action='my_action',
            user=request.user,
            request=request,
            success=True,
            details={'result': result}
        )
        
        return Response({'success': True})
```

### Check Rate Limit in View
```python
from auditing.security_monitor import SecurityMonitor

class VoteView(APIView):
    def post(self, request):
        # Check rate limit
        result = SecurityMonitor.check_rate_limit(
            user_id=request.user.id,
            action='vote',
            max_attempts=1,
            window=60
        )
        
        if not result['allowed']:
            return Response(
                {'error': 'Rate limit exceeded'},
                status=429
            )
        
        # Process vote
        ...
```

## API Response Examples

### 2FA Status
```json
GET /api/accounts/2fa/status/
{
  "enabled": true,
  "enabled_at": "2026-01-15T10:00:00Z",
  "last_used": "2026-01-15T12:00:00Z",
  "backup_codes_remaining": 8
}
```

### Audit Log Entry
```json
{
  "id": 1,
  "user": "user@example.com",
  "action": "login",
  "severity": "info",
  "ip_address": "192.168.1.1",
  "request_path": "/api/accounts/auth/login/",
  "success": true,
  "timestamp": "2026-01-15T10:00:00Z",
  "details": {"method": "2fa"}
}
```

### Security Event
```json
{
  "id": 1,
  "event_type": "brute_force",
  "status": "open",
  "user": "attacker@example.com",
  "ip_address": "1.2.3.4",
  "description": "5 failed login attempts in 10 minutes",
  "risk_score": 75,
  "auto_blocked": true,
  "created_at": "2026-01-15T09:00:00Z"
}
```

### Risk Profile
```json
{
  "user_id": "user-uuid",
  "email": "user@example.com",
  "risk_score": 45,
  "risk_level": "medium",
  "failed_logins_7d": 2,
  "suspicious_activities_30d": 1,
  "open_security_events": 0,
  "total_security_events_30d": 1
}
```

## Emergency Procedures

### Account Compromised
1. Invalidate all sessions
2. Disable 2FA temporarily
3. Force password reset
4. Review audit logs
5. Check for unauthorized actions

### System Under Attack
1. Enable adaptive throttling
2. Increase rate limiting
3. Block suspicious IPs
4. Review security events
5. Alert administrators

### Data Breach Suspected
1. Review audit logs immediately
2. Identify affected users
3. Check security events
4. Analyze access patterns
5. Generate compliance report
