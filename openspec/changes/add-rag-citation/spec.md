# RAG Factual Citation & Input Rewriting Specification

## Overview

RAG system enhancements for factual citation, input rewriting, and answer grounding to improve response accuracy and trustworthiness.

## Goals

- Source attribution with precise citations
- Input rewriting for better retrieval
- Answer grounding with fact verification
- Hallucination prevention

## Technical Design

### 1. Factual Citation

#### Source Attribution
- **Inline citations**: `[source_id]` markers in generated text
- **Citation metadata**: Source title, URL, confidence score, excerpt
- **Citation chains**: Trace claims to source documents

#### Citation Types
```python
class CitationType(Enum):
    EXACT_MATCH = "exact"      # Word-for-word from source
    SEMANTIC_MATCH = "semantic" # Paraphrased from source
    INFERRED = "inferred"      # Derived from multiple sources
    NO_CITATION = "none"       # General knowledge
```

#### Citation Formatting
```python
def format_citation(source: Source, span: TextSpan) -> str:
    return f"[{source.id}]({source.title}|{source.url})"

def format_source_card(sources: list[Source]) -> SourceCard:
    return SourceCard(
        items=[SourceItem(id=s.id, title=s.title, url=s.url, excerpt=s.excerpt)
              for s in sources],
        confidence=compute_confidence(sources)
    )
```

### 2. Input Rewriting

#### Query Expansion
```python
async def expand_query(query: str, user_context: Context) -> list[str]:
    expansions = [
        query,                           # Original
        f"{query} definition",            # Clarification
        f"{query} example",               # Examples
        f"{query} how to",               # Instructions
        f"why {query}",                  # Rationale
    ]
    return await llm.generate_unique(expansions)
```

#### Query Decomposition
```python
def decompose_query(query: str) -> list[SubQuery]:
    return [
        SubQuery(text=q, intent=classify_intent(q))
        for q in split_compound_query(query)
    ]
```

#### Hallucination Prevention
- **Uncertainty marking**: `[?]` for low-confidence claims
- **Source requirement**: Claims must have citation
- **Contradiction detection**: Flag conflicting sources

### 3. Answer Grounding

#### Fact Verification Pipeline
```python
async def verify_answer(answer: str, sources: list[Source]) -> VerificationResult:
    claims = extract_claims(answer)
    verified = []
    for claim in claims:
        matches = find_source_matches(claim, sources)
        verified.append(ClaimVerification(
            claim=claim,
            supported=len(matches) > 0,
            confidence=sum(s.confidence for s in matches) / len(matches),
            sources=matches
        ))
    return VerificationResult(claims=verified)
```

#### Confidence Scoring
```python
def compute_answer_confidence(verification: VerificationResult) -> float:
    if not verification.claims:
        return 0.5
    supported = sum(1 for c in verification.claims if c.supported)
    weights = [c.confidence for c in verification.claims]
    return supported / len(verification.claims) * mean(weights)
```

### 4. Citation UI Components

#### Inline Citation
```markdown
According to our documentation,[1](API Reference|link)...
```

#### Source Card
```html
<div class="source-card">
  <div class="source-item" data-source-id="1">
    <span class="source-number">[1]</span>
    <span class="source-title">API Reference</span>
    <a href="...">View Source</a>
  </div>
</div>
```

## Implementation Plan

### Phase 1: Citation Foundation
- [ ] 1.1 Citation data model
- [ ] 1.2 Inline citation parsing
- [ ] 1.3 Source attribution pipeline

### Phase 2: Input Rewriting
- [ ] 2.1 Query expansion
- [ ] 2.2 Query decomposition
- [ ] 2.3 Hallucination detection

### Phase 3: Answer Grounding
- [ ] 3.1 Fact verification
- [ ] 3.2 Confidence scoring
- [ ] 3.3 Source card rendering

### Phase 4: UI Components
- [ ] 4.1 Citation component
- [ ] 4.2 Source card component
- [ ] 4.3 Hover preview

## Acceptance Criteria

- [ ] All factual claims have citations
- [ ] Inline citations render correctly
- [ ] Source cards show metadata
- [ ] Confidence scores are accurate
- [ ] Hallucination rate reduced