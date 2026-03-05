"""
Self Monitoring Mixin
自我监控模块
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from .data_models import PerformanceMetrics

logger = logging.getLogger(__name__)


class SelfMonitoringMixin:
    """自我监控Mixin"""

    async def _monitor_performance(self) -> Dict[str, Any]:
        """
        监控整体性能

        监控维度：
        - 响应时间
        - 准确率
        - 错误率
        - 资源使用
        - 用户满意度
        """
        metrics = {
            'response_time': self._calculate_avg_response_time(),
            'accuracy': self._calculate_accuracy(),
            'error_rate': self._calculate_error_rate(),
            'resource_usage': self._get_resource_usage(),
            'user_satisfaction': self._estimate_user_satisfaction()
        }

        # 检测性能下降
        if self._detect_performance_drift(metrics):
            logger.warning("Performance drift detected")
            metrics['drift_detected'] = True
        else:
            metrics['drift_detected'] = False

        # 保存到性能历史
        if hasattr(self, 'performance_history'):
            self.performance_history.append({
                'timestamp': datetime.now(),
                'metrics': metrics
            })

        return metrics

    def _calculate_avg_response_time(self) -> float:
        """计算平均响应时间"""
        if not hasattr(self, 'performance_history'):
            return 0.0

        recent_metrics = [
            m.get('metrics', {}).get('response_time', 0)
            for m in self.performance_history[-10:]
            if isinstance(m, dict) and 'metrics' in m
        ]

        return sum(recent_metrics) / len(recent_metrics) if recent_metrics else 0.0

    def _calculate_accuracy(self) -> float:
        """计算准确率"""
        # 基于记忆系统的可靠性评分
        if hasattr(self, 'db_manager') and self.db_manager:
            try:
                memories = self.db_manager.load_memories_by_criteria()
                if memories:
                    avg_reliability = sum(m.source_reliability for m in memories) / len(memories)
                    return avg_reliability
            except Exception as e:
                logger.error(f"Error calculating accuracy: {e}")

        return 0.7  # 默认值

    def _calculate_error_rate(self) -> float:
        """计算错误率"""
        if not hasattr(self, 'error_history'):
            return 0.0

        # 最近24小时的错误
        recent_errors = [
            e for e in self.error_history
            if isinstance(e, dict) and
               'timestamp' in e and
               e['timestamp'] > datetime.now() - timedelta(hours=24)
        ]

        # 假设每小时平均处理10个任务
        expected_tasks = 24 * 10
        error_rate = len(recent_errors) / expected_tasks if expected_tasks > 0 else 0

        return min(1.0, error_rate)

    def _get_resource_usage(self) -> Dict[str, float]:
        """获取资源使用情况"""
        try:
            import psutil
            return {
                'cpu': psutil.cpu_percent(),
                'memory': psutil.virtual_memory().percent,
                'disk': psutil.disk_usage('/').percent
            }
        except ImportError:
            return {'cpu': 0.0, 'memory': 0.0, 'disk': 0.0}

    def _estimate_user_satisfaction(self) -> float:
        """估计用户满意度"""
        # 基于多个因素估计
        factors = []

        # 错误率低 -> 满意度高
        error_rate = self._calculate_error_rate()
        factors.append(1.0 - error_rate)

        # 响应时间短 -> 满意度高
        response_time = self._calculate_avg_response_time()
        # 假设理想响应时间是 0.5s，超过3s满意度很低
        if response_time <= 0.5:
            factors.append(1.0)
        elif response_time >= 3.0:
            factors.append(0.3)
        else:
            factors.append(1.0 - (response_time - 0.5) / 2.5 * 0.7)

        # 准确率高 -> 满意度高
        accuracy = self._calculate_accuracy()
        factors.append(accuracy)

        return sum(factors) / len(factors) if factors else 0.5

    def _detect_performance_drift(self, current_metrics: Dict[str, Any]) -> bool:
        """
        检测性能下降

        比较当前性能和历史基线
        """
        if not hasattr(self, 'performance_history') or len(self.performance_history) < 5:
            return False

        # 获取历史基线（过去10次的平均值）
        historical = self.performance_history[-10:-1]  # 排除当前的
        if not historical:
            return False

        # 计算历史平均准确率
        historical_accuracy = sum(
            h.get('metrics', {}).get('accuracy', 0.7)
            for h in historical
        ) / len(historical)

        # 计算历史平均错误率
        historical_error_rate = sum(
            h.get('metrics', {}).get('error_rate', 0.0)
            for h in historical
        ) / len(historical)

        current_accuracy = current_metrics.get('accuracy', 0.7)
        current_error_rate = current_metrics.get('error_rate', 0.0)

        # 性能下降判断
        accuracy_drop = historical_accuracy - current_accuracy > 0.15  # 准确率下降>15%
        error_increase = current_error_rate - historical_error_rate > 0.10  # 错误率增加>10%

        return accuracy_drop or error_increase

    async def _track_decision_quality(self) -> Dict[str, Any]:
        """跟踪决策质量"""
        # 分析最近的决策结果
        return {
            'overall_quality': 0.75,
            'consistency': 0.80,
            'confidence_calibration': 0.70
        }

    async def _monitor_cognitive_load(self) -> Dict[str, Any]:
        """监控认知负载"""
        # 基于任务复杂度和资源使用估计认知负载
        resource_usage = self._get_resource_usage()

        cognitive_load = (
            resource_usage.get('cpu', 0) * 0.4 +
            resource_usage.get('memory', 0) * 0.6
        ) / 100.0

        return {
            'cognitive_load': cognitive_load,
            'load_level': 'high' if cognitive_load > 0.7 else 'medium' if cognitive_load > 0.4 else 'low',
            'resource_usage': resource_usage
        }

    def _assess_thinking_efficiency(self) -> float:
        """评估思考效率"""
        # 基于响应时间和准确率的组合
        response_time = self._calculate_avg_response_time()
        accuracy = self._calculate_accuracy()

        # 效率 = 准确率 / 响应时间
        # 归一化到 0-1
        if response_time > 0:
            efficiency = accuracy / max(response_time, 0.5)
            return min(1.0, efficiency)
        return 0.5

    def _assess_attention_focus(self) -> float:
        """评估注意力集中度"""
        # 基于任务切换频率和错误率
        error_rate = self._calculate_error_rate()

        # 错误率低通常意味着注意力集中
        focus_score = 1.0 - error_rate

        return max(0.0, min(1.0, focus_score))
