"""
Pattern Separator - 模式分离器

基于论文 "Key-value memory in the brain" (Benna & Fusi, 2024)

核心概念：
- 海马体齿状回(DG)的核心功能是"模式分离"
- 将相似的输入映射到不同的表征
- 目的：避免相似记忆之间的干扰和混淆

神经科学依据：
- 齿状回(DG)的稀疏编码
- 高度不同的活动模式用于相似输入
- 空间导航中，重叠路线的表征会变得更加不同（相互排斥）

使用场景：
- 存储相似事件时（周一的会议 vs 周三的会议）
- 需要区分近似经历时
- 防止记忆混淆和干扰
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class DiscriminativeFeatures:
    """
    辨别性特征 - 用于区分相似记忆的关键特征

    当两个记忆相似时，标记它们之间的差异点
    """
    memory_id: str
    unique_entities: List[str] = field(default_factory=list)      # 独特实体
    unique_temporal: Optional[str] = None                          # 独特时间特征
    unique_keywords: List[str] = field(default_factory=list)       # 独特关键词
    contrast_memory_ids: List[str] = field(default_factory=list)   # 对比记忆ID
    separation_score: float = 0.0                                  # 分离程度 (0-1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'memory_id': self.memory_id,
            'unique_entities': self.unique_entities,
            'unique_temporal': self.unique_temporal,
            'unique_keywords': self.unique_keywords,
            'contrast_memory_ids': self.contrast_memory_ids,
            'separation_score': self.separation_score
        }


class PatternSeparator:
    """
    模式分离器 - 增大相似记忆键的可辨别性

    职责：
    1. 检测相似记忆
    2. 提取辨别性特征
    3. 增强键的可辨别性
    4. 在检索时利用辨别性特征提高准确性

    神经科学类比：
    - 模拟海马体齿状回(DG)的功能
    - 稀疏编码：少数神经元高度激活
    - 模式分离：相似输入→不同表征
    """

    def __init__(
        self,
        similarity_threshold: float = 0.7,
        min_separation_score: float = 0.3,
        max_similar_memories: int = 10
    ):
        """
        初始化模式分离器

        Args:
            similarity_threshold: 相似度阈值，超过此值视为相似
            min_separation_score: 最小分离分数，低于此值需要增强分离
            max_similar_memories: 每个记忆最多关联的相似记忆数
        """
        self.similarity_threshold = similarity_threshold
        self.min_separation_score = min_separation_score
        self.max_similar_memories = max_similar_memories

        # 存储辨别性特征
        self.discriminative_features: Dict[str, DiscriminativeFeatures] = {}

        # 相似度缓存
        self.similarity_cache: Dict[Tuple[str, str], float] = {}

        # 实体到记忆的映射（用于快速查找相似记忆）
        self.entity_memory_index: Dict[str, Set[str]] = defaultdict(set)

        logger.info(f"PatternSeparator initialized: threshold={similarity_threshold}")

    def process_new_memory(
        self,
        memory_id: str,
        content: str,
        entities: List[str],
        timestamp: datetime,
        embedding: Optional[np.ndarray] = None,
        existing_memories: Optional[List[Dict[str, Any]]] = None
    ) -> DiscriminativeFeatures:
        """
        处理新记忆，进行模式分离

        Args:
            memory_id: 新记忆ID
            content: 记忆内容
            entities: 实体列表
            timestamp: 时间戳
            embedding: 记忆向量
            existing_memories: 现有记忆列表（用于比较）

        Returns:
            辨别性特征
        """
        # 更新实体索引
        for entity in entities:
            self.entity_memory_index[entity].add(memory_id)

        # 找到相似记忆
        similar_memories = self._find_similar_memories(
            memory_id, entities, embedding, existing_memories
        )

        # 提取辨别性特征
        features = self._extract_discriminative_features(
            memory_id=memory_id,
            content=content,
            entities=entities,
            timestamp=timestamp,
            similar_memories=similar_memories
        )

        # 存储特征
        self.discriminative_features[memory_id] = features

        # 更新相似记忆的辨别性特征
        self._update_contrast_features(memory_id, entities, similar_memories)

        logger.debug(
            f"Pattern separation for {memory_id}: "
            f"found {len(similar_memories)} similar, "
            f"unique_entities={features.unique_entities}, "
            f"separation_score={features.separation_score:.2f}"
        )

        return features

    def _find_similar_memories(
        self,
        memory_id: str,
        entities: List[str],
        embedding: Optional[np.ndarray],
        existing_memories: Optional[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """查找相似记忆"""
        similar = []

        # 基于实体重叠查找候选
        candidate_ids = set()
        for entity in entities:
            candidate_ids.update(self.entity_memory_index.get(entity, set()))
        candidate_ids.discard(memory_id)

        if not existing_memories:
            return []

        # 创建记忆字典
        memory_dict = {m.get('id', m.get('memory_id', '')): m for m in existing_memories}

        for candidate_id in candidate_ids:
            if candidate_id not in memory_dict:
                continue

            candidate = memory_dict[candidate_id]
            similarity = self._calculate_similarity(
                entities, candidate.get('entities', []),
                embedding, candidate.get('embedding')
            )

            if similarity >= self.similarity_threshold:
                similar.append({
                    **candidate,
                    'similarity_score': similarity
                })

        # 按相似度排序，取前N个
        similar.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
        return similar[:self.max_similar_memories]

    def _calculate_similarity(
        self,
        entities1: List[str],
        entities2: List[str],
        embedding1: Optional[np.ndarray] = None,
        embedding2: Optional[np.ndarray] = None
    ) -> float:
        """计算两个记忆的相似度"""
        scores = []
        weights = []

        # 实体Jaccard相似度
        if entities1 and entities2:
            set1, set2 = set(entities1), set(entities2)
            intersection = len(set1 & set2)
            union = len(set1 | set2)
            if union > 0:
                entity_sim = intersection / union
                scores.append(entity_sim)
                weights.append(0.6)

        # 向量余弦相似度
        if embedding1 is not None and embedding2 is not None:
            if isinstance(embedding1, list):
                embedding1 = np.array(embedding1)
            if isinstance(embedding2, list):
                embedding2 = np.array(embedding2)

            norm1, norm2 = np.linalg.norm(embedding1), np.linalg.norm(embedding2)
            if norm1 > 0 and norm2 > 0:
                vector_sim = float(np.dot(embedding1, embedding2) / (norm1 * norm2))
                scores.append(vector_sim)
                weights.append(0.4)

        if not scores:
            return 0.0

        return sum(s * w for s, w in zip(scores, weights)) / sum(weights)

    def _extract_discriminative_features(
        self,
        memory_id: str,
        content: str,
        entities: List[str],
        timestamp: datetime,
        similar_memories: List[Dict[str, Any]]
    ) -> DiscriminativeFeatures:
        """提取辨别性特征"""
        features = DiscriminativeFeatures(memory_id=memory_id)

        if not similar_memories:
            # 没有相似记忆，所有特征都是独特的
            features.unique_entities = entities.copy()
            features.separation_score = 1.0
            return features

        # 收集所有相似记忆的实体
        all_similar_entities = set()
        for mem in similar_memories:
            all_similar_entities.update(mem.get('entities', []))

        # 找出独特实体
        current_entities = set(entities)
        features.unique_entities = list(current_entities - all_similar_entities)

        # 找出独特时间特征
        features.unique_temporal = self._extract_temporal_discriminator(
            timestamp, similar_memories
        )

        # 找出独特关键词
        features.unique_keywords = self._extract_unique_keywords(
            content, similar_memories
        )

        # 记录对比记忆
        features.contrast_memory_ids = [
            m.get('id', m.get('memory_id', ''))
            for m in similar_memories
        ]

        # 计算分离分数
        features.separation_score = self._calculate_separation_score(features)

        return features

    def _extract_temporal_discriminator(
        self,
        timestamp: datetime,
        similar_memories: List[Dict[str, Any]]
    ) -> Optional[str]:
        """提取时间辨别特征"""
        # 提取日期和时间特征
        day_of_week = timestamp.strftime('%A')  # Monday, Tuesday, etc.
        time_of_day = self._get_time_of_day(timestamp)
        date_str = timestamp.strftime('%Y-%m-%d')

        # 检查相似记忆的时间
        similar_days = set()
        similar_times = set()
        similar_dates = set()

        for mem in similar_memories:
            mem_ts = mem.get('timestamp')
            if isinstance(mem_ts, str):
                try:
                    mem_ts = datetime.fromisoformat(mem_ts.replace('Z', '+00:00'))
                except:
                    continue
            if isinstance(mem_ts, datetime):
                similar_days.add(mem_ts.strftime('%A'))
                similar_times.add(self._get_time_of_day(mem_ts))
                similar_dates.add(mem_ts.strftime('%Y-%m-%d'))

        # 返回最具辨别性的时间特征
        if date_str not in similar_dates:
            return f"date:{date_str}"
        if day_of_week not in similar_days:
            return f"day:{day_of_week}"
        if time_of_day not in similar_times:
            return f"time:{time_of_day}"

        return None

    def _get_time_of_day(self, timestamp: datetime) -> str:
        """获取一天中的时间段"""
        hour = timestamp.hour
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"

    def _extract_unique_keywords(
        self,
        content: str,
        similar_memories: List[Dict[str, Any]]
    ) -> List[str]:
        """提取独特关键词"""
        # 简单的关键词提取（可以用更复杂的NLP方法）
        import re

        # 当前内容的词
        current_words = set(re.findall(r'\b\w{3,}\b', content.lower()))

        # 相似记忆的词
        similar_words = set()
        for mem in similar_memories:
            mem_content = mem.get('content', '')
            similar_words.update(re.findall(r'\b\w{3,}\b', mem_content.lower()))

        # 独特词
        unique = current_words - similar_words

        # 过滤停用词
        stopwords = {'the', 'and', 'for', 'that', 'with', 'this', 'was', 'are', 'been'}
        unique = [w for w in unique if w not in stopwords]

        return unique[:5]  # 最多5个

    def _calculate_separation_score(self, features: DiscriminativeFeatures) -> float:
        """计算分离分数"""
        score = 0.0

        # 独特实体加分
        if features.unique_entities:
            score += min(0.4, len(features.unique_entities) * 0.1)

        # 独特时间特征加分
        if features.unique_temporal:
            score += 0.3

        # 独特关键词加分
        if features.unique_keywords:
            score += min(0.3, len(features.unique_keywords) * 0.06)

        return min(1.0, score)

    def _update_contrast_features(
        self,
        new_memory_id: str,
        new_entities: List[str],
        similar_memories: List[Dict[str, Any]]
    ):
        """更新相似记忆的对比特征"""
        new_entities_set = set(new_entities)

        for mem in similar_memories:
            mem_id = mem.get('id', mem.get('memory_id', ''))
            if mem_id in self.discriminative_features:
                features = self.discriminative_features[mem_id]

                # 添加新记忆为对比对象
                if new_memory_id not in features.contrast_memory_ids:
                    features.contrast_memory_ids.append(new_memory_id)

                # 更新独特实体（排除新记忆的实体）
                mem_entities = set(mem.get('entities', []))
                features.unique_entities = list(mem_entities - new_entities_set)

                # 重新计算分离分数
                features.separation_score = self._calculate_separation_score(features)

    def get_discriminative_features(self, memory_id: str) -> Optional[DiscriminativeFeatures]:
        """获取记忆的辨别性特征"""
        return self.discriminative_features.get(memory_id)

    def boost_retrieval_score(
        self,
        memory_id: str,
        query_entities: List[str],
        query_keywords: List[str],
        base_score: float
    ) -> float:
        """
        使用辨别性特征增强检索分数

        当查询包含记忆的独特特征时，提高其排名

        Args:
            memory_id: 记忆ID
            query_entities: 查询中的实体
            query_keywords: 查询中的关键词
            base_score: 基础检索分数

        Returns:
            增强后的分数
        """
        features = self.discriminative_features.get(memory_id)
        if not features:
            return base_score

        boost = 0.0

        # 独特实体匹配加分
        if query_entities and features.unique_entities:
            unique_match = len(set(query_entities) & set(features.unique_entities))
            if unique_match > 0:
                boost += 0.15 * unique_match

        # 独特关键词匹配加分
        if query_keywords and features.unique_keywords:
            keyword_match = len(set(query_keywords) & set(features.unique_keywords))
            if keyword_match > 0:
                boost += 0.1 * keyword_match

        # 分离分数加成
        boost *= (1 + features.separation_score * 0.5)

        return min(1.0, base_score + boost)

    def get_separation_statistics(self) -> Dict[str, Any]:
        """获取模式分离统计信息"""
        if not self.discriminative_features:
            return {
                'total_memories': 0,
                'avg_separation_score': 0.0,
                'well_separated': 0,
                'poorly_separated': 0
            }

        scores = [f.separation_score for f in self.discriminative_features.values()]

        return {
            'total_memories': len(self.discriminative_features),
            'avg_separation_score': sum(scores) / len(scores),
            'well_separated': sum(1 for s in scores if s >= self.min_separation_score),
            'poorly_separated': sum(1 for s in scores if s < self.min_separation_score),
            'avg_unique_entities': sum(
                len(f.unique_entities) for f in self.discriminative_features.values()
            ) / len(self.discriminative_features),
            'memories_with_temporal_discriminator': sum(
                1 for f in self.discriminative_features.values() if f.unique_temporal
            )
        }

    def remove_memory(self, memory_id: str):
        """移除记忆的模式分离信息"""
        if memory_id in self.discriminative_features:
            features = self.discriminative_features[memory_id]

            # 从对比记忆中移除引用
            for contrast_id in features.contrast_memory_ids:
                if contrast_id in self.discriminative_features:
                    contrast_features = self.discriminative_features[contrast_id]
                    if memory_id in contrast_features.contrast_memory_ids:
                        contrast_features.contrast_memory_ids.remove(memory_id)

            del self.discriminative_features[memory_id]

        # 从实体索引中移除
        for entity_set in self.entity_memory_index.values():
            entity_set.discard(memory_id)

    def clear_cache(self):
        """清除缓存"""
        self.similarity_cache.clear()
