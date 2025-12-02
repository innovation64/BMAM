"""
对比学习键优化器 (Contrastive Key Optimizer)

基于论文: "Key-value memory in the brain" (Benna & Fusi, 2024)

核心思想:
- 键向量应该具有最大区分度(discriminability)
- 通过检索反馈(正/负样本)优化键向量
- 成功检索 → 强化当前键
- 检索失败/混淆 → 调整键以增加区分度

神经科学依据:
- 海马体DG区的稀疏编码实现模式分离
- 反馈驱动的突触可塑性(Hebbian + anti-Hebbian)
- 相似记忆需要更独特的检索键

实现方式:
- 简化的对比学习: 正样本拉近,负样本推远
- 在线学习: 每次检索后即时更新
- 软更新: 小步长渐进调整,避免灾难性遗忘
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import numpy as np
import json
import os

logger = logging.getLogger(__name__)


@dataclass
class RetrievalFeedback:
    """检索反馈记录"""
    query_id: str
    query_vector: np.ndarray
    query_entities: List[str]

    # 正样本: 用户确认相关的记忆
    positive_ids: List[str] = field(default_factory=list)
    # 负样本: 检索到但不相关的记忆
    negative_ids: List[str] = field(default_factory=list)
    # 遗漏样本: 应该检索到但没有的记忆
    missed_ids: List[str] = field(default_factory=list)

    timestamp: datetime = field(default_factory=datetime.now)
    feedback_type: str = "explicit"  # explicit, implicit, automatic


@dataclass
class KeyOptimizationState:
    """键优化状态"""
    memory_id: str
    original_vector: np.ndarray
    current_vector: np.ndarray
    adjustment_count: int = 0
    last_adjustment: Optional[datetime] = None

    # 累积梯度(用于momentum)
    momentum: Optional[np.ndarray] = None

    # 统计信息
    positive_count: int = 0
    negative_count: int = 0
    missed_count: int = 0


class ContrastiveKeyOptimizer:
    """
    对比学习键优化器

    功能:
    1. 收集检索反馈(正/负样本)
    2. 计算对比损失
    3. 更新键向量
    4. 维护优化状态

    优化策略:
    - 正样本: 将键向量拉向查询向量
    - 负样本: 将键向量推离查询向量
    - 遗漏样本: 将键向量拉向查询向量(强化)
    """

    def __init__(
        self,
        learning_rate: float = 0.01,
        momentum_beta: float = 0.9,
        margin: float = 0.2,
        max_adjustment_per_step: float = 0.1,
        min_feedback_for_update: int = 1,
        persistence_path: Optional[str] = None
    ):
        """
        初始化优化器

        Args:
            learning_rate: 学习率
            momentum_beta: 动量系数
            margin: 对比学习margin
            max_adjustment_per_step: 每步最大调整幅度
            min_feedback_for_update: 触发更新的最小反馈数
            persistence_path: 持久化路径
        """
        self.learning_rate = learning_rate
        self.momentum_beta = momentum_beta
        self.margin = margin
        self.max_adjustment_per_step = max_adjustment_per_step
        self.min_feedback_for_update = min_feedback_for_update
        self.persistence_path = persistence_path

        # 键优化状态
        self.key_states: Dict[str, KeyOptimizationState] = {}

        # 反馈缓冲区
        self.feedback_buffer: List[RetrievalFeedback] = []

        # 统计信息
        self.total_updates = 0
        self.total_feedback = 0

        # 加载持久化状态
        if persistence_path and os.path.exists(persistence_path):
            self._load_state()

    def register_key(
        self,
        memory_id: str,
        vector: np.ndarray
    ):
        """
        注册新的键向量

        Args:
            memory_id: 记忆ID
            vector: 键向量
        """
        if memory_id not in self.key_states:
            self.key_states[memory_id] = KeyOptimizationState(
                memory_id=memory_id,
                original_vector=vector.copy(),
                current_vector=vector.copy()
            )

    def get_optimized_key(self, memory_id: str) -> Optional[np.ndarray]:
        """
        获取优化后的键向量

        Args:
            memory_id: 记忆ID

        Returns:
            优化后的向量,如果不存在返回None
        """
        if memory_id in self.key_states:
            return self.key_states[memory_id].current_vector
        return None

    def add_feedback(
        self,
        query_vector: np.ndarray,
        query_entities: List[str],
        positive_ids: List[str],
        negative_ids: Optional[List[str]] = None,
        missed_ids: Optional[List[str]] = None,
        feedback_type: str = "explicit"
    ):
        """
        添加检索反馈

        Args:
            query_vector: 查询向量
            query_entities: 查询实体
            positive_ids: 正样本ID列表
            negative_ids: 负样本ID列表
            missed_ids: 遗漏样本ID列表
            feedback_type: 反馈类型
        """
        import uuid

        feedback = RetrievalFeedback(
            query_id=str(uuid.uuid4()),
            query_vector=query_vector,
            query_entities=query_entities,
            positive_ids=positive_ids,
            negative_ids=negative_ids or [],
            missed_ids=missed_ids or [],
            feedback_type=feedback_type
        )

        self.feedback_buffer.append(feedback)
        self.total_feedback += 1

        # 更新统计
        for mem_id in positive_ids:
            if mem_id in self.key_states:
                self.key_states[mem_id].positive_count += 1

        for mem_id in (negative_ids or []):
            if mem_id in self.key_states:
                self.key_states[mem_id].negative_count += 1

        for mem_id in (missed_ids or []):
            if mem_id in self.key_states:
                self.key_states[mem_id].missed_count += 1

        # 检查是否触发更新
        if len(self.feedback_buffer) >= self.min_feedback_for_update:
            self._process_feedback_batch()

    def add_implicit_feedback(
        self,
        query_vector: np.ndarray,
        retrieved_ids: List[str],
        clicked_ids: List[str],
        time_spent: Optional[Dict[str, float]] = None
    ):
        """
        添加隐式反馈(基于用户行为)

        Args:
            query_vector: 查询向量
            retrieved_ids: 检索到的ID列表
            clicked_ids: 用户点击/选择的ID列表
            time_spent: 用户在每个结果上花费的时间
        """
        # 点击的是正样本
        positive_ids = clicked_ids

        # 没点击的是负样本(但只有在返回较多结果时)
        negative_ids = []
        if len(retrieved_ids) > 3:
            negative_ids = [mid for mid in retrieved_ids if mid not in clicked_ids]

        # 时间分析(可选)
        if time_spent:
            # 长时间查看的可能是正样本
            for mem_id, time_sec in time_spent.items():
                if time_sec > 5.0 and mem_id not in positive_ids:
                    positive_ids.append(mem_id)
                elif time_sec < 1.0 and mem_id in positive_ids:
                    # 快速跳过的可能不是真正的正样本
                    pass

        self.add_feedback(
            query_vector=query_vector,
            query_entities=[],
            positive_ids=positive_ids,
            negative_ids=negative_ids,
            feedback_type="implicit"
        )

    def _process_feedback_batch(self):
        """处理反馈批次,更新键向量"""
        if not self.feedback_buffer:
            return

        # 收集所有需要更新的键
        updates: Dict[str, List[Tuple[np.ndarray, float]]] = defaultdict(list)

        for feedback in self.feedback_buffer:
            query_vec = feedback.query_vector

            # 处理正样本: 拉近
            for mem_id in feedback.positive_ids:
                if mem_id in self.key_states:
                    # 正梯度: 向查询方向移动
                    updates[mem_id].append((query_vec, 1.0))

            # 处理负样本: 推远
            for mem_id in feedback.negative_ids:
                if mem_id in self.key_states:
                    # 负梯度: 远离查询方向
                    updates[mem_id].append((query_vec, -1.0))

            # 处理遗漏样本: 强拉近
            for mem_id in feedback.missed_ids:
                if mem_id in self.key_states:
                    # 强正梯度: 这个记忆应该被检索到
                    updates[mem_id].append((query_vec, 1.5))

        # 应用更新
        for mem_id, gradients in updates.items():
            self._update_key(mem_id, gradients)

        # 清空缓冲区
        self.feedback_buffer = []
        self.total_updates += 1

        # 持久化
        if self.persistence_path:
            self._save_state()

    def _update_key(
        self,
        memory_id: str,
        gradients: List[Tuple[np.ndarray, float]]
    ):
        """
        更新单个键向量

        使用带动量的梯度下降:
        - 正权重: 拉向查询向量
        - 负权重: 推离查询向量

        Args:
            memory_id: 记忆ID
            gradients: (查询向量, 权重)列表
        """
        state = self.key_states[memory_id]
        current_vec = state.current_vector

        # 计算累积梯度
        total_gradient = np.zeros_like(current_vec)

        for query_vec, weight in gradients:
            # 方向: 从当前键指向查询
            direction = query_vec - current_vec

            # 归一化
            norm = np.linalg.norm(direction)
            if norm > 1e-8:
                direction = direction / norm

            # 加权
            total_gradient += direction * weight

        # 归一化梯度
        grad_norm = np.linalg.norm(total_gradient)
        if grad_norm > 1e-8:
            total_gradient = total_gradient / grad_norm

        # 应用动量
        if state.momentum is None:
            state.momentum = np.zeros_like(current_vec)

        state.momentum = (
            self.momentum_beta * state.momentum +
            (1 - self.momentum_beta) * total_gradient
        )

        # 计算更新步长
        step = self.learning_rate * state.momentum

        # 限制最大调整幅度
        step_norm = np.linalg.norm(step)
        if step_norm > self.max_adjustment_per_step:
            step = step * (self.max_adjustment_per_step / step_norm)

        # 更新向量
        new_vec = current_vec + step

        # 重新归一化(保持单位向量)
        new_norm = np.linalg.norm(new_vec)
        if new_norm > 1e-8:
            new_vec = new_vec / new_norm

        state.current_vector = new_vec
        state.adjustment_count += 1
        state.last_adjustment = datetime.now()

        logger.debug(
            f"Key updated: {memory_id}, "
            f"adjustment={step_norm:.4f}, total_adjustments={state.adjustment_count}"
        )

    def compute_key_drift(self, memory_id: str) -> float:
        """
        计算键向量的漂移程度

        Args:
            memory_id: 记忆ID

        Returns:
            余弦距离(0表示无漂移,1表示完全相反)
        """
        if memory_id not in self.key_states:
            return 0.0

        state = self.key_states[memory_id]

        # 计算余弦相似度
        dot_product = np.dot(state.original_vector, state.current_vector)
        orig_norm = np.linalg.norm(state.original_vector)
        curr_norm = np.linalg.norm(state.current_vector)

        if orig_norm < 1e-8 or curr_norm < 1e-8:
            return 0.0

        similarity = dot_product / (orig_norm * curr_norm)

        # 转换为距离
        return 1.0 - similarity

    def get_optimization_statistics(self) -> Dict[str, Any]:
        """获取优化统计信息"""
        if not self.key_states:
            return {
                "total_keys": 0,
                "total_updates": self.total_updates,
                "total_feedback": self.total_feedback
            }

        drifts = [self.compute_key_drift(mid) for mid in self.key_states]
        adjustment_counts = [s.adjustment_count for s in self.key_states.values()]

        return {
            "total_keys": len(self.key_states),
            "total_updates": self.total_updates,
            "total_feedback": self.total_feedback,
            "average_drift": float(np.mean(drifts)),
            "max_drift": float(np.max(drifts)),
            "average_adjustments": float(np.mean(adjustment_counts)),
            "keys_with_adjustments": sum(1 for c in adjustment_counts if c > 0)
        }

    def reset_key(self, memory_id: str):
        """重置键向量到原始状态"""
        if memory_id in self.key_states:
            state = self.key_states[memory_id]
            state.current_vector = state.original_vector.copy()
            state.momentum = None
            state.adjustment_count = 0

    def remove_key(self, memory_id: str):
        """移除键"""
        if memory_id in self.key_states:
            del self.key_states[memory_id]

    def _save_state(self):
        """持久化状态"""
        if not self.persistence_path:
            return

        try:
            state_data = {
                "total_updates": self.total_updates,
                "total_feedback": self.total_feedback,
                "key_states": {}
            }

            for mem_id, state in self.key_states.items():
                state_data["key_states"][mem_id] = {
                    "original_vector": state.original_vector.tolist(),
                    "current_vector": state.current_vector.tolist(),
                    "adjustment_count": state.adjustment_count,
                    "last_adjustment": state.last_adjustment.isoformat() if state.last_adjustment else None,
                    "momentum": state.momentum.tolist() if state.momentum is not None else None,
                    "positive_count": state.positive_count,
                    "negative_count": state.negative_count,
                    "missed_count": state.missed_count
                }

            with open(self.persistence_path, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Failed to save ContrastiveKeyOptimizer state: {e}")

    def _load_state(self):
        """加载持久化状态"""
        if not self.persistence_path or not os.path.exists(self.persistence_path):
            return

        try:
            with open(self.persistence_path, 'r', encoding='utf-8') as f:
                state_data = json.load(f)

            self.total_updates = state_data.get("total_updates", 0)
            self.total_feedback = state_data.get("total_feedback", 0)

            for mem_id, state_dict in state_data.get("key_states", {}).items():
                self.key_states[mem_id] = KeyOptimizationState(
                    memory_id=mem_id,
                    original_vector=np.array(state_dict["original_vector"]),
                    current_vector=np.array(state_dict["current_vector"]),
                    adjustment_count=state_dict.get("adjustment_count", 0),
                    last_adjustment=datetime.fromisoformat(state_dict["last_adjustment"])
                        if state_dict.get("last_adjustment") else None,
                    momentum=np.array(state_dict["momentum"])
                        if state_dict.get("momentum") else None,
                    positive_count=state_dict.get("positive_count", 0),
                    negative_count=state_dict.get("negative_count", 0),
                    missed_count=state_dict.get("missed_count", 0)
                )

            logger.info(f"Loaded ContrastiveKeyOptimizer state: {len(self.key_states)} keys")

        except Exception as e:
            logger.error(f"Failed to load ContrastiveKeyOptimizer state: {e}")


class AdaptiveContrastiveOptimizer(ContrastiveKeyOptimizer):
    """
    自适应对比学习优化器

    扩展功能:
    1. 自适应学习率(根据反馈质量调整)
    2. 困难样本挖掘(关注经常混淆的记忆对)
    3. 群组感知(相似记忆组的协调优化)
    """

    def __init__(
        self,
        base_learning_rate: float = 0.01,
        lr_adaptation_rate: float = 0.1,
        hard_negative_boost: float = 2.0,
        **kwargs
    ):
        super().__init__(learning_rate=base_learning_rate, **kwargs)

        self.base_learning_rate = base_learning_rate
        self.lr_adaptation_rate = lr_adaptation_rate
        self.hard_negative_boost = hard_negative_boost

        # 困难对追踪
        self.confusion_pairs: Dict[Tuple[str, str], int] = defaultdict(int)

        # 学习率调整因子
        self.lr_factors: Dict[str, float] = defaultdict(lambda: 1.0)

    def add_confusion_pair(self, mem_id_1: str, mem_id_2: str):
        """
        记录混淆对(两个经常被混淆的记忆)

        Args:
            mem_id_1: 记忆1 ID
            mem_id_2: 记忆2 ID
        """
        pair = tuple(sorted([mem_id_1, mem_id_2]))
        self.confusion_pairs[pair] += 1

        # 增加这两个记忆的学习率
        self.lr_factors[mem_id_1] = min(2.0, self.lr_factors[mem_id_1] + 0.1)
        self.lr_factors[mem_id_2] = min(2.0, self.lr_factors[mem_id_2] + 0.1)

    def get_hard_negatives(self, memory_id: str, top_k: int = 5) -> List[str]:
        """
        获取某个记忆的困难负样本

        Args:
            memory_id: 记忆ID
            top_k: 返回数量

        Returns:
            困难负样本ID列表
        """
        confusions = []

        for (id1, id2), count in self.confusion_pairs.items():
            if id1 == memory_id:
                confusions.append((id2, count))
            elif id2 == memory_id:
                confusions.append((id1, count))

        confusions.sort(key=lambda x: x[1], reverse=True)
        return [c[0] for c in confusions[:top_k]]

    def _update_key(
        self,
        memory_id: str,
        gradients: List[Tuple[np.ndarray, float]]
    ):
        """带自适应学习率的键更新"""
        # 调整学习率
        original_lr = self.learning_rate
        self.learning_rate = self.base_learning_rate * self.lr_factors[memory_id]

        # 调用父类更新
        super()._update_key(memory_id, gradients)

        # 恢复学习率
        self.learning_rate = original_lr

        # 衰减学习率因子
        self.lr_factors[memory_id] = max(
            1.0,
            self.lr_factors[memory_id] * (1 - self.lr_adaptation_rate)
        )

    def push_apart_confusing_pairs(self):
        """
        主动推远混淆对

        定期调用以增加经常混淆的记忆对之间的区分度
        """
        for (id1, id2), count in self.confusion_pairs.items():
            if count < 3:  # 只处理多次混淆的对
                continue

            if id1 not in self.key_states or id2 not in self.key_states:
                continue

            vec1 = self.key_states[id1].current_vector
            vec2 = self.key_states[id2].current_vector

            # 计算当前相似度
            similarity = np.dot(vec1, vec2) / (
                np.linalg.norm(vec1) * np.linalg.norm(vec2) + 1e-8
            )

            if similarity > 0.5:  # 如果还是很相似
                # 推远
                direction = vec1 - vec2
                direction = direction / (np.linalg.norm(direction) + 1e-8)

                step = direction * self.learning_rate * self.hard_negative_boost

                self.key_states[id1].current_vector = vec1 + step
                self.key_states[id2].current_vector = vec2 - step

                # 归一化
                self.key_states[id1].current_vector /= (
                    np.linalg.norm(self.key_states[id1].current_vector) + 1e-8
                )
                self.key_states[id2].current_vector /= (
                    np.linalg.norm(self.key_states[id2].current_vector) + 1e-8
                )

                logger.info(
                    f"Pushed apart confusing pair: {id1} <-> {id2}, "
                    f"confusion_count={count}"
                )
