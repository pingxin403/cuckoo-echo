# Tasks

## Implementation Checklist

### Phase 1: Core Webhook
- [x] 1.1 Add webhook model and database table
- [x] 1.2 Create webhook delivery service
- [x] 1.3 Add signature verification

### Phase 2: Events
- [x] 2.1 Emit events from chat service
- [x] 2.2 Add event queue (Redis)
- [x] 2.3 Implement retry logic

### Phase 3: Admin API
- [x] 3.1 Webhook CRUD endpoints
- [x] 3.2 Event log viewer
- [x] 3.3 Test webhook endpoint

## Event Types

- conversation.created
- conversation.resolved
- conversation.escalated
- message.received
- message.sent
- hitl.requested
- hitl.taken
- hitl.completed
- billing.limit_exceeded
- feedback.received

## API Endpoints

- GET /admin/v1/webhooks
- POST /admin/v1/webhooks
- PUT /admin/v1/webhooks/{id}
- DELETE /admin/v1/webhooks/{id}
- POST /admin/v1/webhooks/{id}/test

## Database Table

webhooks: id, tenant_id, url, secret, events, enabled, created_at