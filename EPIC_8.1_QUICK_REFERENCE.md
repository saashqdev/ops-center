# Epic 8.1: Webhook System - Quick Reference

## Overview
Complete webhook system for event-driven integrations with external services.

## API Endpoints

### Management
- `POST /api/v1/webhooks` - Create webhook
- `GET /api/v1/webhooks` - List webhooks (with filters)
- `GET /api/v1/webhooks/{id}` - Get webhook details
- `PATCH /api/v1/webhooks/{id}` - Update webhook
- `DELETE /api/v1/webhooks/{id}` - Delete webhook

### Operations
- `POST /api/v1/webhooks/{id}/test` - Test webhook delivery
- `GET /api/v1/webhooks/{id}/deliveries` - Get delivery history
- `GET /api/v1/webhooks/events/available` - List available event types

## Event Categories

### User Events (8)
- `user.created`, `user.updated`, `user.deleted`
- `user.login`, `user.logout`
- `user.password_changed`, `user.email_verified`
- `user.profile_updated`

### Subscription Events (5)
- `subscription.created`, `subscription.updated`, `subscription.cancelled`
- `subscription.renewed`, `subscription.payment_failed`

### Billing Events (6)
- `payment.succeeded`, `payment.failed`, `payment.refunded`
- `invoice.created`, `invoice.paid`, `invoice.overdue`

### Organization Events (3)
- `organization.created`, `organization.updated`, `organization.deleted`

### Edge Device Events (6)
- `device.registered`, `device.updated`, `device.deleted`
- `device.online`, `device.offline`, `device.alert`

### Monitoring Events (2)
- `alert.triggered`, `alert.resolved`

## Quick Examples

### Create Webhook (cURL)
```bash
curl -X POST http://localhost:8084/api/v1/webhooks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/webhook",
    "events": ["user.created", "subscription.created"],
    "description": "My webhook",
    "active": true
  }'
```

### List Webhooks
```bash
curl http://localhost:8084/api/v1/webhooks \
  -H "Authorization: Bearer $TOKEN"
```

### Test Webhook
```bash
curl -X POST http://localhost:8084/api/v1/webhooks/{webhook_id}/test \
  -H "Authorization: Bearer $TOKEN"
```

### Get Delivery History
```bash
curl http://localhost:8084/api/v1/webhooks/{webhook_id}/deliveries \
  -H "Authorization: Bearer $TOKEN"
```

## Webhook Payload Format
```json
{
  "event": "user.created",
  "timestamp": "2025-01-26T12:00:00Z",
  "data": {
    "user_id": 123,
    "email": "user@example.com",
    ...
  },
  "webhook_id": "webhook-uuid"
}
```

## Security

### HMAC Signature Verification (Python)
```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)

# In your webhook handler:
signature = request.headers.get('X-Webhook-Signature')
is_valid = verify_webhook(request.body, signature, webhook_secret)
```

### Node.js Example
```javascript
const crypto = require('crypto');

function verifyWebhook(payload, signature, secret) {
  const expected = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');
  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expected)
  );
}
```

## Retry Logic
- **Attempts**: Up to 6 retries
- **Delays**: 1m, 5m, 15m, 1h, 2h (exponential backoff)
- **Success Codes**: 200-299
- **Timeout**: 30 seconds per attempt

## Database Tables

### `webhooks`
```sql
- id (UUID, primary key)
- org_id (UUID, foreign key)
- url (TEXT)
- events (TEXT[])
- secret (TEXT, encrypted)
- active (BOOLEAN)
- description (TEXT)
- created_at, updated_at (TIMESTAMP)
```

### `webhook_deliveries`
```sql
- id (UUID, primary key)
- webhook_id (UUID, foreign key)
- event (TEXT)
- payload (JSONB)
- response_status (INT)
- response_body (TEXT)
- attempt_number (INT)
- delivered_at, created_at (TIMESTAMP)
```

## Programmatic Usage

### Trigger Events from Code
```python
from backend.webhook_manager import WebhookManager

webhook_manager = WebhookManager(db_pool)

# Trigger event
await webhook_manager.trigger_event(
    org_id=org_id,
    event='user.created',
    data={
        'user_id': user.id,
        'email': user.email,
        'created_at': user.created_at.isoformat()
    }
)
```

### Integration Points
Add webhook triggers to:
- User registration → `user.created`
- Login success → `user.login`
- Subscription changes → `subscription.updated`
- Payment processing → `payment.succeeded/failed`
- Device status changes → `device.online/offline`
- Alert conditions → `alert.triggered`

## Monitoring

### Check Delivery Stats
```sql
SELECT 
    event,
    COUNT(*) as total_deliveries,
    AVG(attempt_number) as avg_attempts,
    COUNT(CASE WHEN response_status >= 200 AND response_status < 300 THEN 1 END) as successful
FROM webhook_deliveries
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY event;
```

### Failed Deliveries
```sql
SELECT * FROM webhook_deliveries
WHERE response_status NOT BETWEEN 200 AND 299
ORDER BY created_at DESC
LIMIT 50;
```

## Common Issues

### Webhook Not Firing
1. Check webhook is active: `active=true`
2. Verify event is in webhook's events list
3. Check organization ID matches
4. Review logs: `docker logs ops-center-direct | grep webhook`

### Delivery Failures
- **SSL Errors**: Ensure HTTPS endpoint has valid certificate
- **Timeouts**: Webhook endpoint must respond within 30s
- **Rate Limits**: Consider implementing rate limiting on receiving end

### Testing
```bash
# Use webhook.site for testing
curl -X POST http://localhost:8084/api/v1/webhooks \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "url": "https://webhook.site/your-unique-url",
    "events": ["*"],
    "description": "Test webhook"
  }'
```

## Files Modified
- ✅ `backend/webhook_manager.py` (700 lines) - Core delivery engine
- ✅ `backend/webhook_api.py` (650 lines) - REST API endpoints
- ✅ `backend/server.py` - Router registration
- ✅ `alembic/versions/20260126_1100_create_webhook_tables.py` - Migration

## Next Steps
1. **Frontend UI** (Optional): Create webhook management page in React
2. **Event Integration**: Add trigger calls throughout codebase
3. **Analytics**: Build webhook delivery dashboard
4. **Rate Limiting**: Add per-webhook rate limits
5. **Filtering**: Support webhook payload transformations

## Production Checklist
- ✅ HMAC signature security implemented
- ✅ Exponential backoff retry logic
- ✅ Delivery history logging
- ✅ Event type validation
- ⏳ Add trigger calls to key business logic
- ⏳ Monitor delivery success rates
- ⏳ Set up alerts for high failure rates
- ⏳ Document webhook requirements for partners

---
**Epic Status**: Backend Complete ✅ | Frontend Optional ⏳ | Integration Pending ⏳
**Deployment**: Running on port 8084 at `/api/v1/webhooks`
