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

🔥 Phase 3 Enhancement:
- Adaptive capacity based on task complexity
- Memory compression for related items
- Priority-based eviction instead of pure FIFO
"""

# 🔥 NEW: Configuration for adaptive capacity
CAPACITY_CONFIG = {
    'min_capacity': 7,        # Miller's law lower bound (7-2)
    'default_capacity': 10,   # Default capacity
    'max_capacity': 15,       # Miller's law upper bound (7+2) + buffer
    'complexity_simple': 7,
    'complexity_medium': 10,
    'complexity_complex': 15,
    'auto_compress_threshold': 0.8,  # Compress when 80% full
}

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
            You hold temporary information for immediate use (adaptive capacity).
            You use priority-based eviction strategy.
            You prioritize high-priority tasks and current conversation context.
            You coordinate other brain regions for complex tasks.
            You perform self-monitoring and reflection on system performance.""",
            client=client
        )

        # 🔥 工作记忆 (自适应容量)
        self.base_capacity = capacity
        self.capacity = capacity
        self.max_capacity = CAPACITY_CONFIG['max_capacity']
        self.working_memory: deque = deque(maxlen=self.max_capacity)  # Use max for storage
        self.memory_dict: Dict[str, WorkingMemoryItem] = {}
        self._current_task_complexity = 'medium'  # Track current task complexity

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
        self.total_compressions = 0  # 🔥 NEW

        # 🔥 Auto-persistence setup (使用 BMAMPaths 支持并行测试)
        from src.utils.paths import BMAMPaths
        self.state_file = BMAMPaths.PREFRONTAL_STATE
        self._load_state_from_file()

        logger.info(f"✅ PrefrontalAgent initialized (capacity={capacity}, max={self.max_capacity})")

    def set_task_complexity(self, complexity: str) -> Dict[str, Any]:
        """
        Set task complexity to adjust working memory capacity
        设置任务复杂度以调整工作记忆容量

        Args:
            complexity: 'simple', 'medium', 'complex'

        Returns:
            {
                'previous_capacity': int,
                'new_capacity': int,
                'complexity': str
            }
        """
        prev_capacity = self.capacity
        self._current_task_complexity = complexity

        if complexity == 'simple':
            self.capacity = CAPACITY_CONFIG['complexity_simple']
        elif complexity == 'complex':
            self.capacity = CAPACITY_CONFIG['complexity_complex']
        else:
            self.capacity = CAPACITY_CONFIG['complexity_medium']

        logger.info(f"📊 Working memory capacity adjusted: {prev_capacity} → {self.capacity} (complexity={complexity})")

        # 🔥 Trigger compression if over new capacity
        if len(self.working_memory) > self.capacity:
            self._trigger_compression()

        return {
            'previous_capacity': prev_capacity,
            'new_capacity': self.capacity,
            'complexity': complexity
        }

    def _estimate_task_complexity(self, content: str, task_type: str) -> str:
        """
        Estimate task complexity from content and type
        从内容和类型估计任务复杂度
        """
        content_lower = content.lower() if content else ''

        # Complex indicators
        complex_indicators = [
            'multi-hop', 'reasoning chain', 'analyze', 'compare',
            'relationship', 'inference', 'complex', 'multiple'
        ]
        complex_task_types = ['reasoning_chain', 'multi_hop', 'analysis', 'planning']

        # Simple indicators
        simple_indicators = ['store', 'retrieve', 'simple', 'direct']
        simple_task_types = ['store', 'retrieve', 'lookup', 'general']

        complex_count = sum(1 for ind in complex_indicators if ind in content_lower)
        simple_count = sum(1 for ind in simple_indicators if ind in content_lower)

        if task_type in complex_task_types or complex_count >= 2:
            return 'complex'
        elif task_type in simple_task_types or simple_count >= 2:
            return 'simple'
        return 'medium'

    def _should_auto_compress(self) -> bool:
        """Check if auto-compression should be triggered"""
        if len(self.working_memory) == 0:
            return False
        usage_ratio = len(self.working_memory) / self.capacity
        return usage_ratio >= CAPACITY_CONFIG['auto_compress_threshold']

    def _trigger_compression(self) -> int:
        """
        Compress working memory by merging related items
        通过合并相关项来压缩工作记忆

        Returns:
            Number of items compressed
        """
        if len(self.working_memory) <= CAPACITY_CONFIG['min_capacity']:
            return 0

        # Group items by task_type
        grouped: Dict[str, List[WorkingMemoryItem]] = {}
        for item in self.working_memory:
            task_type = item.task_type or 'general'
            if task_type not in grouped:
                grouped[task_type] = []
            grouped[task_type].append(item)

        # Compress groups with 3+ items
        compressed_count = 0
        new_items = []

        for task_type, items in grouped.items():
            if len(items) >= 3:
                # Keep highest priority and most recent
                sorted_items = sorted(items, key=lambda x: (-x.priority, x.timestamp), reverse=True)
                # Keep top 2, merge rest into summary
                kept = sorted_items[:2]
                merged = sorted_items[2:]

                # Create summary item
                merged_content = f"[Compressed {len(merged)} items]: " + "; ".join(
                    m.content[:50] for m in merged
                )
                summary_item = WorkingMemoryItem(
                    id=f"compressed_{task_type}_{self.total_compressions}",
                    content=merged_content[:200],
                    timestamp=max(m.timestamp for m in merged),
                    task_type=task_type,
                    priority=max(m.priority for m in merged),
                    metadata={'compressed_from': [m.id for m in merged]}
                )

                new_items.extend(kept)
                new_items.append(summary_item)
                compressed_count += len(merged)

                logger.info(f"📦 Compressed {len(merged)} '{task_type}' items into 1")
            else:
                new_items.extend(items)

        if compressed_count > 0:
            # Rebuild working memory
            self.working_memory.clear()
            self.memory_dict.clear()
            for item in new_items:
                self.working_memory.append(item)
                self.memory_dict[item.id] = item

            self.total_compressions += 1
            logger.info(f"✅ Compression complete: {compressed_count} items compressed")

        return compressed_count

    def _evict_lowest_priority(self) -> WorkingMemoryItem:
        """
        Evict lowest priority item (instead of pure FIFO)
        驱逐最低优先级的项（而非纯FIFO）
        """
        if not self.working_memory:
            return None

        # Find lowest priority item
        lowest = min(self.working_memory, key=lambda x: (x.priority, x.timestamp))

        # Remove it
        self.working_memory.remove(lowest)
        if lowest.id in self.memory_dict:
            del self.memory_dict[lowest.id]

        self.total_evicted += 1
        logger.debug(f"🔻 Evicted low-priority item: {lowest.id[:8]} (priority={lowest.priority})")

        return lowest

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
                internal_results=message.content.get(
                    'internal_results',
                    message.content.get('results', [])
                ),
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
            # 🔥 2025-12-16: 实现路由查询 - 返回路由建议，由 BrainCoordinator 执行
            # PrefrontalAgent 作为"建议者"而非"执行者"，避免循环依赖
            query = message.content.get('query', '')
            context = message.content.get('context', {})
            return await self._generate_routing_recommendation(query, context)
            
        elif action == 'get_meta_statistics':
            return self.controller.get_statistics()

        return {'error': f'Unknown action: {action}'}

    async def _generate_routing_recommendation(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        🔥 2025-12-16: 生成路由建议

        基于查询特征和当前上下文，推荐最合适的脑区组合。
        PrefrontalAgent 作为"建议者"，由 BrainCoordinator 执行实际路由。

        Args:
            query: 用户查询
            context: 上下文信息 (包含 query_type, emotion_state 等)

        Returns:
            Dict containing:
                - recommended_regions: List of brain regions to query
                - priority_weights: Dict of region -> weight
                - reasoning: Explanation of routing decision
                - should_use_parallel: Whether to query regions in parallel
        """
        # 默认推荐
        recommended_regions = []
        priority_weights = {}
        reasoning_parts = []

        query_lower = query.lower()
        query_type = context.get('query_type', 'general')
        emotion_state = context.get('emotion_state', 'neutral')

        # 1. 时间相关查询 → 海马体优先
        time_keywords = ['when', 'what time', 'date', 'yesterday', 'last week', 'ago',
                        '什么时候', '几点', '昨天', '上周', '之前']
        if any(kw in query_lower for kw in time_keywords) or query_type == 'temporal':
            recommended_regions.append('hippocampus')
            priority_weights['hippocampus'] = 0.9
            reasoning_parts.append("时间相关查询 → 海马体 (episodic memory)")

        # 2. 情感相关查询 → 杏仁核优先
        emotion_keywords = ['feel', 'emotion', 'happy', 'sad', 'angry', 'love', 'hate',
                           '感觉', '情绪', '高兴', '难过', '生气', '喜欢', '讨厌']
        if any(kw in query_lower for kw in emotion_keywords) or emotion_state != 'neutral':
            recommended_regions.append('amygdala')
            priority_weights['amygdala'] = 0.8
            reasoning_parts.append("情感相关查询 → 杏仁核 (emotional memory)")

        # 3. 事实/知识查询 → 颞叶优先
        fact_keywords = ['what is', 'who is', 'where is', 'definition', 'meaning',
                        '什么是', '谁是', '在哪里', '定义', '意思']
        if any(kw in query_lower for kw in fact_keywords) or query_type == 'factual':
            recommended_regions.append('temporal_lobe')
            priority_weights['temporal_lobe'] = 0.85
            reasoning_parts.append("事实查询 → 颞叶 (semantic memory)")

        # 4. 习惯/技能查询 → 基底神经节
        habit_keywords = ['how to', 'routine', 'habit', 'usually', 'always',
                         '怎么', '习惯', '通常', '一般']
        if any(kw in query_lower for kw in habit_keywords) or query_type == 'procedural':
            recommended_regions.append('basal_ganglia')
            priority_weights['basal_ganglia'] = 0.75
            reasoning_parts.append("习惯/技能查询 → 基底神经节 (procedural memory)")

        # 5. 默认: 海马体 + 颞叶 (最常用的组合)
        if not recommended_regions:
            recommended_regions = ['hippocampus', 'temporal_lobe']
            priority_weights = {'hippocampus': 0.7, 'temporal_lobe': 0.6}
            reasoning_parts.append("通用查询 → 海马体 + 颞叶 (综合检索)")

        # 6. 判断是否并行查询
        should_use_parallel = len(recommended_regions) > 1

        return {
            'recommended_regions': recommended_regions,
            'priority_weights': priority_weights,
            'reasoning': ' | '.join(reasoning_parts),
            'should_use_parallel': should_use_parallel,
            'query_analysis': {
                'query_type': query_type,
                'emotion_state': emotion_state,
                'query_length': len(query)
            }
        }

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
