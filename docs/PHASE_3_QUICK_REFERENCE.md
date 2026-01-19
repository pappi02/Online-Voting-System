# Phase 3 Quick Reference Guide

**Status**: ✅ COMPLETE  
**Date**: January 15, 2026

---

## API Quick Links

### Election Endpoints
```
GET    /api/v1/elections/                          # List all elections
POST   /api/v1/elections/                          # Create election
GET    /api/v1/elections/{id}/                     # Get details
PUT    /api/v1/elections/{id}/                     # Update
DELETE /api/v1/elections/{id}/                     # Delete
POST   /api/v1/elections/{id}/schedule_start/      # Start voting
POST   /api/v1/elections/{id}/close/               # Close voting
GET    /api/v1/elections/{id}/candidates/          # List candidates
GET    /api/v1/elections/{id}/voters/              # Participation stats
GET    /api/v1/elections/{id}/results/             # Results
```

### Position Endpoints
```
GET    /api/v1/elections/{election_id}/positions/                          # List
POST   /api/v1/elections/{election_id}/positions/                          # Create
GET    /api/v1/elections/{election_id}/positions/{id}/                     # Detail
PUT    /api/v1/elections/{election_id}/positions/{id}/                     # Update
DELETE /api/v1/elections/{election_id}/positions/{id}/                     # Delete
```

### Candidate Endpoints
```
GET    /api/v1/elections/{election_id}/positions/{position_id}/candidates/              # List
POST   /api/v1/elections/{election_id}/positions/{position_id}/candidates/              # Register
GET    /api/v1/elections/{election_id}/positions/{position_id}/candidates/{id}/         # Detail
POST   /api/v1/elections/{election_id}/positions/{position_id}/candidates/{id}/approve/  # Approve
POST   /api/v1/elections/{election_id}/positions/{position_id}/candidates/{id}/reject/   # Reject
POST   /api/v1/elections/{election_id}/positions/{position_id}/candidates/{id}/withdraw/ # Withdraw
```

---

## Common API Patterns

### Create Election
```json
POST /api/v1/elections/
{
  "title": "Student Council Elections 2026",
  "description": "Annual student council election",
  "election_type": "general",
  "scheduled_start": "2026-02-01T09:00:00Z",
  "scheduled_end": "2026-02-01T17:00:00Z",
  "allow_all_eligible": true,
  "allow_multiple_candidates": false,
  "results_visible_before_close": false
}
```

### Create Position
```json
POST /api/v1/elections/{election_id}/positions/
{
  "title": "President",
  "description": "Student council president",
  "seats_available": 1,
  "candidates_per_voter": 1,
  "display_order": 0
}
```

### Register as Candidate
```json
POST /api/v1/elections/{election_id}/positions/{position_id}/candidates/
{
  "full_name": "John Doe",
  "biography": "3rd year student, experienced leader",
  "party_affiliation": "Independent",
  "email": "john@example.com",
  "phone": "+1-555-0123",
  "website_url": "https://johndoe.example.com"
}
```

### Approve Candidate
```json
POST /api/v1/elections/{election_id}/positions/{position_id}/candidates/{id}/approve/
{
  "approval_notes": "All documents verified"
}
```

### Get Election Results
```json
GET /api/v1/elections/{election_id}/results/
{
  "results": [
    {
      "position": "President",
      "candidates": [
        {"id": "...", "name": "John Doe", "votes": 245},
        {"id": "...", "name": "Jane Smith", "votes": 189}
      ]
    }
  ]
}
```

---

## Model Reference

### Election Status Workflow
```
draft → scheduled → active → closed
  ↘                    ↙ (pause → paused → resume → active)
    cancelled
```

### Candidate Status Flow
```
pending → approved → (votes recorded)
    ↓
  rejected
    ↓
  (application denied)

approved → withdrawn (candidate choice)
```

### Voter Status Values
- `eligible`: Can participate in election
- `voted`: Has cast their vote
- `abstained`: Chose not to vote
- `ineligible`: Not allowed to vote

---

## Database Schema (Text)

