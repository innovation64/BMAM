"""
反馈循环模块 (Feedback Loop)

让系统"活"起来的核心: 将检索结果转化为学习信号

设计理念:
- 每次检索都是学习机会
- 高置信度检索 → 正样本 → 强化键向量
- 低置信度检索 → 负样本 → 调整键向量
- 检索失败 → 知识缺口 → 标记需要学习

神经科学依据:
- 海马体-前额叶反馈回路
- 多巴胺奖励信号驱动学习
- 错误驱动的突触可塑性
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RetrievalOutcome:
    """检索结果的学习信号"""
    query: str
    query_vector: Optional[np.ndarray]
    query_entities: List[str]

    # 检索结果
    retrieved_ids: List[str]
    relevance_scores: List[float]

    # 质量评估
    confidence: float  # 0-1, 系统对结果的置信度
    has_strong_match: bool  # 是否有高相关性匹配

    # 后续反馈 (可选, 用户反馈或推理结果)
    was_helpful: Optional[bool] = None  # 结果是否有帮助
    correct_ids: Optional[List[str]] = None  # 真正正确的记忆ID

    timestamp: datetime = field(default_factory=datetime.now)


class FeedbackLoop:
    """
    反馈循环控制器

    核心功能:
    1. 收集检索结果
    2. 评估检索质量
    3. 生成学习信号
    4. 驱动ContrastiveKeyOptimizer
    """

    def __init__(
        self,
        key_optimizer=None,
        metamemory_monitor=None,
        confidence_threshold: float = 0.6,
        learning_enabled: bool = True
    ):
        """
        初始化反馈循环

        Args:
            key_optimizer: ContrastiveKeyOptimizer实例
            metamemory_monitor: MetamemoryMonitor实例
            confidence_threshold: 置信度阈值
            learning_enabled: 是否启用学习
        """
        self.key_optimizer = key_optimizer
        self.metamemory_monitor = metamemory_monitor
        self.confidence_threshold = confidence_threshold
        self.learning_enabled = learning_enabled

        # 历史记录
        self.outcome_history: List[RetrievalOutcome] = []
        self.knowledge_gaps: List[Dict[str, Any]] = []

        # 统计
        self.stats = {
            'total_retrievals': 0,
            'high_confidence': 0,
            'low_confidence': 0,
            'learning_signals_generated': 0,
            'knowledge_gaps_detected': 0
        }

        logger.info("FeedbackLoop initialized")

    def evaluate_retrieval(
        self,
        query: str,
        query_vector: Optional[np.ndarray],
        query_entities: List[str],
        memories: List[Dict[str, Any]]
    ) -> RetrievalOutcome:
        """
        评估检索结果质量

        Args:
            query: 查询文本
            query_vector: 查询向量
            query_entities: 查询中的实体
            memories: 检索到的记忆列表

        Returns:
            RetrievalOutcome 学习信号
        """
        self.stats['total_retrievals'] += 1

        # 提取分数
        retrieved_ids = [m.get('id', '') for m in memories]
        relevance_scores = [m.get('relevance', 0.0) for m in memories]

        # 计算置信度
        confidence, has_strong_match = self._calculate_confidence(
            memories, query_entities
        )

        if confidence >= self.confidence_threshold:
            self.stats['high_confidence'] += 1
        else:
            self.stats['low_confidence'] += 1

        outcome = RetrievalOutcome(
            query=query,
            query_vector=query_vector,
            query_entities=query_entities,
            retrieved_ids=retrieved_ids,
            relevance_scores=relevance_scores,
            confidence=confidence,
            has_strong_match=has_strong_match
        )

        # 记录历史
        self.outcome_history.append(outcome)
        if len(self.outcome_history) > 1000:
            self.outcome_history = self.outcome_history[-500:]  # 保留最近500条

        # 检测知识缺口
        if not has_strong_match and query_entities:
            self._detect_knowledge_gap(outcome)

        return outcome

    def _calculate_confidence(
        self,
        memories: List[Dict[str, Any]],
        query_entities: List[str]
    ) -> Tuple[float, bool]:
        """
        计算检索置信度

        置信度基于:
        1. 最高相关性分数
        2. 实体匹配情况
        3. 分数分布 (高分且集中 = 高置信度)

        Returns:
            (confidence, has_strong_match)
        """
        if not memories:
            return 0.0, False

        # 获取相关性分数
        scores = [m.get('relevance', 0.0) for m in memories]
        max_score = max(scores) if scores else 0.0

        # 检查实体匹配
        entity_matched = False
        for m in memories[:3]:  # 检查前3个结果
            mem_entities = m.get('entities', [])
            if mem_entities and query_entities:
                overlap = set(e.lower() for e in mem_entities) & set(e.lower() for e in query_entities)
                if overlap:
                    entity_matched = True
                    break

        # 分数分布 (高方差 = 低置信度)
        score_variance = np.var(scores) if len(scores) > 1 else 0.0
        distribution_factor = 1.0 - min(score_variance, 0.5)  # 方差越小越好

        # 综合置信度
        base_confidence = max_score
        entity_bonus = 0.2 if entity_matched else 0.0

        confidence = min(1.0, base_confidence * distribution_factor + entity_bonus)
        has_strong_match = max_score >= 0.7

        return confidence, has_strong_match

    def _detect_knowledge_gap(self, outcome: RetrievalOutcome):
        """检测知识缺口"""
        gap = {
            'query': outcome.query,
            'entities': outcome.query_entities,
            'best_score': max(outcome.relevance_scores) if outcome.relevance_scores else 0.0,
            'timestamp': datetime.now().isoformat(),
            'status': 'detected'
        }
        self.knowledge_gaps.append(gap)
        self.stats['knowledge_gaps_detected'] += 1

        logger.info(f"Knowledge gap detected: entities={outcome.query_entities}, "
                   f"best_score={gap['best_score']:.2f}")

    def generate_learning_signal(
        self,
        outcome: RetrievalOutcome,
        was_helpful: bool = None,
        correct_ids: List[str] = None
    ) -> Dict[str, Any]:
        """
        生成学习信号并发送给优化器

        Args:
            outcome: 检索结果
            was_helpful: 结果是否有帮助 (可选反馈)
            correct_ids: 真正正确的ID (可选反馈)

        Returns:
            学习信号详情
        """
        if not self.learning_enabled:
            return {'status': 'disabled'}

        signal = {
            'query': outcome.query,
            'timestamp': datetime.now().isoformat(),
            'positive_ids': [],
            'negative_ids': [],
            'missed_ids': []
        }

        # 基于置信度生成信号
        if outcome.has_strong_match:
            # 高置信度: 前几个结果作为正样本
            signal['positive_ids'] = outcome.retrieved_ids[:3]
        elif outcome.confidence < 0.4:
            # 低置信度: 可能是负样本
            signal['negative_ids'] = outcome.retrieved_ids[:2]

        # 如果有显式反馈
        if was_helpful is not None:
            outcome.was_helpful = was_helpful
            if was_helpful and outcome.retrieved_ids:
                signal['positive_ids'] = outcome.retrieved_ids[:3]
            elif not was_helpful:
                signal['negative_ids'] = outcome.retrieved_ids[:3]

        if correct_ids:
            outcome.correct_ids = correct_ids
            signal['positive_ids'] = correct_ids
            # 检索到但不在correct中的是负样本
            signal['negative_ids'] = [
                rid for rid in outcome.retrieved_ids[:5]
                if rid not in correct_ids
            ]

        # 发送给优化器
        if self.key_optimizer and (signal['positive_ids'] or signal['negative_ids']):
            try:
                self.key_optimizer.add_feedback(
                    query_vector=outcome.query_vector,
                    query_entities=outcome.query_entities,
                    positive_ids=signal['positive_ids'],
                    negative_ids=signal['negative_ids'],
                    missed_ids=signal.get('missed_ids', []),
                    feedback_type='automatic'
                )
                self.stats['learning_signals_generated'] += 1
                logger.debug(f"Learning signal sent: +{len(signal['positive_ids'])} "
                           f"-{len(signal['negative_ids'])}")
            except Exception as e:
                logger.warning(f"Failed to send learning signal: {e}")

        return signal

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            'confidence_rate': (
                self.stats['high_confidence'] / self.stats['total_retrievals']
                if self.stats['total_retrievals'] > 0 else 0.0
            ),
            'knowledge_gaps_count': len(self.knowledge_gaps),
            'history_size': len(self.outcome_history)
        }

    def get_recent_gaps(self, k: int = 10) -> List[Dict[str, Any]]:
        """获取最近的知识缺口"""
        return self.knowledge_gaps[-k:]


class LiveLearningSystem:
    """
    活的学习系统 - 整合所有学习组件

    这是让系统"有灵魂"的核心:
    - 每次交互都学习
    - 持续优化检索
    - 主动发现不足
    """

    def __init__(
        self,
        hippocampus=None,
        temporal_lobe=None,
        key_optimizer=None,
        metamemory_monitor=None
    ):
        """
        初始化活的学习系统

        Args:
            hippocampus: 海马体 (提供embedding)
            temporal_lobe: 颞叶 (语义记忆)
            key_optimizer: 键优化器
            metamemory_monitor: 元记忆监控
        """
        self.hippocampus = hippocampus
        self.temporal_lobe = temporal_lobe

        # 创建反馈循环
        self.feedback_loop = FeedbackLoop(
            key_optimizer=key_optimizer,
            metamemory_monitor=metamemory_monitor
        )

        # 注册优化器到海马体/颞叶
        self._register_key_optimizer(key_optimizer)

        logger.info("LiveLearningSystem initialized - system is now ALIVE")

    def _register_key_optimizer(self, key_optimizer):
        """将现有记忆的键注册到优化器"""
        if not key_optimizer:
            return

        # 从海马体注册
        if self.hippocampus and hasattr(self.hippocampus, 'memories'):
            for mem in self.hippocampus.memories:
                if mem.embedding is not None:
                    key_optimizer.register_key(mem.id, np.array(mem.embedding))

        # 从颞叶注册
        if self.temporal_lobe and hasattr(self.temporal_lobe, 'memories'):
            for mem in self.temporal_lobe.memories:
                if mem.embedding is not None:
                    key_optimizer.register_key(mem.id, np.array(mem.embedding))

    async def on_retrieval_complete(
        self,
        query: str,
        query_vector: Optional[np.ndarray],
        query_entities: List[str],
        memories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        检索完成后的回调 - 核心学习入口

        每次检索完成后调用，生成学习信号

        Args:
            query: 查询
            query_vector: 查询向量
            query_entities: 查询实体
            memories: 检索结果

        Returns:
            学习信号摘要
        """
        # 评估检索质量
        outcome = self.feedback_loop.evaluate_retrieval(
            query=query,
            query_vector=query_vector,
            query_entities=query_entities,
            memories=memories
        )

        # 生成学习信号 (自动模式)
        signal = self.feedback_loop.generate_learning_signal(outcome)

        return {
            'confidence': outcome.confidence,
            'has_strong_match': outcome.has_strong_match,
            'learning_signal': signal,
            'stats': self.feedback_loop.get_statistics()
        }

    async def on_user_feedback(
        self,
        query: str,
        was_helpful: bool,
        correct_memory_ids: List[str] = None
    ) -> Dict[str, Any]:
        """
        用户反馈回调 - 强化学习

        当用户给出反馈时调用

        Args:
            query: 原始查询
            was_helpful: 结果是否有帮助
            correct_memory_ids: 正确的记忆ID (如果有)

        Returns:
            学习结果
        """
        # 找到最近的相关检索
        relevant_outcome = None
        for outcome in reversed(self.feedback_loop.outcome_history):
            if outcome.query == query:
                relevant_outcome = outcome
                break

        if not relevant_outcome:
            logger.warning(f"No recent outcome found for query: {query[:50]}")
            return {'status': 'no_outcome_found'}

        # 生成强化学习信号
        signal = self.feedback_loop.generate_learning_signal(
            outcome=relevant_outcome,
            was_helpful=was_helpful,
            correct_ids=correct_memory_ids
        )

        return {
            'status': 'feedback_processed',
            'learning_signal': signal
        }

    def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        stats = self.feedback_loop.get_statistics()

        # 健康指标
        health = {
            'alive': True,
            'learning_active': self.feedback_loop.learning_enabled,
            'confidence_rate': stats.get('confidence_rate', 0.0),
            'knowledge_gaps': stats.get('knowledge_gaps_count', 0),
            'learning_signals': stats.get('learning_signals_generated', 0)
        }

        # 健康评分
        health['score'] = (
            0.4 * health['confidence_rate'] +
            0.3 * (1.0 if health['learning_active'] else 0.0) +
            0.3 * min(1.0, health['learning_signals'] / 100)
        )

        return health
