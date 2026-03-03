"""Chat related schemas."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.schemas.common import TimestampMixin


class MessageRole(str, Enum):
    """Message roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class MessageType(str, Enum):
    """Message types."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"


class ChatMessage(BaseModel):
    """Chat message schema."""

    role: MessageRole
    content: str
    message_type: MessageType = MessageType.TEXT
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    """Chat request schema."""

    session_id: Optional[str] = None
    message: str
    context: Optional[List[ChatMessage]] = None
    stream: bool = False
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    tools: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Chat response schema."""

    session_id: str
    message: ChatMessage
    usage: Optional[Dict[str, int]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    finish_reason: Optional[str] = None


class ChatSession(BaseModel, TimestampMixin):
    """Chat session schema."""

    id: str
    user_id: Optional[str] = None
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    message_count: int = 0


class ChatHistoryResponse(BaseModel):
    """Chat history response."""

    session: ChatSession
    messages: List[ChatMessage]


class StreamChunk(BaseModel):
    """Stream chunk for SSE."""

    session_id: str
    chunk: str
    is_finished: bool = False
    finish_reason: Optional[str] = None
