"""
Forgetting Agent Module - Retrieval-Based Forgetting
遗忘智能体模块 - 检索诱导遗忘

检索诱导遗忘（Retrieval-Induced Forgetting, RIF）：
当你检索某个记忆时，相关但未被检索的记忆会变得更难回忆。
这是记忆系统中的一种竞争性抑制机制。

核心机制：
1. 检索练习（Retrieval Practice）：强化被检索的记忆
2. 竞争性抑制（Competitive Inhibition）：抑制相关但未检索的记忆
3. 分类抑制（Category Inhibition）：整个类别的记忆可能受到抑制
"""

from datetime import datetime
from typing import Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)

from .core import ForgettingAgentCore
from ....memory.memory_item import MemoryItem


class RetrievalBasedForgettingMixin:
    """检索诱导遗忘功能"""

    async def _apply_retrieval_induced_forgetting(
        self,
        retrieved_memory_id: str
    ) -> Dict[str, Any]:
        """
        应用检索诱导遗忘（RIF）

        现象：检索某记忆会导致相关但未检索的记忆更难回忆

        工作机制：
        1. 识别被检索的记忆
        2. 查找相关但未被检索的记忆
        3. 对相关记忆应用竞争性抑制
        4. 强化被检索的记忆

        Args:
            retrieved_memory_id: 被检索的记忆ID

        Returns:
            包含RIF应用结果的字典
        """

        if not self.db_manager:
            return {'error': 'Database manager not available'}

        retrieved_memory = self.db_manager.load_memory(retrieved_memory_id)
        if not retrieved_memory:
            return {'error': f'Memory {retrieved_memory_id} not found'}

        # 查找相关但未检索的记忆
        related_memories = self._find_related_unretreived_memories(retrieved_memory)

        # 对相关记忆应用抑制
        suppressed_memories = []
        for related_id in related_memories:
            suppression_result = self._suppress_related_memory(
                related_id,
                strength=0.1  # 轻度抑制
            )
            suppressed_memories.append(suppression_result)

        # 强化被检索的记忆
        self._strengthen_retrieved_memory(retrieved_memory)

        return {
            'retrieval_induced_forgetting_applied': True,
            'retrieved_memory': retrieved_memory_id,
            'suppressed_count': len(suppressed_memories),
            'suppressed_memories': suppressed_memories,
            'retrieval_timestamp': datetime.now().isoformat()
        }

    def _find_related_unretreived_memories(
        self,
        retrieved_memory: MemoryItem
    ) -> List[str]:
        """
        查找相关但未被检索的记忆

        相关性基于：
        - 共享的关联
        - 相似的标签
        - 相同的记忆类型
        - 相似的上下文

        Args:
            retrieved_memory: 被检索的记忆

        Returns:
            相关记忆的ID列表
        """
        if not self.db_manager:
            return []

        all_memories = self.db_manager.search_memories()
        related_memory_ids = []

        for memory in all_memories:
            # 跳过被检索的记忆本身
            if memory.id == retrieved_memory.id:
                continue

            # 计算相关性分数
            relatedness_score = self._calculate_memory_relatedness(
                retrieved_memory,
                memory
            )

            # 如果相关性高于阈值，添加到列表
            if relatedness_score > 0.5:
                related_memory_ids.append(memory.id)

        return related_memory_ids

    def _calculate_memory_relatedness(
        self,
        memory1: MemoryItem,
        memory2: MemoryItem
    ) -> float:
        """
        计算两个记忆之间的相关性

        Args:
            memory1: 第一个记忆
            memory2: 第二个记忆

        Returns:
            相关性分数 (0.0-1.0)
        """
        relatedness = 0.0

        # 共享关联
        if memory1.associations and memory2.associations:
            shared_associations = set(memory1.associations) & set(memory2.associations)
            if shared_associations:
                relatedness += 0.3

        # 相似标签
        if memory1.tags and memory2.tags:
            shared_tags = set(memory1.tags) & set(memory2.tags)
            if shared_tags:
                relatedness += 0.2 * (len(shared_tags) / max(len(memory1.tags), len(memory2.tags)))

        # 相同记忆类型
        if memory1.memory_type == memory2.memory_type:
            relatedness += 0.2

        # 相似上下文
        if memory1.context_tags and memory2.context_tags:
            shared_context = set(memory1.context_tags) & set(memory2.context_tags)
            if shared_context:
                relatedness += 0.2 * (len(shared_context) / max(len(memory1.context_tags), len(memory2.context_tags)))

        # 相似情感内容
        if memory1.emotional_context and memory2.emotional_context:
            if memory1.emotional_context.get('dominant_emotion') == \
               memory2.emotional_context.get('dominant_emotion'):
                relatedness += 0.1

        return min(1.0, relatedness)

    def _suppress_related_memory(
        self,
        memory_id: str,
        strength: float = 0.1
    ) -> Dict[str, Any]:
        """
        抑制相关记忆

        RIF中的抑制是轻度的，不是完全遗忘。

        Args:
            memory_id: 待抑制的记忆ID
            strength: 抑制强度（默认0.1）

        Returns:
            抑制结果
        """
        memory = self.db_manager.load_memory(memory_id)
        if not memory:
            return {'error': f'Memory {memory_id} not found'}

        original_importance = memory.importance

        # 应用轻度抑制
        memory.importance *= (1.0 - strength)

        # 记录RIF抑制
        memory.metadata['rif_suppressed'] = True
        memory.metadata['rif_suppression_count'] = \
            memory.metadata.get('rif_suppression_count', 0) + 1
        memory.metadata['last_rif_suppression'] = datetime.now().isoformat()

        self.db_manager.save_memory(memory)

        return {
            'memory_id': memory_id,
            'original_importance': original_importance,
            'new_importance': memory.importance,
            'suppression_strength': strength
        }

    def _strengthen_retrieved_memory(self, memory: MemoryItem):
        """
        强化被检索的记忆

        检索行为本身会强化记忆（测试效应）

        Args:
            memory: 被检索的记忆
        """
        # 增加重要性（轻微）
        memory.importance = min(1.0, memory.importance * 1.05)

        # 增加巩固水平
        if memory.consolidation_level < 3:
            # 每次检索都可能增加巩固
            retrieval_count = memory.metadata.get('retrieval_count', 0) + 1
            memory.metadata['retrieval_count'] = retrieval_count

            # 多次检索后提升巩固水平
            if retrieval_count % 5 == 0:
                memory.consolidation_level = min(3, memory.consolidation_level + 1)

        # 减少衰减率
        memory.decay_rate = max(0.01, memory.decay_rate * 0.95)

        # 更新访问时间
        memory.last_accessed = datetime.now()
        memory.access_frequency += 1

        # 记录检索强化
        memory.metadata['last_retrieval_strengthening'] = datetime.now().isoformat()

        self.db_manager.save_memory(memory)

    async def _apply_category_based_rif(
        self,
        category: str,
        retrieved_items: List[str]
    ) -> Dict[str, Any]:
        """
        应用基于类别的检索诱导遗忘

        当检索某个类别中的部分项目时，
        同类别中未被检索的项目会受到抑制。

        Args:
            category: 记忆类别
            retrieved_items: 被检索的项目ID列表

        Returns:
            包含类别RIF应用结果的字典
        """

        if not self.db_manager:
            return {'error': 'Database manager not available'}

        # 查找该类别的所有记忆
        all_memories = self.db_manager.search_memories()
        category_memories = [
            m for m in all_memories
            if category in m.tags or m.memory_type == category
        ]

        # 区分已检索和未检索的项目
        retrieved_set = set(retrieved_items)
        unretrieved_memories = [
            m for m in category_memories
            if m.id not in retrieved_set
        ]

        # 对未检索的项目应用抑制
        suppression_results = []
        for memory in unretrieved_memories:
            # 类别内竞争导致的抑制
            original_importance = memory.importance
            memory.importance *= 0.9  # 10%抑制

            memory.metadata['category_rif_applied'] = True
            memory.metadata['category'] = category
            memory.metadata['category_rif_timestamp'] = datetime.now().isoformat()

            self.db_manager.save_memory(memory)

            suppression_results.append({
                'memory_id': memory.id,
                'original_importance': original_importance,
                'new_importance': memory.importance
            })

        # 强化被检索的项目
        for item_id in retrieved_items:
            memory = self.db_manager.load_memory(item_id)
            if memory:
                self._strengthen_retrieved_memory(memory)

        return {
            'category_rif_applied': True,
            'category': category,
            'total_category_items': len(category_memories),
            'retrieved_items': len(retrieved_items),
            'suppressed_items': len(suppression_results),
            'suppression_results': suppression_results
        }

    def _calculate_rif_vulnerability(self, memory: MemoryItem) -> float:
        """
        计算记忆对RIF的脆弱性

        某些记忆更容易受到RIF影响：
        - 低巩固水平
        - 低访问频率
        - 弱关联

        Args:
            memory: 待评估的记忆

        Returns:
            脆弱性分数 (0.0-1.0)，越高越容易受RIF影响
        """
        vulnerability = 0.0

        # 低巩固水平 -> 高脆弱性
        vulnerability += (1.0 - memory.consolidation_level / 3.0) * 0.4

        # 低访问频率 -> 高脆弱性
        if memory.access_frequency == 0:
            vulnerability += 0.3
        else:
            vulnerability += (1.0 / (1.0 + memory.access_frequency)) * 0.3

        # 弱关联 -> 高脆弱性
        if not memory.associations:
            vulnerability += 0.2
        else:
            vulnerability += (1.0 / (1.0 + len(memory.associations))) * 0.2

        # 低重要性 -> 高脆弱性
        vulnerability += (1.0 - memory.importance) * 0.1

        return min(1.0, vulnerability)

    async def _analyze_rif_effects(self) -> Dict[str, Any]:
        """
        分析系统中RIF的整体效应

        Returns:
            包含RIF分析结果的字典
        """
        if not self.db_manager:
            return {'error': 'Database manager not available'}

        all_memories = self.db_manager.search_memories()

        # 统计受RIF影响的记忆
        rif_affected = [
            m for m in all_memories
            if m.metadata.get('rif_suppressed', False)
        ]

        # 统计类别RIF
        category_rif_affected = [
            m for m in all_memories
            if m.metadata.get('category_rif_applied', False)
        ]

        # 计算平均脆弱性
        total_vulnerability = sum(
            self._calculate_rif_vulnerability(m) for m in all_memories
        )
        avg_vulnerability = total_vulnerability / len(all_memories) if all_memories else 0

        return {
            'rif_analysis_complete': True,
            'total_memories': len(all_memories),
            'rif_affected_count': len(rif_affected),
            'category_rif_affected_count': len(category_rif_affected),
            'average_vulnerability': avg_vulnerability,
            'rif_affected_percentage': len(rif_affected) / len(all_memories) * 100 if all_memories else 0
        }
