# Tasks

## Implementation Checklist

### Phase 1: Core Translation
- [x] 1.1 Add translation service (shared/translation.py)
- [x] 1.2 Add language detection (detect_language function)
- [ ] 1.3 Integrate into chat pipeline (future - external API)
- [ ] 1.4 Add unit tests

### Phase 2: Admin API
- [ ] 2.1 Add language config to admin panel
- [ ] 2.2 Add per-tenant language settings

### Phase 3: UI
- [ ] 3.1 Add language selector to chat widget
- [ ] 3.2 Show detected language to users

## Implementation Notes

### shared/translation.py
- detect_language() - Language detection using Unicode ranges
- translate() - Translation service (placeholder for external API)
- get_language_name() - Language code to name mapping

### Supported Languages
- English, Chinese, Japanese, Korean, Spanish, French, German, Russian, Arabic, Portuguese, Italian

## Acceptance Criteria
- [ ] User can send message in any supported language
- [ ] Bot responds in user's preferred language
- [ ] Admin can configure default language per tenant
- [ ] Language auto-detection works for CJK languages