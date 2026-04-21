# User Intent Recognition Specification

## Overview

Advanced user intent recognition system for accurate understanding of user goals, entities, and conversation flow.

## Goals

- Multi-level intent classification
- Entity extraction and resolution
- Conversation state tracking
- Intent switching detection

## Technical Design

### 1. Intent Classification

#### Intent Hierarchy
```python
class IntentLevel(Enum):
    DOMAIN = "domain"        # Greeting, Help, Complaint
    TASK = "task"           # Query, Action, Transaction
    SUBTASK = "subtask"     # Specific action type
    PARAMETER = "parameter" # Action modifiers
```

#### Intent Types
```python
INTENTS = {
    "greeting": ["hello", "hi", "hey"],
    "query": ["what", "how", "why", "when", "where"],
    "task": {
        "search": ["find", "search", "look for"],
        "create": ["create", "add", "new"],
        "update": ["edit", "modify", "change"],
        "delete": ["delete", "remove", "cancel"],
        "execute": ["run", "do", "perform"],
    },
    "help": ["help", "support", "assist"],
    "complaint": ["problem", "issue", "broken", "wrong"],
    "feedback": ["feedback", "suggest", "improve"],
}
```

#### Classification Pipeline
```python
class IntentClassifier:
    def __init__(self):
        self.hierarchical = HierarchicalClassifier()
        self.llm_fallback = LLMClassifier()
        self.confidence_threshold = 0.7

    async def classify(self, message: str, context: ConversationContext) -> IntentResult:
        # Rule-based fast path
        result = self.hierarchical.classify(message)
        if result.confidence >= self.confidence_threshold:
            return result

        # LLM enhanced classification
        return await self.llm_fallback.classify(message, context)
```

### 2. Entity Extraction

#### Entity Types
```python
ENTITY_TYPES = {
    "person": ["user", "customer", "admin"],
    "organization": ["company", "team", "department"],
    "datetime": ["date", "time", "duration", "frequency"],
    "number": ["quantity", "price", "percentage"],
    "location": ["address", "city", "country"],
    "product": ["item", "service", "subscription"],
    "status": ["pending", "active", "completed", "failed"],
}
```

#### Extraction Implementation
```python
async def extract_entities(message: str, intent: Intent) -> list[Entity]:
    # Named entity recognition
    ner_entities = await ner.extract(message)

    # Slot filling based on intent
    slot_entities = await fill_slots(message, intent.slots)

    # Entity resolution
    resolved = await resolve_entities(ner_entities + slot_entities)

    return resolved

def resolve_entities(entities: list[Entity]) -> list[Entity]:
    # Link to known entities
    # Disambiguate ambiguous mentions
    # Resolve co-references
    return resolved_entities
```

### 3. Conversation State

#### State Machine
```python
class ConversationState(Enum):
    INITIAL = "initial"
    GREETING = "greeting"
    INTENT_CLARIFICATION = "clarification"
    ENTITY_COLLECTION = "collection"
    TASK_EXECUTION = "execution"
    CONFIRMATION = "confirmation"
    COMPLETION = "completion"
    ERROR = "error"
```

#### State Transitions
```python
def next_state(current: ConversationState, intent: Intent, entities: list[Entity]) -> ConversationState:
    transitions = {
        (ConversationState.INITIAL, "greeting"): ConversationState.GREETING,
        (ConversationState.INITIAL, "query"): ConversationState.TASK_EXECUTION,
        (ConversationState.INITIAL, "task"): ConversationState.ENTITY_COLLECTION,
        (ConversationState.ENTITY_COLLECTION, None): ConversationState.TASK_EXECUTION,
        (ConversationState.TASK_EXECUTION, "confirm"): ConversationState.CONFIRMATION,
        (ConversationState.CONFIRMATION, "complete"): ConversationState.COMPLETION,
    }
    return transitions.get((current, intent.type), ConversationState.INITIAL)
```

### 4. Intent Switching

#### Multi-Intent Detection
```python
def detect_multi_intent(message: str) -> list[Intent]:
    # Detect conjunctions
    if " and " in message or " also " in message:
        parts = split_by_conjunction(message)
        return [classify(p) for p in parts]

    # Detect sequential intents
    if detect_sequence_markers(message):
        return classify_sequence(message)

    return [classify(message)]
```

#### Handling Ambiguity
```python
async def resolve_ambiguity(message: str, intents: list[Intent]) -> Intent:
    if len(intents) == 1:
        return intents[0]

    # Ask clarification question
    clarification = generate_clarification(intents)
    return ClarificationIntent(clarification, intents)
```

### 5. Confidence Scoring

```python
def compute_confidence(classification: IntentClassification) -> float:
    scores = {
        "intent_match": classification.intent_score,
        "entity_coverage": len(found_entities) / len(required_entities),
        "context_consistency": context_score,
        "historical_accuracy": user_history_accuracy,
    }

    weights = {"intent_match": 0.4, "entity_coverage": 0.3,
               "context_consistency": 0.2, "historical_accuracy": 0.1}

    return sum(scores[k] * weights[k] for k in weights)
```

## Implementation Plan

### Phase 1: Core Classification
- [ ] 1.1 Intent hierarchy model
- [ ] 1.2 Rule-based classifier
- [ ] 1.3 LLM fallback classifier

### Phase 2: Entity Extraction
- [ ] 2.1 NER integration
- [ ] 2.2 Slot filling
- [ ] 2.3 Entity resolution

### Phase 3: State Management
- [ ] 3.1 State machine
- [ ] 3.2 State transitions
- [ ] 3.3 Context persistence

### Phase 4: Advanced Features
- [ ] 4.1 Multi-intent detection
- [ ] 4.2 Ambiguity resolution
- [ ] 4.3 Confidence scoring

## Acceptance Criteria

- [ ] Intent accuracy > 90%
- [ ] Entity F1 score > 0.85
- [ ] State tracking works correctly
- [ ] Multi-intent detection works
- [ ] Confidence scores are reliable