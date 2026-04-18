# Requirements Document: User Feedback Loop

## Introduction

This feature adds a user feedback loop (👍/👎) to the Cuckoo-Echo AI chat platform. The feedback loop is the "fuel" for all other improvements including RAG evaluation, Prompt optimization, and model selection. Users can provide feedback on individual chat messages, and this data will be stored for analysis and continuous improvement of the AI system.

## Glossary

- **Cuckoo-Echo**: The AI chat platform that provides conversational AI services
- **Chat Service**: The FastAPI + LangGraph microservice that handles chat completions
- **Thread**: A conversation thread between a user and the AI
- **Message**: An individual message in a chat thread (user or AI)
- **Feedback**: User-provided thumbs up/down rating on a message
- **PartitionKey**: Multi-tenant isolation identifier derived from tenant_id
- **RLS**: Row Level Security in PostgreSQL for multi-tenant data isolation
- **Langfuse**: LLM tracing and observability platform
- **SSE**: Server-Sent Events for streaming chat responses

## Requirements

### Requirement 1: Feedback Collection

**User Story:** As a user, I want to provide feedback on AI responses, so that the system can learn from my interactions and improve future responses.

#### Acceptance Criteria

1. WHEN a user views a chat message, THE UI SHALL display thumbs up (👍) and thumbs down (👎) buttons
2. WHEN a user clicks a feedback button, THE Chat Service SHALL record the feedback with timestamp
3. WHILE a user is viewing a chat thread, THE UI SHALL display the current feedback state for each message
4. IF a user clicks the same feedback button twice, THE Chat Service SHALL toggle the feedback off (remove it)
5. WHERE a user has not provided feedback, THE UI SHALL display neutral feedback icons

### Requirement 2: Data Storage

**User Story:** As a system administrator, I want feedback data to be stored persistently, so that it can be used for analysis and model improvement.

#### Acceptance Criteria

1. WHEN feedback is recorded, THE PostgreSQL database SHALL store the feedback record
2. THE feedback record SHALL include thread_id, message_id, user_id, tenant_id, feedback_type, and timestamp
3. WHILE data is being stored, THE system SHALL maintain multi-tenant isolation using PartitionKey
4. IF a feedback record already exists for a message, THE system SHALL update the existing record instead of creating a duplicate
5. WHEN feedback is updated, THE system SHALL preserve the original creation timestamp and only update the feedback_type

### Requirement 3: Multi-Tenant Isolation

**User Story:** As a platform operator, I want feedback data to be isolated per tenant, so that tenants cannot access each other's feedback data.

#### Acceptance Criteria

1. WHEN feedback is queried, THE system SHALL only return feedback for the current tenant
2. WHILE storing feedback, THE system SHALL enforce Row Level Security (RLS) policies
3. IF a user attempts to access feedback from another tenant, THE system SHALL return an empty result
4. THE PartitionKey SHALL be derived from the authenticated user's tenant_id
5. WHEN feedback statistics are calculated, THE system SHALL only include feedback from the current tenant

### Requirement 4: Feedback Statistics API

**User Story:** As a product manager, I want to view feedback statistics, so that I can understand user satisfaction and identify areas for improvement.

#### Acceptance Criteria

1. WHEN a request for feedback statistics is made, THE API SHALL return total feedback count, thumbs up count, and thumbs down count
2. WHERE a thread_id is provided, THE API SHALL filter statistics to that specific thread
3. WHERE a message_id is provided, THE API SHALL return statistics for that specific message
4. WHEN statistics are requested, THE system SHALL calculate percentages (thumbs_up_percentage, thumbs_down_percentage)
5. IF no feedback exists for the requested scope, THE API SHALL return zero counts and null percentages

### Requirement 5: Integration with Langfuse

**User Story:** As a data scientist, I want feedback data to be available in Langfuse, so that I can correlate user feedback with LLM performance metrics.

#### Acceptance Criteria

1. WHEN feedback is recorded, THE system SHALL send a feedback event to Langfuse
2. THE Langfuse feedback event SHALL include the original prompt, response, and user feedback
3. WHEN Langfuse trace is updated with feedback, THE system SHALL include thread_id and message_id as metadata
4. IF Langfuse is unavailable, THE system SHALL log the error but continue processing feedback
5. THE feedback event SHALL be sent asynchronously to avoid blocking the response

### Requirement 6: Frontend Integration

**User Story:** As a frontend developer, I want clear API specifications for feedback buttons, so that I can implement the UI correctly.

#### Acceptance Criteria

1. WHEN a message is received via SSE, THE response SHALL include feedback_state field
2. THE feedback_state field SHALL indicate current feedback type (null, "thumbs_up", "thumbs_down")
3. WHEN feedback is submitted, THE API SHALL return the updated feedback state
4. THE UI SHALL provide visual feedback when feedback is submitted (button state change)
5. WHERE SSE streaming is not available, THE UI SHALL fall back to polling the feedback endpoint

### Requirement 7: Error Handling

**User Story:** As a user, I want clear error messages when feedback fails, so that I know if my feedback was not recorded.

#### Acceptance Criteria

1. IF the database fails to store feedback, THE system SHALL return a 500 error with descriptive message
2. IF authentication fails, THE system SHALL return a 401 error
3. IF the thread_id or message_id is invalid, THE system SHALL return a 400 error
4. IF a user attempts to provide feedback on a message they did not receive, THE system SHALL return a 403 error
5. WHEN an error occurs, THE system SHALL log the error with context (thread_id, message_id, user_id)

### Requirement 8: Performance

**User Story:** As a platform operator, I want feedback operations to be fast, so that they don't impact chat response latency.

#### Acceptance Criteria

1. WHEN feedback is recorded, THE API response time SHALL be under 100ms for 95% of requests
2. WHEN feedback statistics are requested, THE API response time SHALL be under 200ms for 95% of requests
3. THE feedback recording operation SHALL NOT block the SSE stream
4. IF feedback statistics are requested frequently, THE system SHALL cache results for up to 60 seconds
5. WHEN bulk feedback operations are performed, THE system SHALL handle concurrent requests without deadlocks
