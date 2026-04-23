# Tasks

## Phase 1: Redis Session Store
- [ ] 1.1 Create shared/session_store.py
- [ ] 1.2 Implement Redis session backend
- [ ] 1.3 Add TTL configuration

## Phase 2: Session Manager Integration
- [ ] 2.1 Update session_manager.py to use session_store
- [ ] 2.2 Add fallback to in-memory on Redis failure
- [ ] 2.3 Keep in-memory for unit test compatibility

## Phase 3: Atomic Operations
- [ ] 3.1 Use Redis pipeline for batch operations
- [ ] 3.2 Add session lock for concurrent updates
- [ ] 3.3 Verify transaction semantics

## Phase 4: Testing
- [ ] 4.1 Unit tests with mocked Redis
- [ ] 4.2 Integration tests with real Redis
- [ ] 4.3 Performance benchmark