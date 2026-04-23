# Tasks / 任务清单

## Phase 1: Core Implementation

- [ ] Create shared/shutdown.py with graceful shutdown handlers
- [ ] Register lifespan in chat_service/main.py
- [ ] Register lifespan in admin_service/main.py
- [ ] Register lifespan in api_gateway/main.py
- [ ] Register lifespan in asr_service/main.py
- [ ] Add shutdown state to health checks

## Phase 2: Integration

- [ ] Test SIGTERM handling
- [ ] Test SIGINT handling
- [ ] Verify connection cleanup
- [ ] Verify checkpointer flush

## Phase 3: Documentation

- [ ] Update architecture.md with shutdown flow
- [ ] Document deployment best practices