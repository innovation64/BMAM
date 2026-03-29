"""
Hippocampus Agent - 海马体智能体
对应脑区: 海马体 (Hippocampus)
主要功能: 情节记忆存储+检索+巩固
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)


from ...base import BrainAgent, AgentMessage, BrainRegion
from ....utils.knowledge_graph_builder import KnowledgeGraphBuilder
from ....memory.storage_adapter import MemoryStorageAdapter, StorageConfig
from ....memory.key_value_stores import KeyValueMemoryStore
from ....memory.brain_regions.hippocampal_event_graph import HippocampalEventGraph
from ....memory.storage_coordinator import get_storage_coordinator
from ....utils.paths import BMAMPaths


@dataclass
class EpisodicMemory:
    """情节记忆项"""
    id: str
    content: str
    timestamp: datetime
    entities: List[str] = field(default_factory=list)
    importance: float = 0.5
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    emotion_tags: List[str] = field(default_factory=list)
    emotion_intensity: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    event_id: Optional[str] = None
    speaker: Optional[str] = None
    user_id: str = "default"  # 🔥 2025-12-25: 用户ID隔离


class HippocampusAgentCore(BrainAgent):
    """
    海马体智能体核心类 - 包含初始化和消息处理
    """
    def __init__(
        self,
        capacity: int = 20000,
        temporal_lobe_agent=None,
        client=None,
        embedding_service=None,
        kg_builder: Optional[KnowledgeGraphBuilder] = None,
        memory_system=None,  # ✅ NEW: Global memory system for delegation
        use_global_storage: bool = False,  # ✅ NEW: Enable storage delegation
        global_vector_db=None,  # 🔥 2025-12-20 FIX: 全局FAISS向量库用于检索Agent
        global_db_manager=None  # 🔥 2026-01-27 FIX-011: 全局DBManager确保检索一致性
    ):
        super().__init__(
            agent_id="hippocampus",
            brain_region=BrainRegion.HIPPOCAMPUS,
            system_prompt="""You are the Hippocampus agent, responsible for episodic memory storage, retrieval, and consolidation.
            You store life events, conversations, and experiences.
            You prioritize important and frequently accessed memories, and forget less important ones when capacity is reached.
            You automatically consolidate important episodic memories into semantic knowledge for long-term storage.""",
            client=client
        )

        # 🔥 Phase 3: Storage Delegation (委托存储)
        self.storage_adapter = MemoryStorageAdapter(
            memory_system=memory_system,
            agent_id=self.agent_id,
            config=StorageConfig(
                use_global_storage=use_global_storage,
                enable_local_cache=True,  # Keep cache for fast access
                sync_on_store=True
            ),
            global_vector_db=global_vector_db,  # 🔥 2025-12-20 FIX: 传递全局FAISS
            global_db_manager=global_db_manager  # 🔥 2026-01-27 FIX-011: 传递全局DBManager
        )

        # 🧠 Key-Value Memory Store Integration
        self.memory_store = memory_system if isinstance(memory_system, KeyValueMemoryStore) else None
        
        # 🧠 Hippocampal Event Graph
        self.event_graph = HippocampalEventGraph(enable_pattern_separation=True)

        # 🔥 内部记忆存储 (人一生容量)
        # Note: When use_global_storage=True, self.memories becomes a cache
        self.capacity = capacity
        self.memories: List[EpisodicMemory] = []  # ✅ Backward compatible cache

        # 🔥 索引结构 (不使用FAISS,使用简单索引)
        self.entity_index: Dict[str, List[str]] = defaultdict(list)  # {entity: [memory_ids]}
        self.time_index: Dict[str, List[str]] = defaultdict(list)    # {date: [memory_ids]}
        self.memory_dict: Dict[str, EpisodicMemory] = {}            # {id: memory}
        # 🔥 Phase 1: Event Segmentation (事件分割索引)
        self.event_index: Dict[str, List[str]] = defaultdict(list)   # {event_id: [memory_ids]}
        # 🔥 Phase 1: Entity-Action Binding (实体-动作绑定索引)
        self.entity_action_index: Dict[str, List[str]] = defaultdict(list)  # {(entity, action): [memory_ids]}
        self.current_event_id: Optional[str] = None  # 当前事件ID

        # 🔥 Embedding服务 (混合检索: keyword + semantic)
        self.embedding_service = embedding_service

        # 🧠 Plan C: 集成处理功能
        self.temporal_lobe = temporal_lobe_agent  # 用于记忆巩固
        # ❌ 移除硬编码: self.consolidation_threshold = 0.2
        # ✅ 使用动态LLM决策是否巩固

        # 🎯 P3: Knowledge Graph Builder (自动关系提取)
        self.kg_builder = kg_builder or KnowledgeGraphBuilder(llm_client=client)

        # 统计信息
        self.total_stored = 0
        self.total_forgotten = 0
        self.total_consolidated = 0

        self._shared_kg_builder = kg_builder is not None

        # 🔥 Auto-persistence setup (使用 BMAMPaths 统一路径管理)
        self.state_file = BMAMPaths.HIPPOCAMPUS_STATE
        self._load_state_from_file()

        # 🔥 NEW: Track if global sync is needed on first async operation
        self._global_sync_done = False
        self._use_global_storage = use_global_storage

        logger.info(
            f"✅ HippocampusAgent initialized (capacity={capacity}, "
            f"consolidation={'enabled' if temporal_lobe_agent else 'disabled'}, "
            f"kg_extraction={'shared' if self._shared_kg_builder else 'local'}, "
            f"storage={'delegated' if use_global_storage else 'local'})"
        )

    async def ensure_global_sync(self) -> Dict[str, Any]:
        """
        Ensure local cache is synced with global storage
        确保本地缓存与全局存储同步

        Called automatically on first async operation if global storage is enabled.
        Should also be called explicitly after program restart.

        Returns:
            Sync result from storage_adapter
        """
        if self._global_sync_done:
            return {'already_synced': True}

        if not self._use_global_storage:
            self._global_sync_done = True
            return {'global_storage_disabled': True}

        try:
            # Sync from global storage to local cache
            sync_result = await self.storage_adapter.sync_from_global(
                limit=self.capacity  # Sync up to capacity
            )

            # Rebuild local structures from synced cache
            if sync_result.get('synced_count', 0) > 0:
                await self._rebuild_from_cache()

            # Verify consistency
            consistency = await self.storage_adapter.verify_consistency()
            sync_result['consistency'] = consistency

            self._global_sync_done = True
            logger.info(f"✅ Global sync complete: {sync_result}")
            return sync_result

        except Exception as e:
            logger.error(f"❌ Global sync failed: {e}")
            self._global_sync_done = True  # Mark as done to avoid retry loop
            return {'error': str(e)}

    async def _rebuild_from_cache(self) -> None:
        """
        Rebuild local memory structures from storage adapter cache
        从存储适配器缓存重建本地记忆结构
        """
        # Clear existing local structures and rebuild atomically
        async with self._memory_write_lock:
            self.memories.clear()
            self.memory_dict.clear()
            self.entity_index.clear()
            self.time_index.clear()
            self.event_index.clear()
            self.entity_action_index.clear()

            for memory_id, memory_dict in self.storage_adapter._local_cache.items():
                memory = self._dict_to_memory(memory_dict)
                self.memories.append(memory)
                self.memory_dict[memory.id] = memory
                self._update_indexes(memory)

        logger.info(f"✅ Rebuilt {len(self.memories)} memories from global cache")

    def _dict_to_memory(self, memory_dict: Dict[str, Any]) -> EpisodicMemory:
        """Convert dict to EpisodicMemory"""
        timestamp = memory_dict.get('timestamp')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        last_accessed = memory_dict.get('last_accessed')
        if isinstance(last_accessed, str):
            last_accessed = datetime.fromisoformat(last_accessed)

        return EpisodicMemory(
            id=memory_dict.get('id'),
            content=memory_dict.get('content', ''),
            timestamp=timestamp or datetime.now(),
            entities=memory_dict.get('entities', []),
            importance=memory_dict.get('importance', 0.5),
            access_count=memory_dict.get('access_count', 0),
            last_accessed=last_accessed,
            emotion_tags=memory_dict.get('emotion_tags', []),
            emotion_intensity=memory_dict.get('emotion_intensity', 0.0),
            metadata=memory_dict.get('metadata', {}),
            embedding=memory_dict.get('embedding'),
            event_id=memory_dict.get('event_id'),
            speaker=memory_dict.get('speaker')
        )

    def _update_indexes(self, memory: EpisodicMemory) -> None:
        """Update all indexes for a memory"""
        # Entity index
        for entity in memory.entities:
            self.entity_index[entity].append(memory.id)
            entity_lower = entity.lower()
            if entity_lower != entity:
                self.entity_index[entity_lower].append(memory.id)

        # Time index
        date_key = memory.timestamp.strftime('%Y-%m-%d')
        self.time_index[date_key].append(memory.id)

        # Event index
        if memory.event_id:
            self.event_index[memory.event_id].append(memory.id)

    async def get_capacity_status_global(self) -> Dict[str, Any]:
        """
        Get capacity status based on global storage (not just local list)
        基于全局存储获取容量状态

        This fixes the issue where capacity was only checked against local list,
        which could be incomplete when using global storage delegation.
        """
        if self._use_global_storage:
            global_status = await self.storage_adapter.get_global_capacity_status()
            global_count = global_status.get('global_count', len(self.memories))
            return {
                'current': global_count,
                'local_cache': len(self.memories),
                'max': self.capacity,
                'usage_percent': (global_count / self.capacity) * 100 if self.capacity > 0 else 0,
                'source': 'global'
            }
        else:
            current = len(self.memories)
            return {
                'current': current,
                'local_cache': current,
                'max': self.capacity,
                'usage_percent': (current / self.capacity) * 100 if self.capacity > 0 else 0,
                'source': 'local'
            }

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """处理消息"""
        action = message.content.get('action')

        if action == 'store_episode':
            return await self.store_memory(
                content=message.content['content'],
                entities=message.content.get('entities', []),
                importance=message.content.get('importance', 0.5),
                emotion_tags=message.content.get('emotion_tags', []),
                emotion_intensity=message.content.get('emotion_intensity', 0.0),
                metadata=message.content.get('metadata', {})
            )

        elif action == 'search_episodes':
            return await self.search_memories(
                query=message.content.get('query'),
                entities=message.content.get('entities'),
                time_range=message.content.get('time_range'),
                k=message.content.get('k', 10)
            )

        elif action == 'get_statistics':
            return self.get_statistics()

        elif action == 'trigger_consolidation':
            return await self.consolidate_memories()

        # 🔥 Phase 1: New actions for event segmentation
        elif action == 'store_with_event_segmentation':
            return await self.store_memory_with_event_segmentation(
                content=message.content['content'],
                timestamp=message.content.get('timestamp'),
                speaker=message.content.get('speaker'),
                entities=message.content.get('entities', []),
                importance=message.content.get('importance', 0.5),
                emotion_tags=message.content.get('emotion_tags', []),
                emotion_intensity=message.content.get('emotion_intensity', 0.0),
                metadata=message.content.get('metadata', {})
            )

        elif action == 'batch_consolidate':
            return await self.batch_consolidate(
                batch_size=message.content.get('batch_size', 50),
                similarity_threshold=message.content.get('similarity_threshold', 0.7)
            )

        elif action == 'retrieve_by_timeline':
            return await self.retrieve_by_timeline(
                start_time=message.content['start_time'],
                end_time=message.content['end_time'],
                k=message.content.get('k', 50)
            )

        elif action == 'retrieve_by_event':
            return await self.retrieve_by_event(
                event_id=message.content['event_id'],
                include_context=message.content.get('include_context', True)
            )

        elif action == 'search_with_temporal_reasoning':
            return await self.search_with_temporal_reasoning(
                query=message.content['query'],
                k=message.content.get('k', 10)
            )

        elif action == 'search_with_entity_action_binding':
            return await self.search_with_entity_action_binding(
                query=message.content['query'],
                k=message.content.get('k', 10)
            )

        return {'error': f'Unknown action: {action}'}

    def export_state(self) -> Dict[str, Any]:
        """
        Export hippocampus state to JSON-serializable format for BMA archive.

        Returns:
            Dict containing all episodic memories and indices
        """
        # Serialize episodic memories
        memories_data = []
        for mem in self.memories:
            memories_data.append({
                'id': mem.id,
                'content': mem.content,
                'timestamp': mem.timestamp.isoformat() if mem.timestamp else None,
                'entities': mem.entities,
                'importance': mem.importance,
                'access_count': mem.access_count,
                'last_accessed': mem.last_accessed.isoformat() if mem.last_accessed else None,
                'emotion_tags': mem.emotion_tags,
                'emotion_intensity': mem.emotion_intensity,
                'metadata': mem.metadata,
                'embedding': mem.embedding,  # May be None
                'event_id': mem.event_id,
                'speaker': mem.speaker
            })

        # Export state
        state = {
            'format_version': '1.0.0',
            'agent_id': self.agent_id,
            'brain_region': 'hippocampus',
            'capacity': self.capacity,
            'current_event_id': self.current_event_id,
            'memories': memories_data,
            'entity_index': dict(self.entity_index),
            'time_index': dict(self.time_index),
            'event_index': dict(self.event_index),
            'entity_action_index': dict(self.entity_action_index),
            'statistics': {
                'total_stored': self.total_stored,
                'total_forgotten': self.total_forgotten,
                'total_consolidated': self.total_consolidated,
                'current_count': len(self.memories)
            }
        }

        logger.info(f"✅ Exported HippocampusAgent state: {len(memories_data)} memories")
        return state

    def load_state(self, state: Dict[str, Any]) -> bool:
        """
        Load hippocampus state from exported data.

        Args:
            state: State dictionary from export_state()

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate format
            if state.get('brain_region') != 'hippocampus':
                logger.error(f"❌ Invalid brain region: {state.get('brain_region')}")
                return False

            # Clear current state (load_state runs at init, no concurrent access)
            self.memories.clear()
            self.memory_dict.clear()
            self.entity_index.clear()
            self.time_index.clear()
            self.event_index.clear()
            self.entity_action_index.clear()

            # Restore configuration
            self.capacity = state.get('capacity', self.capacity)
            self.current_event_id = state.get('current_event_id')

            # Restore memories
            for mem_data in state.get('memories', []):
                memory = EpisodicMemory(
                    id=mem_data['id'],
                    content=mem_data['content'],
                    timestamp=datetime.fromisoformat(mem_data['timestamp']) if mem_data['timestamp'] else datetime.now(),
                    entities=mem_data.get('entities', []),
                    importance=mem_data.get('importance', 0.5),
                    access_count=mem_data.get('access_count', 0),
                    last_accessed=datetime.fromisoformat(mem_data['last_accessed']) if mem_data.get('last_accessed') else None,
                    emotion_tags=mem_data.get('emotion_tags', []),
                    emotion_intensity=mem_data.get('emotion_intensity', 0.0),
                    metadata=mem_data.get('metadata', {}),
                    embedding=mem_data.get('embedding'),
                    event_id=mem_data.get('event_id'),
                    speaker=mem_data.get('speaker')
                )
                self.memories.append(memory)
                self.memory_dict[memory.id] = memory

            # Restore indices
            self.entity_index = defaultdict(list, state.get('entity_index', {}))
            self.time_index = defaultdict(list, state.get('time_index', {}))
            self.event_index = defaultdict(list, state.get('event_index', {}))
            self.entity_action_index = defaultdict(list, state.get('entity_action_index', {}))

            # Restore statistics
            stats = state.get('statistics', {})
            self.total_stored = stats.get('total_stored', 0)
            self.total_forgotten = stats.get('total_forgotten', 0)
            self.total_consolidated = stats.get('total_consolidated', 0)

            # 🔥 2025-12-13: 同步到KV存储（如果启用）
            if self.memory_store:
                synced = 0
                for memory in self.memories:
                    try:
                        # 使用同步版本避免协程问题
                        self.memory_store.store_memory_sync(
                            memory_id=memory.id,
                            content=memory.content,
                            embedding=memory.embedding,
                            entities=memory.entities,
                            timestamp=memory.timestamp,
                            importance=memory.importance,
                            metadata=memory.metadata
                        )
                        synced += 1
                    except Exception as e:
                        logger.warning(f"Failed to sync memory {memory.id} to KV store: {e}")
                logger.info(f"🔄 Synced {synced}/{len(self.memories)} memories to KV store")

            logger.info(f"✅ Loaded HippocampusAgent state: {len(self.memories)} memories")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to load HippocampusAgent state: {e}")
            return False

    def _load_state_from_file(self):
        """Auto-load state from JSON file on startup using StorageCoordinator"""
        if not self.state_file.exists():
            logger.info(f"📂 No existing state file found at {self.state_file}, starting fresh")
            return

        try:
            # 使用存储协调器安全加载（支持自动从备份恢复）
            coordinator = get_storage_coordinator()
            state = coordinator.safe_json_load(str(self.state_file))

            if state is None:
                logger.error(f"❌ Failed to load state from {self.state_file} (file corrupted and no backup)")
                return

            success = self.load_state(state)
            if success:
                logger.info(f"✅ Auto-loaded Hippocampus state from {self.state_file}")
            else:
                logger.warning(f"⚠️  Failed to parse Hippocampus state from {self.state_file}")
        except Exception as e:
            logger.error(f"❌ Error loading Hippocampus state from {self.state_file}: {e}")

    def _save_state_to_file(self):
        """Auto-save current state to JSON file using StorageCoordinator"""
        try:
            # Ensure data directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            state = self.export_state()

            # 使用存储协调器进行安全写入（自动处理ndarray等类型）
            coordinator = get_storage_coordinator()
            success = coordinator.safe_json_dump(state, str(self.state_file), create_backup=True)

            if success:
                logger.debug(f"✅ Hippocampus state saved to {self.state_file}")
            else:
                logger.error(f"❌ Failed to save Hippocampus state to {self.state_file}")

        except Exception as e:
            logger.error(f"❌ Error saving Hippocampus state to {self.state_file}: {e}")

    async def receive_retrieval_feedback(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        接收检索/推理反馈，调低低置信度记忆的权重并记录负样本

        Args:
            feedback: {
                'confidence': float,
                'retrieved_memory_ids': [id1, id2, ...],
                ...
            }
        """
        confidence = feedback.get('confidence', 0.0)
        memory_ids = feedback.get('retrieved_memory_ids') or []

        updated = 0
        for mid in memory_ids:
            mem = self.memory_dict.get(mid)
            if not mem:
                continue

            # 记录负反馈次数，供后续巩固/遗忘使用
            negative_count = mem.metadata.get('negative_feedback_count', 0) + 1
            mem.metadata['negative_feedback_count'] = negative_count
            mem.metadata['last_feedback_time'] = datetime.now().isoformat()

            # 低置信度信号 -> 略微降低重要性，避免重复命中
            if confidence < 0.5:
                mem.importance = max(0.1, mem.importance - 0.05)

            updated += 1

        if updated:
            # 保持轻量持久化，确保反馈可追溯
            self._save_state_to_file()

        return {
            'feedback_applied': updated,
            'confidence': confidence
        }

    async def sync_to_global_vectordb(self, memory_system=None, batch_size: int = 100) -> Dict[str, Any]:
        """
        🔥 P0 FIX: 将本地历史记忆同步到全局VectorDB

        解决问题：Hippocampus从JSON加载的历史记忆没有索引到FAISS VectorDB，
        导致语义检索返回0结果。

        Uses a persistent sync ledger file to track which hippocampus memory IDs
        have already been synced, preventing duplicate vectors on restart.

        Args:
            memory_system: 全局记忆系统实例（如未提供则使用storage_adapter的）
            batch_size: 每批处理的记忆数量

        Returns:
            同步结果统计
        """
        ms = memory_system or (self.storage_adapter.memory_system if self.storage_adapter else None)
        if not ms:
            logger.warning("⚠️ No memory_system available for VectorDB sync")
            return {'error': 'no_memory_system', 'synced': 0}

        synced = 0
        skipped = 0
        failed = 0

        # Load persistent sync ledger (tracks which hippocampus IDs are already synced)
        import json as _json
        ledger_path = Path(BMAMPaths.DATA_DIR) / "memory" / "sync_ledger.json"
        synced_ids = set()
        try:
            if ledger_path.exists():
                synced_ids = set(_json.loads(ledger_path.read_text()))
                logger.info(f"📋 Loaded sync ledger: {len(synced_ids)} previously synced IDs")
        except Exception as e:
            logger.warning(f"Failed to load sync ledger: {e}")

        logger.info(f"🔄 Starting VectorDB sync: {len(self.memories)} local memories, {len(synced_ids)} already synced")

        # 分批处理
        memories_to_sync = [m for m in self.memories if m.id not in synced_ids]
        total_to_sync = len(memories_to_sync)

        if total_to_sync == 0:
            logger.info("✅ All memories already synced to VectorDB")
            return {'synced': 0, 'skipped': len(self.memories), 'total': len(self.memories)}

        for i in range(0, total_to_sync, batch_size):
            batch = memories_to_sync[i:i + batch_size]

            for memory in batch:
                try:
                    # 准备记忆数据
                    memory_dict = {
                        'id': memory.id,
                        'content': memory.content,
                        'timestamp': memory.timestamp,
                        'entities': memory.entities,
                        'importance': memory.importance,
                        'emotion_tags': memory.emotion_tags,
                        'emotion_intensity': memory.emotion_intensity,
                        'metadata': memory.metadata,
                        'event_id': memory.event_id,
                        'speaker': memory.speaker,
                        'embedding': memory.embedding  # 可能为None，需要重新生成
                    }

                    # 存储到全局系统（会自动生成embedding并索引到FAISS）
                    # _skip_index_save=True: defer FAISS save to batch boundary
                    result_id = await ms.store_memory(
                        content=memory.content,
                        memory_type="episodic",
                        importance=memory.importance,
                        emotion_tags=memory.emotion_tags,
                        context_tags=["hippocampus"],
                        metadata={
                            **memory.metadata,
                            'original_id': memory.id,
                            'entities': memory.entities,
                            'event_id': memory.event_id,
                            'speaker': memory.speaker,
                            'timestamp': memory.timestamp.isoformat() if memory.timestamp else None
                        },
                        embedding=memory.embedding,
                        _skip_index_save=True
                    )

                    if result_id:
                        synced += 1
                        synced_ids.add(memory.id)
                    else:
                        failed += 1

                except Exception as e:
                    logger.warning(f"Failed to sync memory {memory.id}: {e}")
                    failed += 1

            # 每批次后保存索引 + 更新ledger
            if hasattr(ms, 'vector_db'):
                ms.vector_db.save_index()
            try:
                ledger_path.parent.mkdir(parents=True, exist_ok=True)
                ledger_path.write_text(_json.dumps(list(synced_ids)))
            except Exception as e:
                logger.warning(f"Failed to save sync ledger: {e}")

            logger.info(f"📊 VectorDB sync progress: {synced}/{total_to_sync} synced, {failed} failed")

        skipped = len(self.memories) - total_to_sync

        logger.info(
            f"✅ VectorDB sync complete: synced={synced}, skipped={skipped}, failed={failed}, "
            f"VectorDB total={ms.vector_db.index.ntotal if hasattr(ms, 'vector_db') else 'N/A'}"
        )

        return {
            'synced': synced,
            'skipped': skipped,
            'failed': failed,
            'total': len(self.memories),
            'vectordb_total': ms.vector_db.index.ntotal if hasattr(ms, 'vector_db') else 0
        }

    async def apply_emotional_modulation(
        self,
        memory_id: str,
        importance_boost: float,
        emotion_tags: Optional[List[str]] = None,
        emotion_intensity: float = 0.0
    ) -> Dict[str, Any]:
        """
        由杏仁核调用：把情绪调节结果落地到海马体记忆
        """
        mem = self.memory_dict.get(memory_id)
        if not mem:
            return {'modulated': False, 'reason': 'memory_not_found'}

        # 提升重要性并记录情绪历史
        old_importance = mem.importance
        mem.importance = min(1.0, mem.importance + importance_boost)
        mem.metadata.setdefault('emotion_modulations', []).append({
            'boost': importance_boost,
            'emotion_tags': emotion_tags or [],
            'emotion_intensity': emotion_intensity,
            'timestamp': datetime.now().isoformat()
        })

        # 高情绪强度时优先巩固
        consolidated = False
        if emotion_intensity >= 0.7 and self.temporal_lobe:
            try:
                await self._consolidate_to_temporal_lobe(mem)
                consolidated = True
            except Exception as e:
                logger.warning(f"Failed to consolidate after emotional modulation: {e}")

        self._save_state_to_file()

        return {
            'modulated': True,
            'old_importance': old_importance,
            'new_importance': mem.importance,
            'consolidated': consolidated
        }
