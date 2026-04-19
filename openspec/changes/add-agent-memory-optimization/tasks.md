# Tasks

## Implementation Checklist

- [ ] 1.1 添加 token budget 配置
- [ ] 1.2 实现 auto-summarizer
- [ ] 1.3 添加 message compression
- [ ] 1.4 实现 memory policies (FIFO, importance)
- [ ] 1.5 添加 context window 管理
- [ ] 1.6 添加 analytics metrics
- [ ] 1.7 添加单元测试

## Pending

### chat_service/
- summarizer.py - Already exists
- agent/memory.py - New memory management

### Config
- max_context_tokens: 8192
- compression_threshold: 0.8