"""Common types and base models for the BMAM API."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """Memory types mapped to brain-region specializations."""
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    WORKING = "working"


class BrainRegionName(str, Enum):
    """The 5 brain-region agents in BMAM."""
    HIPPOCAMPUS = "hippocampus"
    TEMPORAL_LOBE = "temporal_lobe"
    AMYGDALA = "amygdala"
    PREFRONTAL = "prefrontal"
    BASAL_GANGLIA = "basal_ganglia"


class ScopingParams(BaseModel):
    """User / agent / session scoping for multi-tenant use."""
    user_id: Optional[str] = Field(
        default=None, description="User identifier for memory isolation"
    )
    agent_id: Optional[str] = Field(
        default=None, description="Agent identifier"
    )
    session_id: Optional[str] = Field(
        default=None, description="Session identifier"
    )


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(
        default=50, ge=1, le=1000, description="Items per page"
    )
