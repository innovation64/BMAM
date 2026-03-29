"""
Core Operations for Prefrontal Agent
核心操作模块 - 存储、检索、清理
"""

import logging
from typing import Dict, List, Any
from datetime import datetime
import uuid

from .data_models import WorkingMemoryItem

logger = logging.getLogger(__name__)


class CoreOperationsMixin:
    """Core operations mixin for PrefrontalAgent"""

    async def store_item(
        self,
        content: str,
        task_type: str = 'general',
        priority: int = 0,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        存储工作记忆项 (FIFO)

        Args:
            content: 记忆内容
            task_type: 任务类型
            priority: 优先级 (0-10)
            metadata: 元数据

        Returns:
            {'memory_id': str, 'stored': bool, 'evicted': Optional[str]}
        """

        # 创建记忆项
        item = WorkingMemoryItem(
            id=uuid.uuid4().hex,
            content=content,
            timestamp=datetime.now(),
            task_type=task_type,
            priority=priority,
            metadata=metadata or {}
        )

        # 容量满时驱逐最低优先级项（不是 FIFO）
        evicted_id = None
        async with self._memory_write_lock:
            if len(self.working_memory) >= self.capacity:
                evicted = self._evict_lowest_priority()
                if evicted:
                    evicted_id = evicted.id

            self.working_memory.append(item)
            self.memory_dict[item.id] = item

        self.total_stored += 1

        # 🔥 Auto-persist to JSON file
        self._save_state_to_file()

        return {
            'memory_id': item.id,
            'stored': True,
            'evicted': evicted_id,
            'capacity_status': self._get_capacity_status()
        }

    def retrieve_items(
        self,
        task_type: str = None,
        k: int = 10
    ) -> Dict[str, Any]:
        """
        检索工作记忆

        Args:
            task_type: 任务类型过滤 (None = 所有)
            k: 返回数量

        Returns:
            {'items': List[Dict], 'count': int}
        """

        # 过滤
        items = []
        for item in self.working_memory:
            if task_type and item.task_type != task_type:
                continue
            items.append(item)

        # 按优先级和时间排序 (高优先级 + 新的 优先)
        items.sort(
            key=lambda x: (x.priority, x.timestamp),
            reverse=True
        )

        # 限制数量
        items = items[:k]

        return {
            'items': [self._item_to_dict(item) for item in items],
            'count': len(items)
        }

    def clear_all(self) -> Dict[str, Any]:
        """清空所有工作记忆"""
        count = len(self.working_memory)
        self.working_memory.clear()
        self.memory_dict.clear()

        # 🔥 Auto-persist to JSON file
        self._save_state_to_file()

        return {
            'cleared': count,
            'capacity_status': self._get_capacity_status()
        }

    def _get_capacity_status(self) -> Dict[str, Any]:
        """获取容量状态"""
        current = len(self.working_memory)
        return {
            'current': current,
            'max': self.capacity,
            'usage_percent': (current / self.capacity) * 100 if self.capacity > 0 else 0
        }

    async def coordinate_task(
        self,
        task_description: str,
        required_agents: List[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行控制: 协调多个脑区完成复杂任务 (Plan C)

        模拟前额叶的执行控制功能:
        - 任务分解
        - 脑区协调
        - 工作记忆管理

        Args:
            task_description: 任务描述
            required_agents: 需要协调的智能体
            context: 任务上下文

        Returns:
            {'task_id': str, 'plan': str, 'agents_coordinated': List[str]}
        """

        if not self.brain_coordinator:
            return {
                'error': 'Brain coordinator not available',
                'task_id': None
            }

        try:
            # 使用LLM进行任务分解和规划
            prompt = f"""作为前额叶执行控制中心,请为以下任务制定执行计划:

任务描述: {task_description}
可用脑区: {', '.join(required_agents)}
当前上下文: {json.dumps(context, indent=2, ensure_ascii=False)}

请输出:
1. 任务分解 (子任务列表)
2. 脑区协调方案 (每个子任务需要哪些脑区)
3. 执行顺序

以结构化的JSON格式输出。"""

            plan_str = await self.call_llm(
                prompt=prompt,
                context=context,
                max_tokens=800,
                temperature=0.5
            )

            # 创建任务记录
            task_id = uuid.uuid4().hex
            task_record = {
                'task_id': task_id,
                'description': task_description,
                'required_agents': required_agents,
                'plan': plan_str,
                'status': 'planned',
                'created_at': datetime.now().isoformat()
            }

            # 压入任务栈
            self.current_task_stack.append(task_record)

            # 将任务添加到工作记忆
            await self.store_item(
                content=f"Task: {task_description[:50]}...",
                task_type='coordination',
                priority=8,
                metadata={'task_id': task_id, 'agents': required_agents}
            )

            self.total_tasks_coordinated += 1

            # 🔥 Auto-persist (store_item already saves, but task_stack was modified)
            # Note: store_item() above already called _save_state_to_file()

            return {
                'task_id': task_id,
                'plan': plan_str,
                'agents_coordinated': required_agents,
                'status': 'planned'
            }

        except (json.JSONDecodeError) as e:
            logger.error(f"Failed to coordinate task: {e}")
            return {
                'error': str(e),
                'task_id': None
            }

    async def reflect_on_performance(
        self,
        task_description: str,
        performance_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        元认知: 对系统表现进行反思 (Plan C)

        模拟前额叶的自我监控和反思功能:
        - 评估任务完成质量
        - 识别问题和改进点
        - 生成优化建议

        Args:
            task_description: 任务描述
            performance_data: 性能数据 (响应时间、成功率等)

        Returns:
            {'reflection_id': str, 'insights': str, 'suggestions': List[str]}
        """

        try:
            # 使用LLM进行反思分析
            prompt = f"""作为前额叶元认知系统,请对以下任务的执行表现进行反思:

任务: {task_description}
性能数据:
{json.dumps(performance_data, indent=2, ensure_ascii=False)}

请分析:
1. 任务完成质量评估
2. 发现的问题和瓶颈
3. 改进建议
4. 脑区协调的优化方向

以结构化方式输出洞察和建议。"""

            reflection_str = await self.call_llm(
                prompt=prompt,
                context=performance_data,
                max_tokens=1000,
                temperature=0.4
            )

            # 创建反思记录
            reflection_id = uuid.uuid4().hex
            reflection_record = {
                'reflection_id': reflection_id,
                'task_description': task_description,
                'performance_data': performance_data,
                'insights': reflection_str,
                'timestamp': datetime.now().isoformat()
            }

            # 保存到反思历史
            self.reflection_history.append(reflection_record)

            # 限制历史长度
            if len(self.reflection_history) > 50:
                self.reflection_history = self.reflection_history[-50:]

            self.total_reflections += 1

            # 🔥 Auto-persist to JSON file
            self._save_state_to_file()

            return {
                'reflection_id': reflection_id,
                'insights': reflection_str,
                'total_reflections': self.total_reflections
            }

        except (json.JSONDecodeError) as e:
            logger.error(f"Failed to reflect on performance: {e}")
            return {
                'error': str(e),
                'reflection_id': None
            }

    def get_task_status(self) -> Dict[str, Any]:
        """获取当前任务栈状态"""
        return {
            'current_tasks': self.current_task_stack,
            'task_count': len(self.current_task_stack),
            'recent_reflections': self.reflection_history[-5:] if self.reflection_history else []
        }

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'agent_id': self.agent_id,
            'brain_region': self.brain_region,
            'capacity': self.capacity,
            'current_items': len(self.working_memory),
            'usage_percent': self._get_capacity_status()['usage_percent'],
            'total_stored': self.total_stored,
            'total_evicted': self.total_evicted,
            'total_tasks_coordinated': self.total_tasks_coordinated,
            'total_reflections': self.total_reflections,
            'executive_control_enabled': self.brain_coordinator is not None
        }

    def _item_to_dict(self, item: WorkingMemoryItem) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': item.id,
            'content': item.content,
            'timestamp': item.timestamp.isoformat(),
            'task_type': item.task_type,
            'priority': item.priority,
            'metadata': item.metadata
        }

    # ============================================================================
    # Phase 2: 元认知与冲突检测 (Metacognition & Conflict Detection)
    # ============================================================================