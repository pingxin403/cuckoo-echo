from typing import Any
from pydantic import BaseModel
import math


class RerankedResult(BaseModel):
    doc_id: str
    text: str
    original_score: float
    rerank_score: float
    metadata: dict[str, Any] = {}


class Reranker:
    def __init__(self, embedding_service=None):
        self.embedding_service = embedding_service

    def cross_encoder_rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        limit: int = 10,
    ) -> list[RerankedResult]:
        if not documents:
            return []
        
        scored = []
        for doc in documents:
            relevance = self._compute_relevance(query, doc.get("text", ""))
            scored.append(RerankedResult(
                doc_id=doc.get("id", ""),
                text=doc.get("text", ""),
                original_score=doc.get("score", 0.0),
                rerank_score=relevance,
                metadata=doc.get("metadata", {}),
            ))
        
        scored.sort(key=lambda x: x.rerank_score, reverse=True)
        return scored[:limit]

    def mmr_diversity(
        self,
        query: str,
        documents: list[dict[str, Any]],
        limit: int = 10,
        lambda_mult: float = 0.5,
    ) -> list[RerankedResult]:
        if not documents:
            return []
        
        selected = []
        remaining = list(documents)
        
        while len(selected) < limit and remaining:
            best_score = -float("inf")
            best_doc = None
            best_idx = 0
            
            for i, doc in enumerate(remaining):
                relevance = self._compute_relevance(query, doc.get("text", ""))
                
                diversity = 0.0
                if selected:
                    max_sim = max(
                        self._compute_similarity(doc.get("text", ""), s.text)
                        for s in selected
                    )
                    diversity = 1 - max_sim
                
                mmr_score = lambda_mult * relevance + (1 - lambda_mult) * diversity
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_doc = doc
                    best_idx = i
            
            if best_doc:
                selected.append(RerankedResult(
                    doc_id=best_doc.get("id", ""),
                    text=best_doc.get("text", ""),
                    original_score=best_doc.get("score", 0.0),
                    rerank_score=best_score,
                    metadata=best_doc.get("metadata", {}),
                ))
                remaining.pop(best_idx)
            else:
                break
        
        return selected

    def dynamic_k(
        self,
        query: str,
        base_k: int = 10,
    ) -> int:
        query_complexity = self._estimate_complexity(query)
        
        if query_complexity > 0.8:
            return int(base_k * 1.5)
        elif query_complexity > 0.5:
            return base_k
        else:
            return int(base_k * 0.7)

    def _compute_relevance(self, query: str, document: str) -> float:
        query_terms = set(query.lower().split())
        doc_terms = set(document.lower().split())
        
        if not query_terms or not doc_terms:
            return 0.0
        
        intersection = query_terms & doc_terms
        return len(intersection) / len(query_terms)

    def _compute_similarity(self, text1: str, text2: str) -> float:
        terms1 = set(text1.lower().split())
        terms2 = set(text2.lower().split())
        
        if not terms1 or not terms2:
            return 0.0
        
        intersection = terms1 & terms2
        union = terms1 | terms2
        
        return len(intersection) / len(union) if union else 0.0

    def _estimate_complexity(self, query: str) -> float:
        complexity = 0.0
        
        if any(w in query.lower() for w in ["and", "or", "but"]):
            complexity += 0.3
        
        if any(w in query.lower() for w in ["compare", "difference", "versus"]):
            complexity += 0.4
        
        if len(query.split()) > 10:
            complexity += 0.2
        
        if "?" in query:
            complexity += 0.1
        
        return min(1.0, complexity)