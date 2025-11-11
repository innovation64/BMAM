"""
Ebbinghaus Forgetting Curve Module | 艾宾浩斯遗忘曲线模块

Implements the Ebbinghaus forgetting curve for natural memory decay.
实现自然记忆衰减的艾宾浩斯遗忘曲线。

Formula: R(t) = e^(-t/S)
R=retention rate | t=time elapsed | S=strength factor (based on importance)
"""

import math
from datetime import datetime
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class EbbinghausMixin:
    """
    Ebbinghaus Forgetting Curve Mixin | 艾宾浩斯遗忘曲线混入类

    Implements the Ebbinghaus forgetting curve for memory decay.
    实现记忆衰减的艾宾浩斯遗忘曲线。
    """

    async def _apply_ebbinghaus_forgetting(
        self,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Apply Ebbinghaus forgetting curve to decay memories naturally
        应用艾宾浩斯遗忘曲线自然衰减记忆

        Args: time_window_hours - Time window for decay calculation
        Returns: Dictionary with decay results
        """
        if not self.db_manager:
            return {'error': 'Database manager not available'}

        all_memories = self.db_manager.search_memories()

        if not all_memories:
            return {
                'ebbinghaus_forgetting_complete': True,
                'memories_processed': 0,
                'message': 'No memories to process for decay'
            }

        decay_results = []

        for memory in all_memories:
            decay_info = self._calculate_ebbinghaus_decay(memory)
            decay_results.append(decay_info)

        decayed_count = len([r for r in decay_results if r.get('decayed', False)])

        return {
            'ebbinghaus_forgetting_complete': True,
            'memories_processed': len(all_memories),
            'memories_decayed': decayed_count,
            'decay_rate': decayed_count / len(all_memories) if all_memories else 0,
            'time_window_hours': time_window_hours,
            'results': decay_results
        }

    def _calculate_ebbinghaus_decay(self, memory) -> Dict[str, Any]:
        """
        Calculate Ebbinghaus decay for a single memory | 计算单个记忆的艾宾浩斯衰减

        Args: memory - Memory item to calculate decay for
        Returns: Dictionary with decay information
        """
        hours_since_creation = (
            (datetime.now() - memory.timestamp).total_seconds() / 3600
        )

        hours_since_access = 0
        if memory.last_accessed:
            hours_since_access = (
                (datetime.now() - memory.last_accessed).total_seconds() / 3600
            )

        # Calculate strength factor (higher importance = slower decay)
        strength_factor = max(1.0, memory.importance * 10)

        # Calculate retention based on creation and access time
        creation_retention = math.exp(-hours_since_creation / strength_factor)
        access_retention = 1.0

        if memory.last_accessed:
            access_retention = math.exp(-hours_since_access / strength_factor)

        # Take the maximum (last access resets forgetting)
        current_retention = max(creation_retention, access_retention)

        # Apply forgetting if retention is below current importance
        original_importance = memory.importance

        if current_retention < memory.importance:
            return self._apply_decay_to_memory(
                memory,
                original_importance,
                current_retention,
                hours_since_creation,
                hours_since_access
            )

        return {
            'memory_id': memory.id,
            'importance': memory.importance,
            'retention_rate': current_retention,
            'decayed': False
        }

    def _apply_decay_to_memory(
        self,
        memory,
        original_importance: float,
        current_retention: float,
        hours_since_creation: float,
        hours_since_access: float
    ) -> Dict[str, Any]:
        """Apply decay to memory based on retention rate | 基于保持率对记忆应用衰减"""
        new_importance = max(0.0, memory.importance * current_retention)
        memory.importance = new_importance
        memory.decay_rate = min(1.0, memory.decay_rate + 0.1)

        self.db_manager.save_memory(memory)

        return {
            'memory_id': memory.id,
            'original_importance': original_importance,
            'new_importance': new_importance,
            'retention_rate': current_retention,
            'hours_since_creation': hours_since_creation,
            'hours_since_access': hours_since_access,
            'decayed': True
        }
