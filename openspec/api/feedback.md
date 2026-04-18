# Feedback API

## POST /v1/feedback

Submit user feedback for a message.

### Request

```bash
curl -X POST http://localhost:8000/v1/feedback \
  -H "Authorization: Bearer ck_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "msg_xxx",
    "vote": "thumbs_up"
  }'
```

### Response

```json
{
  "success": true
}
```

### Vote Values

| Value | Description |
|-------|-------------|
| `thumbs_up` | Positive feedback |
| `thumbs_down` | Negative feedback |

---

## GET /v1/feedback/{message_id}

Get feedback for a specific message.

### Response

```json
{
  "message_id": "msg_xxx",
  "thumbs_up": 10,
  "thumbs_down": 2
}
```

---

## GET /admin/feedback/stats

Get aggregate feedback statistics.

### Response

```json
{
  "total_messages": 1000,
  "thumbs_up": 750,
  "thumbs_down": 50,
  "sentiment_score": 0.875
}
```