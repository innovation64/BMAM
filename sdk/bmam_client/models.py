"""SDK-side Pydantic models (mirrors server models, avoids server dependency)."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Memory
# ------------------------------------------------------------------

class Memory(BaseModel):
    """A single memory record."""
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


class MemoryList(BaseModel):
    """Paginated list of memories."""
    memories: List[Memory]
    total: int
    page: int
    page_size: int


# ------------------------------------------------------------------
# Search
# ------------------------------------------------------------------

class SearchResult(BaseModel):
    """A single search hit."""
    id: str
    content: str
    score: float = 0.0
    memory_type: str = "episodic"
    brain_region: str = "hippocampus"
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResults(BaseModel):
    """Search response envelope."""
    results: List[SearchResult]
    total: int
    query: str
    retrieval_mode: str = "semantic"


# ------------------------------------------------------------------
# Brain
# ------------------------------------------------------------------

class BrainRetrieveResult(BaseModel):
    """Result from brain-distributed retrieval."""
    memories: List[SearchResult]
    path_type: str
    iterations: int
    gaps_detected: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float
    retrieval_time_ms: float
    debug_info: Dict[str, Any] = Field(default_factory=dict)


class ProcessResult(BaseModel):
    """Result from the full processing pipeline."""
    response: str
    agents_involved: List[str] = Field(default_factory=list)
    memories_retrieved: List[Dict[str, Any]] = Field(default_factory=list)
    memory_stored: bool = False
    processing_time: float = 0.0
    success: bool = True
    error: Optional[str] = None
    insights: Dict[str, Any] = Field(default_factory=dict)


class FeedbackResult(BaseModel):
    """Feedback application result."""
    status: str
    query_type: str
    reward: float
    weight_delta: float = 0.0


# ------------------------------------------------------------------
# System
# ------------------------------------------------------------------

class HealthStatus(BaseModel):
    """System health."""
    status: str
    features: Dict[str, bool] = Field(default_factory=dict)
    healthy_count: int = 0
    total_count: int = 0
    degraded_features: List[str] = Field(default_factory=list)
    health_percentage: float = 0.0


class SystemStats(BaseModel):
    """Memory statistics."""
    total_memories: int = 0
    episodic_memories: int = 0
    semantic_memories: int = 0
    database_url: str = ""


class ArchiveResult(BaseModel):
    """Archive operation result."""
    success: bool
    message: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)
