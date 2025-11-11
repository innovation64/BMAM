"""
Meta Learning Mixin
元学习模块 - 学习如何学习
"""

import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class MetaLearningMixin:
    """元学习Mixin - 学习如何学习"""

    async def _meta_learn_from_reflection(self, reflection_cycle: Dict) -> Dict:
        """
        从反思周期中元学习

        元学习内容：
        - 哪些反思触发器最有效
        - 哪些洞察导致了实际改进
        - 反思频率是否合适
        - 学习策略是否有效
        """
        learnings = {
            'effective_triggers': self._identify_effective_triggers(),
            'actionable_insights': self._track_actionable_insights(),
            'optimal_frequency': self._calculate_optimal_frequency(),
            'strategy_effectiveness': self._evaluate_strategies()
        }

        # 更新学习策略
        await self._update_learning_strategies(learnings)

        return learnings

    def _identify_effective_triggers(self) -> List[Dict]:
        """识别有效的触发器"""
        # 分析哪些触发器导致了有用的反思
        if not hasattr(self, 'reflection_cycles'):
            return []

        trigger_effectiveness = defaultdict(lambda: {'count': 0, 'useful': 0})

        for cycle in getattr(self, 'reflection_cycles', []):
            if isinstance(cycle, dict):
                triggers = cycle.get('triggers', [])
                insights = cycle.get('insights', [])

                # 如果产生了可操作的洞察，认为触发是有效的
                is_useful = any(
                    insight.get('actionable', False)
                    for insight in insights
                    if isinstance(insight, dict)
                )

                for trigger in triggers:
                    if isinstance(trigger, dict):
                        trigger_type = trigger.get('trigger_type', 'unknown')
                        trigger_effectiveness[trigger_type]['count'] += 1
                        if is_useful:
                            trigger_effectiveness[trigger_type]['useful'] += 1

        # 计算有效率
        effective_triggers = []
        for trigger_type, stats in trigger_effectiveness.items():
            if stats['count'] > 0:
                effectiveness = stats['useful'] / stats['count']
                effective_triggers.append({
                    'trigger_type': trigger_type,
                    'effectiveness': effectiveness,
                    'count': stats['count']
                })

        return sorted(effective_triggers, key=lambda x: x['effectiveness'], reverse=True)

    def _track_actionable_insights(self) -> Dict[str, Any]:
        """跟踪可操作洞察的实施和效果"""
        if not hasattr(self, 'insights'):
            return {'total': 0, 'implemented': 0, 'effective': 0}

        insights = getattr(self, 'insights', [])
        total_actionable = 0
        implemented = 0
        effective = 0

        for insight in insights:
            if isinstance(insight, dict) and insight.get('actionable', False):
                total_actionable += 1
                if insight.get('implemented', False):
                    implemented += 1
                    if insight.get('effective', False):
                        effective += 1

        return {
            'total_actionable': total_actionable,
            'implemented': implemented,
            'effective': effective,
            'implementation_rate': implemented / total_actionable if total_actionable > 0 else 0,
            'effectiveness_rate': effective / implemented if implemented > 0 else 0
        }

    def _calculate_optimal_frequency(self) -> Dict[str, Any]:
        """计算最优反思频率"""
        # 分析反思频率和效果的关系
        if not hasattr(self, 'reflection_cycles') or len(getattr(self, 'reflection_cycles', [])) < 3:
            return {
                'current_frequency': 'unknown',
                'recommended_frequency': 'medium',
                'reason': 'Insufficient data'
            }

        cycles = getattr(self, 'reflection_cycles', [])

        # 计算平均间隔
        intervals = []
        for i in range(1, len(cycles)):
            if isinstance(cycles[i], dict) and isinstance(cycles[i-1], dict):
                current_time = cycles[i].get('start_time', datetime.now())
                prev_time = cycles[i-1].get('start_time', datetime.now())
                interval = (current_time - prev_time).total_seconds() / 3600  # 小时
                intervals.append(interval)

        avg_interval = sum(intervals) / len(intervals) if intervals else 24

        # 评估当前频率
        if avg_interval < 2:
            current_freq = 'very_high'
            recommendation = 'Reduce frequency - may be too frequent'
        elif avg_interval < 6:
            current_freq = 'high'
            recommendation = 'Good frequency for active learning'
        elif avg_interval < 24:
            current_freq = 'medium'
            recommendation = 'Balanced frequency'
        else:
            current_freq = 'low'
            recommendation = 'Consider increasing frequency'

        return {
            'current_frequency': current_freq,
            'avg_interval_hours': avg_interval,
            'recommended_frequency': 'medium',
            'recommendation': recommendation
        }

    def _evaluate_strategies(self) -> Dict[str, float]:
        """评估学习策略的有效性"""
        strategies = {
            'deep_reflection': self._evaluate_deep_reflection_strategy(),
            'pattern_recognition': self._evaluate_pattern_recognition_strategy(),
            'bias_detection': self._evaluate_bias_detection_strategy(),
            'insight_generation': self._evaluate_insight_generation_strategy()
        }

        return strategies

    def _evaluate_deep_reflection_strategy(self) -> float:
        """评估深度反思策略"""
        if not hasattr(self, 'deep_reflections'):
            return 0.5

        deep_reflections = getattr(self, 'deep_reflections', 0)
        insights_generated = getattr(self, 'insights_generated', 0)

        # 深度反思应该产生高质量洞察
        if deep_reflections > 0:
            insight_rate = insights_generated / deep_reflections
            return min(1.0, insight_rate / 5)  # 期望每次深度反思产生5个洞察
        return 0.5

    def _evaluate_pattern_recognition_strategy(self) -> float:
        """评估模式识别策略"""
        patterns_identified = getattr(self, 'patterns_identified', 0)

        # 基于识别的模式数量评估
        if patterns_identified > 20:
            return 0.9
        elif patterns_identified > 10:
            return 0.7
        elif patterns_identified > 5:
            return 0.5
        else:
            return 0.3

    def _evaluate_bias_detection_strategy(self) -> float:
        """评估偏差检测策略"""
        biases_detected = getattr(self, 'biases_detected', 0)

        # 检测到一些偏差是好的，但太多可能意味着系统有问题
        if 5 <= biases_detected <= 15:
            return 0.8
        elif biases_detected < 5:
            return 0.6  # 可能检测不够敏感
        else:
            return 0.4  # 检测到太多可能有问题

    def _evaluate_insight_generation_strategy(self) -> float:
        """评估洞察生成策略"""
        insights_generated = getattr(self, 'insights_generated', 0)

        if insights_generated > 50:
            return 0.9
        elif insights_generated > 20:
            return 0.7
        elif insights_generated > 10:
            return 0.5
        else:
            return 0.3

    async def _update_learning_strategies(self, learnings: Dict):
        """根据元学习结果更新学习策略"""
        # 调整反思频率
        optimal_freq = learnings.get('optimal_frequency', {})
        if optimal_freq.get('current_frequency') == 'very_high':
            # 降低频率
            if hasattr(self, 'config'):
                self.config['frequency']['time_interval'] = \
                    int(self.config['frequency']['time_interval'] * 1.5)

        elif optimal_freq.get('current_frequency') == 'low':
            # 提高频率
            if hasattr(self, 'config'):
                self.config['frequency']['time_interval'] = \
                    int(self.config['frequency']['time_interval'] * 0.75)

        # 调整策略权重
        strategy_effectiveness = learnings.get('strategy_effectiveness', {})
        for strategy, effectiveness in strategy_effectiveness.items():
            if effectiveness < 0.4:
                logger.warning(f"Strategy {strategy} has low effectiveness: {effectiveness:.2f}")

    async def _learn_from_mistakes(self, errors: List[Dict]) -> Dict:
        """从错误中学习"""
        error_patterns = defaultdict(int)

        for error in errors:
            if isinstance(error, dict):
                error_type = error.get('type', 'unknown')
                error_patterns[error_type] += 1

        # 生成学习
        learnings = {
            'error_patterns': dict(error_patterns),
            'most_common_error': max(error_patterns, key=error_patterns.get) if error_patterns else None,
            'total_errors': len(errors),
            'unique_error_types': len(error_patterns)
        }

        return learnings

    async def _adapt_reflection_frequency(self, performance_data: Dict):
        """根据性能数据调整反思频率"""
        # 如果性能下降，增加反思频率
        if performance_data.get('drift_detected', False):
            if hasattr(self, 'config'):
                current_interval = self.config['frequency']['time_interval']
                new_interval = int(current_interval * 0.8)  # 减少20%
                self.config['frequency']['time_interval'] = max(1800, new_interval)  # 至少30分钟
                logger.info(f"Increased reflection frequency due to performance drift: {new_interval}s")

        # 如果性能稳定且良好，可以降低频率
        elif performance_data.get('accuracy', 0) > 0.85 and not performance_data.get('drift_detected'):
            if hasattr(self, 'config'):
                current_interval = self.config['frequency']['time_interval']
                new_interval = int(current_interval * 1.2)  # 增加20%
                self.config['frequency']['time_interval'] = min(14400, new_interval)  # 最多4小时
                logger.info(f"Decreased reflection frequency due to stable performance: {new_interval}s")
