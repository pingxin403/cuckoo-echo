# API Specifications

## 认证

所有 API 需要 `Authorization: Bearer <api_key>` 头。

## 端点

### Chat API

| Method | Path | Description |
|--------|------|-------------|
| POST | /v1/chat/completions | SSE 流式对话 |
| GET | /v1/threads/{id} | 获取对话历史 |
| WS | /v1/chat/ws | WebSocket 对话 |

### Feedback API

| Method | Path | Description |
|--------|------|-------------|
| POST | /v1/feedback | 记录反馈 |
| GET | /v1/feedback/stats | 获取统计 |

### Admin API

| Method | Path | Description |
|--------|------|-------------|
| POST | /admin/v1/knowledge/docs | 上传文档 |
| GET | /admin/v1/knowledge/docs | 列表 |
| DELETE | /admin/v1/knowledge/docs/{id} | 删除 |
| WS | /admin/v1/ws/hitl | HITL WebSocket |

## 错误码

| Status | Description |
|--------|-------------|
| 401 | Unauthorized |
| 429 | Rate limit |
| 503 | Service unavailable |
