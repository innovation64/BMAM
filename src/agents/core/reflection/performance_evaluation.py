"""
Performance Evaluation Mixin
性能评估模块
"""

import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class PerformanceEvaluationMixin:
    """性能评估Mixin"""

    async def _evaluate_overall_performance(self, time_window: int = 3600) -> Dict:
        """
        评估整体性能

        评估维度：
        - 任务完成质量
        - 响应速度
        - 错误率趋势
        - 改进速度
        - 学习效率
        """
        evaluation = {
            'quality_score': self._calculate_quality_score(time_window),
            'efficiency_score': self._calculate_efficiency_score(time_window),
            'reliability_score': self._calculate_reliability_score(time_window),
            'improvement_trend': await self._assess_improvement_trends(time_window),
            'learning_rate': self._calculate_learning_rate()
        }

        # 计算综合分数
        evaluation['overall_score'] = (
            evaluation['quality_score'] * 0.3 +
            evaluation['efficiency_score'] * 0.2 +
            evaluation['reliability_score'] * 0.3 +
            evaluation['learning_rate'] * 0.2
        )

        return evaluation

    def _calculate_quality_score(self, time_window: int) -> float:
        """计算质量分数"""
        if not hasattr(self, 'db_manager') or not self.db_manager:
            return 0.7  # 默认值

        try:
            # 获取时间窗口内的记忆
            cutoff_time = datetime.now() - timedelta(seconds=time_window)
            memories = self.db_manager.load_memories_by_criteria()

            recent_memories = [
                m for m in memories
                if m.timestamp > cutoff_time
            ]

            if not recent_memories:
                return 0.7

            # 基于重要性和可靠性计算质量
            avg_importance = sum(m.importance for m in recent_memories) / len(recent_memories)
            avg_reliability = sum(m.source_reliability for m in recent_memories) / len(recent_memories)

            quality_score = (avg_importance * 0.6 + avg_reliability * 0.4)
            return quality_score

        except Exception as e:
            logger.error(f"Error calculating quality score: {e}")
            return 0.7

    def _calculate_efficiency_score(self, time_window: int) -> float:
        """计算效率分数"""
        if not hasattr(self, 'performance_history'):
            return 0.7

        # 获取时间窗口内的性能记录
        cutoff_time = datetime.now() - timedelta(seconds=time_window)
        recent_performance = [
            p for p in self.performance_history
            if isinstance(p, dict) and
               'timestamp' in p and
               p['timestamp'] > cutoff_time
        ]

        if not recent_performance:
            return 0.7

        # 基于响应时间和准确率计算效率
        response_times = [
            p.get('metrics', {}).get('response_time', 1.0)
            for p in recent_performance
        ]
        accuracies = [
            p.get('metrics', {}).get('accuracy', 0.7)
            for p in recent_performance
        ]

        avg_response_time = sum(response_times) / len(response_times) if response_times else 1.0
        avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0.7

        # 效率 = 准确率 / 响应时间 (归一化)
        # 假设理想响应时间是0.5s
        time_efficiency = min(1.0, 0.5 / max(avg_response_time, 0.1))
        efficiency_score = (avg_accuracy * 0.7 + time_efficiency * 0.3)

        return min(1.0, efficiency_score)

    def _calculate_reliability_score(self, time_window: int) -> float:
        """计算可靠性分数"""
        if not hasattr(self, 'error_history'):
            return 0.8

        # 获取时间窗口内的错误
        cutoff_time = datetime.now() - timedelta(seconds=time_window)
        recent_errors = [
            e for e in self.error_history
            if isinstance(e, dict) and
               'timestamp' in e and
               e['timestamp'] > cutoff_time
        ]

        # 假设时间窗口内预期处理的任务数
        expected_tasks = time_window / 360  # 假设每6分钟一个任务
        error_rate = len(recent_errors) / max(expected_tasks, 1)

        # 可靠性 = 1 - 错误率
        reliability_score = max(0.0, 1.0 - error_rate)

        return reliability_score

    async def _assess_improvement_trends(self, time_window: int) -> Dict[str, Any]:
        """评估改进趋势"""
        if not hasattr(self, 'performance_history') or len(self.performance_history) < 2:
            return {
                'trend': 'insufficient_data',
                'improvement_rate': 0.0
            }

        # 获取历史数据
        all_performance = self.performance_history

        # 分成两个时间段比较
        mid_point = len(all_performance) // 2
        early_half = all_performance[:mid_point]
        recent_half = all_performance[mid_point:]

        if not early_half or not recent_half:
            return {'trend': 'insufficient_data', 'improvement_rate': 0.0}

        # 计算两个时段的平均准确率
        early_accuracy = sum(
            p.get('metrics', {}).get('accuracy', 0.7)
            for p in early_half
        ) / len(early_half)

        recent_accuracy = sum(
            p.get('metrics', {}).get('accuracy', 0.7)
            for p in recent_half
        ) / len(recent_half)

        improvement_rate = recent_accuracy - early_accuracy

        if improvement_rate > 0.05:
            trend = 'improving'
        elif improvement_rate < -0.05:
            trend = 'declining'
        else:
            trend = 'stable'

        return {
            'trend': trend,
            'improvement_rate': improvement_rate,
            'early_accuracy': early_accuracy,
            'recent_accuracy': recent_accuracy
        }

    def _calculate_learning_rate(self) -> float:
        """计算学习速率"""
        # 基于洞察生成数量和时间计算学习速率
        insights_generated = getattr(self, 'insights_generated', 0)
        patterns_identified = getattr(self, 'patterns_identified', 0)

        # 简单的学习速率估计
        learning_indicators = insights_generated * 0.6 + patterns_identified * 0.4

        # 归一化到0-1范围
        # 假设100个学习指标是优秀的学习速率
        learning_rate = min(1.0, learning_indicators / 100)

        return learning_rate

    def _assess_memory_system_health(self, memories: List) -> Dict[str, float]:
        """评估记忆系统健康度"""
        from ....memory.memory_item import MemoryItem

        if not memories:
            return {'overall_health': 0.0}

        # 过滤有效的记忆项
        valid_memories = [m for m in memories if isinstance(m, MemoryItem)]
        if not valid_memories:
            return {'overall_health': 0.0}

        health_metrics = {
            'consolidation_rate': sum(
                1 for m in valid_memories if m.consolidation_level >= 2
            ) / len(valid_memories),
            'access_rate': sum(
                1 for m in valid_memories if m.access_frequency > 0
            ) / len(valid_memories),
            'association_rate': sum(
                1 for m in valid_memories if m.associations
            ) / len(valid_memories),
            'importance_distribution': sum(
                m.importance for m in valid_memories
            ) / len(valid_memories),
            'reliability_score': sum(
                m.source_reliability for m in valid_memories
            ) / len(valid_memories)
        }

        health_metrics['overall_health'] = sum(health_metrics.values()) / len(health_metrics)

        return health_metrics

    def _assess_learning_effectiveness(self, memories: List) -> Dict[str, float]:
        """评估学习有效性"""
        from ....memory.memory_item import MemoryItem

        if not memories:
            return {'effectiveness': 0.0}

        valid_memories = [m for m in memories if isinstance(m, MemoryItem)]
        if not valid_memories:
            return {'effectiveness': 0.0}

        # 语义记忆和洞察记忆比例
        semantic_memories = [m for m in valid_memories if m.memory_type == 'semantic']
        insight_memories = [m for m in valid_memories if 'insight' in m.context_tags]

        return {
            'semantic_ratio': len(semantic_memories) / len(valid_memories),
            'insight_generation_rate': len(insight_memories) / len(valid_memories),
            'consolidation_effectiveness': sum(
                m.consolidation_level for m in valid_memories
            ) / (len(valid_memories) * 3),
            'effectiveness': (len(semantic_memories) + len(insight_memories)) / len(valid_memories)
        }

    def _calculate_overall_confidence(self, assessment: Dict) -> float:
        """计算整体置信度"""
        scores = []

        if 'memory_system_health' in assessment:
            scores.append(assessment['memory_system_health'].get('overall_health', 0.5))

        if 'learning_effectiveness' in assessment:
            scores.append(assessment['learning_effectiveness'].get('effectiveness', 0.5))

        if 'emotional_patterns' in assessment:
            scores.append(assessment['emotional_patterns'].get('emotional_health', 0.5))

        return sum(scores) / len(scores) if scores else 0.5
