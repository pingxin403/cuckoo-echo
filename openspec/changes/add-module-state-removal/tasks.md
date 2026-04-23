# Tasks

## Phase 1: Main App Lifespan
- [ ] 1.1 Update chat_service/main.py with async lifespan
- [ ] 1.2 Initialize all services in lifespan context
- [ ] 1.3 Add graceful shutdown handling

## Phase 2: Remove Module Globals
- [ ] 2.1 Remove redis_client global from shared/redis_client.py
- [ ] 2.2 Remove embedding_service global from shared/embedding_service.py
- [ ] 2.3 Remove db_pool global from shared/db_pool.py

## Phase 3: Dependency Injection
- [ ] 3.1 Update RAGEngine to accept services via constructor
- [ ] 3.2 Update LLMGenerate to accept embedding_service
- [ ] 3.3 Update all node classes to use injected services

## Phase 4: Testing
- [ ] 4.1 Create test fixtures for mocked services
- [ ] 4.2 Verify services not initialized at module import
- [ ] 4.3 Test graceful shutdown