```
Election (6 status, 5 types)
├── created_by → User
├── modified_by → User
├── eligible_voters → VoterProfile (M2M)
│
├─→ Position (1+)
│   ├── candidates_per_voter: int
│   ├── seats_available: int
│   └─→ Candidate (0+)
│       ├── user → User
│       ├── approved_by → User
│       ├── resume: File
│       └── status: pending/approved/rejected/withdrawn
│
├─→ ElectionSchedule (1:1)
│   └── pending_action, pending_action_time
│
├─→ ElectionVoter (1 per voter)
│   ├── voter → VoterProfile
│   ├── status: eligible/voted/abstained/ineligible
│   └── voted_at: DateTime, ip_address, user_agent
│
└─→ ElectionInvite (1+)
    ├── position → Position
    ├── recipient_email, recipient_name
    ├── status: sent/accepted/declined/expired
    └── expires_at: DateTime
```

---

## Permission Matrix

|  | List | Create | Read | Update | Delete |
|--|------|--------|------|--------|--------|
| **Elections** | Auth | Auth | Auth | Creator+ | Creator+ |
| **Positions** | Auth | Creator+ | Auth | Creator+ | Creator+ |
| **Candidates** | Auth | Auth | Auth | Creator+ | Creator+ |
| **Approve** | - | - | - | Creator+ | - |
| **Voters** | Creator+ | - | - | - | - |
| **Schedule** | Creator+ | Creator+ | - | Creator+ | - |
| **Invites** | Creator+ | Creator+ | Auth | - | - |

*Auth = Authenticated user  
Creator+ = Creator or Staff*

---

## Common Tasks

### Initialize New Election
```python
# 1. Create election
election = Election.objects.create(
    title="My Election",
    election_type="general",
    scheduled_start=future_datetime,
    scheduled_end=future_datetime_later,
    created_by=request.user
)

# 2. Create positions
for pos_name in ['President', 'VP', 'Treasurer']:
    Position.objects.create(
        election=election,
        title=pos_name,
        seats_available=1,
        candidates_per_voter=1
    )

# 3. Start accepting candidates (automatic via API)
# 4. Review & approve candidates (via admin or API)
# 5. Activate election (change status to active)
# 6. Monitor participation (voters API endpoint)
# 7. Close election (change status to closed)
# 8. View results (results endpoint)
```

### Start Election Voting
```python
# Via API
POST /api/v1/elections/{id}/schedule_start/

# Via Python
election.status = 'active'
election.save()
```

### Close Election
```python
# Via API
POST /api/v1/elections/{id}/close/

# Via Python
election.status = 'closed'
election.save()
```

---

## Admin Dashboard Access

1. **Elections**: `/admin/elections/election/`
2. **Positions**: `/admin/elections/position/`
3. **Candidates**: `/admin/elections/candidate/`
4. **Voters**: `/admin/elections/electionvoter/`
5. **Schedules**: `/admin/elections/electionschedule/`
6. **Invites**: `/admin/elections/electioninvite/`

---

## Filtering & Searching

### List Elections with Filters
```
/api/v1/elections/?status=active&election_type=general&search=student
```

### List Candidates by Status
```
/api/v1/elections/{id}/positions/{pos_id}/candidates/?status=pending
```

### List Voters by Status
```
/api/v1/elections/{id}/voters/?status=voted
```

---

## Error Responses

### 400 Bad Request
```json
{
  "title": ["An election with this title already exists"]
}
```

### 403 Forbidden
```json
{
  "detail": "Permission denied"
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

---

## Test the Implementation

```bash
# Run test suite
python backend/test_phase3.py

# Test API
curl -H "Authorization: Bearer {token}" http://localhost:8000/api/v1/elections/

# Check admin
# http://localhost:8000/admin/
```

---

## Dependencies

- Django 5.0.1
- Django REST Framework 3.14.0
- drf-nested-routers 0.93.5
- Python 3.10+

---

## Next Steps

1. **Frontend**: Implement election management UI in React
2. **Phase 4**: Implement voting system with encryption
3. **Phase 5**: Add vote tallying and results
4. **Phase 6**: Implement audit logging

---

**For detailed documentation, see PHASE_3_COMPLETE.md**
