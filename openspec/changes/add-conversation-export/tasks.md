# Tasks / 任务清单

## Phase 1: Core Implementation

- [ ] Add export endpoint to admin_service/routes/conversations.py
- [ ] Create export job model in database
- [ ] Implement JSON export formatter
- [ ] Implement CSV export formatter
- [ ] Implement Markdown export formatter

## Phase 2: Async Export

- [ ] Create background worker for large exports
- [ ] Add job status endpoint
- [ ] Add download endpoint
- [ ] Implement pagination

## Phase 3: Filtering

- [ ] Add date range filtering
- [ ] Add status filtering
- [ ] Add message count filtering
- [ ] Add export audit logging

## Phase 4: Testing

- [ ] Unit tests for formatters
- [ ] Integration tests for export API
- [ ] Test large export async job flow