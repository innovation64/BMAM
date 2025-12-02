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
import json
from pathlib import Path
from typing import Dict, List, Any
from collections import deque

from ...base import BrainAgent, AgentMessage, BrainRegion
from .data_models import WorkingMemoryItem
from .core_operations import CoreOperationsMixin
from .task_coordination import TaskCoordinationMixin
from .confidence_assessment import ConfidenceAssessmentMixin
from .conflict_detection import ConflictDetectionMixin
from .conflict_detection import ConflictDetectionMixin
from .memory_compression import MemoryCompressionMixin
from ....brain.prefrontal_controller import PrefrontalController

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
        
        # 🧠 Prefrontal Controller (Meta-memory & Routing)
        self.controller = PrefrontalController()

        # 统计信息
        self.total_stored = 0
        self.total_evicted = 0
        self.total_tasks_coordinated = 0
        self.total_reflections = 0

        # 🔥 Auto-persistence setup
        self.state_file = Path("data/prefrontal_state.json")
        self._load_state_from_file()

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
            
        # 🧠 Prefrontal Controller Actions
        elif action == 'route_query':
            # 需要传入其他脑区的引用，这里假设通过brain_coordinator获取或直接传入
            # 为了简化，我们假设调用者会处理脑区引用，或者我们在controller中处理
            # 这里我们暂时只返回controller的统计信息，实际路由逻辑可能需要在BrainNetwork层面调用
            # 或者我们需要在PrefrontalAgent中持有其他脑区的引用(这可能导致循环引用)
            
            # 更好的方式是: PrefrontalAgent作为协调者，接收查询，然后调用BrainNetwork或其他Agent
            # 但PrefrontalAgent目前没有直接持有其他Agent的引用(除了brain_coordinator)
            
            # 临时方案: 仅返回controller统计，实际路由逻辑在BrainNetwork中实现，或者由BrainCoordinator调用
            pass
            
        elif action == 'get_meta_statistics':
            return self.controller.get_statistics()

        return {'error': f'Unknown action: {action}'}

    def export_state(self) -> Dict[str, Any]:
        """
        Export prefrontal cortex state to JSON-serializable format for BMA archive.

        Returns:
            Dict containing working memory items and task state
        """
        from datetime import datetime

        # Serialize working memory items
        working_memory_data = []
        for item in self.working_memory:
            working_memory_data.append({
                'id': item.id,
                'content': item.content,
                'task_type': item.task_type,
                'priority': item.priority,
                'timestamp': item.timestamp.isoformat() if item.timestamp else None,
                'metadata': item.metadata
            })

        # Serialize task stack
        task_stack_data = []
        for task in self.current_task_stack:
            # Handle datetime objects in task dict
            task_copy = task.copy()
            for key, value in task_copy.items():
                if isinstance(value, datetime):
                    task_copy[key] = value.isoformat()
            task_stack_data.append(task_copy)

        # Serialize reflection history
        reflection_data = []
        for reflection in self.reflection_history:
            # Handle datetime objects in reflection dict
            refl_copy = reflection.copy()
            for key, value in refl_copy.items():
                if isinstance(value, datetime):
                    refl_copy[key] = value.isoformat()
            reflection_data.append(refl_copy)

        # Export state
        state = {
            'format_version': '1.0.0',
            'agent_id': self.agent_id,
            'brain_region': 'prefrontal',
            'capacity': self.capacity,
            'working_memory': working_memory_data,
            'task_stack': task_stack_data,
            'reflection_history': reflection_data,
            'statistics': {
                'total_stored': self.total_stored,
                'total_evicted': self.total_evicted,
                'total_tasks_coordinated': self.total_tasks_coordinated,
                'total_reflections': self.total_reflections,
                'current_count': len(self.working_memory)
            }
        }

        logger.info(f"✅ Exported PrefrontalAgent state: {len(working_memory_data)} items in working memory")
        return state

    def load_state(self, state: Dict[str, Any]) -> bool:
        """
        Load prefrontal cortex state from exported data.

        Args:
            state: State dictionary from export_state()

        Returns:
            True if successful, False otherwise
        """
        from datetime import datetime

        try:
            # Validate format
            if state.get('brain_region') != 'prefrontal':
                logger.error(f"❌ Invalid brain region: {state.get('brain_region')}")
                return False

            # Clear current state
            self.working_memory.clear()
            self.memory_dict.clear()
            self.current_task_stack.clear()
            self.reflection_history.clear()

            # Restore configuration
            self.capacity = state.get('capacity', self.capacity)

            # Restore working memory items
            for item_data in state.get('working_memory', []):
                from .data_models import WorkingMemoryItem
                item = WorkingMemoryItem(
                    id=item_data['id'],
                    content=item_data['content'],
                    task_type=item_data.get('task_type', 'general'),
                    priority=item_data.get('priority', 0),
                    timestamp=datetime.fromisoformat(item_data['timestamp']) if item_data.get('timestamp') else datetime.now(),
                    metadata=item_data.get('metadata', {})
                )

                self.working_memory.append(item)
                self.memory_dict[item.id] = item

            # Restore task stack
            for task_data in state.get('task_stack', []):
                # Restore datetime objects
                task_copy = task_data.copy()
                for key, value in task_copy.items():
                    if isinstance(value, str) and 'T' in value:  # ISO format detection
                        try:
                            task_copy[key] = datetime.fromisoformat(value)
                        except:
                            pass
                self.current_task_stack.append(task_copy)

            # Restore reflection history
            for refl_data in state.get('reflection_history', []):
                # Restore datetime objects
                refl_copy = refl_data.copy()
                for key, value in refl_copy.items():
                    if isinstance(value, str) and 'T' in value:  # ISO format detection
                        try:
                            refl_copy[key] = datetime.fromisoformat(value)
                        except:
                            pass
                self.reflection_history.append(refl_copy)

            # Restore statistics
            stats = state.get('statistics', {})
            self.total_stored = stats.get('total_stored', 0)
            self.total_evicted = stats.get('total_evicted', 0)
            self.total_tasks_coordinated = stats.get('total_tasks_coordinated', 0)
            self.total_reflections = stats.get('total_reflections', 0)

            logger.info(f"✅ Loaded PrefrontalAgent state: {len(self.working_memory)} items in working memory")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to load PrefrontalAgent state: {e}")
            return False

    def _load_state_from_file(self):
        """Auto-load state from JSON file on startup"""
        if not self.state_file.exists():
            logger.info(f"📂 No existing state file found at {self.state_file}, starting fresh")
            return

        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                success = self.load_state(state)
                if success:
                    logger.info(f"✅ Auto-loaded PrefrontalCortex state from {self.state_file}")
                else:
                    logger.warning(f"⚠️  Failed to load PrefrontalCortex state from {self.state_file}")
        except Exception as e:
            logger.error(f"❌ Error loading PrefrontalCortex state from {self.state_file}: {e}")

    def _save_state_to_file(self):
        """Auto-save current state to JSON file"""
        try:
            # Ensure data directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            state = self.export_state()
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            logger.error(f"❌ Error saving PrefrontalCortex state to {self.state_file}: {e}")
