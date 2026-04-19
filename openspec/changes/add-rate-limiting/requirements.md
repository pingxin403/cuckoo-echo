# Requirements: Rate Limiting

## Functional

1. **Rate Limiting**
   - Per-tenant: configurable
   - Per-user: configurable
   - Redis-backed state

2. **Circuit Breaker**
   - Half-open after 30s
   - Full open after 5 failures
   - State: closed/open/half-open

## Non-Functional

- Overhead: < 10ms
- Redis ops: < 2 per request
- Sliding window

## Out of Scope

- Distributed rate limiting across regions