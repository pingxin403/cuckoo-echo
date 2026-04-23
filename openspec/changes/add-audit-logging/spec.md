# Audit Logging for Compliance

## Problem / 问题

Enterprise customers require audit trails for:
- SOC 2 compliance
- GDPR compliance (access logs)
- Internal security reviews
- Legal discovery

Currently there is no structured audit logging for sensitive operations.

## Background / 背景

Operations that should be audited:
- Login/logout events
- Conversation access
- Configuration changes
- Admin actions
- Data exports
- API key changes

Each audit log should contain:
- Timestamp
- Actor (user/tenant_id)
- Action type
- Resource affected
- Result (success/failure)
- IP address

## Requirements / 需求

1. **Audit Log Storage**
   - Separate audit log table
   - Append-only design
   - Immutable records

2. **Audited Events**
   - Authentication (login, logout, failed)
   - Conversation CRUD
   - Knowledge management
   - Admin configuration changes
   - Export operations
   - API key management
   - Billing changes

3. **Audit Log Entry**
   ```python
   {
       "timestamp": "2026-04-23T10:00:00Z",
       "tenant_id": "uuid",
       "user_id": "uuid",
       "action": "conversation.export",
       "resource_id": "uuid",
       "result": "success",
       "ip_address": "192.168.1.1",
       "metadata": {}
   }
   ```

4. **Audit Query API**
   - Query by date range
   - Query by user
   - Query by action type
   - Export audit logs

## Implementation / 实现方案

```python
#.shared/audit.py
class AuditLogger:
    async def log(self, action: str, tenant_id: str, user_id: str, ...):
        await db_pool.execute(
            "INSERT INTO audit_logs (...) VALUES (...)",
            timestamp=datetime.utcnow(),
            action=action,
            # ...
        )
```

Middleware for HTTP endpoints:
```python
# Audit middleware
async def audit_middleware(request: Request, call_next):
    result = await call_next(request)
    await audit_logger.log(
        action=request.url.path,
        tenant_id=get_tenant_id(request),
        # ...
    )
    return result
```

## Acceptance Criteria / 验收标准

- [ ] Audit log table created with RLS
- [ ] Login/logout events logged
- [ ] Admin actions logged
- [ ] Export operations logged
- [ ] Audit query endpoint implemented
- [ ] Audit logs are immutable
- [ ] Query by date range works
- [ ] Query by user works