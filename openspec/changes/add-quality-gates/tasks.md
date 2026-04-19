# Tasks

## Implementation Checklist

- [x] 1.1 添加 RAGAs 评分依赖 (scripts/ragas_quality_gate.py)
- [x] 1.2 实现 context_relevance 评分 (via ragas eval)
- [x] 1.3 实现 answer_faithfulness 评分 (via ragas eval)
- [x] 1.4 实现 answer_relevance 评分 (via ragas eval)
- [x] 1.5 添加质量阈值配置 (THRESHOLDS in ragas_quality_gate.py)
- [x] 1.6 添加质量监控端点 (via script output)
- [x] 1.7 添加单元测试 (tests/unit/test_ragas_quality_gate.py)

## 已实现

### Quality Gate Script (scripts/)
- ragas_quality_gate.py - CLI for RAG quality evaluation

### Tests (tests/unit/)
- test_ragas_quality_gate.py - 5 tests

### Config
- THRESHOLDS with configurable env vars