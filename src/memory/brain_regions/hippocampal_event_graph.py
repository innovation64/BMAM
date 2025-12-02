"""
Hippocampal Event Graph - 海马体事件图

功能: 存储事件序列和时间关系
结构: 有向图 (DAG - Directed Acyclic Graph)
节点: Event (事件)
边: 时间顺序 (temporal links)

灵感来源:
- 海马体负责情节记忆 (episodic memory)
- 存储"what happened when where"
- 不是向量，是Graph结构

优化更新 (2025-11-30):
- 集成模式分离机制 (Pattern Separation)
- 相似事件自动标记辨别性特征
- 检索时利用辨别性特征提高准确性

基于论文: "Key-value memory in the brain" (Benna & Fusi, 2024)
"""

import uuid
import logging
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass, field

from ..pattern_separator import PatternSeparator, DiscriminativeFeatures

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """事件节点"""
    id: str
    content: str
    entities: List[str]  # ["PersonA", "GroupName"]
    timestamp: datetime
    next_events: List[str] = field(default_factory=list)  # 后续事件IDs
    prev_events: List[str] = field(default_factory=list)  # 之前事件IDs
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 模式分离相关字段 (2025-11-30新增)
    discriminative_entities: List[str] = field(default_factory=list)  # 辨别性实体
    discriminative_temporal: Optional[str] = None  # 辨别性时间特征
    separation_score: float = 1.0  # 分离程度 (0-1, 1表示完全独特)


