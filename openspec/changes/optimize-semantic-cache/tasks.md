# Tasks

## Implementation Checklist

- [x] 1.1 分析线上缓存命中率 (via logs)
- [x] 1.2 调整相似度阈值 (semantic_threshold configurable)
- [x] 1.3 添加缓存指标到监控 (semantic_cache_hit/miss logs)
- [x] 1.4 优化 TTL 策略 (cache_invalidate on KB updates)
- [x] 1.5 验证效果 (14 unit tests)

## 已实现

### Semantic Cache (shared/)
- semantic_cache.py - cache_lookup, cache_store, cache_invalidate
- TTL strategy: auto-invalidate on knowledge base updates

### Integration (chat_service/)
- rag_engine.py calls cache_lookup
- llm_generate.py calls cache_store

### Tests (tests/unit/)
- test_semantic_cache.py - 14 tests