"""Query rewriting for improved RAG retrieval."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QueryExpansion:
    original: str
    expanded: list[str] = field(default_factory=list)
    strategy: str = "default"

    async def expand(self, llm_client: Optional[object] = None) -> list[str]:
        if self.expanded:
            return self.expanded

        expansions = [
            self.original,
            f"{self.original} definition",
            f"{self.original} example",
            f"{self.original} how to",
            f"why {self.original}",
        ]
        if llm_client:
            return await llm_client.generate_unique(expansions)
        return expansions


@dataclass
class SubQuery:
    text: str
    intent: str = "query"
    dependencies: list[str] = field(default_factory=list)


def decompose_query(query: str) -> list[SubQuery]:
    conjunctions = [" and ", " also ", " and then "]
    for conj in conjunctions:
        if conj in query.lower():
            parts = query.split(conj)
            return [
                SubQuery(text=p.strip(), intent="query")
                for p in parts
                if p.strip()
            ]
    return [SubQuery(text=query, intent="query")]


@dataclass
class HallucinationCheck:
    claim: str
    is_supported: bool = False
    confidence: float = 0.0
    matching_sources: list[str] = field(default_factory=list)


def check_hallucination(
    claim: str,
    sources: list[str],
    threshold: float = 0.5,
) -> HallucinationCheck:
    if not sources:
        return HallucinationCheck(claim=claim, is_supported=False, confidence=0.0)

    matches = [s for s in sources if _text_similarity(claim, s) > threshold]
    confidence = max((_text_similarity(claim, s) for s in sources), default=0.0)

    return HallucinationCheck(
        claim=claim,
        is_supported=len(matches) > 0,
        confidence=confidence,
        matching_sources=matches,
    )


def _text_similarity(a: str, b: str) -> float:
    a_lower = a.lower()
    b_lower = b.lower()
    a_words = set(a_lower.split())
    b_words = set(b_lower.split())
    if not a_words or not b_words:
        return 0.0
    intersection = a_words & b_words
    return len(intersection) / len(a_words)