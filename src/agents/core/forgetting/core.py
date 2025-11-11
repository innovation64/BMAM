"""
Forgetting Agent Core
遗忘智能体核心 - 类定义和消息处理
"""

import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
import logging

from ...base import BrainAgent, AgentMessage, BrainRegion
from ....memory.memory_item import MemoryItem

logger = logging.getLogger(__name__)


class ForgettingAgentCore(BrainAgent):
    """
    Forgetting Agent (Prefrontal Inhibition Network)

    核心概念：遗忘
    对应脑区：前额叶抑制网络
    主要功能：主动遗忘，记忆清理，干扰消除
    """
    def __init__(self, db_manager=None):
        super().__init__(
            agent_id="forgetting",
            brain_region=BrainRegion.INHIBITION,
            system_prompt="""You manage memory decay and selective forgetting.
            Remove low-value memories and resolve interference to maintain optimal capacity."""
        )
        
        # External services
        self.db_manager = db_manager
        
        # Forgetting parameters
        self.forgetting_threshold = 0.2  # Memories below this importance are candidates for forgetting
        self.capacity_limit = 10000  # Maximum active memories (soft limit)
        self.interference_threshold = 0.7  # Threshold for detecting memory interference

        # Forgetting strategies - will be initialized lazily via property
        self._forgetting_strategies = None
        
        # Forgetting curves and parameters
        self.ebbinghaus_params = {
            'initial_strength': 1.0,
            'decay_constant': 0.1,
            'time_constant': 24.0  # hours
        }
        
        # Statistics
        self.memories_forgotten = 0
        self.decay_applications = 0
        self.active_suppressions = 0
        self.interferences_resolved = 0
        
        # Suppression history (to avoid over-suppression)
        self.suppression_history = {}

    @property
    def forgetting_strategies(self) -> Dict[str, Any]:
        """Lazily initialize forgetting strategies (after mixins are available)"""
        if self._forgetting_strategies is None:
            self._forgetting_strategies = {
                'passive_decay': self._apply_ebbinghaus_forgetting,
                'active_suppression': self._active_memory_suppression,
                'interference_resolution': self._resolve_memory_interference,
                'capacity_management': self._manage_memory_capacity,
                'contextual_forgetting': self._contextual_forgetting,
                'emotional_suppression': self._emotional_memory_suppression
            }
        return self._forgetting_strategies

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process forgetting and memory management requests"""
        action = message.content.get('action')
        
        if action == 'passive_decay':
            return await self._apply_passive_decay()
        elif action == 'active_forgetting':
            return await self._active_forgetting(message.content['memory_ids'])
        elif action == 'interference_resolution':
            return await self._resolve_interference(message.content['conflicting_memories'])
        elif action == 'capacity_management':
            return await self._manage_memory_capacity()
        elif action == 'selective_forgetting':
            return await self._selective_forgetting(message.content['criteria'])
        elif action == 'forgetting_analysis':
            return await self._analyze_forgetting_patterns()
        elif action == 'memory_pruning':
            return await self._intelligent_memory_pruning()
        elif action == 'trauma_suppression':
            return await self._suppress_traumatic_memories(message.content.get('memory_ids', []))
        
        return {'error': f'Unknown forgetting action: {action}'}
