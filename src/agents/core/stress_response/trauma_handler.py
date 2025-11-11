"""
Trauma Handler Mixin
创伤处理功能模块
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from ....memory.memory_item import MemoryItem
from ...base import BrainRegion

logger = logging.getLogger(__name__)


class TraumaHandlerMixin:
    """创伤处理Mixin"""

    async def _process_traumatic_memory(self, trauma_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Special processing for traumatic memories with protective mechanisms

        使用保护性措施处理创伤记忆
        """
        # Create trauma memory with special properties
        trauma_memory = MemoryItem(
            content=trauma_data['content'],
            memory_type='traumatic',
            brain_region=BrainRegion.AMYGDALA,
            emotion_tags=['trauma', 'fear'] + trauma_data.get('additional_emotions', []),
            emotion_intensity=1.0,  # Maximum intensity
            importance=1.0,  # Maximum importance
            stress_marker=True,
            consolidation_level=2,  # Strong immediate consolidation
            decay_rate=0.01,  # Very slow decay - trauma memories persist
            context_tags=trauma_data.get('context_tags', []) + ['trauma'],
            metadata={
                'trauma_memory': True,
                'trauma_type': trauma_data.get('type', 'unknown'),
                'processing_status': 'acute',
                'requires_therapeutic_processing': True,
                'protective_mechanisms_active': True,
                'encoding_stress_level': self.stress_level,
                'trauma_timestamp': datetime.now().isoformat()
            }
        )

        # Apply protective processing mechanisms
        protective_measures = self._apply_trauma_protective_measures(trauma_memory, trauma_data)

        # Update stress response to trauma level
        self.stress_level = min(1.0, self.stress_level + 0.7)  # Significant stress increase
        self.cortisol_level = min(1.0, self.cortisol_level + 0.5)
        self.adrenaline_level = min(1.0, self.adrenaline_level + 0.6)

        # Update emotional state
        self.emotional_state.update({
            'valence': -0.8,  # Highly negative
            'arousal': 0.9,   # High arousal
            'dominance': 0.2  # Low sense of control
        })

        # Save traumatic memory
        if self.db_manager:
            self.db_manager.save_memory(trauma_memory)

        self.trauma_memories_processed += 1

        return {
            'trauma_processing_complete': True,
            'memory_id': trauma_memory.id,
            'trauma_type': trauma_data.get('type', 'unknown'),
            'protective_measures': protective_measures,
            'stress_impact': 'severe',
            'stress_level': self.stress_level,
            'emotional_impact': self.emotional_state.copy(),
            'processing_status': 'acute',
            'recommendations': self._get_trauma_processing_recommendations(trauma_data)
        }

    def _apply_trauma_protective_measures(self, trauma_memory: MemoryItem, trauma_data: Dict[str, Any]) -> List[str]:
        """Apply protective measures for trauma memory processing"""

        protective_measures = []

        # Memory fragmentation (natural protective mechanism)
        trauma_memory.metadata['fragmented_encoding'] = True
        protective_measures.append('memory_fragmentation')

        # Emotional numbing
        if trauma_memory.emotion_intensity > 0.9:
            trauma_memory.metadata['emotional_numbing_active'] = True
            protective_measures.append('emotional_numbing')

        # Dissociation markers
        trauma_memory.metadata['dissociation_markers'] = True
        protective_measures.append('dissociation_protection')

        # Avoid overgeneralization
        trauma_memory.context_tags.append('specific_context_isolated')
        protective_measures.append('context_isolation')

        # Time distortion markers
        trauma_memory.metadata['temporal_processing_altered'] = True
        protective_measures.append('temporal_distortion')

        return protective_measures

    def _get_trauma_processing_recommendations(self, trauma_data: Dict[str, Any]) -> List[str]:
        """Get recommendations for trauma memory processing"""

        recommendations = [
            'Trauma memory encoded with protective mechanisms',
            'Professional therapeutic support recommended',
            'Memory processing should be gradual and controlled',
            'Avoid retraumatization through excessive recall',
            'Focus on building emotional regulation skills'
        ]

        trauma_type = trauma_data.get('type', 'unknown')

        if trauma_type == 'acute':
            recommendations.append('Time-limited intervention may be effective')
        elif trauma_type == 'complex':
            recommendations.append('Long-term therapeutic relationship needed')
        elif trauma_type == 'developmental':
            recommendations.append('Address developmental impact on self-concept')

        return recommendations
