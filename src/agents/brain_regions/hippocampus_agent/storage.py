"""
Hippocampus Agent - 海马体智能体
对应脑区: 海马体 (Hippocampus)
主要功能: 情节记忆存储+检索+巩固

🔥 2025-12-05 优化: 事件时间提取
- 使用 FlexibleDateParser 从内容中提取事件发生时间
- 区分 storage_time (存储时间) 和 event_time (事件时间)
- 支持相对日期解析 (yesterday, last week 等)
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
import uuid
import numpy as np

logger = logging.getLogger(__name__)


from .core import EpisodicMemory, HippocampusAgentCore
from ....utils.flexible_date_parser import FlexibleDateParser, get_global_parser

import asyncio


# 全局日期解析器实例
_date_parser: Optional[FlexibleDateParser] = None


def get_date_parser() -> FlexibleDateParser:
    """获取日期解析器单例"""
    global _date_parser
    if _date_parser is None:
        _date_parser = get_global_parser()
    return _date_parser


def extract_event_time_from_content(
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    fallback_time: Optional[datetime] = None
) -> tuple[Optional[datetime], str]:
    """
    从内容中提取事件发生时间

    🔥 核心优化: 解决 temporal 类别准确率低的问题

    Args:
        content: 记忆内容文本
        metadata: 元数据 (可能包含 conversation_date)
        fallback_time: 如果无法提取，使用的默认时间

    Returns:
        (event_time, extraction_method)
        - event_time: 提取的事件时间，或 None
        - extraction_method: 提取方法 ('relative', 'absolute', 'metadata', 'fallback')

    Examples:
        "[Context: This conversation is on 08 May 2023] Yesterday, I went to the museum"
        → (2023-05-07, 'relative')

        "On May 7, 2023, I visited the park"
        → (2023-05-07, 'absolute')
    """
    import re
    parser = get_date_parser()

    # 1. 🔥 首先从 content 中提取 [Context: This conversation is on DATE] 格式
    reference_date = None
    context_pattern = r'\[Context:.*?(?:conversation is on|conversation on|date is)\s*([^\]]+)\]'
    context_match = re.search(context_pattern, content, re.IGNORECASE)
    if context_match:
        context_date_str = context_match.group(1).strip()
        # 尝试解析 "08 May 2023" 格式
        reference_date = parser.parse_possible_date(context_date_str)
        if reference_date:
            logger.debug(f"Extracted conversation_date from content: {reference_date}")

    # 2. 如果 content 中没找到，尝试从 metadata 获取
    if not reference_date and metadata:
        conv_date = metadata.get('conversation_date') or metadata.get('context_date')
        if conv_date:
            if isinstance(conv_date, str):
                try:
                    reference_date = datetime.fromisoformat(conv_date.replace('Z', '+00:00'))
                except ValueError:
                    reference_date = parser.parse_possible_date(conv_date)
            elif isinstance(conv_date, datetime):
                reference_date = conv_date

    # 3. 去掉 [Context: ...] 部分，只分析实际内容
    content_without_context = re.sub(r'\[Context:[^\]]*\]', '', content).strip()

    # 4. 尝试用 FlexibleDateParser 解析相对时间 (利用 dateparser 库，非硬编码)
    if reference_date:
        # FlexibleDateParser 内部使用 dateparser 库来智能解析相对时间
        relative_result = parser.parse_possible_date(content_without_context, reference_date=reference_date)
        if relative_result and relative_result != reference_date:
            return relative_result, 'relative'

    # 5. 尝试从 content 中提取绝对日期 (如 "May 7, 2023")
    absolute_dates = parser.extract_all_dates(content_without_context, reference_date=reference_date or datetime.now())
    if absolute_dates:
        return absolute_dates[0], 'absolute'

    # 6. 如果 metadata 中直接有 event_time
    if metadata and metadata.get('event_time'):
        event_time = metadata['event_time']
        if isinstance(event_time, str):
            try:
                return datetime.fromisoformat(event_time), 'metadata'
            except ValueError:
                pass
        elif isinstance(event_time, datetime):
            return event_time, 'metadata'

    # 7. 使用 reference_date 作为默认事件时间
    if reference_date:
        return reference_date, 'context'

    return fallback_time, 'fallback'


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

        # 🎯 P3优化: 自动提取实体和关系 (带降级机制)
        extracted_entities: List[str] = []
        extracted_relations: List[Dict[str, Any]] = []
        kg_entity_payload: List[Dict[str, Any]] = []

        if auto_extract_kg:
            kg_context = {}
            if metadata and isinstance(metadata, dict):
                kg_context = metadata

            # 🔥 FIX 2025-12-05: 三级降级机制 (LLM → 规则 → 强制)
            try:
                # Level 1: 尝试LLM提取
                entities_list, relations_list = await self.kg_builder.extract_from_text(
                    text=content,
                    use_llm=True,
                    context=kg_context
                )
                kg_entity_payload = entities_list or []
                extracted_entities = [
                    e.get('name', e) if isinstance(e, dict) else e
                    for e in kg_entity_payload
                ]
                extracted_relations = relations_list or []
                logger.debug(f"✅ KG extracted via LLM: {len(extracted_entities)} entities")

            except Exception as llm_error:
                logger.warning(f"⚠️ LLM extraction failed: {llm_error}, trying rules fallback")
                try:
                    # Level 2: 降级到规则提取
                    entities_list, relations_list = await self.kg_builder.extract_from_text(
                        text=content,
                        use_llm=False,  # 禁用LLM，只用规则
                        context=kg_context
                    )
                    kg_entity_payload = entities_list or []
                    extracted_entities = [
                        e.get('name', e) if isinstance(e, dict) else e
                        for e in kg_entity_payload
                    ]
                    extracted_relations = relations_list or []
                    logger.debug(f"✅ KG extracted via rules: {len(extracted_entities)} entities")

                except Exception as rule_error:
                    logger.warning(f"⚠️ Rule extraction failed: {rule_error}, using forced extraction")
                    # Level 3: 强制提取 (从speaker和基本pattern)
                    extracted_entities = []
                    extracted_relations = []
                    kg_entity_payload = []

            # 🔥 Level 3 fallback: 如果提取结果为空，强制从内容提取
            if not extracted_entities:
                # 从metadata提取speaker
                if metadata and metadata.get('speaker'):
                    speaker = metadata['speaker']
                    if speaker and speaker.strip():
                        extracted_entities.append(speaker.strip())
                        kg_entity_payload.append({'name': speaker.strip(), 'type': 'Person'})

                # 基本正则提取人名 (大写开头的词)
                import re
                words = content.split()
                for word in words:
                    clean = re.sub(r'[^\w]', '', word)
                    if clean and clean[0].isupper() and len(clean) > 1 and clean.lower() not in {
                        'i', 'the', 'a', 'an', 'my', 'your', 'he', 'she', 'it', 'we', 'they',
                        'this', 'that', 'what', 'when', 'where', 'why', 'how', 'yes', 'no',
                        'oh', 'okay', 'sure', 'well', 'just', 'really', 'actually', 'maybe'
                    }:
                        if clean not in extracted_entities:
                            extracted_entities.append(clean)
                            kg_entity_payload.append({'name': clean, 'type': 'Unknown'})

                if extracted_entities:
                    logger.debug(f"✅ KG forced extraction: {len(extracted_entities)} entities")

        # 合并手动传入的entities和自动提取的entities
        final_entities = list(set((entities or []) + extracted_entities))

        # 🔥 2025-12-05: 提取事件发生时间 (解决 temporal 准确率问题)
        storage_time = datetime.now()
        event_time, extraction_method = extract_event_time_from_content(
            content=content,
            metadata=metadata,
            fallback_time=storage_time
        )

        # 更新 metadata 记录事件时间
        # 🔥 2025-12-14 FIX v2: 分层处理不同提取方法 (与 store_memory_with_event_segmentation 保持一致)
        final_metadata = metadata.copy() if metadata else {}
        HIGH_CONFIDENCE_METHODS = ('relative', 'absolute', 'explicit', 'metadata')
        LOW_CONFIDENCE_METHODS = ('context',)

        if event_time and extraction_method in HIGH_CONFIDENCE_METHODS:
            # 高置信度: 明确提取的时间
            final_metadata['event_time'] = event_time.isoformat()
            final_metadata['event_time_extraction'] = extraction_method
            final_metadata['event_time_confidence'] = 'high'
            logger.debug(f"Extracted event_time: {event_time} ({extraction_method})")
        elif event_time and extraction_method in LOW_CONFIDENCE_METHODS:
            # 低置信度: 用对话日期作为近似
            final_metadata['event_time'] = event_time.isoformat()
            final_metadata['event_time_extraction'] = 'context_approximate'
            final_metadata['event_time_confidence'] = 'low'
            logger.debug(f"Using context date as approximate event_time: {event_time}")
        else:
            # 无法提取事件时间
            logger.debug(f"No event_time available (method={extraction_method})")

        # 创建记忆项 - 使用事件时间作为 timestamp (而非存储时间)
        memory = EpisodicMemory(
            id=uuid.uuid4().hex,
            content=content,
            timestamp=event_time or storage_time,  # 🔥 优先使用事件时间
            entities=final_entities,
            importance=importance,
            emotion_tags=emotion_tags or [],
            emotion_intensity=emotion_intensity,
            metadata=final_metadata
        )

        # 记录存储时间到 metadata (区分于事件时间)
        memory.metadata['storage_time'] = storage_time.isoformat()

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

        # 🧠 Key-Value Store Integration
        if self.memory_store:
            self.memory_store.store(
                memory_id=memory.id,
                content=memory.content,
                vector=np.array(memory.embedding) if memory.embedding else None,
                entities=memory.entities,
                timestamp=memory.timestamp,
                relations=extracted_relations,  # Pass extracted relations
                details=memory.metadata,
                importance=memory.importance,
                emotion_intensity=memory.emotion_intensity
            )

        # 🧠 Event Graph Integration
        if self.event_graph:
            self.event_graph.add_event(
                content=memory.content,
                entities=memory.entities,
                timestamp=memory.timestamp,
                metadata=memory.metadata,
                embedding=np.array(memory.embedding) if memory.embedding else None
            )

        # 存储到本地列表/缓存 (for backward compatibility)
        self.memories.append(memory)
        self.memory_dict[memory.id] = memory

        # 更新索引
        self._update_indexes(memory)

        # 🔥 FIX: 容量控制 - 基于全局存储计数，而非仅本地列表
        should_forget = False
        if self._use_global_storage:
            # Use global count for capacity check
            capacity_status = await self.get_capacity_status_global()
            if capacity_status.get('current', 0) > self.capacity:
                should_forget = True
        else:
            # Local mode: use local list
            if len(self.memories) > self.capacity:
                should_forget = True

        if should_forget:
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
        """更新索引 - 增强版"""
        # 实体索引 (同时索引原样和小写版本)
        for entity in memory.entities:
            self.entity_index[entity].append(memory.id)
            # 🔧 FIX: 也索引小写版本，提高检索命中率
            entity_lower = entity.lower()
            if entity_lower != entity:
                self.entity_index[entity_lower].append(memory.id)

        # 🔧 NEW: 从内容中提取并索引关系词 (grandma, mom, friend 等)
        relation_words = {
            'grandma', 'grandmother', 'grandpa', 'grandfather',
            'mom', 'mother', 'dad', 'father', 'parent', 'parents',
            'sister', 'brother', 'sibling', 'aunt', 'uncle',
            'cousin', 'wife', 'husband', 'spouse', 'partner',
            'friend', 'boyfriend', 'girlfriend',
            'son', 'daughter', 'child', 'children', 'kid', 'kids',
            'boss', 'coworker', 'colleague', 'mentor', 'teacher'
        }
        content_lower = memory.content.lower()
        for rel_word in relation_words:
            if rel_word in content_lower:
                self.entity_index[rel_word].append(memory.id)

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
        """转换为字典格式 - 🔥 FIX: 包含 embedding 避免重复计算"""
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
            'speaker': memory.speaker,
            'embedding': memory.embedding  # 🔥 FIX: 传递预计算的 embedding
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
        metadata: Dict[str, Any] = None,
        inherited_event_time: datetime = None  # 🔥 2025-12-16: 继承的事件时间 (用于 [Event] 记忆)
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
            inherited_event_time: 🔥 继承的事件时间 (从原始对话传递给 [Event] 摘要)

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

        # 🔥 FIX: 自动提取实体和关系 (复用 store_memory 的逻辑)
        extracted_entities: List[str] = []
        extracted_relations: List[Dict[str, Any]] = []
        kg_entity_payload: List[Dict[str, Any]] = []

        if self.kg_builder and not entities:  # 只在没有手动传入entities时自动提取
            try:
                kg_context = metadata or {}
                entities_list, relations_list = await self.kg_builder.extract_from_text(
                    text=content,
                    use_llm=True,
                    context=kg_context
                )
                kg_entity_payload = entities_list or []
                extracted_entities = [
                    e.get('name', e) if isinstance(e, dict) else e
                    for e in kg_entity_payload
                ]
                extracted_relations = relations_list or []
            except Exception as e:
                logger.warning(f"Failed to auto-extract entities: {e}")

        # 合并手动传入的entities和自动提取的entities
        final_entities = list(set((entities or []) + extracted_entities))

        # 🔥 2025-12-05: 提取事件发生时间 (解决 temporal 准确率问题)
        # 🔥 2025-12-11: 修复! timestamp 是会话时间，不是事件时间
        #    "yesterday" + conversation_date(08 May) = event_date(07 May)
        storage_time = datetime.now()
        final_metadata = metadata.copy() if metadata else {}

        # 🔥 2025-12-16 FIX: 优先使用继承的事件时间 (用于 [Event] 摘要)
        # 当从原始对话创建 [Event] 摘要时，应该继承原始对话的精确 event_time
        if inherited_event_time:
            event_time = inherited_event_time
            extraction_method = 'inherited'
            final_metadata['event_time'] = event_time.isoformat()
            final_metadata['event_time_extraction'] = 'inherited'
            final_metadata['event_time_confidence'] = 'high'
            final_metadata['inherited_from_source'] = True
            logger.debug(f"🔗 Using inherited event_time: {event_time}")
        else:
            # timestamp 是会话/上下文时间，用它作为计算相对时间的参考
            # 但 event_time 应该从内容中提取 (处理 "yesterday", "last week" 等)
            reference_time = timestamp or storage_time

            # 先尝试从内容中提取事件时间
            event_time, extraction_method = extract_event_time_from_content(
                content=content,
                metadata=final_metadata,
                fallback_time=reference_time  # 用会话时间作为参考和fallback
            )

            # 🔥 2025-12-14 FIX v2: 分层处理不同提取方法
            # 高置信度方法直接写入，低置信度方法标记后写入
            HIGH_CONFIDENCE_METHODS = ('relative', 'absolute', 'explicit', 'metadata')
            LOW_CONFIDENCE_METHODS = ('context',)  # context=对话日期，作为近似值

            # 记录事件时间信息
            if event_time and extraction_method in HIGH_CONFIDENCE_METHODS:
                # 高置信度: 明确提取的时间
                final_metadata['event_time'] = event_time.isoformat()
                final_metadata['event_time_extraction'] = extraction_method
                final_metadata['event_time_confidence'] = 'high'
            elif event_time and extraction_method in LOW_CONFIDENCE_METHODS:
                # 🔥 2025-12-14: 低置信度也写入，但标记，让检索模块可以使用
                # 对于 [Event] 类记忆，用对话日期作为近似 event_time 比完全没有强
                final_metadata['event_time'] = event_time.isoformat()
                final_metadata['event_time_extraction'] = 'context_approximate'
                final_metadata['event_time_confidence'] = 'low'
                logger.debug(f"Using context date as approximate event_time: {event_time}")
            elif timestamp:
                # 🔥 2025-12-14: 即使无法提取，也用 conversation_date 作为最后手段
                # 这确保 [Event] 类记忆至少有时间参考
                final_metadata['event_time'] = timestamp.isoformat()
                final_metadata['event_time_extraction'] = 'conversation_fallback'
                final_metadata['event_time_confidence'] = 'fallback'
                event_time = timestamp
                logger.debug(f"Using conversation_date as fallback event_time: {timestamp}")
            else:
                # 完全无法确定时间
                logger.debug(f"No event_time available (method={extraction_method})")
                event_time = None

        final_metadata['storage_time'] = storage_time.isoformat()
        # 🔥 2025-12-11 新增: 记录 conversation_date（会话日期）
        # 用于后续模块从 metadata 读取，而不依赖解析 [Context: ...] 前缀
        if timestamp:
            final_metadata['conversation_date'] = timestamp.isoformat()

        # 创建记忆项 - 使用事件时间
        memory = EpisodicMemory(
            id=uuid.uuid4().hex,
            content=content,
            timestamp=event_time or storage_time,  # 🔥 优先使用事件时间
            entities=final_entities,  # 🔥 使用合并后的实体列表
            importance=importance,
            emotion_tags=emotion_tags or [],
            emotion_intensity=emotion_intensity,
            metadata=final_metadata,
            event_id=self.current_event_id,  # 🔥 关联事件ID
            speaker=speaker  # 🔥 记录说话人
        )

        # 🔥 FIX: 保存提取的关系到metadata
        if extracted_relations:
            memory.metadata['kg_relations'] = extracted_relations
            memory.metadata['kg_auto_extracted'] = True
        if kg_entity_payload:
            memory.metadata['kg_entities'] = [
                e.get('name') if isinstance(e, dict) else str(e)
                for e in kg_entity_payload
            ]

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

        # 🔥 FIX: 容量控制 - 基于全局存储计数，而非仅本地列表
        should_forget = False
        if self._use_global_storage:
            capacity_status = await self.get_capacity_status_global()
            if capacity_status.get('current', 0) > self.capacity:
                should_forget = True
        else:
            if len(self.memories) > self.capacity:
                should_forget = True

        if should_forget:
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

        # 🔥 2025-12-11 修复: 传入提取的实体和关系，否则KG永远为空!
        await self._update_knowledge_graph(memory, kg_entity_payload, extracted_relations)

        # 🔥 Auto-persist to JSON file
        self._save_state_to_file()

        # 🔥 2025-12-11 修复: 返回 event_time 供跨脑区分发使用
        return {
            'memory_id': memory.id,
            'event_id': self.current_event_id,
            'is_new_event': is_new_event,
            'event_boundary_reason': boundary_reason,
            'stored': True,
            'capacity_status': self._get_capacity_status(),
            'event_time': event_time,  # 🔥 从内容提取的事件时间
            'event_time_extraction': extraction_method  # 提取方法: relative/absolute/context/fallback
        }


