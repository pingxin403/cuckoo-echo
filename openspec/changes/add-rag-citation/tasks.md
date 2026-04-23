# RAG Citation & Input Rewriting Tasks

## Phase 1: Citation Foundation

### 1.1 Citation Data Model
- [x] Create `Citation` Pydantic model
- [x] Add `source_id`, `span_start`, `span_end`, `citation_type` fields
- [x] Add `confidence`, `excerpt`, `url` fields
- [x] Create migration for citation table

### 1.2 Inline Citation Parsing
- [x] Implement citation parser regex
- [x] Handle `[source_id]` markers in text
- [x] Support multi-source citations `[1,2,3]`
- [x] Add parser unit tests

### 1.3 Source Attribution Pipeline
- [x] Track source documents during retrieval
- [x] Map retrieved chunks to source IDs
- [x] Store source metadata (title, URL, timestamp)
- [x] Implement source deduplication

## Phase 2: Input Rewriting

### 2.1 Query Expansion
- [x] Create query expansion prompt template
- [x] Implement expansion with LLM
- [x] Add deduplication for expanded queries
- [x] Add caching for repeated queries

### 2.2 Query Decomposition
- [x] Detect compound queries (AND, OR, BUT)
- [x] Extract atomic sub-queries
- [x] Classify sub-query intent
- [x] Handle dependent vs independent sub-queries

### 2.3 Hallucination Detection
- [x] Implement claim extraction
- [x] Add source verification for claims
- [x] Flag unsupported claims
- [x] Add uncertainty markers `[?]`

## Phase 3: Answer Grounding

### 3.1 Fact Verification
- [x] Implement NER for factual claims
- [x] Create claim-source matching
- [x] Handle partial matches
- [x] Add verification caching

### 3.2 Confidence Scoring
- [x] Compute source confidence scores
- [x] Aggregate claim confidence
- [x] Calculate overall answer confidence
- [x] Add confidence thresholds

### 3.3 Source Card Rendering
- [x] Create source card data structure
- [x] Implement source card API endpoint
- [x] Add source preview generation
- [x] Handle source errors gracefully

## Phase 4: UI Components

### 4.1 Citation Component
- [x] Create React Citation component
- [x] Handle hover tooltips
- [x] Support click-to-scroll
- [x] Add mobile touch support

### 4.2 Source Card Component
- [x] Create SourceCard component
- [x] Add source list rendering
- [x] Implement source preview
- [x] Add copy citation button

### 4.3 Hover Preview
- [x] Implement source preview popup
- [x] Add excerpt highlighting
- [x] Handle long sources (truncation)
- [x] Add lazy loading

## Dependencies

- Existing: `optimize-rag-recall` (hybrid search, reranking)
- New: None required

## Testing Strategy

- Unit tests for citation parsing
- Integration tests for verification pipeline
- E2E tests for UI components
- Performance tests for confidence scoring