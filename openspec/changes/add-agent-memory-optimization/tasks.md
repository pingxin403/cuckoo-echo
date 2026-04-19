# Tasks

## Implementation Checklist

- [x] 1.1 添加 token budget 配置 (SUMMARIZE_THRESHOLD config)
- [x] 1.2 实现 auto-summarizer (chat_service/agent/summarizer.py)
- [x] 1.3 添加 message compression (llm_summarizer.summarize())
- [x] 1.4 实现 memory policies (FIFO via config)
- [x] 1.5 添加 context window 管理 (llm_generate.py context window)
- [x] 1.6 添加 analytics metrics (via structlog)
- [x] 1.7 添加单元测试 (tests/unit/test_summarizer.py + test_summary_compression.py)

## 已实现

### Summarizer (chat_service/)
- agent/summarizer.py - LLMSummarizer
- agent/nodes/preprocess.py - compression trigger

### Tests
- test_summarizer.py - 8 tests
- test_summary_compression.py - compression tests