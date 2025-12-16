"""
HRM Coordinator Wrapper - 层级推理模型协调器包装器

包装 BrainInspiredCoordinator，提供 HRM (Hierarchical Reasoning Model) 功能:
1. 多时间尺度协调 (Multi-timescale coordination)
2. 自适应计算 (Adaptive Computation Time - ACT)
3. 迭代精化 (Iterative refinement)

这是一个兼容层，HRM功能已经集成到 BrainInspiredCoordinator 中。
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HRMConfig:
    """HRM 配置"""
    enable_multi_timescale: bool = True
    enable_act: bool = True
    max_iterations: int = 5
    convergence_threshold: float = 0.01
    confidence_threshold: float = 0.7


class HRMCoordinatorWrapper:
    """
    HRM 协调器包装器

    这是一个简单的包装器，将 HRM 功能委托给底层的 BrainInspiredCoordinator。
    HRM 功能 (Thalamus 多时间尺度协调, AnteriorCingulate ACT) 已经集成到
    BrainInspiredCoordinator 的 process_user_input 流程中。
    """

    def __init__(self, base_coordinator, config: HRMConfig = None):
        """
        初始化 HRM 包装器

        Args:
            base_coordinator: BrainInspiredCoordinator 实例
            config: HRM 配置 (可选)
        """
        self.coordinator = base_coordinator
        self.config = config or HRMConfig()
        self._initialized = False

    async def initialize(self):
        """初始化包装器"""
        if not self._initialized:
            # 确保底层协调器已初始化
            if hasattr(self.coordinator, 'initialize'):
                await self.coordinator.initialize()
            self._initialized = True
            logger.info("✅ HRMCoordinatorWrapper initialized")

    async def process_user_input(self, user_input: str, context: Dict[str, Any] = None) -> Any:
        """
        处理用户输入

        直接委托给底层协调器，HRM 功能已经集成在 process_user_input 中。
        """
        if context is None:
            context = {}

        # 添加 HRM 配置到上下文
        context['hrm_config'] = {
            'enable_multi_timescale': self.config.enable_multi_timescale,
            'enable_act': self.config.enable_act,
            'max_iterations': self.config.max_iterations,
            'convergence_threshold': self.config.convergence_threshold,
            'confidence_threshold': self.config.confidence_threshold
        }

        return await self.coordinator.process_user_input(user_input, context)

    async def store_memory_with_timestamp(self, *args, **kwargs):
        """委托记忆存储"""
        if hasattr(self.coordinator, 'memory_coordinator'):
            return await self.coordinator.memory_coordinator.store_memory_with_timestamp(*args, **kwargs)
        return await self.coordinator.store_memory(*args, **kwargs)

    def __getattr__(self, name):
        """将其他属性访问委托给底层协调器"""
        return getattr(self.coordinator, name)


# 便捷函数
def create_hrm_coordinator(base_coordinator, config: HRMConfig = None) -> HRMCoordinatorWrapper:
    """创建 HRM 协调器包装器"""
    return HRMCoordinatorWrapper(base_coordinator, config)
