"""Output filtering for Layer 3 guardrails."""

from __future__ import annotations

import re
import structlog

logger = structlog.get_logger(__name__)

TOXIC_PATTERNS = [
    re.compile(r"\b(hate|violent|explicit)\b", re.I),
]


class OutputFilter:
    def __init__(self, hallucination_threshold: float = 0.7):
        self.hallucination_threshold = hallucination_threshold
        self._toxic_words = {"hate", "violent", "explicit", "harmful"}

    def check_toxicity(self, text: str) -> float:
        if not text:
            return 0.0
        toxic_count = sum(1 for word in self._toxic_words if word in text.lower())
        return min(toxic_count / 3.0, 1.0)

    def check_hallucination(self, text: str, sources: list[str] | None = None) -> float:
        if not sources:
            return 0.5
        text_lower = text.lower()
        source_matches = sum(1 for src in sources if src.lower() in text_lower)
        if not source_matches:
            return 0.8
        return max(0.0, 1.0 - (source_matches / len(sources)))

    def filter_output(self, text: str) -> str:
        for pattern in TOXIC_PATTERNS:
            text = pattern.sub("[FILTERED]", text)
        return text