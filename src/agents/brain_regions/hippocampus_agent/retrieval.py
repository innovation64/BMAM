"""
Hippocampus Agent - 海马体智能体
对应脑区: 海马体 (Hippocampus)
主要功能: 情节记忆存储+检索+巩固

优化更新 (2025-11-30):
- 集成实体感知检索 (Entity-Aware Retrieval)
- 自动从查询中提取实体
- 实体匹配权重提升
- 集成Pattern Separation支持
"""

import logging
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)


from .core import EpisodicMemory, HippocampusAgentCore
import numpy as np


def extract_entities_from_query(query: str) -> List[str]:
    """
    从查询中提取实体 (简化版实体识别)

    提取规则:
    1. 首字母大写的词 (人名、地名)
    2. 常见人名模式
    3. 跳过句首大写和常见词

    Args:
        query: 查询文本

    Returns:
        提取的实体列表
    """
    if not query:
        return []

    entities = []

    # 跳过的常见词
    skip_words = {
        'when', 'what', 'where', 'who', 'why', 'how', 'did', 'does', 'do',
        'is', 'are', 'was', 'were', 'the', 'a', 'an', 'in', 'on', 'at',
        'to', 'for', 'of', 'with', 'about', 'this', 'that', 'it', 'i',
        'you', 'he', 'she', 'they', 'we', 'my', 'your', 'his', 'her',
        'their', 'our', 'would', 'could', 'should', 'will', 'can', 'may',
        'might', 'must', 'have', 'has', 'had', 'been', 'being', 'be'
    }

    # 分词并检查首字母大写
    words = query.split()
    for i, word in enumerate(words):
        # 清理标点
        clean_word = re.sub(r'[^\w]', '', word)

        if not clean_word:
            continue

        # 检查是否首字母大写且不是句首
        if clean_word[0].isupper() and clean_word.lower() not in skip_words:
            # 跳过句首词 (如果前一个词以句号/问号结尾或是第一个词)
            if i > 0:
                prev_word = words[i - 1]
                if not prev_word.endswith(('.', '?', '!')):
                    entities.append(clean_word)
            # 对于句首词，只在长度>2时考虑（避免I, A等）
            elif len(clean_word) > 2:
                # 检查是否是常见人名模式
                if clean_word not in skip_words:
                    entities.append(clean_word)

    return list(set(entities))


def extract_event_keywords(query: str) -> List[str]:
    """
    🧠 类脑增强: 从查询中提取事件关键词

    人脑检索不只依赖实体，还会基于事件类型检索：
    - 活动类: camping, speech, race, meeting, party
    - 计划类: planning, going to, will
    - 时间类: yesterday, last week, next month

    Args:
        query: 查询文本

    Returns:
        事件关键词列表
    """
    if not query:
        return []

    query_lower = query.lower()
    keywords = []

    # 活动/事件关键词 (通用词，不针对特定数据集)
    event_words = {
        # 活动类
        'camping', 'camp', 'speech', 'race', 'meeting', 'meet', 'party',
        'wedding', 'birthday', 'trip', 'vacation', 'travel', 'visit',
        'dinner', 'lunch', 'breakfast', 'concert', 'movie', 'show',
        'graduation', 'ceremony', 'interview', 'appointment', 'class',
        'workshop', 'conference', 'seminar', 'lecture', 'presentation',
        # 社交类
        'support group', 'lgbtq', 'charity', 'volunteer', 'mentors',
        'friends', 'family', 'colleagues', 'school', 'university',
        # 创作类
        'paint', 'painted', 'painting', 'sunrise', 'art', 'research',
        'researched', 'adopt', 'adoption', 'counseling', 'therapy',
        # 通用运动/娱乐
        'game', 'games', 'match', 'sport', 'sports', 'team', 'teams',
        'book', 'books', 'reading', 'club', 'hobby', 'hobbies',
        # 通用动作
        'start', 'started', 'begin', 'began', 'finish', 'finished',
        'return', 'returned', 'attend', 'attended', 'join', 'joined'
    }

    # 提取匹配的事件词
    words = re.findall(r'\b\w+\b', query_lower)
    for word in words:
        if word in event_words:
            keywords.append(word)

    # 提取动名词 (planning, going, running 等)
    gerunds = re.findall(r'\b\w+ing\b', query_lower)
    important_gerunds = {'planning', 'going', 'running', 'meeting', 'painting', 'camping'}
    for g in gerunds:
        if g in important_gerunds:
            keywords.append(g)

    return list(set(keywords))


