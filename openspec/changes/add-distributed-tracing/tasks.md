# Tasks

## Implementation Checklist

- [ ] 1.1 添加 OpenTelemetry 依赖
- [ ] 1.2 实现 trace context middleware
- [ ] 1.3 添加 span creation
- [ ] 1.4 配置 OTLP exporter
- [ ] 1.5 添加Tempo到docker-compose
- [ ] 1.6 配置Grafana数据源
- [ ] 1.7 添加单元测试

## Pending

### Middleware
- api_gateway/middleware/tracing.py

### Services
- chat_service/tracing.py
- shared/tracing.py

### Config
- Tempo in docker-compose.monitoring.yml