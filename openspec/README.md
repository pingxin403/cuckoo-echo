# Cuckoo-Echo OpenSpec

## 概述

Cuckoo-Echo 是一个企业级 AI 智能客服 SaaS 平台。本目录包含产品的完整技术规范和后续改进方向。

## 当前状态 (MVP 发布)

| 指标 | 状态 |
|------|------|
| 单元测试 | 329 ✅ |
| Lint | 0 errors ✅ |
| Build | Pass ✅ |
| Backend Features | 100% ✅ |
| Frontend Features | 100% ✅ |

## 规范结构

```
openspec/
├── README.md              # 本文件
├── IMPROVEMENTS.md        # 后续改进方向
├── ROADMAP.md             # 产品路线图
├── api/                   # API 规范
│   ├── chat.md           # 对话 API
│   ├── admin.md          # 管理 API
│   └── feedback.md        # 反馈 API
├── architecture/          # 架构文档
│   ├── system.md         # 系统架构
│   ├── data-flow.md      # 数据流
│   └── multi-tenant.md   # 多租户设计
└── ops/                   # 运维文档
    ├── deployment.md      # 部署指南
    └── monitoring.md     # 监控配置
```

## 快速链接

- **API 文档**: [api/](api/)
- **改进方向**: [IMPROVEMENTS.md](IMPROVEMENTS.md)
- **路线图**: [ROADMAP.md](ROADMAP.md)

---