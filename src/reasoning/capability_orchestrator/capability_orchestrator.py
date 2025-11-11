"""
🧠 推理能力编排器 - Reasoning Capability Orchestrator

职责:
1. 接收CapabilityAnalyzer的分析结果
2. 按优先级顺序执行各推理能力
3. 在能力之间传递中间结果
4. 组合最终答案

Author: BMAM Team
"""

import logging
import os
from typing import Dict, Any

from .basic_capabilities import BasicCapabilitiesMixin
from .reasoning_capabilities import ReasoningCapabilitiesMixin
from .answer_synthesis import AnswerSynthesisMixin
from .core_execution import CoreExecutionMixin

logger = logging.getLogger(__name__)

# 🚀 性能优化配置
ENABLE_DYNAMIC_CONSTRAINTS = os.getenv('ENABLE_DYNAMIC_CONSTRAINTS', 'false').lower() == 'true'
ENABLE_PARALLEL_EXECUTION = os.getenv('ENABLE_PARALLEL_EXECUTION', 'true').lower() == 'true'


class CapabilityOrchestrator(
    BasicCapabilitiesMixin,
    ReasoningCapabilitiesMixin,
    AnswerSynthesisMixin,
    CoreExecutionMixin
):
    """
    推理能力编排器

    工作流程:
    1. 根据capability分析结果,按priority执行
    2. 每个能力产生中间结果,传递给下一个
    3. 最终组合所有结果
    """

    def __init__(self, brain_agents: Dict[str, Any], memory_system=None):
        """
        Args:
            brain_agents: 所有brain agents的字典 {agent_id: agent_instance}
            memory_system: 记忆系统实例 (用于HippocampalPrefrontalLoop)
        """
        self.agents = brain_agents
        self.memory_system = memory_system

        # 🔥 集成条件约束引擎
        from src.reasoning.conditional_constraint_engine import ConditionalConstraintEngine
        self.constraint_engine = ConditionalConstraintEngine()

        # 🔥 NEW: 集成3个脑区协作模块
        from src.brain.region_activation import RegionActivationDynamics
        from src.brain.hippocampal_loop import HippocampalPrefrontalLoop
        from src.brain.collaborative_output import CollaborativeOutput

        self.region_activation = RegionActivationDynamics()
        self.hippocampal_loop = HippocampalPrefrontalLoop(
            memory_system=memory_system
        ) if memory_system else None
        self.collaborative_output = CollaborativeOutput(
            brain_agents=brain_agents
        )

        logger.debug("✅ Initialized CapabilityOrchestrator with ConditionalConstraintEngine")
        logger.info("🔥 Brain collaboration modules integrated")
