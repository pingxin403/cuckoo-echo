# Tasks

## Phase 1: Health Monitor Update
- [ ] 1.1 Add AI Gateway health check method
- [ ] 1.2 Add timeout configuration (5s default)
- [ ] 1.3 Include ai_gateway in service list

## Phase 2: Latency Tracking
- [ ] 2.1 Track AI Gateway response latency
- [ ] 2.2 Store latency in HealthMonitor state
- [ ] 2.3 Report latency in health response

## Phase 3: Error Reporting
- [ ] 3.1 Report LLM failures to HealthMonitor
- [ ] 3.2 Track consecutive failures
- [ ] 3.3 Include error rate in health response

## Phase 4: Integration
- [ ] 4.1 Verify /health/detailed includes ai_gateway
- [ ] 4.2 Add Grafana dashboard panel
- [ ] 4.3 Add alerting rule for AI Gateway down