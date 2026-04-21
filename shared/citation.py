"""Citation and source attribution for RAG responses."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CitationType(Enum):
    EXACT_MATCH = "exact"
    SEMANTIC_MATCH = "semantic"
    INFERRED = "inferred"
    NO_CITATION = "none"


@dataclass
class Source:
    id: str
    title: str
    url: Optional[str] = None
    excerpt: Optional[str] = None
    confidence: float = 1.0
    chunk_id: Optional[str] = None
    citation_type: CitationType = CitationType.SEMANTIC_MATCH

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "excerpt": self.excerpt,
            "confidence": self.confidence,
            "chunk_id": self.chunk_id,
            "citation_type": self.citation_type.value,
        }


@dataclass
class SourceCard:
    items: list[Source] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "items": [s.to_dict() for s in self.items],
            "confidence": self.confidence,
        }


def format_citation(source: Source, index: int) -> str:
    return f"[{index}]"


def format_inline_citations(sources: list[Source]) -> str:
    if not sources:
        return ""
    return " ".join(format_citation(s, i + 1) for i, s in enumerate(sources))


def compute_card_confidence(sources: list[Source]) -> float:
    if not sources:
        return 0.0
    return sum(s.confidence for s in sources) / len(sources)


def create_source_card(sources: list[Source]) -> SourceCard:
    return SourceCard(
        items=sources,
        confidence=compute_card_confidence(sources),
    )
