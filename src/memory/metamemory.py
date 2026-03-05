"""
元记忆模块 (Metamemory)

基于论文: "Key-value memory in the brain" (Benna & Fusi, 2024)

核心概念:
- 元记忆 = 对记忆过程的监控和控制
- 不是记忆内容本身，而是"关于记忆的记忆"

关键功能:
1. TOT状态 (Tip-of-Tongue): 知道有记忆但无法提取
2. FOK判断 (Feeling-of-Knowing): 预测能否回忆成功
3. JOL评估 (Judgment-of-Learning): 评估学习效果
4. 自信度校准: 调整检索结果的置信度

神经科学依据:
- 前额叶皮层监控记忆过程
- 海马体提供部分激活信号
- 元认知错误驱动学习策略调整

应用场景:
- 检索失败时提供"我知道但想不起来"的状态
- 帮助系统决定是否需要更多线索
- 辅助用户理解系统的记忆状态
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import numpy as np
import json
import os

logger = logging.getLogger(__name__)


class MemoryState(Enum):
    """记忆状态枚举"""
    ACCESSIBLE = "accessible"           # 可直接访问
    TIP_OF_TONGUE = "tip_of_tongue"    # 舌尖状态(知道但想不起来)
    FAMILIAR = "familiar"               # 熟悉但不确定
    FORGOTTEN = "forgotten"             # 遗忘(检索失败)
    NEVER_ENCODED = "never_encoded"    # 从未编码


@dataclass
class TOTState:
    """
    舌尖状态 (Tip-of-Tongue)

    当系统知道有相关记忆但无法完全检索时触发
    """
    query: str
    partial_matches: List[Dict[str, Any]]  # 部分匹配的记忆
    activation_level: float  # 激活水平(0-1)
    known_features: List[str]  # 已知的特征(如首字母、音节数等)
    suggested_cues: List[str]  # 建议的提示词
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def is_resolvable(self) -> bool:
        """是否可能通过更多线索解决"""
        return self.activation_level > 0.3 and len(self.partial_matches) > 0


@dataclass
class FOKJudgment:
    """
    知道感判断 (Feeling-of-Knowing)

    预测给定查询能否成功回忆
    """
    query: str
    fok_score: float  # 0-1, 高分表示有信心能回忆
    basis: List[str]  # 判断依据
    related_concepts: List[str]  # 相关概念(即使想不起具体内容)
    timestamp: datetime = field(default_factory=datetime.now)

    def get_confidence_label(self) -> str:
        """获取置信度标签"""
        if self.fok_score >= 0.8:
            return "high_confidence"
        elif self.fok_score >= 0.5:
            return "medium_confidence"
        elif self.fok_score >= 0.3:
            return "low_confidence"
        else:
            return "no_confidence"


@dataclass
class JOLEvaluation:
    """
    学习判断 (Judgment-of-Learning)

    评估新记忆的编码质量和未来可检索性
    """
    memory_id: str
    content_summary: str
    jol_score: float  # 0-1, 预测未来能否回忆
    encoding_strength: float  # 编码强度
    distinctiveness: float  # 独特性
    elaboration_level: float  # 精细加工程度
    timestamp: datetime = field(default_factory=datetime.now)

    def needs_reinforcement(self) -> bool:
        """是否需要强化学习"""
        return self.jol_score < 0.5 or self.encoding_strength < 0.4


@dataclass
class MetamemoryEvent:
    """元记忆事件记录"""
    event_type: str  # "tot", "fok", "jol", "retrieval_failure", "false_positive"
    query: Optional[str] = None
    memory_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class MetamemoryMonitor:
    """
    元记忆监控器

    功能:
    1. 监控记忆检索过程
    2. 检测TOT状态
    3. 计算FOK判断
    4. 评估JOL
    5. 校准置信度
    """

    def __init__(
        self,
        tot_threshold: float = 0.4,
        fok_calibration_window: int = 100,
        persistence_path: Optional[str] = None
    ):
        """
        初始化元记忆监控器

        Args:
            tot_threshold: TOT检测阈值
            fok_calibration_window: FOK校准窗口大小
            persistence_path: 持久化路径
        """
        self.tot_threshold = tot_threshold
        self.fok_calibration_window = fok_calibration_window
        self.persistence_path = persistence_path

        # 事件历史
        self.event_history: List[MetamemoryEvent] = []

        # FOK校准数据
        self.fok_predictions: List[Tuple[float, bool]] = []  # (预测分数, 实际结果)

        # 记忆状态缓存
        self.memory_states: Dict[str, MemoryState] = {}

        # JOL历史
        self.jol_history: Dict[str, List[JOLEvaluation]] = defaultdict(list)

        # 统计
        self.total_retrievals = 0
        self.successful_retrievals = 0
        self.tot_occurrences = 0
        self.false_positives = 0

        # 加载状态
        if persistence_path and os.path.exists(persistence_path):
            self._load_state()

    def detect_tot_state(
        self,
        query: str,
        query_vector: Optional[np.ndarray],
        partial_matches: List[Dict[str, Any]],
        activation_levels: List[float]
    ) -> Optional[TOTState]:
        """
        检测舌尖状态

        当有部分激活但无完全匹配时触发

        Args:
            query: 查询文本
            query_vector: 查询向量
            partial_matches: 部分匹配的记忆
            activation_levels: 激活水平列表

        Returns:
            TOTState if detected, None otherwise
        """
        if not partial_matches or not activation_levels:
            return None

        max_activation = max(activation_levels)
        avg_activation = np.mean(activation_levels)

        # TOT条件: 有中等激活但没有高激活
        is_tot = (
            avg_activation > self.tot_threshold * 0.5 and
            max_activation < 0.7 and
            max_activation > self.tot_threshold
        )

        if not is_tot:
            return None

        # 提取已知特征
        known_features = []
        for match in partial_matches[:3]:
            content = match.get('content', '')
            # 提取关键词
            if content:
                words = content.split()[:3]
                known_features.extend(words)

            # 提取实体
            entities = match.get('entities', [])
            known_features.extend(entities[:2])

        # 生成建议的提示词
        suggested_cues = self._generate_cue_suggestions(query, partial_matches)

        tot_state = TOTState(
            query=query,
            partial_matches=partial_matches,
            activation_level=max_activation,
            known_features=list(set(known_features))[:5],
            suggested_cues=suggested_cues
        )

        # 记录事件
        self.event_history.append(MetamemoryEvent(
            event_type="tot",
            query=query,
            details={
                "activation_level": max_activation,
                "num_partial_matches": len(partial_matches)
            }
        ))
        self.tot_occurrences += 1

        logger.info(f"TOT state detected: activation={max_activation:.2f}, query='{query[:50]}'")

        return tot_state

    def _generate_cue_suggestions(
        self,
        query: str,
        partial_matches: List[Dict[str, Any]]
    ) -> List[str]:
        """生成提示词建议"""
        suggestions = []

        # 从部分匹配中提取高频实体
        entity_counts = defaultdict(int)
        for match in partial_matches:
            for entity in match.get('entities', []):
                entity_counts[entity] += 1

        top_entities = sorted(
            entity_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        for entity, _ in top_entities:
            suggestions.append(f"关于 {entity} 的记忆?")

        # 时间相关提示
        timestamps = [m.get('timestamp') for m in partial_matches if m.get('timestamp')]
        if timestamps:
            suggestions.append("是什么时候的事情?")

        # 情境相关提示
        suggestions.append("当时的情境是什么?")

        return suggestions[:5]

    def compute_fok(
        self,
        query: str,
        query_vector: Optional[np.ndarray],
        candidate_memories: List[Dict[str, Any]],
        similarity_scores: List[float]
    ) -> FOKJudgment:
        """
        计算知道感判断

        预测能否成功回忆

        Args:
            query: 查询文本
            query_vector: 查询向量
            candidate_memories: 候选记忆
            similarity_scores: 相似度分数

        Returns:
            FOK判断
        """
        # 基础分数: 基于相似度分布
        if not similarity_scores:
            base_score = 0.0
        else:
            max_score = max(similarity_scores)
            score_variance = np.var(similarity_scores) if len(similarity_scores) > 1 else 0

            # 高最大分 + 低方差 = 高FOK
            base_score = max_score * 0.7 + (1 - min(score_variance, 1)) * 0.3

        # 调整因子
        adjustment = 0.0

        # 1. 候选数量调整
        if len(candidate_memories) == 1 and similarity_scores[0] > 0.7:
            adjustment += 0.1  # 唯一高相关候选增加信心
        elif len(candidate_memories) > 10:
            adjustment -= 0.1  # 太多候选降低信心

        # 2. 实体匹配调整
        query_words = set(query.lower().split())
        for mem in candidate_memories[:3]:
            entities = set(e.lower() for e in mem.get('entities', []))
            if query_words & entities:
                adjustment += 0.05

        # 3. 历史校准
        calibration = self._get_fok_calibration()
        base_score = base_score * calibration

        final_score = max(0, min(1, base_score + adjustment))

        # 收集相关概念
        related_concepts = []
        for mem in candidate_memories[:5]:
            related_concepts.extend(mem.get('entities', [])[:2])
        related_concepts = list(set(related_concepts))[:5]

        # 判断依据
        basis = []
        if max(similarity_scores) if similarity_scores else 0 > 0.7:
            basis.append("高语义相似度")
        if len(candidate_memories) == 1:
            basis.append("唯一候选")
        if related_concepts:
            basis.append(f"相关概念: {', '.join(related_concepts[:3])}")

        fok = FOKJudgment(
            query=query,
            fok_score=final_score,
            basis=basis,
            related_concepts=related_concepts
        )

        return fok

    def _get_fok_calibration(self) -> float:
        """
        获取FOK校准因子

        基于历史预测准确性调整
        """
        if len(self.fok_predictions) < 10:
            return 1.0  # 数据不足，不调整

        recent = self.fok_predictions[-self.fok_calibration_window:]

        # 计算校准误差
        # 如果预测偏高但实际失败多，降低
        # 如果预测偏低但实际成功多，提高
        high_predictions = [p for p in recent if p[0] > 0.7]
        if high_predictions:
            high_accuracy = sum(1 for _, actual in high_predictions if actual) / len(high_predictions)
            if high_accuracy < 0.7:
                return 0.9  # 过度自信，降低

        low_predictions = [p for p in recent if p[0] < 0.4]
        if low_predictions:
            low_accuracy = sum(1 for _, actual in low_predictions if not actual) / len(low_predictions)
            if low_accuracy < 0.7:
                return 1.1  # 过度悲观，提高

        return 1.0

    def record_fok_outcome(self, fok_score: float, was_successful: bool):
        """
        记录FOK预测结果

        用于校准

        Args:
            fok_score: 预测分数
            was_successful: 实际是否成功
        """
        self.fok_predictions.append((fok_score, was_successful))

        # 保持窗口大小
        if len(self.fok_predictions) > self.fok_calibration_window * 2:
            self.fok_predictions = self.fok_predictions[-self.fok_calibration_window:]

    def evaluate_jol(
        self,
        memory_id: str,
        content: str,
        encoding_context: Dict[str, Any]
    ) -> JOLEvaluation:
        """
        评估学习判断

        预测新记忆未来的可检索性

        Args:
            memory_id: 记忆ID
            content: 记忆内容
            encoding_context: 编码上下文

        Returns:
            JOL评估
        """
        # 编码强度: 基于上下文丰富程度
        encoding_strength = 0.5

        if encoding_context.get('emotion_intensity', 0) > 0.5:
            encoding_strength += 0.2
        if encoding_context.get('entities', []):
            encoding_strength += 0.1
        if encoding_context.get('relations', []):
            encoding_strength += 0.1
        if encoding_context.get('importance', 0) > 0.7:
            encoding_strength += 0.1

        encoding_strength = min(1.0, encoding_strength)

        # 独特性: 基于内容独特程度
        distinctiveness = encoding_context.get('distinctiveness', 0.5)

        # 精细加工程度: 基于内容长度和结构
        content_length = len(content)
        if content_length > 200:
            elaboration_level = 0.7
        elif content_length > 100:
            elaboration_level = 0.5
        else:
            elaboration_level = 0.3

        if encoding_context.get('has_temporal_marker', False):
            elaboration_level += 0.1
        if encoding_context.get('has_causal_link', False):
            elaboration_level += 0.1

        elaboration_level = min(1.0, elaboration_level)

        # 综合JOL分数
        jol_score = (
            encoding_strength * 0.4 +
            distinctiveness * 0.3 +
            elaboration_level * 0.3
        )

        jol = JOLEvaluation(
            memory_id=memory_id,
            content_summary=content[:100],
            jol_score=jol_score,
            encoding_strength=encoding_strength,
            distinctiveness=distinctiveness,
            elaboration_level=elaboration_level
        )

        # 记录历史
        self.jol_history[memory_id].append(jol)

        if jol.needs_reinforcement():
            logger.info(
                f"Memory needs reinforcement: {memory_id}, JOL={jol_score:.2f}"
            )

        return jol

    def record_retrieval_attempt(
        self,
        query: str,
        retrieved_ids: List[str],
        was_successful: bool,
        confidence: float
    ):
        """
        记录检索尝试

        用于更新元记忆统计

        Args:
            query: 查询
            retrieved_ids: 检索到的ID
            was_successful: 是否成功
            confidence: 置信度
        """
        self.total_retrievals += 1

        if was_successful:
            self.successful_retrievals += 1
            # 更新记忆状态
            for mem_id in retrieved_ids:
                self.memory_states[mem_id] = MemoryState.ACCESSIBLE
        else:
            # 记录失败
            self.event_history.append(MetamemoryEvent(
                event_type="retrieval_failure",
                query=query,
                details={
                    "retrieved_ids": retrieved_ids,
                    "confidence": confidence
                }
            ))

    def record_false_positive(
        self,
        query: str,
        false_positive_ids: List[str]
    ):
        """
        记录误报

        检索到但实际不相关的记忆

        Args:
            query: 查询
            false_positive_ids: 误报的记忆ID
        """
        self.false_positives += len(false_positive_ids)

        self.event_history.append(MetamemoryEvent(
            event_type="false_positive",
            query=query,
            details={"false_positive_ids": false_positive_ids}
        ))

    def get_memory_state(self, memory_id: str) -> MemoryState:
        """获取记忆状态"""
        return self.memory_states.get(memory_id, MemoryState.FORGOTTEN)

    def get_retrieval_statistics(self) -> Dict[str, Any]:
        """获取检索统计"""
        success_rate = (
            self.successful_retrievals / self.total_retrievals
            if self.total_retrievals > 0 else 0
        )

        return {
            "total_retrievals": self.total_retrievals,
            "successful_retrievals": self.successful_retrievals,
            "success_rate": success_rate,
            "tot_occurrences": self.tot_occurrences,
            "false_positives": self.false_positives,
            "fok_calibration": self._get_fok_calibration()
        }

    def get_reinforcement_recommendations(
        self,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取需要强化的记忆推荐

        基于JOL评估和检索历史

        Args:
            top_k: 返回数量

        Returns:
            需要强化的记忆列表
        """
        recommendations = []

        for memory_id, jol_list in self.jol_history.items():
            if not jol_list:
                continue

            latest_jol = jol_list[-1]

            if latest_jol.needs_reinforcement():
                recommendations.append({
                    "memory_id": memory_id,
                    "jol_score": latest_jol.jol_score,
                    "encoding_strength": latest_jol.encoding_strength,
                    "reason": "low_jol_score",
                    "content_summary": latest_jol.content_summary
                })

        # 按JOL分数排序(低分优先)
        recommendations.sort(key=lambda x: x["jol_score"])

        return recommendations[:top_k]

    def suggest_retrieval_strategy(
        self,
        query: str,
        fok: FOKJudgment,
        tot: Optional[TOTState] = None
    ) -> Dict[str, Any]:
        """
        基于元记忆状态建议检索策略

        Args:
            query: 查询
            fok: FOK判断
            tot: TOT状态

        Returns:
            策略建议
        """
        strategy = {
            "should_expand_search": False,
            "use_cues": [],
            "confidence_adjustment": 0,
            "fallback_suggestion": None
        }

        # TOT状态: 建议使用提示词
        if tot and tot.is_resolvable:
            strategy["should_expand_search"] = True
            strategy["use_cues"] = tot.suggested_cues
            strategy["fallback_suggestion"] = "尝试提供更多上下文线索"

        # 低FOK: 降低置信度，扩大搜索
        if fok.fok_score < 0.4:
            strategy["should_expand_search"] = True
            strategy["confidence_adjustment"] = -0.2
            strategy["fallback_suggestion"] = "可能没有相关记忆，考虑使用外部知识"

        # 高FOK但低激活: 可能是沉默印迹
        if fok.fok_score > 0.6 and (not tot or tot.activation_level < 0.5):
            strategy["fallback_suggestion"] = "记忆可能处于沉默状态，尝试使用更强的线索激活"

        return strategy

    def _save_state(self):
        """持久化状态"""
        if not self.persistence_path:
            return

        try:
            state = {
                "total_retrievals": self.total_retrievals,
                "successful_retrievals": self.successful_retrievals,
                "tot_occurrences": self.tot_occurrences,
                "false_positives": self.false_positives,
                "fok_predictions": self.fok_predictions[-self.fok_calibration_window:],
                "memory_states": {
                    k: v.value for k, v in self.memory_states.items()
                }
            }

            with open(self.persistence_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Failed to save metamemory state: {e}")

    def _load_state(self):
        """加载持久化状态"""
        if not self.persistence_path or not os.path.exists(self.persistence_path):
            return

        try:
            with open(self.persistence_path, 'r', encoding='utf-8') as f:
                state = json.load(f)

            self.total_retrievals = state.get("total_retrievals", 0)
            self.successful_retrievals = state.get("successful_retrievals", 0)
            self.tot_occurrences = state.get("tot_occurrences", 0)
            self.false_positives = state.get("false_positives", 0)
            self.fok_predictions = state.get("fok_predictions", [])
            self.memory_states = {
                k: MemoryState(v) for k, v in state.get("memory_states", {}).items()
            }

            logger.info("Metamemory state loaded")

        except Exception as e:
            logger.error(f"Failed to load metamemory state: {e}")


class MetamemoryController:
    """
    元记忆控制器

    集成元记忆监控到检索流程
    """

    def __init__(
        self,
        monitor: MetamemoryMonitor,
        silent_engram_store: Optional[Any] = None
    ):
        """
        初始化控制器

        Args:
            monitor: 元记忆监控器
            silent_engram_store: 沉默印迹存储(可选)
        """
        self.monitor = monitor
        self.silent_engram_store = silent_engram_store

    async def enhanced_retrieval(
        self,
        query: str,
        query_vector: np.ndarray,
        base_results: List[Dict[str, Any]],
        similarity_scores: List[float]
    ) -> Dict[str, Any]:
        """
        增强检索(集成元记忆)

        Args:
            query: 查询
            query_vector: 查询向量
            base_results: 基础检索结果
            similarity_scores: 相似度分数

        Returns:
            增强后的检索结果
        """
        # 计算FOK
        fok = self.monitor.compute_fok(
            query=query,
            query_vector=query_vector,
            candidate_memories=base_results,
            similarity_scores=similarity_scores
        )

        # 检测TOT
        tot = self.monitor.detect_tot_state(
            query=query,
            query_vector=query_vector,
            partial_matches=base_results,
            activation_levels=similarity_scores
        )

        # 获取策略建议
        strategy = self.monitor.suggest_retrieval_strategy(query, fok, tot)

        # 构建增强结果
        enhanced_result = {
            "results": base_results,
            "fok": {
                "score": fok.fok_score,
                "confidence_label": fok.get_confidence_label(),
                "related_concepts": fok.related_concepts,
                "basis": fok.basis
            },
            "tot": None,
            "strategy": strategy,
            "confidence_adjusted": False
        }

        # 添加TOT信息
        if tot:
            enhanced_result["tot"] = {
                "detected": True,
                "activation_level": tot.activation_level,
                "known_features": tot.known_features,
                "suggested_cues": tot.suggested_cues,
                "is_resolvable": tot.is_resolvable
            }

        # 尝试激活沉默印迹
        if (
            strategy.get("fallback_suggestion") and
            "沉默状态" in strategy["fallback_suggestion"] and
            self.silent_engram_store
        ):
            reactivated = self.silent_engram_store.try_reactivate(
                query_vector=query_vector,
                boost_factor=1.5
            )

            if reactivated:
                enhanced_result["reactivated_silent_engrams"] = [
                    {"memory_id": mid, "score": score}
                    for mid, score, _ in reactivated[:3]
                ]

        return enhanced_result
