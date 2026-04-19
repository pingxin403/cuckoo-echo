# Tasks

## Implementation Checklist

### Phase 1: Database Schema
- [x] 1.1 添加 billing_accounts 表 (tenant_id, plan_id, balance, credit_limit, status)
- [x] 1.2 添加 billing_plans 表 (name, price, message_limit, token_limit, features)
- [x] 1.3 添加 usage_records 表 (tenant_id, period, messages, tokens, tools, storage_mb)
- [x] 1.4 添加 invoices 表 (tenant_id, amount, status, period, created_at)
- [x] 1.5 创建数据库迁移文件 (007_billing_tables.py)

### Phase 2: Billing Service
- [x] 2.1 创建 shared/billing.py - 核心计费逻辑
- [x] 2.2 添加 token 使用统计 (record_usage_to_db)
- [x] 2.3 实现额度检查与预警 (check_limit)
- [x] 2.4 实现超额计费计算

### Phase 3: Admin API
- [x] 3.1 添加 /admin/billing/plans CRUD
- [x] 3.2 添加 /admin/billing/usage/{tenant_id}
- [x] 3.3 添加 /admin/billing/invoices
- [x] 3.4 添加管理后台套餐配置页面 (API完成，前端可后续对接)

### Phase 4: Integration
- [x] 4.1 集成到 API Gateway (token 统计)
- [x] 4.2 集成到 Chat Service (消息统计)
- [x] 4.3 添加余额不足拦截

### Phase 5: Tests
- [x] 5.1 添加 billing integration tests
- [x] 5.2 添加 usage calculation tests
