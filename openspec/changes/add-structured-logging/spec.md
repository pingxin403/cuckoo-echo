# Add Structured Logging

## Overview

Add distributed tracing support with correlation IDs (trace_id, span_id) propagated across all LangGraph nodes for observability and debugging.

## Motivation

Current logging lacks distributed tracing context. When a request spans multiple nodes (preprocess → rag → llm_generate → guardrails), correlating logs across nodes is difficult without correlation IDs.

## Specification

### Core Features

1. **Correlation ID Generation**
   - Generate trace_id at request entry (chat or websocket)
   - Propagate trace_id through AgentState
   - Inject trace_id into structlog context

2. **Node-Level Span Logging**
   - Each LangGraph node logs start/end with trace_id
   - Include node name, input size, output size, duration
   - Log levels: DEBUG (node entry/exit), INFO (success), WARN (degraded), ERROR (failure)

3. **Structured Fields**
   - `trace_id`: UUID4, unique per request
   - `span_id`: Incremental per node, dot-separated path
   - `correlation_id`: Optional, from headers (X-Correlation-ID)
   - `tenant_id`: Always included
   - `user_id`: When available

4. **Context Propagation**
   - Add trace_id to LangGraph state
   - Middleware extracts/creates trace_id from request headers
   - WebSocket handler passes trace_id in connect message

### File Changes

- `shared/logging.py`: Add correlation ID helpers
- `chat_service/main.py`: Middleware to extract/create trace_id
- `chat_service/routes/chat.py`: Pass trace_id to agent
- `chat_service/routes/ws_chat.py`: Pass trace_id to agent
- All `chat_service/agent/nodes/*.py`: Log with trace context

### Metrics

- Log entries per request (target: 20-50 entries)
- Average log size (target: <500 bytes per entry)
- Trace coverage (% of requests with valid trace_id)

## Acceptance Criteria

- [ ] All API endpoints include trace_id in all log entries
- [ ] WebSocket connections propagate trace_id
- [ ] LangGraph node transitions logged with span hierarchy
- [ ] trace_id queryable in Loki/Grafana
- [ ] Zero performance regression (>5ms overhead per request)

## Priority

**High** - Foundation for observability