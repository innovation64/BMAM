"""
Silent Engram Store - 沉默印迹存储

基于论文 "Key-value memory in the brain" (Benna & Fusi, 2024)

核心概念：
- 遗忘不是信息删除，而是检索失败
- 被"遗忘"的记忆转为沉默印迹(Silent Engram)
- 沉默印迹保留检索键，但需要更强的线索才能激活
- 强线索可以重新激活沉默印迹，恢复完整记忆

神经科学依据：
- Richards & Frankland (2017): 记忆痕迹持续存在
- Tonegawa实验室: 光遗传学激活"遗忘"记忆
- 童年记忆可被气味、音乐重新唤醒

使用场景：
- 长期未访问的记忆
- 容量压力下被清理的记忆
- 用户明确"忘记"但可能需要恢复的记忆
"""

import logging
import json
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class SilentEngram:
    """
    沉默印迹 - 被遗忘但可重新激活的记忆痕迹

    保留：
    - 检索键（向量、实体、时间）
    - 激活阈值
    - 元数据

    不保留：
    - 完整内容（由外部ValueStore保存）
    """
    memory_id: str                          # 原始记忆ID
    key_vector: Optional[np.ndarray]        # 语义检索键（向量）
    key_entities: List[str]                 # 实体检索键
    key_timestamp: datetime                 # 时间检索键
    content_hash: str                       # 内容哈希（用于验证恢复）

    # 激活参数
    activation_threshold: float = 0.85      # 需要85%匹配度才能激活
    base_threshold: float = 0.85            # 基础阈值（用于恢复）

    # 元数据
    original_importance: float = 0.5        # 原始重要性
    original_emotion_intensity: float = 0.0 # 原始情感强度
    silence_timestamp: datetime = field(default_factory=datetime.now)  # 沉默时间
    silence_reason: str = "capacity"        # 沉默原因

    # 激活历史
    reactivation_attempts: int = 0          # 激活尝试次数
    reactivation_successes: int = 0         # 成功激活次数
    last_activation_attempt: Optional[datetime] = None

    def __post_init__(self):
        if isinstance(self.key_vector, list):
            self.key_vector = np.array(self.key_vector)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            'memory_id': self.memory_id,
            'key_vector': self.key_vector.tolist() if self.key_vector is not None else None,
            'key_entities': self.key_entities,
            'key_timestamp': self.key_timestamp.isoformat(),
            'content_hash': self.content_hash,
            'activation_threshold': self.activation_threshold,
            'base_threshold': self.base_threshold,
            'original_importance': self.original_importance,
            'original_emotion_intensity': self.original_emotion_intensity,
            'silence_timestamp': self.silence_timestamp.isoformat(),
            'silence_reason': self.silence_reason,
            'reactivation_attempts': self.reactivation_attempts,
            'reactivation_successes': self.reactivation_successes,
            'last_activation_attempt': self.last_activation_attempt.isoformat() if self.last_activation_attempt else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SilentEngram':
        """从字典反序列化"""
        return cls(
            memory_id=data['memory_id'],
            key_vector=np.array(data['key_vector']) if data.get('key_vector') else None,
            key_entities=data.get('key_entities', []),
            key_timestamp=datetime.fromisoformat(data['key_timestamp']),
            content_hash=data['content_hash'],
            activation_threshold=data.get('activation_threshold', 0.85),
            base_threshold=data.get('base_threshold', 0.85),
            original_importance=data.get('original_importance', 0.5),
            original_emotion_intensity=data.get('original_emotion_intensity', 0.0),
            silence_timestamp=datetime.fromisoformat(data['silence_timestamp']),
            silence_reason=data.get('silence_reason', 'capacity'),
            reactivation_attempts=data.get('reactivation_attempts', 0),
            reactivation_successes=data.get('reactivation_successes', 0),
            last_activation_attempt=datetime.fromisoformat(data['last_activation_attempt']) if data.get('last_activation_attempt') else None
        )


