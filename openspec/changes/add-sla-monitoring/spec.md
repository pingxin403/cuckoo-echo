# Add SLA Monitoring

## Overview

Response time tracking, SLA metrics dashboard, and alerting for customer service SLAs.

## Motivation

Enterprise customers require SLA guarantees. Need to track:
- First response time
- Average response time
- SLA breach count

## Specification

### Core Features

1. **Metrics Collection**
   - Record request timestamp
   - Track response completion time
   - Store per-tenant metrics

2. **SLA Configuration**
   - Configurable SLA thresholds per tenant
   - Default: 30s first response
   - Customizable per tier

3. **Alerting**
   - Alert when SLA breach imminent
   - Dashboard showing current SLA status
   - Historical SLA reports

### File Changes

- `shared/sla_monitor.py`: SLA monitoring
- `chat_service/routes/sla.py`: SLA API

## Acceptance Criteria

- [ ] Response time tracked per request
- [ ] SLA breach alerts fired
- [ ] Dashboard shows real-time SLA
- [ ] Historical reports available