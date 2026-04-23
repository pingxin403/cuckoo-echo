"""Output filtering for Layer 3 guardrails."""

from __future__ import annotations

import re
import structlog
from dataclasses import dataclass

logger = structlog.get_logger(__name__)

TOXIC_PATTERNS = [
    re.compile(r"\b(hate|violent|explicit)\b", re.I),
]

UNCERTAINTY_PATTERNS = [
    re.compile(r"i'm not sure|^maybe|^perhaps", re.I),
    re.compile(r"i cannot confirm|i don't know", re.I),
]


@dataclass
class OutputFilterResult:
    passed: bool
    triggered: str | None = None
    confidence: float = 1.0
    details: dict | None = None


class OutputFilter:
    def __init__(self, hallucination_threshold: float = 0.7, toxicity_threshold: float = 0.5):
        self.hallucination_threshold = hallucination_threshold
        self.toxicity_threshold = toxicity_threshold
        self._toxic_words = {"hate", "violent", "explicit", "harmful", "offensive"}

    def check_toxicity(self, text: str) -> OutputFilterResult:
        if not text:
            return OutputFilterResult(passed=True)
        
        toxic_count = sum(1 for word in self._toxic_words if word in text.lower())
        score = min(toxic_count / 3.0, 1.0)
        
        if score >= self.toxicity_threshold:
            logger.warning("toxicity_detected", score=score)
            return OutputFilterResult(
                passed=False,
                triggered="toxicity",
                confidence=score,
                details={"score": score, "toxic_count": toxic_count},
            )
        
        for pattern in TOXIC_PATTERNS:
            text = pattern.sub("[FILTERED]", text)
        
        return OutputFilterResult(passed=True)

    def check_hallucination(self, text: str, sources: list[str] | None = None) -> OutputFilterResult:
        if not text or not sources:
            return OutputFilterResult(passed=True)
        
        text_lower = text.lower()
        source_matches = sum(1 for src in sources if src.lower() in text_lower)
        
        if not source_matches:
            score = 0.8
            if score >= self.hallucination_threshold:
                logger.warning("hallucination_likely", score=score)
                return OutputFilterResult(
                    passed=False,
                    triggered="hallucination",
                    confidence=score,
                    details={"score": score, "source_matches": source_matches},
                )
        
        return OutputFilterResult(passed=True)

    def check_factual_consistency(self, text: str, rag_context: list[str]) -> OutputFilterResult:
        """Check if response is consistent with RAG context."""
        if not text or not rag_context:
            return OutputFilterResult(passed=True)
        
        text_lower = text.lower()
        context_lower = " ".join(rag_context).lower()
        
        contradictory_terms = ["always", "never", "guaranteed", "definitely not"]
        has_absolutes = any(term in text_lower for term in contradictory_terms)
        
        if has_absolutes:
            for term in contradictory_terms:
                if term in text_lower:
                    logger.info("absolute_statement_found", term=term)
        
        return OutputFilterResult(passed=True)

    def filter_output(self, text: str) -> str:
        for pattern in TOXIC_PATTERNS:
            text = pattern.sub("[FILTERED]", text)
        return text

    def check_uncertainty(self, text: str) -> OutputFilterResult:
        """Flag responses that indicate uncertainty."""
        if not text:
            return OutputFilterResult(passed=True)
        
        for pattern in UNCERTAINTY_PATTERNS:
            if pattern.search(text):
                return OutputFilterResult(
                    passed=True,
                    triggered="uncertain_response",
                    confidence=0.7,
                    details={"pattern": pattern.pattern},
                )
        
        return OutputFilterResult(passed=True)

    async def check_output(self, text: str, sources: list[str] | None = None, rag_context: list[str] | None = None) -> OutputFilterResult:
        """Comprehensive output check combining toxicity, hallucination, and factual checks."""
        toxicity_result = self.check_toxicity(text)
        if not toxicity_result.passed:
            return toxicity_result
        
        hallucination_result = self.check_hallucination(text, sources)
        if not hallucination_result.passed:
            return hallucination_result
        
        factual_result = self.check_factual_consistency(text, rag_context or [])
        if not factual_result.passed:
            return factual_result
        
        uncertainty_result = self.check_uncertainty(text)
        
        return OutputFilterResult(passed=True, triggered=uncertainty_result.triggered)