class SilentEngramStore:
    """
    沉默印迹存储管理器

    职责：
    1. 存储和管理沉默印迹
    2. 尝试激活匹配的沉默印迹
    3. 管理激活阈值的动态调整
    4. 持久化沉默印迹数据
    """

    def __init__(
        self,
        max_engrams: int = 10000,
        default_threshold: float = 0.85,
        threshold_decay_rate: float = 0.01,
        min_threshold: float = 0.6,
        persistence_path: Optional[str] = None
    ):
        """
        初始化沉默印迹存储

        Args:
            max_engrams: 最大沉默印迹数量
            default_threshold: 默认激活阈值
            threshold_decay_rate: 阈值随时间衰减率
            min_threshold: 最小激活阈值
            persistence_path: 持久化文件路径
        """
        self.max_engrams = max_engrams
        self.default_threshold = default_threshold
        self.threshold_decay_rate = threshold_decay_rate
        self.min_threshold = min_threshold
        self.persistence_path = persistence_path

        # 存储结构
        self.engrams: Dict[str, SilentEngram] = {}

        # 索引结构（用于快速检索）
        self.entity_index: Dict[str, Set[str]] = defaultdict(set)  # entity -> memory_ids
        self.time_index: Dict[str, Set[str]] = {}  # date_str -> memory_ids

        # 统计
        self.total_silenced: int = 0
        self.total_reactivated: int = 0
        self.total_permanently_lost: int = 0

        # 加载持久化数据
        if persistence_path:
            self._load_from_disk()

        logger.info(f"SilentEngramStore initialized: max={max_engrams}, threshold={default_threshold}")

    def silence_memory(
        self,
        memory_id: str,
        content: str,
        embedding: Optional[np.ndarray] = None,
        entities: Optional[List[str]] = None,
        timestamp: Optional[datetime] = None,
        importance: float = 0.5,
        emotion_intensity: float = 0.0,
        reason: str = "capacity"
    ) -> SilentEngram:
        """
        将记忆转为沉默印迹

        Args:
            memory_id: 记忆ID
            content: 记忆内容（用于生成哈希）
            embedding: 语义向量
            entities: 相关实体
            timestamp: 时间戳
            importance: 原始重要性
            emotion_intensity: 原始情感强度
            reason: 沉默原因

        Returns:
            创建的沉默印迹
        """
        # 生成内容哈希
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # 创建沉默印迹
        engram = SilentEngram(
            memory_id=memory_id,
            key_vector=embedding.copy() if embedding is not None else None,
            key_entities=entities or [],
            key_timestamp=timestamp or datetime.now(),
            content_hash=content_hash,
            activation_threshold=self.default_threshold,
            base_threshold=self.default_threshold,
            original_importance=importance,
            original_emotion_intensity=emotion_intensity,
            silence_timestamp=datetime.now(),
            silence_reason=reason
        )

        # 容量检查
        if len(self.engrams) >= self.max_engrams:
            self._evict_oldest_engram()

        # 存储
        self.engrams[memory_id] = engram

        # 建立索引
        for entity in engram.key_entities:
            self.entity_index[entity].add(memory_id)

        date_key = engram.key_timestamp.strftime('%Y-%m-%d')
        if date_key not in self.time_index:
            self.time_index[date_key] = set()
        self.time_index[date_key].add(memory_id)

        self.total_silenced += 1

        logger.debug(f"Memory silenced: {memory_id}, reason={reason}, entities={entities}")

        return engram

    def try_reactivate(
        self,
        query_vector: Optional[np.ndarray] = None,
        query_entities: Optional[List[str]] = None,
        query_time_range: Optional[Tuple[datetime, datetime]] = None,
        boost_factor: float = 1.0
    ) -> List[Tuple[str, float, SilentEngram]]:
        """
        尝试重新激活沉默印迹

        Args:
            query_vector: 查询向量
            query_entities: 查询实体
            query_time_range: 查询时间范围
            boost_factor: 激活增强因子（强线索时增大）

        Returns:
            [(memory_id, activation_score, engram), ...] 激活的印迹列表
        """
        if not self.engrams:
            return []

        # 候选筛选
        candidates = self._get_candidates(query_entities, query_time_range)

        if not candidates:
            candidates = set(self.engrams.keys())

        activated = []

        for memory_id in candidates:
            engram = self.engrams.get(memory_id)
            if not engram:
                continue

            # 计算激活分数
            score = self._calculate_activation_score(
                engram, query_vector, query_entities, boost_factor
            )

            # 记录激活尝试
            engram.reactivation_attempts += 1
            engram.last_activation_attempt = datetime.now()

            # 检查是否超过阈值
            current_threshold = self._get_current_threshold(engram)

            if score >= current_threshold:
                engram.reactivation_successes += 1
                activated.append((memory_id, score, engram))
                logger.info(f"Silent engram reactivated: {memory_id}, score={score:.3f}")

        # 按分数排序
        activated.sort(key=lambda x: x[1], reverse=True)

        return activated

    def _calculate_activation_score(
        self,
        engram: SilentEngram,
        query_vector: Optional[np.ndarray],
        query_entities: Optional[List[str]],
        boost_factor: float
    ) -> float:
        """计算激活分数"""
        scores = []
        weights = []

        # 向量相似度
        if query_vector is not None and engram.key_vector is not None:
            vector_sim = self._cosine_similarity(query_vector, engram.key_vector)
            scores.append(vector_sim)
            weights.append(0.6)

        # 实体重叠
        if query_entities and engram.key_entities:
            entity_overlap = len(set(query_entities) & set(engram.key_entities))
            entity_score = entity_overlap / max(len(engram.key_entities), 1)
            scores.append(entity_score)
            weights.append(0.3)

        # 情感和重要性加成
        emotion_boost = engram.original_emotion_intensity * 0.1
        importance_boost = engram.original_importance * 0.1

        if not scores:
            return 0.0

        # 加权平均
        base_score = sum(s * w for s, w in zip(scores, weights)) / sum(weights)

        # 应用增强
        final_score = min(1.0, (base_score + emotion_boost + importance_boost) * boost_factor)

        return final_score

    def _get_current_threshold(self, engram: SilentEngram) -> float:
        """
        获取当前激活阈值

        阈值随时间缓慢降低，使得久远的记忆更容易被激活
        """
        time_since_silence = (datetime.now() - engram.silence_timestamp).days
        decay = self.threshold_decay_rate * time_since_silence
        current_threshold = max(
            self.min_threshold,
            engram.base_threshold - decay
        )
        return current_threshold

    def _get_candidates(
        self,
        query_entities: Optional[List[str]],
        query_time_range: Optional[Tuple[datetime, datetime]]
    ) -> Set[str]:
        """获取候选沉默印迹"""
        candidates = set()

        # 实体匹配
        if query_entities:
            for entity in query_entities:
                candidates.update(self.entity_index.get(entity, set()))

        # 时间范围匹配
        if query_time_range:
            start, end = query_time_range
            for date_str, memory_ids in self.time_index.items():
                try:
                    date = datetime.strptime(date_str, '%Y-%m-%d')
                    if start <= date <= end:
                        candidates.update(memory_ids)
                except ValueError:
                    continue

        return candidates

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """计算余弦相似度"""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def _evict_oldest_engram(self):
        """移除最旧的沉默印迹"""
        if not self.engrams:
            return

        # 找到最旧且激活尝试最少的
        oldest_id = min(
            self.engrams.keys(),
            key=lambda k: (
                self.engrams[k].reactivation_attempts,
                self.engrams[k].silence_timestamp
            )
        )

        self.remove_engram(oldest_id)
        self.total_permanently_lost += 1
        logger.debug(f"Evicted oldest engram: {oldest_id}")

    def remove_engram(self, memory_id: str):
        """移除沉默印迹"""
        if memory_id not in self.engrams:
            return

        engram = self.engrams[memory_id]

        # 清理索引
        for entity in engram.key_entities:
            self.entity_index[entity].discard(memory_id)

        date_key = engram.key_timestamp.strftime('%Y-%m-%d')
        if date_key in self.time_index:
            self.time_index[date_key].discard(memory_id)

        del self.engrams[memory_id]

    def mark_reactivated(self, memory_id: str):
        """标记印迹已被重新激活（恢复为活跃记忆）"""
        if memory_id in self.engrams:
            self.remove_engram(memory_id)
            self.total_reactivated += 1
            logger.info(f"Engram fully reactivated and removed: {memory_id}")

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_engrams': len(self.engrams),
            'total_silenced': self.total_silenced,
            'total_reactivated': self.total_reactivated,
            'total_permanently_lost': self.total_permanently_lost,
            'reactivation_rate': self.total_reactivated / max(1, self.total_silenced),
            'entity_index_size': len(self.entity_index),
            'time_index_size': len(self.time_index)
        }

    def save_to_disk(self):
        """持久化到磁盘"""
        if not self.persistence_path:
            return

        data = {
            'engrams': {k: v.to_dict() for k, v in self.engrams.items()},
            'statistics': {
                'total_silenced': self.total_silenced,
                'total_reactivated': self.total_reactivated,
                'total_permanently_lost': self.total_permanently_lost
            }
        }

        try:
            with open(self.persistence_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Silent engrams saved: {len(self.engrams)} engrams")
        except Exception as e:
            logger.error(f"Failed to save silent engrams: {e}")

    def _load_from_disk(self):
        """从磁盘加载"""
        if not self.persistence_path:
            return

        try:
            with open(self.persistence_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for memory_id, engram_data in data.get('engrams', {}).items():
                engram = SilentEngram.from_dict(engram_data)
                self.engrams[memory_id] = engram

                # 重建索引
                for entity in engram.key_entities:
                    self.entity_index[entity].add(memory_id)

                date_key = engram.key_timestamp.strftime('%Y-%m-%d')
                if date_key not in self.time_index:
                    self.time_index[date_key] = set()
                self.time_index[date_key].add(memory_id)

            stats = data.get('statistics', {})
            self.total_silenced = stats.get('total_silenced', 0)
            self.total_reactivated = stats.get('total_reactivated', 0)
            self.total_permanently_lost = stats.get('total_permanently_lost', 0)

            logger.info(f"Silent engrams loaded: {len(self.engrams)} engrams")
        except FileNotFoundError:
            logger.debug("No existing silent engrams file found")
        except Exception as e:
            logger.error(f"Failed to load silent engrams: {e}")
