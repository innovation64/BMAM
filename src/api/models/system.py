"""System health, stats, and archive models."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """System health status."""
    status: str = Field(
        ..., description="'healthy', 'degraded', or 'unhealthy'"
    )
    features: Dict[str, bool] = Field(default_factory=dict)
    healthy_count: int = 0
    total_count: int = 0
    degraded_features: List[str] = Field(default_factory=list)
    health_percentage: float = 0.0


class SystemStatsResponse(BaseModel):
    """Memory system statistics."""
    total_memories: int = 0
    episodic_memories: int = 0
    semantic_memories: int = 0
    database_url: str = ""


class ArchiveExportRequest(BaseModel):
    """Request to export a memory archive (soul transfer)."""
    archive_name: str = Field(..., min_length=1)
    description: str = ""
    tags: Optional[List[str]] = None
    include_faiss: bool = True
    metadata: Optional[Dict[str, Any]] = None
    output_dir: str = "archives/"


class ArchiveImportRequest(BaseModel):
    """Request to import a memory archive."""
    archive_path: str = Field(..., min_length=1)
    target_dir: Optional[str] = None
    validate_archive: bool = Field(default=True, description="Validate archive integrity")
    force: bool = False


class ArchiveResponse(BaseModel):
    """Result of an archive operation."""
    success: bool
    message: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)