class RetrievalMixin:
    """基本检索和搜索功能 - 优化版"""

    def _get_entity_match_score(
        self,
        query_entities: List[str],
        memory_entities: List[str]
    ) -> float:
        """
        计算实体匹配分数

        Args:
            query_entities: 查询中的实体
            memory_entities: 记忆中的实体

        Returns:
            匹配分数 (0-1)
        """
        if not query_entities or not memory_entities:
            return 0.0

        query_set = set(e.lower() for e in query_entities)
        memory_set = set(e.lower() for e in memory_entities)

        # 完全匹配
        exact_matches = query_set & memory_set
        if exact_matches:
            return len(exact_matches) / len(query_set)

        # 部分匹配 (子串)
        partial_score = 0.0
        for qe in query_set:
            for me in memory_set:
                if qe in me or me in qe:
                    partial_score += 0.5
                    break

        return min(1.0, partial_score / len(query_set))

    async def search_memories(
        self,
        query: str = None,
        entities: List[str] = None,
        time_range: Dict[str, str] = None,
        k: int = 10
    ) -> Dict[str, Any]:
        """
        搜索情节记忆 - 优化版

        优化点:
        1. 自动从查询中提取实体
        2. 实体匹配权重提升 (解决Caroline/Melanie混淆问题)
        3. 支持Pattern Separation辨别性特征

        Args:
            query: 查询文本
            entities: 实体过滤 (可选,会自动提取)
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

        # 🔥 新增: 自动提取查询中的实体
        query_entities = entities or []
        if query and not entities:
            auto_entities = extract_entities_from_query(query)
            if auto_entities:
                query_entities = auto_entities
                logger.debug(f"Auto-extracted entities from query: {query_entities}")

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

        # 初始化变量
        entity_filtered = False
        candidates = []

        # 🔥 策略1: 实体索引检索 (使用自动提取的实体)
        # 优化: 使用query_entities而不是entities参数
        if query_entities:
            candidate_ids = set()
            for entity in query_entities:
                # 尝试精确匹配
                candidate_ids.update(self.entity_index.get(entity, []))
                # 尝试小写匹配
                candidate_ids.update(self.entity_index.get(entity.lower(), []))

            if candidate_ids:
                candidates = [self.memory_dict[mid] for mid in candidate_ids if mid in self.memory_dict]
                entity_filtered = True
                logger.debug(f"Entity filter: {len(candidates)} candidates from entities {query_entities}")
            else:
                # 没找到精确匹配，使用全部记忆但后续会用实体分数排序
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

            # 🧠 类脑增强: 提取事件关键词
            event_keywords = extract_event_keywords(query)
            logger.debug(f"Event keywords extracted: {event_keywords}")

            for mem in candidates:
                # 1️⃣ 关键词相关性 (BM25-like + 事件关键词增强)
                content_lower = mem.content.lower()
                content_words = set(content_lower.split())
                overlap = len(query_words & content_words)
                keyword_score = overlap / len(query_words) if overlap > 0 else 0.1

                # 🧠 事件关键词增强: 如果记忆包含查询中的事件关键词，大幅提升分数
                event_match_count = 0
                for ek in event_keywords:
                    if ek in content_lower:
                        event_match_count += 1
                        logger.debug(f"Event keyword '{ek}' found in memory: {mem.content[:50]}...")

                if event_match_count > 0 and event_keywords:
                    # 事件关键词匹配可以大幅提升关键词分数
                    event_boost = min(0.5, event_match_count * 0.2)  # 每个匹配+0.2, 最多+0.5
                    keyword_score = min(1.0, keyword_score + event_boost)

                # 2️⃣ 语义相关性 (Cosine Similarity)
                semantic_score = 0.0
                if query_embedding and mem.embedding:
                    semantic_score = self._cosine_similarity(query_embedding, mem.embedding)

                # 🔥 新增: 实体匹配分数 (关键优化点!)
                # 解决Caroline/Melanie混淆问题
                entity_score = 0.0
                if query_entities:
                    # 获取记忆中的实体
                    mem_entities = []
                    if hasattr(mem, 'entities') and mem.entities:
                        mem_entities = mem.entities
                    elif mem.metadata and mem.metadata.get('entities'):
                        mem_entities = mem.metadata.get('entities', [])

                    # 计算实体匹配
                    entity_score = self._get_entity_match_score(query_entities, mem_entities)

                    # 如果没有实体索引匹配，也检查内容中是否包含实体
                    if entity_score == 0:
                        content_lower = mem.content.lower()
                        for qe in query_entities:
                            if qe.lower() in content_lower:
                                entity_score = max(entity_score, 0.8)
                                break

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

                # 🔥 优化后的混合分数计算
                # 调整权重: 实体匹配 > 关键词 > 语义 (解决人名混淆问题)
                # 原始: 0.3 * keyword + 0.5 * semantic
                # 优化: 0.35 * entity + 0.25 * keyword + 0.3 * semantic + kg_boost
                if query_embedding and mem.embedding:
                    if query_entities and entity_score > 0:
                        # 有实体匹配时，实体分数权重最高
                        relevance = 0.35 * entity_score + 0.25 * keyword_score + 0.3 * semantic_score + kg_boost
                    else:
                        # 无实体时，保持原有逻辑
                        relevance = 0.3 * keyword_score + 0.5 * semantic_score + kg_boost
                else:
                    if query_entities and entity_score > 0:
                        relevance = 0.5 * entity_score + 0.4 * keyword_score + kg_boost
                    else:
                        relevance = 0.7 * keyword_score + kg_boost  # Fallback to keyword + kg

                results.append({
                    'memory': mem,
                    'relevance': relevance,
                    'keyword_score': keyword_score,
                    'semantic_score': semantic_score,
                    'entity_score': entity_score,  # 🔥 新增: 实体匹配分数
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
            mem_dict['entity_score'] = r.get('entity_score', 0.0)  # 🔥 新增: 实体匹配分数
            mem_dict['kg_boost'] = r.get('kg_boost', 0.0)  # 🎯 P3: KG增强分数
            memories_with_scores.append(mem_dict)

        return {
            'memories': memories_with_scores,
            'count': len(results),
            'search_time_ms': search_time,
            'query_entities': query_entities,  # 🔥 新增: 返回提取的实体
            'entity_filtered': entity_filtered,  # 🔥 新增: 是否使用了实体过滤
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


