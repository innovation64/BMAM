"""
Memory Coordinator Module
Handles memory storage, retrieval, consolidation, and forgetting operations.

This is the slim public API that delegates to handler classes:
- MemoryStorageHandler: storage, chunking, dispatch, consolidation, forgetting
- MemoryRetrievalHandler: smart_retrieve, semantic fallback, episode extraction
- MemoryAnalysisHandler: KG coverage, cross-region retrieval, fusion, StoryArc
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from ..utils.config import get_logger
from .confidence_calibrator import get_confidence_calibrator
from .brain_retrieval_integration import get_brain_retrieval
from ..memory.story_arc import get_story_arc_manager

from .memory_storage import MemoryStorageHandler
from .memory_retrieval import MemoryRetrievalHandler
from .memory_analysis import MemoryAnalysisHandler

logger = get_logger(__name__)


class MemoryCoordinator:
    """Coordinates memory operations across brain regions"""

    def __init__(self, hippocampus, temporal_lobe, consolidation_agent,
                 forgetting_agent, agent_lifecycle_manager, memory_system=None,
                 amygdala=None, prefrontal_storage=None, basal_ganglia=None):
        """
        Initialize Memory Coordinator

        Args:
            hippocampus: Hippocampus agent instance
            temporal_lobe: Temporal lobe agent instance
            consolidation_agent: Consolidation agent instance
            forgetting_agent: Forgetting agent instance
            agent_lifecycle_manager: Agent lifecycle manager for activation
            memory_system: MemorySystem instance for persistent storage (optional)
            amygdala: Amygdala agent for emotional tagging (optional)
            prefrontal_storage: Prefrontal agent for reasoning traces (optional)
            basal_ganglia: Basal ganglia agent for procedural memory (optional)
        """
        self.hippocampus = hippocampus
        self.temporal_lobe = temporal_lobe
        self.consolidation_agent = consolidation_agent
        self.forgetting_agent = forgetting_agent
        self.agent_lifecycle = agent_lifecycle_manager
        self.memory_system = memory_system

        # Additional brain regions for collaborative storage
        self.amygdala = amygdala
        self.prefrontal_storage = prefrontal_storage
        self.basal_ganglia = basal_ganglia

        # Cross-region confidence calibrator
        self.confidence_calibrator = get_confidence_calibrator()

        # Brain-inspired retrieval system (fast/slow paths + iterative + gap detection)
        self.brain_retrieval = get_brain_retrieval(
            memory_coordinator=self,
            enable_fast_path=True,
            enable_iterative=True,
            max_iterations=3
        )
        logger.info("MemoryCoordinator: BrainInspiredRetrieval initialized")

        # StoryArc timeline indexing
        self.story_arc = get_story_arc_manager()
        logger.info(
            f"MemoryCoordinator: StoryArcManager initialized "
            f"({self.story_arc.get_statistics()['total_events']} events)"
        )

        # Initialize handler classes
        self._storage = MemoryStorageHandler(self)
        self._retrieval = MemoryRetrievalHandler(self)
        self._analysis = MemoryAnalysisHandler(self)

    # ==================================================================
    # Storage delegates
    # ==================================================================

    async def store_long_document(self, *args, **kwargs):
        return await self._storage.store_long_document(*args, **kwargs)

    async def store_memory_with_timestamp(self, *args, **kwargs):
        return await self._storage.store_memory_with_timestamp(*args, **kwargs)

    async def _dispatch_to_other_brain_regions(self, *args, **kwargs):
        return await self._storage._dispatch_to_other_brain_regions(
            *args, **kwargs
        )

    async def _extract_and_store_preferences(self, *args, **kwargs):
        return await self._storage._extract_and_store_preferences(
            *args, **kwargs
        )

    async def store_memory_if_needed(self, *args, **kwargs):
        return await self._storage.store_memory_if_needed(*args, **kwargs)

    async def trigger_consolidation(self, *args, **kwargs):
        return await self._storage.trigger_consolidation(*args, **kwargs)

    async def consolidate_memories(self, *args, **kwargs):
        return await self._storage.consolidate_memories(*args, **kwargs)

    async def trigger_forgetting(self, *args, **kwargs):
        return await self._storage.trigger_forgetting(*args, **kwargs)

    async def _async_post_process_summary(self, *args, **kwargs):
        return await self._storage._async_post_process_summary(
            *args, **kwargs
        )

    # ==================================================================
    # Retrieval delegates
    # ==================================================================

    async def smart_retrieve(self, *args, **kwargs):
        return await self._retrieval.smart_retrieve(*args, **kwargs)

    async def _pure_semantic_fallback(self, *args, **kwargs):
        return await self._retrieval._pure_semantic_fallback(*args, **kwargs)

    async def extract_semantic_from_episodes(self, *args, **kwargs):
        return await self._retrieval.extract_semantic_from_episodes(
            *args, **kwargs
        )

    # ==================================================================
    # Analysis delegates
    # ==================================================================

    def _calculate_kg_coverage(self, *args, **kwargs):
        return self._analysis._calculate_kg_coverage(*args, **kwargs)

    def _is_multi_hop_query(self, *args, **kwargs):
        return self._analysis._is_multi_hop_query(*args, **kwargs)

    async def cross_region_retrieval(self, *args, **kwargs):
        return await self._analysis.cross_region_retrieval(*args, **kwargs)

    async def _fuse_cross_region_results(self, *args, **kwargs):
        return await self._analysis._fuse_cross_region_results(
            *args, **kwargs
        )

    def record_retrieval_outcome(self, *args, **kwargs):
        return self._analysis.record_retrieval_outcome(*args, **kwargs)

    def get_calibration_stats(self, *args, **kwargs):
        return self._analysis.get_calibration_stats(*args, **kwargs)

    def save_calibration(self, *args, **kwargs):
        return self._analysis.save_calibration(*args, **kwargs)

    def _calibrate_region_confidence(self, *args, **kwargs):
        return self._analysis._calibrate_region_confidence(*args, **kwargs)

    def _get_memory_id(self, *args, **kwargs):
        return self._analysis._get_memory_id(*args, **kwargs)

    def _get_memory_score(self, *args, **kwargs):
        return self._analysis._get_memory_score(*args, **kwargs)

    async def query_event_time(self, *args, **kwargs):
        return await self._analysis.query_event_time(*args, **kwargs)

    async def calculate_duration(self, *args, **kwargs):
        return await self._analysis.calculate_duration(*args, **kwargs)

    def get_story_arc_statistics(self, *args, **kwargs):
        return self._analysis.get_story_arc_statistics(*args, **kwargs)

    def clear_story_arc(self, *args, **kwargs):
        return self._analysis.clear_story_arc(*args, **kwargs)
