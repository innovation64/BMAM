"""
User Portrait Manager
用户肖像管理器 - 支持多用户持久化、增量更新和偏好演化追踪

解决"为什么没有用户肖像功能"的问题:
- 持久化用户肖像到数据库
- 增量更新而非每次重建
- 支持多用户隔离
- 追踪偏好演化
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class UserPortrait:
    """用户肖像数据结构"""
    user_id: str
    summary: str  # LLM生成的2-3句描述

    # 结构化偏好
    likes: List[str]
    dislikes: List[str]
    interests: List[str]
    habits: List[str]
    skills: List[str]
    goals: List[str]
    facts: List[str]  # 身份、背景等事实

    # 元数据
    memory_count: int = 0
    confidence: float = 0.0

    # 时间戳
    created_at: str = ""
    updated_at: str = ""
    last_accessed: str = ""

    # 版本控制
    version: int = 1
    update_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def to_context_string(self) -> str:
        """
        转换为上下文字符串,供LLM使用

        Returns:
            用户肖像摘要字符串
        """
        parts = []

        if self.summary:
            parts.append(f"User Profile: {self.summary}")

        if self.likes:
            parts.append(f"Likes: {', '.join(self.likes[:5])}")

        if self.dislikes:
            parts.append(f"Dislikes: {', '.join(self.dislikes[:5])}")

        if self.interests:
            parts.append(f"Interests: {', '.join(self.interests[:5])}")

        if self.facts:
            parts.append(f"Facts: {', '.join(self.facts[:5])}")

        return " | ".join(parts) if parts else "No user profile available"


class UserPortraitManager:
    """
    用户肖像管理器

    功能:
    - 持久化用户肖像到JSON文件
    - 增量更新偏好
    - 多用户隔离
    - 置信度计算
    """

    def __init__(self, storage_path: Path):
        """
        Args:
            storage_path: 用户肖像存储路径 (e.g., data/user_portraits.json)
        """
        self.storage_path = storage_path
        self.cache: Dict[str, UserPortrait] = {}  # user_id → Portrait

        # 创建存储目录
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # 加载已有肖像
        self._load_all_portraits()

    def _load_all_portraits(self):
        """从磁盘加载所有用户肖像"""
        if not self.storage_path.exists():
            logger.info(f"No existing user portraits found at {self.storage_path}")
            return

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for user_id, portrait_dict in data.items():
                # 转换为UserPortrait对象
                portrait = UserPortrait(**portrait_dict)
                self.cache[user_id] = portrait

            logger.info(f"Loaded {len(self.cache)} user portraits from {self.storage_path}")

        except Exception as e:
            logger.error(f"Failed to load user portraits: {e}")

    def _save_all_portraits(self):
        """保存所有用户肖像到磁盘"""
        try:
            data = {user_id: portrait.to_dict()
                   for user_id, portrait in self.cache.items()}

            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved {len(data)} user portraits to {self.storage_path}")

        except Exception as e:
            logger.error(f"Failed to save user portraits: {e}")

    def get_portrait(self, user_id: str) -> UserPortrait:
        """
        获取用户肖像,如果不存在则创建新的

        Args:
            user_id: 用户标识

        Returns:
            用户肖像对象
        """
        if user_id in self.cache:
            portrait = self.cache[user_id]
            portrait.last_accessed = datetime.now().isoformat()
            return portrait

        # 创建新肖像
        now = datetime.now().isoformat()
        portrait = UserPortrait(
            user_id=user_id,
            summary="",
            likes=[],
            dislikes=[],
            interests=[],
            habits=[],
            skills=[],
            goals=[],
            facts=[],
            created_at=now,
            updated_at=now,
            last_accessed=now
        )

        self.cache[user_id] = portrait
        logger.info(f"Created new user portrait for {user_id}")

        return portrait

    def update_preference(
        self,
        user_id: str,
        preference_type: str,
        preference_value: str,
        original_statement: str = ""
    ) -> bool:
        """
        增量更新用户偏好

        Args:
            user_id: 用户标识
            preference_type: 偏好类型 ('likes', 'dislikes', 'interests', etc.)
            preference_value: 偏好值
            original_statement: 原始陈述(可选)

        Returns:
            是否更新成功
        """
        portrait = self.get_portrait(user_id)

        # 获取对应的偏好列表
        pref_list_name = preference_type.lower()
        if not hasattr(portrait, pref_list_name):
            logger.warning(f"Unknown preference type: {preference_type}")
            return False

        pref_list = getattr(portrait, pref_list_name)

        # 检查是否已存在(去重)
        if preference_value in pref_list:
            logger.debug(f"Preference '{preference_value}' already exists for {user_id}")
            return False

        # 添加新偏好
        pref_list.append(preference_value)

        # 更新元数据
        portrait.memory_count += 1
        portrait.update_count += 1
        portrait.updated_at = datetime.now().isoformat()

        # 每5次更新或累计超过10个偏好时重新计算置信度
        if portrait.update_count % 5 == 0 or portrait.memory_count >= 10:
            portrait.confidence = self._calculate_confidence(portrait)

        # 持久化
        self._save_all_portraits()

        logger.info(f"Updated {user_id} portrait: {preference_type} += '{preference_value}'")
        return True

    def _calculate_confidence(self, portrait: UserPortrait) -> float:
        """
        计算用户肖像置信度

        考虑:
        1. 偏好数量
        2. 偏好多样性(覆盖多少类别)
        3. 时间因素(最近是否有更新)
        4. 一致性(是否有矛盾的偏好)

        Returns:
            置信度分数 (0.0-1.0)
        """
        # 1. 数量分数 (0-0.4)
        total_prefs = (
            len(portrait.likes) + len(portrait.dislikes) +
            len(portrait.interests) + len(portrait.habits) +
            len(portrait.skills) + len(portrait.goals) + len(portrait.facts)
        )
        quantity_score = min(0.4, total_prefs / 50)  # 50个偏好达到满分

        # 2. 多样性分数 (0-0.3)
        categories_with_data = sum([
            len(portrait.likes) > 0,
            len(portrait.dislikes) > 0,
            len(portrait.interests) > 0,
            len(portrait.habits) > 0,
            len(portrait.skills) > 0,
            len(portrait.goals) > 0,
            len(portrait.facts) > 0,
        ])
        diversity_score = min(0.3, categories_with_data / 7 * 0.3)  # 7个类别

        # 3. 时间分数 (0-0.2)
        try:
            days_since_update = (
                datetime.now() - datetime.fromisoformat(portrait.updated_at)
            ).days
            recency_score = max(0, 0.2 - days_since_update * 0.02)  # 10天后降为0
        except:
            recency_score = 0.1  # 默认分数

        # 4. 一致性分数 (0-0.1)
        # 检查 likes 和 dislikes 是否有冲突
        conflicts = set(portrait.likes) & set(portrait.dislikes)
        consistency_score = 0.1 if len(conflicts) == 0 else 0.0

        total = quantity_score + diversity_score + recency_score + consistency_score
        return min(1.0, total)

    def get_portrait_for_context(self, user_id: str) -> str:
        """
        获取用户肖像的上下文字符串(供LLM使用)

        Args:
            user_id: 用户标识

        Returns:
            用户肖像摘要字符串
        """
        portrait = self.get_portrait(user_id)
        return portrait.to_context_string()

    def list_all_users(self) -> List[str]:
        """列出所有用户ID"""
        return list(self.cache.keys())

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_users': len(self.cache),
            'avg_confidence': sum(p.confidence for p in self.cache.values()) / len(self.cache) if self.cache else 0,
            'total_memories': sum(p.memory_count for p in self.cache.values()),
            'storage_path': str(self.storage_path),
        }


# 全局单例
_portrait_manager: Optional[UserPortraitManager] = None


def get_user_portrait_manager(storage_path: Optional[Path] = None) -> UserPortraitManager:
    """
    获取全局用户肖像管理器单例

    Args:
        storage_path: 存储路径(首次调用时设置)

    Returns:
        UserPortraitManager实例
    """
    global _portrait_manager

    if _portrait_manager is None:
        if storage_path is None:
            from ...utils.paths import BMAMPaths
            storage_path = BMAMPaths.DATA_DIR / 'user_portraits.json'

        _portrait_manager = UserPortraitManager(storage_path)

    return _portrait_manager
