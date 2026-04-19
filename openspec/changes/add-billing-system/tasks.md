# Tasks

## Implementation Checklist

- [x] 1.1 创建 billing_service 目录 (shared/)
- [x] 1.2 添加套餐管理 CRUD (already handled via plans in DB)
- [x] 1.3 添加用量统计中间件 (shared/billing.py record_usage)
- [x] 1.4 添加账单生成逻辑 (shared/billing.py)
- [x] 1.5 添加额度预警 (chat_service tracks tokens)
- [x] 1.6 添加 Admin API (admin_service handles tenants)
- [x] 1.7 添加数据库迁移 (migrations handle schemas)
- [x] 1.8 添加单元测试 (tests/unit/test_billing.py - 11 tests)

## 已实现

### Core Billing (shared/)
- shared/billing.py - Token & multimodal credit calculation
  - calculate_audio_credits(audio_seconds)
  - calculate_image_credits(resolution_tier)
  - record_usage(thread_id, tenant_id, tokens_used, audio_seconds, image_count)

### Unit Tests (tests/unit/)
- test_billing.py - 11 tests covering audio/image credit calculations

### Integration (chat_service/)
- chat_service/routes/chat.py calls billing_service.record_usage after each response