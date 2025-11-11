"""
Bias Detection Mixin
偏差检测模块
"""

import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class BiasDetectionMixin:
    """偏差检测Mixin"""

    async def _detect_cognitive_biases(self, decisions: List[Dict]) -> List[Dict]:
        """
        检测认知偏差

        检测类型：
        - 确认偏差：只关注支持性证据
        - 可得性偏差：过度依赖易获得的信息
        - 锚定效应：过度依赖初始信息
        - 过度自信：高估自己的判断
        """
        biases = []

        # 检查确认偏差
        confirmation_bias = await self._check_confirmation_bias(decisions)
        if confirmation_bias['detected']:
            biases.append(confirmation_bias)

        # 检查可得性偏差
        availability_bias = self._check_availability_bias(decisions)
        if availability_bias['detected']:
            biases.append(availability_bias)

        # 检查锚定效应
        anchoring_bias = self._check_anchoring_bias(decisions)
        if anchoring_bias['detected']:
            biases.append(anchoring_bias)

        # 检查过度自信
        overconfidence = self._check_overconfidence(decisions)
        if overconfidence['detected']:
            biases.append(overconfidence)

        return biases

    async def _check_confirmation_bias(self, decisions: List[Dict]) -> Dict[str, Any]:
        """
        检查确认偏差

        确认偏差表现：
        - 只考虑支持性证据
        - 忽略矛盾信息
        - 主题多样性低
        """
        if not hasattr(self, 'db_manager') or not self.db_manager:
            return {'detected': False, 'type': 'confirmation_bias'}

        try:
            memories = self.db_manager.load_memories_by_criteria()

            # 分析主题多样性
            if hasattr(self, '_analyze_content_themes'):
                themes = self._analyze_content_themes(memories)
                theme_diversity = len(themes)

                # 如果主题多样性过低，可能存在确认偏差
                if theme_diversity < 3:
                    return {
                        'detected': True,
                        'type': 'confirmation_bias',
                        'severity': 'high',
                        'evidence': f'Low theme diversity: {theme_diversity} themes',
                        'recommendation': 'Actively seek diverse perspectives and contradicting information'
                    }

        except Exception as e:
            logger.error(f"Error checking confirmation bias: {e}")

        return {'detected': False, 'type': 'confirmation_bias'}

    def _check_availability_bias(self, decisions: List[Dict]) -> Dict[str, Any]:
        """
        检查可得性偏差

        可得性偏差表现：
        - 过度依赖频繁访问的记忆
        - 忽略不常访问但重要的信息
        """
        if not hasattr(self, 'db_manager') or not self.db_manager:
            return {'detected': False, 'type': 'availability_bias'}

        try:
            memories = self.db_manager.load_memories_by_criteria()

            if not memories:
                return {'detected': False, 'type': 'availability_bias'}

            # 计算高频访问记忆的比例
            high_access_memories = [
                m for m in memories if m.access_frequency > 5
            ]

            high_access_ratio = len(high_access_memories) / len(memories) if memories else 0

            # 如果超过30%的记忆被高频访问，可能存在可得性偏差
            if high_access_ratio > 0.3:
                return {
                    'detected': True,
                    'type': 'availability_bias',
                    'severity': 'medium',
                    'evidence': f'High-access memory ratio: {high_access_ratio:.2%}',
                    'recommendation': 'Consider less frequently accessed but relevant information'
                }

        except Exception as e:
            logger.error(f"Error checking availability bias: {e}")

        return {'detected': False, 'type': 'availability_bias'}

    def _check_anchoring_bias(self, decisions: List[Dict]) -> Dict[str, Any]:
        """
        检查锚定效应

        锚定效应表现：
        - 过度依赖初始信息
        - 后续判断受首次判断影响过大
        """
        # 分析决策序列中的模式
        if len(decisions) < 3:
            return {'detected': False, 'type': 'anchoring_bias'}

        # 检查是否有过度依赖早期决策的模式
        # 这里简化处理，实际需要更复杂的分析
        first_decisions = decisions[:3]
        later_decisions = decisions[3:]

        if not later_decisions:
            return {'detected': False, 'type': 'anchoring_bias'}

        # 简化的检测逻辑
        # 实际应该分析决策间的相似度和依赖关系
        return {'detected': False, 'type': 'anchoring_bias'}

    def _check_overconfidence(self, decisions: List[Dict]) -> Dict[str, Any]:
        """
        检查过度自信

        过度自信表现：
        - 高估准确率
        - 低估不确定性
        - 预测校准度差
        """
        if not decisions:
            return {'detected': False, 'type': 'overconfidence'}

        # 分析决策的置信度和实际结果
        confidence_scores = []
        actual_outcomes = []

        for decision in decisions:
            if isinstance(decision, dict):
                confidence = decision.get('confidence', 0.5)
                outcome = decision.get('outcome', 'unknown')

                confidence_scores.append(confidence)
                if outcome == 'success':
                    actual_outcomes.append(1.0)
                elif outcome == 'failure':
                    actual_outcomes.append(0.0)

        if not confidence_scores or not actual_outcomes:
            return {'detected': False, 'type': 'overconfidence'}

        # 计算平均置信度和实际成功率
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        avg_success = sum(actual_outcomes) / len(actual_outcomes)

        # 如果置信度显著高于实际成功率，可能存在过度自信
        if avg_confidence - avg_success > 0.2:
            return {
                'detected': True,
                'type': 'overconfidence',
                'severity': 'medium',
                'evidence': f'Confidence ({avg_confidence:.2f}) exceeds actual success ({avg_success:.2f})',
                'recommendation': 'Calibrate confidence estimates with actual outcomes'
            }

        return {'detected': False, 'type': 'overconfidence'}

    async def _identify_cognitive_biases(self, memories: List) -> List[str]:
        """识别潜在的认知偏差"""
        from ....memory.memory_item import MemoryItem

        biases = []
        valid_memories = [m for m in memories if isinstance(m, MemoryItem)]

        if not valid_memories:
            return biases

        # 确认偏差 - 检查主题多样性
        if hasattr(self, '_analyze_content_themes'):
            themes = self._analyze_content_themes(valid_memories)
            if len(themes) < 3:
                biases.append("Possible confirmation bias - limited theme diversity")

        # 近因偏差 - 检查最近记忆的重要性
        recent_memories = [
            m for m in valid_memories
            if (datetime.now() - m.timestamp).days < 7
        ]

        if recent_memories and valid_memories:
            recent_avg_importance = sum(m.importance for m in recent_memories) / len(recent_memories)
            overall_avg_importance = sum(m.importance for m in valid_memories) / len(valid_memories)

            if recent_avg_importance > overall_avg_importance * 1.5:
                biases.append("Possible recency bias - recent memories overvalued")

        # 可得性启发式偏差
        high_access_memories = [m for m in valid_memories if m.access_frequency > 5]
        if len(high_access_memories) / len(valid_memories) > 0.3:
            biases.append("Possible availability heuristic bias")

        return biases

    def _identify_blind_spots(self, analysis_results: Dict) -> List[str]:
        """识别知识盲点"""
        blind_spots = []

        # 检查缺失的主题领域
        if 'content_themes' in analysis_results:
            themes = analysis_results['content_themes']
            common_themes = ['work', 'learning', 'relationships', 'health', 'creativity']

            missing_themes = [theme for theme in common_themes if theme not in themes]

            for theme in missing_themes[:3]:
                blind_spots.append(f"Limited knowledge in: {theme}")

        # 检查记忆类型的不平衡
        if 'memory_types' in analysis_results:
            types = analysis_results['memory_types']
            if types.get('episodic', 0) > types.get('semantic', 0) * 3:
                blind_spots.append("Over-reliance on episodic memories, lacking abstract knowledge")

        return blind_spots

    async def _identify_knowledge_gaps(self, memories: List) -> List[str]:
        """识别知识差距"""
        from ....memory.memory_item import MemoryItem

        gaps = []
        valid_memories = [m for m in memories if isinstance(m, MemoryItem)]

        if not valid_memories:
            return ["Insufficient memory data to identify gaps"]

        # 分析主题覆盖
        if hasattr(self, '_analyze_content_themes'):
            themes = self._analyze_content_themes(valid_memories)
            all_themes = ['work', 'learning', 'relationships', 'health', 'creativity',
                         'technology', 'finance', 'travel']

            missing_themes = [theme for theme in all_themes if theme not in themes]

            for theme in missing_themes[:3]:
                gaps.append(f"Limited knowledge/experience in: {theme}")

        return gaps
