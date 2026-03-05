"""
Forgetting Agent Module - Context-Dependent Forgetting
遗忘智能体模块 - 上下文依赖遗忘

上下文依赖遗忘（Context-Dependent Forgetting）：
当编码和检索时的上下文不匹配时，记忆检索会受到影响。
这个模块实现基于上下文的选择性遗忘功能。
"""

from datetime import datetime
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

from .core import ForgettingAgentCore
from ....memory.memory_item import MemoryItem


class ContextDependentMixin:
    """上下文依赖遗忘功能"""

    async def _contextual_forgetting(self, context_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于上下文标准忘记记忆

        上下文标准可以包括：
        - time_range: 时间范围
        - emotion_state: 情感状态
        - memory_type: 记忆类型
        - importance_below: 重要性阈值
        - forgetting_strength: 遗忘强度

        Args:
            context_criteria: 包含上下文标准的字典

        Returns:
            包含遗忘结果的字典
        """

        if not self.db_manager:
            return {'error': 'Database manager not available'}

        # 加载记忆并按上下文过滤
        all_memories = self.db_manager.search_memories()
        contextual_candidates = []

        for memory in all_memories:
            should_forget = False

            # 检查各种上下文标准
            if 'time_range' in context_criteria:
                time_range = context_criteria['time_range']
                if time_range['start'] <= memory.timestamp <= time_range['end']:
                    should_forget = True

            if 'emotion_state' in context_criteria:
                target_emotion = context_criteria['emotion_state']
                if memory.emotional_context.get('dominant_emotion') == target_emotion:
                    should_forget = True

            if 'memory_type' in context_criteria:
                if memory.memory_type in context_criteria['memory_type']:
                    should_forget = True

            if 'importance_below' in context_criteria:
                if memory.importance < context_criteria['importance_below']:
                    should_forget = True

            if should_forget:
                contextual_candidates.append(memory)

        # 应用上下文遗忘
        forgetting_results = []

        for memory in contextual_candidates:
            original_importance = memory.importance

            # 基于上下文强度应用遗忘
            context_strength = context_criteria.get('forgetting_strength', 0.5)
            memory.importance *= (1.0 - context_strength)
            memory.decay_rate = min(1.0, memory.decay_rate + context_strength * 0.4)

            # 添加上下文标记
            if 'contextual_forgotten' not in memory.tags:
                memory.tags.append('contextual_forgotten')

            # 保存更新的记忆
            self.db_manager.save_memory(memory)

            forgetting_results.append({
                'memory_id': memory.id,
                'original_importance': original_importance,
                'new_importance': memory.importance,
                'context_strength': context_strength,
                'context_match': True
            })

        return {
            'contextual_forgetting_complete': True,
            'total_memories': len(all_memories),
            'contextual_candidates': len(contextual_candidates),
            'memories_forgotten': len(forgetting_results),
            'context_criteria': context_criteria,
            'results': forgetting_results
        }

    def _check_context_match(self, memory: MemoryItem, context: Dict[str, Any]) -> float:
        """
        检查记忆与当前上下文的匹配程度

        Args:
            memory: 待检查的记忆
            context: 当前上下文

        Returns:
            匹配分数 (0.0-1.0)
        """
        match_score = 0.0
        total_factors = 0

        # 检查情感上下文匹配
        if 'emotional_context' in context and memory.emotional_context:
            total_factors += 1
            current_emotion = context['emotional_context'].get('dominant_emotion')
            memory_emotion = memory.emotional_context.get('dominant_emotion')
            if current_emotion == memory_emotion:
                match_score += 0.3

        # 检查物理/环境上下文匹配
        if 'environment_tags' in context and memory.context_tags:
            total_factors += 1
            env_tags = set(context['environment_tags'])
            mem_tags = set(memory.context_tags)
            overlap = len(env_tags & mem_tags)
            if overlap > 0:
                match_score += 0.3 * (overlap / max(len(env_tags), len(mem_tags)))

        # 检查时间上下文匹配
        if 'time_of_day' in context:
            total_factors += 1
            memory_time = memory.timestamp.hour
            current_time = context['time_of_day']
            # 如果在相似的时间段（±3小时），增加匹配分数
            if abs(memory_time - current_time) <= 3:
                match_score += 0.2

        # 检查认知状态匹配
        if 'cognitive_state' in context and 'cognitive_state' in memory.metadata:
            total_factors += 1
            if context['cognitive_state'] == memory.metadata['cognitive_state']:
                match_score += 0.2

        return match_score

    def _apply_context_dependent_decay(
        self,
        memory: MemoryItem,
        current_context: Dict[str, Any]
    ) -> float:
        """
        应用上下文依赖的衰减

        当上下文不匹配时，记忆更容易被遗忘。

        Args:
            memory: 待衰减的记忆
            current_context: 当前上下文

        Returns:
            衰减因子 (0.0-1.0)，值越小表示衰减越严重
        """
        # 计算上下文匹配度
        context_match = self._check_context_match(memory, current_context)

        # 上下文不匹配时增加衰减
        # 匹配度高（接近1.0）-> 衰减因子接近1.0（几乎不衰减）
        # 匹配度低（接近0.0）-> 衰减因子接近0.6（较强衰减）
        decay_factor = 0.6 + (context_match * 0.4)

        # 应用衰减
        memory.importance *= decay_factor

        # 记录上下文不匹配信息
        if context_match < 0.3:
            memory.metadata['context_mismatch_count'] = \
                memory.metadata.get('context_mismatch_count', 0) + 1

        return decay_factor

    async def _context_based_retrieval_difficulty(
        self,
        memory_ids: List[str],
        current_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        评估在当前上下文下检索记忆的难度

        Args:
            memory_ids: 记忆ID列表
            current_context: 当前上下文

        Returns:
            包含检索难度评估的字典
        """
        if not self.db_manager:
            return {'error': 'Database manager not available'}

        retrieval_analysis = {
            'easy_to_retrieve': [],
            'moderate_difficulty': [],
            'hard_to_retrieve': [],
            'context_match_scores': {}
        }

        for memory_id in memory_ids:
            memory = self.db_manager.load_memory(memory_id)
            if not memory:
                continue

            # 计算上下文匹配度
            match_score = self._check_context_match(memory, current_context)
            retrieval_analysis['context_match_scores'][memory_id] = match_score

            # 分类检索难度
            if match_score > 0.7:
                retrieval_analysis['easy_to_retrieve'].append(memory_id)
            elif match_score > 0.3:
                retrieval_analysis['moderate_difficulty'].append(memory_id)
            else:
                retrieval_analysis['hard_to_retrieve'].append(memory_id)

        return {
            'context_based_retrieval_analysis': True,
            'current_context': current_context,
            'total_memories_analyzed': len(memory_ids),
            'results': retrieval_analysis
        }
