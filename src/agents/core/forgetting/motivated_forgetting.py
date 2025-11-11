"""
Forgetting Agent Module - Motivated Forgetting
遗忘智能体模块 - 动机性遗忘

动机性遗忘（Motivated Forgetting）：
指有意识或无意识地抑制不愉快或创伤性记忆的过程。
包括：
1. 情感记忆抑制（Emotional Memory Suppression）
2. 创伤记忆容纳（Trauma Memory Containment）
3. 有意识遗忘（Directed Forgetting）
"""

from datetime import datetime
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

from .core import ForgettingAgentCore
from ....memory.memory_item import MemoryItem


class MotivatedForgettingMixin:
    """动机性遗忘功能"""

    async def _emotional_memory_suppression(self, emotion_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于情感标准抑制记忆

        抑制高强度的负面情感记忆，以保护心理健康。

        Args:
            emotion_criteria: 情感标准字典，包括：
                - target_emotions: 目标情感列表（默认：['anxiety', 'sadness', 'anger']）
                - intensity_threshold: 强度阈值（默认：0.7）
                - suppression_strength: 抑制强度（默认：0.6）

        Returns:
            包含抑制结果的字典
        """

        if not self.db_manager:
            return {'error': 'Database manager not available'}

        # 默认抑制负面高强度情感
        target_emotions = emotion_criteria.get('target_emotions', ['anxiety', 'sadness', 'anger'])
        intensity_threshold = emotion_criteria.get('intensity_threshold', 0.7)
        suppression_strength = emotion_criteria.get('suppression_strength', 0.6)

        # 加载记忆并找到情感候选
        all_memories = self.db_manager.search_memories()
        emotional_candidates = []

        for memory in all_memories:
            if memory.emotion_intensity >= intensity_threshold:
                dominant_emotion = memory.emotional_context.get('dominant_emotion', 'neutral')
                if dominant_emotion in target_emotions:
                    emotional_candidates.append(memory)

        if not emotional_candidates:
            return {
                'emotional_suppression_complete': True,
                'memories_processed': len(all_memories),
                'message': 'No memories meet emotional suppression criteria'
            }

        suppression_results = []

        for memory in emotional_candidates:
            # 检查是否受保护
            if self._is_memory_protected(memory):
                continue

            original_importance = memory.importance

            # 应用情感抑制
            memory.importance *= (1.0 - suppression_strength)
            memory.decay_rate = min(1.0, memory.decay_rate + suppression_strength * 0.3)

            # 添加抑制标记
            memory.metadata['emotionally_suppressed'] = True
            memory.metadata['suppression_timestamp'] = datetime.now().isoformat()
            memory.metadata['suppressed_emotion'] = memory.emotional_context.get('dominant_emotion')

            # 保存更新的记忆
            self.db_manager.save_memory(memory)

            suppression_results.append({
                'memory_id': memory.id,
                'emotion': memory.emotional_context.get('dominant_emotion'),
                'intensity': memory.emotion_intensity,
                'original_importance': original_importance,
                'new_importance': memory.importance,
                'suppression_applied': True
            })

        return {
            'emotional_suppression_complete': True,
            'total_memories': len(all_memories),
            'emotional_candidates': len(emotional_candidates),
            'memories_suppressed': len(suppression_results),
            'target_emotions': target_emotions,
            'intensity_threshold': intensity_threshold,
            'suppression_strength': suppression_strength,
            'results': suppression_results
        }

    async def _suppress_traumatic_memories(self, memory_ids: List[str]) -> Dict[str, Any]:
        """
        对创伤记忆应用特殊抑制技术

        创伤记忆需要特殊处理 - 容纳而非完全抑制。
        容纳（containment）减少记忆的可访问性，但保持记忆的完整性，
        这对于创伤后成长和心理治疗很重要。

        Args:
            memory_ids: 待处理的记忆ID列表

        Returns:
            包含抑制结果的字典
        """

        if not self.db_manager:
            return {'error': 'Database manager not available'}

        suppression_results = {
            'attempted': len(memory_ids),
            'suppressed': [],
            'containment_applied': []
        }

        for memory_id in memory_ids:
            memory = self.db_manager.load_memory(memory_id)
            if not memory:
                continue

            # 对创伤记忆应用特定抑制
            if memory.stress_marker or 'trauma' in memory.emotion_tags:
                # 容纳而非完全抑制
                containment_result = self._apply_trauma_containment(memory)

                suppression_results['containment_applied'].append({
                    'memory_id': memory_id,
                    'containment_level': containment_result['level'],
                    'accessibility_reduced': containment_result['accessibility_reduction']
                })

                self.db_manager.save_memory(memory)

            else:
                # 对非创伤记忆的常规抑制
                suppression_success = self._apply_active_suppression(memory)
                if suppression_success:
                    suppression_results['suppressed'].append(memory_id)

        return {
            'trauma_suppression_complete': True,
            'results': suppression_results
        }

    def _apply_trauma_containment(self, memory: MemoryItem) -> Dict[str, Any]:
        """
        对创伤记忆应用专门的容纳技术

        创伤记忆需要特殊处理 - 容纳而非抑制。
        这保持了记忆的完整性，同时减少了它的侵入性。

        容纳策略：
        - 高强度（>0.9）：高级容纳，可访问性降低70%
        - 中强度（0.7-0.9）：中级容纳，可访问性降低50%
        - 低强度（<0.7）：低级容纳，可访问性降低30%

        Args:
            memory: 创伤记忆项

        Returns:
            包含容纳级别和可访问性降低程度的字典
        """

        # 创伤记忆需要特殊处理 - 容纳而非抑制
        containment_level = 'moderate'
        accessibility_reduction = 0.4

        if memory.emotion_intensity > 0.9:
            containment_level = 'high'
            accessibility_reduction = 0.7
        elif memory.emotion_intensity > 0.7:
            containment_level = 'moderate'
            accessibility_reduction = 0.5
        else:
            containment_level = 'low'
            accessibility_reduction = 0.3

        # 应用容纳
        memory.metadata['trauma_contained'] = True
        memory.metadata['containment_level'] = containment_level
        memory.metadata['containment_timestamp'] = datetime.now().isoformat()

        # 降低可访问性但保持记忆完整性
        memory.importance *= (1.0 - accessibility_reduction)

        # 不要增加创伤记忆的衰减率 - 它们需要被保留
        # 但可访问性降低

        return {
            'level': containment_level,
            'accessibility_reduction': accessibility_reduction
        }

    async def _active_forgetting(self, memory_ids: List[str]) -> Dict[str, Any]:
        """
        主动抑制特定记忆（有意识遗忘）

        这是一种有意识的、有目的的遗忘过程，用于：
        - 移除不再相关的信息
        - 减少记忆干扰
        - 管理认知负荷

        Args:
            memory_ids: 待抑制的记忆ID列表

        Returns:
            包含抑制结果的字典
        """

        if not self.db_manager:
            return {'error': 'Database manager not available'}

        suppression_results = {
            'attempted': len(memory_ids),
            'suppressed': [],
            'failed': [],
            'protected': []
        }

        for memory_id in memory_ids:
            memory = self.db_manager.load_memory(memory_id)
            if not memory:
                suppression_results['failed'].append({
                    'memory_id': memory_id,
                    'reason': 'Memory not found'
                })
                continue

            # 检查记忆是否受保护
            if self._is_memory_protected(memory):
                suppression_results['protected'].append({
                    'memory_id': memory_id,
                    'reason': self._get_protection_reason(memory)
                })
                continue

            # 应用主动抑制
            suppression_success = self._apply_active_suppression(memory)

            if suppression_success:
                # 记录抑制
                self.suppression_history[memory_id] = {
                    'timestamp': datetime.now().isoformat(),
                    'original_importance': memory.importance,
                    'suppression_strength': suppression_success['strength']
                }

                suppression_results['suppressed'].append({
                    'memory_id': memory_id,
                    'suppression_strength': suppression_success['strength'],
                    'new_importance': memory.importance,
                    'method': suppression_success['method']
                })

                self.active_suppressions += 1
            else:
                suppression_results['failed'].append({
                    'memory_id': memory_id,
                    'reason': 'Suppression failed'
                })

        return {
            'active_forgetting_complete': True,
            'results': suppression_results,
            'total_suppressions': self.active_suppressions
        }

    def _apply_active_suppression(self, memory: MemoryItem) -> Dict[str, Any]:
        """
        对记忆应用主动抑制

        抑制强度基于记忆属性：
        - 高巩固记忆更难抑制
        - 高重要性记忆更难抑制
        - 高访问频率记忆更难抑制

        Args:
            memory: 待抑制的记忆

        Returns:
            包含抑制强度和方法的字典，失败时返回None
        """

        # 基于记忆属性计算抑制强度
        base_suppression = 0.7

        # 高巩固记忆更难抑制
        if memory.consolidation_level >= 2:
            base_suppression *= 0.7

        # 高重要性记忆更难抑制
        if memory.importance > 0.7:
            base_suppression *= 0.8

        # 频繁访问的记忆更难抑制
        if memory.access_frequency > 5:
            base_suppression *= 0.9

        # 应用抑制
        memory.importance *= (1.0 - base_suppression)
        memory.decay_rate = min(1.0, memory.decay_rate + base_suppression * 0.5)

        # 添加抑制标记
        memory.metadata['actively_suppressed'] = True
        memory.metadata['suppression_timestamp'] = datetime.now().isoformat()
        memory.metadata['suppression_strength'] = base_suppression

        # 保存记忆
        self.db_manager.save_memory(memory)

        return {
            'strength': base_suppression,
            'method': 'active_suppression',
            'success': True
        }

    async def _selective_forgetting(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于特定标准执行选择性遗忘

        选择性遗忘允许基于多种标准有针对性地遗忘记忆：
        - 重要性阈值
        - 记忆类型
        - 情感内容
        - 时间范围
        - 访问频率

        Args:
            criteria: 包含选择标准的字典

        Returns:
            包含遗忘结果的字典
        """

        if not self.db_manager:
            return {'error': 'Database manager not available'}

        # 加载记忆
        memories = self.db_manager.search_memories()

        # 基于标准过滤
        candidates = self._filter_memories_by_criteria(memories, criteria)

        # 应用选择性遗忘
        forgetting_results = {
            'candidates_identified': len(candidates),
            'forgotten_memories': [],
            'preserved_memories': [],
            'criteria_used': criteria
        }

        for memory in candidates:
            # 评估记忆是否应该被遗忘
            forget_score = self._calculate_forgetting_score(memory, criteria)

            if forget_score > 0.6:  # 高遗忘分数
                # 应用遗忘
                self._apply_selective_forgetting_to_memory(memory, criteria)
                forgetting_results['forgotten_memories'].append({
                    'memory_id': memory.id,
                    'forget_score': forget_score,
                    'reason': self._get_forgetting_reason(criteria)
                })

                self.db_manager.save_memory(memory)

            else:
                forgetting_results['preserved_memories'].append(memory.id)

        return {
            'selective_forgetting_complete': True,
            'results': forgetting_results
        }

    def _filter_memories_by_criteria(
        self,
        memories: List[MemoryItem],
        criteria: Dict[str, Any]
    ) -> List[MemoryItem]:
        """基于标准过滤记忆"""
        filtered = []

        for memory in memories:
            matches = True

            if 'importance_below' in criteria:
                if memory.importance >= criteria['importance_below']:
                    matches = False

            if 'memory_types' in criteria:
                if memory.memory_type not in criteria['memory_types']:
                    matches = False

            if 'emotion_tags' in criteria:
                if not any(tag in memory.emotion_tags for tag in criteria['emotion_tags']):
                    matches = False

            if 'access_frequency_below' in criteria:
                if memory.access_frequency >= criteria['access_frequency_below']:
                    matches = False

            if matches:
                filtered.append(memory)

        return filtered

    def _calculate_forgetting_score(
        self,
        memory: MemoryItem,
        criteria: Dict[str, Any]
    ) -> float:
        """计算遗忘分数（越高越可能被遗忘）"""
        score = 0.0

        # 低重要性增加分数
        score += (1.0 - memory.importance) * 0.4

        # 低访问频率增加分数
        if memory.access_frequency == 0:
            score += 0.3
        else:
            score += (1.0 / (1.0 + memory.access_frequency)) * 0.3

        # 低巩固水平增加分数
        score += (1.0 - memory.consolidation_level / 3.0) * 0.2

        # 特定标准调整
        if 'urgency' in criteria:
            score *= criteria['urgency']

        return min(1.0, score)

    def _apply_selective_forgetting_to_memory(
        self,
        memory: MemoryItem,
        criteria: Dict[str, Any]
    ):
        """对记忆应用选择性遗忘"""
        strength = criteria.get('strength', 0.7)

        memory.importance *= (1.0 - strength)
        memory.decay_rate = min(1.0, memory.decay_rate + strength * 0.5)
        memory.metadata['selectively_forgotten'] = True
        memory.metadata['forgetting_criteria'] = str(criteria)

    def _get_forgetting_reason(self, criteria: Dict[str, Any]) -> str:
        """获取遗忘原因"""
        if 'reason' in criteria:
            return criteria['reason']
        return 'Selective forgetting based on specified criteria'
