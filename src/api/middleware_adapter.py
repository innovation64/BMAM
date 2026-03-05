"""MiddlewareAdapter — the single translation layer between REST API and Coordinator.

This is the *only* new class that touches BrainInspiredCoordinator. All routes
delegate to this adapter; no route imports coordinator internals directly.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.api.models.memory import (
    MemoryCreateRequest,
    MemoryCreateResponse,
    MemoryResponse,
    MemoryListResponse,
    MemoryUpdateRequest,
)
from src.api.models.search import (
    SearchRequest,
    SearchResponse,
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

logger = logging.getLogger(__name__)


class MiddlewareAdapter:
    """Translates REST CRUD semantics into BrainInspiredCoordinator calls.

    Instantiated once at application startup and shared across all requests
    via FastAPI dependency injection.
    """

    def __init__(self, coordinator) -> None:
        """
        Args:
            coordinator: A fully-initialised ``BrainInspiredCoordinator``.
        """
        self.coordinator = coordinator
        self.memory_system = coordinator.memory_system
        if self.memory_system is None:
            raise RuntimeError(
                "Coordinator memory_system is None — "
                "ensure the coordinator is fully initialised before creating the adapter."
            )

    # ------------------------------------------------------------------
    # Memory CRUD
    # ------------------------------------------------------------------

    async def add(self, req: MemoryCreateRequest) -> MemoryCreateResponse:
        """Store a new memory (Mem0 ``add()`` equivalent)."""
        try:
            content = req.resolved_content()
            timestamp = req.timestamp or datetime.now()
            result = await self.coordinator.store_memory_with_timestamp(
                content=content,
                timestamp=timestamp,
                speaker=req.speaker,
                importance=req.importance,
                user_id=req.user_id or "default",
                context=req.metadata,
            )
            memory_id = self._extract_memory_id(result)
            return MemoryCreateResponse(id=memory_id)
        except Exception as exc:
            logger.error("add() failed: %s", exc, exc_info=True)
            raise

    async def get(self, memory_id: str) -> Optional[MemoryResponse]:
        """Get a single memory by ID."""
        try:
            raw = await asyncio.to_thread(
                self.memory_system.db_manager.load_memory, memory_id
            )
            if raw is None:
                return None
            return self._memory_item_to_response(raw)
        except Exception as exc:
            logger.error("get(%s) failed: %s", memory_id, exc, exc_info=True)
            raise

    async def get_all(
        self,
        user_id: str = "default",
        page: int = 1,
        page_size: int = 50,
    ) -> MemoryListResponse:
        """List all memories with pagination."""
        try:
            all_memories = await asyncio.to_thread(
                self.memory_system.db_manager.get_all_memories
            )
            total = len(all_memories)
            start = (page - 1) * page_size
            end = start + page_size
            page_items = all_memories[start:end]
            return MemoryListResponse(
                memories=[self._dict_to_response(m) for m in page_items],
                total=total,
                page=page,
                page_size=page_size,
            )
        except Exception as exc:
            logger.error("get_all() failed: %s", exc, exc_info=True)
            raise

    async def update(
        self, memory_id: str, req: MemoryUpdateRequest
    ) -> bool:
        """Update a memory's fields."""
        try:
            updates: Dict[str, Any] = {}
            if req.content is not None:
                updates["content"] = req.content
            if req.importance is not None:
                updates["importance"] = req.importance
            if req.emotion_tags is not None:
                updates["emotion_tags"] = req.emotion_tags
            if req.context_tags is not None:
                updates["context_tags"] = req.context_tags
            if req.metadata is not None:
                updates["metadata"] = req.metadata
            if not updates:
                return True
            return await self.memory_system.update_memory(memory_id, updates)
        except Exception as exc:
            logger.error("update(%s) failed: %s", memory_id, exc, exc_info=True)
            raise

    async def delete(self, memory_id: str) -> bool:
        """Soft-delete a memory."""
        try:
            return await self.memory_system.delete_memory(memory_id)
        except Exception as exc:
            logger.error("delete(%s) failed: %s", memory_id, exc, exc_info=True)
            raise

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(self, req: SearchRequest) -> SearchResponse:
        """Semantic search (Mem0 ``search()`` equivalent).

        When ``use_brain_retrieval`` is *True*, delegates to the full 5-brain-region
        distributed retrieval pipeline.
        """
        try:
            context = req.context or {}
            if req.temporal_filter:
                context["temporal_filter"] = {
                    "start": (
                        req.temporal_filter.start.isoformat()
                        if req.temporal_filter.start else None
                    ),
                    "end": (
                        req.temporal_filter.end.isoformat()
                        if req.temporal_filter.end else None
                    ),
                }

            if req.use_brain_retrieval:
                brain_result = await self.coordinator.brain_retrieve(
                    query=req.query,
                    k=req.limit,
                    context=context,
                )
                items = [
                    self._dict_to_search_item(m)
                    for m in brain_result.memories
                ]
                return SearchResponse(
                    results=items,
                    total=len(items),
                    query=req.query,
                    retrieval_mode="brain_distributed",
                )

            raw = await self.coordinator.smart_retrieve(
                query=req.query,
                k=req.limit,
                strategy=req.strategy,
                context=context,
            )
            items = [self._dict_to_search_item(m) for m in raw]
            return SearchResponse(
                results=items,
                total=len(items),
                query=req.query,
                retrieval_mode="semantic",
            )
        except Exception as exc:
            logger.error("search() failed: %s", exc, exc_info=True)
            raise

    # ------------------------------------------------------------------
    # Brain-specific operations
    # ------------------------------------------------------------------

    async def brain_retrieve(
        self, req: BrainRetrieveRequest
    ) -> BrainRetrieveResponse:
        """5-brain-region distributed retrieval (BMAM exclusive)."""
        try:
            result = await self.coordinator.brain_retrieve(
                query=req.query,
                k=req.k,
                context=req.context,
                activation_plan=req.activation_plan,
                force_slow_path=req.force_slow_path,
            )
            items = [self._dict_to_search_item(m) for m in result.memories]
            return BrainRetrieveResponse(
                memories=items,
                path_type=result.path_type,
                iterations=result.iterations,
                gaps_detected=result.gaps_detected,
                confidence=result.confidence,
                retrieval_time_ms=result.retrieval_time_ms,
                debug_info=result.debug_info,
            )
        except Exception as exc:
            logger.error("brain_retrieve() failed: %s", exc, exc_info=True)
            raise

    async def process_input(
        self, req: ProcessInputRequest
    ) -> ProcessInputResponse:
        """Run the full brain-inspired processing pipeline."""
        try:
            context = req.context or {}
            context["user_id"] = req.user_id or "default"
            result = await self.coordinator.process_user_input(
                user_input=req.input,
                context=context,
            )
            return ProcessInputResponse(
                response=result.response,
                agents_involved=result.agents_involved,
                memories_retrieved=result.memories_retrieved,
                memory_stored=result.memory_stored,
                processing_time=result.processing_time,
                success=result.success,
                error=result.error,
                insights=result.insights,
                activation_trace=result.activation_trace,
            )
        except Exception as exc:
            logger.error("process_input() failed: %s", exc, exc_info=True)
            raise

    async def consolidate(self, req: ConsolidateRequest) -> Dict[str, Any]:
        """Trigger memory consolidation."""
        try:
            return await self.coordinator.consolidate_memories(
                evaluation_mode=req.evaluation_mode,
            )
        except Exception as exc:
            logger.error("consolidate() failed: %s", exc, exc_info=True)
            raise

    async def forget(self, req: ForgetRequest) -> Dict[str, Any]:
        """Trigger memory forgetting / pruning."""
        try:
            return await self.coordinator.trigger_forgetting(
                region=req.region,
                capacity_threshold=req.capacity_threshold,
            )
        except Exception as exc:
            logger.error("forget() failed: %s", exc, exc_info=True)
            raise

    async def apply_feedback(self, req: FeedbackRequest) -> FeedbackResponse:
        """Submit reinforcement feedback for a query."""
        try:
            result = await self.coordinator.apply_feedback(
                query_type=req.query_type,
                reward_signal=req.reward_signal,
                query=req.query,
                response=req.response,
                context=req.context,
            )
            return FeedbackResponse(
                status=result.get("status", "applied"),
                query_type=result.get("query_type", req.query_type),
                reward=result.get("reward", req.reward_signal),
                weight_delta=result.get("weight_delta", 0.0),
            )
        except Exception as exc:
            logger.error("apply_feedback() failed: %s", exc, exc_info=True)
            raise

    async def get_preferences(
        self, query: str, user_id: Optional[str] = None, k: int = 5
    ) -> PreferencesResponse:
        """Retrieve user preferences."""
        try:
            prefs = await self.coordinator.get_user_preferences(
                query=query, user_id=user_id, k=k
            )
            return PreferencesResponse(preferences=prefs, user_id=user_id)
        except Exception as exc:
            logger.error("get_preferences() failed: %s", exc, exc_info=True)
            raise

    # ------------------------------------------------------------------
    # System / health
    # ------------------------------------------------------------------

    def health(self) -> HealthResponse:
        """Return system health."""
        try:
            raw = self.coordinator.get_feature_health()
            pct = raw.get("health_percentage", 0.0)
            if pct >= 80:
                status = "healthy"
            elif pct >= 50:
                status = "degraded"
            else:
                status = "unhealthy"
            return HealthResponse(
                status=status,
                features=raw.get("features", {}),
                healthy_count=raw.get("healthy_count", 0),
                total_count=raw.get("total_count", 0),
                degraded_features=raw.get("degraded_features", []),
                health_percentage=pct,
            )
        except Exception as exc:
            logger.error("health() failed: %s", exc, exc_info=True)
            raise

    async def stats(self) -> SystemStatsResponse:
        """Return memory system statistics."""
        try:
            raw = await asyncio.to_thread(
                self.memory_system.db_manager.get_memory_stats
            )
            return SystemStatsResponse(
                total_memories=raw.get("total_memories", 0),
                episodic_memories=raw.get("episodic_memories", 0),
                semantic_memories=raw.get("semantic_memories", 0),
                database_url=raw.get("database_url", ""),
            )
        except Exception as exc:
            logger.error("stats() failed: %s", exc, exc_info=True)
            raise

    # ------------------------------------------------------------------
    # Archives (soul transfer)
    # ------------------------------------------------------------------

    def export_archive(self, req: ArchiveExportRequest) -> ArchiveResponse:
        """Export a memory archive."""
        try:
            result = self.coordinator.export_memory_archive(
                archive_name=req.archive_name,
                output_dir=Path(req.output_dir),
                description=req.description,
                tags=req.tags,
                include_faiss=req.include_faiss,
                metadata=req.metadata,
            )
            return ArchiveResponse(
                success=True, message="Archive exported", details=result
            )
        except Exception as exc:
            logger.exception("Archive export failed")
            return ArchiveResponse(
                success=False, message=str(exc)
            )

    def import_archive(self, req: ArchiveImportRequest) -> ArchiveResponse:
        """Import a memory archive."""
        try:
            result = self.coordinator.load_memory_archive(
                archive_path=Path(req.archive_path),
                target_dir=(
                    Path(req.target_dir) if req.target_dir else None
                ),
                validate=req.validate_archive,
                force=req.force,
            )
            return ArchiveResponse(
                success=True, message="Archive imported", details=result
            )
        except Exception as exc:
            logger.exception("Archive import failed")
            return ArchiveResponse(
                success=False, message=str(exc)
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_memory_id(result: Any) -> str:
        """Best-effort extraction of the memory ID from coordinator result."""
        if isinstance(result, dict):
            for key in ("memory_id", "id", "stored_id"):
                if key in result:
                    return str(result[key])
        if isinstance(result, str):
            return result
        return str(result) if result else "unknown"

    @staticmethod
    def _memory_item_to_response(item) -> MemoryResponse:
        """Convert a MemoryItem dataclass to MemoryResponse."""
        return MemoryResponse(
            id=item.id,
            content=item.content,
            memory_type=item.memory_type,
            importance=item.importance,
            brain_region=item.brain_region,
            consolidation_level=item.consolidation_level,
            access_frequency=item.access_frequency,
            timestamp=(
                item.timestamp.isoformat()
                if isinstance(item.timestamp, datetime) else str(item.timestamp)
            ),
            emotion_tags=item.emotion_tags or [],
            context_tags=item.context_tags or [],
            metadata=item.metadata or {},
        )

    @staticmethod
    def _dict_to_response(d: Dict[str, Any]) -> MemoryResponse:
        """Convert a raw dict (from db_manager.get_all_memories) to MemoryResponse."""
        return MemoryResponse(
            id=d.get("id", ""),
            content=d.get("content", ""),
            memory_type=d.get("memory_type", "episodic"),
            importance=d.get("importance", 0.5),
            brain_region=d.get("brain_region", "hippocampus"),
            consolidation_level=d.get("consolidation_level", 0),
            access_frequency=d.get("access_frequency", 0),
            timestamp=d.get("timestamp"),
            emotion_tags=d.get("emotion_tags", []),
            context_tags=d.get("context_tags", []),
            metadata=d.get("metadata", {}),
        )

    @staticmethod
    def _dict_to_search_item(d: Dict[str, Any]) -> SearchResultItem:
        """Convert a raw memory dict to SearchResultItem."""
        return SearchResultItem(
            id=d.get("id", d.get("memory_id", "")),
            content=d.get("content", ""),
            score=d.get("score", d.get("relevance_score", 0.0)),
            memory_type=d.get("memory_type", "episodic"),
            brain_region=d.get("brain_region", "hippocampus"),
            timestamp=d.get("timestamp"),
            metadata=d.get("metadata", {}),
        )
