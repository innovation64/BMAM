"""
Preference-Aware Retrieval System
偏好感知检索系统

针对PersonaMem (28%)和PrefEval (33.3%)优化:
1. 偏好检测 - 识别偏好相关的查询和记忆
2. 偏好增强 - 检索时提升偏好记忆权重
3. 对比学习 - 基于反馈优化检索键
4. 元记忆 - TOT检测触发扩展搜索
5. 沉默印迹 - 激活遗忘的偏好记忆

设计原则:
- 提升PersonaMem和PrefEval性能
- 不影响LongMemEval时间推理 (86.7%)
- 不影响LoCoMo多会话记忆 (75.4%)

Author: BMAM Team
Date: 2025-12-21
"""

import logging
import re
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime

from .contrastive_key_optimizer import ContrastiveKeyOptimizer, AdaptiveContrastiveOptimizer
from .metamemory import MetamemoryMonitor, MetamemoryController
from .silent_engram import SilentEngramStore, SilentEngram
from ..utils.paths import BMAMPaths

logger = logging.getLogger(__name__)


# Preference-related keywords (English + Chinese)
PREFERENCE_KEYWORDS = {
    # English preference markers
    'prefer', 'preference', 'like', 'love', 'hate', 'dislike',
    'favorite', 'favourite', 'rather', 'instead', 'always', 'never',
    'usually', 'typically', 'better', 'best', 'worse', 'worst',
    'enjoy', 'avoid', 'allergic', 'vegetarian', 'vegan', 'diet',
    'style', 'taste', 'choice', 'habit', 'routine',
    # Chinese preference markers
    '喜欢', '偏好', '偏爱', '讨厌', '不喜欢', '最爱', '总是', '从不',
    '通常', '习惯', '风格', '品味', '选择', '常常', '经常',
    # Question patterns
    'what do i', 'how do i', 'do i like', 'do i prefer',
    'what is my', 'what are my', "what's my",
}

PREFERENCE_QUESTION_PATTERNS = [
    r'what.*(prefer|like|love|favorite)',
    r'do\s+i\s+(prefer|like|enjoy|hate)',
    r'how\s+do\s+i\s+(usually|typically)',
    r"what's?\s+my\s+(favorite|preference|habit)",
    r'what\s+are\s+my\s+(preferences|favorites)',
    r'remember.*?(prefer|like|favorite)',
    r'我.*(喜欢|偏好|偏爱|习惯)',
]


@dataclass
class PreferenceDetectionResult:
    """偏好检测结果"""
    is_preference_query: bool
    preference_score: float  # 0-1
    detected_keywords: List[str]
    preference_type: str  # 'food', 'style', 'activity', 'general'


@dataclass
class PreferenceRetrievalResult:
    """偏好增强检索结果"""
    memories: List[Dict[str, Any]]
    preference_memories: List[Dict[str, Any]]  # 专门的偏好记忆
    reactivated_memories: List[Dict[str, Any]]  # 从沉默印迹激活的
    tot_triggered: bool
    fok_score: float
    boost_applied: bool
    debug_info: Dict[str, Any]


