# Requirements

## 功能需求

### A/B Testing

| 功能 | 优先级 | 状态 |
|------|--------|------|
| 实验配置 | P0 | 待实现 |
| 流量分流 | P0 | 待实现 |
| 指标追踪 | P0 | 待实现 |
| 统计计算 | P1 | 待实现 |
| Dashboard | P2 | 待实现 |

## 实验类型

- **Prompt 变体**: 测试不同 prompt 效果
- **模型切换**: A/B 测试不同 LLM
- **功能开关**: 渐进式发布

## API 设计

### POST /admin/experiments

```json
{
  "name": "new-prompt-v2",
  "type": "prompt",
  "variants": [
    {"id": "control", "weight": 50},
    {"id": "variant_a", "weight": 50}
  ],
  "metric": "conversion_rate"
}
```

### GET /admin/experiments/{id}/results

```json
{
  "experiment_id": "exp_xxx",
  "status": "running",
  "results": [
    {"variant": "control", "visitors": 1000, "conversions": 50, "rate": 0.05},
    {"variant": "variant_a", "visitors": 980, "conversions": 65, "rate": 0.066}
  ],
  "significance": 0.92
}
```

## 分流算法

- Cookie-based 稳定分流
- 哈希算法: `hash(tenant_id + experiment_id) % 100`
- 可配置权重