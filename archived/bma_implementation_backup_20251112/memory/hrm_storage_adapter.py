"""
HRM Storage Adapter - HRM感知的存储适配器
HRM-aware extension of MemoryStorageAdapter

Integrates HRM's multi-timescale coordination with Phase 3's storage delegation:
1. Supports timescale-aware storage (L=1, H=10)
2. Handles reset signals from higher timescales
3. Maintains working memory for fast iterations
4. Coordinates with Thalamus for global sync
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
import logging

from .storage_adapter import MemoryStorageAdapter, StorageConfig

logger = logging.getLogger(__name__)


@dataclass
class HRMStorageConfig(StorageConfig):
    """
    HRM Storage Configuration
    HRM存储配置

    Extends StorageConfig with HRM-specific settings.
    """
    timescale: int = 1  # Timescale (L=1 fast, H=10 slow)
    enable_working_memory: bool = True  # Local working memory for fast iterations
    working_memory_size: int = 50  # Size of working memory
    sync_on_reset: bool = True  # Full sync when receiving reset signal


class HRMStorageAdapter(MemoryStorageAdapter):
    """
    HRM-aware Storage Adapter
    HRM感知的存储适配器

    Extends MemoryStorageAdapter with HRM multi-timescale support:

    Features:
    1. Timescale-aware operations (fast L vs slow H)
    2. Reset signal handling from higher timescales
    3. Working memory for fast iterations
    4. Strategic guidance integration
    5. Local convergence detection support

    Usage:
        # For fast L module (Hippocampus)
        adapter = HRMStorageAdapter(
            memory_system=global_memory,
            agent_id="hippocampus",
            config=HRMStorageConfig(
                use_global_storage=True,
                timescale=1,  # Fast
                enable_working_memory=True
            )
        )

        # For slow H module (Prefrontal)
        adapter = HRMStorageAdapter(
            memory_system=global_memory,
            agent_id="prefrontal",
            config=HRMStorageConfig(
                use_global_storage=True,
                timescale=10,  # Slow
                enable_working_memory=False
            )
        )
    """

    def __init__(
        self,
        memory_system=None,
        agent_id: str = "hippocampus",
        config: Optional[HRMStorageConfig] = None
    ):
        """
        Initialize HRM Storage Adapter

        Args:
            memory_system: Global MemorySystem instance
            agent_id: Agent identifier
            config: HRM storage configuration
        """
        # Initialize parent with HRM config or default
        hrm_config = config or HRMStorageConfig()
        super().__init__(
            memory_system=memory_system,
            agent_id=agent_id,
            config=hrm_config
        )

        # HRM-specific config
        self.hrm_config = hrm_config

        # Working memory for fast iterations (L module)
        self.working_memory: List[Dict[str, Any]] = []
        self._working_memory_ids: set = set()

        # Strategic guidance from H module
        self.strategic_guidance: Optional[Dict[str, Any]] = None

        # Reset tracking
        self.last_reset_step = 0
        self.reset_count = 0

        # Timescale state
        self.current_step = 0
        self.should_update_this_step = True  # For slow modules

        # HRM metrics
        self.hrm_stats = {
            'timescale': hrm_config.timescale,
            'total_resets': 0,
            'working_memory_hits': 0,
            'working_memory_misses': 0,
            'fast_iterations': 0,
            'slow_iterations': 0
        }

        logger.info(
            f"HRMStorageAdapter initialized "
            f"(timescale={hrm_config.timescale}, "
            f"agent={agent_id}, "
            f"working_memory={'enabled' if hrm_config.enable_working_memory else 'disabled'})"
        )

    async def receive_reset_signal(
        self,
        reset_data: Dict[str, Any],
        source_agent: str = "prefrontal"
    ) -> Dict[str, Any]:
        """
        Receive Reset Signal from Higher Timescale (H → L)
        接收来自更高时间尺度的重置信号

        When H module (slow) decides to reset L module (fast):
        1. Clear working memory
        2. Update strategic guidance
        3. Reset iteration counters
        4. Optionally sync with global storage

        Args:
            reset_data: Reset information from H module
                - guidance: Strategic guidance for retrieval
                - focus_areas: Areas to focus on
                - reset_reason: Why the reset was triggered
            source_agent: Source of reset signal

        Returns:
            Status of reset operation
        """
        self.reset_count += 1
        self.hrm_stats['total_resets'] += 1
        self.last_reset_step = self.current_step

        logger.info(
            f"Received reset signal from {source_agent} "
            f"(step={self.current_step}, reset#{self.reset_count})"
        )

        # Update strategic guidance
        self.strategic_guidance = reset_data.get('guidance', {})

        # Clear working memory
        if self.hrm_config.enable_working_memory:
            old_size = len(self.working_memory)
            self.working_memory.clear()
            self._working_memory_ids.clear()
            logger.debug(f"Cleared working memory ({old_size} items)")

        # Optionally sync with global storage
        if self.hrm_config.sync_on_reset and self.config.use_global_storage:
            try:
                # Refresh cache from global system based on guidance
                focus_areas = reset_data.get('focus_areas', [])
                if focus_areas:
                    await self._refresh_cache_with_guidance(focus_areas)
            except Exception as e:
                logger.warning(f"Failed to sync on reset: {e}")

        return {
            'reset_acknowledged': True,
            'working_memory_cleared': self.hrm_config.enable_working_memory,
            'guidance_updated': bool(self.strategic_guidance),
            'reset_count': self.reset_count,
            'step': self.current_step
        }

    async def fast_retrieve(
        self,
        query: str,
        k: int = 10,
        use_working_memory: bool = True
    ) -> Dict[str, Any]:
        """
        Fast Retrieval for L Module
        L模块的快速检索

        Optimized for fast iterations:
        1. First check working memory (if enabled)
        2. Use strategic guidance for filtering
        3. Cache results in working memory

        Args:
            query: Search query
            k: Number of results
            use_working_memory: Whether to use working memory

        Returns:
            Retrieval results with HRM metadata
        """
        self.hrm_stats['fast_iterations'] += 1

        # Check working memory first (L module optimization)
        if use_working_memory and self.hrm_config.enable_working_memory:
            wm_results = self._search_working_memory(query, k)
            if wm_results:
                self.hrm_stats['working_memory_hits'] += 1
                logger.debug(
                    f"Working memory hit: {len(wm_results)} results for '{query[:30]}...'"
                )
                return {
                    'memories': wm_results,
                    'count': len(wm_results),
                    'source': 'working_memory',
                    'hrm_iteration': self.current_step - self.last_reset_step
                }

        self.hrm_stats['working_memory_misses'] += 1

        # Build filters from strategic guidance
        filters = {}
        if self.strategic_guidance:
            focus_areas = self.strategic_guidance.get('focus_areas', [])
            if focus_areas:
                filters['entities'] = focus_areas

        # Delegate to parent's retrieve
        results = await self.retrieve_memories(
            query=query,
            filters=filters,
            k=k
        )

        # Update working memory
        if self.hrm_config.enable_working_memory:
            self._update_working_memory(results)

        return {
            **results,
            'hrm_iteration': self.current_step - self.last_reset_step,
            'guided_by': 'strategic_guidance' if self.strategic_guidance else 'none'
        }

    async def slow_store(
        self,
        memory_dict: Dict[str, Any],
        strategic_importance: float = 0.5
    ) -> Dict[str, Any]:
        """
        Slow Storage for H Module
        H模块的慢速存储

        Used by H module (Prefrontal) for strategic storage:
        1. Add strategic metadata
        2. Store to global system
        3. Broadcast to L modules if needed

        Args:
            memory_dict: Memory data
            strategic_importance: Importance from H module perspective

        Returns:
            Storage result
        """
        self.hrm_stats['slow_iterations'] += 1

        # Add HRM metadata
        memory_dict['metadata'] = memory_dict.get('metadata', {})
        memory_dict['metadata'].update({
            'hrm_timescale': 'H',
            'strategic_importance': strategic_importance,
            'stored_at_step': self.current_step
        })

        # Delegate to parent's store
        result = await self.store_memory(memory_dict)

        logger.debug(
            f"Slow storage (H module): {memory_dict.get('id')} "
            f"(strategic_importance={strategic_importance})"
        )

        return result

    def _search_working_memory(
        self,
        query: str,
        k: int
    ) -> List[Dict[str, Any]]:
        """
        Search Working Memory
        搜索工作记忆

        Simple keyword matching in working memory.
        """
        if not self.working_memory:
            return []

        query_words = set(query.lower().split())

        # Score each memory
        scored = []
        for mem in self.working_memory:
            content = mem.get('content', '').lower()
            content_words = set(content.split())

            # Simple overlap score
            overlap = len(query_words & content_words)
            if overlap > 0:
                scored.append((mem, overlap))

        # Sort by score and return top k
        scored.sort(key=lambda x: x[1], reverse=True)
        return [mem for mem, score in scored[:k]]

    def _update_working_memory(self, memories: List[Dict[str, Any]]) -> None:
        """
        Update Working Memory
        更新工作记忆

        Add new memories, evict old ones if full (LRU).
        """
        if not self.hrm_config.enable_working_memory:
            return

        for mem in memories:
            mem_id = mem.get('id')
            if mem_id and mem_id not in self._working_memory_ids:
                # Add to working memory
                self.working_memory.append(mem)
                self._working_memory_ids.add(mem_id)

                # Evict oldest if full
                if len(self.working_memory) > self.hrm_config.working_memory_size:
                    evicted = self.working_memory.pop(0)
                    self._working_memory_ids.discard(evicted.get('id'))

    async def _refresh_cache_with_guidance(self, focus_areas: List[str]) -> None:
        """
        Refresh Cache with Strategic Guidance
        根据策略指导刷新缓存

        Pull relevant memories from global system based on focus areas.
        """
        if not self.config.use_global_storage or not self.memory_system:
            return

        try:
            # Query global system with focus areas
            filters = {'entities': focus_areas}
            results = await self.memory_system.search_memories(
                query=" ".join(focus_areas),
                k=self.hrm_config.working_memory_size,
                filters=filters
            )

            # Update working memory
            if results:
                self._update_working_memory(results)
                logger.debug(
                    f"Refreshed cache with {len(results)} memories "
                    f"for focus areas: {focus_areas}"
                )
        except Exception as e:
            logger.warning(f"Failed to refresh cache with guidance: {e}")

    def step(self) -> None:
        """
        Advance HRM Step Counter
        推进HRM步数计数器

        Should be called at each iteration by Thalamus.
        """
        self.current_step += 1

        # Check if slow module should update this step
        if self.hrm_config.timescale > 1:
            self.should_update_this_step = (
                self.current_step % self.hrm_config.timescale == 0
            )

    def get_hrm_stats(self) -> Dict[str, Any]:
        """Get HRM-specific statistics"""
        base_stats = super().get_stats()

        # Calculate working memory hit rate
        total_queries = (
            self.hrm_stats['working_memory_hits'] +
            self.hrm_stats['working_memory_misses']
        )
        hit_rate = (
            self.hrm_stats['working_memory_hits'] / total_queries
            if total_queries > 0 else 0.0
        )

        return {
            **base_stats,
            'hrm': {
                **self.hrm_stats,
                'current_step': self.current_step,
                'steps_since_reset': self.current_step - self.last_reset_step,
                'working_memory_size': len(self.working_memory),
                'working_memory_hit_rate': hit_rate,
                'has_strategic_guidance': bool(self.strategic_guidance)
            }
        }
