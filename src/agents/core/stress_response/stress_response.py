"""
Stress Response Agent
应激反应智能体 - 主类
"""

import logging
from collections import deque
from typing import Dict, Any

from ...base import BrainAgent, AgentMessage, BrainRegion

# 导入所有Mixin
from .threat_detection import ThreatDetectionMixin
from .emotional_processing import EmotionalProcessingMixin
from .stress_modulation import StressModulationMixin
from .trauma_handler import TraumaHandlerMixin
from .regulation_strategies import RegulationStrategiesMixin
from .data_models import EmotionalState, THREAT_KEYWORDS, EMOTION_CATEGORIES, HPA_DEFAULTS

logger = logging.getLogger(__name__)


class StressResponseAgent(
    BrainAgent,
    ThreatDetectionMixin,
    EmotionalProcessingMixin,
    StressModulationMixin,
    TraumaHandlerMixin,
    RegulationStrategiesMixin
):
    """
    Stress Response Agent (Amygdala + HPA Axis)

    核心概念：应激
    对应脑区：杏仁核（Amygdala）+ HPA轴
    主要功能：威胁检测，情绪记忆编码，应激调节
    """

    def __init__(self, db_manager=None):
        super().__init__(
            agent_id="stress_response",
            brain_region=BrainRegion.AMYGDALA,
            system_prompt="""You detect threats and encode emotional memories with appropriate intensity.
            Modulate stress responses and regulate their impact on memory formation."""
        )

        # External services
        self.db_manager = db_manager

        # Initialize emotional state
        self.emotional_state = EmotionalState()
        self.stress_level = 0.3  # Current stress level (0-1)

        # Threat detection parameters
        self.threat_keywords = THREAT_KEYWORDS.copy()

        # Emotional categories and intensities
        self.emotion_categories = EMOTION_CATEGORIES.copy()

        # Stress response buffers
        self.threat_history = deque(maxlen=20)
        self.emotional_buffer = deque(maxlen=15)
        self.stress_events = deque(maxlen=10)

        # HPA axis simulation parameters
        self.cortisol_level = HPA_DEFAULTS['cortisol_level']
        self.adrenaline_level = HPA_DEFAULTS['adrenaline_level']
        self.recovery_rate = HPA_DEFAULTS['recovery_rate']

        # Statistics
        self.threats_detected = 0
        self.emotional_memories_encoded = 0
        self.stress_responses_triggered = 0
        self.trauma_memories_processed = 0

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process stress response and emotional processing requests"""
        action = message.content.get('action')

        if action == 'threat_detection':
            return await self._detect_threat(message.content['stimulus'])
        elif action == 'emotional_encoding':
            return await self._emotional_memory_encoding(message.content['memory_data'])
        elif action == 'stress_modulation':
            return await self._modulate_stress_response(message.content.get('stressor'))
        elif action == 'trauma_processing':
            return await self._process_traumatic_memory(message.content['trauma_data'])
        elif action == 'emotional_regulation':
            return await self._regulate_emotional_state(message.content['regulation_strategy'])
        elif action == 'stress_assessment':
            return await self._assess_current_stress_state()
        elif action == 'fight_flight_freeze':
            return await self._trigger_fight_flight_freeze(message.content['threat_level'])
        elif action == 'emotional_contagion':
            return await self._process_emotional_contagion(message.content['emotional_input'])

        return {'error': f'Unknown stress response action: {action}'}
