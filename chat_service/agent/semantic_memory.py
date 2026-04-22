from datetime import datetime
from typing import Any
from pydantic import BaseModel


class UserPreference(BaseModel):
    key: str
    value: Any
    confidence: float = 1.0
    source: str = "explicit"
    updated_at: datetime


class EntityKnowledge(BaseModel):
    entity_type: str
    entity_id: str
    properties: dict[str, Any]
    confidence: float = 1.0
    created_at: datetime
    updated_at: datetime


class Relationship(BaseModel):
    source_id: str
    target_id: str
    relation_type: str
    strength: float = 1.0


class SemanticMemory:
    def __init__(self, vector_store=None, db_pool=None):
        self.vector_store = vector_store
        self.db = db_pool
        self._preferences: dict[str, dict[str, UserPreference]] = {}
        self._entities: dict[str, dict[str, EntityKnowledge]] = {}
        self._relationships: list[Relationship] = []

    async def store_preference(
        self,
        user_id: str,
        key: str,
        value: Any,
        confidence: float = 1.0,
        source: str = "explicit",
    ) -> UserPreference:
        pref = UserPreference(
            key=key,
            value=value,
            confidence=confidence,
            source=source,
            updated_at=datetime.now(),
        )
        
        if user_id not in self._preferences:
            self._preferences[user_id] = {}
        self._preferences[user_id][key] = pref
        
        if self.db:
            await self._persist_preference(user_id, pref)
        
        return pref

    async def get_preferences(self, user_id: str) -> dict[str, Any]:
        if user_id in self._preferences:
            return {k: v.value for k, v in self._preferences[user_id].items()}
        return {}

    async def store_entity(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
        properties: dict[str, Any],
        confidence: float = 1.0,
    ) -> EntityKnowledge:
        entity = EntityKnowledge(
            entity_type=entity_type,
            entity_id=entity_id,
            properties=properties,
            confidence=confidence,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        if user_id not in self._entities:
            self._entities[user_id] = {}
        self._entities[user_id][entity_id] = entity
        
        if self.db:
            await self._persist_entity(user_id, entity)
        
        return entity

    async def get_entities(self, user_id: str, entity_type: str | None = None) -> list[EntityKnowledge]:
        if user_id not in self._entities:
            return []
        
        entities = list(self._entities[user_id].values())
        if entity_type:
            entities = [e for e in entities if e.entity_type == entity_type]
        return entities

    async def add_relationship(self, source_id: str, target_id: str, relation_type: str, strength: float = 1.0) -> Relationship:
        rel = Relationship(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            strength=strength,
        )
        self._relationships.append(rel)
        return rel

    async def retrieve(self, user_id: str, query: str, k: int = 3) -> list[dict[str, Any]]:
        results = []
        
        prefs = await self.get_preferences(user_id)
        if prefs:
            results.append({"type": "preferences", "data": prefs})
        
        entities = await self.get_entities(user_id)
        if entities:
            results.append({"type": "entities", "data": entities[:k]})
        
        return results

    async def _persist_preference(self, user_id: str, pref: UserPreference) -> None:
        pass

    async def _persist_entity(self, user_id: str, entity: EntityKnowledge) -> None:
        pass
