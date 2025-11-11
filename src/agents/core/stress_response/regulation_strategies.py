"""
Regulation Strategies Mixin
情绪和压力调节策略模块
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class RegulationStrategiesMixin:
    """情绪和压力调节策略Mixin"""

    async def _regulate_emotional_state(self, regulation_strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Apply emotional regulation strategies"""

        strategy_type = regulation_strategy.get('type', 'cognitive_reappraisal')
        target_emotion = regulation_strategy.get('target_emotion')
        intensity = regulation_strategy.get('intensity', 0.5)

        old_emotional_state = self.emotional_state.copy()

        regulation_result = {
            'strategy_applied': strategy_type,
            'target_emotion': target_emotion,
            'success': False,
            'regulation_strength': 0.0
        }

        if strategy_type == 'cognitive_reappraisal':
            # Reframe the emotional interpretation
            regulation_strength = self._apply_cognitive_reappraisal(regulation_strategy)
            regulation_result['regulation_strength'] = regulation_strength
            regulation_result['success'] = regulation_strength > 0.3

        elif strategy_type == 'emotional_suppression':
            # Suppress emotional expression/experience
            regulation_strength = self._apply_emotional_suppression(regulation_strategy)
            regulation_result['regulation_strength'] = regulation_strength
            regulation_result['success'] = regulation_strength > 0.3

        elif strategy_type == 'mindfulness':
            # Mindful awareness without judgment
            regulation_strength = self._apply_mindfulness_regulation(regulation_strategy)
            regulation_result['regulation_strength'] = regulation_strength
            regulation_result['success'] = regulation_strength > 0.3

        elif strategy_type == 'distraction':
            # Redirect attention away from emotional stimulus
            regulation_strength = self._apply_distraction_regulation(regulation_strategy)
            regulation_result['regulation_strength'] = regulation_strength
            regulation_result['success'] = regulation_strength > 0.3

        return {
            'emotional_regulation_complete': True,
            'regulation_result': regulation_result,
            'emotional_state_before': old_emotional_state,
            'emotional_state_after': self.emotional_state.copy(),
            'stress_level': self.stress_level
        }

    async def _trigger_fight_flight_freeze(self, threat_level: float) -> Dict[str, Any]:
        """Trigger fight-flight-freeze response based on threat level"""

        # Determine response type based on threat characteristics
        if threat_level > 0.8:
            response_type = 'freeze'  # Overwhelming threat
        elif threat_level > 0.6:
            # Choose between fight or flight based on context
            response_type = 'flight' if self.emotional_state.dominance < 0.5 else 'fight'
        elif threat_level > 0.4:
            response_type = 'fight'  # Manageable threat
        else:
            response_type = 'alert'  # Low threat

        # Apply physiological changes
        physiological_changes = self._apply_fight_flight_freeze_physiology(response_type, threat_level)

        # Apply cognitive changes
        cognitive_changes = self._apply_fight_flight_freeze_cognition(response_type, threat_level)

        # Apply memory changes
        memory_changes = self._apply_fight_flight_freeze_memory(response_type, threat_level)

        return {
            'fight_flight_freeze_activated': True,
            'response_type': response_type,
            'threat_level': threat_level,
            'physiological_changes': physiological_changes,
            'cognitive_changes': cognitive_changes,
            'memory_changes': memory_changes,
            'duration_estimate': self._estimate_response_duration(response_type, threat_level)
        }

    def _apply_cognitive_reappraisal(self, regulation_strategy: Dict) -> float:
        """Apply cognitive reappraisal regulation"""
        intensity = regulation_strategy.get('intensity', 0.5)

        # Modify emotional valence through reappraisal
        current_valence = self.emotional_state.valence
        if current_valence < 0:
            # Reappraise negative emotions
            reappraisal_effect = intensity * 0.4
            self.emotional_state.valence += reappraisal_effect
            self.emotional_state.valence = min(1.0, self.emotional_state.valence)

        # Reduce arousal
        self.emotional_state.arousal *= (1.0 - intensity * 0.3)

        # Increase sense of control
        self.emotional_state.dominance += intensity * 0.2
        self.emotional_state.dominance = min(1.0, self.emotional_state.dominance)

        return intensity * 0.6  # Return regulation strength

    def _apply_emotional_suppression(self, regulation_strategy: Dict) -> float:
        """Apply emotional suppression regulation"""
        intensity = regulation_strategy.get('intensity', 0.5)

        # Suppress emotional expression (less effective, potential side effects)
        suppression_effect = intensity * 0.3

        # Reduce arousal
        self.emotional_state.arousal *= (1.0 - suppression_effect)

        # Note: Suppression doesn't change valence, may even increase stress
        self.stress_level = min(1.0, self.stress_level + suppression_effect * 0.1)

        return intensity * 0.4  # Lower effectiveness than reappraisal

    def _apply_mindfulness_regulation(self, regulation_strategy: Dict) -> float:
        """Apply mindfulness-based regulation"""
        intensity = regulation_strategy.get('intensity', 0.5)

        # Mindfulness creates acceptance without changing emotions directly
        # Reduces arousal and stress
        mindfulness_effect = intensity * 0.5

        self.emotional_state.arousal *= (1.0 - mindfulness_effect * 0.4)
        self.stress_level *= (1.0 - mindfulness_effect * 0.3)
        self.stress_level = max(0.1, self.stress_level)

        # Increases sense of control through acceptance
        self.emotional_state.dominance += mindfulness_effect * 0.3
        self.emotional_state.dominance = min(1.0, self.emotional_state.dominance)

        return intensity * 0.7  # High effectiveness

    def _apply_distraction_regulation(self, regulation_strategy: Dict) -> float:
        """Apply distraction-based regulation"""
        intensity = regulation_strategy.get('intensity', 0.5)

        # Distraction temporarily reduces emotional intensity
        distraction_effect = intensity * 0.4

        # Reduce arousal
        self.emotional_state.arousal *= (1.0 - distraction_effect)

        # Slight valence improvement
        if self.emotional_state.valence < 0:
            self.emotional_state.valence += distraction_effect * 0.2
            self.emotional_state.valence = min(1.0, self.emotional_state.valence)

        return intensity * 0.5  # Moderate effectiveness

    def _apply_fight_flight_freeze_physiology(self, response_type: str, threat_level: float) -> Dict[str, Any]:
        """Apply physiological changes for fight-flight-freeze"""
        changes = {
            'heart_rate_increase': threat_level * 0.5,
            'breathing_rate_increase': threat_level * 0.4,
            'muscle_tension_increase': threat_level * 0.6,
            'sensory_sharpening': threat_level * 0.7
        }

        if response_type == 'freeze':
            changes['muscle_tension_increase'] = 0.9  # High tension in freeze
            changes['heart_rate_increase'] *= 0.7  # Paradoxical decrease

        return changes

    def _apply_fight_flight_freeze_cognition(self, response_type: str, threat_level: float) -> Dict[str, Any]:
        """Apply cognitive changes for fight-flight-freeze"""
        changes = {
            'attention_narrowing': threat_level * 0.8,
            'decision_speed_increase': threat_level * 0.6,
            'risk_assessment_impairment': threat_level * 0.5,
            'memory_encoding_enhancement': threat_level * 0.4
        }

        if response_type == 'freeze':
            changes['decision_speed_increase'] = 0.1  # Decision paralysis
            changes['attention_narrowing'] = 0.9

        return changes

    def _apply_fight_flight_freeze_memory(self, response_type: str, threat_level: float) -> Dict[str, Any]:
        """Apply memory changes for fight-flight-freeze"""
        changes = {
            'episodic_encoding_enhancement': threat_level * 0.7,
            'working_memory_impairment': threat_level * 0.4,
            'retrieval_bias_toward_threats': threat_level * 0.8,
            'consolidation_priority_boost': threat_level * 0.6
        }

        return changes

    def _estimate_response_duration(self, response_type: str, threat_level: float) -> str:
        """Estimate duration of fight-flight-freeze response"""
        base_durations = {
            'fight': 'minutes to hours',
            'flight': 'seconds to minutes',
            'freeze': 'seconds to minutes',
            'alert': 'minutes'
        }

        if threat_level > 0.8:
            return f"Extended {base_durations.get(response_type, 'unknown')}"
        else:
            return base_durations.get(response_type, 'unknown')
