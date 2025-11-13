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


from .core import EpisodicMemory, HippocampusAgentCore

import asyncio


class StorageMixin:
    """存储和索引管理功能"""
    async def store_memory(
        self,
        content: str,
        entities: List[str] = None,
        importance: float = 0.5,
        emotion_tags: List[str] = None,
        emotion_intensity: float = 0.0,
        metadata: Dict[str, Any] = None,
        auto_extract_kg: bool = True  # 🎯 P3: 自动提取KG关系
    ) -> Dict[str, Any]:
        """
        存储情节记忆

        Args:
            content: 记忆内容
            entities: 相关实体 (人名、地点等) - 如果None且auto_extract_kg=True，会自动提取
            importance: 重要性 (0.0-1.0)
            emotion_tags: 情绪标签
            emotion_intensity: 情绪强度
            metadata: 元数据
            auto_extract_kg: 是否自动提取实体和关系 (P3优化)

        Returns:
            {
                'memory_id': str,
                'stored': bool,
                'entities_extracted': List[str],
                'relations_extracted': List[Dict],
                'capacity_status': {...}
            }
        """

        # 🎯 P3优化: 自动提取实体和关系
        extracted_entities: List[str] = []
        extracted_relations: List[Dict[str, Any]] = []
        kg_entity_payload: List[Dict[str, Any]] = []

        if auto_extract_kg:
            try:
                # 使用 KG Builder 自动提取
                kg_context = {}
                if metadata and isinstance(metadata, dict):
                    kg_context = metadata

                entities_list, relations_list = await self.kg_builder.extract_from_text(
                    text=content,
                    use_llm=True,  # 使用LLM获得更准确的结果
                    context=kg_context
                )

                # 提取实体名称
                kg_entity_payload = entities_list or []
                extracted_entities = [
                    e.get('name', e) if isinstance(e, dict) else e
                    for e in kg_entity_payload
                ]

                # 保存关系到metadata
                extracted_relations = relations_list


            except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                logger.warning(f"Failed to auto-extract KG: {e}")
                extracted_entities = []
                extracted_relations = []
                kg_entity_payload = []

        # 合并手动传入的entities和自动提取的entities
        final_entities = list(set((entities or []) + extracted_entities))

        # 创建记忆项
        memory = EpisodicMemory(
            id=uuid.uuid4().hex,
            content=content,
            timestamp=datetime.now(),
            entities=final_entities,
            importance=importance,
            emotion_tags=emotion_tags or [],
            emotion_intensity=emotion_intensity,
            metadata=metadata or {}
        )

        # 🎯 P3优化: 保存提取的关系到metadata
        if extracted_relations:
            memory.metadata['kg_relations'] = extracted_relations
            memory.metadata['kg_auto_extracted'] = True
        elif metadata and metadata.get('kg_relations'):
            extracted_relations = metadata.get('kg_relations', [])

        if kg_entity_payload:
            memory.metadata['kg_entities'] = [
                e.get('name') if isinstance(e, dict) else str(e)
                for e in kg_entity_payload
            ]

        # 🔥 计算embedding (混合检索)
        if self.embedding_service:
            try:
                embedding = await self.embedding_service.encode_text(content)
                memory.embedding = embedding.tolist() if hasattr(embedding, 'tolist') else embedding
            except (RuntimeError, ValueError) as e:
                logger.warning(f"Failed to compute embedding: {e}")
                memory.embedding = None

        # 🔥 Phase 3: Delegate to storage adapter
        memory_dict = self._memory_to_dict(memory)
        storage_result = await self.storage_adapter.store_memory(memory_dict)

        # 存储到本地列表/缓存 (for backward compatibility)
        self.memories.append(memory)
        self.memory_dict[memory.id] = memory

        # 更新索引
        self._update_indexes(memory)

        # 容量控制
        if len(self.memories) > self.capacity:
            await self._trigger_forgetting()

        self.total_stored += 1

        # Log delegation status
        if storage_result.get('storage_location') == 'global':
            logger.debug(
                f"Memory {memory.id} delegated to global storage "
                f"(cached={storage_result.get('cached')})"
            )

        # 🧠 Plan C: 自动巩固重要记忆 - 使用LLM动态决策
        should_consolidate = False
        if self.temporal_lobe:
            should_consolidate = await self._should_consolidate_memory(memory)
            if should_consolidate:
                await self._consolidate_to_temporal_lobe(memory)

        # 🎯 P3: 日志显示提取的信息
        if extracted_entities or extracted_relations:
            logger.info(f"Extracted {len(extracted_entities)} entities, {len(extracted_relations)} relations")
        else:
            pass

        await self._update_knowledge_graph(memory, kg_entity_payload, extracted_relations)

        # 🔥 Auto-persist to JSON file
        self._save_state_to_file()

        return {
            'memory_id': memory.id,
            'stored': True,
            'entities_extracted': final_entities,  # 🎯 P3: 返回提取的实体
            'relations_extracted': extracted_relations,  # 🎯 P3: 返回提取的关系
            'capacity_status': self._get_capacity_status(),
            'consolidated': should_consolidate
        }


    async def _update_knowledge_graph(
        self,
        memory: EpisodicMemory,
        entity_payload: Optional[List[Dict[str, Any]]],
        relations_payload: Optional[List[Dict[str, Any]]]
    ) -> None:
        """同步海马体提取的KG信号到共享知识图谱和颞叶"""
        builder_entities: List[Dict[str, Any]] = entity_payload or []
        builder_relations: List[Dict[str, Any]] = relations_payload or []

        if not builder_entities and memory.entities:
            builder_entities = [
                {'name': name, 'type': 'Unknown', 'mentions': 1}
                for name in memory.entities
            ]

        if not builder_relations:
            builder_relations = memory.metadata.get('kg_relations', []) or []

        if self.kg_builder and (builder_entities or builder_relations):
            try:
                self.kg_builder.add_to_graph(builder_entities, builder_relations)
            except (Exception) as e:
                logger.warning(f"Failed to update shared knowledge graph: {e}")

        if builder_relations and self.temporal_lobe and hasattr(self.temporal_lobe, 'ingest_kg_relations'):
            try:
                await self.temporal_lobe.ingest_kg_relations(
                    builder_relations,
                    source_memory_id=memory.id,
                    source_region=self.brain_region if hasattr(self, 'brain_region') else 'hippocampus'
                )
            except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                logger.warning(f"Failed to propagate KG relations to temporal lobe: {e}")


    def _update_indexes(self, memory: EpisodicMemory):
        """更新索引"""
        # 实体索引
        for entity in memory.entities:
            self.entity_index[entity].append(memory.id)

        # 时间索引
        date_key = memory.timestamp.strftime('%Y-%m-%d')
        self.time_index[date_key].append(memory.id)

        # 🔥 Phase 1: 事件索引
        if memory.event_id:
            self.event_index[memory.event_id].append(memory.id)

        # 🔥 Phase 1: 实体-动作绑定索引 (异步构建,存储时先不提取)
        # 动作提取在检索时进行,避免存储时的LLM开销


    def _rebuild_indexes(self):
        """重建所有索引"""
        self.entity_index.clear()
        self.time_index.clear()

        for mem in self.memories:
            self._update_indexes(mem)


    def _get_capacity_status(self) -> Dict[str, Any]:
        """获取容量状态"""
        current = len(self.memories)
        return {
            'current': current,
            'max': self.capacity,
            'usage_percent': (current / self.capacity) * 100 if self.capacity > 0 else 0
        }


    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'agent_id': self.agent_id,
            'brain_region': self.brain_region,
            'capacity': self.capacity,
            'current_memories': len(self.memories),
            'usage_percent': self._get_capacity_status()['usage_percent'],
            'total_stored': self.total_stored,
            'total_forgotten': self.total_forgotten,
            'total_consolidated': self.total_consolidated,
            'consolidation_enabled': self.temporal_lobe is not None,
            'indexes': {
                'entities': len(self.entity_index),
                'dates': len(self.time_index)
            }
        }


    def _memory_to_dict(self, memory: EpisodicMemory) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': memory.id,
            'content': memory.content,
            'timestamp': memory.timestamp.isoformat(),
            'entities': memory.entities,
            'importance': memory.importance,
            'access_count': memory.access_count,
            'last_accessed': memory.last_accessed.isoformat() if memory.last_accessed else None,
            'emotion_tags': memory.emotion_tags,
            'emotion_intensity': memory.emotion_intensity,
            'metadata': memory.metadata,
            'event_id': memory.event_id,
            'speaker': memory.speaker
        }

    def _dict_to_memory(self, memory_dict: Dict[str, Any]) -> EpisodicMemory:
        """
        从字典格式转换为EpisodicMemory对象
        Convert dictionary format to EpisodicMemory object

        Used when retrieving memories from global storage adapter.
        """
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

    # ============================================================================
    # Phase 1: Event Segmentation & Timeline Retrieval (事件分割与时间线检索)
    # ============================================================================


    async def store_memory_with_event_segmentation(
        self,
        content: str,
        timestamp: datetime = None,
        speaker: str = None,
        entities: List[str] = None,
        importance: float = 0.5,
        emotion_tags: List[str] = None,
        emotion_intensity: float = 0.0,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        带事件分割的记忆存储 (Phase 1核心功能)

        人脑的事件分割机制: 海马体会自动检测事件边界
        - 主题切换 (topic shift)
        - 时间跳跃 (time gap > 1 hour)
        - 说话人改变 (speaker change in dialogue)
        - 情绪变化 (emotion shift)

        Args:
            content: 记忆内容
            timestamp: 时间戳 (None则使用当前时间)
            speaker: 说话人 (对话场景)
            entities: 相关实体
            importance: 重要性
            emotion_tags: 情绪标签
            emotion_intensity: 情绪强度
            metadata: 元数据

        Returns:
            {
                'memory_id': str,
                'event_id': str,
                'is_new_event': bool,
                'event_boundary_reason': str
            }
        """

        if timestamp is None:
            timestamp = datetime.now()
        elif isinstance(timestamp, str):
            # 🔥 如果传入的是字符串，转换为datetime
            timestamp = datetime.fromisoformat(timestamp)

        # 🧠 检测事件边界
        is_new_event, boundary_reason = await self._detect_event_boundary(
            content=content,
            timestamp=timestamp,
            speaker=speaker,
            emotion_tags=emotion_tags or [],
            recent_memories=self.memories[-5:] if len(self.memories) > 0 else []
        )

        # 🔥 如果是新事件,创建新的event_id
        if is_new_event or self.current_event_id is None:
            self.current_event_id = f"event_{timestamp.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        # 创建记忆项
        memory = EpisodicMemory(
            id=uuid.uuid4().hex,
            content=content,
            timestamp=timestamp,
            entities=entities or [],
            importance=importance,
            emotion_tags=emotion_tags or [],
            emotion_intensity=emotion_intensity,
            metadata=metadata or {},
            event_id=self.current_event_id,  # 🔥 关联事件ID
            speaker=speaker  # 🔥 记录说话人
        )

        # 🔥 计算embedding
        if self.embedding_service:
            try:
                embedding = await self.embedding_service.encode_text(content)
                memory.embedding = embedding.tolist() if hasattr(embedding, 'tolist') else embedding
            except (RuntimeError, ValueError) as e:
                logger.warning(f"Failed to compute embedding: {e}")
                memory.embedding = None

        # 🔥 Phase 3: Delegate to storage adapter
        memory_dict = self._memory_to_dict(memory)
        storage_result = await self.storage_adapter.store_memory(memory_dict)

        # 存储到本地列表/缓存 (for backward compatibility)
        self.memories.append(memory)
        self.memory_dict[memory.id] = memory

        # 更新所有索引 (包括event_index)
        self._update_indexes(memory)

        # 容量控制
        if len(self.memories) > self.capacity:
            await self._trigger_forgetting()

        self.total_stored += 1

        # Log delegation status
        if storage_result.get('storage_location') == 'global':
            logger.debug(
                f"Event memory {memory.id} (event={self.current_event_id}) "
                f"delegated to global storage"
            )

        # 自动巩固重要记忆 - 使用LLM动态决策
        if self.temporal_lobe:
            should_consolidate = await self._should_consolidate_memory(memory)
            if should_consolidate:
                await self._consolidate_to_temporal_lobe(memory)

        await self._update_knowledge_graph(memory, None, None)

        # 🔥 Auto-persist to JSON file
        self._save_state_to_file()

        return {
            'memory_id': memory.id,
            'event_id': self.current_event_id,
            'is_new_event': is_new_event,
            'event_boundary_reason': boundary_reason,
            'stored': True,
            'capacity_status': self._get_capacity_status()
        }


