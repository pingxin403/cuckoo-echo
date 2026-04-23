# Add AI Gateway Health Check

## Overview

Add AI Gateway service health monitoring to HealthMonitor for comprehensive system observability.

## Motivation

AI Gateway is a critical dependency. Current health check doesn't verify AI Gateway availability. Need to proactively detect AI Gateway degradation before user-facing failures.

## Specification

### Core Features

1. **AI Gateway Health Endpoint**
   - HTTP GET to AI Gateway /health endpoint
   - Measure response latency
   - Track success/failure rate

2. **Health Response Integration**
   - Add `ai_gateway` to service health list
   - Include AI Gateway in aggregated health status
   - Report AI Gateway latency in metrics

3. **Graceful Degradation**
   - AI Gateway down → mark as "degraded"
   - Timeout (>5s) → mark as "unhealthy"
   - Include AI Gateway status in /health/detailed

### File Changes

- `shared/health_monitor.py`: Add AI Gateway check
- `chat_service/agent/nodes/llm_generate.py`: Report LLM errors to HealthMonitor

### Metrics

- ai_gateway_healthy (boolean)
- ai_gateway_latency_ms (histogram)
- ai_gateway_error_rate (gauge)

## Acceptance Criteria

- [ ] AI Gateway health reported in /health/detailed
- [ ] Latency tracked per request
- [ ] Circuit breaker state affects health status
- [ ] Fallback message shown when AI Gateway unavailable