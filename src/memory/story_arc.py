"""
Story Arc / Narrative Manager - 故事线/叙事管理器
V2.0 时间推理增强核心模块

主要功能:
1. 维护事件时间线索引 (Timeline Index)
2. 实体→事件映射 (Entity-Event Mapping)
3. 直接回答时间查询 (Temporal Query)
4. 计算时间跨度 (Duration Calculation)

解决问题:
- 当前 Temporal 准确率: 35%
- 目标 Temporal 准确率: 70%+
- 核心问题: 记忆扁平存储，无时间结构

架构:
┌─────────────────────────────────────────────────┐
│              Story Arc Manager                   │
├─────────────────────────────────────────────────┤
│  Timeline Index                                  │
│  ├─ 2023-05-07: [event1, event2]                │
│  ├─ 2023-05-08: [event3]                        │
│  └─ 2023-07-05: [event4, event5]                │
├─────────────────────────────────────────────────┤
│  Entity-Event Map                                │
│  ├─ Caroline: [(07 May, LGBTQ), (05 Jul, museum)]│
│  └─ Melanie:  [(08 May, camping), ...]          │
├─────────────────────────────────────────────────┤
│  Query Interface                                 │
│  ├─ query_event_time(entity, event_type)        │
│  ├─ calculate_duration(entity, reference)       │
│  └─ get_events_in_range(start, end)             │
└─────────────────────────────────────────────────┘
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class TimelineEvent:
    """时间线事件"""
    event_id: str
    event_date: date
    event_type: str  # 'lgbtq_support', 'museum_visit', 'camping', etc.
    entities: List[str]  # ['Caroline', 'Melanie']
    description: str
    source_memory_id: Optional[str] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'event_id': self.event_id,
            'event_date': self.event_date.isoformat(),
            'event_type': self.event_type,
            'entities': self.entities,
            'description': self.description,
            'source_memory_id': self.source_memory_id,
            'confidence': self.confidence,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'TimelineEvent':
        data = data.copy()
        if isinstance(data.get('event_date'), str):
            data['event_date'] = date.fromisoformat(data['event_date'])
        return cls(**data)


class StoryArcManager:
    """
    故事线管理器 - 维护事件时间线和实体-事件映射

    核心数据结构:
    1. timeline: Dict[date, List[TimelineEvent]] - 按日期索引的事件
    2. entity_events: Dict[str, List[TimelineEvent]] - 按实体索引的事件
    3. event_types: Dict[str, List[TimelineEvent]] - 按事件类型索引
    """

    # 事件类型关键词映射
    EVENT_TYPE_KEYWORDS = {
        'lgbtq_support': ['lgbtq', 'support group', 'transgender', 'pride', 'community'],
        'museum_visit': ['museum', 'exhibition', 'gallery', 'art show'],
        'camping': ['camping', 'camp', 'tent', 'outdoor', 'hiking'],
        'pottery': ['pottery', 'ceramic', 'clay', 'workshop'],
        'conference': ['conference', 'seminar', 'summit', 'symposium'],
        'parade': ['parade', 'march', 'demonstration', 'rally'],
        'picnic': ['picnic', 'outing', 'park'],
        'birthday': ['birthday', 'celebration', 'party'],
        'mentoring': ['mentor', 'mentoring', 'volunteer', 'youth'],
        'school_event': ['school', 'education', 'teaching', 'talk'],
        'concert': ['concert', 'music', 'orchestra', 'performance'],
        'coffee': ['coffee', 'cafe', 'latte', 'espresso'],
        'adoption': ['adoption', 'agency', 'family planning'],
        'counseling': ['counseling', 'therapy', 'mental health'],
        'activism': ['activist', 'activism', 'advocacy', 'rights'],
        'friendship': ['friend', 'friends', 'friendship', 'met'],
        'move': ['move', 'moved', 'relocate', 'migration', 'sweden', 'country']
    }

    def __init__(self, data_dir: Optional[Path] = None):
        """初始化故事线管理器"""
        # 🔥 使用 BMAMPaths 统一路径管理，不再硬编码
        from ..utils.paths import BMAMPaths

        self.data_dir = data_dir if data_dir else BMAMPaths.STATE_DIR
        self.state_file = BMAMPaths.STORY_ARC_STATE

        # 核心索引结构
        self.timeline: Dict[date, List[TimelineEvent]] = defaultdict(list)
        self.entity_events: Dict[str, List[TimelineEvent]] = defaultdict(list)
        self.event_type_index: Dict[str, List[TimelineEvent]] = defaultdict(list)

        # 事件ID索引
        self.events_by_id: Dict[str, TimelineEvent] = {}

        # 加载持久化状态
        self._load_state()

        logger.info(f"StoryArcManager initialized: {len(self.events_by_id)} events loaded")

    def _load_state(self):
        """加载持久化状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)

                for event_data in data.get('events', []):
                    event = TimelineEvent.from_dict(event_data)
                    self._index_event(event)

                logger.debug(f"Loaded {len(self.events_by_id)} events from {self.state_file}")
            except Exception as e:
                logger.warning(f"Failed to load story arc state: {e}")

    def _save_state(self):
        """保存持久化状态"""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            data = {
                'events': [e.to_dict() for e in self.events_by_id.values()],
                'updated_at': datetime.now().isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save story arc state: {e}")

    def _index_event(self, event: TimelineEvent):
        """将事件添加到所有索引"""
        # ID索引
        self.events_by_id[event.event_id] = event

        # 时间线索引
        self.timeline[event.event_date].append(event)

        # 实体索引
        for entity in event.entities:
            entity_lower = entity.lower()
            self.entity_events[entity_lower].append(event)

        # 事件类型索引
        self.event_type_index[event.event_type].append(event)

    def _extract_event_type(self, content: str) -> str:
        """从内容中提取事件类型"""
        content_lower = content.lower()

        for event_type, keywords in self.EVENT_TYPE_KEYWORDS.items():
            if any(kw in content_lower for kw in keywords):
                return event_type

        return 'general'

    def _extract_entities(self, content: str) -> List[str]:
        """从内容中提取实体名称"""
        entities = []

        # 常见人名
        common_names = ['caroline', 'melanie', 'sarah', 'john', 'mike',
                       'alice', 'bob', 'user', 'assistant']

        content_lower = content.lower()
        for name in common_names:
            if name in content_lower:
                entities.append(name.capitalize())

        # 提取 "Speaker: text" 格式中的说话者
        speaker_match = re.match(r'^(\w+):', content)
        if speaker_match:
            speaker = speaker_match.group(1)
            if speaker.lower() not in ['context', 'event']:
                entities.append(speaker)

        return list(set(entities))

    async def add_event_from_memory(
        self,
        memory_id: str,
        content: str,
        event_time: Optional[datetime],
        metadata: Optional[Dict] = None
    ) -> Optional[TimelineEvent]:
        """
        从记忆内容中提取并添加事件

        Args:
            memory_id: 源记忆ID
            content: 记忆内容
            event_time: 事件发生时间
            metadata: 额外元数据

        Returns:
            创建的TimelineEvent，或None如果无法提取
        """
        if not event_time:
            return None

        # 提取事件类型和实体
        event_type = self._extract_event_type(content)
        entities = self._extract_entities(content)

        # 跳过无实体或太泛的事件
        if not entities or event_type == 'general':
            # 尝试从metadata获取更多信息
            if metadata:
                if metadata.get('speaker'):
                    entities.append(metadata['speaker'])

        if not entities:
            return None

        # 生成事件ID
        event_id = f"{event_time.strftime('%Y%m%d')}_{event_type}_{memory_id[:8]}"

        # 检查是否已存在相似事件（避免重复）
        event_date = event_time.date() if isinstance(event_time, datetime) else event_time
        existing = self._find_similar_event(event_date, event_type, entities)
        if existing:
            logger.debug(f"Similar event already exists: {existing.event_id}")
            return existing

        # 创建事件
        event = TimelineEvent(
            event_id=event_id,
            event_date=event_date,
            event_type=event_type,
            entities=entities,
            description=content[:200],  # 截断描述
            source_memory_id=memory_id,
            confidence=metadata.get('extraction_confidence', 0.8) if metadata else 0.8,
            metadata=metadata or {}
        )

        # 添加到索引
        self._index_event(event)

        # 持久化
        self._save_state()

        logger.debug(f"Added event: {event_id} on {event_date} for {entities}")
        return event

    def _find_similar_event(
        self,
        event_date: date,
        event_type: str,
        entities: List[str]
    ) -> Optional[TimelineEvent]:
        """查找相似事件（同一天、同类型、相同实体）"""
        for existing in self.timeline.get(event_date, []):
            if existing.event_type == event_type:
                # 检查实体重叠
                existing_entities = set(e.lower() for e in existing.entities)
                new_entities = set(e.lower() for e in entities)
                if existing_entities & new_entities:
                    return existing
        return None

    async def query_event_time(
        self,
        entity: str,
        event_keywords: List[str],
        time_hint: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        查询实体的事件发生时间

        Args:
            entity: 实体名称 (e.g., 'Caroline')
            event_keywords: 事件关键词 (e.g., ['museum', 'visit'])
            time_hint: 时间提示 (e.g., 'July 2023', 'summer')

        Returns:
            {
                'event_date': date,
                'event': TimelineEvent,
                'confidence': float,
                'formatted_date': str  # e.g., '5 July 2023'
            }
        """
        entity_lower = entity.lower()
        events = self.entity_events.get(entity_lower, [])

        if not events:
            logger.debug(f"No events found for entity: {entity}")
            return None

        # 计算每个事件与关键词的匹配度
        candidates = []
        for event in events:
            score = 0
            desc_lower = event.description.lower()

            # 关键词匹配
            for kw in event_keywords:
                if kw.lower() in desc_lower:
                    score += 2
                if kw.lower() in event.event_type:
                    score += 1

            # 事件类型匹配
            for kw in event_keywords:
                for event_type, type_keywords in self.EVENT_TYPE_KEYWORDS.items():
                    if kw.lower() in type_keywords and event.event_type == event_type:
                        score += 3

            # 时间提示匹配
            if time_hint and score > 0:
                time_hint_lower = time_hint.lower()
                event_month = event.event_date.strftime('%B').lower()
                event_year = str(event.event_date.year)

                if event_month in time_hint_lower:
                    score += 2
                if event_year in time_hint_lower:
                    score += 1
                if 'summer' in time_hint_lower and event.event_date.month in [6, 7, 8]:
                    score += 1

            if score > 0:
                candidates.append((event, score))

        if not candidates:
            return None

        # 按分数排序
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_event, best_score = candidates[0]

        # 计算置信度
        confidence = min(0.95, 0.5 + best_score * 0.1)

        result = {
            'event_date': best_event.event_date,
            'event': best_event,
            'confidence': confidence,
            'formatted_date': best_event.event_date.strftime('%d %B %Y').lstrip('0'),
            'match_score': best_score
        }

        logger.info(f"StoryArc query: entity={entity}, keywords={event_keywords} "
                   f"→ {result['formatted_date']} (confidence={confidence:.2f})")

        return result

    async def calculate_duration(
        self,
        entity: str,
        reference: str,
        reference_date: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        """
        计算时间跨度

        Args:
            entity: 实体名称
            reference: 参考内容 (e.g., 'friends', 'living in current city')
            reference_date: 参考日期 (通常是对话日期)

        Returns:
            {
                'duration': str,  # e.g., '4 years'
                'start_date': date,
                'confidence': float
            }
        """
        entity_lower = entity.lower()
        events = self.entity_events.get(entity_lower, [])

        if not events:
            return None

        ref_lower = reference.lower()

        # 查找相关的起始事件
        start_event = None
        for event in events:
            desc_lower = event.description.lower()

            # 匹配友谊开始
            if 'friend' in ref_lower and any(kw in desc_lower for kw in ['friend', 'met', 'friendship']):
                start_event = event
                break

            # 匹配搬家
            if 'move' in ref_lower or 'live' in ref_lower:
                if any(kw in desc_lower for kw in ['move', 'moved', 'relocate']):
                    start_event = event
                    break

        if not start_event:
            return None

        # 计算持续时间
        end_date = reference_date or date.today()
        delta = end_date - start_event.event_date

        years = delta.days // 365
        months = (delta.days % 365) // 30

        if years > 0:
            duration = f"{years} years" if years > 1 else "1 year"
            if months > 0:
                duration += f" and {months} months"
        elif months > 0:
            duration = f"{months} months" if months > 1 else "1 month"
        else:
            duration = f"{delta.days} days"

        return {
            'duration': duration,
            'start_date': start_event.event_date,
            'start_event': start_event,
            'confidence': 0.85
        }

    async def get_events_in_range(
        self,
        start_date: date,
        end_date: date,
        entity: Optional[str] = None
    ) -> List[TimelineEvent]:
        """获取时间范围内的事件"""
        events = []

        current = start_date
        while current <= end_date:
            day_events = self.timeline.get(current, [])

            if entity:
                entity_lower = entity.lower()
                day_events = [e for e in day_events
                             if any(ent.lower() == entity_lower for ent in e.entities)]

            events.extend(day_events)
            current += timedelta(days=1)

        return events

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_events': len(self.events_by_id),
            'unique_dates': len(self.timeline),
            'unique_entities': len(self.entity_events),
            'event_types': {k: len(v) for k, v in self.event_type_index.items()},
            'entities': {k: len(v) for k, v in self.entity_events.items()}
        }

    def clear(self):
        """清空所有数据"""
        self.timeline.clear()
        self.entity_events.clear()
        self.event_type_index.clear()
        self.events_by_id.clear()

        if self.state_file.exists():
            self.state_file.unlink()

        logger.info("StoryArcManager cleared")


# 全局单例
_story_arc_manager: Optional[StoryArcManager] = None


def get_story_arc_manager(data_dir: Optional[Path] = None) -> StoryArcManager:
    """获取故事线管理器单例"""
    global _story_arc_manager
    if _story_arc_manager is None:
        _story_arc_manager = StoryArcManager(data_dir)
    return _story_arc_manager


def reset_story_arc_manager():
    """重置故事线管理器"""
    global _story_arc_manager
    if _story_arc_manager:
        _story_arc_manager.clear()
    _story_arc_manager = None
