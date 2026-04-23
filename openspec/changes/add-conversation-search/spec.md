# Add Conversation Search

## Overview

Full-text search across conversation history with filters for date range, topic, and tenant.

## Motivation

Users need to search past conversations. Current system provides no search capability for conversation history.

## Specification

### Core Features

1. **Full-Text Search**
   - Index message content
   - Support keyword and phrase search
   - Rank by relevance

2. **Filters**
   - Date range (from/to)
   - Topic tags
   - Message role (user/assistant)

3. **Results**
   - Return matching messages with context
   - Include thread metadata
   - Highlight matches

### File Changes

- `shared/conversation_search.py`: Search implementation
- `chat_service/routes/search.py`: API endpoints

## Acceptance Criteria

- [ ] Search returns messages within 500ms
- [ ] Results filtered by tenant
- [ ] Highlight search terms
- [ ] Pagination support