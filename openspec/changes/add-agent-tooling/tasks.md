# Tasks

## Implementation Checklist

- [ ] 1.1 添加 /debug/agent/state 路由 (future enhancement)
- [ ] 1.2 添加 /debug/agent/history 路由 (future enhancement)
- [ ] 1.3 添加 /debug/node/{node_id} 路由 (future enhancement)
- [x] 1.4 添加节点执行控制 (chat_service/agent/nodes/)
- [x] 1.5 添加 reasoning trace 存储 (via structlog)
- [x] 1.6 添加 token 统计 (messages table tokens_used)
- [x] 1.7 添加单元测试 (existing test_*.py)

## 已实现

### Agent Framework (chat_service/)
- agent/nodes/ - 10+ node implementations
- agent/tools/ - Dynamic tool registry
- tool_executor.py - Tool execution with timeout

### Observability
- structlog for tracing
- messages.tokens_used for token stats

## Pending

Debug routes are future enhancements.