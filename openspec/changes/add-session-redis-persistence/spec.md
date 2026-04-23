# Add Session Redis Persistence

## Overview

Migrate SessionManager from in-memory storage to Redis-backed storage for multi-instance deployment.

## Motivation

Current SessionManager uses in-memory dict. In multi-instance deployment (K8s), requests may hit different pods, losing session context. Redis provides shared session state.

## Specification

### Core Features

1. **Redis Backend**
   - Store sessions in Redis with TTL
   - Key format: `session:{tenant_id}:{session_id}`
   - Default TTL: 24 hours

2. **Session Operations**
   - Get/create session from Redis
   - Update session with atomic operations
   - Delete session on user request

3. **Fallback**
   - If Redis unavailable, fall back to in-memory
   - Log warning for degraded mode
   - Continue with limited functionality

### File Changes

- `shared/session_store.py`: Redis session backend (new)
- `chat_service/agent/session_manager.py`: Use session_store

## Acceptance Criteria

- [ ] Sessions persist across pod restarts
- [ ] Redis failure gracefully handled
- [ ] Session TTL configurable
- [ ] Performance <10ms overhead per operation