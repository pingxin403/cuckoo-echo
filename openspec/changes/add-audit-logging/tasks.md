# Tasks / 任务清单

## Phase 1: Core Implementation

- [ ] Create audit_logs table migration
- [ ] Create shared/audit.py module
- [ ] Implement AuditLogger class
- [ ] Add audit middleware

## Phase 2: Event Coverage

- [ ] Log authentication events (login, logout, failed)
- [ ] Log conversation access
- [ ] Log knowledge management
- [ ] Log admin configuration changes
- [ ] Log export operations
- [ ] Log API key changes
- [ ] Log billing changes

## Phase 3: Query API

- [ ] Add audit query endpoint
- [ ] Add date range filtering
- [ ] Add user filtering
- [ ] Add action type filtering
- [ ] Add export audit logs endpoint

## Phase 4: Testing

- [ ] Unit tests for audit logger
- [ ] Integration tests for audit events
- [ ] Test audit query API
- [ ] Test immutability