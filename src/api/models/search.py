"""Search / retrieval models."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TemporalFilter(BaseModel):
    """Time-range filter for search queries."""
    start: Optional[datetime] = None
    end: Optional[datetime] = None


class SearchRequest(BaseModel):
    """Semantic memory search — Mem0-compatible ``search()`` interface.

    Set ``use_brain_retrieval=True`` to enable the full 5 brain-region
    distributed retrieval pipeline (BMAM-exclusive).

    Accepts either ``limit`` or ``k`` to specify result count.
    """
    query: str = Field(..., min_length=1, description="Search query")
    user_id: Optional[str] = Field(default="default")
    limit: int = Field(default=10, ge=1, le=100)
    use_brain_retrieval: bool = Field(
        default=False,
        description="Enable 5-brain-region distributed retrieval",
    )
    temporal_filter: Optional[TemporalFilter] = None
    strategy: str = Field(
        default="auto",
        description="Retrieval strategy: auto | fast | slow",
    )
    context: Optional[Dict[str, Any]] = None

    @model_validator(mode="before")
    @classmethod
    def _k_alias(cls, data):
        """Accept ``k`` as an alias for ``limit``."""
        if isinstance(data, dict) and "k" in data and "limit" not in data:
            data["limit"] = data.pop("k")
        return data


class SearchResultItem(BaseModel):
    """A single search result."""
    id: str
    content: str
    score: float = 0.0
    memory_type: str = "episodic"
    brain_region: str = "hippocampus"
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Search results envelope."""
    results: List[SearchResultItem]
    total: int
    query: str
    retrieval_mode: str = "semantic"
