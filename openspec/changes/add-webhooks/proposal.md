# Proposal: Add Webhooks

## Summary

Add webhook integration for external system notifications.

## Problem

- No real-time notifications
- No CRM/ERP integration
- No automation triggers

## Solution

### P0 - Webhook Events

- **thread.created**: New conversation
- **thread.escalated**: HITL triggered
- **thread.resolved**: Issue resolved
- **feedback.received**: User feedback

### P1 - Webhook Management

- **CRUD**: Create/read/update/delete webhooks
- **Test**: Test webhook endpoint
- **Retry**: Failed webhook retry (3x)

### P2 - Security

- **Secret**: HMAC signature
- **IP allowlist**: IP-based access
- **Rate limiting**: Per-webhook limits

## Priority

P1 - Integration

## Impact

- External system integration
- Workflow automation
- Better support