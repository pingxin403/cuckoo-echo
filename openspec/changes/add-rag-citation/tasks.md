# RAG Citation & Input Rewriting Tasks

## Phase 1: Citation Foundation

### 1.1 Citation Data Model
- [ ] Create `Citation` Pydantic model
- [ ] Add `source_id`, `span_start`, `span_end`, `citation_type` fields
- [ ] Add `confidence`, `excerpt`, `url` fields
- [ ] Create migration for citation table

### 1.2 Inline Citation Parsing
- [ ] Implement citation parser regex
- [ ] Handle `[source_id]` markers in text
- [ ] Support multi-source citations `[1,2,3]`
- [ ] Add parser unit tests

### 1.3 Source Attribution Pipeline
- [ ] Track source documents during retrieval
- [ ] Map retrieved chunks to source IDs
- [ ] Store source metadata (title, URL, timestamp)
- [ ] Implement source deduplication

## Phase 2: Input Rewriting

### 2.1 Query Expansion
- [ ] Create query expansion prompt template
- [ ] Implement expansion with LLM
- [ ] Add deduplication for expanded queries
- [ ] Add caching for repeated queries

### 2.2 Query Decomposition
- [ ] Detect compound queries (AND, OR, BUT)
- [ ] Extract atomic sub-queries
- [ ] Classify sub-query intent
- [ ] Handle dependent vs independent sub-queries

### 2.3 Hallucination Detection
- [ ] Implement claim extraction
- [ ] Add source verification for claims
- [ ] Flag unsupported claims
- [ ] Add uncertainty markers `[?]`

## Phase 3: Answer Grounding

### 3.1 Fact Verification
- [ ] Implement NER for factual claims
- [ ] Create claim-source matching
- [ ] Handle partial matches
- [ ] Add verification caching

### 3.2 Confidence Scoring
- [ ] Compute source confidence scores
- [ ] Aggregate claim confidence
- [ ] Calculate overall answer confidence
- [ ] Add confidence thresholds

### 3.3 Source Card Rendering
- [ ] Create source card data structure
- [ ] Implement source card API endpoint
- [ ] Add source preview generation
- [ ] Handle source errors gracefully

## Phase 4: UI Components

### 4.1 Citation Component
- [ ] Create React Citation component
- [ ] Handle hover tooltips
- [ ] Support click-to-scroll
- [ ] Add mobile touch support

### 4.2 Source Card Component
- [ ] Create SourceCard component
- [ ] Add source list rendering
- [ ] Implement source preview
- [ ] Add copy citation button

### 4.3 Hover Preview
- [ ] Implement source preview popup
- [ ] Add excerpt highlighting
- [ ] Handle long sources (truncation)
- [ ] Add lazy loading

## Dependencies

- Existing: `optimize-rag-recall` (hybrid search, reranking)
- New: None required

## Testing Strategy

- Unit tests for citation parsing
- Integration tests for verification pipeline
- E2E tests for UI components
- Performance tests for confidence scoring