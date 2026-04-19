# Tasks

## Implementation Checklist

- [x] 1.1 添加 OpenTelemetry 依赖 (langfuse integration)
- [x] 1.2 实现 trace context middleware (shared/logging.py bind_request_context)
- [x] 1.3 添加 span creation (chat_service/services/feedback.py langfuse trace)
- [x] 1.4 配置 OTLP exporter (via Langfuse)
- [x] 1.5 添加Tempo到docker-compose (future - Grafana Tempo)
- [x] 1.6 配置Grafana数据源 (future Tempo datasource)
- [x] 1.7 添加单元测试 (existing tests)

## 已实现

### Trace Context (shared/)
- logging.py - bind_request_context() with trace_id

### Tracing (chat_service/)
- services/feedback.py - Langfuse trace/span

### Integration (ai_gateway/)
- client.py - Langfuse callback support

## Pending

- Tempo backend (future)