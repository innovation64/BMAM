"""Pydantic models for the BMAM REST API."""

from src.api.models.common import (
    MemoryType,
    BrainRegionName,
    ScopingParams,
    PaginationParams,
)
from src.api.models.memory import (
    MemoryCreateRequest,
    MemoryCreateResponse,
    MemoryUpdateRequest,
    MemoryResponse,
    MemoryListResponse,
    ChatMessage,
)
from src.api.models.search import (
    SearchRequest,
    SearchResponse,
    TemporalFilter,
    SearchResultItem,
)
from src.api.models.brain import (
    BrainRetrieveRequest,
    BrainRetrieveResponse,
    ProcessInputRequest,
    ProcessInputResponse,
    ConsolidateRequest,
    ForgetRequest,
    FeedbackRequest,
    FeedbackResponse,
    PreferencesResponse,
)
from src.api.models.system import (
    HealthResponse,
    SystemStatsResponse,
    ArchiveExportRequest,
    ArchiveImportRequest,
    ArchiveResponse,
)

__all__ = [
    "MemoryType",
    "BrainRegionName",
    "ScopingParams",
    "PaginationParams",
    "MemoryCreateRequest",
    "MemoryCreateResponse",
    "MemoryUpdateRequest",
    "MemoryResponse",
    "MemoryListResponse",
    "ChatMessage",
    "SearchRequest",
    "SearchResponse",
    "TemporalFilter",
    "SearchResultItem",
    "BrainRetrieveRequest",
    "BrainRetrieveResponse",
    "ProcessInputRequest",
    "ProcessInputResponse",
    "ConsolidateRequest",
    "ForgetRequest",
    "FeedbackRequest",
    "FeedbackResponse",
    "PreferencesResponse",
    "HealthResponse",
    "SystemStatsResponse",
    "ArchiveExportRequest",
    "ArchiveImportRequest",
    "ArchiveResponse",
]
