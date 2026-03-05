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
import os

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
        config: Optional[StorageConfig] = None,
        global_vector_db=None,  # 🔥 2025-12-20 FIX: 全局FAISS用于MemoryRetrievalAgent
        global_db_manager=None  # 🔥 2026-01-27 FIX-011: 全局DBManager用于检索一致性
    ):
        """
        Initialize Storage Adapter

        Args:
            memory_system: Global MemorySystem instance (None for local-only mode)
            agent_id: Agent identifier for filtering
            config: Storage configuration
            global_vector_db: 🔥 Global VectorDB (FAISS) used by MemoryRetrievalAgent
            global_db_manager: 🔥 Global DBManager for retrieval consistency
        """
        self.memory_system = memory_system
        self.agent_id = agent_id
        self.config = config or StorageConfig()
        self.global_vector_db = global_vector_db  # 🔥 2025-12-20 FIX: 存储FAISS引用
        self.global_db_manager = global_db_manager  # 🔥 2026-01-27 FIX-011

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
            'delegation_calls': 0,
            'faiss_syncs': 0,  # 🔥 2025-12-20 FIX: FAISS同步次数
            'db_syncs': 0      # 🔥 2026-01-27 FIX-011: DB同步次数
        }

        logger.info(
            f"MemoryStorageAdapter initialized "
            f"(mode={'delegated' if self.config.use_global_storage else 'local'}, "
            f"cache={'enabled' if self.config.enable_local_cache else 'disabled'}, "
            f"global_faiss={'enabled' if global_vector_db else 'disabled'}, "
            f"global_db={'enabled' if global_db_manager else 'disabled'})"  # 🔥 FIX-011
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

                # 🔥 2026-01-27 FIX-011: 使用 global_memory_id 同步到 FAISS
                # 确保 FAISS 中的 ID 与 DB 中的 ID 一致
                faiss_memory_dict = memory_dict.copy()
                if global_memory_id:
                    faiss_memory_dict['id'] = global_memory_id  # 使用 DB 返回的 ID
                await self._sync_to_global_faiss(faiss_memory_dict)

                # Update local cache if enabled
                if self.config.enable_local_cache:
                    self._update_cache(memory_id, memory_dict)

                self.stats['delegation_calls'] += 1

                return {
                    'memory_id': global_memory_id or memory_id,
                    'stored': True,
                    'storage_location': 'global',
                    'cached': self.config.enable_local_cache,
                    'faiss_synced': self.global_vector_db is not None  # 🔥 FIX
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
        🔥 FIX: 传递预计算的 embedding 避免重复计算和丢失
        """
        try:
            # Extract fields
            content = memory_dict.get('content', '')
            importance = memory_dict.get('importance', 0.5)
            emotion_tags = memory_dict.get('emotion_tags', [])
            embedding = memory_dict.get('embedding')  # 🔥 FIX: 提取预计算的 embedding

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

            # 🔥 FIX: 传递预计算的 embedding 给全局系统
            memory_id = await self.memory_system.store_memory(
                content=content,
                memory_type="episodic",
                importance=importance,
                emotion_tags=emotion_tags,
                context_tags=[self.agent_id],  # Tag with source agent
                metadata=metadata,
                embedding=embedding  # 🔥 FIX: 传递 embedding
            )

            if memory_id:
                logger.debug(f"Delegated memory storage to global system: {memory_id}")
            else:
                logger.warning(f"Global storage returned None for memory (embedding may have failed)")

            return memory_id

        except Exception as e:
            logger.error(f"Error storing to global system: {e}")
            return None

    async def _sync_to_global_faiss(self, memory_dict: Dict[str, Any]) -> bool:
        """
        🔥 2025-12-20 FIX: 同步记忆到全局FAISS向量库
        🔥 2026-01-27 FIX-011: 同时同步到 DBManager 确保检索一致性

        解决问题: Hippocampus存储到KV后，MemoryRetrievalAgent无法检索到新记忆，
        因为 MemoryRetrievalAgent 使用 db_manager，而非 KV store。

        此方法在存储到KV后，同时同步到 FAISS 和 DBManager，确保检索一致性。

        Args:
            memory_dict: 包含 'id', 'content', 'embedding' 的记忆字典

        Returns:
            True if synced successfully, False otherwise
        """
        import numpy as np
        from .memory_item import MemoryItem

        memory_id = memory_dict.get('id')
        content = memory_dict.get('content', '')
        embedding = memory_dict.get('embedding')

        faiss_ok = False
        db_ok = False

        # 1. 同步到 FAISS
        if self.global_vector_db and embedding:
            try:
                embedding_np = np.array(embedding).astype('float32')
                if len(embedding_np.shape) == 2:
                    embedding_np = embedding_np.flatten()

                faiss_id = self.global_vector_db.add_vector(memory_id, embedding_np)
                self.stats['faiss_syncs'] += 1
                faiss_ok = True

                if self.stats['faiss_syncs'] % 100 == 0:
                    self.global_vector_db.save_index()
                    logger.info(f"📊 FAISS sync checkpoint: {self.stats['faiss_syncs']} synced")

                logger.debug(f"✅ FAISS sync: {memory_id} → idx={faiss_id}")

            except Exception as e:
                logger.warning(f"FAISS sync failed for {memory_id}: {e}")

        # 2. FIX-011 (deprecated): DBManager dual-write
        # Controlled by BMAM_USE_DISTRIBUTED_RETRIEVAL env var.
        # Default "true" => skip dual-write (FIX-016 distributed
        # retrieval is the primary path).
        # Set to "false" to re-enable the legacy dual-write.
        _use_distributed = os.environ.get(
            "BMAM_USE_DISTRIBUTED_RETRIEVAL", "true"
        ).lower() in ("true", "1", "yes")

        if not _use_distributed and self.global_db_manager:
            try:
                # 创建 MemoryItem
                memory_item = MemoryItem(
                    id=memory_id,
                    content=content,
                    memory_type=memory_dict.get(
                        'metadata', {}
                    ).get('memory_type', 'episodic'),
                    importance=memory_dict.get(
                        'importance', 0.5
                    ),
                    emotion_tags=memory_dict.get(
                        'emotion_tags', []
                    ),
                    context_tags=[self.agent_id],
                    metadata=memory_dict.get('metadata', {})
                )

                # 设置 embedding
                if embedding:
                    memory_item.embedding = np.array(embedding)

                # 保存到 DB
                success = self.global_db_manager.save_memory(
                    memory_item
                )
                if success:
                    self.stats['db_syncs'] += 1
                    db_ok = True
                    logger.debug(
                        f"DB sync: {memory_id}"
                    )
                else:
                    logger.warning(
                        f"DB sync returned False "
                        f"for {memory_id}"
                    )

            except Exception as e:
                logger.warning(
                    f"DB sync failed for "
                    f"{memory_id}: {e}"
                )
        elif _use_distributed and self.global_db_manager:
            logger.debug(
                f"Skipping DBManager dual-write for "
                f"{memory_id} (distributed retrieval "
                f"enabled via FIX-016)"
            )

        return faiss_ok or db_ok

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
        k: int = 10,
        query_vector: Optional[List[float]] = None  # 🔥 2025-12-20 FIX: 添加查询向量参数
    ) -> List[Dict[str, Any]]:
        """
        Retrieve Memories (from global system or local cache)
        检索记忆（从全局系统或本地缓存）

        Args:
            query: Search query text
            filters: Filter criteria (entities, time_range, etc.)
            k: Number of results to return
            query_vector: Pre-computed query embedding for semantic search (optional)

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

                # 🔥 2025-12-20 FIX: 传递查询向量以启用语义检索
                # 修复存储/检索割裂问题 - 之前全局路径未使用向量检索
                import numpy as np
                query_vector_np = np.array(query_vector) if query_vector else None

                # Call global system's search
                results = await self.memory_system.search_memories(
                    query=query or "",
                    k=k,
                    filters=global_filters,
                    query_vector=query_vector_np  # 🔥 FIX: 传递查询向量
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

    # =========================================================================
    # 🔥 NEW: Global Storage Sync (全局存储同步)
    # =========================================================================

    async def sync_from_global(
        self,
        limit: int = 1000,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Sync memories from global storage to local cache
        从全局存储同步记忆到本地缓存

        Called on startup to ensure local cache reflects global state.
        解决本地缓存与全局存储状态漂移问题。

        Args:
            limit: Maximum memories to sync
            filters: Optional filters for sync

        Returns:
            {
                'synced_count': int,
                'global_total': int,
                'cache_updated': bool
            }
        """
        if not self.config.use_global_storage or not self.memory_system:
            return {
                'synced_count': 0,
                'global_total': 0,
                'cache_updated': False,
                'reason': 'global_storage_disabled'
            }

        try:
            # Query global storage for this agent's memories
            global_filters = filters or {}
            global_filters['context_tags'] = [self.agent_id]

            # Get total count from global storage
            global_total = await self._get_global_count()

            # Retrieve memories from global storage
            results = await self.memory_system.search_memories(
                query="",  # Empty query to get all
                k=limit,
                filters=global_filters
            )

            # Update local cache
            synced_count = 0
            for result in results:
                memory_dict = self._convert_from_global(result)
                memory_id = memory_dict.get('id')
                if memory_id:
                    self._update_cache(memory_id, memory_dict)
                    synced_count += 1

            self.stats['sync_from_global'] = self.stats.get('sync_from_global', 0) + 1

            logger.info(
                f"✅ Synced {synced_count} memories from global storage "
                f"(global_total={global_total}, cache_size={len(self._local_cache)})"
            )

            return {
                'synced_count': synced_count,
                'global_total': global_total,
                'cache_updated': True
            }

        except Exception as e:
            logger.error(f"❌ Failed to sync from global storage: {e}")
            return {
                'synced_count': 0,
                'global_total': 0,
                'cache_updated': False,
                'error': str(e)
            }

    async def _get_global_count(self) -> int:
        """
        Get total memory count from global storage for this agent
        获取全局存储中该agent的记忆总数
        """
        try:
            if hasattr(self.memory_system, 'get_memory_count'):
                return await self.memory_system.get_memory_count(
                    filters={'context_tags': [self.agent_id]}
                )
            elif hasattr(self.memory_system, 'count_memories'):
                return await self.memory_system.count_memories(
                    filters={'context_tags': [self.agent_id]}
                )
            else:
                # Fallback: do a search and count results
                results = await self.memory_system.search_memories(
                    query="",
                    k=10000,  # Large number to get all
                    filters={'context_tags': [self.agent_id]}
                )
                return len(results)
        except Exception as e:
            logger.warning(f"Failed to get global count: {e}")
            return 0

    async def verify_consistency(self) -> Dict[str, Any]:
        """
        Verify consistency between local cache and global storage
        验证本地缓存与全局存储的一致性

        Returns:
            {
                'consistent': bool,
                'local_count': int,
                'global_count': int,
                'missing_in_local': int,
                'missing_in_global': int
            }
        """
        if not self.config.use_global_storage or not self.memory_system:
            return {
                'consistent': True,
                'reason': 'local_only_mode'
            }

        try:
            local_ids = set(self._local_cache.keys())
            local_count = len(local_ids)

            # Get global IDs
            global_results = await self.memory_system.search_memories(
                query="",
                k=10000,
                filters={'context_tags': [self.agent_id]}
            )
            global_ids = set()
            for r in global_results:
                metadata = r.get('metadata', {})
                original_id = metadata.get('original_id', r.get('id'))
                if original_id:
                    global_ids.add(original_id)
            global_count = len(global_ids)

            # Find discrepancies
            missing_in_local = global_ids - local_ids
            missing_in_global = local_ids - global_ids

            consistent = len(missing_in_local) == 0 and len(missing_in_global) == 0

            result = {
                'consistent': consistent,
                'local_count': local_count,
                'global_count': global_count,
                'missing_in_local': len(missing_in_local),
                'missing_in_global': len(missing_in_global)
            }

            if not consistent:
                logger.warning(
                    f"⚠️ Cache inconsistency detected: "
                    f"local={local_count}, global={global_count}, "
                    f"missing_local={len(missing_in_local)}, missing_global={len(missing_in_global)}"
                )

            return result

        except Exception as e:
            logger.error(f"❌ Failed to verify consistency: {e}")
            return {
                'consistent': False,
                'error': str(e)
            }

    async def get_global_capacity_status(self) -> Dict[str, Any]:
        """
        Get capacity status based on global storage (not just local cache)
        基于全局存储获取容量状态（而非仅本地缓存）

        Returns:
            {
                'global_count': int,
                'local_cache_count': int,
                'capacity': int,
                'usage_percent': float,
                'source': 'global' | 'local'
            }
        """
        if self.config.use_global_storage and self.memory_system:
            global_count = await self._get_global_count()
            return {
                'global_count': global_count,
                'local_cache_count': len(self._local_cache),
                'source': 'global'
            }
        else:
            return {
                'global_count': len(self._local_cache),
                'local_cache_count': len(self._local_cache),
                'source': 'local'
            }
