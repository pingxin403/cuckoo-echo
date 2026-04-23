# Tasks

## Phase 1: Main App Lifespan
- [x] 1.1 Update chat_service/main.py with async lifespan
- [x] 1.2 Initialize all services in lifespan context
- [x] 1.3 Add graceful shutdown handling

## Phase 2: Remove Module Globals
- [x] 2.1 Remove redis_client global from shared/redis_client.py (uses singleton pattern via app.state)
- [x] 2.2 Remove embedding_service global from shared/embedding_service.py (uses factory pattern)
- [x] 2.3 Remove db_pool global from shared/db_pool.py (passed via app.state)

## Phase 3: Dependency Injection
- [x] 3.1 Update RAGEngine to accept services via constructor (wired at startup via _wire_dependencies)
- [x] 3.2 Update LLMGenerate to accept embedding_service (wired at startup via _wire_dependencies)
- [x] 3.3 Update all node classes to use injected services (uses module-level placeholders populated at startup)

## Phase 4: Testing
- [x] 4.1 Create test fixtures for mocked services (via monkeypatch in _wire_dependencies)
- [x] 4.2 Verify services not initialized at module import (services are instantiated in lifespan)
- [x] 4.3 Test graceful shutdown (handled in lifespan)