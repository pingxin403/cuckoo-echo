from datetime import datetime
from typing import Any
from enum import Enum

from pydantic import BaseModel


class Interaction(BaseModel):
    id: str
    user_id: str
    session_id: str
    messages: list[dict[str, Any]]
    importance_score: float = 0.5
    created_at: datetime
    metadata: dict[str, Any] = {}


class EpisodicMemory:
    def __init__(self, vector_store=None, db_pool=None):
        self.vector_store = vector_store
        self.db = db_pool

    async def store_interaction(
        self,
        user_id: str,
        session_id: str,
        messages: list[dict[str, Any]],
        importance: float = 0.5,
    ) -> Interaction:
        interaction = Interaction(
            id=f"ep_{datetime.now().timestamp()}",
            user_id=user_id,
            session_id=session_id,
            messages=messages,
            importance_score=importance,
            created_at=datetime.now(),
        )
        
        if self.vector_store:
            await self._index_interaction(interaction)
        
        if self.db:
            await self._persist_interaction(interaction)
        
        return interaction

    async def recall(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
        time_range: tuple[datetime, datetime] | None = None,
    ) -> list[Interaction]:
        results = []
        
        if self.vector_store:
            semantic_results = await self._semantic_recall(user_id, query, limit)
            results.extend(semantic_results)
        
        if self.db:
            db_results = await self._db_recall(user_id, time_range, limit)
            results.extend(db_results)
        
        results.sort(key=lambda x: x.importance_score, reverse=True)
        return results[:limit]

    async def _index_interaction(self, interaction: Interaction) -> None:
        pass

    async def _persist_interaction(self, interaction: Interaction) -> None:
        pass

    async def _semantic_recall(self, user_id: str, query: str, limit: int) -> list[Interaction]:
        return []

    async def _db_recall(self, user_id: str, time_range: tuple[datetime, datetime] | None, limit: int) -> list[Interaction]:
        return []