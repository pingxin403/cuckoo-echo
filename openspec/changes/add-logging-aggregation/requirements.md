# Requirements: Logging Aggregation

## Functional

1. **Log Aggregation**
   - All services ship logs to Loki
   - Logs include: timestamp, level, service, tenant_id, trace_id
   - Queryable via Grafana

2. **Metrics**
   - Request latency histograms
   - Error rates by service
   - RAG query latency
   - LLM token usage

3. **Alerts**
   - Error rate > 5% in 5min
   - P99 latency > 3s
   - Service down

## Non-Functional

- Log retention: 30 days
- Query latency: < 1s
- Storage: ~10GB/month

## Out of Scope

- Distributed tracing (future)
- APM (future)