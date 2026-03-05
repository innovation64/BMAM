"""
Capacity Management System for Brain Regions
容量管理系统 - 确保记忆系统的稳定性和高效性

核心设计原则:
1. 每个脑区有realistic容量上限
2. 超过容量 → 触发遗忘或外部存储
3. 推理上下文始终保持合理大小
4. 性能不随记忆增长而下降
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class BrainRegionCapacity:
    """Brain region capacity configuration with validation."""
    region_name: str
    max_items: int  # Maximum number of memories
    max_context_items: int  # Maximum items for reasoning context
    overflow_strategy: str  # 'forget' or 'archive' or 'external'
    current_count: int = 0

    def __post_init__(self):
        """Validate configuration after initialization."""
        # Precondition: region_name must be non-empty string
        if not isinstance(self.region_name, str):
            raise TypeError(f"Region name must be string, got {type(self.region_name).__name__}")
        if not self.region_name or not self.region_name.strip():
            raise ValueError("Region name cannot be empty")

        # Precondition: max_items must be positive integer
        if not isinstance(self.max_items, int):
            raise TypeError(f"Max items must be integer, got {type(self.max_items).__name__}")
        if self.max_items <= 0:
            raise ValueError(f"Max items must be positive, got {self.max_items}")
        if self.max_items > 1000000:  # Sanity check
            raise ValueError(f"Max items too large ({self.max_items}), maximum 1000000")

        # Precondition: max_context_items must be positive and <= max_items
        if not isinstance(self.max_context_items, int):
            raise TypeError(f"Max context items must be integer, got {type(self.max_context_items).__name__}")
        if self.max_context_items <= 0:
            raise ValueError(f"Max context items must be positive, got {self.max_context_items}")
        if self.max_context_items > self.max_items:
            raise ValueError(
                f"Max context items ({self.max_context_items}) cannot exceed max items ({self.max_items})"
            )

        # Precondition: overflow_strategy must be valid
        valid_strategies = ['forget', 'archive', 'external']
        if not isinstance(self.overflow_strategy, str):
            raise TypeError(f"Overflow strategy must be string, got {type(self.overflow_strategy).__name__}")
        if self.overflow_strategy not in valid_strategies:
            raise ValueError(
                f"Invalid overflow strategy: {self.overflow_strategy}, must be one of {valid_strategies}"
            )

        # Precondition: current_count must be non-negative
        if not isinstance(self.current_count, int):
            raise TypeError(f"Current count must be integer, got {type(self.current_count).__name__}")
        if self.current_count < 0:
            raise ValueError(f"Current count cannot be negative, got {self.current_count}")


class CapacityManager:
    """
    容量管理器 - 管理所有脑区的容量限制

    Brain Region Capacities (基于认知神经科学):
    - WorkingMemory (PrefrontalCortex): 5-9 items (Miller's Law)
    - EpisodicMemory (Hippocampus): 20,000 items (快速遗忘)
    - SemanticMemory (TemporalLobe): 100,000 items (长期保存)
    - EmotionalMemory (Amygdala): 1,000 items (高优先级)
    - ProceduralMemory (BasalGanglia): 500 items (技能/习惯)
    """

    def __init__(self):
        self.capacities: Dict[str, BrainRegionCapacity] = {}
        self._initialize_default_capacities()

    def _initialize_default_capacities(self):
        """初始化默认容量配置"""
        configs = [
            # Working Memory - 最小容量(7±2 items)
            BrainRegionCapacity(
                region_name='prefrontal',
                max_items=10,
                max_context_items=7,  # Miller's Law
                overflow_strategy='forget'
            ),

            # Episodic Memory - 中等容量,快速遗忘
            BrainRegionCapacity(
                region_name='hippocampus',
                max_items=20000,
                max_context_items=50,  # 推理时最多50条情节
                overflow_strategy='forget'
            ),

            # Semantic Memory - 大容量,长期保存
            BrainRegionCapacity(
                region_name='temporal_lobe',
                max_items=100000,
                max_context_items=100,  # 推理时最多100条语义知识
                overflow_strategy='archive'
            ),

            # Emotional Memory - 小容量,高优先级
            BrainRegionCapacity(
                region_name='amygdala',
                max_items=1000,
                max_context_items=20,
                overflow_strategy='forget'
            ),

            # Procedural Memory - 小容量
            BrainRegionCapacity(
                region_name='basal_ganglia',
                max_items=500,
                max_context_items=10,
                overflow_strategy='forget'
            )
        ]

        for config in configs:
            self.capacities[config.region_name] = config


    def check_capacity(self, region_name: str, current_count: int) -> Dict[str, Any]:
        """Check brain region capacity status with validation.

        Args:
            region_name: Name of the brain region
            current_count: Current number of items

        Returns:
            Dictionary with capacity status information

        Raises:
            TypeError: If parameters have wrong types
            ValueError: If parameters are invalid
        """
        # Precondition: validate inputs
        if not isinstance(region_name, str):
            raise TypeError(f"Region name must be string, got {type(region_name).__name__}")
        if not region_name or not region_name.strip():
            raise ValueError("Region name cannot be empty")

        if not isinstance(current_count, int):
            raise TypeError(f"Current count must be integer, got {type(current_count).__name__}")
        if current_count < 0:
            raise ValueError(f"Current count cannot be negative, got {current_count}")
        if current_count > 10000000:  # Sanity check
            raise ValueError(f"Current count unreasonably large ({current_count}), maximum 10000000")

        # Handle unknown region
        if region_name not in self.capacities:
            logger.warning(f"Unknown brain region: {region_name}")
            return {
                'at_capacity': False,
                'usage_percent': 0.0,
                'should_trigger_overflow': False,
                'overflow_strategy': 'none'
            }

        capacity = self.capacities[region_name]
        capacity.current_count = current_count

        # Calculate metrics
        usage_percent = (current_count / capacity.max_items) * 100
        at_capacity = current_count >= capacity.max_items

        # Trigger overflow at 90% capacity
        should_trigger_overflow = usage_percent >= 90

        result = {
            'at_capacity': at_capacity,
            'usage_percent': usage_percent,
            'should_trigger_overflow': should_trigger_overflow,
            'overflow_strategy': capacity.overflow_strategy,
            'max_items': capacity.max_items,
            'current_count': current_count
        }

        # Postcondition: usage_percent must be valid
        assert 0.0 <= result['usage_percent'] <= 200.0, \
            f"Invalid usage percent: {result['usage_percent']}"

        return result

    def get_max_context_items(self, region_name: str) -> int:
        """Get maximum reasoning context items for brain region.

        Args:
            region_name: Name of the brain region

        Returns:
            Maximum context items (default 50 if region unknown)

        Raises:
            TypeError: If region_name is not string
            ValueError: If region_name is invalid
        """
        # Precondition: validate region_name
        if not isinstance(region_name, str):
            raise TypeError(f"Region name must be string, got {type(region_name).__name__}")
        if not region_name or not region_name.strip():
            raise ValueError("Region name cannot be empty")

        if region_name not in self.capacities:
            return 50  # Default fallback

        max_items = self.capacities[region_name].max_context_items

        # Postcondition: max_items must be positive
        assert isinstance(max_items, int) and max_items > 0, \
            f"Invalid max_context_items: {max_items}"

        return max_items

    def should_limit_context(self, region_name: str, requested_items: int) -> bool:
        """Determine if context size should be limited.

        Args:
            region_name: Name of the brain region
            requested_items: Number of items requested

        Returns:
            True if requested items exceeds limit

        Raises:
            TypeError: If parameters have wrong types
            ValueError: If parameters are invalid
        """
        # Precondition: validate requested_items
        if not isinstance(requested_items, int):
            raise TypeError(f"Requested items must be integer, got {type(requested_items).__name__}")
        if requested_items < 0:
            raise ValueError(f"Requested items cannot be negative, got {requested_items}")

        max_context = self.get_max_context_items(region_name)

        # Postcondition: both values must be non-negative
        assert requested_items >= 0 and max_context >= 0, \
            f"Invalid values: requested={requested_items}, max={max_context}"

        return requested_items > max_context

    def get_overflow_action(self, region_name: str) -> str:
        """获取溢出处理策略"""
        if region_name not in self.capacities:
            return 'forget'

        return self.capacities[region_name].overflow_strategy

    def get_capacity_report(self) -> Dict[str, Any]:
        """生成容量报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'regions': {}
        }

        for name, capacity in self.capacities.items():
            usage_percent = (capacity.current_count / capacity.max_items) * 100
            status = '🟢' if usage_percent < 70 else '🟡' if usage_percent < 90 else '🔴'

            report['regions'][name] = {
                'status': status,
                'current': capacity.current_count,
                'max': capacity.max_items,
                'usage_percent': round(usage_percent, 1),
                'overflow_strategy': capacity.overflow_strategy
            }

        return report


# ============================================================
# Singleton Pattern with Thread Safety
# ============================================================
import threading

class CapacityManagerSingleton:
    """
    Thread-safe singleton for CapacityManager

    Pattern: Singleton with lazy initialization and thread safety
    Why: Global resource manager tracking capacity across all brain regions
    """
    _instance: Optional['CapacityManager'] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> 'CapacityManager':
        """获取全局容量管理器实例 (thread-safe)"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = CapacityManager()
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset singleton instance (mainly for testing)"""
        with cls._lock:
            cls._instance = None


def get_capacity_manager() -> CapacityManager:
    """获取全局容量管理器实例 (backward compatible)"""
    return CapacityManagerSingleton.get_instance()

