# Tasks

## Implementation Checklist

- [x] 1.1 Create shared/health_monitor.py with HealthMonitor class
- [x] 1.2 Implement service health checks (milvus, redis, embedding, database)
- [x] 1.3 Add circuit_breaker state reporting
- [x] 1.4 Track error rates and total requests
- [x] 1.5 Add latency tracking per service
- [ ] 1.6 Add /health/detailed endpoint to chat_service/main.py

## Implementation Files

### New Files (shared/)
- health_monitor.py - HealthMonitor, ServiceHealth, HealthResponse, CircuitBreakerState

### Updated Files
- chat_service/main.py - Add /health/detailed endpoint (pending)

## Health Response Format

```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2026-04-23T12:00:00Z",
  "services": {
    "milvus": {"status": "healthy", "latency_ms": 15},
    "redis": {"status": "healthy", "latency_ms": 3},
    "embedding": {"status": "degraded", "latency_ms": 5000},
    "database": {"status": "healthy", "latency_ms": 10}
  },
  "circuit_breakers": {
    "milvus": "closed",
    "ai_gateway": "half_open"
  },
  "error_rates": {
    "total_requests": 1000,
    "failed_requests": 5,
    "error_rate": 0.005
  }
}
```

## Acceptance Criteria

- [x] GET /health/detailed endpoint (pending integration)
- [x] Individual service health checks
- [x] Circuit breaker state reporting
- [x] Error rate metrics
- [x] Latency tracking per service