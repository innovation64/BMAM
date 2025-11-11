"""
Passive Decay Module | 被动衰减模块

Implements passive forgetting through time-based memory decay.
通过基于时间的记忆衰减实现被动遗忘。
"""

from datetime import datetime
from typing import Dict, Any
import logging

from .....memory.memory_item import MemoryItem

logger = logging.getLogger(__name__)


class PassiveDecayMixin:
    """
    Passive Decay Mixin | 被动衰减混入类

    Applies passive decay to memories based on time elapsed.
    基于经过的时间对记忆应用被动衰减。
    """

    async def _apply_passive_decay(self) -> Dict[str, Any]:
        """
        Apply passive forgetting through time-based decay | 应用基于时间的被动遗忘

        Returns: Dictionary with decay results and statistics
        """
        if not self.db_manager:
            return {'error': 'Database manager not available'}

        memories = self.db_manager.search_memories()
        decay_results = self._initialize_decay_results(len(memories))
        retention_scores = []

        for memory in memories:
            self._process_memory_decay(memory, decay_results, retention_scores)

        self._calculate_decay_statistics(decay_results, retention_scores, memories)
        self.decay_applications += 1

        return {
            'passive_decay_complete': True,
            'decay_cycle': self.decay_applications,
            'results': decay_results,
            'ebbinghaus_params': self.ebbinghaus_params
        }

    def _initialize_decay_results(self, total_count: int) -> Dict[str, Any]:
        """Initialize decay results dictionary | 初始化衰减结果字典"""
        return {
            'total_processed': total_count,
            'significant_decay': 0,
            'marked_for_forgetting': 0,
            'memories_deactivated': 0,
            'average_retention': 0.0
        }

    def _process_memory_decay(
        self,
        memory: MemoryItem,
        decay_results: Dict[str, Any],
        retention_scores: list
    ) -> None:
        """Process decay for a single memory | 处理单个记忆的衰减"""
        # Calculate time elapsed
        last_time = memory.last_accessed or memory.timestamp
        time_elapsed_hours = (
            (datetime.now() - last_time).total_seconds() / 3600
        )

        # Apply Ebbinghaus curve and decay factors
        retention = self._calculate_retention_score(memory, time_elapsed_hours)
        retention_scores.append(retention)

        old_importance = memory.importance
        new_importance = old_importance * retention
        decay_factors = self._calculate_decay_factors(memory)
        memory.importance = max(0.01, new_importance * decay_factors['compound_factor'])

        # Track significant decay
        if abs(old_importance - memory.importance) > 0.2:
            decay_results['significant_decay'] += 1

        # Mark for forgetting if needed
        if memory.importance < self.forgetting_threshold:
            self._mark_memory_for_forgetting(memory, decay_results)

        self.db_manager.save_memory(memory)

    def _mark_memory_for_forgetting(
        self,
        memory: MemoryItem,
        decay_results: Dict[str, Any]
    ) -> None:
        """Mark memory for forgetting if below threshold | 如果低于阈值则标记记忆为待遗忘"""
        memory.metadata['marked_for_forgetting'] = True
        memory.metadata['forgetting_reason'] = 'passive_decay'
        memory.metadata['decay_timestamp'] = datetime.now().isoformat()
        decay_results['marked_for_forgetting'] += 1

        # Deactivate if critically low and not protected
        if (memory.importance < 0.05 and
            memory.consolidation_level < 2 and
            not memory.metadata.get('protected', False)):

            memory.metadata['deactivated'] = True
            decay_results['memories_deactivated'] += 1
            self.memories_forgotten += 1

    def _calculate_decay_statistics(
        self,
        decay_results: Dict[str, Any],
        retention_scores: list,
        memories: list
    ) -> None:
        """Calculate decay statistics | 计算衰减统计信息"""
        if retention_scores:
            decay_results['average_retention'] = (
                sum(retention_scores) / len(retention_scores)
            )

        if memories:
            decay_results['forgetting_rate'] = (
                decay_results['marked_for_forgetting'] / len(memories)
            )
