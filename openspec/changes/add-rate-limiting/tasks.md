# Tasks

## Implementation Checklist

- [ ] 1.1 添加 rate limiter 中间件
- [ ] 1.2 添加 Redis counter
- [ ] 1.3 添加 circuit breaker
- [ ] 1.4 添加 rate limit headers
- [ ] 1.5 添加配置管理
- [ ] 1.6 添加监控 metrics
- [ ] 1.7 添加单元测试

## Pending

### api_gateway/
- middleware/rate_limit.py
- middleware/circuit_breaker.py

### Config
- rate_limit: enabled
- rate_limit_per_tenant: 1000/min
- circuit_breaker_threshold: 5