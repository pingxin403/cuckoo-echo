# Add Tenant Isolation Validation

## Overview

Add explicit tenant_id validation for all database operations to prevent cross-tenant data access.

## Motivation

Current implementation relies on implicit tenant_id from auth. Add explicit validation to prevent accidental data leaks and meet enterprise security requirements.

## Specification

### Core Features

1. **Thread Ownership Verification**
   - Verify thread belongs to requesting tenant
   - Check thread.tenant_id matches request tenant
   - Return 403 Forbidden on mismatch

2. **Message Access Control**
   - Verify messages belong to tenant's threads
   - Prevent access to other tenant's conversations

3. **TenantContext Helper**
   - Create tenant_context() dependency
   - Extract and validate tenant from request
   - Use in all route handlers

### File Changes

- `chat_service/routes/chat.py`: Add tenant validation
- `chat_service/routes/ws_chat.py`: Add tenant validation
- `chat_service/agent/checkpointer.py`: Verify tenant access
- `shared/tenant_context.py`: New dependency

### Security

- Audit log for cross-tenant access attempts
- Return generic 403 message (no details)
- Alert on suspicious patterns

## Acceptance Criteria

- [ ] Thread operations check tenant ownership
- [ ] WebSocket messages verified per tenant
- [ ] Audit log entries for denied access
- [ ] Unit tests for tenant isolation