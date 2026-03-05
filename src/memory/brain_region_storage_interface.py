"""
Brain Region Storage Interface - 脑区存储统一接口
Unified storage interface for all brain regions with HRM support

Provides:
1. Abstract interface for brain-region-specific storage
2. HRM timescale awareness
3. Pluggable storage backends
4. Cross-region memory consolidation support
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import IntEnum
import logging

from .memory_item import MemoryItem

logger = logging.getLogger(__name__)


class BrainRegionType(IntEnum):
    """
    Brain Region Types
    脑区类型枚举
    """
    HIPPOCAMPUS = 1      # Episodic memory (fast, L module)
    TEMPORAL_LOBE = 2    # Semantic memory (slow, H module)
    AMYGDALA = 3         # Emotional memory (fast, L module)
    PREFRONTAL = 4       # Executive/working memory (slow, H module)
    BASAL_GANGLIA = 5    # Procedural memory (medium)


class HRMTimescale(IntEnum):
    """
    HRM Timescales for Brain Regions
    HRM时间尺度
    """
    FAST = 1       # L module: Hippocampus, Amygdala
    MEDIUM = 3     # Basal Ganglia
    SLOW = 10      # H module: Prefrontal, Temporal Lobe


@dataclass
class StorageCapabilities:
    """
    Storage Capabilities for a Brain Region
    脑区存储能力描述
    """
    supports_vector_search: bool = True
    supports_keyword_search: bool = True
    supports_graph_relations: bool = False
    supports_emotional_tags: bool = False
    supports_temporal_indexing: bool = True
    max_capacity: Optional[int] = None
    forgetting_enabled: bool = True


@dataclass
class BrainRegionStorageConfig:
    """
    Brain Region Storage Configuration
    脑区存储配置
    """
    brain_region: BrainRegionType
    hrm_timescale: HRMTimescale
    capabilities: StorageCapabilities
    use_global_storage: bool = True
    enable_local_cache: bool = True
    cache_size: int = 1000
    sync_on_store: bool = True


class IBrainRegionStorage(ABC):
    """
    Brain Region Storage Interface
    脑区存储统一接口

    All brain region storage adapters must implement this interface.
    Provides HRM-aware storage and retrieval with region-specific optimizations.
    """

    def __init__(
        self,
        config: BrainRegionStorageConfig,
        memory_system=None,
        agent_id: str = "unknown"
    ):
        """
        Initialize Brain Region Storage

        Args:
            config: Storage configuration
            memory_system: Global memory system instance
            agent_id: Agent identifier
        """
        self.config = config
        self.memory_system = memory_system
        self.agent_id = agent_id

        # HRM state
        self.current_step = 0
        self.last_update_step = -1

        # Cache for fast access
        self.local_cache: List[MemoryItem] = []
        self._cache_ids: set = set()

        # Statistics
        self.stats = {
            'total_stores': 0,
            'total_retrievals': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'hrm_fast_ops': 0,
            'hrm_slow_ops': 0
        }

        logger.info(
            f"IBrainRegionStorage initialized "
            f"(region={config.brain_region.name}, timescale={config.hrm_timescale.value})"
        )

    @property
    @abstractmethod
    def brain_region_name(self) -> str:
        """Get brain region name"""
        pass

    @property
    def hrm_timescale(self) -> int:
        """Get HRM timescale"""
        return self.config.hrm_timescale.value

    @property
    def should_update_this_step(self) -> bool:
        """
        Check if this region should update at current step
        检查当前步是否应该更新
        """
        if self.config.hrm_timescale == HRMTimescale.FAST:
            return True  # Update every step
        else:
            return self.current_step % self.config.hrm_timescale.value == 0

    @abstractmethod
    async def region_store(
        self,
        memory: MemoryItem,
        hrm_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store Memory with Brain-Region-Specific Strategy
        使用脑区特异性策略存储记忆

        Args:
            memory: Memory item to store
            hrm_metadata: HRM-specific metadata (timescale, guidance, etc.)

        Returns:
            Memory ID
        """
        pass

    @abstractmethod
    async def region_retrieve(
        self,
        query: str,
        hrm_guidance: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
        k: int = 10
    ) -> List[MemoryItem]:
        """
        Retrieve Memories with Brain-Region-Specific Strategy
        使用脑区特异性策略检索记忆

        Args:
            query: Search query
            hrm_guidance: Strategic guidance from H module
            filters: Additional filters
            k: Number of results

        Returns:
            List of memory items
        """
        pass

    @abstractmethod
    async def receive_hrm_signal(
        self,
        signal: Dict[str, Any],
        source_region: str
    ) -> Dict[str, Any]:
        """
        Receive HRM Signal from Other Brain Region
        接收来自其他脑区的HRM信号

        Args:
            signal: HRM signal (reset, consolidation, etc.)
            source_region: Source brain region

        Returns:
            Acknowledgment
        """
        pass

    def advance_step(self) -> None:
        """
        Advance HRM Step Counter
        推进HRM步数计数器

        Called by Thalamus at each global step.
        """
        self.current_step += 1

    def _should_use_cache(self) -> bool:
        """Check if cache should be used for this operation"""
        return self.config.enable_local_cache and len(self.local_cache) > 0

    def _dict_to_memory_item(self, mem_dict: Dict[str, Any]) -> MemoryItem:
        """Convert memory dict from memory_system to MemoryItem object"""
        return MemoryItem(
            id=mem_dict.get('id', ''),
            content=mem_dict.get('content', ''),
            memory_type=mem_dict.get('memory_type', 'episodic'),
            timestamp=mem_dict.get('timestamp', ''),
            importance=mem_dict.get('importance', 0.5),
            entities=mem_dict.get('entities', []),
            relations=mem_dict.get('relations', []),
            emotion_tags=mem_dict.get('emotion_tags', []),
            metadata=mem_dict.get('metadata', {})
        )

    def _update_cache(self, memories: List[MemoryItem]) -> None:
        """
        Update Local Cache
        更新本地缓存

        Args:
            memories: Memories to cache
        """
        if not self.config.enable_local_cache:
            return

        for mem in memories:
            if mem.id not in self._cache_ids:
                self.local_cache.append(mem)
                self._cache_ids.add(mem.id)

                # Evict oldest if cache full
                if len(self.local_cache) > self.config.cache_size:
                    evicted = self.local_cache.pop(0)
                    self._cache_ids.discard(evicted.id)

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get Storage Statistics
        获取存储统计信息

        Returns:
            Statistics dictionary
        """
        return {
            'agent_id': self.agent_id,
            'brain_region': self.config.brain_region.name,
            'hrm_timescale': self.config.hrm_timescale.value,
            'current_step': self.current_step,
            'cache_size': len(self.local_cache),
            'cache_hit_rate': (
                self.stats['cache_hits'] /
                max(1, self.stats['cache_hits'] + self.stats['cache_misses'])
            ),
            'stats': self.stats
        }


class HippocampusStorage(IBrainRegionStorage):
    """
    Hippocampus-Specific Storage
    海马体专属存储

    Optimized for:
    - Fast episodic memory retrieval (L module)
    - Event-based indexing
    - Temporal queries
    """

    @property
    def brain_region_name(self) -> str:
        return "hippocampus"

    async def region_store(
        self,
        memory: MemoryItem,
        hrm_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store episodic memory with event indexing"""
        self.stats['total_stores'] += 1
        self.stats['hrm_fast_ops'] += 1

        # Set brain region
        memory.brain_region = "hippocampus"
        memory.memory_type = "episodic"

        # Add HRM metadata
        if hrm_metadata:
            memory.metadata.update({
                'hrm_timescale': 'L',
                'hrm_iteration': hrm_metadata.get('iteration', 0)
            })

        # Store to global system
        if self.memory_system and self.config.use_global_storage:
            memory_id = await self.memory_system.store_memory(
                content=memory.content,
                memory_type=memory.memory_type,
                importance=memory.importance,
                emotion_tags=memory.emotion_tags,
                context_tags=memory.context_tags,
                metadata=memory.metadata
            )
        else:
            memory_id = memory.id

        # Update cache
        self._update_cache([memory])

        logger.debug(f"Hippocampus stored episodic memory: {memory_id}")

        return memory_id

    async def region_retrieve(
        self,
        query: str,
        hrm_guidance: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
        k: int = 10
    ) -> List[MemoryItem]:
        """Retrieve episodic memories with HRM guidance"""
        self.stats['total_retrievals'] += 1
        self.stats['hrm_fast_ops'] += 1

        # Check cache first (L module optimization)
        if self._should_use_cache():
            cache_results = self._search_cache(query, k)
            if cache_results:
                self.stats['cache_hits'] += 1
                logger.debug(f"Hippocampus cache hit: {len(cache_results)} results")
                return cache_results

        self.stats['cache_misses'] += 1

        # Apply HRM guidance to filters
        if hrm_guidance:
            filters = filters or {}
            if 'focus_areas' in hrm_guidance:
                filters['entities'] = hrm_guidance['focus_areas']

        # Retrieve from global system
        if self.memory_system and self.config.use_global_storage:
            raw_results = await self.memory_system.search_memories(
                query=query,
                k=k,
                filters=filters
            )
            # Convert dicts to MemoryItem objects
            results = [self._dict_to_memory_item(r) for r in raw_results]
        else:
            results = []

        # Update cache
        self._update_cache(results)

        return results

    async def receive_hrm_signal(
        self,
        signal: Dict[str, Any],
        source_region: str
    ) -> Dict[str, Any]:
        """Receive reset/guidance signal from Prefrontal (H module)"""
        action = signal.get('action')

        if action == 'reset_working_memory':
            # Clear cache
            self.local_cache.clear()
            self._cache_ids.clear()
            logger.info(f"Hippocampus received reset from {source_region}")

        return {'acknowledged': True, 'action': action}

    def _search_cache(self, query: str, k: int) -> List[MemoryItem]:
        """Search local cache"""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        # Score cached memories
        scored = []
        for mem in self.local_cache:
            content_words = set(mem.content.lower().split())
            overlap = len(query_words & content_words)
            if overlap > 0:
                scored.append((mem, overlap))

        # Sort and return top k
        scored.sort(key=lambda x: x[1], reverse=True)
        return [mem for mem, score in scored[:k]]