class PreferenceDetector:
    """偏好检测器 - 识别偏好相关的查询和记忆"""

    def __init__(self):
        self.preference_patterns = [re.compile(p, re.IGNORECASE) for p in PREFERENCE_QUESTION_PATTERNS]

    def detect_preference_query(self, query: str) -> PreferenceDetectionResult:
        """
        检测查询是否是偏好相关的

        Args:
            query: 用户查询

        Returns:
            偏好检测结果
        """
        query_lower = query.lower()
        detected_keywords = []

        # 1. 关键词匹配
        for keyword in PREFERENCE_KEYWORDS:
            if keyword in query_lower:
                detected_keywords.append(keyword)

        # 2. 模式匹配
        pattern_matches = 0
        for pattern in self.preference_patterns:
            if pattern.search(query_lower):
                pattern_matches += 1

        # 3. 计算偏好分数
        keyword_score = min(len(detected_keywords) / 3, 1.0)
        pattern_score = min(pattern_matches / 2, 1.0)
        preference_score = keyword_score * 0.4 + pattern_score * 0.6

        # 4. 确定偏好类型
        preference_type = self._classify_preference_type(query_lower, detected_keywords)

        is_preference_query = preference_score > 0.2 or pattern_matches > 0

        return PreferenceDetectionResult(
            is_preference_query=is_preference_query,
            preference_score=preference_score,
            detected_keywords=detected_keywords,
            preference_type=preference_type
        )

    def detect_preference_memory(self, content: str, entities: List[str] = None) -> float:
        """
        检测记忆内容是否包含偏好信息

        Args:
            content: 记忆内容
            entities: 实体列表

        Returns:
            偏好分数 (0-1)
        """
        content_lower = content.lower()

        # 关键词计数
        keyword_count = 0
        for keyword in PREFERENCE_KEYWORDS:
            if keyword in content_lower:
                keyword_count += 1

        # 模式匹配
        pattern_count = 0
        for pattern in self.preference_patterns:
            if pattern.search(content_lower):
                pattern_count += 1

        # 实体中是否有偏好相关词
        entity_boost = 0
        if entities:
            for entity in entities:
                if any(kw in entity.lower() for kw in ['preference', 'favorite', 'like', '喜欢', '偏好']):
                    entity_boost += 0.1

        score = min(keyword_count / 4 + pattern_count / 2 + entity_boost, 1.0)
        return score

    def _classify_preference_type(self, query: str, keywords: List[str]) -> str:
        """分类偏好类型"""
        food_words = {'food', 'eat', 'drink', 'restaurant', 'cuisine', 'vegetarian', 'vegan', 'allergic', '食物', '吃', '餐'}
        style_words = {'style', 'fashion', 'color', 'design', '风格', '颜色', '设计'}
        activity_words = {'activity', 'sport', 'hobby', 'music', 'movie', '活动', '运动', '爱好'}

        query_words = set(query.split())

        if food_words & query_words or any(w in query for w in food_words):
            return 'food'
        elif style_words & query_words or any(w in query for w in style_words):
            return 'style'
        elif activity_words & query_words or any(w in query for w in activity_words):
            return 'activity'
        else:
            return 'general'


