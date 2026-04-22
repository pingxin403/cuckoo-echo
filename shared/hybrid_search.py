from typing import Any
from pydantic import BaseModel


class SearchResult(BaseModel):
    doc_id: str
    text: str
    score: float
    source: str


class HybridSearch:
    def __init__(self, embedding_service=None, milvus_client=None):
        self.embedding_service = embedding_service
        self.milvus_client = milvus_client
        self.bm25_index = {}

    def dense_search(
        self,
        query: str,
        collection: str,
        limit: int = 10,
    ) -> list[SearchResult]:
        if not self.embedding_service or not self.milvus_client:
            return []
        
        return []

    def sparse_search(
        self,
        query: str,
        collection: str,
        limit: int = 10,
    ) -> list[SearchResult]:
        if collection not in self.bm25_index:
            return []
        
        return []

    def reciprocal_rank_fusion(
        self,
        result_lists: list[list[SearchResult]],
        k: int = 60,
    ) -> list[SearchResult]:
        doc_scores: dict[str, float] = {}
        
        for results in result_lists:
            for rank, result in enumerate(results, 1):
                score = 1.0 / (k + rank)
                doc_scores[result.doc_id] = doc_scores.get(result.doc_id, 0) + score
        
        fused = [
            SearchResult(doc_id=doc_id, text=r.text, score=score, source="hybrid")
            for results in result_lists
            for r in results
            for doc_id, score in doc_scores.items()
            if r.doc_id == doc_id
        ]
        
        fused.sort(key=lambda x: doc_scores.get(x.doc_id, 0), reverse=True)
        return fused[:len(result_lists[0]) if result_lists else 10]

    def search(
        self,
        query: str,
        collection: str,
        limit: int = 10,
    ) -> list[SearchResult]:
        dense = self.dense_search(query, collection, limit)
        sparse = self.sparse_search(query, collection, limit)
        
        if not dense and not sparse:
            return []
        if not dense:
            return sparse[:limit]
        if not sparse:
            return dense[:limit]
        
        return self.reciprocal_rank_fusion([dense, sparse])