class HippocampalEventGraph:
    """
    海马体事件图 - 存储事件序列

    核心特点:
    1. Graph结构，不是向量
    2. 支持时间顺序查询
    3. 支持实体相关事件查询
    4. O(1)复杂度的索引查询
    5. 模式分离 - 自动区分相似事件 (2025-11-30新增)

    神经科学类比:
    - 模拟海马体齿状回(DG)的模式分离功能
    - 相似输入 → 不同表征
    - 避免记忆混淆和干扰
    """

    def __init__(self, enable_pattern_separation: bool = True):
        # 核心存储
        self.events: Dict[str, Event] = {}  # {event_id: Event}

        # 索引结构 (快速查询)
        self.entity_index: Dict[str, List[str]] = defaultdict(list)  # {entity: [event_ids]}
        self.time_index: Dict[str, List[str]] = {}  # {date_str: [event_ids]}
        self.temporal_chain: List[str] = []  # 全局时间链 (按时间排序的event_ids)

        # 模式分离器 (2025-11-30新增)
        self.enable_pattern_separation = enable_pattern_separation
        if enable_pattern_separation:
            self.pattern_separator = PatternSeparator(
                similarity_threshold=0.7,
                min_separation_score=0.3
            )
        else:
            self.pattern_separator = None

        logger.info(f"HippocampalEventGraph initialized, pattern_separation={enable_pattern_separation}")


    def add_event(
        self,
        content: str,
        entities: List[str],
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict] = None,
        embedding: Optional[np.ndarray] = None
    ) -> str:
        """
        添加事件到图

        Args:
            content: 事件描述 "Person去了某个活动"
            entities: 实体列表 ["PersonA", "EventName"]
            timestamp: 时间戳
            metadata: 额外元数据
            embedding: 事件向量（用于模式分离）

        Returns:
            event_id
        """
        if timestamp is None:
            timestamp = datetime.now()

        event_id = f"event_{uuid.uuid4().hex[:8]}"

        # 创建事件节点
        event = Event(
            id=event_id,
            content=content,
            entities=entities,
            timestamp=timestamp,
            metadata=metadata or {}
        )

        # ========== 模式分离处理 (2025-11-30新增) ==========
        if self.enable_pattern_separation and self.pattern_separator:
            # 获取现有事件用于比较
            existing_memories = [
                {
                    'id': e.id,
                    'content': e.content,
                    'entities': e.entities,
                    'timestamp': e.timestamp,
                    'embedding': e.metadata.get('embedding')
                }
                for e in self.events.values()
            ]

            # 进行模式分离
            disc_features = self.pattern_separator.process_new_memory(
                memory_id=event_id,
                content=content,
                entities=entities,
                timestamp=timestamp,
                embedding=embedding,
                existing_memories=existing_memories
            )

            # 将辨别性特征存入事件
            event.discriminative_entities = disc_features.unique_entities
            event.discriminative_temporal = disc_features.unique_temporal
            event.separation_score = disc_features.separation_score

            # 同时更新metadata
            event.metadata['discriminative_features'] = disc_features.to_dict()

            if disc_features.separation_score < 0.3:
                logger.warning(
                    f"Low separation score for event {event_id}: {disc_features.separation_score:.2f}, "
                    f"similar to {disc_features.contrast_memory_ids}"
                )

        # 存储向量到metadata（如果提供）
        if embedding is not None:
            event.metadata['embedding'] = embedding

        # 存储事件
        self.events[event_id] = event

        # 建立实体索引
        for entity in entities:
            self.entity_index[entity].append(event_id)

        # 建立时间索引
        date_key = timestamp.strftime('%Y-%m-%d')
        if date_key not in self.time_index:
            self.time_index[date_key] = []
        self.time_index[date_key].append(event_id)

        # 维护全局时间链
        self._insert_into_temporal_chain(event_id, timestamp)

        # 链接时间顺序 (连接到最近的事件)
        self._link_temporal_neighbors(event_id, timestamp)

        logger.debug(
            f"Event added: {event_id}, entities={entities}, "
            f"separation_score={event.separation_score:.2f}"
        )

        return event_id

    def _insert_into_temporal_chain(self, event_id: str, timestamp: datetime):
        """
        将事件插入到全局时间链 (保持时间排序)

        使用二分查找插入 O(log n)
        """
        import bisect

        # 找到插入位置
        insertion_point = bisect.bisect_right(
            [self.events[eid].timestamp for eid in self.temporal_chain],
            timestamp
        )

        self.temporal_chain.insert(insertion_point, event_id)

    def _link_temporal_neighbors(self, event_id: str, timestamp: datetime):
        """
        链接事件的时间邻居 (prev/next)

        只链接时间上最近的事件 (不是全连接)
        """
        if event_id not in self.temporal_chain:
            return

        index = self.temporal_chain.index(event_id)

        # 链接前一个事件
        if index > 0:
            prev_id = self.temporal_chain[index - 1]
            self.events[event_id].prev_events.append(prev_id)
            self.events[prev_id].next_events.append(event_id)

        # 链接后一个事件 (如果有)
        if index < len(self.temporal_chain) - 1:
            next_id = self.temporal_chain[index + 1]
            self.events[event_id].next_events.append(next_id)
            self.events[next_id].prev_events.append(event_id)

    def get_events_by_entity(self, entity: str, limit: Optional[int] = None) -> List[Event]:
        """
        通过实体获取所有相关事件

        Args:
            entity: 实体名称 "PersonA"
            limit: 最多返回多少个事件

        Returns:
            事件列表 (按时间排序)
        """
        event_ids = self.entity_index.get(entity, [])

        if limit:
            event_ids = event_ids[:limit]

        events = [self.events[eid] for eid in event_ids if eid in self.events]

        # 按时间排序
        events.sort(key=lambda e: e.timestamp)


        return events

    def get_events_by_date(self, date: str) -> List[Event]:
        """
        获取某一天的所有事件

        Args:
            date: 日期字符串 "2023-05-07"

        Returns:
            事件列表
        """
        event_ids = self.time_index.get(date, [])
        events = [self.events[eid] for eid in event_ids if eid in self.events]


        return events

    def get_event_chain(
        self,
        start_event_id: str,
        direction: str = 'forward',
        depth: int = 3
    ) -> List[Event]:
        """
        获取事件链 (从某个事件开始的前/后事件)

        Args:
            start_event_id: 起始事件ID
            direction: 'forward' (后续) or 'backward' (之前)
            depth: 遍历深度

        Returns:
            事件链
        """
        if start_event_id not in self.events:
            return []

        chain = []
        visited = set()

        def dfs(event_id: str, current_depth: int):
            if current_depth > depth or event_id in visited:
                return
            visited.add(event_id)

            event = self.events.get(event_id)
            if not event:
                return

            chain.append(event)

            # 选择遍历方向
            neighbors = event.next_events if direction == 'forward' else event.prev_events

            for neighbor_id in neighbors:
                dfs(neighbor_id, current_depth + 1)

        dfs(start_event_id, 0)


        return chain

    def get_events_in_time_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Event]:
        """
        获取时间范围内的所有事件

        Args:
            start_date: 开始时间
            end_date: 结束时间

        Returns:
            事件列表
        """
        events = []

        for event in self.events.values():
            if start_date <= event.timestamp <= end_date:
                events.append(event)

        # 按时间排序
        events.sort(key=lambda e: e.timestamp)


        return events

    def get_all_entities(self) -> List[str]:
        """获取所有实体名称"""
        return list(self.entity_index.keys())

    def get_entity_cooccurrence(self, entity1: str, entity2: str) -> List[Event]:
        """
        获取两个实体共现的事件

        Args:
            entity1: 实体1
            entity2: 实体2

        Returns:
            包含两个实体的事件列表
        """
        events1 = set(self.entity_index.get(entity1, []))
        events2 = set(self.entity_index.get(entity2, []))

        common_event_ids = events1 & events2
        events = [self.events[eid] for eid in common_event_ids if eid in self.events]


        return events

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_events': len(self.events),
            'total_entities': len(self.entity_index),
            'date_range': (
                min(e.timestamp for e in self.events.values()),
                max(e.timestamp for e in self.events.values())
            ) if self.events else (None, None),
            'avg_entities_per_event': sum(len(e.entities) for e in self.events.values()) / len(self.events) if self.events else 0
        }

    def to_dict(self) -> Dict:
        """序列化为字典 (用于持久化)"""
        return {
            'events': {
                eid: {
                    'id': e.id,
                    'content': e.content,
                    'entities': e.entities,
                    'timestamp': e.timestamp.isoformat(),
                    'next_events': e.next_events,
                    'prev_events': e.prev_events,
                    'metadata': e.metadata
                }
                for eid, e in self.events.items()
            },
            'temporal_chain': self.temporal_chain
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'HippocampalEventGraph':
        """从字典反序列化"""
        graph = cls()

        # 恢复事件
        for eid, event_data in data.get('events', {}).items():
            event = Event(
                id=event_data['id'],
                content=event_data['content'],
                entities=event_data['entities'],
                timestamp=datetime.fromisoformat(event_data['timestamp']),
                next_events=event_data.get('next_events', []),
                prev_events=event_data.get('prev_events', []),
                metadata=event_data.get('metadata', {})
            )
            graph.events[eid] = event

            # 重建索引
            for entity in event.entities:
                graph.entity_index[entity].append(eid)

            date_key = event.timestamp.strftime('%Y-%m-%d')
            if date_key not in graph.time_index:
                graph.time_index[date_key] = []
            graph.time_index[date_key].append(eid)

        # 恢复时间链
        graph.temporal_chain = data.get('temporal_chain', [])

        # 恢复模式分离器状态
        if graph.enable_pattern_separation and graph.pattern_separator:
            for event in graph.events.values():
                if 'discriminative_features' in event.metadata:
                    # 重建模式分离器索引
                    for entity in event.entities:
                        graph.pattern_separator.entity_memory_index[entity].add(event.id)

        return graph

    # ========== 模式分离增强方法 (2025-11-30新增) ==========

    def get_events_by_entity_with_discrimination(
        self,
        entity: str,
        query_keywords: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[Tuple[Event, float]]:
        """
        通过实体获取事件，并使用辨别性特征增强排序

        Args:
            entity: 实体名称
            query_keywords: 查询关键词（用于辨别性匹配）
            limit: 最多返回多少个事件

        Returns:
            [(事件, 增强分数), ...] 按分数排序
        """
        event_ids = self.entity_index.get(entity, [])
        events_with_scores = []

        for eid in event_ids:
            if eid not in self.events:
                continue

            event = self.events[eid]
            base_score = 1.0

            # 使用模式分离器增强分数
            if self.pattern_separator and query_keywords:
                boosted_score = self.pattern_separator.boost_retrieval_score(
                    memory_id=eid,
                    query_entities=[entity],
                    query_keywords=query_keywords,
                    base_score=base_score
                )
            else:
                # 使用事件自身的辨别性特征
                boosted_score = base_score
                if query_keywords and event.discriminative_entities:
                    match_count = len(set(query_keywords) & set(event.discriminative_entities))
                    boosted_score += match_count * 0.1

            events_with_scores.append((event, boosted_score))

        # 按分数排序
        events_with_scores.sort(key=lambda x: x[1], reverse=True)

        if limit:
            events_with_scores = events_with_scores[:limit]

        return events_with_scores

    def find_most_distinctive_event(
        self,
        entity: str,
        discriminator: str
    ) -> Optional[Event]:
        """
        找到最具辨别性的事件

        例如：找到 "Person 周一的活动"（周一是辨别性特征）

        Args:
            entity: 实体名称
            discriminator: 辨别性特征（如 "周一", "morning", "2023-05-07"）

        Returns:
            最匹配的事件
        """
        event_ids = self.entity_index.get(entity, [])

        for eid in event_ids:
            if eid not in self.events:
                continue

            event = self.events[eid]

            # 检查辨别性时间特征
            if event.discriminative_temporal:
                if discriminator in event.discriminative_temporal:
                    return event

            # 检查辨别性实体
            if discriminator in event.discriminative_entities:
                return event

            # 检查内容
            if discriminator.lower() in event.content.lower():
                return event

        return None

    def get_similar_events(self, event_id: str) -> List[Event]:
        """
        获取与指定事件相似的其他事件

        用于"你是不是想找..."的推荐

        Args:
            event_id: 事件ID

        Returns:
            相似事件列表
        """
        if not self.pattern_separator:
            return []

        features = self.pattern_separator.get_discriminative_features(event_id)
        if not features:
            return []

        similar_events = []
        for contrast_id in features.contrast_memory_ids:
            if contrast_id in self.events:
                similar_events.append(self.events[contrast_id])

        return similar_events

    def get_pattern_separation_statistics(self) -> Dict[str, Any]:
        """获取模式分离统计信息"""
        stats = {
            'total_events': len(self.events),
            'pattern_separation_enabled': self.enable_pattern_separation
        }

        if self.pattern_separator:
            stats.update(self.pattern_separator.get_separation_statistics())

        # 事件级别的统计
        if self.events:
            separation_scores = [e.separation_score for e in self.events.values()]
            stats['event_avg_separation_score'] = sum(separation_scores) / len(separation_scores)
            stats['events_with_discriminative_entities'] = sum(
                1 for e in self.events.values() if e.discriminative_entities
            )
            stats['events_with_temporal_discriminator'] = sum(
                1 for e in self.events.values() if e.discriminative_temporal
            )

        return stats
