# Tasks

## Phase 1: Stream Context Helper
- [ ] 1.1 Create shared/stream_context.py
- [ ] 1.2 Implement TokenQueueContext
- [ ] 1.3 Add queue factory method

## Phase 2: AI Gateway Refactor
- [ ] 2.1 Remove module-level _token_queue
- [ ] 2.2 Accept queue as parameter
- [ ] 2.3 Return queue-aware response generator

## Phase 3: Route Integration
- [ ] 3.1 Update chat.py to create queue per request
- [ ] 3.2 Pass queue to stream_chat_completion
- [ ] 3.3 Clean up queue after SSE complete

## Phase 4: Testing
- [ ] 4.1 Unit tests without global state
- [ ] 4.2 Concurrent request isolation test
- [ ] 4.3 Cleanup verification