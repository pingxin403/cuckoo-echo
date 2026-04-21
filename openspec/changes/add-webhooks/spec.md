# Webhook System Specification

## Overview

Event-driven webhook system for external integrations and notifications.

## Goals
- Real-time event notifications
- External system integration
- Retry logic with exponential backoff
- Event filtering and transformation

## Technical Design

### Event Types
1. **conversation** - conversation.created, conversation.resolved, conversation.escalated
2. **message** - message.received, message.sent
3. **hitl** - hitl.requested, hitl.taken, hitl.completed
4. **billing** - billing.limit_exceeded, billing.payment_failed
5. **feedback** - feedback.received

### Webhook Configuration
- Secret key for signature verification
- Event filtering by type
- Request transformation template
- Retry policy (max 3 attempts)

## Implementation Plan

### Phase 1: Core Webhook
1.1 Add webhook model and database table
1.2 Create webhook delivery service
1.3 Add signature verification

### Phase 2: Events
2.1 Emit events from chat service
2.2 Add event queue (Redis)
2.3 Implement retry logic

### Phase 3: Admin API
3.1 Webhook CRUD endpoints
3.2 Event log viewer
3.3 Test webhook endpoint

## Acceptance Criteria
- [x] Webhooks can be configured per tenant
- [x] Events delivered with retry logic
- [x] Signature verification works
- [x] Admin can manage webhooks