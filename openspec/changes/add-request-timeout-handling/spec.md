# Add Request Timeout Handling

## Overview

Add explicit timeout configuration for AI Gateway calls with configurable defaults and per-tenant overrides.

## Motivation

Current implementation relies on default asyncio timeout. Need explicit timeout handling with graceful timeout responses and metrics.

## Specification

### Core Features

1. **Timeout Configuration**
   - Default timeout: 30 seconds
   - Configurable via environment variable
   - Per-tenant timeout override in tenant config

2. **Timeout Handling**
   - Catch asyncio.TimeoutError
   - Return user-friendly timeout message
   - Include retry suggestion

3. **Metrics**
   - Count timeout occurrences per tenant
   - Track timeout rate
   - Alert on high timeout rate

### File Changes

- `chat_service/agent/nodes/llm_generate.py`: Add timeout handling
- `ai_gateway/client.py`: Add timeout parameter
- `shared/config.py`: Add timeout configuration

## Acceptance Criteria

- [ ] Timeout defaults to 30s
- [ ] Timeout returns helpful message
- [ ] Timeout metrics tracked
- [ ] Per-tenant timeout configurable