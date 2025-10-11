"""
Context Budget Manager
上下文预算管理器 - 优化Token使用

基于Anthropic原则：
- Context is a finite resource (上下文是有限资源)
- Diminishing marginal returns (边际效用递减)
- Allocate tokens wisely by priority (按优先级明智分配)
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Priority(Enum):
    """任务优先级"""
    CRITICAL = "critical"  # 关键任务（如用户直接查询）
    HIGH = "high"         # 高优先级（如记忆检索）
    MEDIUM = "medium"     # 中优先级（如反思）
    LOW = "low"          # 低优先级（如后台整理）


@dataclass
class TokenAllocation:
    """Token分配记录"""
    agent_id: str
    task_type: str
    priority: Priority
    allocated_tokens: int
    actual_used: Optional[int] = None


class ContextBudgetManager:
    """
    上下文预算管理器

    功能：
    1. 为不同优先级任务分配token预算
    2. 跟踪实际使用情况
    3. 动态调整分配策略
    4. 防止上下文窗口溢出
    """

    def __init__(self, max_total_tokens: int = 8000):
        """
        初始化预算管理器

        Args:
            max_total_tokens: 最大上下文窗口大小（保守值，为模型留余量）
        """
        self.max_total_tokens = max_total_tokens
        self.current_usage = 0
        self.allocations: List[TokenAllocation] = []

        # 优先级对应的基础分配比例
        self.priority_weights = {
            Priority.CRITICAL: 0.40,  # 关键任务可用40%
            Priority.HIGH: 0.30,      # 高优先级30%
            Priority.MEDIUM: 0.20,    # 中优先级20%
            Priority.LOW: 0.10        # 低优先级10%
        }

        # 每种任务类型的典型token需求
        self.task_budgets = {
            'user_query': 2000,       # 用户查询响应
            'memory_retrieval': 1000, # 记忆检索
            'consolidation': 800,     # 记忆巩固
            'reflection': 600,        # 反思
            'summary': 400,           # 摘要
            'quick_check': 200        # 快速检查
        }

        self.stats = {
            'total_allocated': 0,
            'total_used': 0,
            'allocations_count': 0,
            'budget_overruns': 0
        }

    def allocate(
        self,
        agent_id: str,
        task_type: str = 'general',
        priority: Priority = Priority.MEDIUM,
        requested_tokens: Optional[int] = None
    ) -> int:
        """
        为任务分配token预算

        Args:
            agent_id: Agent标识
            task_type: 任务类型
            priority: 优先级
            requested_tokens: 请求的token数（可选，优先使用）

        Returns:
            分配的token数
        """
        # 计算可分配的token
        available_tokens = self.max_total_tokens - self.current_usage

        if available_tokens <= 0:
            logger.warning(f"Token budget exhausted! Current usage: {self.current_usage}/{self.max_total_tokens}")
            # 紧急情况下，为CRITICAL任务分配最小量
            if priority == Priority.CRITICAL:
                allocated = 500
            else:
                allocated = 0
        else:
            # 根据优先级和任务类型计算分配
            if requested_tokens:
                base_allocation = requested_tokens
            else:
                base_allocation = self.task_budgets.get(task_type, 1000)

            # 应用优先级权重
            priority_factor = self.priority_weights[priority]
            allocated = min(
                int(base_allocation * priority_factor),
                available_tokens,
                base_allocation  # 不超过基础需求
            )

        # 记录分配
        allocation = TokenAllocation(
            agent_id=agent_id,
            task_type=task_type,
            priority=priority,
            allocated_tokens=allocated
        )
        self.allocations.append(allocation)
        self.current_usage += allocated
        self.stats['total_allocated'] += allocated
        self.stats['allocations_count'] += 1

        logger.debug(
            f"Token allocated: {agent_id}/{task_type} = {allocated} tokens "
            f"(priority={priority.value}, usage={self.current_usage}/{self.max_total_tokens})"
        )

        return allocated

    def report_usage(self, agent_id: str, actual_tokens: int):
        """
        报告实际token使用量

        Args:
            agent_id: Agent标识
            actual_tokens: 实际使用的token数
        """
        # 找到最近的分配记录
        for allocation in reversed(self.allocations):
            if allocation.agent_id == agent_id and allocation.actual_used is None:
                allocation.actual_used = actual_tokens

                # 调整当前使用量
                diff = actual_tokens - allocation.allocated_tokens
                self.current_usage += diff
                self.stats['total_used'] += actual_tokens

                if actual_tokens > allocation.allocated_tokens:
                    self.stats['budget_overruns'] += 1
                    logger.warning(
                        f"Budget overrun: {agent_id} used {actual_tokens} "
                        f"(allocated {allocation.allocated_tokens})"
                    )

                break

    def release(self, agent_id: str):
        """
        释放Agent的token预算（任务完成后调用）

        Args:
            agent_id: Agent标识
        """
        released = 0
        for allocation in reversed(self.allocations):
            if allocation.agent_id == agent_id and allocation.actual_used is not None:
                # 已知实际使用量，释放差额
                released = allocation.allocated_tokens - allocation.actual_used
                if released > 0:
                    self.current_usage -= released
                break

        if released > 0:
            logger.debug(f"Released {released} tokens from {agent_id}")

    def get_available_budget(self) -> int:
        """获取剩余可用预算"""
        return max(0, self.max_total_tokens - self.current_usage)

    def should_compact(self) -> bool:
        """判断是否应该触发上下文压缩"""
        usage_ratio = self.current_usage / self.max_total_tokens
        # 使用超过75%时建议压缩
        return usage_ratio > 0.75

    def reset(self):
        """重置预算（压缩后调用）"""
        old_usage = self.current_usage
        self.current_usage = 0
        self.allocations = []
        logger.info(f"Budget reset: freed {old_usage} tokens")

    def get_stats(self) -> Dict[str, Any]:
        """获取预算统计"""
        usage_ratio = self.current_usage / self.max_total_tokens if self.max_total_tokens > 0 else 0
        efficiency = self.stats['total_used'] / max(self.stats['total_allocated'], 1)

        return {
            'max_budget': self.max_total_tokens,
            'current_usage': self.current_usage,
            'available': self.get_available_budget(),
            'usage_ratio': f"{usage_ratio:.1%}",
            'total_allocated': self.stats['total_allocated'],
            'total_used': self.stats['total_used'],
            'allocation_efficiency': f"{efficiency:.1%}",
            'budget_overruns': self.stats['budget_overruns'],
            'should_compact': self.should_compact()
        }

    def get_recommendations(self) -> List[str]:
        """获取优化建议"""
        recommendations = []

        if self.should_compact():
            recommendations.append("⚠️ 上下文使用率超过75%，建议触发compaction")

        efficiency = self.stats['total_used'] / max(self.stats['total_allocated'], 1)
        if efficiency < 0.6:
            recommendations.append("💡 分配效率较低，考虑降低预分配量")

        if self.stats['budget_overruns'] > 3:
            recommendations.append("📊 预算超支频繁，考虑提高基础分配或降低并发任务")

        return recommendations


# 全局单例
_global_budget_manager = ContextBudgetManager()


def get_budget_manager() -> ContextBudgetManager:
    """获取全局预算管理器"""
    return _global_budget_manager
