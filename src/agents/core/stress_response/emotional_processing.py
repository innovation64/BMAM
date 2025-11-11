"""
Emotional Processing Mixin
情绪处理功能模块
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from ....memory.memory_item import MemoryItem
from ...base import BrainRegion

logger = logging.getLogger(__name__)


class EmotionalProcessingMixin:
    """情绪处理Mixin"""

    async def _emotional_memory_encoding(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        情绪记忆编码

        为记忆添加情绪标签和重要性权重
        """
        emotions = memory_data.get('emotions', [])
        emotion_intensity = memory_data.get('intensity', 0.5)
        content = memory_data['content']

        # Analyze emotional content
        emotion_analysis = self._analyze_emotional_content(content, emotions, emotion_intensity)

        # Create emotionally enhanced memory
        memory = MemoryItem(
            content=content,
            memory_type='emotional' if emotion_intensity > 0.6 else 'episodic',
            brain_region=BrainRegion.AMYGDALA if emotion_intensity > 0.7 else BrainRegion.HIPPOCAMPUS,
            emotion_tags=emotions,
            emotion_intensity=emotion_intensity,
            importance=self._calculate_emotional_importance(emotion_intensity, emotions),
            stress_marker=self.stress_level > 0.6,
            context_tags=memory_data.get('context_tags', []),
            metadata={
                'emotional_encoding': True,
                'encoding_stress_level': self.stress_level,
                'emotional_state_at_encoding': self.emotional_state.copy(),
                'emotion_analysis': emotion_analysis
            }
        )

        # Apply stress-enhanced consolidation
        if self.stress_level > 0.5 and emotion_intensity > 0.6:
            memory.consolidation_level = 1  # Pre-consolidate emotional memories
            memory.decay_rate = max(0.05, memory.decay_rate * 0.5)  # Slower decay

        # Modulate memory based on emotional valence
        if emotion_analysis['valence'] < -0.5:  # Negative emotions
            memory.importance += 0.2  # Negative events are more salient
            if emotion_analysis['arousal'] > 0.7:  # High arousal negative
                memory.consolidation_level = min(3, memory.consolidation_level + 1)

        # Add to emotional buffer for processing
        emotional_record = {
            'memory_id': memory.id,
            'emotion_tags': emotions,
            'emotion_intensity': emotion_intensity,
            'emotional_state': self.emotional_state.copy(),
            'timestamp': datetime.now().isoformat()
        }

        self.emotional_buffer.append(emotional_record)

        # Save memory
        if self.db_manager:
            self.db_manager.save_memory(memory)

        self.emotional_memories_encoded += 1

        return {
            'emotional_encoding_complete': True,
            'memory_id': memory.id,
            'memory_type': memory.memory_type,
            'emotion_tags': emotions,
            'emotion_intensity': emotion_intensity,
            'importance': memory.importance,
            'stress_enhanced': memory.stress_marker,
            'consolidation_level': memory.consolidation_level,
            'brain_region': memory.brain_region,
            'emotion_analysis': emotion_analysis
        }

    async def _process_emotional_contagion(self, emotional_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process emotional contagion from external emotional signals"""

        source_emotions = emotional_input.get('emotions', [])
        source_intensity = emotional_input.get('intensity', 0.5)
        source_valence = emotional_input.get('valence', 0.0)
        contagion_strength = emotional_input.get('contagion_strength', 0.3)

        # Calculate susceptibility to emotional contagion
        susceptibility = self._calculate_contagion_susceptibility()

        # Apply emotional contagion effect
        contagion_effect = contagion_strength * susceptibility

        old_emotional_state = self.emotional_state.copy()

        # Update emotional state through contagion
        self.emotional_state.valence += (source_valence - self.emotional_state.valence) * contagion_effect
        self.emotional_state.arousal += (source_intensity - self.emotional_state.arousal) * contagion_effect * 0.5

        # Clamp values
        self.emotional_state.valence = max(-1.0, min(1.0, self.emotional_state.valence))
        self.emotional_state.arousal = max(0.0, min(1.0, self.emotional_state.arousal))

        # Update stress level if negative contagion
        if source_valence < -0.5 and contagion_effect > 0.3:
            self.stress_level = min(1.0, self.stress_level + contagion_effect * 0.3)

        return {
            'emotional_contagion_processed': True,
            'source_emotions': source_emotions,
            'contagion_strength': contagion_strength,
            'susceptibility': susceptibility,
            'contagion_effect': contagion_effect,
            'emotional_state_before': old_emotional_state,
            'emotional_state_after': self.emotional_state.copy(),
            'stress_level': self.stress_level
        }

    def _analyze_emotional_content(self, content: str, emotions: List[str], intensity: float) -> Dict[str, Any]:
        """Analyze emotional content of memory"""

        # Categorize emotions
        emotion_categories = {'positive': 0, 'negative': 0, 'neutral': 0}

        for emotion in emotions:
            if emotion in self.emotion_categories['positive']:
                emotion_categories['positive'] += 1
            elif emotion in self.emotion_categories['negative']:
                emotion_categories['negative'] += 1
            else:
                emotion_categories['neutral'] += 1

        # Calculate emotional valence
        total_emotions = sum(emotion_categories.values())
        if total_emotions > 0:
            valence = (emotion_categories['positive'] - emotion_categories['negative']) / total_emotions
        else:
            valence = 0.0

        # Calculate arousal from intensity
        arousal = intensity

        return {
            'valence': valence,
            'arousal': arousal,
            'emotion_categories': emotion_categories,
            'dominant_category': max(emotion_categories, key=emotion_categories.get) if total_emotions > 0 else 'neutral'
        }

    def _calculate_emotional_importance(self, emotion_intensity: float, emotions: List[str]) -> float:
        """Calculate memory importance based on emotional factors"""

        base_importance = 0.5

        # Emotion intensity boosts importance
        intensity_boost = emotion_intensity * 0.3

        # Negative emotions often more salient
        negative_boost = 0.1 if any(e in self.emotion_categories['negative'] for e in emotions) else 0

        # Current stress level affects encoding
        stress_boost = self.stress_level * 0.2

        total_importance = base_importance + intensity_boost + negative_boost + stress_boost

        return min(1.0, total_importance)

    def _calculate_emotional_stability(self) -> float:
        """Calculate emotional stability metric"""
        # Analyze recent emotional buffer for stability
        if len(self.emotional_buffer) < 3:
            return 0.6  # Default stable if insufficient data

        # Calculate variance in emotional intensity over recent buffer
        intensities = [record.get('emotion_intensity', 0.5) for record in list(self.emotional_buffer)[-10:]]
        mean_intensity = sum(intensities) / len(intensities)
        variance = sum((x - mean_intensity) ** 2 for x in intensities) / len(intensities)

        # Lower variance = higher stability
        stability = max(0.0, min(1.0, 1.0 - variance))

        return stability

    def _analyze_mood_trend(self) -> str:
        """Analyze recent mood trend"""
        if len(self.emotional_buffer) < 3:
            return "stable"

        # Get recent emotional states
        recent_records = list(self.emotional_buffer)[-5:]
        valences = [record.get('emotional_state', {}).get('valence', 0.0) for record in recent_records]

        # Calculate trend
        if len(valences) >= 2:
            trend = valences[-1] - valences[0]
            if trend > 0.3:
                return "improving"
            elif trend < -0.3:
                return "declining"

        return "stable"

    def _calculate_contagion_susceptibility(self) -> float:
        """Calculate susceptibility to emotional contagion"""
        base_susceptibility = 0.5

        # High stress increases susceptibility
        stress_modifier = self.stress_level * 0.3

        # Current emotional arousal affects susceptibility
        arousal_modifier = self.emotional_state.arousal * 0.2

        return min(1.0, base_susceptibility + stress_modifier + arousal_modifier)

    def _assess_regulation_capacity(self) -> float:
        """Assess current emotional regulation capacity"""
        return max(0.2, 1.0 - self.stress_level * 0.6)
