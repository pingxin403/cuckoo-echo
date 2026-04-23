# Agent Safety Guardrails Specification

## Overview

Implement layered guardrails for AI agent safety: input validation, action boundaries, output filtering, and real-time interception.

## Background

Industry best practices (2025-2026):
- Defense-in-depth: Single guardrail fails; need 3+ layers
- Layer 0: Fast moderation (pre-LLM)
- Layer 1: Input validation (PII, prompt injection)
- Layer 2: Action boundaries (tool allowlisting)
- Layer 3: Output filtering (hallucination, toxicity)

Guardrails must intercept in real-time, before bad input reaches LLM or bad output reaches user.

## Goals

1. Multi-layer defense against harmful inputs
2. Tool execution boundaries
3. Output quality gates
4. Audit trail for compliance

## Technical Approach

### Layered Architecture

```yaml
Layer 3: Output Guardrails    # Post-LLM: hallucination, toxicity, factual validation
Layer 2: Action Boundaries  # Tool allowlisting, permission scoping
Layer 1: Input Guardrails  # Pre-LLM: PII detection, prompt injection
Layer 0: Fast Moderation   # Pre-LLM: moderation API
```

### Guardrail Types

1. **Input Guardrails**
   - PII detection and redaction
   - Prompt injection detection
   - Input schema validation

2. **Action Guardrails**
   - Tool allowlisting
   - Permission scoping
   - Rate limiting per action

3. **Output Guardrails**
   - Hallucination detection
   - Toxicity filtering
   - Factual verification

### Implementation

```python
class GuardrailResult:
    passed: bool
    triggered: str | None  # Guardrail name
    confidence: float
    action: GuardrailAction  # BLOCK, WARN, LOG

class GuardrailEngine:
    async def check_input(self, text: str) -> GuardrailResult:
    async def check_output(self, text: str) -> GuardrailResult:
    async def check_action(self, tool: str, params: dict) -> GuardrailResult:
```

## Files

1. `shared/guardrails.py` - GuardrailEngine, GuardrailResult
2. `shared/pii_detector.py` - PII detection
3. `shared/action_policy.py` - Action boundary enforcement

## Acceptance Criteria

- [x] PII detection and redaction
- [x] Prompt injection detection
- [x] Tool allowlisting enforcement
- [x] Post-LLM output filtering (NLI-based hallucination detection)
- [x] Guardrail audit logging (via structlog)
- [x] Configurable thresholds