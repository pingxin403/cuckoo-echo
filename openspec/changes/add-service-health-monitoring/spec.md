# Add Service Health Monitoring Specification

## Overview

Add detailed /health endpoint showing service status, circuit breaker states, and error rate metrics for monitoring system health.

## Background

Need comprehensive health monitoring to detect and diagnose service degradation. Current system lacks visibility into service health.

## Technical Approach

### Health Response Format
```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2026-04-23T12:00:00Z",
  "services": {
    "milvus": {"status": "healthy", "latency_ms": 15},
    "redis": {"status": "healthy", "latency_ms": 3},
    "ai_gateway": {"status": "healthy", "latency_ms": 250},
    "embedding": {"status": "degraded", "latency_ms": 5000}
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

- [ ] GET /health/detailed endpoint
- [ ] Individual service health checks
- [ ] Circuit breaker state reporting
- [ ] Error rate metrics
- [ ] Latency tracking per service