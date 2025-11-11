"""
Prefrontal Agent - 前额叶智能体
对应脑区: 前额叶皮层 (Prefrontal Cortex)
主要功能: 工作记忆 + 执行控制 + 反思

核心设计:
1. 极小容量 (10条) - 符合Miller's 7±2法则
2. FIFO策略 (先进先出,不保留)
3. 不使用遗忘机制 (直接清理最旧的)
4. 用于临时任务状态管理
5. 执行控制: 协调其他脑区,规划任务
6. 元认知: 自我监控和反思
"""

import logging
from typing import Dict, List, Any
from collections import deque

from ...base import BrainAgent, AgentMessage, BrainRegion
from .data_models import WorkingMemoryItem
from .core_operations import CoreOperationsMixin
from .task_coordination import TaskCoordinationMixin
from .confidence_assessment import ConfidenceAssessmentMixin
from .conflict_detection import ConflictDetectionMixin
from .memory_compression import MemoryCompressionMixin

logger = logging.getLogger(__name__)


class PrefrontalAgent(
    CoreOperationsMixin,
    TaskCoordinationMixin,
    ConfidenceAssessmentMixin,
    ConflictDetectionMixin,
    MemoryCompressionMixin,
    BrainAgent
):
    """
    前额叶智能体 - 工作记忆 + 执行控制 + 反思

    容量: 10条 (Miller's 7±2法则的上限)
    存储格式: FIFO Queue (deque)
    清理机制: FIFO (不遗忘,直接替换)
    功能: 临时任务状态、当前对话上下文、推理过程
    执行控制: 协调其他脑区,任务规划
    元认知: 自我监控和反思
    """

    def __init__(self, capacity: int = 10, brain_coordinator=None, client=None):
        super().__init__(
            agent_id="prefrontal",
            brain_region=BrainRegion.PREFRONTAL,
            system_prompt="""You are the Prefrontal Cortex agent, responsible for working memory, executive control, and metacognition.
            You hold temporary information for immediate use (10 items max).
            You use FIFO strategy to replace old items when capacity is reached.
            You prioritize high-priority tasks and current conversation context.
            You coordinate other brain regions for complex tasks.
            You perform self-monitoring and reflection on system performance.""",
            client=client
        )

        # 🔥 工作记忆 (FIFO队列)
        self.capacity = capacity
        self.working_memory: deque = deque(maxlen=capacity)
        self.memory_dict: Dict[str, WorkingMemoryItem] = {}

        # 🧠 集成执行控制功能
        self.brain_coordinator = brain_coordinator  # 用于协调其他脑区
        self.current_task_stack: List[Dict[str, Any]] = []  # 任务栈
        self.reflection_history: List[Dict[str, Any]] = []  # 反思历史

        # 统计信息
        self.total_stored = 0
        self.total_evicted = 0
        self.total_tasks_coordinated = 0
        self.total_reflections = 0

        logger.info(f"✅ PrefrontalAgent initialized (capacity={capacity})")

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """处理消息"""
        action = message.content.get('action')

        if action == 'store':
            return await self.store_item(
                content=message.content['content'],
                task_type=message.content.get('task_type', 'general'),
                priority=message.content.get('priority', 0),
                metadata=message.content.get('metadata', {})
            )

        elif action == 'retrieve':
            return self.retrieve_items(
                task_type=message.content.get('task_type'),
                limit=message.content.get('limit', self.capacity)
            )

        elif action == 'clear':
            return self.clear_all()

        elif action == 'coordinate':
            return await self.coordinate_task(
                task_description=message.content['task_description'],
                required_regions=message.content.get('required_regions', [])
            )

        elif action == 'reflect':
            return await self.reflect_on_performance(
                time_window_minutes=message.content.get('time_window_minutes', 60)
            )

        elif action == 'assess_confidence':
            return await self.assess_confidence(
                query=message.content['query'],
                results=message.content.get('results', []),
                context=message.content.get('context', {})
            )

        elif action == 'detect_conflicts':
            return await self.detect_conflicts(
                memories=message.content.get('memories', [])
            )

        elif action == 'compress':
            return await self.compress_working_memory()

        elif action == 'get_status':
            return self.get_task_status()

        elif action == 'get_statistics':
            return self.get_statistics()

        return {'error': f'Unknown action: {action}'}