class TemporalLobeStorage(IBrainRegionStorage):
    """
    Temporal Lobe-Specific Storage
    颞叶专属存储

    Optimized for:
    - Slow semantic consolidation (H module)
    - Knowledge graph integration
    - Concept-based retrieval
    """

    @property
    def brain_region_name(self) -> str:
        return "temporal_lobe"

    async def region_store(
        self,
        memory: MemoryItem,
        hrm_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store semantic memory with KG integration"""
        self.stats['total_stores'] += 1
        self.stats['hrm_slow_ops'] += 1

        # Set brain region
        memory.brain_region = "neocortex"  # Temporal lobe uses neocortex
        memory.memory_type = "semantic"

        # Add HRM metadata
        if hrm_metadata:
            memory.metadata.update({
                'hrm_timescale': 'H',
                'consolidation_step': hrm_metadata.get('consolidation_step', 0)
            })

        # Store to global system
        if self.memory_system and self.config.use_global_storage:
            memory_id = await self.memory_system.store_memory(
                content=memory.content,
                memory_type=memory.memory_type,
                importance=memory.importance,
                context_tags=memory.context_tags,
                metadata=memory.metadata
            )
        else:
            memory_id = memory.id

        logger.debug(f"Temporal Lobe stored semantic memory: {memory_id}")

        return memory_id

    async def region_retrieve(
        self,
        query: str,
        hrm_guidance: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
        k: int = 10
    ) -> List[MemoryItem]:
        """Retrieve semantic memories"""
        self.stats['total_retrievals'] += 1
        self.stats['hrm_slow_ops'] += 1

        # Semantic retrieval from global system
        if self.memory_system and self.config.use_global_storage:
            results = await self.memory_system.search_memories(
                query=query,
                k=k,
                filters={'memory_type': 'semantic', **(filters or {})}
            )
        else:
            results = []

        return results

    async def receive_hrm_signal(
        self,
        signal: Dict[str, Any],
        source_region: str
    ) -> Dict[str, Any]:
        """Receive consolidation signal from Hippocampus (L module)"""
        action = signal.get('action')

        if action == 'promote_to_semantic':
            # Handle episodic → semantic consolidation
            memory_ids = signal.get('memory_ids', [])
            logger.info(
                f"Temporal Lobe received consolidation request from {source_region}: "
                f"{len(memory_ids)} memories"
            )

        return {'acknowledged': True, 'action': action}


class AmygdalaStorage(IBrainRegionStorage):
    """
    Amygdala-Specific Storage
    杏仁核专属存储

    Optimized for:
    - Fast emotional tagging (L module)
    - Emotion-based indexing
    - High-intensity memory prioritization
    """

    @property
    def brain_region_name(self) -> str:
        return "amygdala"

    async def region_store(
        self,
        memory: MemoryItem,
        hrm_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store emotional tag"""
        self.stats['total_stores'] += 1
        self.stats['hrm_fast_ops'] += 1

        # Set brain region
        memory.brain_region = "amygdala"

        # Add HRM metadata
        if hrm_metadata:
            memory.metadata.update({
                'hrm_timescale': 'L',
                'emotion_regulation': hrm_metadata.get('regulation', 'normal')
            })

        # Store to global system
        if self.memory_system and self.config.use_global_storage:
            memory_id = await self.memory_system.store_memory(
                content=memory.content,
                memory_type=memory.memory_type,
                importance=memory.importance,
                emotion_tags=memory.emotion_tags,
                emotion_intensity=memory.emotion_intensity,
                metadata=memory.metadata
            )
        else:
            memory_id = memory.id

        logger.debug(f"Amygdala stored emotional tag: {memory_id}")

        return memory_id

    async def region_retrieve(
        self,
        query: str,
        hrm_guidance: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
        k: int = 10
    ) -> List[MemoryItem]:
        """Retrieve emotion-tagged memories"""
        self.stats['total_retrievals'] += 1
        self.stats['hrm_fast_ops'] += 1

        # Filter by emotion intensity
        filters = filters or {}
        filters['min_emotion_intensity'] = 0.5  # High-emotion memories

        # Retrieve from global system
        if self.memory_system and self.config.use_global_storage:
            results = await self.memory_system.search_memories(
                query=query,
                k=k,
                filters=filters
            )
        else:
            results = []

        return results

    async def receive_hrm_signal(
        self,
        signal: Dict[str, Any],
        source_region: str
    ) -> Dict[str, Any]:
        """Receive emotion regulation signal from Prefrontal"""
        action = signal.get('action')

        if action == 'reset_emotional_state':
            # Clear emotional state
            logger.info(f"Amygdala received reset from {source_region}")

        return {'acknowledged': True, 'action': action}
