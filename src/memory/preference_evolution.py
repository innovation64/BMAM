"""
Preference Evolution Tracker - 偏好演变追踪器
解决 PersonaMem 评测中偏好追踪问题

核心功能:
1. 从对话中提取偏好信息 (likes, dislikes, interests, skills, goals)
2. 建立偏好演变时间线 (preference_timeline)
3. 与杏仁核协作标记情绪相关偏好 (emotion_weighted_preferences)
4. 与故事弧协作追踪偏好变化事件 (preference_change_events)
5. 在问答时提供整合的用户肖像 (unified_user_portrait)

架构:
┌─────────────────────────────────────────────────────────────┐
│                 PreferenceEvolutionTracker                   │
├─────────────────────────────────────────────────────────────┤
│  Preference Extractor (metacognition.UserPreferenceExtractor)│
│  ├─ extract_from_text(content) → preferences                │
│  └─ 支持显式+隐式偏好提取                                     │
├─────────────────────────────────────────────────────────────┤
│  Preference Timeline                                         │
│  ├─ [T1] music_production: like (confidence=0.9)            │
│  ├─ [T2] podcasting: dislike (confidence=0.7, reason=...)   │
│  └─ [T3] sound_engineering: like (confidence=0.95)          │
├─────────────────────────────────────────────────────────────┤
│  Preference Change Events (with StoryArc)                    │
│  ├─ preference_added: "started liking X"                    │
│  ├─ preference_changed: "stopped liking X because Y"        │
│  └─ preference_evolved: "deepened interest in X"            │
├─────────────────────────────────────────────────────────────┤
│  Emotion-Weighted Preferences (with Amygdala)                │
│  ├─ high_emotion: music (intensity=0.9)                     │
│  └─ low_emotion: reading (intensity=0.3)                    │
├─────────────────────────────────────────────────────────────┤
│  Query Interface                                             │
│  ├─ get_user_preferences(category) → List[Preference]       │
│  ├─ get_preference_evolution(topic) → Timeline              │
│  ├─ get_preference_change_reasons(topic) → List[Reason]     │
│  └─ get_user_portrait() → UnifiedPortrait                   │
└─────────────────────────────────────────────────────────────┘
"""

import logging
import re
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Set
from pathlib import Path
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


class PreferenceType(Enum):
    """偏好类型"""
    LIKE = "like"
    DISLIKE = "dislike"
    INTEREST = "interest"
    SKILL = "skill"
    GOAL = "goal"
    HABIT = "habit"
    ACTIVITY = "activity"
    FACT = "fact"


class PreferenceChangeType(Enum):
    """偏好变化类型"""
    ADDED = "added"  # 新增偏好
    REMOVED = "removed"  # 移除偏好
    STRENGTHENED = "strengthened"  # 强化偏好
    WEAKENED = "weakened"  # 弱化偏好
    REVERSED = "reversed"  # 反转偏好 (like -> dislike)


@dataclass
class Preference:
    """单个偏好"""
    id: str
    content: str  # 偏好内容，如 "music production"
    pref_type: PreferenceType  # 偏好类型
    confidence: float  # 置信度 0.0-1.0
    emotion_intensity: float  # 情绪强度 0.0-1.0 (来自杏仁核)
    first_mentioned: datetime
    last_mentioned: datetime
    mention_count: int = 1
    reasons: List[str] = field(default_factory=list)  # 偏好原因
    source_messages: List[str] = field(default_factory=list)  # 来源消息
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'content': self.content,
            'pref_type': self.pref_type.value,
            'confidence': self.confidence,
            'emotion_intensity': self.emotion_intensity,
            'first_mentioned': self.first_mentioned.isoformat(),
            'last_mentioned': self.last_mentioned.isoformat(),
            'mention_count': self.mention_count,
            'reasons': self.reasons,
            'source_messages': self.source_messages[:5],  # 只保留前5条
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Preference':
        data = data.copy()
        data['pref_type'] = PreferenceType(data['pref_type'])
        data['first_mentioned'] = datetime.fromisoformat(data['first_mentioned'])
        data['last_mentioned'] = datetime.fromisoformat(data['last_mentioned'])
        return cls(**data)


