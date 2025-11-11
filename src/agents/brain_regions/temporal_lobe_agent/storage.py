"""
Storage operations for Temporal Lobe Agent
存储操作模块
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set

from .data_models import SemanticMemory, MemoryType

logger = logging.getLogger(__name__)


class StorageMixin:
    """Storage operations mixin for TemporalLobeAgent"""

    async def store_memory(
        self,
        content: str,
        memory_subtype: str = 'semantic',
        entities: List[str] = None,
        relations: List[Tuple[str, str, str]] = None,
        importance: float = 0.5,
        metadata: Dict[str, Any] = None,
        event_time: datetime = None,  # 🔥 NEW: 事件发生时间
        memory_type: Optional[MemoryType] = None  # 🔥 阶段1: 记忆类型
    ) -> Dict[str, Any]:
        """
        存储语义记忆

        Args:
            content: 记忆内容
            memory_subtype: 'semantic' or 'common_sense'
            entities: 相关实体
            relations: 关系三元组 [(source, relation, target)]
            importance: 重要性
            metadata: 元数据
            event_time: 事件发生时间 (None = 使用当前时间)
            memory_type: 记忆类型 (FACTUAL/RELATIONAL/TEMPORAL/PROCEDURAL/SUMMARY)

        Returns:
            {'memory_id': str, 'stored': bool, 'kg_updated': bool}
        """

        # 🔥 如果是字符串，转换为datetime
        if isinstance(event_time, str):
            event_time = datetime.fromisoformat(event_time)

        # 🔥 优先级2: 计算并缓存embedding（如果embedding_service可用）
        embedding = None
        if self.embedding_service:
            try:
                embedding_result = await self.embedding_service.encode_text(content)
                # 转换为list（避免numpy序列化问题）
                if hasattr(embedding_result, 'tolist'):
                    embedding = embedding_result.tolist()
                else:
                    embedding = embedding_result
            except (RuntimeError, ValueError) as e:
                logger.warning(f"Failed to compute embedding for memory: {e}")

        # 创建记忆项
        memory = SemanticMemory(
            id=uuid.uuid4().hex,
            content=content,
            memory_subtype=memory_subtype,
            timestamp=datetime.now(),  # 学习时间
            entities=entities or [],
            relations=relations or [],
            importance=importance,
            metadata=metadata or {},
            event_time=event_time,  # 🔥 事件时间
            embedding=embedding,  # 🔥 优先级2: 缓存embedding
            memory_type=memory_type  # 🔥 阶段1: 记忆类型
        )

        # 存储到列表
        self.memories.append(memory)
        self.memory_dict[memory.id] = memory

        # 更新BM25索引
        self._update_bm25_index(memory)

        # 🔥 更新知识图谱
        kg_updated = False
        for (source, relation, target) in memory.relations:
            self.kg.add_triple(source, relation, target)
            kg_updated = True

        if self.kg_builder and (memory.entities or memory.relations):
            try:
                builder_entities = [
                    {'name': name, 'type': 'Unknown', 'mentions': 1}
                    for name in memory.entities
                ]
                builder_relations = [
                    {'source': source, 'relation': relation, 'target': target}
                    for (source, relation, target) in memory.relations
                ]
                self.kg_builder.add_to_graph(builder_entities, builder_relations)
            except (Exception) as e:
                logger.warning(f"Failed to sync semantic memory into shared KG: {e}")

        # 容量控制
        if len(self.memories) > self.capacity:
            await self._trigger_forgetting()

        self.total_stored += 1

        return {
            'memory_id': memory.id,
            'stored': True,
            'kg_updated': kg_updated,
            'capacity_status': self._get_capacity_status()
        }

    async def ingest_kg_relations(
        self,
        relations: List[Dict[str, Any]],
        source_memory_id: Optional[str] = None,
        source_region: str = 'hippocampus',
        sync_builder: bool = False
    ) -> Dict[str, Any]:
        """
        接收来自其他脑区的知识图谱关系 (例如海马体自动抽取)
        并更新颞叶内部的知识图谱
        """
        if not relations:
            return {'triples_added': 0, 'source_memory_id': source_memory_id}

        triples_added = 0
        entity_names: Set[str] = set()

        for rel in relations:
            source = rel.get('source')
            relation = rel.get('relation')
            target = rel.get('target')

            if not (source and relation and target):
                continue

            self.kg.add_triple(source, relation, target)
            triples_added += 1
            entity_names.add(source)
            entity_names.add(target)

        if triples_added:
            logger.info(
                f"🔗 Ingested {triples_added} KG relations from {source_region} "
                f"(memory={source_memory_id[:8] if source_memory_id else 'unknown'})"
            )

        if sync_builder and self.kg_builder and triples_added:
            try:
                builder_entities = [
                    {'name': name, 'type': 'Unknown', 'mentions': 1}
                    for name in entity_names
                    if name
                ]
                self.kg_builder.add_to_graph(builder_entities, relations)
            except (Exception) as e:
                logger.warning(f"Failed to sync relations to shared KG builder: {e}")

        return {
            'triples_added': triples_added,
            'source_memory_id': source_memory_id
        }
