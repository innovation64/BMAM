"""
Hippocampus Agent - 海马体智能体
对应脑区: 海马体 (Hippocampus)
主要功能: 情节记忆存储+检索+巩固 (Plan C: 集成存储和处理)

核心设计:
1. 内部存储20,000条情节记忆 (人一生重要事件容量)
2. 支持时间检索和实体检索
3. 快速遗忘机制 (保留重要的事件)
4. 不使用FAISS,使用简单索引
5. 自动巩固: 重要记忆 → TemporalLobeAgent (语义记忆)
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
import uuid

from ..base import BrainAgent, AgentMessage, BrainRegion
from ...utils.knowledge_graph_builder import KnowledgeGraphBuilder

logger = logging.getLogger(__name__)


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
    embedding: Optional[List[float]] = None  # 🔥 语义embedding (混合检索)
    # 🔥 Phase 1: Event Segmentation (事件分割)
    event_id: Optional[str] = None  # 事件ID (用于事件边界检测)
    speaker: Optional[str] = None  # 说话人 (用于对话场景)


class HippocampusAgent(BrainAgent):
    """
    海马体智能体 - 情节记忆存储+检索+巩固 (Plan C)

    容量: 20,000条情节记忆 (人一生重要事件)
    存储格式: List + Entity/Time Index
    遗忘机制: 快速遗忘 (保留重要的,基于importance和access_count)
    巩固机制: 自动提取重要记忆 → TemporalLobeAgent
    """

    def __init__(
        self,
        capacity: int = 20000,
        temporal_lobe_agent=None,
        client=None,
        embedding_service=None,
        kg_builder: Optional[KnowledgeGraphBuilder] = None
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

        # 🔥 内部记忆存储 (人一生容量)
        self.capacity = capacity
        self.memories: List[EpisodicMemory] = []

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
            f"kg_extraction={'shared' if self._shared_kg_builder else 'local'})"
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

        # 存储到列表
        self.memories.append(memory)
        self.memory_dict[memory.id] = memory

        # 更新索引
        self._update_indexes(memory)

        # 容量控制
        if len(self.memories) > self.capacity:
            await self._trigger_forgetting()

        self.total_stored += 1

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

    async def search_memories(
        self,
        query: str = None,
        entities: List[str] = None,
        time_range: Dict[str, str] = None,
        k: int = 10
    ) -> Dict[str, Any]:
        """
        搜索情节记忆

        Args:
            query: 查询文本
            entities: 实体过滤
            time_range: 时间范围 {'start': 'YYYY-MM-DD', 'end': 'YYYY-MM-DD'}
            k: 返回数量

        Returns:
            {
                'memories': List[Dict],
                'count': int,
                'search_time_ms': float
            }
        """

        start_time = datetime.now()
        results = []

        # 🔥 策略1: 实体索引检索 (如果提供了entities)
        if entities:
            candidate_ids = set()
            for entity in entities:
                candidate_ids.update(self.entity_index.get(entity, []))

            candidates = [self.memory_dict[mid] for mid in candidate_ids if mid in self.memory_dict]

            # 🧠 Plan C修复: entity index没找到时fallback到全文搜索
            if not candidates:
                candidates = self.memories

        # 🔥 策略2: 时间索引检索 (如果提供了time_range)
        elif time_range:
            start_date = datetime.fromisoformat(time_range.get('start', '1970-01-01'))
            end_date = datetime.fromisoformat(time_range.get('end', '2100-01-01'))

            candidate_ids = []
            for date_str, ids in self.time_index.items():
                date = datetime.fromisoformat(date_str)
                if start_date <= date <= end_date:
                    candidate_ids.extend(ids)

            candidates = [self.memory_dict[mid] for mid in candidate_ids if mid in self.memory_dict]

            # 🧠 Plan C修复: time index没找到时fallback到全文搜索
            if not candidates:
                candidates = self.memories

        # 🔥 策略3: 全文本搜索 (BM25-like keyword matching)
        else:
            candidates = self.memories

        # 🔥 混合检索: Keyword + Semantic (Plan C完整实现)
        if query:
            # 计算query embedding (如果服务可用)
            query_embedding = None
            if self.embedding_service:
                try:
                    query_embedding = await self.embedding_service.encode_text(query)
                    query_embedding = query_embedding.tolist() if hasattr(query_embedding, 'tolist') else query_embedding
                except (RuntimeError, ValueError) as e:
                    logger.warning(f"Failed to compute query embedding: {e}")

            query_words = set(query.lower().split())

            for mem in candidates:
                # 1️⃣ 关键词相关性 (BM25-like)
                content_words = set(mem.content.lower().split())
                overlap = len(query_words & content_words)
                keyword_score = overlap / len(query_words) if overlap > 0 else 0.1

                # 2️⃣ 语义相关性 (Cosine Similarity)
                semantic_score = 0.0
                if query_embedding and mem.embedding:
                    semantic_score = self._cosine_similarity(query_embedding, mem.embedding)

                # 🎯 P3: KG关系增强 - 如果query中的实体在memory的KG关系中出现，提升分数
                kg_boost = 0.0
                if mem.metadata.get('kg_relations'):
                    relations = mem.metadata.get('kg_relations', [])
                    for rel in relations:
                        # 检查关系的source/target是否在query中
                        source = rel.get('source', '').lower()
                        target = rel.get('target', '').lower()
                        relation_type = rel.get('relation', '').lower()

                        # 如果query提到了关系中的实体，提升相关性
                        query_lower = query.lower()
                        if source in query_lower or target in query_lower:
                            kg_boost += 0.15  # 每个匹配的关系提升15%
                        if relation_type.replace('_', ' ') in query_lower:
                            kg_boost += 0.1  # 如果关系类型也匹配，再提升10%

                    # 限制KG boost最多50%
                    kg_boost = min(kg_boost, 0.5)

                # 3️⃣ 混合分数 (Hybrid: 0.3 * keyword + 0.5 * semantic + 0.2 * kg_boost)
                # 语义权重更高，KG关系作为辅助增强
                if query_embedding and mem.embedding:
                    relevance = 0.3 * keyword_score + 0.5 * semantic_score + kg_boost
                else:
                    relevance = 0.7 * keyword_score + kg_boost  # Fallback to keyword + kg

                results.append({
                    'memory': mem,
                    'relevance': relevance,
                    'keyword_score': keyword_score,
                    'semantic_score': semantic_score,
                    'kg_boost': kg_boost  # 🎯 P3: 记录KG增强分数
                })
        else:
            # 无query,返回所有candidates
            results = [{'memory': mem, 'relevance': 1.0, 'keyword_score': 1.0, 'semantic_score': 1.0} for mem in candidates]

        # 更新访问统计
        for item in results:
            mem = item['memory']
            mem.access_count += 1
            mem.last_accessed = datetime.now()
            metadata = mem.metadata or {}
            metadata['hit_count'] = mem.access_count
            metadata['last_accessed'] = mem.last_accessed.isoformat()
            if query:
                metadata['last_used_query'] = query
            metadata.setdefault('last_access_context', {})
            if entities:
                metadata['last_access_context']['entities'] = entities
            if time_range:
                metadata['last_access_context']['time_range'] = time_range
            mem.metadata = metadata

        # 排序: relevance > importance > timestamp
        results.sort(
            key=lambda x: (
                x['relevance'],
                x['memory'].importance,
                x['memory'].timestamp
            ),
            reverse=True
        )

        # 🧠 Plan C修复：如果结果太少，返回所有记忆让reasoning判断
        # 人脑的海马体会激活相关记忆网络，不会因为关键词不匹配就0记忆
        if len(results) < min(3, k):
            # 返回所有记忆，按最近访问排序
            results = [{'memory': mem, 'relevance': 0.5} for mem in self.memories]
            results.sort(key=lambda x: x['memory'].timestamp, reverse=True)

        # 限制返回数量（但至少返回所有存储的记忆如果总数<k）
        results = results[:k]

        search_time = (datetime.now() - start_time).total_seconds() * 1000

        # 返回记忆+分数信息
        memories_with_scores = []
        for r in results:
            mem_dict = self._memory_to_dict(r['memory'])
            mem_dict['relevance'] = r.get('relevance', 0.0)
            mem_dict['keyword_score'] = r.get('keyword_score', 0.0)
            mem_dict['semantic_score'] = r.get('semantic_score', 0.0)
            mem_dict['kg_boost'] = r.get('kg_boost', 0.0)  # 🎯 P3: KG增强分数
            memories_with_scores.append(mem_dict)

        return {
            'memories': memories_with_scores,
            'count': len(results),
            'search_time_ms': search_time,
            'kg_enhanced': any(r.get('kg_boost', 0) > 0 for r in results)  # 🎯 P3: 标记是否使用了KG增强
        }

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        计算余弦相似度

        Args:
            vec1, vec2: 向量

        Returns:
            相似度 (0-1)
        """
        import numpy as np

        v1 = np.array(vec1)
        v2 = np.array(vec2)

        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return float(max(0.0, similarity))  # 确保非负

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

    async def _should_consolidate_memory(self, memory: EpisodicMemory) -> bool:
        """
        LLM动态决策是否巩固记忆

        神经科学依据:
        - 海马体根据记忆的"重要性特征"决定是否巩固到新皮层
        - 不是简单的阈值判断,而是综合考虑多个因素

        文献: McClelland et al. (1995) "Systems Consolidation"
        """

        # 构建决策prompt
        decision_prompt = f"""你是海马体的记忆巩固控制器。判断以下情节记忆是否需要巩固到长期记忆。

记忆内容: {memory.content}
记忆属性:
- 重要性: {memory.importance}
- 访问次数: {memory.access_count}
- 情绪标签: {', '.join(memory.emotion_tags) if memory.emotion_tags else '无'}
- 情绪强度: {memory.emotion_intensity}
- 实体: {', '.join(memory.entities) if memory.entities else '无'}

巩固标准 (综合判断,非硬编码阈值):
1. 高重要性 (importance > 0.6) - 但不是唯一标准
2. 强情绪体验 (emotion_intensity > 0.7) - 情绪记忆更易巩固
3. 包含重要实体关系 - 实体间的关系值得长期记住
4. 可提取语义知识 - 有复用价值的经验

请综合考虑以上因素,判断是否巩固。

返回JSON:
{{
    "should_consolidate": true/false,
    "reasoning": "详细理由"
}}

只输出JSON,不要其他文字。"""

        try:
            response = await self.call_llm(decision_prompt, max_tokens=200, temperature=0.3)

            import json
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group())
                should_consolidate = decision.get('should_consolidate', False)
                reasoning = decision.get('reasoning', '')

                if should_consolidate:
                    logger.debug(f"Consolidating memory {memory.id[:8]}: {reasoning}")

                return should_consolidate
            else:
                # Fallback: 使用简化规则
                return memory.importance > 0.6 or memory.emotion_intensity > 0.7

        except (json.JSONDecodeError) as e:
            logger.warning(f"LLM consolidation decision failed: {e}, using fallback")
            # Fallback: 简化规则
            return memory.importance > 0.6 or memory.emotion_intensity > 0.7

    async def _trigger_forgetting(self):
        """
        触发遗忘机制 - 使用LLM动态决策保护策略

        神经科学依据:
        - 海马体的遗忘是选择性的,不是简单的时间或阈值决策
        - 综合考虑重要性、情绪、访问频率、时间衰减

        文献: Richards & Frankland (2017) "The Persistence and Transience of Memory"
        """
        from datetime import datetime, timedelta

        now = datetime.now()

        # LLM决策保护策略
        protected = []
        forgettable = []

        # 对每个记忆进行保护判断
        for mem in self.memories:
            # 基本保护: 最近记忆总是保护 (时间衰减曲线)
            time_ago_hours = (now - mem.timestamp).total_seconds() / 3600
            if time_ago_hours < 24:  # 24小时内必保护
                protected.append(mem)
                continue

            # LLM决策是否保护 (综合判断,非硬编码阈值)
            should_protect = await self._should_protect_from_forgetting(mem, time_ago_hours)

            if should_protect:
                protected.append(mem)
            else:
                forgettable.append(mem)

        # 如果没有可遗忘的,直接返回
        if not forgettable:
            return

        # 从forgettable中选择遗忘的记忆 (动态比例)
        # 不是固定20%,而是根据容量压力动态调整
        capacity_pressure = len(self.memories) / self.capacity
        if capacity_pressure > 0.9:
            forget_ratio = 0.3  # 高压力: 遗忘30%
        elif capacity_pressure > 0.7:
            forget_ratio = 0.2  # 中压力: 遗忘20%
        else:
            forget_ratio = 0.1  # 低压力: 遗忘10%

        forgettable.sort(
            key=lambda m: (m.importance, m.access_count, m.timestamp),
            reverse=False  # 升序 - 最不重要的在前
        )

        forget_count = max(1, int(len(forgettable) * forget_ratio))
        forgotten = forgettable[:forget_count]
        kept_forgettable = forgettable[forget_count:]

        # 更新memories列表
        self.memories = protected + kept_forgettable

        # 更新memory_dict
        for mem in forgotten:
            if mem.id in self.memory_dict:
                del self.memory_dict[mem.id]

        # 重建索引
        self._rebuild_indexes()

        self.total_forgotten += forget_count


    async def _should_protect_from_forgetting(self, memory: EpisodicMemory, time_ago_hours: float) -> bool:
        """
        LLM决策是否保护记忆免于遗忘

        考虑因素:
        - 重要性
        - 访问频率
        - 情绪强度
        - 时间衰减
        """

        # 快速规则: 高访问频率或强情绪总是保护
        if memory.access_count >= 3 or memory.emotion_intensity > 0.8:
            return True

        # 使用LLM综合判断 (采样决策,不是每个都调用LLM)
        # 对于边界情况才调用LLM
        if 0.4 < memory.importance < 0.7:
            try:
                decision_prompt = f"""判断是否保护以下记忆免于遗忘:

记忆: {memory.content[:100]}
- 重要性: {memory.importance}
- 访问次数: {memory.access_count}
- 距今时间: {time_ago_hours:.1f}小时
- 情绪强度: {memory.emotion_intensity}

考虑艾宾浩斯遗忘曲线和记忆特征,判断是否保留。

返回JSON: {{"protect": true/false, "reason": "简短理由"}}"""

                response = await self.call_llm(decision_prompt, max_tokens=100, temperature=0.3, quick_fail=True)

                import json
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    decision = json.loads(json_match.group())
                    return decision.get('protect', memory.importance >= 0.5)

            except (json.JSONDecodeError) as e:
                # LLM失败,使用简化规则
                pass

        # Fallback规则
        return memory.importance >= 0.5

    def _rebuild_indexes(self):
        """重建所有索引"""
        self.entity_index.clear()
        self.time_index.clear()

        for mem in self.memories:
            self._update_indexes(mem)

    async def _consolidate_to_temporal_lobe(self, memory: EpisodicMemory):
        """
        内部巩固功能: Hippocampus → TemporalLobe (Plan C)
        将重要的情节记忆提取为语义知识

        模拟人脑的记忆巩固过程 (睡眠时海马体向新皮层转移记忆)
        """
        if not self.temporal_lobe:
            return

        try:
            # 使用LLM提取语义知识
            prompt = f"""从以下情节记忆中提取核心的语义知识:

情节内容: {memory.content}
实体: {', '.join(memory.entities)}
情绪: {', '.join(memory.emotion_tags)} (强度: {memory.emotion_intensity})

请提取:
1. 核心事实和知识点
2. 实体之间的关系
3. 可复用的经验或模式

以简洁的语义知识形式输出。"""

            knowledge = await self.call_llm(
                prompt=prompt,
                context={'memory_id': memory.id, 'timestamp': memory.timestamp.isoformat()},
                max_tokens=500,
                temperature=0.3
            )

            # 🔥 提取关系三元组 (Plan C完整实现：LLM提取精细关系)
            relations = []
            if memory.entities:
                try:
                    # 让LLM提取结构化关系
                    relation_prompt = f"""从以下情节记忆中提取结构化的关系三元组。

情节内容: {memory.content}
实体: {', '.join(memory.entities)}

请提取精确的关系类型（不要只用generic的related_to）。

常见关系类型示例：
- attended（参加）: Person attended Event
- researched（研究）: Person researched Topic
- interested_in（对...感兴趣）: Person interested_in Topic
- learned_about（学习）: Person learned_about Topic
- works_in（工作于）: Person works_in Field
- identifies_as（认同为）: Person identifies_as Identity
- supports（支持）: Organization supports Community

输出JSON格式：
{{
  "relations": [
    ["source_entity", "relation_type", "target_entity"],
    ...
  ]
}}

只输出JSON，不要其他文字。"""

                    rel_result = await self.call_llm(
                        prompt=relation_prompt,
                        max_tokens=300,
                        temperature=0.1
                    )

                    # 解析JSON
                    import json
                    import re
                    json_match = re.search(r'\{.*\}', rel_result, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group())
                        relations = [tuple(r) for r in parsed.get('relations', [])]
                    else:
                        # Fallback to simple related_to
                        if len(memory.entities) >= 2:
                            relations = [(memory.entities[0], "related_to", memory.entities[1])]
                except (json.JSONDecodeError) as e:
                    logger.warning(f"Failed to extract relations via LLM: {e}, using fallback")
                    # Fallback to simple related_to
                    if len(memory.entities) >= 2:
                        for i in range(len(memory.entities) - 1):
                            relations.append((memory.entities[i], "related_to", memory.entities[i+1]))

            # 发送到TemporalLobe (✅ 保留source_episode_id用于回溯)
            await self.temporal_lobe.process_message(AgentMessage(
                sender='hippocampus',
                receiver='temporal_lobe',
                message_type='request',
                content={
                    'action': 'store_semantic',
                    'content': knowledge,
                    'memory_subtype': 'semantic',
                    'entities': memory.entities,
                    'relations': relations,
                    'importance': memory.importance,
                    'event_time': memory.timestamp,  # 🔥 传递事件时间 (而非学习时间)
                    'metadata': {
                        'source_episode_id': memory.id,  # 🔥 保留源情节记忆ID用于回溯
                        'event_id': memory.event_id,     # 🔥 保留事件ID
                        'consolidation_time': datetime.now().isoformat()
                    }
                }
            ))

            self.total_consolidated += 1

        except (Exception) as e:
            logger.error(f"Failed to consolidate memory {memory.id}: {e}")

    async def consolidate_memories(self) -> Dict[str, Any]:
        """
        批量记忆巩固: 找到重要但未巩固的记忆,提取模式 (Plan C)

        这个方法会在后台定期调用,模拟睡眠时的记忆巩固
        """

        if not self.temporal_lobe:
            return {
                'consolidated': 0,
                'message': 'TemporalLobe not connected'
            }

        # 找到重要但访问较少的记忆 (候选巩固对象)
        # ✅ 移除硬编码 consolidation_threshold,使用动态筛选
        consolidation_candidates = [
            mem for mem in self.memories
            if (mem.importance > 0.5 or mem.emotion_intensity > 0.6)  # 动态标准
            and mem.access_count < 3  # 避免重复巩固
        ]

        consolidated_count = 0

        # 按时间分组,提取模式
        time_groups = defaultdict(list)
        for mem in consolidation_candidates[:100]:  # 限制处理数量
            date_key = mem.timestamp.strftime('%Y-%m-%d')
            time_groups[date_key].append(mem)

        # 对每一天的记忆进行巩固
        for date_key, memories in time_groups.items():
            if len(memories) > 1:
                # 合并同一天的多个记忆
                combined_content = "\n".join([f"- {m.content}" for m in memories])
                all_entities = list(set(sum([m.entities for m in memories], [])))

                try:
                    # 提取日摘要和模式
                    prompt = f"""从以下{len(memories)}条情节记忆中提取关键模式和知识:

{combined_content}

请提取:
1. 这一天的核心主题和模式
2. 重要的事实和知识
3. 实体关系

以结构化的语义知识输出。"""

                    pattern = await self.call_llm(
                        prompt=prompt,
                        context={'date': date_key, 'memory_count': len(memories)},
                        max_tokens=800,
                        temperature=0.3
                    )

                    # 发送到TemporalLobe
                    await self.temporal_lobe.process_message(AgentMessage(
                        sender='hippocampus',
                        receiver='temporal_lobe',
                        message_type='request',
                        content={
                            'action': 'store_semantic',
                            'content': f"[{date_key}] {pattern}",
                            'memory_subtype': 'semantic',
                            'entities': all_entities,
                            'relations': [],
                            'importance': 0.8,
                            'metadata': {
                                'consolidated_from': [m.id for m in memories],
                                'consolidation_date': datetime.now().isoformat()
                            }
                        }
                    ))

                    consolidated_count += 1

                except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                    logger.error(f"Failed to consolidate memories for {date_key}: {e}")

        self.total_consolidated += consolidated_count

        return {
            'consolidated': consolidated_count,
            'total_consolidated': self.total_consolidated,
            'message': f'Successfully consolidated {consolidated_count} memory patterns'
        }

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

        # 存储到列表
        self.memories.append(memory)
        self.memory_dict[memory.id] = memory

        # 更新所有索引 (包括event_index)
        self._update_indexes(memory)

        # 容量控制
        if len(self.memories) > self.capacity:
            await self._trigger_forgetting()

        self.total_stored += 1

        # 自动巩固重要记忆 - 使用LLM动态决策
        if self.temporal_lobe:
            should_consolidate = await self._should_consolidate_memory(memory)
            if should_consolidate:
                await self._consolidate_to_temporal_lobe(memory)

        await self._update_knowledge_graph(memory, None, None)

        return {
            'memory_id': memory.id,
            'event_id': self.current_event_id,
            'is_new_event': is_new_event,
            'event_boundary_reason': boundary_reason,
            'stored': True,
            'capacity_status': self._get_capacity_status()
        }

    async def _detect_event_boundary(
        self,
        content: str,
        timestamp: datetime,
        speaker: Optional[str],
        emotion_tags: List[str],
        recent_memories: List[EpisodicMemory]
    ) -> tuple[bool, str]:
        """
        检测事件边界 (Event Boundary Detection) - LLM动态决策

        神经科学依据:
        - 海马体根据多种特征综合判断事件边界,不是简单的阈值
        - 事件分割理论 (Zacks et al., 2007): Event Segmentation Theory

        文献: Radvansky & Zacks (2014) "Event boundaries in memory and cognition"
        """

        if not recent_memories:
            return True, "first_memory"

        last_memory = recent_memories[-1]

        # 1️⃣ 绝对时间跳跃 (> 6小时认为是明确的事件边界)
        time_gap = (timestamp - last_memory.timestamp).total_seconds() / 3600  # hours
        if time_gap > 6.0:
            return True, f"large_time_gap_{time_gap:.1f}h"

        # 2️⃣ 说话人改变 (对话场景)
        if speaker and last_memory.speaker and speaker != last_memory.speaker:
            return True, f"speaker_change_{last_memory.speaker}->{speaker}"

        # 3️⃣ 使用LLM动态判断事件边界 (综合时间、主题、情绪)
        try:
            boundary_prompt = f"""判断是否是新事件边界 (Event Boundary Detection):

当前记忆: {content}
- 时间: {timestamp.strftime('%Y-%m-%d %H:%M')}
- 情绪: {', '.join(emotion_tags) if emotion_tags else '无'}

最近记忆: {last_memory.content}
- 时间: {last_memory.timestamp.strftime('%Y-%m-%d %H:%M')}
- 情绪: {', '.join(last_memory.emotion_tags) if last_memory.emotion_tags else '无'}

时间间隔: {time_gap:.1f}小时

判断标准 (Event Segmentation Theory):
1. 主题是否切换 (topic shift) - 谈论的是不同的话题?
2. 时间跳跃 (1-6小时间隔是否足够大?)
3. 情绪变化 (情绪是否发生显著转变?)
4. 情境变化 (是否换了场景/活动?)

综合判断是否是新事件。

返回JSON: {{"is_new_event": true/false, "reason": "简短理由"}}"""

            response = await self.call_llm(boundary_prompt, max_tokens=150, temperature=0.3, quick_fail=True)

            import json
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group())
                is_new = decision.get('is_new_event', False)
                reason = decision.get('reason', 'llm_decision')

                if is_new:
                    return True, f"llm_{reason}"
                else:
                    return False, "continue_current_event"

        except (json.JSONDecodeError) as e:
            logger.warning(f"LLM event grouping decision parse failed: {e}")

        # 4️⃣ Fallback: 语义相似度检测
        if self.embedding_service and last_memory.embedding:
            try:
                current_embedding = await self.embedding_service.encode_text(content)
                current_embedding = current_embedding.tolist() if hasattr(current_embedding, 'tolist') else current_embedding

                similarity = self._cosine_similarity(current_embedding, last_memory.embedding)

                # 动态阈值: 时间越长,阈值越高 (更容易判定为新事件)
                threshold = 0.3 + (time_gap / 6.0) * 0.2  # 0.3-0.5之间
                if similarity < threshold:
                    return True, f"topic_shift_sim={similarity:.2f}_threshold={threshold:.2f}"

            except (RuntimeError, ValueError) as e:
                logger.warning(f"Failed to compute similarity for event detection: {e}")

        # 5️⃣ 最终fallback: 关键词相似度
        content_words = set(content.lower().split())
        last_words = set(last_memory.content.lower().split())
        overlap = len(content_words & last_words)
        keyword_similarity = overlap / len(content_words) if len(content_words) > 0 else 0

        # 动态关键词阈值
        keyword_threshold = 0.2 + (time_gap / 6.0) * 0.1
        if keyword_similarity < keyword_threshold:
            return True, f"keyword_shift_sim={keyword_similarity:.2f}"

        # 默认: 继续当前事件
        return False, "continue_current_event"

    async def retrieve_by_timeline(
        self,
        start_time: datetime,
        end_time: datetime,
        k: int = 50
    ) -> Dict[str, Any]:
        """
        时间线检索 (Timeline Retrieval)

        人脑的时间细胞 (Time Cells): 海马体CA1区有专门编码时间的神经元
        支持按时间范围快速检索记忆

        Args:
            start_time: 起始时间
            end_time: 结束时间
            k: 最大返回数量

        Returns:
            {
                'memories': List[Dict],
                'events': List[str],  # 该时间段内的所有事件ID
                'count': int
            }
        """

        # 🔥 使用time_index快速过滤
        candidate_ids = []
        current_date = start_time.date()
        end_date = end_time.date()

        while current_date <= end_date:
            date_key = current_date.strftime('%Y-%m-%d')
            candidate_ids.extend(self.time_index.get(date_key, []))
            current_date += timedelta(days=1)

        # 获取记忆对象并精确过滤时间
        memories = []
        events = set()

        for mem_id in candidate_ids:
            if mem_id in self.memory_dict:
                mem = self.memory_dict[mem_id]
                if start_time <= mem.timestamp <= end_time:
                    memories.append(mem)
                    if mem.event_id:
                        events.add(mem.event_id)

        # 按时间排序
        memories.sort(key=lambda m: m.timestamp)

        # 限制返回数量
        memories = memories[:k]

        # 转换为字典格式
        memories_dict = [self._memory_to_dict(m) for m in memories]

        return {
            'memories': memories_dict,
            'events': sorted(list(events)),
            'count': len(memories_dict),
            'time_range': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            }
        }

    async def retrieve_by_event(
        self,
        event_id: str,
        include_context: bool = True
    ) -> Dict[str, Any]:
        """
        事件检索 (Event-based Retrieval)

        检索某个事件的所有记忆
        人脑的情节记忆是以事件为单位组织的

        Args:
            event_id: 事件ID
            include_context: 是否包含前后事件的上下文

        Returns:
            {
                'event_id': str,
                'memories': List[Dict],
                'context_events': List[str],  # 前后事件ID
                'count': int
            }
        """

        # 获取事件的所有记忆
        memory_ids = self.event_index.get(event_id, [])
        memories = [self.memory_dict[mid] for mid in memory_ids if mid in self.memory_dict]

        # 按时间排序
        memories.sort(key=lambda m: m.timestamp)

        # 如果需要上下文,找到相邻事件
        context_events = []
        if include_context and memories:
            first_time = memories[0].timestamp
            last_time = memories[-1].timestamp

            # 找前一个事件 (1小时内)
            prev_events = set()
            next_events = set()

            # 动态上下文窗口: 根据事件持续时间调整
            event_duration = (last_time - first_time).total_seconds() / 3600  # hours
            # 如果事件很短(< 1小时),窗口=事件时长的2倍; 否则1.5倍,上限6小时
            if event_duration < 1:
                context_window = event_duration * 2  # 30分钟事件 → 1小时窗口
            else:
                context_window = min(6, event_duration * 1.5)  # 2小时事件 → 3小时窗口,上限6h

            for mem in self.memories:
                if mem.event_id and mem.event_id != event_id:
                    # 前一个事件
                    if first_time - timedelta(hours=context_window) <= mem.timestamp < first_time:
                        prev_events.add(mem.event_id)
                    # 后一个事件
                    elif last_time < mem.timestamp <= last_time + timedelta(hours=context_window):
                        next_events.add(mem.event_id)

            context_events = sorted(list(prev_events)) + sorted(list(next_events))

        return {
            'event_id': event_id,
            'memories': [self._memory_to_dict(m) for m in memories],
            'context_events': context_events,
            'count': len(memories)
        }

    async def batch_consolidate(
        self,
        batch_size: int = 50,
        similarity_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        批量记忆巩固 (Batch Consolidation) - Phase 1核心功能

        模拟人脑的睡眠巩固过程:
        1. 每50条记忆触发一次巩固
        2. 聚类相似记忆 (topic clustering)
        3. 提取语义知识
        4. 存储到TemporalLobe
        5. 释放Hippocampus容量

        人脑机制 (Rasch & Born, 2013):
        - 慢波睡眠时,海马体重播记忆序列
        - 新皮层接收并整合为长期知识
        - 海马体释放容量以接收新记忆

        Args:
            batch_size: 批量大小 (默认50条)
            similarity_threshold: 相似度阈值 (默认0.7)

        Returns:
            {
                'consolidated_clusters': int,
                'total_memories_processed': int,
                'clusters': List[Dict]
            }
        """

        if not self.temporal_lobe:
            return {
                'consolidated_clusters': 0,
                'message': 'TemporalLobe not connected'
            }

        if len(self.memories) < batch_size:
            return {
                'consolidated_clusters': 0,
                'message': f'Not enough memories for consolidation (current={len(self.memories)}, required={batch_size})'
            }

        # Step 1: 取最后batch_size条记忆
        batch_memories = self.memories[-batch_size:]

        # Step 2: 聚类相似记忆
        clusters = await self._cluster_memories_by_topic(
            memories=batch_memories,
            similarity_threshold=similarity_threshold
        )

        consolidated_count = 0
        cluster_details = []

        # Step 3: 对每个cluster提取语义知识
        for cluster_id, cluster_mems in clusters.items():
            if len(cluster_mems) < 2:
                continue  # 跳过单个记忆的cluster

            # 提取语义知识
            semantic_knowledge = await self._extract_semantic_knowledge(cluster_mems)

            # 存储到TemporalLobe
            try:
                await self.temporal_lobe.process_message(AgentMessage(
                    sender='hippocampus',
                    receiver='temporal_lobe',
                    message_type='request',
                    content={
                        'action': 'store_semantic',
                        'content': semantic_knowledge['summary'],
                        'memory_subtype': 'consolidated_cluster',
                        'entities': semantic_knowledge['entities'],
                        'relations': semantic_knowledge['relations'],
                        'importance': 0.8,
                        'metadata': {
                            'consolidated_from': [m.id for m in cluster_mems],
                            'cluster_id': cluster_id,
                            'consolidation_time': datetime.now().isoformat(),
                            'cluster_topic': semantic_knowledge.get('topic', 'unknown')
                        }
                    }
                ))

                consolidated_count += 1
                cluster_details.append({
                    'cluster_id': cluster_id,
                    'memory_count': len(cluster_mems),
                    'topic': semantic_knowledge.get('topic', 'unknown'),
                    'entities': semantic_knowledge['entities']
                })


            except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                logger.error(f"Failed to consolidate cluster {cluster_id}: {e}")

        self.total_consolidated += consolidated_count

        return {
            'consolidated_clusters': consolidated_count,
            'total_memories_processed': len(batch_memories),
            'clusters': cluster_details,
            'total_consolidated': self.total_consolidated
        }

    async def _cluster_memories_by_topic(
        self,
        memories: List[EpisodicMemory],
        similarity_threshold: float = 0.7
    ) -> Dict[str, List[EpisodicMemory]]:
        """
        按主题聚类记忆 (Topic Clustering)

        使用简单的贪婪聚类算法:
        1. 按时间顺序遍历记忆
        2. 如果与当前cluster相似度 > threshold,加入
        3. 否则创建新cluster

        Args:
            memories: 记忆列表
            similarity_threshold: 相似度阈值

        Returns:
            {cluster_id: [EpisodicMemory, ...]}
        """

        if not memories:
            return {}

        clusters: Dict[str, List[EpisodicMemory]] = {}
        current_cluster_id = None
        current_cluster_embedding = None

        for mem in memories:
            if not mem.embedding:
                # 没有embedding的记忆单独成cluster
                single_cluster_id = f"cluster_{mem.id[:8]}"
                clusters[single_cluster_id] = [mem]
                continue

            # 如果是第一个记忆,创建第一个cluster
            if current_cluster_id is None:
                current_cluster_id = f"cluster_{len(clusters)}"
                clusters[current_cluster_id] = [mem]
                current_cluster_embedding = mem.embedding
                continue

            # 计算与当前cluster的相似度
            similarity = self._cosine_similarity(mem.embedding, current_cluster_embedding)

            if similarity >= similarity_threshold:
                # 加入当前cluster
                clusters[current_cluster_id].append(mem)
                # 更新cluster embedding (平均)
                current_cluster_embedding = self._average_embeddings(
                    [m.embedding for m in clusters[current_cluster_id] if m.embedding]
                )
            else:
                # 创建新cluster
                current_cluster_id = f"cluster_{len(clusters)}"
                clusters[current_cluster_id] = [mem]
                current_cluster_embedding = mem.embedding

        return clusters

    def _average_embeddings(self, embeddings: List[List[float]]) -> List[float]:
        """计算embedding的平均值"""
        import numpy as np

        if not embeddings:
            return []

        arr = np.array(embeddings)
        avg = np.mean(arr, axis=0)
        return avg.tolist()

    async def _extract_semantic_knowledge(
        self,
        cluster_memories: List[EpisodicMemory]
    ) -> Dict[str, Any]:
        """
        从记忆cluster中提取语义知识

        使用LLM提取:
        1. 主题 (topic)
        2. 核心事实 (core facts)
        3. 实体关系 (entity relations)
        4. 摘要 (summary)

        Args:
            cluster_memories: 聚类的记忆列表

        Returns:
            {
                'topic': str,
                'summary': str,
                'entities': List[str],
                'relations': List[tuple]
            }
        """

        # 合并记忆内容
        combined_content = "\n".join([
            f"[{m.timestamp.strftime('%H:%M')}] {m.speaker or 'Unknown'}: {m.content}"
            for m in cluster_memories
        ])

        # 收集所有实体
        all_entities = list(set(sum([m.entities for m in cluster_memories], [])))

        # 使用LLM提取语义知识
        prompt = f"""从以下{len(cluster_memories)}条情节记忆中提取核心语义知识:

{combined_content}

请提取:
1. **主题**: 这些记忆的共同主题 (1-5个词)
2. **核心事实**: 最重要的3-5个事实
3. **实体关系**: 实体之间的关系 (如果有)
4. **摘要**: 简洁的总结 (2-3句话)

以JSON格式输出:
{{
  "topic": "主题",
  "core_facts": ["事实1", "事实2", ...],
  "relations": [["实体1", "关系", "实体2"], ...],
  "summary": "摘要"
}}

只输出JSON,不要其他文字。"""

        try:
            result = await self.call_llm(
                prompt=prompt,
                max_tokens=800,
                temperature=0.3
            )

            # 解析JSON
            import json
            import re
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())

                return {
                    'topic': parsed.get('topic', 'unknown'),
                    'summary': parsed.get('summary', combined_content[:200]),
                    'entities': all_entities,
                    'relations': [tuple(r) for r in parsed.get('relations', [])]
                }
            else:
                raise ValueError("No JSON found in LLM response")

        except (json.JSONDecodeError) as e:
            logger.warning(f"Failed to extract semantic knowledge via LLM: {e}")
            # Fallback
            return {
                'topic': 'consolidated_memories',
                'summary': f"Consolidated {len(cluster_memories)} memories",
                'entities': all_entities,
                'relations': []
            }

    # ============================================================================
    # Phase 1: Temporal Reasoning (时间推理检索)
    # ============================================================================

    async def search_with_temporal_reasoning(
        self,
        query: str,
        k: int = 10
    ) -> Dict[str, Any]:
        """
        带时间推理的记忆检索 - 解决Q1失败问题

        问题场景:
        - Q1: "Caroline什么时候参加LGBTQ支持群?"
        - 期望: 7 May 2023
        - 实际: 15 March 2023 (错误)

        原因: 时间索引不够智能,无法区分多个候选时间

        解决方案: LLM时间推理
        1. 提取查询中的时间线索
        2. 检索所有相关记忆
        3. LLM分析每个记忆的时间相关性
        4. 选择最匹配的时间

        神经科学依据:
        - 海马体时间细胞 (Time Cells) - MacDonald et al., 2011
        - 不是简单的时间索引,而是时序推理能力

        Args:
            query: 查询文本 (通常包含时间线索)
            k: 返回数量

        Returns:
            {
                'memories': List[Dict],  # 按时间相关性排序
                'temporal_analysis': str,  # LLM的时间推理过程
                'most_relevant_time': str,  # 最相关的时间
                'count': int
            }
        """

        # Step 1: LLM提取时间线索
        temporal_cues = await self._extract_temporal_cues(query)

        # Step 2: 基于线索检索候选记忆
        candidates = await self._retrieve_temporal_candidates(query, temporal_cues)

        if not candidates:
            return {
                'memories': [],
                'temporal_analysis': 'No relevant memories found',
                'most_relevant_time': None,
                'count': 0
            }

        # Step 3: LLM时间推理 - 分析每个候选的时间相关性
        ranked_results = await self._rank_by_temporal_relevance(
            query=query,
            candidates=candidates,
            temporal_cues=temporal_cues
        )

        # 限制返回数量
        top_results = ranked_results[:k]

        # 提取最相关的时间
        most_relevant_time = None
        if top_results:
            most_relevant_time = top_results[0]['memory'].timestamp.isoformat()

        return {
            'memories': [self._memory_to_dict(r['memory']) for r in top_results],
            'temporal_analysis': ranked_results[0].get('reasoning', '') if ranked_results else '',
            'most_relevant_time': most_relevant_time,
            'count': len(top_results)
        }

    async def _extract_temporal_cues(self, query: str) -> Dict[str, Any]:
        """
        提取时间线索 - LLM分析查询中的时间信息

        不使用硬编码时间词表,而是LLM理解语义
        """

        cue_prompt = f"""分析以下查询中的时间线索:

查询: "{query}"

提取:
1. **显式时间**: 明确的日期/时间 (如"2023年5月", "上周")
2. **隐式时间**: 暗示的时序 (如"第一次", "最早", "最近")
3. **时间关系**: 相对时间 (如"之前", "之后")
4. **时序事件**: 涉及时间顺序的事件 (如"开始", "参加")

返回JSON:
{{
    "explicit_time": "显式时间表达 (如果有)",
    "implicit_cues": ["隐式线索1", "隐式线索2"],
    "time_relation": "before/after/during/none",
    "temporal_event": "时序事件描述",
    "is_temporal_query": true/false
}}

只输出JSON,不要其他文字。"""

        try:
            response = await self.call_llm(cue_prompt, max_tokens=200, temperature=0.3)

            import json
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                cues = json.loads(json_match.group())
                return cues
            else:
                return {'is_temporal_query': False}

        except (json.JSONDecodeError) as e:
            logger.warning(f"Temporal cue extraction failed: {e}")
            return {'is_temporal_query': False}

    async def _retrieve_temporal_candidates(
        self,
        query: str,
        temporal_cues: Dict
    ) -> List[EpisodicMemory]:
        """
        检索时间相关的候选记忆

        策略: 混合检索 (语义 + 时间索引)
        """

        # 策略1: 如果有显式时间,使用时间索引
        if temporal_cues.get('explicit_time'):
            # TODO: 解析显式时间并使用time_index
            # 目前简化为全文检索
            pass

        # 策略2: 语义检索 (获取相关记忆)
        search_result = await self.search_memories(query=query, k=50)  # 扩大候选集
        candidates = []

        for mem_dict in search_result['memories']:
            mem = self.memory_dict.get(mem_dict['id'])
            if mem:
                candidates.append(mem)

        return candidates

    async def _rank_by_temporal_relevance(
        self,
        query: str,
        candidates: List[EpisodicMemory],
        temporal_cues: Dict
    ) -> List[Dict[str, Any]]:
        """
        LLM时间推理 - 排序候选记忆的时间相关性

        关键创新: 不是简单的时间匹配,而是理解查询意图

        例如:
        - "第一次参加" → 选择最早的时间
        - "最近参加" → 选择最晚的时间
        - "什么时候参加LGBTQ" → 选择与LGBTQ最相关的时间
        """

        # 构建候选记忆摘要
        candidates_summary = []
        for i, mem in enumerate(candidates[:10]):  # 限制分析数量,避免token过多
            candidates_summary.append({
                'index': i,
                'content': mem.content[:150],  # 截断内容
                'timestamp': mem.timestamp.isoformat(),
                'entities': mem.entities
            })

        import json

        ranking_prompt = f"""你是海马体的时间推理模块。分析查询的时间意图,并排序候选记忆。

查询: "{query}"

时间线索:
{json.dumps(temporal_cues, indent=2, ensure_ascii=False)}

候选记忆 (按索引):
{json.dumps(candidates_summary, indent=2, ensure_ascii=False)}

请进行时间推理:
1. 理解查询的时间意图 (第一次? 最近? 特定时间?)
2. 分析每个候选记忆与时间意图的匹配度
3. 选出最符合时间意图的记忆

返回JSON (按相关性排序):
{{
    "reasoning": "时间推理过程",
    "ranked_indices": [index1, index2, index3, ...],
    "most_relevant_index": index,
    "most_relevant_reason": "为什么这个时间最相关"
}}

只输出JSON,不要其他文字。"""

        try:
            response = await self.call_llm(ranking_prompt, max_tokens=400, temperature=0.3)

            import json
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                ranking = json.loads(json_match.group())

                # 按LLM排序重新组织候选
                ranked_results = []
                for idx in ranking.get('ranked_indices', [])[:10]:
                    if 0 <= idx < len(candidates):
                        ranked_results.append({
                            'memory': candidates[idx],
                            'reasoning': ranking.get('reasoning', ''),
                            'temporal_relevance': 1.0 if idx == ranking.get('most_relevant_index') else 0.5
                        })

                # 如果LLM排序失败,返回原始候选
                if not ranked_results:
                    ranked_results = [{'memory': mem, 'reasoning': '', 'temporal_relevance': 0.5} for mem in candidates]

                return ranked_results

        except (json.JSONDecodeError) as e:
            logger.warning(f"Temporal ranking failed: {e}, using fallback")

        # Fallback: 按时间戳排序 (如果有"最早""第一次"等线索)
        implicit_cues = temporal_cues.get('implicit_cues', [])
        if any(cue in ['第一次', '最早', 'first', 'earliest'] for cue in implicit_cues):
            # 按时间升序
            sorted_candidates = sorted(candidates, key=lambda m: m.timestamp)
        elif any(cue in ['最近', '最后', 'recent', 'latest', 'last'] for cue in implicit_cues):
            # 按时间降序
            sorted_candidates = sorted(candidates, key=lambda m: m.timestamp, reverse=True)
        else:
            # 默认按relevance (已在search_memories中排序)
            sorted_candidates = candidates

        return [{'memory': mem, 'reasoning': 'fallback_temporal_sort', 'temporal_relevance': 0.5} for mem in sorted_candidates]

    # ============================================================================
    # Phase 1: Entity-Action Binding (实体-动作绑定检索)
    # ============================================================================

    async def search_with_entity_action_binding(
        self,
        query: str,
        k: int = 10
    ) -> Dict[str, Any]:
        """
        实体-动作绑定检索 - 解决Q3失败问题

        问题场景:
        - Q3: "Caroline研究什么?"
        - 期望: adoption
        - 实际: 气候变化 (错误 - 混淆了不同实体的动作)

        原因: 纯语义检索无法区分:
        - "Caroline研究adoption"
        - "他人研究气候变化"

        解决方案: Entity-Action Binding
        1. LLM提取查询中的 (entity, action)
        2. 检索记忆中的 (entity, action) 绑定
        3. 优先返回精确匹配的记忆

        神经科学依据:
        - 海马体的关系编码 (Relational Encoding)
        - 不仅记住"什么",还记住"谁做了什么"

        文献: Ranganath & Ritchey (2012) "Two cortical systems for memory-guided behaviour"

        Args:
            query: 查询文本 (通常包含实体和动作)
            k: 返回数量

        Returns:
            {
                'memories': List[Dict],  # 按entity-action匹配度排序
                'entity_action_analysis': str,  # LLM的分析过程
                'extracted_entity': str,
                'extracted_action': str,
                'count': int
            }
        """

        # Step 1: LLM提取实体和动作
        entity_action = await self._extract_entity_action(query)

        if not entity_action.get('entity') and not entity_action.get('action'):
            # 如果无法提取entity/action,回退到普通检索
            search_result = await self.search_memories(query=query, k=k)
            return {
                'memories': search_result['memories'],
                'entity_action_analysis': 'No entity/action found, fallback to semantic search',
                'extracted_entity': None,
                'extracted_action': None,
                'count': search_result['count']
            }

        # Step 2: 检索候选记忆 (混合检索: 语义 + 实体索引)
        candidates = await self._retrieve_entity_action_candidates(
            entity=entity_action.get('entity'),
            action=entity_action.get('action'),
            query=query
        )

        if not candidates:
            return {
                'memories': [],
                'entity_action_analysis': f"No memories found for entity='{entity_action.get('entity')}' action='{entity_action.get('action')}'",
                'extracted_entity': entity_action.get('entity'),
                'extracted_action': entity_action.get('action'),
                'count': 0
            }

        # Step 3: LLM排序 - 根据entity-action绑定的精确度
        ranked_results = await self._rank_by_entity_action_binding(
            query=query,
            candidates=candidates,
            entity=entity_action.get('entity'),
            action=entity_action.get('action')
        )

        # 限制返回数量
        top_results = ranked_results[:k]

        return {
            'memories': [self._memory_to_dict(r['memory']) for r in top_results],
            'entity_action_analysis': ranked_results[0].get('reasoning', '') if ranked_results else '',
            'extracted_entity': entity_action.get('entity'),
            'extracted_action': entity_action.get('action'),
            'count': len(top_results)
        }

    async def _extract_entity_action(self, query: str) -> Dict[str, Any]:
        """
        LLM提取实体和动作 - 无硬编码动词列表

        理解查询的深层语义:
        - "Caroline研究什么?" → entity=Caroline, action=研究
        - "谁参加了LGBTQ活动?" → entity=None, action=参加
        - "Alice买了什么?" → entity=Alice, action=买
        """

        extraction_prompt = f"""分析以下查询,提取实体和动作:

查询: "{query}"

提取:
1. **实体** (Entity): 主要涉及的人物/组织 (如果有)
   - 例如: "Caroline", "Alice", "Bob"
   - 如果查询是"谁...",则entity=None

2. **动作** (Action): 关键的动作/行为 (如果有)
   - 例如: "研究", "参加", "买", "讨论"
   - 不要只匹配动词,要理解语义 ("关注"等隐含动作也算)

3. **对象** (Object): 动作的对象 (如果查询在问这个)
   - 例如: "研究什么?" → object=unknown (需要查询)
   - 例如: "参加LGBTQ活动" → object=LGBTQ活动

返回JSON:
{{
    "entity": "实体名称或null",
    "action": "动作或null",
    "object": "对象或unknown",
    "query_intent": "查询意图描述"
}}

只输出JSON,不要其他文字。"""

        try:
            response = await self.call_llm(extraction_prompt, max_tokens=200, temperature=0.3)

            import json
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                return {}

        except (json.JSONDecodeError) as e:
            logger.warning(f"Entity-action extraction failed: {e}")
            return {}

    async def _retrieve_entity_action_candidates(
        self,
        entity: Optional[str],
        action: Optional[str],
        query: str
    ) -> List[EpisodicMemory]:
        """
        检索entity-action候选记忆

        策略:
        1. 如果有entity,优先使用entity_index
        2. 结合语义检索扩大候选集
        """

        candidates = []

        # 策略1: 实体索引检索
        if entity and entity in self.entity_index:
            memory_ids = self.entity_index[entity]
            candidates = [self.memory_dict[mid] for mid in memory_ids if mid in self.memory_dict]

        # 策略2: 语义检索 (扩大候选集)
        search_result = await self.search_memories(query=query, k=50)
        semantic_candidates = []
        for mem_dict in search_result['memories']:
            mem = self.memory_dict.get(mem_dict['id'])
            if mem and mem not in candidates:
                semantic_candidates.append(mem)

        # 合并候选 (entity_index优先 + semantic补充)
        candidates.extend(semantic_candidates)


        return candidates

    async def _rank_by_entity_action_binding(
        self,
        query: str,
        candidates: List[EpisodicMemory],
        entity: Optional[str],
        action: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        LLM排序 - 根据entity-action绑定的精确度

        关键: 区分
        - "Caroline研究adoption" (精确匹配)
        - "他人研究气候变化" (entity不匹配)
        - "Caroline浏览adoption" (action相似但不精确)
        """

        # 构建候选记忆摘要
        candidates_summary = []
        for i, mem in enumerate(candidates[:15]):  # 限制分析数量
            candidates_summary.append({
                'index': i,
                'content': mem.content,
                'entities': mem.entities,
                'timestamp': mem.timestamp.isoformat()
            })

        import json

        ranking_prompt = f"""你是海马体的关系编码模块。分析查询的entity-action意图,并排序候选记忆。

查询: "{query}"

提取的实体-动作:
- Entity: {entity or 'None'}
- Action: {action or 'None'}

候选记忆 (按索引):
{json.dumps(candidates_summary, indent=2, ensure_ascii=False)}

请进行关系推理:
1. 判断每个候选记忆是否包含 **精确的entity-action绑定**
2. 优先选择 "实体X执行动作Y" 的记忆
3. 区分不同实体执行相似动作的记忆
4. 如果查询问"对象"(如"研究什么"),提取对应的对象

返回JSON (按entity-action匹配度排序):
{{
    "reasoning": "关系推理过程",
    "ranked_indices": [index1, index2, index3, ...],
    "best_match_index": index,
    "best_match_reason": "为什么这个记忆最匹配",
    "extracted_object": "如果查询问对象,提取的对象"
}}

只输出JSON,不要其他文字。"""

        try:
            response = await self.call_llm(ranking_prompt, max_tokens=500, temperature=0.3)

            import json
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                ranking = json.loads(json_match.group())

                # 按LLM排序重新组织候选
                ranked_results = []
                for idx in ranking.get('ranked_indices', [])[:15]:
                    if 0 <= idx < len(candidates):
                        ranked_results.append({
                            'memory': candidates[idx],
                            'reasoning': ranking.get('reasoning', ''),
                            'binding_score': 1.0 if idx == ranking.get('best_match_index') else 0.5
                        })

                # 如果LLM排序失败,使用简单启发式
                if not ranked_results:
                    ranked_results = self._fallback_entity_action_ranking(candidates, entity, action)

                return ranked_results

        except (json.JSONDecodeError) as e:
            logger.warning(f"Entity-action ranking failed: {e}, using fallback")
            return self._fallback_entity_action_ranking(candidates, entity, action)

    def _fallback_entity_action_ranking(
        self,
        candidates: List[EpisodicMemory],
        entity: Optional[str],
        action: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Fallback排序 - 算法约束 (非硬编码)

        算法:
        1. 如果有entity,优先选择entities中包含该entity的记忆
        2. 如果有action,优先选择content中包含action的记忆
        3. 按importance降序
        """

        scored_candidates = []

        for mem in candidates:
            score = 0.0

            # 实体匹配 (权重0.6)
            if entity and entity in mem.entities:
                score += 0.6

            # 动作匹配 (权重0.3) - 简单关键词匹配
            if action and action in mem.content:
                score += 0.3

            # 重要性 (权重0.1)
            score += mem.importance * 0.1

            scored_candidates.append({
                'memory': mem,
                'reasoning': f'fallback_score={score:.2f}',
                'binding_score': score
            })

        # 按score降序排序
        scored_candidates.sort(key=lambda x: x['binding_score'], reverse=True)

        return scored_candidates

    # ============================================================================
    # Phase 2: 高级双向反馈 (Advanced Bidirectional Feedback)
    # ============================================================================

    async def refine_search_with_feedback(
        self,
        query: str,
        initial_results: List[Dict],
        feedback: Dict[str, Any]
    ) -> List[Dict]:
        """
        Phase 2核心功能: 高级双向反馈检索精化

        理论依据:
        - Norman & O'Reilly (2003) - 前额叶控制海马体检索策略
        - Ranganath & Ritchey (2012) - 海马体-皮层双向交互

        问题场景:
        当前双向反馈实现过于简单 (reasoning_validator.py line 595-610):
        - 只能用refined_query重新检索
        - 无法传递详细反馈信息 (时间范围、实体过滤、情绪过滤等)

        Phase 2增强:
        - 支持多维度反馈 (时间、实体、情绪、重要性)
        - 算法化过滤 (非硬编码)
        - 补充缺失维度

        Args:
            query: 原始查询
            initial_results: 初次检索结果 (List[Dict] from search_memories)
            feedback: 推理层反馈
                {
                    'missing_aspects': ['时间信息不足', '缺少情绪细节'],
                    'irrelevant_ids': ['mem123', 'mem456'],
                    'preferred_time_range': ('2023-03-01', '2023-05-01'),
                    'preferred_entities': ['Caroline', 'LGBTQ'],
                    'min_importance': 0.5,
                    'min_emotion_intensity': 0.6
                }

        Returns:
            精化后的记忆列表 (List[Dict])
        """


        # Step 1: 转换initial_results为EpisodicMemory对象
        initial_memories = []
        for result_dict in initial_results:
            mem_id = result_dict.get('id')
            if mem_id and mem_id in self.memory_dict:
                initial_memories.append(self.memory_dict[mem_id])

        if not initial_memories:
            logger.warning("⚠️ No valid initial memories found, cannot refine")
            return []

        refined = initial_memories.copy()

        # Step 2: 过滤不相关记忆
        irrelevant_ids = set(feedback.get('irrelevant_ids', []))
        if irrelevant_ids:
            refined = [m for m in refined if m.id not in irrelevant_ids]

        # Step 3: 时间过滤 (算法: 时间范围约束)
        if 'preferred_time_range' in feedback:
            time_range = feedback['preferred_time_range']
            if isinstance(time_range, tuple) and len(time_range) == 2:
                start_str, end_str = time_range
                start_time = datetime.fromisoformat(start_str) if isinstance(start_str, str) else start_str
                end_time = datetime.fromisoformat(end_str) if isinstance(end_str, str) else end_str

                before_count = len(refined)
                refined = [
                    m for m in refined
                    if start_time <= m.timestamp <= end_time
                ]

        # Step 4: 实体过滤 (算法: 实体集合交集)
        if 'preferred_entities' in feedback:
            preferred_entities = set(feedback['preferred_entities'])
            before_count = len(refined)
            refined = [
                m for m in refined
                if any(e in preferred_entities for e in m.entities)
            ]

        # Step 5: 重要性过滤 (算法: 阈值约束)
        if 'min_importance' in feedback:
            min_imp = feedback['min_importance']
            before_count = len(refined)
            refined = [m for m in refined if m.importance >= min_imp]

        # Step 6: 情绪过滤 (算法: 情绪强度阈值)
        if 'min_emotion_intensity' in feedback:
            min_emo = feedback['min_emotion_intensity']
            before_count = len(refined)
            refined = [m for m in refined if m.emotion_intensity >= min_emo]

        # Step 7: 补充缺失维度 (如果过滤后数量不足)
        if len(refined) < 5 and 'missing_aspects' in feedback:

            for aspect in feedback['missing_aspects']:
                # 根据aspect构建新查询
                supplementary_query = f"{query} {aspect}"

                # 构建搜索参数
                search_kwargs = {'query': supplementary_query, 'k': 10}

                # 应用feedback中的过滤器
                if 'preferred_entities' in feedback:
                    search_kwargs['entities'] = feedback['preferred_entities']
                if 'preferred_time_range' in feedback:
                    start_str, end_str = feedback['preferred_time_range']
                    search_kwargs['time_range'] = {
                        'start': start_str if isinstance(start_str, str) else start_str.isoformat(),
                        'end': end_str if isinstance(end_str, str) else end_str.isoformat()
                    }

                # 执行补充检索
                additional_result = await self.search_memories(**search_kwargs)

                # 转换为EpisodicMemory并去重
                existing_ids = {m.id for m in refined}
                new_memories = []
                for mem_dict in additional_result['memories']:
                    mem_id = mem_dict.get('id')
                    if mem_id and mem_id in self.memory_dict and mem_id not in existing_ids:
                        mem = self.memory_dict[mem_id]

                        # 应用重要性/情绪过滤
                        if 'min_importance' in feedback and mem.importance < feedback['min_importance']:
                            continue
                        if 'min_emotion_intensity' in feedback and mem.emotion_intensity < feedback['min_emotion_intensity']:
                            continue

                        new_memories.append(mem)
                        existing_ids.add(mem_id)

                refined.extend(new_memories)


        # 转换回字典格式返回
        return [self._memory_to_dict(m) for m in refined]

    async def retrieve_memory_by_id(self, memory_id: str) -> Dict[str, Any]:
        """
        Phase 2辅助功能: 根据ID检索单个记忆

        用途: 支持TemporalLobe的反向溯源 (语义记忆 → 源情节记忆)

        Args:
            memory_id: 记忆ID

        Returns:
            记忆字典 (如果找到) 或 None
        """
        if memory_id in self.memory_dict:
            mem = self.memory_dict[memory_id]
            mem.access_count += 1
            mem.last_accessed = datetime.now()
            return self._memory_to_dict(mem)
        else:
            logger.warning(f"⚠️ Memory not found: {memory_id}")
            return None

    # ============================================================================
    # Consolidation Interface Methods (for BrainCoordinator)
    # ============================================================================

    async def get_consolidation_candidates(
        self,
        min_access_count: int = 3,
        min_age_hours: float = 24,
        max_count: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取待巩固的情节记忆候选

        用于协调层的巩固流程:
        - 被访问多次的重要记忆
        - 存在超过一定时间的记忆
        - 未被标记为已巩固的记忆

        Args:
            min_access_count: 最小访问次数 (默认3次)
            min_age_hours: 最小存在时间(小时) (默认24小时)
            max_count: 最大返回数量 (默认50)

        Returns:
            候选记忆列表 (字典格式)
        """
        now = datetime.now()
        candidates = []

        for mem in self.memories:
            # 检查是否满足巩固条件
            age_hours = (now - mem.timestamp).total_seconds() / 3600

            # 条件1: 访问次数足够
            if mem.access_count < min_access_count:
                continue

            # 条件2: 存在时间足够
            if age_hours < min_age_hours:
                continue

            # 条件3: 未被标记为已巩固
            if mem.metadata.get('consolidated', False):
                continue

            # 条件4: 重要性或情绪强度足够
            if mem.importance < 0.5 and mem.emotion_intensity < 0.6:
                continue

            candidates.append(self._memory_to_dict(mem))

        # 按重要性和访问次数排序
        candidates.sort(
            key=lambda m: (m['importance'], m['access_count']),
            reverse=True
        )

        # 限制返回数量
        candidates = candidates[:max_count]

        # 🎯 P2优化: 增强日志显示阈值信息
        if min_age_hours < 1:
            age_display = f"{min_age_hours * 60:.1f}min"
        else:
            age_display = f"{min_age_hours}h"

        logger.info(f"Forgetting candidates found: {len(candidates)} memories "
                   f"(min_access={min_access_count}, min_age={age_display})")

        return candidates

    async def mark_as_consolidated(
        self,
        episode_ids: List[str],
        semantic_id: str
    ) -> int:
        """
        标记情节记忆为已巩固

        在协调层成功巩固后调用，防止重复巩固

        Args:
            episode_ids: 情节记忆ID列表
            semantic_id: 对应的语义记忆ID

        Returns:
            标记的记忆数量
        """
        marked_count = 0

        for episode_id in episode_ids:
            if episode_id in self.memory_dict:
                mem = self.memory_dict[episode_id]
                mem.metadata['consolidated'] = True
                mem.metadata['semantic_id'] = semantic_id
                mem.metadata['consolidation_time'] = datetime.now().isoformat()
                marked_count += 1

                logger.debug(f"Marked {episode_id[:8]} consolidated "
                   f"(semantic_id={semantic_id[:8]})")

        return marked_count

    # ============================================================================
    # Forgetting Interface Methods (for BrainCoordinator)
    # ============================================================================

    async def get_forgetting_candidates(
        self,
        bottom_percentile: float = 0.2
    ) -> List[Dict[str, Any]]:
        """
        获取遗忘候选记忆

        用于协调层的遗忘流程:
        - 返回重要性和访问频率最低的记忆
        - 由ForgettingAgent评估是否真正遗忘

        Args:
            bottom_percentile: 底部百分比 (默认0.2 = 20%)

        Returns:
            候选记忆列表 (字典格式)
        """
        if not self.memories:
            return []

        # 按重要性、访问次数、时间排序
        sorted_memories = sorted(
            self.memories,
            key=lambda m: (m.importance, m.access_count, m.timestamp),
            reverse=False  # 升序 - 最低价值的在前
        )

        # 取底部百分比
        candidate_count = max(1, int(len(sorted_memories) * bottom_percentile))
        candidates = sorted_memories[:candidate_count]

        logger.info(f"Low-access memory candidates: {len(candidates)} memories "
                   f"(bottom {bottom_percentile*100:.0f}%)")

        return [self._memory_to_dict(mem) for mem in candidates]

    async def forget_memories(self, memory_ids: List[str]) -> int:
        """
        执行记忆遗忘

        由协调层在ForgettingAgent评估后调用

        Args:
            memory_ids: 要遗忘的记忆ID列表

        Returns:
            实际遗忘的记忆数量
        """
        forgotten_count = 0
        forgotten_ids = set(memory_ids)

        # 从列表中移除
        self.memories = [m for m in self.memories if m.id not in forgotten_ids]

        # 从字典中移除
        for mem_id in memory_ids:
            if mem_id in self.memory_dict:
                del self.memory_dict[mem_id]
                forgotten_count += 1

        # 重建索引
        self._rebuild_indexes()

        self.total_forgotten += forgotten_count


        return forgotten_count
