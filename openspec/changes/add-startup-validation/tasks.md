# Tasks / 任务清单

## Phase 1: Core Implementation

- [ ] Add field validators to Settings class in shared/config.py
- [ ] Add validate_dsn helper functions
- [ ] Add check_startup() method
- [ ] Add startup check to all services lifespan

## Phase 2: Validation Rules

- [ ] Validate DATABASE_URL PostgreSQL DSN format
- [ ] Validate REDIS_URL Redis DSN format
- [ ] Validate MILVUS_ADDR host:port format
- [ ] Validate OPENAI_API_KEY presence
- [ ] Validate LANGFUSE_* keys (optional)

## Phase 3: Connectivity Checks

- [ ] Add PostgreSQL connectivity test
- [ ] Add Redis connectivity test
- [ ] Add Milvus connectivity test (warn-only)
- [ ] Add AI Gateway connectivity test (warn-only)

## Phase 4: Integration

- [ ] Integrate with existing health checks
- [ ] Add startup logging
- [ ] Document required env vars

## Phase 5: Testing

- [ ] Test validation failures show clear errors
- [ ] Test startup connectivity warnings
- [ ] Integration tests for validation