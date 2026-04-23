# Add Conversation Export

## Overview

Export conversation history as JSON, Markdown, or PDF.

## Motivation

Users need to export conversations for:
- Archival purposes
- Sharing with team
- Compliance requirements

## Specification

### Core Features

1. **Export Formats**
   - JSON: Structured data
   - Markdown: Human-readable
   - PDF: Print-friendly

2. **Export Options**
   - Full conversation
   - Date range filter
   - Include/exclude metadata

3. **Delivery**
   - Download link (JSON/Markdown)
   - Email with attachment (PDF)
   - API response

### File Changes

- `chat_service/services/export.py`: Export service
- `chat_service/routes/export.py`: Export endpoints

## Acceptance Criteria

- [ ] JSON export works
- [ ] Markdown export formatted
- [ ] PDF export readable
- [ ] Date filter works