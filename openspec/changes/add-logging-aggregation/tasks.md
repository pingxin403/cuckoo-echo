# Tasks

## Implementation Checklist

- [ ] 1.1 添加 Loki 到 docker-compose.yml
- [ ] 1.2 添加 Promtail 配置
- [ ] 1.3 配置日志格式 (JSON + tenant_id)
- [ ] 1.4 添加 Grafana 仪表板
- [ ] 1.5 配置 Prometheus metrics
- [ ] 1.6 添加告警规则
- [ ] 1.7 验证功能

## Pending

### docker-compose
- loki service
- promtail service
- grafana service (optional)

### Configuration
- Shared log format with trace_id
- Tenant context in logs