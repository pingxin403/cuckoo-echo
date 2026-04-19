# Requirements

## 功能需求

### Billing System

| 功能 | 优先级 | 状态 |
|------|--------|------|
| 套餐管理 | P0 | 待实现 |
| 用量统计 | P0 | 待实现 |
| 账单生成 | P0 | 待实现 |
| 额度预警 | P1 | 待实现 |
| 支付集成 | P2 | 待规划 |

## 计费模型

### 套餐

| 套餐 | 价格 | 消息数 | Token数 |
|------|------|--------|---------|
| Free | $0 | 100/月 | 10k/月 |
| Starter | $49/月 | 1k/月 | 100k/月 |
| Pro | $199/月 | 5k/月 | 500k/月 |
| Enterprise | 定制 | 无限制 | 无限制 |

### 计费规则

- 按消息数计费 (超出套餐)
- 按 token 数计费 (超出套餐)
- 按调用工具次数计费
- 按知识库存储量计费

## API 设计

### GET /admin/billing/plans

```json
{
  "plans": [
    {"id": "starter", "name": "Starter", "price": 49, "messages": 1000}
  ]
}
```

### GET /admin/billing/usage/{tenant_id}

```json
{
  "tenant_id": "tenant_123",
  "period": "2026-04",
  "usage": {
    "messages": 850,
    "tokens": 180000,
    "tools": 120
  },
  "cost": 12.50,
  "limit": 1000
}
```

### GET /admin/billing/invoices

```json
{
  "invoices": [
    {"id": "inv_xxx", "amount": 49, "status": "paid", "date": "2026-04-01"}
  ]
}
```