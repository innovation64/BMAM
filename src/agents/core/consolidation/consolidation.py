"""
Consolidation Agent
记忆巩固智能体 - 主类
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
from collections import deque

from ...base import BrainAgent, AgentMessage, BrainRegion

# 导入所有Mixin
from .rehearsal import RehearsalMixin
from .memory_strengthening import MemoryStrengtheningMixin
from .sleep_consolidation import SleepConsolidationMixin
from .batch_processing import BatchProcessingMixin
from .inference import InferenceMixin
from .data_models import (
    ConsolidationStage,
    ConsolidationJob,
    ConsolidationResult,
    CONSOLIDATION_CONFIG
)

logger = logging.getLogger(__name__)


class ConsolidationAgent(
    BrainAgent,
    RehearsalMixin,
    MemoryStrengtheningMixin,
    SleepConsolidationMixin,
    BatchProcessingMixin,
    InferenceMixin
):
    """
    Consolidation Agent (Hippocampus-Neocortex Circuit)

    核心概念：巩固
    对应脑区：海马体-新皮层回路
    主要功能：短期转长期，记忆重播，系统巩固
    """

    def __init__(self, db_manager=None):
        super().__init__(
            agent_id="consolidation",
            brain_region=BrainRegion.HIPPOCAMPUS,
            system_prompt="""You strengthen memories by transferring them from temporary to permanent storage.
            Prioritize important memories and reinforce connections through replay."""
        )

        # External services
        self.db_manager = db_manager

        # Consolidation parameters
        self.consolidation_threshold = CONSOLIDATION_CONFIG['consolidation']['threshold']
        self.replay_buffer = []
        self.replay_capacity = CONSOLIDATION_CONFIG['consolidation']['replay_capacity']

        # Consolidation strategies
        self.strategies = {
            'immediate': self._immediate_consolidation,
            'delayed': self._delayed_consolidation,
            'sleep': self._sleep_consolidation,
            'replay': self._replay_consolidation
        }

        # Statistics
        self.consolidation_cycles = 0
        self.memories_consolidated = 0
        self.replay_events = 0

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process consolidation requests"""
        action = message.content.get('action')

        if action == 'consolidate_memory':
            return await self._consolidate_single_memory(message.content['memory_id'])
        elif action == 'system_consolidation':
            return await self._system_consolidation()
        elif action == 'memory_replay':
            return await self._memory_replay(message.content.get('memory_ids', []))
        elif action == 'sleep_consolidation':
            return await self._sleep_consolidation()
        elif action == 'evaluate_consolidation':
            return await self._evaluate_consolidation_candidates()
        elif action == 'batch_consolidation':
            return await self._batch_consolidation(message.content.get('batch_size', 10))
        elif action == 'process_chunked_queue':
            return await self._process_chunked_text_queue()
        elif action == 'consolidate_preference':
            return await self._consolidate_preference(message.content)
        elif action == 'consolidate_for_inference':
            return await self._consolidate_for_inference(
                message.content.get('memories', []),
                message.content.get('query', '')
            )
        elif action == 'infer_identity_details':
            return await self._infer_identity_details(
                message.content.get('memories', []),
                message.content.get('query', '')
            )

        return {'error': f'Unknown consolidation action: {action}'}