class PreferenceAwareRetrieval:
    """
    偏好感知检索系统

    集成:
    1. PreferenceDetector - 偏好检测
    2. ContrastiveKeyOptimizer - 检索键优化
    3. MetamemoryMonitor - 元记忆监控
    4. SilentEngramStore - 沉默印迹存储
    """

    def __init__(
        self,
        memory_system=None,
        preference_boost_weight: float = 0.3,
        enable_contrastive_learning: bool = True,
        enable_metamemory: bool = True,
        enable_silent_engram: bool = True
    ):
        """
        初始化偏好感知检索

        Args:
            memory_system: 记忆系统引用
            preference_boost_weight: 偏好增强权重
            enable_contrastive_learning: 是否启用对比学习
            enable_metamemory: 是否启用元记忆
            enable_silent_engram: 是否启用沉默印迹
        """
        self.memory_system = memory_system
        self.preference_boost_weight = preference_boost_weight

        # 偏好检测器
        self.preference_detector = PreferenceDetector()

        # 对比学习键优化器
        self.contrastive_optimizer = None
        if enable_contrastive_learning:
            self.contrastive_optimizer = AdaptiveContrastiveOptimizer(
                base_learning_rate=0.01,
                persistence_path=str(BMAMPaths.DATA_DIR / 'contrastive_keys.json')
            )
            logger.info("✅ ContrastiveKeyOptimizer enabled")

        # 元记忆监控器
        self.metamemory_monitor = None
        if enable_metamemory:
            self.metamemory_monitor = MetamemoryMonitor(
                tot_threshold=0.4,
                persistence_path=str(BMAMPaths.DATA_DIR / 'metamemory_state.json')
            )
            logger.info("✅ MetamemoryMonitor enabled")

        # 沉默印迹存储
        self.silent_engram_store = None
        if enable_silent_engram:
            self.silent_engram_store = SilentEngramStore(
                max_engrams=5000,
                default_threshold=0.85,
                persistence_path=str(BMAMPaths.DATA_DIR / 'silent_engrams.json')
            )
            logger.info("✅ SilentEngramStore enabled")

        # 统计
        self.stats = {
            'total_queries': 0,
            'preference_queries': 0,
            'boost_applied': 0,
            'tot_triggered': 0,
            'engrams_reactivated': 0,
            'feedback_positive': 0,
            'feedback_negative': 0
        }

        logger.info(f"PreferenceAwareRetrieval initialized (boost={preference_boost_weight})")

    async def enhance_retrieval(
        self,
        query: str,
        query_vector: Optional[np.ndarray],
        base_results: List[Dict[str, Any]],
        context: Dict[str, Any] = None
    ) -> PreferenceRetrievalResult:
        """
        增强检索 - 对偏好查询应用增强策略

        Args:
            query: 用户查询
            query_vector: 查询向量
            base_results: 基础检索结果
            context: 上下文信息

        Returns:
            增强后的检索结果
        """
        self.stats['total_queries'] += 1
        context = context or {}

        # 1. 偏好检测
        detection = self.preference_detector.detect_preference_query(query)

        # 🔥 FIX: 只对真正的偏好查询应用增强，避免影响其他类型查询（如时间推理）
        if not detection.is_preference_query or detection.preference_score < 0.3:
            # 非偏好查询，直接返回原始结果
            return PreferenceRetrievalResult(
                memories=list(base_results),
                preference_memories=[],
                reactivated_memories=[],
                tot_triggered=False,
                fok_score=0.5,
                boost_applied=False,
                debug_info={
                    'preference_detection': {
                        'is_preference_query': detection.is_preference_query,
                        'preference_score': detection.preference_score,
                        'skipped': True,
                        'reason': 'non_preference_query'
                    }
                }
            )

        if detection.is_preference_query:
            self.stats['preference_queries'] += 1
            logger.debug(f"Preference query detected: score={detection.preference_score:.2f}, type={detection.preference_type}")

        # 2. 元记忆分析 (FOK/TOT)
        fok_score = 0.5
        tot_triggered = False

        if self.metamemory_monitor and query_vector is not None:
            similarity_scores = [r.get('relevance', r.get('score', 0.5)) for r in base_results[:10]]

            # FOK判断
            fok = self.metamemory_monitor.compute_fok(
                query=query,
                query_vector=query_vector,
                candidate_memories=base_results[:10],
                similarity_scores=similarity_scores
            )
            fok_score = fok.fok_score

            # TOT检测
            tot = self.metamemory_monitor.detect_tot_state(
                query=query,
                query_vector=query_vector,
                partial_matches=base_results[:5],
                activation_levels=similarity_scores[:5]
            )

            if tot and tot.is_resolvable:
                tot_triggered = True
                self.stats['tot_triggered'] += 1
                logger.debug(f"TOT state detected: activation={tot.activation_level:.2f}")

        # 3. 沉默印迹激活 (针对偏好查询)
        reactivated_memories = []

        if self.silent_engram_store and detection.is_preference_query and query_vector is not None:
            # 尝试激活相关的沉默印迹
            boost_factor = 1.0 + detection.preference_score * 0.5  # 偏好分数越高,激活因子越大

            reactivated = self.silent_engram_store.try_reactivate(
                query_vector=query_vector,
                query_entities=detection.detected_keywords,
                boost_factor=boost_factor
            )

            for mem_id, score, engram in reactivated[:3]:
                reactivated_memories.append({
                    'memory_id': mem_id,
                    'content': f"[Reactivated] {engram.memory_id}",  # 需要从外部获取完整内容
                    'score': score,
                    'source': 'silent_engram',
                    'reactivation_score': score
                })
                self.stats['engrams_reactivated'] += 1

        # 4. 偏好记忆增强
        preference_memories = []
        boost_applied = False
        enhanced_results = list(base_results)  # 复制

        if detection.is_preference_query:
            # 计算每个结果的偏好分数
            for result in enhanced_results:
                content = result.get('content', '')
                entities = result.get('entities', [])
                pref_score = self.preference_detector.detect_preference_memory(content, entities)

                # 应用偏好增强
                if pref_score > 0.3:
                    original_score = result.get('relevance', result.get('score', 0.5))
                    boost = pref_score * self.preference_boost_weight * detection.preference_score
                    result['relevance'] = min(1.0, original_score + boost)
                    result['preference_boost'] = boost
                    result['is_preference_memory'] = True
                    preference_memories.append(result)
                    boost_applied = True

            # 重新排序
            if boost_applied:
                enhanced_results.sort(key=lambda x: x.get('relevance', x.get('score', 0)), reverse=True)
                self.stats['boost_applied'] += 1

        # 5. 合并激活的沉默印迹
        if reactivated_memories:
            # 将激活的记忆添加到结果中(不重复)
            existing_ids = {r.get('memory_id') for r in enhanced_results}
            for mem in reactivated_memories:
                if mem['memory_id'] not in existing_ids:
                    enhanced_results.append(mem)

        return PreferenceRetrievalResult(
            memories=enhanced_results,
            preference_memories=preference_memories,
            reactivated_memories=reactivated_memories,
            tot_triggered=tot_triggered,
            fok_score=fok_score,
            boost_applied=boost_applied,
            debug_info={
                'preference_detection': {
                    'is_preference_query': detection.is_preference_query,
                    'preference_score': detection.preference_score,
                    'preference_type': detection.preference_type,
                    'detected_keywords': detection.detected_keywords
                },
                'metamemory': {
                    'fok_score': fok_score,
                    'tot_triggered': tot_triggered
                },
                'boost': {
                    'applied': boost_applied,
                    'preference_memories_count': len(preference_memories),
                    'reactivated_count': len(reactivated_memories)
                }
            }
        )

    def provide_feedback(
        self,
        query_vector: np.ndarray,
        retrieved_ids: List[str],
        relevant_ids: List[str],
        irrelevant_ids: List[str] = None
    ):
        """
        提供检索反馈 (用于对比学习)

        Args:
            query_vector: 查询向量
            retrieved_ids: 检索到的记忆ID
            relevant_ids: 相关的记忆ID (正样本)
            irrelevant_ids: 不相关的记忆ID (负样本)
        """
        if not self.contrastive_optimizer:
            return

        irrelevant_ids = irrelevant_ids or []

        # 添加反馈
        self.contrastive_optimizer.add_feedback(
            query_vector=query_vector,
            query_entities=[],
            positive_ids=relevant_ids,
            negative_ids=irrelevant_ids,
            feedback_type='explicit'
        )

        self.stats['feedback_positive'] += len(relevant_ids)
        self.stats['feedback_negative'] += len(irrelevant_ids)

        logger.debug(f"Feedback added: {len(relevant_ids)} positive, {len(irrelevant_ids)} negative")

    def silence_memory(
        self,
        memory_id: str,
        content: str,
        embedding: np.ndarray = None,
        entities: List[str] = None,
        importance: float = 0.5,
        reason: str = 'capacity'
    ):
        """
        将记忆转为沉默印迹

        Args:
            memory_id: 记忆ID
            content: 记忆内容
            embedding: 嵌入向量
            entities: 实体列表
            importance: 重要性
            reason: 沉默原因
        """
        if not self.silent_engram_store:
            return

        # 计算偏好分数,偏好相关的记忆用更低的激活阈值
        pref_score = self.preference_detector.detect_preference_memory(content, entities)

        engram = self.silent_engram_store.silence_memory(
            memory_id=memory_id,
            content=content,
            embedding=embedding,
            entities=entities,
            importance=importance,
            reason=reason
        )

        # 对偏好记忆降低激活阈值(更容易被激活)
        if pref_score > 0.3:
            engram.activation_threshold = max(0.6, engram.activation_threshold - 0.15)
            engram.base_threshold = engram.activation_threshold
            logger.debug(f"Lowered activation threshold for preference memory: {memory_id}")

    def register_memory_key(self, memory_id: str, vector: np.ndarray):
        """注册记忆键(用于对比学习优化)"""
        if self.contrastive_optimizer:
            self.contrastive_optimizer.register_key(memory_id, vector)

    def get_optimized_key(self, memory_id: str) -> Optional[np.ndarray]:
        """获取优化后的检索键"""
        if self.contrastive_optimizer:
            return self.contrastive_optimizer.get_optimized_key(memory_id)
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = dict(self.stats)

        if self.contrastive_optimizer:
            stats['contrastive'] = self.contrastive_optimizer.get_optimization_statistics()

        if self.metamemory_monitor:
            stats['metamemory'] = self.metamemory_monitor.get_retrieval_statistics()

        if self.silent_engram_store:
            stats['silent_engram'] = self.silent_engram_store.get_statistics()

        return stats

    def save_state(self):
        """保存所有状态"""
        if self.contrastive_optimizer:
            self.contrastive_optimizer._save_state()

        if self.metamemory_monitor:
            self.metamemory_monitor._save_state()

        if self.silent_engram_store:
            self.silent_engram_store.save_to_disk()

        logger.info("PreferenceAwareRetrieval state saved")


# 全局单例
_preference_aware_retrieval: Optional[PreferenceAwareRetrieval] = None


def get_preference_aware_retrieval(
    memory_system=None,
    **kwargs
) -> PreferenceAwareRetrieval:
    """获取偏好感知检索单例"""
    global _preference_aware_retrieval

    if _preference_aware_retrieval is None:
        _preference_aware_retrieval = PreferenceAwareRetrieval(
            memory_system=memory_system,
            **kwargs
        )

    return _preference_aware_retrieval


def reset_preference_aware_retrieval():
    """重置偏好感知检索(用于测试)"""
    global _preference_aware_retrieval
    _preference_aware_retrieval = None
