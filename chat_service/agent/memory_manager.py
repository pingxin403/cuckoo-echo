from enum import Enum
from typing import Any
from datetime import datetime
from pydantic import BaseModel
import json


class MemoryType(str, Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryImportance(BaseModel):
    explicit: float = 0.0
    implicit: float = 0.0
    recency: float = 0.0
    relevance: float = 0.0
    total: float = 0.0


class Memory(BaseModel):
    id: str
    user_id: str
    memory_type: MemoryType
    content: dict[str, Any]
    importance: float = 0.5
    created_at: datetime
    expires_at: datetime | None = None
    metadata: dict[str, Any] = {}


class ImportanceScorer:
    def __init__(self):
        self.decay_factor = 0.95

    def score(self, memory: Memory, query: str | None = None) -> float:
        explicit = memory.importance
        recency = self._recency_score(memory.created_at)
        
        implicit = 0.5
        if memory.metadata.get("repeated_mention"):
            implicit += 0.2
        
        relevance = 0.5
        if query and memory.content.get("text"):
            if query.lower() in memory.content["text"].lower():
                relevance = 0.9

        total = (explicit * 0.3 + implicit * 0.2 + recency * 0.2 + relevance * 0.3)
        return min(1.0, max(0.0, total))

    def _recency_score(self, created_at: datetime) -> float:
        age_hours = (datetime.now() - created_at).total_seconds() / 3600
        return self.decay_factor ** (age_hours / 24)


class MemoryManager:
    def __init__(self, db_pool=None, vector_store=None):
        self.db = db_pool
        self.vector_store = vector_store
        self.scorer = ImportanceScorer()
        self._working_memory: dict[str, list[Memory]] = {}
        self._session_buffer: dict[str, list[Memory]] = {}

    async def store_memory(
        self,
        user_id: str,
        memory_type: MemoryType,
        content: dict[str, Any],
        importance: float = 0.5,
        session_id: str | None = None,
        expires_at: datetime | None = None,
    ) -> Memory:
        memory = Memory(
            id=f"mem_{datetime.now().timestamp()}",
            user_id=user_id,
            memory_type=memory_type,
            content=content,
            importance=importance,
            created_at=datetime.now(),
            expires_at=expires_at,
        )
        
        if session_id:
            if session_id not in self._session_buffer:
                self._session_buffer[session_id] = []
            self._session_buffer[session_id].append(memory)
        
        if self.db:
            await self._persist_memory(memory)
        
        if self.vector_store and memory_type == MemoryType.EPISODIC:
            await self._index_memory(memory)
        
        return memory

    async def retrieve_memories(
        self,
        user_id: str,
        query: str | None = None,
        memory_type: MemoryType | None = None,
        limit: int = 10,
        session_id: str | None = None,
    ) -> list[Memory]:
        results = []
        
        if session_id and session_id in self._session_buffer:
            results.extend(self._session_buffer[session_id])
        
        if self.vector_store and query:
            vector_results = await self._semantic_search(user_id, query, limit)
            results.extend(vector_results)
        
        if self.db:
            db_results = await self._db_search(user_id, memory_type, limit)
            results.extend(db_results)
        
        scored = [(m, self.scorer.score(m, query)) for m in results]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return [m for m, _ in scored[:limit]]

    async def consolidate(self, user_id: str, session_id: str) -> None:
        if session_id not in self._session_buffer:
            return
        
        memories = self._session_buffer[session_id]
        
        episodic = [m for m in memories if m.memory_type == MemoryType.EPISODIC]
        if episodic:
            summary = await self._generate_summary(episodic)
            await self.store_memory(
                user_id=user_id,
                memory_type=MemoryType.SEMANTIC,
                content={"type": "conversation_summary", "summary": summary},
                importance=0.6,
            )
        
        del self._session_buffer[session_id]

    async def forget(self, user_id: str, memory_id: str) -> bool:
        if self.db:
            return await self._delete_from_db(user_id, memory_id)
        return False

    async def _persist_memory(self, memory: Memory) -> None:
        pass

    async def _index_memory(self, memory: Memory) -> None:
        pass

    async def _semantic_search(self, user_id: str, query: str, limit: int) -> list[Memory]:
        return []

    async def _db_search(self, user_id: str, memory_type: MemoryType | None, limit: int) -> list[Memory]:
        return []

    async def _delete_from_db(self, user_id: str, memory_id: str) -> bool:
        return True

    async def _generate_summary(self, memories: list[Memory]) -> str:
        return f"Conversation with {len(memories)} messages"
