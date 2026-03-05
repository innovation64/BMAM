"""Brain-specific operation models — BMAM-exclusive endpoints."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.api.models.search import SearchResultItem


class BrainRetrieveRequest(BaseModel):
    """Full brain-region distributed retrieval."""
    query: str = Field(..., min_length=1)
    k: int = Field(default=10, ge=1, le=100)
    context: Optional[Dict[str, Any]] = None
    activation_plan: Optional[Dict[str, bool]] = Field(
        default=None,
        description="Per-region activation overrides, e.g. "
        "{'hippocampus': true, 'amygdala': false}",
    )
    force_slow_path: bool = False


class BrainRetrieveResponse(BaseModel):
    """Response from brain-region retrieval."""
    memories: List[SearchResultItem]
    path_type: str = Field(
        ..., description="'fast' or 'slow' retrieval path"
    )
    iterations: int
    gaps_detected: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float
    retrieval_time_ms: float
    debug_info: Dict[str, Any] = Field(default_factory=dict)


class ProcessInputRequest(BaseModel):
    """Run the full brain processing pipeline on user input."""
    input: str = Field(..., min_length=1, description="User input text")
    user_id: Optional[str] = Field(default="default")
    context: Optional[Dict[str, Any]] = None


class ProcessInputResponse(BaseModel):
    """Response from the full processing pipeline."""
    response: str
    agents_involved: List[str] = Field(default_factory=list)
    memories_retrieved: List[Dict[str, Any]] = Field(default_factory=list)
    memory_stored: bool = False
    processing_time: float = 0.0
    success: bool = True
    error: Optional[str] = None
    insights: Dict[str, Any] = Field(default_factory=dict)
    activation_trace: Optional[List[Dict[str, Any]]] = None


class ConsolidateRequest(BaseModel):
    """Trigger memory consolidation."""
    strategy: str = Field(
        default="batch", description="Consolidation strategy"
    )
    evaluation_mode: bool = Field(
        default=False,
        description="Bypass time/access limits (for testing)",
    )


class ForgetRequest(BaseModel):
    """Trigger memory forgetting / pruning."""
    region: Optional[str] = Field(
        default=None, description="Target brain region (optional)"
    )
    capacity_threshold: float = Field(
        default=0.8, ge=0.0, le=1.0,
        description="Capacity ratio to trigger forgetting",
    )


class FeedbackRequest(BaseModel):
    """Submit learning feedback for a query."""
    query_type: str = Field(
        ...,
        description="Query type: temporal | preference | factual | identity",
    )
    reward_signal: float = Field(
        ..., ge=0.0, le=1.0,
        description="Reward signal (0=error, 1=correct)",
    )
    query: Optional[str] = None
    response: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class FeedbackResponse(BaseModel):
    """Result of feedback application."""
    status: str
    query_type: str
    reward: float
    weight_delta: float = 0.0


class PreferencesResponse(BaseModel):
    """User preference retrieval result."""
    preferences: List[str]
    user_id: Optional[str] = None
