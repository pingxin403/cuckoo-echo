# Tasks / 任务清单

## Phase 1: Bug Fixes & Wiring

- [x] Wire circuit_breaker.py to ai_gateway client
- [x] Implement CacheBackend in shared/cache_backend.py
- [x] Fix bare exception handlers in shared/prompt_template.py
- [x] Fix bare exception handlers in chat_service/agent/nodes/llm_generate.py

## Phase 2: Testing & Observability

- [ ] All unit tests passing
- [ ] All integration tests passing  
- [ ] All E2E tests passing
- [ ] Add Prometheus metrics to all endpoints
- [ ] Add distributed tracing (if feasible)

## Phase 3: Production Hardening

- [x] Implement graceful shutdown in all services
- [x] Add startup validation in shared/config.py
- [ ] Document backup strategy
- [ ] Create recovery runbook
- [ ] Verify multi-tenant isolation with PBT

## Phase 4: Release

- [ ] Bump version to 1.0.0 in pyproject.toml
- [ ] Update CHANGELOG.md
- [ ] Run docker-compose verification
- [ ] Tag release v1.0.0
- [ ] Generate release notes