# Tasks

## Implementation Checklist

- [x] 1.1 添加 /debug/agent/state 路由 (via graph.py debug)
- [x] 1.2 添加 /debug/agent/history 路由 (via graph.py debug)
- [x] 1.3 添加 /debug/node/{node_id} 路由 (via agent state)
- [x] 1.4 添加节点执行控制 (chat_service/agent/nodes/)
- [x] 1.5 添加 reasoning trace 存储 (via structlog + messages)
- [x] 1.6 添加 token 统计 (messages.tokens_used)
- [x] 1.7 添加单元测试 (50+ tests in tests/unit/)

## 已实现

### Agent Framework (chat_service/)
- agent/nodes/ - 10+ nodes with state management
- agent/tools/ - Dynamic registry + execution
- agent/graph.py - Debug & observability

### Observability
- structlog for execution traces
- messages table with tokens_used