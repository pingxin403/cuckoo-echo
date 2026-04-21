# Agent Memory System Specification

## Overview

Comprehensive memory system for AI agents with episodic, semantic, and procedural memory layers following cognitive science principles.

## Goals
- Persistent user identity and preferences
- Conversation history with intelligent retrieval
- Knowledge extraction and consolidation
- Multi-tenant memory isolation

## Technical Design

### 1. Memory Taxonomy (Three-Layer Model)

#### Episodic Memory
- **Storage**: Complete interactions with timestamps
- **Retrieval**: Semantic similarity search
- **Metadata**: Session ID, user ID, importance score
- **Consolidation**: Extract patterns to semantic memory

#### Semantic Memory
- **User preferences**: Explicit preferences, implicit patterns
- **Entity knowledge**: User profile, organization facts
- **Relationship graphs**: User-tool preferences, topic interests
- **Storage**: Vector DB + structured database

#### Procedural Memory
- **Task patterns**: Successful execution sequences
- **Prompt templates**: Effective prompt patterns
- **Tool chains**: Proven tool combinations
- **Storage**: Versioned key-value store

### 2. Memory Hierarchy (Five Layers)

```
Layer 1: In-Context Working Memory
├── System prompt + User profile + Retrieved memories
└── Budget: ~180K tokens (large models), ~8K (edge)

Layer 2: Session Episodic Buffer (In-Process)
├── Recent conversation turns
└── Flushed to persistent store at session end

Layer 3: Persistent Episodic Memory
├── Vector database for semantic search
└── Full conversation history

Layer 4: Semantic Memory
├── User preferences
├── Extracted knowledge
└── Entity relationships

Layer 5: Procedural Memory
├── Task patterns
├── Tool chains
└── Prompt templates
```

### 3. Key Components

#### Memory Manager
- `store_memory()` - Store new memories
- `retrieve_memories()` - Semantic retrieval
- `consolidate()` - Episodic → Semantic
- `forget()` - Memory expiration

#### Importance Scoring
- Explicit importance (user标记)
- Implicit importance (repeated mentions)
- Temporal decay (recent优先)
- Relevance scoring (query-dependent)

#### Memory Consolidation
- **Immediate**: Critical signals processed in real-time
- **Session-end**: Full session summary
- **Background**: Periodic batch consolidation
- **Forgetting**: Low-importance memories expire

### 4. Storage Architecture

```
┌─────────────────────────────────────────────┐
│           Memory API Layer                  │
├─────────────────────────────────────────────┤
│  Working Memory  │  Session Buffer          │
├─────────────────────────────────────────────┤
│  Episodic Store  │  Semantic Store          │
│  (Vector DB)     │  (Vector + Graph DB)    │
├─────────────────────────────────────────────┤
│  Procedural Store │  Cache (Redis)          │
└─────────────────────────────────────────────┘
```

### 5. Retrieval Strategy

```python
def build_context(user_query: str, user_id: str) -> str:
    # 1. Retrieve semantic memories (user preferences)
    prefs = semantic_memory.retrieve(user_query, k=3)
    
    # 2. Find similar past episodes
    episodes = episodic_memory.recall(user_query, k=2)
    
    # 3. Check procedural memory for patterns
    patterns = procedural_memory.get_relevant(user_query)
    
    return format_context(prefs, episodes, patterns)
```

### 6. Multi-Tenant Isolation
- User-level memory segregation
- Organization-level shared memory
- Privacy-aware retrieval (no cross-tenant access)
- GDPR-compliant deletion

## Implementation Plan

### Phase 1: Core Memory
- [ ] 1.1 Memory data models
- [ ] 1.2 Vector store integration
- [ ] 1.3 Basic CRUD operations

### Phase 2: Retrieval
- [ ] 2.1 Semantic similarity search
- [ ] 2.2 Importance scoring
- [ ] 2.3 Context assembly

### Phase 3: Consolidation
- [ ] 3.1 Session summarization
- [ ] 3.2 Pattern extraction
- [ ] 3.3 Memory forgetting

### Phase 4: Advanced Features
- [ ] 4.1 Knowledge graphs
- [ ] 4.2 Procedural memory
- [ ] 4.3 Memory analytics

## Acceptance Criteria
- [ ] Users can retrieve past conversation context
- [ ] Preferences persist across sessions
- [ ] Memory retrieval < 100ms
- [ ] Multi-tenant isolation enforced
- [ ] GDPR deletion works