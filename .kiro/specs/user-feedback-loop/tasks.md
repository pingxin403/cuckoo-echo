# Implementation Plan: User Feedback Loop

## Overview

This feature adds a user feedback loop (👍/👎) to the Cuckoo-Echo AI chat platform. The implementation will add new routes and services for feedback collection, storage, and statistics, while integrating with existing Langfuse tracing. The changes are minimal and follow existing code patterns.

## Tasks

- [x] 1. Create database schema and migrations
  - [x] 1.1 Create feedback table migration (migrations/005_feedback_table.sql)
    - Add feedback table with thread_id, message_id, user_id, tenant_id, feedback_type, created_at, updated_at, partition_key, langfuse_trace_id, langfuse_span_id
    - Add unique constraint on (thread_id, message_id, user_id, tenant_id)
    - Add indexes for tenant_id, thread_id, message_id, partition_key
    - _Requirements: 2.1, 2.2, 3.4_
  
  - [x] 1.2 Create RLS policy migration
    - Add feedback_tenant_isolation policy using current_setting('app.current_tenant')
    - _Requirements: 3.2_
  
  - [x] 1.3 Add partition_key column to existing tables if needed
    - Verify tenant_id is present in threads and messages tables
    - _Requirements: 3.4_

- [x] 11. Frontend FeedbackPanel component
  - [x] 11.1 Create FeedbackPanel.tsx
    - Thumbs up/down buttons
    - API call to POST /v1/feedback
    - Toast notifications
    - _Location: frontend/src/pages/chat/FeedbackPanel.tsx
  
  - [x] 11.2 Integrate with MessageBubble
    - Show feedback buttons on assistant messages
    - Toggle feedback panel on thumb down
    - Submit feedback on button click
    - _Location: frontend/src/pages/chat/MessageBubble.tsx

- [x] 2. Create feedback service
  - [x] 2.1 Implement feedback storage
    - Create `chat_service/services/feedback.py`
    - Implement `store_feedback()` function with upsert logic
    - Implement `get_feedback_state()` function to retrieve current feedback
    - Implement `toggle_feedback()` function to remove feedback on same click
    - _Requirements: 1.2, 1.4, 2.4, 2.5_
  
  - [x] 2.2 Implement feedback statistics
    - Implement `get_feedback_stats()` function with filtering by thread_id and message_id
    - Calculate total, thumbs_up, thumbs_down, and percentages
    - Handle edge case of no feedback (return zero counts and null percentages)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  
  - [x] 2.3 Implement Langfuse integration
    - Implement `send_feedback_to_langfuse()` function
    - Send feedback event with prompt, response, feedback_type, and metadata
    - Make it async and non-blocking (fire and forget)
    - Handle Langfuse unavailability gracefully (log error, continue)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 3. Create feedback routes
  - [x] 3.1 Implement POST /v1/feedback endpoint
    - Create `chat_service/routes/feedback.py`
    - Validate request body (thread_id, message_id, feedback_type)
    - Check authentication and tenant_id from request.state
    - Call feedback service to store feedback
    - Return success response with feedback_state
    - Handle errors (400, 401, 403, 500)
    - _Requirements: 1.2, 7.1, 7.2, 7.3, 7.4_
  
  - [x] 3.2 Implement GET /v1/feedback/stats endpoint
    - Add query parameters for thread_id and message_id
    - Validate UUID format
    - Call feedback service to get statistics
    - Return statistics response
    - Handle errors (400, 401, 500)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 7.2_

- [x] 4. Integrate feedback with existing chat routes
  - [x] 4.1 Update chat_completions endpoint
    - Include feedback_state in SSE response for each message
    - _Requirements: 6.1, 6.2_
  
  - [x] 4.2 Update get_thread_history endpoint
    - Include feedback_state for each message in thread history
    - _Requirements: 6.1, 6.2_

- [x] 5. Update agent state
  - [x] 5.1 Add feedback_state to AgentState
    - Update `chat_service/agent/state.py`
    - Add feedback_state field to track current feedback
    - _Requirements: 6.1, 6.2_

- [x] 6. Add caching for feedback statistics
  - [x] 6.1 Implement Redis caching
    - Cache feedback statistics for 60 seconds
    - Use tenant_id + thread_id/message_id as cache key
    - Invalidate cache on feedback update
    - _Requirements: 8.4_

- [x] 7. Wire up dependencies
  - [x] 7.1 Register feedback routes in main.py
    - Import and include feedback router
    - _Requirements: All_
  
  - [x] 7.2 Inject feedback service into routes
    - Pass feedback service from app.state to routes
    - _Requirements: All_

- [x] 8. Write tests
  - [x] 8.1 Write unit tests for feedback service
    - Test store_feedback() with valid data
    - Test store_feedback() with duplicate (upsert)
    - Test toggle_feedback() (remove on same click)
    - Test get_feedback_state() for existing and non-existing feedback
    - Test get_feedback_stats() with various filters
    - Test Langfuse integration with mocks
    - _Requirements: All_
    - Note: 11 unit tests in tests/unit/test_feedback.py
   
  - [ ] 8.2 Write integration tests for feedback routes
    - Requires running infrastructure (docker compose)
    - Can be tested with make test-integration
   
  - [ ] 8.3 Write property-based tests
    - Requires real database + PBT setup
    - Can be added to tests/pbt/

- [x] 9. Update documentation
  - [x] 9.1 Update API documentation - Added POST /v1/feedback and GET /v1/feedback/stats
  - [x] 9.2 Update architecture documentation - Added User Feedback Loop section

- [x] 10. Final checkpoint - Unit tests pass
  - 11 unit tests passing

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases