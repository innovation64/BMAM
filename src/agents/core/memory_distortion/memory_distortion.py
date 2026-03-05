"""
Memory Distortion Agent
记忆扭曲检测智能体 - 主类
"""

import logging
from typing import Dict, Any

from ...base import BrainAgent, AgentMessage, BrainRegion

from .distortion_detection import DistortionDetectionMixin
from .reconstruction_errors import ReconstructionErrorsMixin
from .source_confusion import SourceConfusionMixin
from .false_memory import FalseMemoryMixin

logger = logging.getLogger(__name__)


class MemoryDistortionAgent(
    BrainAgent,
    DistortionDetectionMixin,
    ReconstructionErrorsMixin,
    SourceConfusionMixin,
    FalseMemoryMixin
):
    """
    Memory Distortion Agent (Medial Temporal Lobe + Prefrontal)

    核心概念：失真
    对应脑区：内侧颞叶 + 前额叶
    主要功能：记忆重构检测，虚假记忆处理，源监控
    """

    def __init__(self, db_manager=None):
        super().__init__(
            agent_id="memory_distortion",
            brain_region=BrainRegion.HIPPOCAMPUS,
            system_prompt="""You detect memory reconstruction errors and verify memory authenticity.
            Flag false memories and monitor source reliability to prevent contamination."""
        )

        # External services
        self.db_manager = db_manager

        # Distortion detection parameters
        self.distortion_threshold = 0.3
        self.false_memory_threshold = 0.7

        # Storage for tracking distortions
        self.false_memory_markers = []
        self.distortion_patterns = {}
        self.source_reliability_cache = {}

        # Distortion types
        self.distortion_types = {
            'temporal': 'Time-related distortions',
            'source': 'Source confusion',
            'detail': 'Detail contamination',
            'emotional': 'Emotional bias',
            'schema': 'Schema-driven distortion',
            'interference': 'Memory interference'
        }

        # Statistics
        self.distortions_detected = 0
        self.false_memories_handled = 0
        self.source_verifications = 0

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process memory distortion detection and management requests"""
        action = message.content.get('action')

        if action == 'detect_distortion':
            return await self._detect_memory_distortion(message.content['memory_id'])
        elif action == 'verify_source':
            return await self._verify_memory_source(message.content['memory_id'])
        elif action == 'handle_false_memory':
            return await self._handle_false_memory(message.content['memory_data'])
        elif action == 'memory_reconstruction':
            return await self._reconstruct_memory(message.content['partial_memory'])
        elif action == 'contamination_check':
            return await self._check_memory_contamination(message.content['memory_ids'])
        elif action == 'source_monitoring':
            return await self._perform_source_monitoring(message.content['memory_id'])
        elif action == 'distortion_analysis':
            return await self._analyze_distortion_patterns()

        return {'error': f'Unknown distortion action: {action}'}
