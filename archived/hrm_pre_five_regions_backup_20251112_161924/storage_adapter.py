"""
Storage Adapter - 存储适配器
统一海马体和全局记忆系统的存储接口

This adapter allows HippocampusAgent to delegate storage to the global MemorySystem
while maintaining backward compatibility with existing code.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class StorageConfig:
    """
    Storage Configuration
    存储配置

    Determines whether hippocampus uses local storage or delegates to global system.
    """
    use_global_storage: bool = True  # ✅ Default: delegate to global system
    enable_local_cache: bool = True  # Keep local cache for fast access
    sync_on_store: bool = True       # Auto-sync to global on every store


class MemoryStorageAdapter:
    """
    Memory Storage Adapter
    记忆存储适配器

    Provides unified interface for hippocampus to access storage,
    delegating to global MemorySystem when configured.

    Benefits:
    1. Single source of truth (global MemorySystem)
    2. Eliminates data duplication
    3. Consistent forgetting/consolidation
    4. Backward compatible with existing hippocampus code

    Usage:
        # Option 1: Delegate to global system (recommended)
        adapter = MemoryStorageAdapter(
            memory_system=global_memory_system,
            config=StorageConfig(use_global_storage=True)
        )

        # Option 2: Local storage only (legacy mode)
        adapter = MemoryStorageAdapter(
            memory_system=None,
            config=StorageConfig(use_global_storage=False)
        )
    """

    def __init__(
        self,
        memory_system=None,
        agent_id: str = "hippocampus",
        config: Optional[StorageConfig] = None
    ):
        """
        Initialize Storage Adapter

        Args:
            memory_system: Global MemorySystem instance (None for local-only mode)
            agent_id: Agent identifier for filtering
            config: Storage configuration
        """
        self.memory_system = memory_system
        self.agent_id = agent_id
        self.config = config or StorageConfig()

        # Local cache (for fast access even in delegation mode)
        self._local_cache: Dict[str, Any] = {}  # {memory_id: memory_dict}
        self._cache_order: List[str] = []  # For LRU eviction
        self._max_cache_size = 1000

        # Statistics
        self.stats = {
            'total_stores': 0,
            'total_retrievals': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'delegation_calls': 0
        }

        logger.info(
            f"MemoryStorageAdapter initialized "
            f"(mode={'delegated' if self.config.use_global_storage else 'local'}, "
            f"cache={'enabled' if self.config.enable_local_cache else 'disabled'})"
        )

    async def store_memory(
        self,
        memory_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Store Memory (delegates to global system if configured)
        存储记忆（如配置则委托给全局系统）

        Args:
            memory_dict: Memory data dictionary containing:
                - id: str
                - content: str
                - timestamp: datetime
                - entities: List[str]
                - importance: float
                - emotion_tags: List[str]
                - emotion_intensity: float
                - metadata: Dict
                - event_id: str (optional)
                - speaker: str (optional)

        Returns:
            {
                'memory_id': str,
                'stored': bool,
                'storage_location': 'global' | 'local',
                'cached': bool
            }
        """
        self.stats['total_stores'] += 1

        memory_id = memory_dict.get('id')

        # Delegate to global system if configured
        if self.config.use_global_storage and self.memory_system:
            try:
                # Convert hippocampus memory format to global system format
                global_memory_id = await self._store_to_global(memory_dict)

                # Update local cache if enabled
                if self.config.enable_local_cache:
                    self._update_cache(memory_id, memory_dict)

                self.stats['delegation_calls'] += 1

                return {
                    'memory_id': global_memory_id or memory_id,
                    'stored': True,
                    'storage_location': 'global',
                    'cached': self.config.enable_local_cache
                }

            except Exception as e:
                logger.error(f"Failed to delegate storage to global system: {e}")
                # Fallback to local storage
                return await self._store_local(memory_dict)

        else:
            # Local storage mode
            return await self._store_local(memory_dict)

    async def _store_to_global(self, memory_dict: Dict[str, Any]) -> Optional[str]:
        """
        Store to Global Memory System
        存储到全局记忆系统

        Maps hippocampus memory format to global system format.
        """
        try:
            # Extract fields
            content = memory_dict.get('content', '')
            importance = memory_dict.get('importance', 0.5)
            emotion_tags = memory_dict.get('emotion_tags', [])

            # Build metadata with hippocampus-specific fields
            metadata = memory_dict.get('metadata', {}).copy()
            metadata.update({
                'source_agent': self.agent_id,
                'original_id': memory_dict.get('id'),
                'entities': memory_dict.get('entities', []),
                'emotion_intensity': memory_dict.get('emotion_intensity', 0.0),
                'event_id': memory_dict.get('event_id'),
                'speaker': memory_dict.get('speaker'),
                'timestamp': memory_dict.get('timestamp').isoformat() if isinstance(memory_dict.get('timestamp'), datetime) else memory_dict.get('timestamp')
            })

            # Call global system's store_memory
            memory_id = await self.memory_system.store_memory(
                content=content,
                memory_type="episodic",
                importance=importance,
                emotion_tags=emotion_tags,
                context_tags=[self.agent_id],  # Tag with source agent
                metadata=metadata
            )

            logger.debug(f"Delegated memory storage to global system: {memory_id}")
            return memory_id

        except Exception as e:
            logger.error(f"Error storing to global system: {e}")
            return None

    async def _store_local(self, memory_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store to Local Cache Only (legacy mode)
        仅存储到本地缓存（遗留模式）
        """
        memory_id = memory_dict.get('id')
        self._update_cache(memory_id, memory_dict)

        return {
            'memory_id': memory_id,
            'stored': True,
            'storage_location': 'local',
            'cached': True
        }

    async def retrieve_memories(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve Memories (from global system or local cache)
        检索记忆（从全局系统或本地缓存）

        Args:
            query: Search query text
            filters: Filter criteria (entities, time_range, etc.)
            k: Number of results to return

        Returns:
            List of memory dictionaries
        """
        self.stats['total_retrievals'] += 1

        # Delegate to global system if configured
        if self.config.use_global_storage and self.memory_system:
            try:
                # Add agent filter to retrieve only hippocampus memories
                global_filters = filters or {}
                global_filters['context_tags'] = [self.agent_id]

                # Call global system's search
                results = await self.memory_system.search_memories(
                    query=query or "",
                    k=k,
                    filters=global_filters
                )

                self.stats['delegation_calls'] += 1

                # Convert back to hippocampus format
                return [self._convert_from_global(r) for r in results]

            except Exception as e:
                logger.error(f"Failed to retrieve from global system: {e}")
                # Fallback to local cache
                return self._retrieve_from_cache(query, filters, k)

        else:
            # Local cache mode
            return self._retrieve_from_cache(query, filters, k)

    def _retrieve_from_cache(
        self,
        query: Optional[str],
        filters: Optional[Dict[str, Any]],
        k: int
    ) -> List[Dict[str, Any]]:
        """Retrieve from local cache (simple filtering)"""
        results = list(self._local_cache.values())

        # Apply basic filters
        if filters:
            if 'entities' in filters:
                target_entities = set(filters['entities'])
                results = [
                    m for m in results
                    if any(e in m.get('entities', []) for e in target_entities)
                ]

            if 'time_range' in filters:
                start, end = filters['time_range']
                results = [
                    m for m in results
                    if start <= m.get('timestamp') <= end
                ]

        # Sort by timestamp (most recent first)
        results.sort(
            key=lambda m: m.get('timestamp', datetime.min),
            reverse=True
        )

        return results[:k]

    def _convert_from_global(self, global_memory: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert global memory format to hippocampus format
        将全局记忆格式转换为海马体格式
        """
        metadata = global_memory.get('metadata', {})

        return {
            'id': metadata.get('original_id', global_memory.get('id')),
            'content': global_memory.get('content'),
            'timestamp': metadata.get('timestamp'),
            'entities': metadata.get('entities', []),
            'importance': global_memory.get('importance'),
            'emotion_tags': global_memory.get('emotion_tags', []),
            'emotion_intensity': metadata.get('emotion_intensity', 0.0),
            'metadata': metadata,
            'event_id': metadata.get('event_id'),
            'speaker': metadata.get('speaker'),
            'access_count': global_memory.get('access_count', 0),
            'last_accessed': global_memory.get('last_accessed')
        }

    def _update_cache(self, memory_id: str, memory_dict: Dict[str, Any]) -> None:
        """
        Update Local Cache (LRU eviction)
        更新本地缓存（LRU驱逐）
        """
        if not self.config.enable_local_cache:
            return

        # Add to cache
        self._local_cache[memory_id] = memory_dict

        # Update LRU order
        if memory_id in self._cache_order:
            self._cache_order.remove(memory_id)
        self._cache_order.append(memory_id)

        # Evict oldest if cache is full
        if len(self._local_cache) > self._max_cache_size:
            oldest_id = self._cache_order.pop(0)
            del self._local_cache[oldest_id]

    def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics"""
        cache_hit_rate = (
            self.stats['cache_hits'] / self.stats['total_retrievals']
            if self.stats['total_retrievals'] > 0 else 0.0
        )

        return {
            **self.stats,
            'cache_size': len(self._local_cache),
            'cache_hit_rate': cache_hit_rate,
            'mode': 'delegated' if self.config.use_global_storage else 'local'
        }
