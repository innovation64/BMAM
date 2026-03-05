"""Memory CRUD models — Mem0-compatible interface."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.api.models.common import MemoryType


class ChatMessage(BaseModel):
    """A single chat message (Mem0 format)."""
    role: str = Field(..., description="Message role: user | assistant | system")
    content: str = Field(..., description="Message text")


class MemoryCreateRequest(BaseModel):
    """Create a new memory.

    Supports two input formats:
      1. Mem0-style: ``messages`` list of ChatMessage
      2. Direct: ``content`` string
    At least one of ``messages`` or ``content`` must be provided.
    """
    messages: Optional[List[ChatMessage]] = Field(
        default=None,
        description="Mem0-compatible chat messages to store",
    )
    content: Optional[str] = Field(
        default=None, description="Direct text content to store"
    )
    user_id: Optional[str] = Field(default="default")
    memory_type: MemoryType = Field(default=MemoryType.EPISODIC)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    emotion_tags: Optional[List[str]] = None
    context_tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    speaker: Optional[str] = None

    def resolved_content(self) -> str:
        """Return the effective content string."""
        if self.content:
            return self.content
        if self.messages:
            return "\n".join(
                f"{m.role}: {m.content}" for m in self.messages
            )
        raise ValueError("Either 'content' or 'messages' must be provided")


class MemoryCreateResponse(BaseModel):
    """Response after creating a memory."""
    id: str = Field(..., description="Memory ID")
    message: str = "Memory created successfully"


class MemoryUpdateRequest(BaseModel):
    """Update an existing memory."""
    content: Optional[str] = None
    importance: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    emotion_tags: Optional[List[str]] = None
    context_tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class MemoryResponse(BaseModel):
    """A single memory item returned to the client."""
    id: str
    content: str
    memory_type: str = "episodic"
    importance: float = 0.5
    brain_region: str = "hippocampus"
    consolidation_level: int = 0
    access_frequency: int = 0
    timestamp: Optional[str] = None
    emotion_tags: List[str] = Field(default_factory=list)
    context_tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryListResponse(BaseModel):
    """Paginated list of memories."""
    memories: List[MemoryResponse]
    total: int
    page: int
    page_size: int
