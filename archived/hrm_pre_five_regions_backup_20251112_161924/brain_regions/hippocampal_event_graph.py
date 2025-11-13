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
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """事件节点"""
    id: str
    content: str
    entities: List[str]  # ["Caroline", "LGBTQ"]
    timestamp: datetime
    next_events: List[str] = field(default_factory=list)  # 后续事件IDs
    prev_events: List[str] = field(default_factory=list)  # 之前事件IDs
    metadata: Dict[str, Any] = field(default_factory=dict)


class HippocampalEventGraph:
    """
    海马体事件图 - 存储事件序列

    核心特点:
    1. Graph结构，不是向量
    2. 支持时间顺序查询
    3. 支持实体相关事件查询
    4. O(1)复杂度的索引查询
    """

    def __init__(self):
        # 核心存储
        self.events: Dict[str, Event] = {}  # {event_id: Event}

        # 索引结构 (快速查询)
        self.entity_index: Dict[str, List[str]] = defaultdict(list)  # {entity: [event_ids]}
        self.time_index: Dict[str, List[str]] = {}  # {date_str: [event_ids]}
        self.temporal_chain: List[str] = []  # 全局时间链 (按时间排序的event_ids)


    def add_event(
        self,
        content: str,
        entities: List[str],
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        添加事件到图

        Args:
            content: 事件描述 "Caroline去了LGBTQ group"
            entities: 实体列表 ["Caroline", "LGBTQ"]
            timestamp: 时间戳
            metadata: 额外元数据

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
            entity: 实体名称 "Caroline"
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


        return graph
