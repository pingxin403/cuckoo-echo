# Tasks

## Implementation Checklist

- [x] 1.1 添加 Loki 到 docker-compose.yml (docker-compose.monitoring.yml)
- [x] 1.2 添加 Promtail 配置 (via docker-compose.monitoring.yml)
- [x] 1.3 配置日志格式 (JSON + tenant_id in shared/logging.py)
- [x] 1.4 添加 Grafana 仪表板 (monitoring/dashboards/cuckoo-echo.json)
- [x] 1.5 配置 Prometheus metrics (monitoring/prometheus.yml)
- [x] 1.6 添加告警规则 (monitoring/alert_rules.yml)
- [x] 1.7 验证功能

## 已实现

### Monitoring Stack (docker-compose.monitoring.yml)
- prometheus: Metrics collection
- loki: Log aggregation
- grafana: Dashboards (port 3000, admin/admin)

### Configuration (monitoring/)
- prometheus.yml - Scraping config
- alert_rules.yml - Alert rules
- dashboards/cuckoo-echo.json - Overview dashboard
- datasources/prometheus.yml - Prometheus datasource