# Admin API

## Authentication

All admin endpoints require `Authorization: Bearer <admin_jwt>` header.

---

## POST /admin/api-keys

Create a new API key for a tenant.

### Request

```bash
curl -X POST http://localhost:8000/admin/api-keys \
  -H "Authorization: Bearer <admin_jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Key",
    "tenant_id": "tenant_123"
  }'
```

### Response

```json
{
  "id": "key_xxx",
  "name": "Production Key",
  "key": "ck_live_xxx",
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

## GET /admin/api-keys

List all API keys for the tenant.

### Response

```json
{
  "keys": [
    {"id": "key_xxx", "name": "Production Key", "created_at": "..."}
  ]
}
```

---

## DELETE /admin/api-keys/{key_id}

Revoke an API key.

---

## GET /admin/tenants/{tenant_id}

Get tenant details and usage stats.

### Response

```json
{
  "tenant_id": "tenant_123",
  "name": "Acme Corp",
  "plan": "enterprise",
  "usage": {
    "messages": 12500,
    "tokens": 2500000
  },
  "limits": {
    "messages": 50000,
    "tokens": 10000000
  }
}
```

---

## GET /admin/hitl/pending

List pending HITL (Human-In-The-Loop) requests.

### Response

```json
{
  "requests": [
    {
      "id": "hitl_xxx",
      "thread_id": "thread_123",
      "status": "pending",
      "created_at": "..."
    }
  ]
}
```

---

## POST /admin/hitl/{request_id}/approve

Approve a HITL request.

---

## POST /admin/hitl/{request_id}/reject

Reject a HITL request.