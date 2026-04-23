# Add Internationalization (i18n)

## Overview

Externalize all hardcoded strings and support Chinese/English localization.

## Motivation

Current system has hardcoded Chinese strings. Need i18n for:
- Multi-language support
- Easy string updates
- Translation workflows

## Specification

### Core Features

1. **String Externalization**
   - Move all strings to locale files
   - Key-based lookup
   - Default: English

2. **Locale Support**
   - English (en) - default
   - Chinese (zh)
   - Extensible for more

3. **Locale Detection**
   - HTTP Accept-Language header
   - Query parameter override
   - User preference storage

### File Changes

- `shared/i18n.py`: i18n utilities
- `locales/en.json`: English strings
- `locales/zh.json`: Chinese strings

## Acceptance Criteria

- [ ] All UI strings externalized
- [ ] Locale switching works
- [ ] No hardcoded strings in code
- [ ] New strings translatable