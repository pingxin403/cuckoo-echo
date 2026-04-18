# Chat API

## POST /v1/chat/completions

流式对话 SSE 端点。

### Request

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer ck_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "uuid",
    "user_id": "user_123",
    "messages": [{"role": "user", "content": "hello"}],
    "stream": true
  }'
```

### Response (SSE)

```
data: {"id":"msg_xxx","delta":{"content":"你好"}}
data: {"id":"msg_xxx","delta":{"content":"，"},"finish_reason":"stop"}
data: [DONE]
```

### Error Codes

| Status | Error | Description |
|--------|-------|-------------|
| 401 | Unauthorized | Invalid API key |
| 429 | Rate limit | Too many requests |
| 503 | Service unavailable | Circuit breaker open |

---

## GET /v1/threads/{thread_id}

获取对话历史。

### Response

```json
{
  "thread_id": "uuid",
  "status": "active",
  "messages": [
    {"id": "msg_xxx", "role": "user", "content": "hello", "created_at": "..."},
    {"id": "msg_xxx", "role": "assistant", "content": "hi", "created_at": "..."}
  ]
}
```

---

## WebSocket /v1/chat/ws

WebSocket 对话连接。

### Client → Server

```json
{"type": "start", "thread_id": "uuid", "user_id": "user_123", "message": "hello"}
```

### Server → Client

```json
{"type": "token", "content": "你"}
{"type": "done"}
{"type": "error", "message": "..."}
```