@dataclass
class PreferenceChangeEvent:
    """偏好变化事件"""
    event_id: str
    preference_id: str
    change_type: PreferenceChangeType
    timestamp: datetime
    reason: str  # 变化原因
    from_state: Optional[str] = None  # 变化前状态
    to_state: Optional[str] = None  # 变化后状态
    source_message: str = ""

    def to_dict(self) -> Dict:
        return {
            'event_id': self.event_id,
            'preference_id': self.preference_id,
            'change_type': self.change_type.value,
            'timestamp': self.timestamp.isoformat(),
            'reason': self.reason,
            'from_state': self.from_state,
            'to_state': self.to_state,
            'source_message': self.source_message[:200]
        }


class PreferenceEvolutionTracker:
    """
    偏好演变追踪器 - 脑区协作核心

    协作机制:
    1. UserPreferenceExtractor: 提取偏好
    2. AmygdalaAgent: 情绪标记
    3. StoryArcManager: 事件时间线
    4. PersonaMemoryAgent: 持久化存储
    """

    def __init__(
        self,
        amygdala_agent=None,
        story_arc_manager=None,
        persona_memory_agent=None
    ):
        # 脑区协作
        self.amygdala = amygdala_agent
        self.story_arc = story_arc_manager
        self.persona_memory = persona_memory_agent

        # 偏好存储
        self.preferences: Dict[str, Preference] = {}  # id -> Preference
        self.preference_by_content: Dict[str, str] = {}  # normalized_content -> id
        self.preference_timeline: List[Tuple[datetime, str, str]] = []  # (time, pref_id, action)

        # 偏好变化事件
        self.change_events: List[PreferenceChangeEvent] = []

        # 偏好分类索引
        self.preferences_by_type: Dict[PreferenceType, List[str]] = defaultdict(list)

        # 话题到偏好的映射
        self.topic_preferences: Dict[str, List[str]] = defaultdict(list)

        # 偏好提取器
        from ..optimization.metacognition import UserPreferenceExtractor
        self.extractor = UserPreferenceExtractor()

        # 偏好变化检测模式
        self.change_patterns = {
            'stopped': [
                r"(?:I\s+)?(?:stopped|no longer|don't|quit|gave up)\s+(?:enjoy|like|doing)\s+([^.,!?]+)",
                r"(?:I\s+)?(?:decided|realized)\s+(?:I\s+)?(?:don't|didn't)\s+(?:enjoy|like)\s+([^.,!?]+)",
            ],
            'reason': [
                r"because\s+([^.,!?]+)",
                r"(?:the reason|reason being|due to)\s+(?:is\s+)?([^.,!?]+)",
                r"(?:which|that)\s+(?:made|caused|led)\s+(?:me\s+)?(?:to\s+)?([^.,!?]+)",
            ],
            'started': [
                r"(?:I\s+)?(?:started|began|picked up|got into)\s+([^.,!?]+)",
                r"(?:I've|I\s+have)\s+(?:recently\s+)?(?:started|begun)\s+([^.,!?]+)",
            ],
            'deepened': [
                r"(?:I\s+)?(?:really|deeply)\s+(?:love|enjoy|appreciate)\s+([^.,!?]+)",
                r"(?:my\s+)?(?:passion|love|interest)\s+(?:for|in)\s+([^.,!?]+)\s+(?:has\s+)?(?:grown|deepened|increased)",
            ]
        }

        logger.info("PreferenceEvolutionTracker initialized")

    def _normalize_content(self, content: str) -> str:
        """标准化偏好内容用于比较"""
        return content.lower().strip()

    def _generate_id(self) -> str:
        """生成唯一ID"""
        import uuid
        return str(uuid.uuid4())[:8]

    async def extract_preferences_from_message(
        self,
        content: str,
        speaker: str,
        timestamp: datetime,
        emotion_intensity: float = 0.5
    ) -> List[Preference]:
        """
        从单条消息中提取偏好

        Args:
            content: 消息内容
            speaker: 说话者 (User/Assistant)
            timestamp: 时间戳
            emotion_intensity: 情绪强度 (可从杏仁核获取)

        Returns:
            提取的偏好列表
        """
        # 只处理用户消息
        if speaker.lower() != 'user':
            # 但助手消息中可能包含用户偏好的确认
            if 'you like' in content.lower() or 'you enjoy' in content.lower():
                pass  # 继续处理
            else:
                return []

        # 使用偏好提取器
        extracted = self.extractor.extract_from_text(content)

        preferences = []

        # 处理各类偏好
        type_mapping = {
            'likes': PreferenceType.LIKE,
            'dislikes': PreferenceType.DISLIKE,
            'interests': PreferenceType.INTEREST,
            'activities': PreferenceType.ACTIVITY,
            'facts': PreferenceType.FACT,
            'skills': PreferenceType.SKILL,
            'goals': PreferenceType.GOAL,
            'habits': PreferenceType.HABIT,
        }

        for category, pref_type in type_mapping.items():
            for pref_content in extracted.get(category, []):
                pref = await self._add_or_update_preference(
                    content=pref_content,
                    pref_type=pref_type,
                    timestamp=timestamp,
                    emotion_intensity=emotion_intensity,
                    source_message=content
                )
                if pref:
                    preferences.append(pref)

        # 检测偏好变化
        await self._detect_preference_changes(content, timestamp)

        return preferences

    async def _add_or_update_preference(
        self,
        content: str,
        pref_type: PreferenceType,
        timestamp: datetime,
        emotion_intensity: float,
        source_message: str
    ) -> Optional[Preference]:
        """添加或更新偏好"""
        normalized = self._normalize_content(content)

        if len(normalized) < 3:  # 忽略太短的偏好
            return None

        existing_id = self.preference_by_content.get(normalized)

        if existing_id and existing_id in self.preferences:
            # 更新现有偏好
            pref = self.preferences[existing_id]
            pref.mention_count += 1
            pref.last_mentioned = timestamp
            pref.confidence = min(1.0, pref.confidence + 0.1)
            pref.emotion_intensity = max(pref.emotion_intensity, emotion_intensity)
            if source_message not in pref.source_messages:
                pref.source_messages.append(source_message)
            return pref
        else:
            # 创建新偏好
            pref_id = self._generate_id()
            pref = Preference(
                id=pref_id,
                content=content,
                pref_type=pref_type,
                confidence=0.7,
                emotion_intensity=emotion_intensity,
                first_mentioned=timestamp,
                last_mentioned=timestamp,
                source_messages=[source_message]
            )
            self.preferences[pref_id] = pref
            self.preference_by_content[normalized] = pref_id
            self.preferences_by_type[pref_type].append(pref_id)
            self.preference_timeline.append((timestamp, pref_id, 'added'))

            # 提取话题关键词
            topic = self._extract_topic(content)
            if topic:
                self.topic_preferences[topic].append(pref_id)

            return pref

    def _extract_topic(self, content: str) -> str:
        """提取偏好的话题"""
        # 简单的话题提取
        content_lower = content.lower()

        topic_keywords = {
            'music': ['music', 'song', 'melody', 'rhythm', 'sound', 'audio'],
            'technology': ['tech', 'software', 'programming', 'code', 'digital'],
            'art': ['art', 'painting', 'drawing', 'creative', 'design'],
            'food': ['food', 'cooking', 'recipe', 'cuisine', 'eating'],
            'travel': ['travel', 'trip', 'journey', 'vacation', 'adventure'],
            'reading': ['book', 'reading', 'novel', 'literature', 'story'],
            'sports': ['sport', 'exercise', 'fitness', 'gym', 'running'],
        }

        for topic, keywords in topic_keywords.items():
            if any(kw in content_lower for kw in keywords):
                return topic

        return ""

    async def _detect_preference_changes(self, content: str, timestamp: datetime):
        """检测偏好变化事件"""
        content_lower = content.lower()

        # 检测停止喜欢的模式
        for pattern in self.change_patterns['stopped']:
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            for match in matches:
                # 提取变化原因
                reason = ""
                for reason_pattern in self.change_patterns['reason']:
                    reason_matches = re.findall(reason_pattern, content_lower, re.IGNORECASE)
                    if reason_matches:
                        reason = reason_matches[0]
                        break

                # 创建变化事件
                event = PreferenceChangeEvent(
                    event_id=self._generate_id(),
                    preference_id="",  # 可能需要查找现有偏好
                    change_type=PreferenceChangeType.REMOVED,
                    timestamp=timestamp,
                    reason=reason,
                    from_state="liked",
                    to_state="stopped liking",
                    source_message=content
                )
                self.change_events.append(event)

                # 更新偏好状态
                normalized = self._normalize_content(match)
                if normalized in self.preference_by_content:
                    pref_id = self.preference_by_content[normalized]
                    pref = self.preferences.get(pref_id)
                    if pref:
                        pref.pref_type = PreferenceType.DISLIKE
                        pref.reasons.append(reason)
                        event.preference_id = pref_id

    async def ingest_conversation(
        self,
        messages: List[Dict[str, Any]],
        base_timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        塑造整个对话，提取所有偏好

        Args:
            messages: 对话消息列表
            base_timestamp: 基础时间戳

        Returns:
            塑造结果统计
        """
        if base_timestamp is None:
            base_timestamp = datetime.now()

        total_preferences = 0
        new_preferences = 0
        updated_preferences = 0

        for i, msg in enumerate(messages):
            role = msg.get('role', 'user')
            content = msg.get('content', '')

            if not content:
                continue

            speaker = 'User' if role == 'user' else 'Assistant'

            # 模拟时间递增
            timestamp = base_timestamp

            # 获取情绪强度 (如果有杏仁核协作)
            emotion_intensity = 0.5
            if self.amygdala:
                try:
                    emotion_result = await self.amygdala.analyze_emotion(content)
                    emotion_intensity = emotion_result.get('intensity', 0.5)
                except Exception:
                    pass

            # 提取偏好
            before_count = len(self.preferences)
            prefs = await self.extract_preferences_from_message(
                content, speaker, timestamp, emotion_intensity
            )
            after_count = len(self.preferences)

            new_preferences += (after_count - before_count)
            updated_preferences += len(prefs) - (after_count - before_count)
            total_preferences += len(prefs)

        # 与故事弧同步
        if self.story_arc:
            await self._sync_with_story_arc()

        # 与 persona memory 同步
        if self.persona_memory:
            await self._sync_with_persona_memory()

        return {
            'total_messages': len(messages),
            'total_preferences_extracted': total_preferences,
            'new_preferences': new_preferences,
            'updated_preferences': updated_preferences,
            'unique_preferences': len(self.preferences),
            'change_events': len(self.change_events)
        }

    async def _sync_with_story_arc(self):
        """
        与故事弧同步偏好变化事件

        🔥 FIX-009: 实现偏好演变时间线追踪
        将偏好变化事件（如"停止喜欢X"）作为时间线事件记录，
        支持回答"用户什么时候改变了对X的看法"类问题
        """
        if not self.story_arc:
            return

        synced_count = 0

        # 将偏好变化事件添加到故事弧
        for event in self.change_events:
            pref = self.preferences.get(event.preference_id)
            if not pref:
                continue

            # 构建偏好变化描述（添加 "User" 前缀以便 StoryArc 能提取到实体）
            change_descriptions = {
                PreferenceChangeType.ADDED: f"User started liking {pref.content}",
                PreferenceChangeType.REMOVED: f"User stopped liking {pref.content}",
                PreferenceChangeType.STRENGTHENED: f"User developed stronger interest in {pref.content}",
                PreferenceChangeType.WEAKENED: f"User lost interest in {pref.content}",
                PreferenceChangeType.REVERSED: f"User changed opinion on {pref.content}",
            }

            description = change_descriptions.get(
                event.change_type,
                f"User preference change: {pref.content}"
            )

            if event.reason:
                description += f" because {event.reason}"

            # 添加到故事弧
            try:
                await self.story_arc.add_event_from_memory(
                    memory_id=f"pref_change_{event.event_id}",
                    content=description,
                    event_time=event.timestamp,
                    metadata={
                        'event_type': 'preference_change',
                        'preference_id': event.preference_id,
                        'change_type': event.change_type.value,
                        'from_state': event.from_state,
                        'to_state': event.to_state,
                        'preference_content': pref.content,
                        'entities': [pref.content]  # 将偏好内容作为实体
                    }
                )
                synced_count += 1
            except Exception as e:
                logger.warning(f"Failed to sync preference change to story arc: {e}")

        if synced_count > 0:
            logger.info(f"Synced {synced_count} preference changes to story arc")

    async def _sync_with_persona_memory(self):
        """与 persona memory 同步偏好"""
        if not self.persona_memory:
            return

        # 将偏好存储到 persona memory
        for pref in self.preferences.values():
            try:
                await self.persona_memory.store_persona({
                    'content': f"{pref.pref_type.value}: {pref.content}",
                    'category': pref.pref_type.value,
                    'importance': pref.confidence,
                    'metadata': {
                        'preference_id': pref.id,
                        'mention_count': pref.mention_count,
                        'emotion_intensity': pref.emotion_intensity,
                        'preference_type': pref.pref_type.value
                    }
                })
            except Exception as e:
                logger.warning(f"Failed to sync preference to persona memory: {e}")

    def get_user_preferences(
        self,
        pref_type: Optional[PreferenceType] = None,
        min_confidence: float = 0.0,
        top_k: int = 20
    ) -> List[Preference]:
        """
        获取用户偏好列表

        Args:
            pref_type: 偏好类型过滤
            min_confidence: 最小置信度
            top_k: 返回数量

        Returns:
            偏好列表
        """
        prefs = list(self.preferences.values())

        # 类型过滤
        if pref_type:
            prefs = [p for p in prefs if p.pref_type == pref_type]

        # 置信度过滤
        prefs = [p for p in prefs if p.confidence >= min_confidence]

        # 按置信度和情绪强度综合排序
        prefs.sort(key=lambda p: p.confidence * 0.6 + p.emotion_intensity * 0.4, reverse=True)

        return prefs[:top_k]

    def get_preference_evolution(self, topic: str) -> List[Tuple[datetime, str, str]]:
        """
        获取特定话题的偏好演变历史

        Args:
            topic: 话题名称

        Returns:
            (时间, 偏好内容, 变化类型) 的列表
        """
        topic_lower = topic.lower()
        evolution = []

        # 从时间线中筛选相关事件
        for timestamp, pref_id, action in self.preference_timeline:
            pref = self.preferences.get(pref_id)
            if pref and topic_lower in pref.content.lower():
                evolution.append((timestamp, pref.content, action))

        # 添加变化事件
        for event in self.change_events:
            pref = self.preferences.get(event.preference_id)
            if pref and topic_lower in pref.content.lower():
                evolution.append((event.timestamp, pref.content, event.change_type.value))

        # 按时间排序
        evolution.sort(key=lambda x: x[0])

        return evolution

    def get_preference_change_reasons(self, topic: str) -> List[Dict[str, Any]]:
        """
        获取偏好变化的原因

        Args:
            topic: 话题名称

        Returns:
            变化原因列表
        """
        topic_lower = topic.lower()
        reasons = []

        for event in self.change_events:
            pref = self.preferences.get(event.preference_id)
            if pref and topic_lower in pref.content.lower():
                reasons.append({
                    'preference': pref.content,
                    'change_type': event.change_type.value,
                    'reason': event.reason,
                    'timestamp': event.timestamp.isoformat(),
                    'from_state': event.from_state,
                    'to_state': event.to_state
                })

        # 也从偏好本身的 reasons 字段获取
        for pref in self.preferences.values():
            if topic_lower in pref.content.lower() and pref.reasons:
                for reason in pref.reasons:
                    reasons.append({
                        'preference': pref.content,
                        'change_type': 'reason_recorded',
                        'reason': reason,
                        'timestamp': pref.last_mentioned.isoformat()
                    })

        return reasons

    def get_user_portrait(self) -> Dict[str, Any]:
        """
        获取整合的用户肖像

        Returns:
            用户肖像字典
        """
        likes = self.get_user_preferences(PreferenceType.LIKE, min_confidence=0.5, top_k=10)
        dislikes = self.get_user_preferences(PreferenceType.DISLIKE, min_confidence=0.5, top_k=5)
        interests = self.get_user_preferences(PreferenceType.INTEREST, min_confidence=0.5, top_k=10)
        skills = self.get_user_preferences(PreferenceType.SKILL, min_confidence=0.5, top_k=5)
        goals = self.get_user_preferences(PreferenceType.GOAL, min_confidence=0.5, top_k=5)
        activities = self.get_user_preferences(PreferenceType.ACTIVITY, min_confidence=0.5, top_k=10)

        # 构建肖像文本
        portrait_parts = []

        if likes:
            like_items = [p.content for p in likes[:5]]
            portrait_parts.append(f"The user likes: {', '.join(like_items)}")

        if interests:
            interest_items = [p.content for p in interests[:5]]
            portrait_parts.append(f"The user is interested in: {', '.join(interest_items)}")

        if skills:
            skill_items = [p.content for p in skills[:3]]
            portrait_parts.append(f"The user is skilled at: {', '.join(skill_items)}")

        if activities:
            activity_items = [p.content for p in activities[:5]]
            portrait_parts.append(f"The user engages in: {', '.join(activity_items)}")

        if dislikes:
            dislike_items = [p.content for p in dislikes[:3]]
            portrait_parts.append(f"The user dislikes: {', '.join(dislike_items)}")

        if goals:
            goal_items = [p.content for p in goals[:3]]
            portrait_parts.append(f"The user's goals include: {', '.join(goal_items)}")

        return {
            'portrait_text': '\n'.join(portrait_parts),
            'likes': [p.to_dict() for p in likes],
            'dislikes': [p.to_dict() for p in dislikes],
            'interests': [p.to_dict() for p in interests],
            'skills': [p.to_dict() for p in skills],
            'goals': [p.to_dict() for p in goals],
            'activities': [p.to_dict() for p in activities],
            'total_preferences': len(self.preferences),
            'change_events_count': len(self.change_events)
        }

    def get_context_for_question(self, question: str, top_k: int = 10) -> str:
        """
        为问题生成相关的偏好上下文

        Args:
            question: 用户问题
            top_k: 返回的偏好数量

        Returns:
            偏好上下文文本
        """
        question_lower = question.lower()

        # 关键词匹配偏好
        matched_prefs = []
        for pref in self.preferences.values():
            content_lower = pref.content.lower()
            # 计算匹配分数
            score = 0.0
            for word in question_lower.split():
                if len(word) > 3 and word in content_lower:
                    score += 0.3
            # 加上置信度和情绪权重
            score += pref.confidence * 0.4 + pref.emotion_intensity * 0.3
            if score > 0.2:
                matched_prefs.append((score, pref))

        # 排序并取前K
        matched_prefs.sort(key=lambda x: x[0], reverse=True)
        top_prefs = [p for _, p in matched_prefs[:top_k]]

        # 生成上下文
        context_parts = []

        # 按类型组织
        likes = [p for p in top_prefs if p.pref_type == PreferenceType.LIKE]
        dislikes = [p for p in top_prefs if p.pref_type == PreferenceType.DISLIKE]
        interests = [p for p in top_prefs if p.pref_type == PreferenceType.INTEREST]
        activities = [p for p in top_prefs if p.pref_type == PreferenceType.ACTIVITY]
        skills = [p for p in top_prefs if p.pref_type == PreferenceType.SKILL]

        if likes:
            context_parts.append(f"User likes: {', '.join(p.content for p in likes)}")
        if interests:
            context_parts.append(f"User is interested in: {', '.join(p.content for p in interests)}")
        if activities:
            context_parts.append(f"User activities: {', '.join(p.content for p in activities)}")
        if skills:
            context_parts.append(f"User skills: {', '.join(p.content for p in skills)}")
        if dislikes:
            context_parts.append(f"User dislikes: {', '.join(p.content for p in dislikes)}")

        # 添加变化原因 (对于 "why" 类问题)
        if 'why' in question_lower or 'reason' in question_lower:
            for pref in top_prefs:
                if pref.reasons:
                    context_parts.append(f"Reason for {pref.content}: {pref.reasons[0]}")

        return '\n'.join(context_parts)

    def clear(self):
        """清空所有偏好数据"""
        self.preferences.clear()
        self.preference_by_content.clear()
        self.preference_timeline.clear()
        self.change_events.clear()
        self.preferences_by_type.clear()
        self.topic_preferences.clear()


# 全局实例
_preference_tracker: Optional[PreferenceEvolutionTracker] = None


def get_preference_tracker() -> PreferenceEvolutionTracker:
    """获取全局偏好追踪器实例"""
    global _preference_tracker
    if _preference_tracker is None:
        _preference_tracker = PreferenceEvolutionTracker()
    return _preference_tracker


def reset_preference_tracker():
    """重置全局偏好追踪器"""
    global _preference_tracker
    if _preference_tracker:
        _preference_tracker.clear()
    _preference_tracker = None
