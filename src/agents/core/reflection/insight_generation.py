"""
Insight Generation Mixin
洞察生成模块
"""

import logging
from typing import Dict, List, Any
from datetime import datetime
from .data_models import Insight

logger = logging.getLogger(__name__)


class InsightGenerationMixin:
    """洞察生成Mixin"""

    async def _generate_insights(self, analysis_results: Dict) -> List[Dict]:
        """
        从分析结果生成洞察

        洞察类型：
        - 模式洞察：识别到的行为模式
        - 偏差洞察：检测到的认知偏差
        - 机会洞察：改进机会
        - 风险洞察：潜在风险
        """
        insights = []

        # 从模式生成洞察
        pattern_insights = await self._synthesize_pattern_insights(
            analysis_results.get('patterns', {})
        )
        insights.extend(pattern_insights)

        # 从性能指标生成洞察
        performance_insights = await self._synthesize_performance_insights(
            analysis_results.get('metrics', {})
        )
        insights.extend(performance_insights)

        # 从偏差检测生成洞察
        if 'biases' in analysis_results:
            bias_insights = self._synthesize_bias_insights(
                analysis_results['biases']
            )
            insights.extend(bias_insights)

        # 优先级排序
        insights = self._prioritize_insights(insights)

        return insights

    async def _synthesize_pattern_insights(self, patterns: Dict) -> List[Dict]:
        """从模式综合洞察"""
        insights = []

        # 错误模式洞察
        if 'recurring_errors' in patterns and patterns['recurring_errors']:
            for error_pattern in patterns['recurring_errors'][:3]:  # Top 3
                insights.append({
                    'type': 'pattern',
                    'subtype': 'error_pattern',
                    'content': f"Recurring error pattern detected: {error_pattern.get('error_type')}",
                    'confidence': 0.8,
                    'actionable': True,
                    'recommendation': f"Implement fix for {error_pattern.get('error_type')}",
                    'priority': 0.9
                })

        # 成功模式洞察
        if 'success_patterns' in patterns and patterns['success_patterns']:
            insights.append({
                'type': 'pattern',
                'subtype': 'success_pattern',
                'content': f"Identified {len(patterns['success_patterns'])} successful approaches",
                'confidence': 0.7,
                'actionable': True,
                'recommendation': "Replicate successful patterns in future tasks",
                'priority': 0.6
            })

        # 时间模式洞察
        temporal = patterns.get('temporal_patterns', {})
        if temporal.get('hourly'):
            peak_hour = max(temporal['hourly'], key=temporal['hourly'].get)
            insights.append({
                'type': 'pattern',
                'subtype': 'temporal',
                'content': f"Peak productivity at {peak_hour}:00",
                'confidence': 0.6,
                'actionable': True,
                'recommendation': f"Schedule important tasks around {peak_hour}:00",
                'priority': 0.5
            })

        return insights

    async def _synthesize_performance_insights(self, metrics: Dict) -> List[Dict]:
        """从性能指标综合洞察"""
        insights = []

        # 准确率洞察
        accuracy = metrics.get('accuracy', 0.7)
        if accuracy < 0.6:
            insights.append({
                'type': 'performance',
                'subtype': 'accuracy',
                'content': f"Low accuracy detected: {accuracy:.2f}",
                'confidence': 0.9,
                'actionable': True,
                'recommendation': "Review and improve decision-making processes",
                'priority': 0.9
            })
        elif accuracy > 0.85:
            insights.append({
                'type': 'performance',
                'subtype': 'accuracy',
                'content': f"High accuracy maintained: {accuracy:.2f}",
                'confidence': 0.8,
                'actionable': False,
                'recommendation': "Continue current approach",
                'priority': 0.3
            })

        # 错误率洞察
        error_rate = metrics.get('error_rate', 0.0)
        if error_rate > 0.15:
            insights.append({
                'type': 'performance',
                'subtype': 'error_rate',
                'content': f"High error rate: {error_rate:.2f}",
                'confidence': 0.9,
                'actionable': True,
                'recommendation': "Investigate root causes of errors",
                'priority': 0.95
            })

        # 性能下降洞察
        if metrics.get('drift_detected'):
            insights.append({
                'type': 'performance',
                'subtype': 'drift',
                'content': "Performance drift detected",
                'confidence': 0.85,
                'actionable': True,
                'recommendation': "Conduct deep analysis to identify causes",
                'priority': 0.9
            })

        return insights

    def _synthesize_bias_insights(self, biases: List[str]) -> List[Dict]:
        """从偏差检测综合洞察"""
        insights = []

        for bias in biases:
            insights.append({
                'type': 'bias',
                'subtype': 'cognitive_bias',
                'content': f"Potential cognitive bias: {bias}",
                'confidence': 0.6,
                'actionable': True,
                'recommendation': f"Implement countermeasures for {bias}",
                'priority': 0.7
            })

        return insights

    def _prioritize_insights(self, insights: List[Dict]) -> List[Dict]:
        """
        对洞察进行优先级排序

        排序因素：
        - 优先级分数
        - 可操作性
        - 置信度
        """
        def insight_score(insight):
            priority = insight.get('priority', 0.5)
            actionable_bonus = 0.2 if insight.get('actionable', False) else 0
            confidence = insight.get('confidence', 0.5)
            return priority * 0.5 + actionable_bonus + confidence * 0.3

        sorted_insights = sorted(insights, key=insight_score, reverse=True)
        return sorted_insights

    async def _formulate_recommendations(self, insights: List[Dict]) -> List[str]:
        """从洞察制定建议"""
        recommendations = []

        for insight in insights:
            if insight.get('actionable', False):
                recommendation = insight.get('recommendation', '')
                if recommendation and recommendation not in recommendations:
                    recommendations.append(recommendation)

        return recommendations[:5]  # Top 5建议

    async def _generate_level_specific_insight(self, memories: List, level: str) -> Dict[str, Any]:
        """
        生成特定层级的洞察

        层级：
        - analytical: 分析性洞察
        - critical: 批判性洞察
        - metacognitive: 元认知洞察
        - transformative: 变革性洞察
        """
        from ....memory.memory_item import MemoryItem

        # 格式化记忆内容
        memory_contents = []
        for mem in memories:
            if isinstance(mem, MemoryItem):
                memory_contents.append(mem.content)
            elif isinstance(mem, dict):
                memory_contents.append(mem.get('content', str(mem)))

        combined_content = "\n".join(memory_contents[:10])  # 限制长度

        prompts = {
            'analytical': f"Analyze relationships and connections in these memories: {combined_content}",
            'critical': f"Critically evaluate and judge these experiences: {combined_content}",
            'metacognitive': f"Think about the thinking processes evident in these memories: {combined_content}",
            'transformative': f"Identify potential paradigm shifts or transformative insights from: {combined_content}"
        }

        prompt = prompts.get(level, f"Reflect on these memories: {combined_content}")

        # 调用LLM生成洞察
        if hasattr(self, 'call_llm'):
            try:
                insight_content = await self.call_llm(prompt)
            except Exception as e:
                logger.error(f"Error calling LLM for insight generation: {e}")
                insight_content = f"Generated {level} insight from {len(memories)} memories"
        else:
            insight_content = f"Generated {level} insight from {len(memories)} memories"

        # 根据层级设置置信度
        confidence_map = {
            'analytical': 0.7,
            'critical': 0.6,
            'metacognitive': 0.5,
            'transformative': 0.4
        }

        return {
            'level': level,
            'content': insight_content,
            'confidence': confidence_map.get(level, 0.5)
        }

    async def _select_best_insight(self, insights: Dict[str, Dict]) -> Dict[str, Any]:
        """从多个层级的洞察中选择最佳的"""
        # 优先级：transformative > metacognitive > critical > analytical
        preference_order = ['transformative', 'metacognitive', 'critical', 'analytical']

        for level in preference_order:
            if level in insights and insights[level].get('content'):
                return insights[level]

        # 回退到任何可用的洞察
        for insight in insights.values():
            if insight.get('content'):
                return insight

        return {'level': 'none', 'content': 'No insights generated', 'confidence': 0.0}

    def _filter_actionable_insights(self, insights: List[Dict]) -> List[Dict]:
        """过滤出可操作的洞察"""
        return [
            insight for insight in insights
            if insight.get('actionable', False)
        ]

    def _group_insights_by_type(self, insights: List[Dict]) -> Dict[str, List[Dict]]:
        """按类型分组洞察"""
        grouped = {}
        for insight in insights:
            insight_type = insight.get('type', 'unknown')
            if insight_type not in grouped:
                grouped[insight_type] = []
            grouped[insight_type].append(insight)

        return grouped
