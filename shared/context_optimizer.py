from typing import Any
from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class SessionType(str, Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"


class SessionMetadata(BaseModel):
    session_id: str
    session_type: SessionType = SessionType.SHORT_TERM
    topic: str | None = None
    bookmarked: bool = False
    message_count: int = 0
    token_count: int = 0


class MessageImportance(BaseModel):
    explicit: float = 0.0
    role_weight: float = 0.0
    recency: float = 0.0
    content_analysis: float = 0.0
    total: float = 0.0


class ContextOptimizer:
    def __init__(self, summarizer=None):
        self.summarizer = summarizer
        self.default_budget = 8000
        self.min_importance_threshold = 0.3

    def token_budget_allocation(
        self,
        messages: list[dict[str, Any]],
        budget: int | None = None,
    ) -> dict[str, int]:
        target_budget = budget or self.default_budget
        
        system_prompt = int(target_budget * 0.15)
        retrieval_context = int(target_budget * 0.25)
        working_memory = int(target_budget * 0.30)
        conversation_history = target_budget - system_prompt - retrieval_context - working_memory
        
        return {
            "system_prompt": system_prompt,
            "retrieval_context": retrieval_context,
            "working_memory": working_memory,
            "conversation_history": conversation_history,
        }

    def importance_scoring(
        self,
        messages: list[dict[str, Any]],
        current_query: str | None = None,
    ) -> list[tuple[dict[str, Any], float]]:
        scored = []
        
        for msg in messages:
            importance = self._score_message(msg, current_query)
            scored.append((msg, importance))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def selective_retention(
        self,
        messages: list[dict[str, Any]],
        budget: int,
        current_query: str | None = None,
    ) -> list[dict[str, Any]]:
        scored = self.importance_scoring(messages, current_query)
        
        selected = []
        total_tokens = 0
        
        for msg, importance in scored:
            if importance < self.min_importance_threshold:
                continue
            
            msg_tokens = self._estimate_tokens(msg)
            
            if total_tokens + msg_tokens > budget:
                remaining = budget - total_tokens
                if remaining > 100:
                    selected.append(msg)
                break
            
            selected.append(msg)
            total_tokens += msg_tokens
        
        selected.sort(key=lambda x: x.get("created_at", datetime.min))
        return selected

    def compress_old_messages(
        self,
        messages: list[dict[str, Any]],
        threshold: int = 50,
    ) -> list[dict[str, Any]]:
        if len(messages) < threshold:
            return messages
        
        recent = messages[-10:]
        older = messages[:-10]
        
        summary_text = f"[Previous {len(older)} messages summarized]"
        
        return older[:1] + [{"role": "system", "content": summary_text}] + recent

    def _score_message(
        self,
        message: dict[str, Any],
        current_query: str | None = None,
    ) -> float:
        explicit = message.get("importance", 0.5)
        
        role_weights = {"system": 0.9, "assistant": 0.7, "user": 0.5, "tool": 0.3}
        role = message.get("role", "user")
        role_weight = role_weights.get(role, 0.5)
        
        created_at = message.get("created_at", datetime.now())
        age_hours = (datetime.now() - created_at).total_seconds() / 3600
        recency = max(0, 1 - (age_hours / 24))
        
        content_analysis = 0.5
        if current_query and message.get("content"):
            content = message["content"].lower()
            query_terms = set(current_query.lower().split())
            content_terms = set(content.split())
            if query_terms & content_terms:
                content_analysis = 0.8

        total = explicit * 0.2 + role_weight * 0.2 + recency * 0.2 + content_analysis * 0.4
        return min(1.0, max(0.0, total))

    def _estimate_tokens(self, message: dict[str, Any]) -> int:
        content = message.get("content", "")
        return len(content.split()) + int(len(content) / 4)


class SessionManager:
    def __init__(self, db_pool=None):
        self.db = db_pool
        self._sessions: dict[str, SessionMetadata] = {}
        self._session_groups: dict[str, list[str]] = {}

    def create_session(
        self,
        session_type: SessionType = SessionType.SHORT_TERM,
    ) -> SessionMetadata:
        session = SessionMetadata(
            session_id=f"sess_{datetime.now().timestamp()}",
            session_type=session_type,
        )
        self._sessions[session.session_id] = session
        return session

    def group_sessions(self, session_ids: list[str], group_name: str) -> None:
        self._session_groups[group_name] = session_ids

    def bookmark_message(self, session_id: str, message_id: str) -> None:
        if session_id in self._sessions:
            self._sessions[session_id].bookmarked = True

    def get_session_context(self, session_id: str) -> SessionMetadata | None:
        return self._sessions.get(session_id)

    def update_counts(self, session_id: str, messages: int, tokens: int) -> None:
        if session_id in self._sessions:
            self._sessions[session_id].message_count = messages
            self._sessions[session_id].token_count = tokens