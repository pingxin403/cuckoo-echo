# Tasks

## Phase 1: Tenant Context Dependency
- [ ] 1.1 Create shared/tenant_context.py
- [ ] 1.2 Add get_current_tenant() helper
- [ ] 1.3 Add tenant validation decorator

## Phase 2: Route Protection
- [ ] 2.1 Add tenant validation to chat.py routes
- [ ] 2.2 Add tenant validation to ws_chat.py
- [ ] 2.3 Verify thread ownership on access

## Phase 3: Database Operations
- [ ] 3.1 Add tenant_id check in checkpointer.py
- [ ] 3.2 Verify thread exists and owned by tenant
- [ ] 3.3 Prevent cross-tenant state access

## Phase 4: Audit Logging
- [ ] 4.1 Log denied access attempts
- [ ] 4.2 Include tenant_id, resource_id, action
- [ ] 4.3 Set up alerting for suspicious patterns

## Phase 5: Testing
- [ ] 5.1 Unit tests for tenant context
- [ ] 5.2 Integration tests for cross-tenant denial
- [ ] 5.3 Security penetration test