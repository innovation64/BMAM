"""
Reflection Triggers Mixin
反思触发器模块
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from .data_models import ReflectionTrigger

logger = logging.getLogger(__name__)


class ReflectionTriggersMixin:
    """反思触发器Mixin"""

    def _should_trigger_reflection(self, context: Dict[str, Any]) -> bool:
        """
        判断是否应该触发反思

        触发条件：
        1. 错误次数达到阈值
        2. 到达时间间隔
        3. 达到任务里程碑
        4. 性能下降超过阈值
        5. 检测到重要模式
        """
        # 检查错误阈值
        if self._check_error_threshold():
            logger.info("Reflection triggered by error threshold")
            return True

        # 检查时间间隔
        if self._check_time_interval():
            logger.info("Reflection triggered by time interval")
            return True

        # 检查任务里程碑
        if self._check_milestone():
            logger.info("Reflection triggered by milestone")
            return True

        # 检查性能阈值
        if self._check_performance_threshold(context):
            logger.info("Reflection triggered by performance threshold")
            return True

        return False

    def _check_error_threshold(self) -> bool:
        """检查错误阈值"""
        if not hasattr(self, 'error_history'):
            return False

        # 获取最近1小时的错误
        recent_errors = [
            e for e in getattr(self, 'error_history', [])
            if isinstance(e, dict) and
               'timestamp' in e and
               e['timestamp'] > datetime.now() - timedelta(hours=1)
        ]

        config = getattr(self, 'config', {})
        error_threshold = config.get('frequency', {}).get('error_threshold', 3)

        return len(recent_errors) >= error_threshold

    def _check_time_interval(self) -> bool:
        """检查时间间隔"""
        if not hasattr(self, 'last_deep_reflection'):
            return True  # 如果从未反思，应该触发

        last_reflection = getattr(self, 'last_deep_reflection', datetime.now())
        config = getattr(self, 'config', {})
        time_interval = config.get('frequency', {}).get('time_interval', 3600)

        time_since_last = (datetime.now() - last_reflection).total_seconds()
        return time_since_last >= time_interval

    def _check_milestone(self) -> bool:
        """检查任务里程碑"""
        # 检查是否达到任务数量里程碑
        tasks_completed = getattr(self, 'tasks_completed_since_reflection', 0)
        config = getattr(self, 'config', {})
        milestone = config.get('frequency', {}).get('milestone_tasks', 10)

        return tasks_completed >= milestone

    def _check_performance_threshold(self, context: Dict[str, Any]) -> bool:
        """检查性能阈值"""
        # 检查性能是否显著下降
        if not hasattr(self, 'performance_history'):
            return False

        performance_history = getattr(self, 'performance_history', [])
        if len(performance_history) < 2:
            return False

        # 比较最近性能和历史平均
        recent_perf = performance_history[-5:] if len(performance_history) >= 5 else performance_history
        historical_perf = performance_history[:-5] if len(performance_history) >= 10 else []

        if not historical_perf:
            return False

        # 简化的性能检查
        recent_avg = sum(recent_perf) / len(recent_perf) if recent_perf else 0
        historical_avg = sum(historical_perf) / len(historical_perf) if historical_perf else 0

        # 如果性能下降超过20%，触发反思
        return recent_avg < historical_avg * 0.8

    def _evaluate_trigger_conditions(self, context: Dict[str, Any]) -> List[ReflectionTrigger]:
        """
        评估所有触发条件，返回触发器列表
        """
        triggers = []

        if self._check_error_threshold():
            triggers.append(ReflectionTrigger(
                trigger_type='error',
                timestamp=datetime.now(),
                context={'reason': 'Error threshold exceeded'},
                priority=0.9
            ))

        if self._check_time_interval():
            triggers.append(ReflectionTrigger(
                trigger_type='scheduled',
                timestamp=datetime.now(),
                context={'reason': 'Scheduled reflection time'},
                priority=0.5
            ))

        if self._check_milestone():
            triggers.append(ReflectionTrigger(
                trigger_type='milestone',
                timestamp=datetime.now(),
                context={'reason': 'Task milestone reached'},
                priority=0.7
            ))

        if self._check_performance_threshold(context):
            triggers.append(ReflectionTrigger(
                trigger_type='threshold',
                timestamp=datetime.now(),
                context={'reason': 'Performance threshold crossed'},
                priority=0.8
            ))

        return triggers

    def _schedule_reflection(self, trigger: ReflectionTrigger) -> Dict[str, Any]:
        """
        安排反思会话
        """
        return {
            'scheduled': True,
            'trigger_type': trigger.trigger_type,
            'priority': trigger.priority,
            'scheduled_time': trigger.timestamp,
            'context': trigger.context
        }

    def _reset_trigger_counters(self):
        """
        重置触发器计数器（在反思后调用）
        """
        if hasattr(self, 'tasks_completed_since_reflection'):
            self.tasks_completed_since_reflection = 0

        if hasattr(self, 'error_history'):
            # 清除旧错误记录
            cutoff_time = datetime.now() - timedelta(hours=24)
            self.error_history = [
                e for e in self.error_history
                if isinstance(e, dict) and
                   'timestamp' in e and
                   e['timestamp'] > cutoff_time
            ]
