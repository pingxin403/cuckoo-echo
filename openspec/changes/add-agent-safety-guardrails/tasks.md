# Tasks

## Implementation Checklist

### Phase 1: Layer 0-1 (Input Guardrails)
- [x] 1.1 Create shared/guardrails.py - GuardrailEngine, GuardrailResult, GuardrailAction
- [x] 1.2 Create shared/pii_detector.py - PII regex patterns and detection
- [x] 1.3 Implement PII redaction
- [x] 1.4 Implement prompt injection detection
- [ ] 1.5 Implement input schema validation

### Phase 2: Layer 2 (Action Boundaries)
- [x] 2.1 Create shared/action_policy.py - ActionPolicy class
- [x] 2.2 Implement tool allowlisting
- [ ] 2.3 Implement permission scoping
- [ ] 2.4 Implement rate limiting per action
- [ ] 2.5 Add action audit logging

### Phase 3: Layer 3 (Output Guardrails)
- [ ] 3.1 Create shared/output_filter.py - OutputFilter class
- [ ] 3.2 Implement hallucination detection
- [ ] 3.3 Implement toxicity filtering
- [ ] 3.4 Implement factual verification
- [ ] 3.5 Add output moderation

### Phase 4: Integration
- [ ] 4.1 Integrate with preprocess node
- [ ] 4.2 Integrate with postprocess node
- [ ] 4.3 Add configurable thresholds
- [ ] 4.4 Add audit trail endpoint

### Phase 5: Tests
- [ ] 5.1 Add guardrails unit tests
- [ ] 5.2 Add PII detection tests
- [ ] 5.3 Add action policy tests
- [ ] 5.4 Add integration tests

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