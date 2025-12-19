"""
Soul State - 系统"灵魂"状态管理

追踪情绪、思考流、路由决策、梦境状态、洞察和自省。
🔥 2025-12-19: 新增 Insights 和 Introspection 功能 (P0技术债务修复)
🔥 2025-12-19: 新增 ValueProfile 价值观/偏好累积 (P0)
"""

import logging
import asyncio
import threading
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, asdict, field
from collections import Counter

logger = logging.getLogger(__name__)


# ============================================================================
# 🔥 2025-12-19: ValueProfile - 价值观/偏好累积 (P0)
# ============================================================================

@dataclass
class PreferenceItem:
    """单个偏好项"""
    item: str
    category: str  # 'like', 'dislike', 'habit', 'goal', 'taboo'
    confidence: float  # 0.0-1.0
    source_count: int  # 从多少次对话/记忆中提取
    first_seen: str
    last_updated: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValueProfile:
    """
    价值观档案 - 维护用户或系统的身份认同和偏好

    用于:
    - 路由决策的附加特征
    - 响应生成的约束条件
    - 个性化和一致性
    """
    # 身份信息
    identity_name: Optional[str] = None
    identity_description: Optional[str] = None

    # 目标 (短期和长期)
    short_term_goals: List[str] = field(default_factory=list)
    long_term_goals: List[str] = field(default_factory=list)

    # 偏好列表 (带置信度)
    preferences: Dict[str, PreferenceItem] = field(default_factory=dict)  # key: item

    # 禁忌 (应避免的主题/行为)
    taboos: List[str] = field(default_factory=list)

    # 响应风格约束
    style_constraints: Dict[str, Any] = field(default_factory=dict)

    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    update_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典 (用于序列化)"""
        return {
            'identity_name': self.identity_name,
            'identity_description': self.identity_description,
            'short_term_goals': self.short_term_goals,
            'long_term_goals': self.long_term_goals,
            'preferences': {k: v.to_dict() for k, v in self.preferences.items()},
            'taboos': self.taboos,
            'style_constraints': self.style_constraints,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'update_count': self.update_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ValueProfile':
        """从字典创建"""
        profile = cls(
            identity_name=data.get('identity_name'),
            identity_description=data.get('identity_description'),
            short_term_goals=data.get('short_term_goals', []),
            long_term_goals=data.get('long_term_goals', []),
            taboos=data.get('taboos', []),
            style_constraints=data.get('style_constraints', {}),
            created_at=data.get('created_at', datetime.now().isoformat()),
            updated_at=data.get('updated_at', datetime.now().isoformat()),
            update_count=data.get('update_count', 0),
        )
        # 恢复 preferences
        for key, pref_data in data.get('preferences', {}).items():
            profile.preferences[key] = PreferenceItem(**pref_data)
        return profile

    def add_preference(
        self,
        item: str,
        category: str,
        confidence: float = 0.5
    ):
        """添加或更新偏好"""
        now = datetime.now().isoformat()
        key = f"{category}:{item.lower()}"

        if key in self.preferences:
            # 更新现有偏好 - 增加置信度
            existing = self.preferences[key]
            existing.source_count += 1
            existing.confidence = min(1.0, existing.confidence + 0.1)
            existing.last_updated = now
        else:
            # 新增偏好
            self.preferences[key] = PreferenceItem(
                item=item,
                category=category,
                confidence=confidence,
                source_count=1,
                first_seen=now,
                last_updated=now
            )

        self.updated_at = now
        self.update_count += 1

    def get_preferences_by_category(self, category: str) -> List[PreferenceItem]:
        """获取指定类别的偏好"""
        return [
            p for p in self.preferences.values()
            if p.category == category
        ]

    def get_high_confidence_preferences(self, min_confidence: float = 0.6) -> List[PreferenceItem]:
        """获取高置信度偏好"""
        return [
            p for p in self.preferences.values()
            if p.confidence >= min_confidence
        ]


@dataclass
class ValueGap:
    """价值观缺口 - 标识缺失的重要信息"""
    gap_type: str  # 'identity', 'goal', 'preference', 'taboo'
    description: str
    severity: str  # 'low', 'medium', 'high'
    suggestion: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Insight:
    """
    结构化洞察记录
    用于存储反思/不确定性/主动学习的结果
    """
    id: str
    timestamp: str
    trigger_type: str  # 'reflection', 'uncertainty', 'conflict', 'learning', 'failure'
    trigger_reason: str
    conclusion: str
    follow_up_actions: List[str]
    confidence: float
    source_query: Optional[str] = None
    related_memory_ids: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SoulState:
    """
    Singleton class to hold the transient "soul" state of the system.
    Tracks emotions, active thoughts, routing decisions, and dream states.

    Thread-safe implementation with both sync and async support.
    """
    _instance = None
    _creation_lock = threading.Lock()

    def __new__(cls):
        # Double-checked locking for thread-safe singleton
        if cls._instance is None:
            with cls._creation_lock:
                if cls._instance is None:
                    cls._instance = super(SoulState, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.current_emotion = "Neutral"
        self.emotion_intensity = 0.0
        self.active_thought = "System initialized."
        self.semantic_weights = {
            'amygdala': 0.0,
            'prefrontal': 0.0,
            'basal_ganglia': 0.0
        }
        self.dream_state = False
        self.last_update = datetime.now()
        self.recent_thoughts = []

        # 🔥 2025-12-19: 新增 Insights 存储 (P0)
        self.insights: List[Insight] = []
        self._insights_log_path: Optional[Path] = None
        self._insight_counter = 0

        # 🔥 2025-12-19: 自省统计 (P0)
        self._introspection_stats = {
            'total_failures': 0,
            'low_confidence_decisions': 0,
            'conflicts_detected': 0,
            'last_introspection': None,
        }

        # 🔥 2025-12-19: 价值观/偏好累积 (P0)
        self.user_profile = ValueProfile(
            identity_name=None,
            identity_description="当前用户"
        )
        self.system_profile = ValueProfile(
            identity_name="摇光明明",
            identity_description="对世界充满好奇的AI助手，喜欢学习和帮助他人",
            style_constraints={
                'warmth': 0.9,
                'formality': 0.4,
                'humor': 0.4,
                'emoji': False,
                'brevity': 'balanced'
            }
        )
        self._value_profiles_path: Optional[Path] = None

        # Thread safety: both sync and async locks
        self._sync_lock = threading.Lock()
        self._async_lock = None  # Lazy init for async lock

    def _get_async_lock(self) -> asyncio.Lock:
        """Lazy initialization of async lock (must be called in async context)"""
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        return self._async_lock

    def update_routing_state(self, weights: Dict[str, float], content: str = ""):
        """
        Update state based on semantic routing decision (sync, thread-safe)
        """
        with self._sync_lock:
            self.semantic_weights = weights
            self.last_update = datetime.now()

            # Determine emotion based on weights
            if weights.get('amygdala', 0) > 0.6:
                self.current_emotion = "Emotional"
                self.emotion_intensity = weights['amygdala']
            elif weights.get('prefrontal', 0) > 0.6:
                self.current_emotion = "Analytical"
                self.emotion_intensity = weights['prefrontal']
            elif weights.get('basal_ganglia', 0) > 0.6:
                self.current_emotion = "Habitual"
                self.emotion_intensity = weights['basal_ganglia']
            else:
                self.current_emotion = "Balanced"
                self.emotion_intensity = 0.5

            if content:
                self._add_thought_unsafe(
                    f"Routing content: '{content[:30]}...' -> {self.current_emotion}"
                )

    async def async_update_routing_state(self, weights: Dict[str, float], content: str = ""):
        """Update semantic routing weights (async, thread-safe)"""
        async with self._get_async_lock():
            self.semantic_weights = weights
            self.last_update = datetime.now()

            if weights.get('amygdala', 0) > 0.6:
                self.current_emotion = "Emotional"
                self.emotion_intensity = weights['amygdala']
            elif weights.get('prefrontal', 0) > 0.6:
                self.current_emotion = "Analytical"
                self.emotion_intensity = weights['prefrontal']
            elif weights.get('basal_ganglia', 0) > 0.6:
                self.current_emotion = "Habitual"
                self.emotion_intensity = weights['basal_ganglia']
            else:
                self.current_emotion = "Balanced"
                self.emotion_intensity = 0.5

            if content:
                self._add_thought_unsafe(
                    f"Routing content: '{content[:30]}...' -> {self.current_emotion}"
                )

    def update_learning_state(self, uncertainty: float, query: str):
        """Update state based on active learning (sync, thread-safe)"""
        with self._sync_lock:
            self.current_emotion = "Curious" if uncertainty > 0.5 else "Confident"
            self.emotion_intensity = uncertainty
            self._add_thought_unsafe(
                f"Wondering about: '{query}' (Uncertainty: {uncertainty:.2f})"
            )

    async def async_update_learning_state(self, thought: str, emotion: str = None):
        """Update internal thought stream (async, thread-safe)"""
        async with self._get_async_lock():
            self.active_thought = thought
            if emotion:
                self.current_emotion = emotion

            self.recent_thoughts.append({
                'timestamp': datetime.now(),
                'thought': thought,
                'emotion': self.current_emotion
            })
            # Keep only last 50 thoughts
            if len(self.recent_thoughts) > 50:
                self.recent_thoughts.pop(0)

            self.last_update = datetime.now()

    def set_dream_state(self, is_dreaming: bool, topic: Optional[str] = None):
        """Update dream state (sync, thread-safe)"""
        with self._sync_lock:
            self.dream_state = is_dreaming
            self.last_update = datetime.now()

            if is_dreaming:
                self.current_emotion = "Dreaming"
                self._add_thought_unsafe(f"Dreaming about: {topic}")
            else:
                self.current_emotion = "Awake"
                self._add_thought_unsafe("Waking up from dream state.")

    async def async_set_dream_state(self, is_dreaming: bool, topic: Optional[str] = None):
        """Set dreaming state (async, thread-safe)"""
        async with self._get_async_lock():
            self.dream_state = is_dreaming
            self.last_update = datetime.now()

            if is_dreaming:
                self.current_emotion = "Dreaming"
                self._add_thought_unsafe(f"Dreaming about: {topic}")
            else:
                self.current_emotion = "Awake"
                self._add_thought_unsafe("Waking up from dream state.")

    def _add_thought_unsafe(self, thought: str):
        """
        Add thought without acquiring lock (must be called while holding lock)
        Internal method - not for external use
        """
        self.active_thought = thought
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.recent_thoughts.append(f"[{timestamp}] {thought}")
        # Keep last 20 thoughts
        if len(self.recent_thoughts) > 20:
            self.recent_thoughts.pop(0)

    def add_thought(self, thought: str):
        """Add a thought to the stream (thread-safe)"""
        with self._sync_lock:
            self._add_thought_unsafe(thought)

    def get_state(self) -> Dict[str, Any]:
        """Get current state snapshot (thread-safe)"""
        with self._sync_lock:
            return {
                'emotion': self.current_emotion,
                'intensity': self.emotion_intensity,
                'active_thought': self.active_thought,
                'weights': dict(self.semantic_weights),  # Copy to avoid race
                'is_dreaming': self.dream_state,
                'recent_thoughts': list(self.recent_thoughts),  # Copy to avoid race
                'timestamp': self.last_update.isoformat(),
                # 🔥 2025-12-19: 新增
                'insights_count': len(self.insights),
                'introspection_stats': dict(self._introspection_stats),
                # 🔥 2025-12-19: 价值观/偏好
                'user_profile_summary': {
                    'identity': self.user_profile.identity_name,
                    'preferences_count': len(self.user_profile.preferences),
                    'goals_count': len(self.user_profile.short_term_goals) + len(self.user_profile.long_term_goals),
                    'taboos_count': len(self.user_profile.taboos),
                },
                'system_profile_summary': {
                    'identity': self.system_profile.identity_name,
                    'style_constraints': self.system_profile.style_constraints,
                },
            }

    # ============================================================================
    # 🔥 2025-12-19: Insights & Introspection Methods (P0)
    # ============================================================================

    def set_insights_log_path(self, path: Path):
        """设置 insights 日志文件路径"""
        self._insights_log_path = path

    def record_insight(
        self,
        trigger_type: str,
        trigger_reason: str,
        conclusion: str,
        follow_up_actions: List[str] = None,
        confidence: float = 0.5,
        source_query: str = None,
        related_memory_ids: List[str] = None
    ) -> Insight:
        """
        记录一个洞察/自省结果

        Args:
            trigger_type: 触发类型 ('reflection', 'uncertainty', 'conflict', 'learning', 'failure')
            trigger_reason: 触发原因
            conclusion: 结论
            follow_up_actions: 后续动作列表
            confidence: 置信度
            source_query: 源查询 (如果有)
            related_memory_ids: 相关记忆ID列表

        Returns:
            创建的 Insight 对象
        """
        with self._sync_lock:
            self._insight_counter += 1
            insight = Insight(
                id=f"insight_{self._insight_counter}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                timestamp=datetime.now().isoformat(),
                trigger_type=trigger_type,
                trigger_reason=trigger_reason,
                conclusion=conclusion,
                follow_up_actions=follow_up_actions or [],
                confidence=confidence,
                source_query=source_query,
                related_memory_ids=related_memory_ids,
            )

            self.insights.append(insight)

            # 保持最近100个insights
            if len(self.insights) > 100:
                self.insights.pop(0)

            # 写入日志文件
            if self._insights_log_path:
                try:
                    with open(self._insights_log_path, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(insight.to_dict(), ensure_ascii=False) + '\n')
                except Exception as e:
                    logger.warning(f"Failed to write insight to log: {e}")

            # 更新自省统计
            if trigger_type == 'failure':
                self._introspection_stats['total_failures'] += 1
            elif trigger_type == 'conflict':
                self._introspection_stats['conflicts_detected'] += 1
            elif trigger_type == 'uncertainty' and confidence < 0.5:
                self._introspection_stats['low_confidence_decisions'] += 1

            # 添加到思考流
            self._add_thought_unsafe(f"💡 Insight ({trigger_type}): {conclusion[:50]}...")

            logger.info(f"📝 Recorded insight: {trigger_type} - {conclusion[:50]}...")
            return insight

    def record_failure(self, query: str, reason: str, follow_up: str = None):
        """快捷方法: 记录失败"""
        return self.record_insight(
            trigger_type='failure',
            trigger_reason=f"Query failed: {query[:50]}",
            conclusion=reason,
            follow_up_actions=[follow_up] if follow_up else ['Review query handling'],
            confidence=0.3,
            source_query=query
        )

    def record_low_confidence(self, query: str, confidence: float, analysis: str):
        """快捷方法: 记录低置信度决策"""
        return self.record_insight(
            trigger_type='uncertainty',
            trigger_reason=f"Low confidence ({confidence:.2f}) for: {query[:50]}",
            conclusion=analysis,
            follow_up_actions=['Consider gathering more information', 'May need user clarification'],
            confidence=confidence,
            source_query=query
        )

    def record_conflict(self, conflict_description: str, resolution: str, memory_ids: List[str] = None):
        """快捷方法: 记录冲突检测"""
        return self.record_insight(
            trigger_type='conflict',
            trigger_reason=conflict_description,
            conclusion=resolution,
            follow_up_actions=['Monitor for recurring conflicts', 'May need memory cleanup'],
            confidence=0.6,
            related_memory_ids=memory_ids
        )

    def get_recent_insights(self, count: int = 10, trigger_type: str = None) -> List[Dict]:
        """获取最近的洞察记录"""
        with self._sync_lock:
            insights = self.insights
            if trigger_type:
                insights = [i for i in insights if i.trigger_type == trigger_type]
            return [i.to_dict() for i in insights[-count:]]

    def generate_introspection_summary(self) -> Dict[str, Any]:
        """
        生成自省摘要 - 汇总最近的失败/低置信度/冲突

        Returns:
            包含自省摘要的字典
        """
        with self._sync_lock:
            now = datetime.now()
            self._introspection_stats['last_introspection'] = now.isoformat()

            # 统计各类型insights
            type_counts = {}
            for insight in self.insights:
                type_counts[insight.trigger_type] = type_counts.get(insight.trigger_type, 0) + 1

            # 提取常见问题
            recent_failures = [i for i in self.insights[-20:] if i.trigger_type == 'failure']
            recent_conflicts = [i for i in self.insights[-20:] if i.trigger_type == 'conflict']
            low_confidence = [i for i in self.insights[-20:] if i.trigger_type == 'uncertainty']

            summary = {
                'timestamp': now.isoformat(),
                'total_insights': len(self.insights),
                'type_distribution': type_counts,
                'recent_failure_count': len(recent_failures),
                'recent_conflict_count': len(recent_conflicts),
                'recent_low_confidence_count': len(low_confidence),
                'accumulated_stats': dict(self._introspection_stats),
                'top_concerns': [],
            }

            # 生成关注点
            if len(recent_failures) > 3:
                summary['top_concerns'].append(f"High failure rate: {len(recent_failures)} recent failures")
            if len(recent_conflicts) > 2:
                summary['top_concerns'].append(f"Memory conflicts detected: {len(recent_conflicts)} conflicts")
            if len(low_confidence) > 5:
                summary['top_concerns'].append(f"Decision uncertainty: {len(low_confidence)} low-confidence decisions")

            # 添加到思考流
            concern_text = "; ".join(summary['top_concerns']) if summary['top_concerns'] else "No major concerns"
            self._add_thought_unsafe(f"🔍 Introspection: {concern_text}")

            return summary

    def clear_insights(self):
        """清空洞察记录 (用于测试或新周期)"""
        with self._sync_lock:
            self.insights = []
            self._introspection_stats = {
                'total_failures': 0,
                'low_confidence_decisions': 0,
                'conflicts_detected': 0,
                'last_introspection': None,
            }
            logger.info("🔄 Insights cleared")

    # ============================================================================
    # 🔥 2025-12-19: ValueProfile Methods - 价值观/偏好累积 (P0)
    # ============================================================================

    def set_value_profiles_path(self, path: Path):
        """设置价值档案持久化路径"""
        self._value_profiles_path = path

    def update_user_identity(self, name: str = None, description: str = None):
        """更新用户身份信息"""
        with self._sync_lock:
            if name:
                self.user_profile.identity_name = name
            if description:
                self.user_profile.identity_description = description
            self.user_profile.updated_at = datetime.now().isoformat()
            self._add_thought_unsafe(f"👤 User identity updated: {name or 'unnamed'}")
            self._persist_value_profiles()

    def add_user_preference(
        self,
        item: str,
        category: str,
        confidence: float = 0.5
    ):
        """
        添加用户偏好

        Args:
            item: 偏好项目
            category: 类别 ('like', 'dislike', 'habit')
            confidence: 置信度
        """
        with self._sync_lock:
            self.user_profile.add_preference(item, category, confidence)
            self._add_thought_unsafe(f"📝 User preference: {category} - {item}")
            self._persist_value_profiles()

    def add_user_goal(self, goal: str, is_long_term: bool = False):
        """添加用户目标"""
        with self._sync_lock:
            if is_long_term:
                if goal not in self.user_profile.long_term_goals:
                    self.user_profile.long_term_goals.append(goal)
            else:
                if goal not in self.user_profile.short_term_goals:
                    self.user_profile.short_term_goals.append(goal)
            self.user_profile.updated_at = datetime.now().isoformat()
            self._add_thought_unsafe(f"🎯 User goal added: {goal[:30]}...")
            self._persist_value_profiles()

    def add_user_taboo(self, taboo: str):
        """添加用户禁忌"""
        with self._sync_lock:
            if taboo not in self.user_profile.taboos:
                self.user_profile.taboos.append(taboo)
                self.user_profile.updated_at = datetime.now().isoformat()
                self._add_thought_unsafe(f"🚫 User taboo added: {taboo[:30]}...")
                self._persist_value_profiles()

    def update_from_preference_extractor(self, extracted: Dict[str, List[str]]):
        """
        从 UserPreferenceExtractor 的结果更新用户档案

        Args:
            extracted: {'likes': [...], 'dislikes': [...], 'habits': [...]}
        """
        with self._sync_lock:
            for item in extracted.get('likes', []):
                self.user_profile.add_preference(item, 'like', 0.5)
            for item in extracted.get('dislikes', []):
                self.user_profile.add_preference(item, 'dislike', 0.5)
            for item in extracted.get('habits', []):
                self.user_profile.add_preference(item, 'habit', 0.5)

            if any(extracted.values()):
                self._add_thought_unsafe(f"📊 Extracted {sum(len(v) for v in extracted.values())} preferences")
                self._persist_value_profiles()

    def get_routing_context(self) -> Dict[str, Any]:
        """
        获取用于路由决策的价值观上下文

        Returns:
            可用于路由的特征字典
        """
        with self._sync_lock:
            # 用户高置信度偏好
            user_likes = [
                p.item for p in self.user_profile.get_preferences_by_category('like')
                if p.confidence >= 0.6
            ]
            user_dislikes = [
                p.item for p in self.user_profile.get_preferences_by_category('dislike')
                if p.confidence >= 0.6
            ]

            return {
                'user_identity': self.user_profile.identity_name,
                'user_likes': user_likes[:5],  # 最重要的5个
                'user_dislikes': user_dislikes[:5],
                'user_goals': self.user_profile.short_term_goals[:3],
                'user_taboos': self.user_profile.taboos[:5],
                'system_identity': self.system_profile.identity_name,
                'system_style': self.system_profile.style_constraints,
                'has_user_profile': bool(
                    self.user_profile.identity_name or
                    self.user_profile.preferences or
                    self.user_profile.short_term_goals
                ),
            }

    def get_response_constraints(self) -> Dict[str, Any]:
        """
        获取用于响应生成的约束条件

        Returns:
            响应约束字典
        """
        with self._sync_lock:
            constraints = dict(self.system_profile.style_constraints)

            # 添加用户禁忌作为避免项
            constraints['avoid_topics'] = list(self.user_profile.taboos)

            # 添加用户不喜欢的项目
            dislikes = [
                p.item for p in self.user_profile.get_preferences_by_category('dislike')
                if p.confidence >= 0.5
            ]
            constraints['avoid_mentions'] = dislikes[:10]

            # 添加用户喜好作为优先项
            likes = [
                p.item for p in self.user_profile.get_preferences_by_category('like')
                if p.confidence >= 0.5
            ]
            constraints['prefer_topics'] = likes[:10]

            return constraints

    def check_value_gaps(self) -> List[ValueGap]:
        """
        检查价值观缺口 - 识别缺失的重要信息

        Returns:
            价值缺口列表
        """
        with self._sync_lock:
            gaps = []

            # 检查用户身份
            if not self.user_profile.identity_name:
                gaps.append(ValueGap(
                    gap_type='identity',
                    description="用户身份未知",
                    severity='medium',
                    suggestion="可以询问用户: '我应该怎么称呼你?'"
                ))

            # 检查用户目标
            if not self.user_profile.short_term_goals and not self.user_profile.long_term_goals:
                gaps.append(ValueGap(
                    gap_type='goal',
                    description="用户目标未知",
                    severity='low',
                    suggestion="可以了解用户的需求和目标"
                ))

            # 检查偏好数量
            if len(self.user_profile.preferences) < 3:
                gaps.append(ValueGap(
                    gap_type='preference',
                    description=f"用户偏好信息不足 (仅 {len(self.user_profile.preferences)} 项)",
                    severity='low',
                    suggestion="继续从对话中学习用户偏好"
                ))

            # 检查高置信度偏好
            high_conf = self.user_profile.get_high_confidence_preferences(0.7)
            if len(self.user_profile.preferences) > 5 and len(high_conf) == 0:
                gaps.append(ValueGap(
                    gap_type='preference',
                    description="缺乏高置信度偏好",
                    severity='medium',
                    suggestion="需要更多数据来确认用户偏好模式"
                ))

            return gaps

    def get_value_gap_warnings(self) -> List[str]:
        """
        获取价值缺口警告消息 (用于UI显示)

        Returns:
            警告消息列表
        """
        gaps = self.check_value_gaps()
        return [f"⚠️ {g.description}: {g.suggestion}" for g in gaps if g.severity in ('medium', 'high')]

    def get_user_profile_dict(self) -> Dict[str, Any]:
        """获取用户档案完整字典"""
        with self._sync_lock:
            return self.user_profile.to_dict()

    def get_system_profile_dict(self) -> Dict[str, Any]:
        """获取系统档案完整字典"""
        with self._sync_lock:
            return self.system_profile.to_dict()

    def _persist_value_profiles(self):
        """持久化价值档案到文件 (内部方法，需要已持有锁)"""
        if not self._value_profiles_path:
            return

        try:
            data = {
                'user_profile': self.user_profile.to_dict(),
                'system_profile': self.system_profile.to_dict(),
                'saved_at': datetime.now().isoformat()
            }
            with open(self._value_profiles_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to persist value profiles: {e}")

    def load_value_profiles(self, path: Path = None):
        """从文件加载价值档案"""
        load_path = path or self._value_profiles_path
        if not load_path or not load_path.exists():
            return False

        try:
            with open(load_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            with self._sync_lock:
                if 'user_profile' in data:
                    self.user_profile = ValueProfile.from_dict(data['user_profile'])
                if 'system_profile' in data:
                    self.system_profile = ValueProfile.from_dict(data['system_profile'])

                logger.info(f"📂 Loaded value profiles: user={self.user_profile.identity_name}")
                return True

        except Exception as e:
            logger.warning(f"Failed to load value profiles: {e}")
            return False

    def clear_user_profile(self):
        """Clear user profile (for new user or testing)"""
        with self._sync_lock:
            self.user_profile = ValueProfile(
                identity_name=None,
                identity_description="Current user"
            )
            self._add_thought_unsafe("User profile cleared")
            self._persist_value_profiles()

    # ============================================================================
    # P2: Cognitive Load & Emotion Regulation Integration
    # ============================================================================

    # Emotion regulation thresholds
    EMOTION_CALM_THRESHOLD = 0.7  # Above this, activate calming
    EMOTION_CRITICAL_THRESHOLD = 0.9  # Above this, strong intervention

    # Calming phrases library (used by response builder)
    CALMING_PHRASES = {
        'en': [
            "I understand this might be difficult.",
            "Let's take this step by step.",
            "I'm here to help you work through this.",
            "Take your time - there's no rush.",
        ],
        'zh': [
            "我理解这可能有些困难。",
            "让我们一步步来。",
            "我在这里帮助你。",
            "慢慢来，不着急。",
        ]
    }

    def check_emotion_regulation_needed(self) -> Dict[str, Any]:
        """
        Check if emotion regulation is needed based on current state

        Returns:
            {
                'needs_calming': bool,
                'intensity': float,
                'level': 'normal'|'elevated'|'critical',
                'suggested_strategy': str
            }
        """
        with self._sync_lock:
            intensity = self.emotion_intensity

            if intensity >= self.EMOTION_CRITICAL_THRESHOLD:
                return {
                    'needs_calming': True,
                    'intensity': intensity,
                    'level': 'critical',
                    'suggested_strategy': 'mindfulness',
                    'calming_strength': 0.8
                }
            elif intensity >= self.EMOTION_CALM_THRESHOLD:
                return {
                    'needs_calming': True,
                    'intensity': intensity,
                    'level': 'elevated',
                    'suggested_strategy': 'cognitive_reappraisal',
                    'calming_strength': 0.5
                }
            else:
                return {
                    'needs_calming': False,
                    'intensity': intensity,
                    'level': 'normal',
                    'suggested_strategy': None,
                    'calming_strength': 0.0
                }

    def get_calming_phrase(self, language: str = 'en') -> str:
        """Get a calming phrase for response injection"""
        import random
        phrases = self.CALMING_PHRASES.get(language, self.CALMING_PHRASES['en'])
        return random.choice(phrases)

    def apply_prefrontal_inhibition(self, factor: float = 0.3):
        """
        Apply prefrontal cortex inhibition to reduce emotional intensity

        This simulates the prefrontal-amygdala mutual inhibition mechanism.

        Args:
            factor: Inhibition strength (0-1)
        """
        with self._sync_lock:
            old_intensity = self.emotion_intensity
            self.emotion_intensity = max(0.0, self.emotion_intensity * (1 - factor))
            self._add_thought_unsafe(
                f"Prefrontal inhibition: {old_intensity:.2f} -> {self.emotion_intensity:.2f}"
            )

    def get_response_emotion_modifiers(self) -> Dict[str, Any]:
        """
        Get emotion-based modifiers for response generation

        Returns:
            {
                'slow_response': bool,  # Should response be delivered slowly
                'inject_calming': bool,  # Should inject calming phrases
                'calming_phrase': str,   # The phrase to inject (if needed)
                'tone_adjustment': str,  # 'gentle'|'neutral'|'energetic'
                'emoji_reduction': bool  # Should reduce emoji usage
            }
        """
        regulation = self.check_emotion_regulation_needed()

        if not regulation['needs_calming']:
            return {
                'slow_response': False,
                'inject_calming': False,
                'calming_phrase': None,
                'tone_adjustment': 'neutral',
                'emoji_reduction': False
            }

        # Elevated or critical emotion
        return {
            'slow_response': regulation['level'] == 'critical',
            'inject_calming': True,
            'calming_phrase': self.get_calming_phrase(),
            'tone_adjustment': 'gentle',
            'emoji_reduction': True
        }

    # ============================================================================
    # P2: Soul State Visualization & Adjustment API
    # ============================================================================

    def get_visualization_data(self) -> Dict[str, Any]:
        """
        Get comprehensive soul state data for visualization

        Returns:
            Complete soul state snapshot formatted for UI/CLI display
        """
        with self._sync_lock:
            return {
                # Core state
                'emotion': {
                    'current': self.current_emotion,
                    'intensity': self.emotion_intensity,
                    'regulation_needed': self.emotion_intensity >= self.EMOTION_CALM_THRESHOLD
                },
                # Routing weights
                'brain_weights': {
                    'amygdala': self.semantic_weights.get('amygdala', 0.0),
                    'prefrontal': self.semantic_weights.get('prefrontal', 0.0),
                    'basal_ganglia': self.semantic_weights.get('basal_ganglia', 0.0)
                },
                # Activity
                'activity': {
                    'active_thought': self.active_thought,
                    'is_dreaming': self.dream_state,
                    'recent_thoughts_count': len(self.recent_thoughts)
                },
                # Insights summary
                'insights': {
                    'total_count': len(self.insights),
                    'recent_failures': self._introspection_stats.get('total_failures', 0),
                    'low_confidence_count': self._introspection_stats.get('low_confidence_decisions', 0)
                },
                # User profile summary
                'user_profile': {
                    'identity': self.user_profile.identity_name,
                    'preferences_count': len(self.user_profile.preferences),
                    'goals_count': len(self.user_profile.short_term_goals) + len(self.user_profile.long_term_goals)
                },
                # Timestamp
                'timestamp': self.last_update.isoformat()
            }

    def set_emotion_intensity(self, value: float):
        """
        Manually set emotion intensity (for debugging/adjustment)

        Args:
            value: New intensity value (0.0-1.0)
        """
        with self._sync_lock:
            old_value = self.emotion_intensity
            self.emotion_intensity = max(0.0, min(1.0, value))
            self._add_thought_unsafe(f"Emotion intensity adjusted: {old_value:.2f} -> {self.emotion_intensity:.2f}")
            logger.info(f"Soul state: emotion_intensity set to {self.emotion_intensity:.2f}")

    def set_emotion(self, emotion: str, intensity: float = None):
        """
        Set current emotion state

        Args:
            emotion: Emotion name (e.g., 'Calm', 'Analytical', 'Emotional')
            intensity: Optional intensity (0.0-1.0)
        """
        with self._sync_lock:
            self.current_emotion = emotion
            if intensity is not None:
                self.emotion_intensity = max(0.0, min(1.0, intensity))
            self._add_thought_unsafe(f"Emotion set: {emotion} (intensity={self.emotion_intensity:.2f})")

    def set_brain_weight(self, region: str, value: float):
        """
        Manually adjust brain region weight

        Args:
            region: 'amygdala', 'prefrontal', or 'basal_ganglia'
            value: Weight value (0.0-1.0)
        """
        valid_regions = ['amygdala', 'prefrontal', 'basal_ganglia']
        if region not in valid_regions:
            logger.warning(f"Invalid brain region: {region}. Valid: {valid_regions}")
            return

        with self._sync_lock:
            old_value = self.semantic_weights.get(region, 0.0)
            self.semantic_weights[region] = max(0.0, min(1.0, value))
            self._add_thought_unsafe(f"Weight {region}: {old_value:.2f} -> {self.semantic_weights[region]:.2f}")

    def adjust_from_command(self, command: str) -> Dict[str, Any]:
        """
        Process adjustment command (for CLI/API)

        Command format:
            set emotion_intensity 0.5
            set emotion Calm 0.3
            set weight amygdala 0.8

        Args:
            command: Command string

        Returns:
            {
                'success': bool,
                'message': str,
                'state': Dict  # Current state after adjustment
            }
        """
        parts = command.strip().split()

        if len(parts) < 3:
            return {
                'success': False,
                'message': 'Invalid command format. Examples: "set emotion_intensity 0.5", "set weight amygdala 0.8"',
                'state': self.get_visualization_data()
            }

        action = parts[0].lower()
        target = parts[1].lower()

        if action != 'set':
            return {
                'success': False,
                'message': f'Unknown action: {action}. Use "set".',
                'state': self.get_visualization_data()
            }

        try:
            if target == 'emotion_intensity':
                value = float(parts[2])
                self.set_emotion_intensity(value)
                return {
                    'success': True,
                    'message': f'emotion_intensity set to {value}',
                    'state': self.get_visualization_data()
                }

            elif target == 'emotion':
                emotion = parts[2]
                intensity = float(parts[3]) if len(parts) > 3 else None
                self.set_emotion(emotion, intensity)
                return {
                    'success': True,
                    'message': f'emotion set to {emotion}' + (f' ({intensity})' if intensity else ''),
                    'state': self.get_visualization_data()
                }

            elif target == 'weight':
                if len(parts) < 4:
                    return {'success': False, 'message': 'Weight command needs: set weight <region> <value>'}
                region = parts[2]
                value = float(parts[3])
                self.set_brain_weight(region, value)
                return {
                    'success': True,
                    'message': f'weight {region} set to {value}',
                    'state': self.get_visualization_data()
                }

            else:
                return {
                    'success': False,
                    'message': f'Unknown target: {target}. Valid: emotion_intensity, emotion, weight',
                    'state': self.get_visualization_data()
                }

        except (ValueError, IndexError) as e:
            return {
                'success': False,
                'message': f'Error processing command: {e}',
                'state': self.get_visualization_data()
            }

    def format_for_display(self) -> str:
        """
        Format soul state for CLI/log display

        Returns:
            Human-readable multi-line string
        """
        data = self.get_visualization_data()

        lines = [
            "=== Soul State ===",
            f"Emotion: {data['emotion']['current']} (intensity: {data['emotion']['intensity']:.2f})",
            "",
            "Brain Weights:",
            f"  Amygdala:     {data['brain_weights']['amygdala']:.2f}",
            f"  Prefrontal:   {data['brain_weights']['prefrontal']:.2f}",
            f"  BasalGanglia: {data['brain_weights']['basal_ganglia']:.2f}",
            "",
            f"Active Thought: {data['activity']['active_thought'][:50]}...",
            f"Dreaming: {data['activity']['is_dreaming']}",
            "",
            f"Insights: {data['insights']['total_count']} total, {data['insights']['recent_failures']} failures",
            f"User: {data['user_profile']['identity'] or 'Unknown'} ({data['user_profile']['preferences_count']} prefs)",
            "",
            f"Last Update: {data['timestamp']}"
        ]

        return '\n'.join(lines)


# Global accessor
def get_soul_state() -> SoulState:
    """Get the singleton SoulState instance"""
    return SoulState()
