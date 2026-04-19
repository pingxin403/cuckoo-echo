# Requirements: Distributed Tracing

## Functional

1. **Trace Context Propagation**
   - W3C traceparent header
   - trace_id across all services

2. **Span Creation**
   - API Gateway: http.server.span
   - Chat Service: ai.span, rag.span, tool.span
   - RAG: embedding.span, search.span, rerank.span

3. **Trace Export**
   - OTLP to Tempo
   - Local dev: stdout exporter

## Non-Functional

- Overhead: < 5% latency
- Storage: 30 day retention

## Out of Scope

- Auto-instrumentation (future)
- Sampling config (future)