"""Multi-agent message protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MessageType(Enum):
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"


@dataclass
class AgentMessage:
    sender: str
    receiver: str
    content: Any
    trace_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    msg_type: MessageType = MessageType.REQUEST
    correlation_id: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict:
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp.isoformat(),
            "msg_type": self.msg_type.value,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentMessage":
        return cls(
            sender=data["sender"],
            receiver=data["receiver"],
            content=data["content"],
            trace_id=data["trace_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            msg_type=MessageType(data["msg_type"]),
            correlation_id=data.get("correlation_id"),
            metadata=data.get("metadata"),
        )