"""Message system for inter-agent communication."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class MessageType(Enum):
    """Types of messages agents can exchange."""

    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    ALERT = "alert"
    COMMAND = "command"
    DATA_UPDATE = "data_update"
    HEALTH_EVENT = "health_event"
    COORDINATION = "coordination"


class MessagePriority(Enum):
    """Priority levels for message processing."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


@dataclass
class Message:
    """
    Message for inter-agent communication.

    Supports typed messaging with priorities and metadata
    for reliable agent-to-agent communication.
    """

    sender_id: str
    recipient_id: str | None  # None for broadcasts
    message_type: MessageType
    content: dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    message_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str | None = None  # For request-response tracking
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ttl_seconds: int = 300  # Time-to-live
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if message has expired based on TTL."""
        elapsed = (datetime.utcnow() - self.timestamp).total_seconds()
        return elapsed > self.ttl_seconds

    def create_response(
        self,
        responder_id: str,
        content: dict[str, Any],
        priority: MessagePriority | None = None
    ) -> "Message":
        """Create a response message to this message."""
        return Message(
            sender_id=responder_id,
            recipient_id=self.sender_id,
            message_type=MessageType.RESPONSE,
            content=content,
            priority=priority or self.priority,
            correlation_id=self.message_id,
            metadata={"in_response_to": self.message_type.value}
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary for serialization."""
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "message_type": self.message_type.value,
            "content": self.content,
            "priority": self.priority.value,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "ttl_seconds": self.ttl_seconds,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        """Create message from dictionary."""
        return cls(
            message_id=data["message_id"],
            sender_id=data["sender_id"],
            recipient_id=data.get("recipient_id"),
            message_type=MessageType(data["message_type"]),
            content=data["content"],
            priority=MessagePriority(data["priority"]),
            correlation_id=data.get("correlation_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            ttl_seconds=data.get("ttl_seconds", 300),
            metadata=data.get("metadata", {}),
        )
