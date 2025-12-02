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
        use_global_storage: bool = False  # ✅ NEW: Enable storage delegation
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
            )
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

        # 🔥 Auto-persistence setup
        self.state_file = Path("data/hippocampus_state.json")
        self._load_state_from_file()

        logger.info(
            f"✅ HippocampusAgent initialized (capacity={capacity}, "
            f"consolidation={'enabled' if temporal_lobe_agent else 'disabled'}, "
            f"kg_extraction={'shared' if self._shared_kg_builder else 'local'}, "
            f"storage={'delegated' if use_global_storage else 'local'})"
        )

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

            # Clear current state
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

            logger.info(f"✅ Loaded HippocampusAgent state: {len(self.memories)} memories")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to load HippocampusAgent state: {e}")
            return False

    def _load_state_from_file(self):
        """Auto-load state from JSON file on startup"""
        if not self.state_file.exists():
            logger.info(f"📂 No existing state file found at {self.state_file}, starting fresh")
            return

        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                success = self.load_state(state)
                if success:
                    logger.info(f"✅ Auto-loaded Hippocampus state from {self.state_file}")
                else:
                    logger.warning(f"⚠️  Failed to load Hippocampus state from {self.state_file}")
        except Exception as e:
            logger.error(f"❌ Error loading Hippocampus state from {self.state_file}: {e}")

    def _save_state_to_file(self):
        """Auto-save current state to JSON file"""
        try:
            # Ensure data directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            state = self.export_state()
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            logger.error(f"❌ Error saving Hippocampus state to {self.state_file}: {e}")

