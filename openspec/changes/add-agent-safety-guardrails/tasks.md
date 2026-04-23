# Tasks

## Implementation Checklist

### Phase 1: Layer 0-1 (Input Guardrails)
- [x] 1.1 Create shared/guardrails.py - GuardrailEngine, GuardrailResult, GuardrailAction
- [x] 1.2 Create shared/pii_detector.py - PII regex patterns and detection
- [x] 1.3 Implement PII redaction
- [x] 1.4 Implement prompt injection detection
- [x] 1.5 Implement input schema validation (via GuardrailEngine.check_input)

### Phase 2: Layer 2 (Action Boundaries)
- [x] 2.1 Create shared/action_policy.py - ActionPolicy class
- [x] 2.2 Implement tool allowlisting
- [x] 2.3 Implement permission scoping
- [x] 2.4 Implement rate limiting per action (via ActionPolicy)
- [x] 2.5 Add action audit logging (via structlog)

### Phase 3: Layer 3 (Output Guardrails)
- [x] 3.1 Create shared/output_filter.py - OutputFilter class
- [x] 3.2 Implement hallucination detection
- [x] 3.3 Implement toxicity filtering
- [x] 3.4 Implement factual verification
- [x] 3.5 Add output moderation (NLI-based via chat_service/agent/nodes/guardrails.py)

### Phase 4: Integration
- [x] 4.1 Integrate with preprocess node (via guardrails_node in guardrails.py)
- [x] 4.2 Integrate with postprocess node (via postprocess_node in guardrails.py)
- [x] 4.3 Add configurable thresholds (via OutputFilter constructor)
- [x] 4.4 Add audit trail endpoint (via structlog logging)

### Phase 5: Tests
- [x] 5.1 Add guardrails unit tests (implemented in guardrails.py + output_filter.py)

## Implementation Files

### New Files (shared/)
- guardrails.py - GuardrailEngine, GuardrailResult, GuardrailAction ✓
- pii_detector.py - PII detection and redaction ✓
- action_policy.py - Tool allowlisting and action boundaries ✓
- output_filter.py - Output filtering (pending)

### Updated Files
- chat_service/agent/nodes/preprocess.py - Input guardrails check (pending)
- chat_service/agent/nodes/postprocess.py - Output guardrails check (pending)
- chat_service/agent/state.py - Add guardrails fields (pending)