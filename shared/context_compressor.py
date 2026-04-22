"""Smart context compression with importance scoring."""

from __future__ import annotations

import structlog
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

logger = structlog.get_logger(__name__)


@dataclass
class Message:
    role: str
    content: str
    timestamp: datetime | None = None
    metadata: dict[str, Any] | None = None


class ContextCompressor:
    PRIORITY_SCORES = {
        "tool": 1.0,
        "preference": 0.9,
        "system": 0.6,
        "user": 0.5,
        "assistant": 0.3,
    }

    def __init__(self, max_tokens: int = 128000):
        self.max_tokens = max_tokens
        self.avg_chars_per_token = 4

    def compress(self, messages: list[Message], budget: int) -> list[Message]:
        if not messages:
            return []

        scored = [(self.score_importance(m), m) for m in messages]
        scored.sort(key=lambda x: x[0], reverse=True)

        result = []
        current_tokens = 0
        for score, msg in scored:
            msg_tokens = len(msg.content) // self.avg_chars_per_token
            if current_tokens + msg_tokens <= budget:
                result.append(msg)
                current_tokens += msg_tokens

        result.sort(key=lambda m: m.timestamp or datetime.min)
        return result

    def score_importance(self, msg: Message) -> float:
        if msg.metadata and msg.metadata.get("is_tool_result"):
            return self.PRIORITY_SCORES["tool"]
        if "prefer" in msg.content.lower() or "always" in msg.content.lower():
            return self.PRIORITY_SCORES["preference"]
        if msg.role == "system":
            return self.PRIORITY_SCORES["system"]
        return self.PRIORITY_SCORES.get(msg.role, 0.3)

    def prune_irrelevant(self, messages: list[Message], query: str) -> list[Message]:
        if not query:
            return messages[-10:]

        query_terms = set(query.lower().split())
        relevant = []
        for msg in messages:
            content_lower = msg.content.lower()
            if any(term in content_lower for term in query_terms):
                relevant.append(msg)

        if not relevant:
            return messages[-10:]
        return relevant