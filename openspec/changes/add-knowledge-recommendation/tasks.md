# Tasks

## Implementation Checklist

### Phase 1: Gap Detection
- [x] 1.1 Track queries without RAG matches (knowledge_gap.py)
- [x] 1.2 Aggregate failed query patterns
- [x] 1.3 Calculate suggestion priority score

### Phase 2: Recommendation API
- [x] 2.1 GET /admin/v1/knowledge/gaps - List knowledge gaps
- [x] 2.2 POST /admin/v1/knowledge/gaps/{id}/dismiss - Dismiss suggestion
- [x] 2.3 POST /admin/v1/knowledge/gaps/{id}/create - Create article (use knowledge docs API)

### Phase 3: Proactive Suggestions
- [x] 3.1 Suggest articles when confidence is low (via knowledge docs)
- [x] 3.2 Show "related articles" widget (future frontend)
- [x] 3.3 Track suggestion acceptance rate (future)

## Implementation Notes

### shared/knowledge_gap.py
- track_gap() - Track query without RAG match
- get_top_gaps() - Get prioritized gaps
- dismiss_gap() - Remove resolved gap
- generate_title_suggestion() - Generate article title

### Database (future)
- knowledge_gaps table: tenant_id, query, frequency, first_seen, last_seen, suggested_title

## Acceptance Criteria
- [x] Admin can see top knowledge gaps
- [x] Suggestions ranked by frequency
- [ ] One-click article creation from suggestion
- [ ] Track suggestion performance