# Requirements

## 功能需求

### Vision LLM

| 功能 | 优先级 | 状态 |
|------|--------|------|
| 图片上传端点 | P0 | 待实现 |
| 多模态 LLM 集成 | P0 | 待实现 |
| 图片理解工具 | P0 | 待实现 |
| 成本监控 | P1 | 待实现 |
| 降级策略 | P1 | 待实现 |

## API 设计

### POST /v1/chat/upload

```bash
curl -X POST http://localhost:8000/v1/chat/upload \
  -H "Authorization: Bearer ck_xxx" \
  -F "file=@screenshot.png"
```

Response:
```json
{
  "file_id": "file_xxx",
  "url": "/v1/files/file_xxx",
  "size": 1024
}
```

### 在消息中使用图片

```json
{
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "这是什么?"},
        {"type": "image_url", "image_url": {"url": "/v1/files/file_xxx"}}
      ]
    }
  ]
}
```

## 成本控制

- 单图最大 10MB
- 每用户每日限制 50 张图
- 记录图片处理 token 消耗