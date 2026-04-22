# Agent Evaluation Framework Specification

## Overview

Comprehensive evaluation framework for AI agents: trajectory tests, process metrics, and continuous quality scoring.

## Background

Agent evaluation ≠ answer evaluation. Key metrics:
- Human escalation rate
- Cost per successful task
- Policy compliance rate
- Step efficiency (steps/task)

Agents need process-centric evaluation, not only answer-centric.

## Goals

1. Trajectory-based testing (tool choice + outcomes)
2. Process metrics collection
3. Quality scoring pipeline
4. Regression detection

## Technical Approach

```python
class AgentEvalResult:
    task_id: str
    trajectory: list[Step]
    score: float
    metrics: AgentMetrics
    passed: bool

class EvaluationSuite:
    async def run_trajectory_test(self, test_case: TestCase) -> AgentEvalResult:
    async def compute_quality_score(self, result: AgentEvalResult) -> float:
```

### Metrics

- Step success rate
- Tool call accuracy
- Policy compliance
- Cost efficiency
- Latency

## Files

1. `chat_service/services/evaluation.py` - EvaluationSuite
2. `tests/unit/test_evaluation.py` - Eval tests

## Acceptance Criteria

- [ ] Trajectory-based test runner
- [ ] Process metrics collection
- [ ] Quality scoring
- [ ] Regression detection
- [ ] Eval dataset management