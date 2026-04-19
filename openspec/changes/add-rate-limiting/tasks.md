# Tasks

## Implementation Checklist

- [x] 1.1 添加 rate limiter 中间件 (api_gateway/middleware/rate_limit.py)
- [x] 1.2 添加 Redis counter (shared/db.py ratelimit_key)
- [x] 1.3 添加 circuit breaker (api_gateway/middleware/circuit_breaker.py)
- [x] 1.4 添加 rate limit headers (X-RateLimit-Limit, X-RateLimit-Remaining)
- [x] 1.5 添加配置管理 (admin_service /rate-limit endpoint)
- [x] 1.6 添加监控 metrics (via structlog)
- [x] 1.7 添加单元测试 (tests/unit/test_gateway.py + tests/pbt/test_p30_rate_limit.py)

## 已实现

### Middleware (api_gateway/)
- rate_limit.py - RateLimitMiddleware (tenant + user tiers)
- circuit_breaker.py - Circuit breaker for LLM/tools

### Config (admin_service/)
- PUT /v1/config/rate-limit - Update rate limits

### Tests
- test_gateway.py - 15+ rate limit tests
- test_p30_rate_limit.py - PBT tests