# Add Streaming Token Queue Refactor

## Overview

Replace module-level `_token_queue` with proper dependency injection for better testability and clean architecture.

## Motivation

Current implementation uses module-level `_token_queue` attribute hack. This couples streaming to global state and makes testing difficult.

## Specification

### Core Features

1. **Queue Factory Pattern**
   - Create token_queue in request context
   - Pass queue through dependency injection
   - No global state

2. **Context Manager**
   - Provide queue context manager
   - Auto-cleanup on request end
   - Thread-safe queue creation

3. **Stream Handler Integration**
   - Inject queue into stream response generator
   - Clean queue after SSE complete
   - Remove module-level attribute

### File Changes

- `ai_gateway/client.py`: Refactor to factory pattern
- `chat_service/routes/chat.py`: Provide queue dependency
- `shared/stream_context.py`: New context helper

## Acceptance Criteria

- [ ] No module-level _token_queue
- [ ] Queue created per request
- [ ] Queue cleaned up after SSE
- [ ] Unit tests without global state