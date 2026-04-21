# Real-time Translation Feature Specification

## Overview

Add real-time translation support for multilingual conversations.

## Goals
- Support 10+ languages
- Auto-detect source language
- Translate user messages and bot responses
- Admin language configuration per tenant

## Technical Design

### Database Schema
- Add `language_preference` column to `tenants` table
- Store default source/target language per tenant

### API Changes
- Add `x-target-language` header to Chat API
- Add `POST /v1/translate` endpoint for content translation

### Translation Service
- Use LibreTranslate (self-hosted) or Google Translate API
- Cache translations to reduce API calls

## Implementation Plan

### Phase 1: Core Translation
1.1 Add translation service (shared/translation.py)
1.2 Add language detection
1.3 Integrate into chat pipeline

### Phase 2: Admin API
2.1 Add language config to admin panel
2.2 Add per-tenant language settings

### Phase 3: UI
3.1 Add language selector to chat widget
3.2 Show detected language to users

## Acceptance Criteria
- [ ] User can send message in any supported language
- [ ] Bot responds in user's preferred language
- [ ] Admin can configure default language per tenant
- [ ] Language auto-detection accuracy > 90%