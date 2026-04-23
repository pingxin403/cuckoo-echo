# Tasks

## Phase 1: Core Infrastructure
- [ ] 1.1 Add trace_id generation utility (shared/logging.py)
- [ ] 1.2 Add correlation_id extraction from headers
- [ ] 1.3 Create trace context injection helper

## Phase 2: HTTP Middleware
- [ ] 2.1 Add trace middleware to chat_service/main.py
- [ ] 2.2 Extract X-Correlation-ID from request headers
- [ ] 2.3 Generate trace_id if not provided

## Phase 3: State Propagation
- [ ] 3.1 Add trace_id to AgentState
- [ ] 3.2 Propagate trace_id through graph
- [ ] 3.3 Log trace context in preprocess_node

## Phase 4: Node-Level Logging
- [ ] 4.1 Add node entry/exit logging (rag_engine_node)
- [ ] 4.2 Add node entry/exit logging (llm_generate_node)
- [ ] 4.3 Add node entry/exit logging (tool_executor_node)
- [ ] 4.4 Add node entry/exit logging (guardrails_node)

## Phase 5: WebSocket Support
- [ ] 5.1 Extract/create trace_id in ws_chat.py
- [ ] 5.2 Pass trace_id in WebSocket connect
- [ ] 5.3 Log WebSocket events with trace context

## Phase 6: Testing & Validation
- [ ] 6.1 Add unit tests for trace context
- [ ] 6.2 Add integration test with trace propagation
- [ ] 6.3 Verify Grafana Loki queries work