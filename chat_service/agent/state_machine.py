"""Conversation state machine for intent tracking."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ConversationState(Enum):
    INITIAL = "initial"
    GREETING = "greeting"
    INTENT_CLARIFICATION = "clarification"
    ENTITY_COLLECTION = "collection"
    TASK_EXECUTION = "execution"
    CONFIRMATION = "confirmation"
    COMPLETION = "completion"
    ERROR = "error"


STATE_TRANSITIONS: dict[tuple[ConversationState, str], ConversationState] = {
    (ConversationState.INITIAL, "greeting"): ConversationState.GREETING,
    (ConversationState.INITIAL, "query"): ConversationState.TASK_EXECUTION,
    (ConversationState.INITIAL, "task"): ConversationState.ENTITY_COLLECTION,
    (ConversationState.INITIAL, "help"): ConversationState.GREETING,
    (ConversationState.INITIAL, "complaint"): ConversationState.ENTITY_COLLECTION,
    (ConversationState.GREETING, "query"): ConversationState.TASK_EXECUTION,
    (ConversationState.GREETING, "task"): ConversationState.ENTITY_COLLECTION,
    (ConversationState.ENTITY_COLLECTION, "complete"): ConversationState.TASK_EXECUTION,
    (ConversationState.TASK_EXECUTION, "confirm"): ConversationState.CONFIRMATION,
    (ConversationState.CONFIRMATION, "complete"): ConversationState.COMPLETION,
    (ConversationState.COMPLETION, "greeting"): ConversationState.INITIAL,
}


def next_state(
    current: ConversationState,
    intent: str,
    entities_complete: bool = True,
) -> ConversationState:
    """Determine next state based on current state and intent."""
    if not entities_complete and intent == "task":
        return ConversationState.ENTITY_COLLECTION

    key = (current, intent)
    return STATE_TRANSITIONS.get(key, ConversationState.INITIAL)


@dataclass
class ConversationContext:
    state: ConversationState = ConversationState.INITIAL
    current_intent: Optional[str] = None
    collected_entities: dict = field(default_factory=dict)
    unresolved_turns: int = 0
    last_topic: Optional[str] = None

    def update(self, intent: Optional[str] = None, entities: Optional[dict] = None):
        if intent:
            self.current_intent = intent
        if entities:
            self.collected_entities.update(entities)

        if self.current_intent:
            self.state = next_state(
                self.state,
                self.current_intent,
                len(self.collected_entities) > 0,
            )

    def increment_unresolved(self):
        self.unresolved_turns += 1

    def reset_unresolved(self):
        self.unresolved_turns = 0
