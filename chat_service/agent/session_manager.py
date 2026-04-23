"""Session management and context engineering for long conversations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class SessionType(Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    SESSION_GROUP = "session_group"


class MessageImportance(Enum):
    CRITICAL = 3
    HIGH = 2
    MEDIUM = 1
    LOW = 0


@dataclass
class SessionMetadata:
    session_id: str = ""
    tenant_id: str = ""
    user_id: str = ""
    session_type: SessionType = SessionType.SHORT_TERM
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    message_count: int = 0
    token_count: int = 0
    topics: list[str] = field(default_factory=list)
    bookmarks: list[int] = field(default_factory=list)
    parent_session: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class MessageNode:
    message_id: str
    content: str
    role: str
    timestamp: datetime
    importance: MessageImportance = MessageImportance.MEDIUM
    topic: str | None = None
    thread_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Thread:
    thread_id: str
    title: str
    messages: list[MessageNode] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_message: datetime = field(default_factory=datetime.utcnow)


class SessionManager:
    """Manages sessions with compression and organization."""

    MAX_TOKEN_BUDGET = 8192

    def __init__(self, max_token_budget: int | None = None):
        self.max_token_budget = max_token_budget or self.MAX_TOKEN_BUDGET
        self._sessions: dict[str, SessionMetadata] = {}
        self._messages: dict[str, list[MessageNode]] = {}
        self._threads: dict[str, Thread] = {}

    def create_session(
        self,
        session_id: str,
        tenant_id: str,
        user_id: str,
        session_type: SessionType = SessionType.SHORT_TERM,
    ) -> SessionMetadata:
        metadata = SessionMetadata(
            session_id=session_id,
            tenant_id=tenant_id,
            user_id=user_id,
            session_type=session_type,
        )
        self._sessions[session_id] = metadata
        self._messages[session_id] = []
        return metadata

    def get_session(self, session_id: str) -> SessionMetadata | None:
        return self._sessions.get(session_id)

    def add_message(
        self,
        session_id: str,
        message_id: str,
        content: str,
        role: str,
        importance: MessageImportance = MessageImportance.MEDIUM,
        topic: str | None = None,
    ) -> MessageNode:
        node = MessageNode(
            message_id=message_id,
            content=content,
            role=role,
            timestamp=datetime.utcnow(),
            importance=importance,
            topic=topic,
        )

        if session_id in self._messages:
            self._messages[session_id].append(node)

        if session_id in self._sessions:
            self._sessions[session_id].message_count += 1
            self._sessions[session_id].last_activity = datetime.utcnow()

            if topic and topic not in self._sessions[session_id].topics:
                self._sessions[session_id].topics.append(topic)

        return node

    def create_thread(
        self, session_id: str, title: str, initial_message_id: str | None = None
    ) -> Thread:
        thread_id = f"thread_{len(self._threads) + 1}"
        thread = Thread(thread_id=thread_id, title=title)

        if initial_message_id and session_id in self._messages:
            for msg in self._messages[session_id]:
                if msg.message_id == initial_message_id:
                    msg.thread_id = thread_id
                    thread.messages.append(msg)
                    break

        self._threads[thread_id] = thread
        return thread

    def add_to_thread(self, thread_id: str, message_node: MessageNode) -> None:
        if thread_id in self._threads:
            message_node.thread_id = thread_id
            self._threads[thread_id].messages.append(message_node)
            self._threads[thread_id].last_message = datetime.utcnow()

    def create_bookmark(self, session_id: str, message_index: int) -> None:
        if session_id in self._sessions:
            if message_index not in self._sessions[session_id].bookmarks:
                self._sessions[session_id].bookmarks.append(message_index)

    def score_message_importance(
        self,
        message: str,
        role: str,
        position: int,
        total_messages: int,
        has_tool_call: bool = False,
    ) -> MessageImportance:
        """Compute importance score for a message."""
        score = MessageImportance.MEDIUM.value

        if role == "system":
            score += MessageImportance.CRITICAL.value
        elif has_tool_call:
            score += MessageImportance.HIGH.value

        if position < 3:
            score += MessageImportance.HIGH.value
        elif position >= total_messages - 3:
            score += MessageImportance.HIGH.value

        import re
        important_patterns = [
            r"(thank|thanks|please|appreciate)",
            r"(order|account|payment|refund)",
            r"(problem|issue|error|wrong)",
        ]
        for pattern in important_patterns:
            if re.search(pattern, message, re.I):
                score += 1

        if score >= MessageImportance.CRITICAL.value * 2:
            return MessageImportance.CRITICAL
        elif score >= MessageImportance.HIGH.value * 2:
            return MessageImportance.HIGH
        elif score <= MessageImportance.LOW.value:
            return MessageImportance.LOW
        return MessageImportance.MEDIUM

    def compute_token_budget(
        self, session_metadata: SessionMetadata, priority_topics: list[str]
    ) -> dict[str, int]:
        """Allocate token budget across message layers."""
        total_tokens = self.max_token_budget

        system_tokens = min(1000, total_tokens // 4)
        recent_tokens = min(4000, total_tokens // 2)
        semantic_tokens = min(2000, total_tokens // 4)
        procedural_tokens = min(512, total_tokens // 16)

        remaining = total_tokens - system_tokens - recent_tokens - semantic_tokens - procedural_tokens
        if remaining > 0:
            recent_tokens += remaining

        return {
            "system": system_tokens,
            "recent": recent_tokens,
            "semantic": semantic_tokens,
            "procedural": procedural_tokens,
        }

    def get_context_for_inference(
        self,
        session_id: str,
        priority_topics: list[str] | None = None,
    ) -> list[MessageNode]:
        """Build context window with importance-based retention."""
        if session_id not in self._messages:
            return []

        messages = self._messages[session_id]
        if not messages:
            return []

        budget = self.compute_token_budget(
            self._sessions.get(session_id, SessionMetadata()),
            priority_topics or [],
        )

        recent = messages[-min(10, len(messages)) :]

        important = [m for m in messages[:-10] if m.importance.value >= MessageImportance.HIGH.value]

        combined = recent + important[:5]
        combined.sort(key=lambda x: x.timestamp, reverse=True)

        return combined[:20]

    def detect_topics(self, messages: list[str]) -> list[str]:
        """Detect conversation topics using keyword patterns."""
        topic_keywords = {
            "orders": ["order", "shipping", "delivery", "track"],
            "account": ["account", "login", "password", "profile"],
            "billing": ["payment", "invoice", "charge", "refund"],
            "technical": ["error", "bug", "crash", "issue"],
            "general": [],
        }

        topics: list[str] = []
        for msg in messages:
            for topic, keywords in topic_keywords.items():
                if any(kw in msg.lower() for kw in keywords):
                    if topic not in topics:
                        topics.append(topic)

        return topics or ["general"]


session_manager = SessionManager()