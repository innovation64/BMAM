"""
Temporal Lobe Agent - 颞叶智能体
对应脑区: 颞叶 (Temporal Lobe)
主要功能: 语义记忆存储 + 知识图谱

核心设计:
1. 内部存储70,000条语义记忆 (人一生知识容量)
   - 50,000条语义记忆 (概念、知识)
   - 20,000条常识记忆
2. 知识图谱 (KG) 用于结构化知识
3. BM25索引用于关键词搜索
4. 慢遗忘机制 (知识长期保留)
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict

from ...base import BrainAgent, AgentMessage, BrainRegion
from ....utils.knowledge_graph_builder import KnowledgeGraphBuilder

from .data_models import SemanticMemory, MemoryType
from .knowledge_graph import SimpleKnowledgeGraph
from .storage import StorageMixin
from .extractors import ExtractorsMixin
from .search import SearchMixin
from .kg_operations import KGOperationsMixin
from .index_management import IndexManagementMixin
from .tracing import TracingMixin

logger = logging.getLogger(__name__)


class TemporalLobeAgent(
    StorageMixin,
    ExtractorsMixin,
    SearchMixin,
    KGOperationsMixin,
    IndexManagementMixin,
    TracingMixin,
    BrainAgent
):
    """
    颞叶智能体 - 语义记忆 + 知识图谱

    容量: 70,000条语义记忆
    - 50,000 语义记忆 (概念、知识)
    - 20,000 常识记忆
    存储格式: List + BM25 + KG
    遗忘机制: 慢遗忘 (知识长期保留,基于consolidation_level)
    """

    def __init__(
        self,
        capacity: int = 70000,
        client=None,
        embedding_service=None,
        knowledge_graph_builder: Optional[KnowledgeGraphBuilder] = None
    ):
        super().__init__(
            agent_id="temporal_lobe",
            brain_region=BrainRegion.NEOCORTEX,  # 使用NEOCORTEX作为脑区
            system_prompt="""You are the Temporal Lobe agent, responsible for semantic memory and knowledge organization.
            You store concepts, knowledge, common sense, and maintain a knowledge graph.
            You consolidate information from episodic memories into structured knowledge.""",
            client=client
        )

        # 🔥 内部记忆存储 (人一生知识容量)
        self.capacity = capacity
        self.memories: List[SemanticMemory] = []
        self.memory_dict: Dict[str, SemanticMemory] = {}

        # 🔥 知识图谱
        self.kg = SimpleKnowledgeGraph()
        self.kg_builder = knowledge_graph_builder

        # 🔥 BM25索引 (简化版: 倒排索引)
        self.inverted_index: Dict[str, List[str]] = defaultdict(list)  # {word: [memory_ids]}

        # 🔥 优先级2: Embedding服务用于语义相似度融合
        self.embedding_service = embedding_service

        # 统计信息
        self.total_stored = 0
        self.total_forgotten = 0

        logger.info(
            f"✅ TemporalLobeAgent initialized (capacity={capacity}, embedding_enabled={embedding_service is not None}, "
            f"kg_shared={'yes' if knowledge_graph_builder else 'no'})"
        )

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """处理消息"""
        action = message.content.get('action')

        if action == 'store_semantic':
            return await self.store_memory(
                content=message.content['content'],
                memory_subtype=message.content.get('memory_subtype', 'semantic'),
                entities=message.content.get('entities', []),
                relations=message.content.get('relations', []),
                importance=message.content.get('importance', 0.5),
                metadata=message.content.get('metadata', {}),
                event_time=message.content.get('event_time')  # 🔥 NEW
            )

        elif action == 'search_semantic':
            return await self.search_memories(
                query=message.content.get('query'),
                memory_subtype=message.content.get('memory_subtype'),
                k=message.content.get('k', 10)
            )

        elif action == 'query_kg':
            return self.query_knowledge_graph(
                entity=message.content.get('entity'),
                relation=message.content.get('relation')
            )

        elif action == 'multi_hop_reasoning':
            return self.multi_hop_reasoning(
                start_entity=message.content['start_entity'],
                max_depth=message.content.get('max_depth', 2)
            )

        elif action == 'get_statistics':
            return self.get_statistics()

        return {'error': f'Unknown action: {action}'}

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        kg_stats = self.kg.get_statistics()

        return {
            'agent_id': self.agent_id,
            'brain_region': self.brain_region,
            'capacity': self.capacity,
            'current_memories': len(self.memories),
            'usage_percent': self._get_capacity_status()['usage_percent'],
            'total_stored': self.total_stored,
            'total_forgotten': self.total_forgotten,
            'knowledge_graph': kg_stats,
            'index_size': len(self.inverted_index)
        }

    def _memory_to_dict(self, memory: SemanticMemory) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': memory.id,
            'content': memory.content,
            'memory_subtype': memory.memory_subtype,
            'timestamp': memory.timestamp.isoformat(),
            'entities': memory.entities,
            'relations': memory.relations,
            'importance': memory.importance,
            'access_count': memory.access_count,
            'last_accessed': memory.last_accessed.isoformat() if memory.last_accessed else None,
            'consolidation_level': memory.consolidation_level,
            'metadata': memory.metadata,
            # 🔥 优先级2修复: 回传embedding缓存以供hybrid路径使用
            'embedding': memory.embedding if memory.embedding else None,
            # 🔥 阶段1: 返回memory_type用于类型感知检索
            'memory_type': memory.memory_type.value if memory.memory_type else None
        }
