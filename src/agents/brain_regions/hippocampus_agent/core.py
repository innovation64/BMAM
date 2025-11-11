"""
Hippocampus Agent - 海马体智能体
对应脑区: 海马体 (Hippocampus)
主要功能: 情节记忆存储+检索+巩固
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)


from ...base import BrainAgent, AgentMessage, BrainRegion
from ....utils.knowledge_graph_builder import KnowledgeGraphBuilder
from ....memory.storage_adapter import MemoryStorageAdapter, StorageConfig


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

