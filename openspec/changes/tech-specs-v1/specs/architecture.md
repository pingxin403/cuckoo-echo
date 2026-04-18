# Architecture

## 系统架构

```
┌─────────────────────────────────────────────────┐
│                   Clients                        │
│   (Web, Mobile, SDK)                            │
└─────────────┬───────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────┐
│              API Gateway (8000)                 │
│   Auth · Rate Limit · Circuit Breaker          │
└─────────────┬───────────────────────────────────┘
              │
    ┌─────────┴─────────┐
    │                   │
┌───▼────┐       ┌────▼──────┐
│ Chat   │       │  Admin    │
│ Service│       │  Service  │
│ (8001) │       │  (8002)  │
└────┬───┘       └────┬─────┘
     │               │
     └───────┬───────┘
             │
    ┌────────┼────────┐
    │        │        │
  PostgreSQL  Milvus  Redis
```

## 多租户隔离

| 层级 | 机制 |
|------|------|
| PostgreSQL | RLS (Row Level Security) |
| Milvus | PartitionKey |
| Redis | Key 前缀 |

## 服务列表

| Service | Port | 职责 |
|---------|------|------|
| api-gateway | 8000 | 鉴权、限流 |
| chat-service | 8001 | 对话核心 |
| admin-service | 8002 | 管理后台 |
| knowledge-pipeline | - | 文档处理 |
