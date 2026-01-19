# Phase 6 Quick Reference

## WebSocket Endpoints

### Election Updates
```javascript
ws://localhost:8000/ws/election/{election_id}/
```

### Dashboard (Admin)
```javascript
ws://localhost:8000/ws/dashboard/
```

### User Notifications
```javascript
ws://localhost:8000/ws/notifications/
```

### System Broadcasts
```javascript
ws://localhost:8000/ws/broadcast/
```

## REST API Endpoints

### Send Broadcast
```bash
POST /api/voting/realtime/broadcast/
{
    "title": "System Maintenance",
    "message": "System down at 10 PM",
    "broadcast_type": "maintenance",
    "priority": "high"
}
```

### Notify User
```bash
POST /api/voting/realtime/notify_user/
{
    "user_id": "uuid",
    "title": "Update",
    "message": "Your profile updated",
    "notification_type": "info"
}
```

### Notify Election Voters
```bash
POST /api/voting/realtime/notify_election/
{
    "election_id": "uuid",
    "title": "Election Update",
    "message": "Voting time extended"
}
```

### Update Election Status
```bash
POST /api/voting/realtime/{election_id}/update_election_status/
{
    "status": "ongoing"
}
```

### Publish Results
```bash
POST /api/voting/realtime/{election_id}/publish_results/
```

### Dashboard Stats
```bash
GET /api/voting/realtime/dashboard_stats/
```

## Python Usage

### Send Notification
```python
from voting.realtime import notification_service

notification_service.send_user_notification(
    user_id='uuid',
    title='Vote Confirmed',
    message='Your vote recorded',
    notification_type='success'
)
```

### Election Event
```python
from voting.realtime import election_notifier

election_notifier.notify_vote_cast('election-uuid')
election_notifier.notify_election_status_change(
    'election-uuid', 'scheduled', 'ongoing'
)
```

### Dashboard Update
```python
from voting.realtime import dashboard_updater

dashboard_updater.notify_new_vote(
    'election-uuid', 'Election Title'
)
```

## JavaScript Client

### Basic Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/election/uuid/');

ws.onopen = () => console.log('Connected');

ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    console.log(msg.type, msg.data);
};

ws.onclose = () => console.log('Disconnected');
```

### Request Update
```javascript
ws.send(JSON.stringify({
    type: 'request_stats'
}));
```

## Deployment

### Run Daphne
```bash
daphne -b 0.0.0.0 -p 8000 ivs_backend.asgi:application
```

### Start Redis
```bash
redis-server
```

### Test Connection
```bash
redis-cli ping  # Should return PONG
```

## Testing

```bash
pytest test_phase6.py -v
```

## Key Files

- `voting/consumers.py` - WebSocket consumers
- `voting/realtime.py` - Notification services
- `voting/realtime_views.py` - REST API
- `voting/routing.py` - WebSocket routing
- `ivs_backend/asgi.py` - ASGI config
