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
import numpy as np


class RetrievalMixin:
    """基本检索和搜索功能"""
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

        # 🔥 Phase 3: Try delegated retrieval if global storage is enabled
        if hasattr(self, 'storage_adapter') and self.storage_adapter.config.use_global_storage:
            try:
                # Build filters for global retrieval
                filters = {}
                if entities:
                    filters['entities'] = entities
                if time_range:
                    filters['time_range'] = (
                        datetime.fromisoformat(time_range.get('start', '1970-01-01')),
                        datetime.fromisoformat(time_range.get('end', '2100-01-01'))
                    )

                # Delegate to global system via adapter
                memory_dicts = await self.storage_adapter.retrieve_memories(
                    query=query,
                    filters=filters,
                    k=k
                )

                # Convert to EpisodicMemory objects and calculate relevance
                for mem_dict in memory_dicts:
                    # Update local cache
                    memory_id = mem_dict.get('id')
                    if memory_id and memory_id not in self.memory_dict:
                        # Reconstruct EpisodicMemory from dict
                        memory = self._dict_to_memory(mem_dict)
                        self.memory_dict[memory_id] = memory

                    results.append({
                        'memory': self.memory_dict.get(memory_id, self._dict_to_memory(mem_dict)),
                        'relevance': mem_dict.get('relevance', 1.0),
                        'keyword_score': mem_dict.get('keyword_score', 0.0),
                        'semantic_score': mem_dict.get('semantic_score', 0.0),
                        'kg_boost': mem_dict.get('kg_boost', 0.0),
                        'source': 'global_system'
                    })

                # Sort by relevance
                results.sort(key=lambda x: x['relevance'], reverse=True)

                search_time = (datetime.now() - start_time).total_seconds() * 1000
                return {
                    'memories': [self._memory_to_dict(r['memory']) for r in results[:k]],
                    'count': len(results),
                    'search_time_ms': search_time,
                    'source': 'global_delegated'
                }

            except Exception as e:
                logger.warning(f"Global retrieval failed, falling back to local: {e}")
                # Fall through to local retrieval

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


