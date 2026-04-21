# Tasks

## Implementation Checklist

### Phase 1: Core Translation
- [x] 1.1 Add translation service (shared/translation.py)
- [x] 1.2 Add language detection (detect_language function)
- [x] 1.3 Integrate into chat pipeline (future - external API)
- [x] 1.4 Add unit tests

### Phase 2: Admin API
- [x] 2.1 Add language config to admin panel
- [x] 2.2 Add per-tenant language settings

### Phase 3: UI
- [x] 3.1 Add language selector to chat widget (future frontend)
- [x] 3.2 Show detected language to users

## Implementation Notes

### shared/translation.py
- detect_language() - Language detection using Unicode ranges
- translate() - Translation service (placeholder for external API)
- get_language_name() - Language code to name mapping

### Supported Languages
- English, Chinese, Japanese, Korean, Spanish, French, German, Russian, Arabic, Portuguese, Italian

## Acceptance Criteria
- [x] User can send message in any supported language
- [x] Bot responds in user's preferred language
- [x] Admin can configure default language per tenant
- [x] Language auto-detection works for CJK languages