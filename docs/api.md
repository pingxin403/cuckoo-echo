# API Reference / 接口文档

All endpoints require authentication via `Authorization: Bearer <api_key>` header.

The API Gateway resolves `tenant_id` from the API key and injects it as `X-Tenant-ID` for downstream services.

---

## C-端对话接口 (Customer-Facing Chat)

### POST /v1/chat/completions — 流式对话 (SSE)

Send a message and receive streaming token response via Server-Sent Events.

```bash
curl -N -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer ck_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "user_ext_123",
    "messages": [
      {"role": "user", "content": "我的订单 12345 到哪了？"}
    ],
    "stream": true
  }'
```

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `thread_id` | UUID | No | Session ID. Omit to create a new thread |
| `user_id` | string | Yes | External user ID from tenant system |
| `messages` | array | Yes | Message array with `role` and `content` |
| `stream` | boolean | No | Enable SSE streaming (default: true) |
| `media` | array | No | Media attachments (image/audio) |

**SSE Response:**

```
data: {"id":"msg_abc123","delta":{"content":"您好"},"finish_reason":null}
data: {"id":"msg_abc123","delta":{"content":"，您的订单"},"finish_reason":null}
data: {"id":"msg_abc123","delta":{"content":"正在配送中"},"finish_reason":"stop"}
data: [DONE]
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 401 | Invalid or missing API key |
| 409 | Concurrent request on same thread (AI still processing) |
| 429 | Rate limit exceeded (`Retry-After` header included) |
| 503 | Service unavailable (circuit breaker open) |

---

### WS /v1/chat/ws — WebSocket 对话

Bidirectional WebSocket for real-time chat.

```bash
# Connect with wscat
wscat -c "ws://localhost:8000/v1/chat/ws" \
  -H "Authorization: Bearer ck_your_api_key_here"
```

**Client → Server:**

```json
{
  "type": "message",
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_ext_123",
  "content": "退货政策是什么？"
}
```

**Server → Client:**

```json
{"type": "token", "content": "根据"}
{"type": "token", "content": "我们的退货政策"}
{"type": "done", "thread_id": "550e8400-e29b-41d4-a716-446655440000"}
```

```json
{"type": "processing", "stage": "asr"}
{"type": "error", "code": "CONCURRENT_REQUEST", "message": "AI is still processing"}
```

---

### GET /v1/threads/{thread_id} — 获取会话历史

```bash
curl http://localhost:8000/v1/threads/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer ck_your_api_key_here"
```

**Response:**

```json
{
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "messages": [
    {
      "id": "msg_001",
      "role": "user",
      "content": "我的订单 12345 到哪了？",
      "created_at": "2024-01-15T10:30:00Z"
    },
    {
      "id": "msg_002",
      "role": "assistant",
      "content": "您的订单 12345 目前正在配送中，预计明天送达。",
      "tool_calls": [
        {"name": "get_order_status", "args": {"order_id": "12345"}, "result": {"status": "shipping"}}
      ],
      "tokens_used": 156,
      "created_at": "2024-01-15T10:30:02Z"
    }
  ]
}
```

---

## Admin 管理接口

All admin endpoints are prefixed with `/admin/v1/` and require admin-level API key authentication.

### POST /admin/v1/knowledge/docs — 上传知识文档

Upload a document for async processing (parse → chunk → vectorize).

```bash
curl -X POST http://localhost:8002/admin/v1/knowledge/docs \
  -H "Authorization: Bearer ck_admin_api_key" \
  -F "file=@product_faq.pdf"
```

**Response:**

```json
{
  "id": "doc_abc123",
  "filename": "product_faq.pdf",
  "status": "pending",
  "created_at": "2024-01-15T10:00:00Z"
}
```

Supported formats: PDF, Word (.docx), HTML, plain text. Max file size: 50MB.

---

### GET /admin/v1/knowledge/docs/{id} — 查询文档处理状态

```bash
curl http://localhost:8002/admin/v1/knowledge/docs/doc_abc123 \
  -H "Authorization: Bearer ck_admin_api_key"
```

**Response:**

```json
{
  "id": "doc_abc123",
  "filename": "product_faq.pdf",
  "status": "completed",
  "chunk_count": 42,
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:02:30Z"
}
```

Status values: `pending` → `processing` → `completed` | `failed`

---

### DELETE /admin/v1/knowledge/docs/{id} — 删除知识文档

Soft-deletes the document. Milvus vectors are cleaned up within 60 seconds.

```bash
curl -X DELETE http://localhost:8002/admin/v1/knowledge/docs/doc_abc123 \
  -H "Authorization: Bearer ck_admin_api_key"
```

**Response:**

```json
{"status": "deleted", "id": "doc_abc123"}
```

---

### POST /admin/v1/hitl/{session_id}/take — 接管会话

Admin user takes over a conversation from the AI agent.

```bash
curl -X POST http://localhost:8002/admin/v1/hitl/sess_xyz789/take \
  -H "Authorization: Bearer ck_admin_api_key" \
  -H "Content-Type: application/json" \
  -d '{"admin_user_id": "admin_001"}'
```

**Response:**

```json
{
  "session_id": "sess_xyz789",
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "admin_user_id": "admin_001",
  "conversation_history": [...]
}
```

---

### POST /admin/v1/hitl/{session_id}/end — 结束人工介入

```bash
curl -X POST http://localhost:8002/admin/v1/hitl/sess_xyz789/end \
  -H "Authorization: Bearer ck_admin_api_key"
```

**Response:**

```json
{
  "session_id": "sess_xyz789",
  "status": "resolved",
  "ended_at": "2024-01-15T11:00:00Z"
}
```

---

### PUT /admin/v1/config/persona — 配置机器人人设

```bash
curl -X PUT http://localhost:8002/admin/v1/config/persona \
  -H "Authorization: Bearer ck_admin_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "system_prompt": "你是一个专业的电商客服助手，语气友好、回答简洁。",
    "persona_name": "小布",
    "greeting": "您好！我是小布，有什么可以帮您的？"
  }'
```

**Response:**

```json
{"status": "updated", "tenant_id": "tenant_uuid"}
```

---

### GET /admin/v1/metrics/overview — 数据看板

```bash
# Default: last 7 days
curl "http://localhost:8002/admin/v1/metrics/overview?period=7d" \
  -H "Authorization: Bearer ck_admin_api_key"
```

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `period` | string | `7d` | Time range: `1d`, `7d`, `30d` |

**Response:**

```json
{
  "period": "7d",
  "total_conversations": 12450,
  "ai_resolution_rate": 0.87,
  "human_escalation_rate": 0.13,
  "avg_ttft_ms": 320,
  "total_tokens_used": 2450000,
  "total_tokens_input": 1800000,
  "total_tokens_output": 650000
}
```

---

## Common Error Responses

```json
{"error": "Unauthorized", "status": 401}
{"error": "Rate limit exceeded", "status": 429, "retry_after": 1}
{"error": "Service unavailable", "status": 503}
{"error": "Unsupported media type", "status": 415}
```

---

## Interactive Docs

Each service exposes auto-generated Swagger UI:

- API Gateway: `http://localhost:8000/docs`
- Chat Service: `http://localhost:8001/docs`
- Admin Service: `http://localhost:8002/docs`
