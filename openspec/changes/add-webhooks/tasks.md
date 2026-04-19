# Tasks

## Implementation Checklist

- [ ] 1.1 添加 webhook model
- [ ] 1.2 添加 webhook CRUD routes
- [ ] 1.3 添加事件触发器
- [ ] 1.4 添加 retry 逻辑
- [ ] 1.5 添加 HMAC 签名
- [ ] 1.6 添加 test endpoint
- [ ] 1.7 添加单元测试

## Pending

### chat_service/
- models/webhook.py
- routes/webhook.py
- services/webhook.py

### Events
- thread.created
- thread.escalated
- thread.resolved
- feedback.received