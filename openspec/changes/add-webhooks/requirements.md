# Requirements: Webhooks

## Functional

1. **Events**
   - thread.created
   - thread.escalated
   - thread.resolved
   - feedback.received

2. **Webhook Management**
   - POST /v1/webhooks
   - GET /v1/webhooks
   - POST /v1/webhooks/{id}/test
   - DELETE /v1/webhooks/{id}

3. **Retry**
   - 3 retries on failure
   - Exponential backoff

## Non-Functional

- Timeout: 10s
- Payload size: < 100KB
- Retry schedule: 1m, 5m, 15m

## Out of Scope

- Webhook playground (future)
- Custom events (future)