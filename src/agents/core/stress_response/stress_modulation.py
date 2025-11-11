"""
Stress Modulation Mixin
压力调节功能模块
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class StressModulationMixin:
    """压力调节Mixin"""

    async def _modulate_stress_response(self, stressor: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Modulate stress response and its effects on memory and cognition"""

        old_stress = self.stress_level
        old_cortisol = self.cortisol_level
        old_adrenaline = self.adrenaline_level

        if stressor:
            # Process new stressor
            stressor_response = self._process_stressor(stressor)

            # Update stress hormones
            self._update_stress_hormones(stressor_response)

            # Record stress event
            stress_event = {
                'timestamp': datetime.now().isoformat(),
                'stressor': stressor,
                'stressor_response': stressor_response,
                'stress_level_before': old_stress,
                'stress_level_after': self.stress_level
            }

            self.stress_events.append(stress_event)
            self.stress_responses_triggered += 1

        else:
            # Natural stress recovery
            self._apply_stress_recovery()

        # Determine stress effects on cognitive systems
        cognitive_effects = self._calculate_stress_effects_on_cognition()

        # Determine memory effects
        memory_effects = self._calculate_stress_effects_on_memory()

        return {
            'stress_modulation_complete': True,
            'stressor_processed': stressor is not None,
            'stress_level_before': old_stress,
            'stress_level_after': self.stress_level,
            'cortisol_before': old_cortisol,
            'cortisol_after': self.cortisol_level,
            'adrenaline_before': old_adrenaline,
            'adrenaline_after': self.adrenaline_level,
            'stress_category': self._get_stress_category(),
            'cognitive_effects': cognitive_effects,
            'memory_effects': memory_effects,
            'recommendations': self._get_stress_management_recommendations()
        }

    async def _assess_current_stress_state(self) -> Dict[str, Any]:
        """Comprehensive assessment of current stress and emotional state"""

        # Physiological markers (simulated)
        physiological_state = {
            'stress_level': self.stress_level,
            'cortisol_level': self.cortisol_level,
            'adrenaline_level': self.adrenaline_level,
            'heart_rate_variability': 1.0 - self.stress_level,  # Inverse relationship
            'autonomic_balance': 0.5 - (self.stress_level - 0.5)  # Sympathetic vs parasympathetic
        }

        # Emotional state analysis
        emotional_analysis = {
            'current_state': self.emotional_state.copy(),
            'emotional_stability': self._calculate_emotional_stability(),
            'mood_trend': self._analyze_mood_trend(),
            'emotional_regulation_capacity': self._assess_regulation_capacity()
        }

        # Cognitive impact assessment
        cognitive_impact = {
            'attention_focus': max(0.1, 1.0 - self.stress_level * 0.6),
            'working_memory_capacity': max(0.3, 1.0 - self.stress_level * 0.4),
            'decision_making_quality': max(0.2, 1.0 - self.stress_level * 0.5),
            'creative_thinking': max(0.1, 0.8 - self.stress_level * 0.7)
        }

        # Risk assessment
        risk_factors = self._assess_stress_risk_factors()

        # Overall wellness score
        wellness_score = self._calculate_overall_wellness_score(
            physiological_state,
            emotional_analysis,
            cognitive_impact
        )

        return {
            'stress_assessment_complete': True,
            'timestamp': datetime.now().isoformat(),
            'physiological_state': physiological_state,
            'emotional_analysis': emotional_analysis,
            'cognitive_impact': cognitive_impact,
            'risk_factors': risk_factors,
            'wellness_score': wellness_score,
            'recommendations': self._generate_wellness_recommendations(wellness_score, risk_factors)
        }

    def _process_stressor(self, stressor: Dict[str, Any]) -> Dict[str, Any]:
        """Process a stressor and determine stress response"""

        stressor_type = stressor.get('type', 'general')
        stressor_intensity = stressor.get('intensity', 0.5)
        stressor_duration = stressor.get('duration', 'short')  # short, medium, long, chronic

        # Calculate stress impact
        impact_multipliers = {
            'acute': 1.5,
            'chronic': 0.8,  # Chronic stress has different pattern
            'intermittent': 1.0,
            'general': 1.0
        }

        duration_multipliers = {
            'short': 1.0,
            'medium': 1.2,
            'long': 1.4,
            'chronic': 2.0
        }

        stress_impact = (stressor_intensity *
                        impact_multipliers.get(stressor_type, 1.0) *
                        duration_multipliers.get(stressor_duration, 1.0))

        # Update stress level
        self.stress_level = min(1.0, self.stress_level + stress_impact * 0.4)

        return {
            'stressor_type': stressor_type,
            'stressor_intensity': stressor_intensity,
            'stressor_duration': stressor_duration,
            'stress_impact': stress_impact,
            'response_magnitude': stress_impact
        }

    def _update_stress_hormones(self, stressor_response: Dict[str, Any]):
        """Update simulated stress hormones"""
        impact = stressor_response['stress_impact']

        # Update cortisol (slower, longer lasting)
        self.cortisol_level = min(1.0, self.cortisol_level + impact * 0.3)

        # Update adrenaline (faster, shorter lasting)
        self.adrenaline_level = min(1.0, self.adrenaline_level + impact * 0.5)

    def _apply_stress_recovery(self):
        """Apply natural stress recovery"""
        # Exponential decay
        self.stress_level = max(0.1, self.stress_level * (1.0 - self.recovery_rate))
        self.cortisol_level = max(0.1, self.cortisol_level * 0.95)  # Slower recovery
        self.adrenaline_level = max(0.1, self.adrenaline_level * 0.9)  # Faster recovery

        # Emotional state recovery
        self.emotional_state.valence += (0.0 - self.emotional_state.valence) * 0.05
        self.emotional_state.arousal *= 0.98
        self.emotional_state.dominance += (0.5 - self.emotional_state.dominance) * 0.03

    def _calculate_stress_effects_on_cognition(self) -> Dict[str, float]:
        """Calculate how current stress affects cognitive functions"""

        # Inverted U-curve: moderate stress can enhance performance
        optimal_stress = 0.4

        if self.stress_level < optimal_stress:
            # Below optimal - some enhancement
            attention_effect = 1.0 + (self.stress_level / optimal_stress) * 0.2
            working_memory_effect = 1.0 + (self.stress_level / optimal_stress) * 0.1
        else:
            # Above optimal - impairment
            excess_stress = self.stress_level - optimal_stress
            attention_effect = 1.0 - excess_stress * 0.5
            working_memory_effect = 1.0 - excess_stress * 0.6

        decision_making_effect = max(0.3, 1.0 - (self.stress_level - 0.3) * 0.7)
        creative_thinking_effect = max(0.2, 1.0 - self.stress_level * 0.8)

        return {
            'attention_modifier': max(0.1, attention_effect),
            'working_memory_modifier': max(0.2, working_memory_effect),
            'decision_making_modifier': decision_making_effect,
            'creative_thinking_modifier': creative_thinking_effect
        }

    def _calculate_stress_effects_on_memory(self) -> Dict[str, float]:
        """Calculate how current stress affects memory systems"""

        return {
            'encoding_modifier': 1.0 + min(0.3, self.stress_level * 0.5),  # Stress can enhance encoding
            'consolidation_modifier': 1.0 + min(0.2, self.stress_level * 0.3),
            'retrieval_modifier': max(0.4, 1.0 - (self.stress_level - 0.5) * 0.8),  # High stress impairs retrieval
            'forgetting_modifier': max(0.5, 1.0 - self.stress_level * 0.3)  # Stress reduces forgetting
        }

    def _get_stress_category(self) -> str:
        """Get current stress category"""
        if self.stress_level < 0.3:
            return 'low'
        elif self.stress_level < 0.6:
            return 'moderate'
        elif self.stress_level < 0.8:
            return 'high'
        else:
            return 'extreme'

    def _get_stress_management_recommendations(self) -> List[str]:
        """Get stress management recommendations"""
        category = self._get_stress_category()

        recommendations = {
            'low': ['Maintain current stress management practices', 'Consider light challenges for growth'],
            'moderate': ['Good stress level for performance', 'Monitor for increases', 'Practice relaxation techniques'],
            'high': ['Implement stress reduction strategies', 'Consider workload adjustment', 'Practice deep breathing'],
            'extreme': ['Immediate stress intervention needed', 'Seek support', 'Remove stressors if possible']
        }

        return recommendations.get(category, ['Monitor stress levels'])

    def _assess_stress_risk_factors(self) -> List[str]:
        """Assess current stress risk factors"""
        risk_factors = []

        if self.stress_level > 0.7:
            risk_factors.append('high_stress_level')

        if self.cortisol_level > 0.7:
            risk_factors.append('elevated_cortisol')

        if len([event for event in self.stress_events if event.get('timestamp')]) > 3:
            risk_factors.append('frequent_recent_stressors')

        return risk_factors

    def _calculate_overall_wellness_score(self, physiological: Dict, emotional: Dict, cognitive: Dict) -> float:
        """Calculate overall wellness score"""

        phys_score = (1.0 - physiological['stress_level'] +
                     physiological['autonomic_balance'] +
                     physiological['heart_rate_variability']) / 3

        emo_score = (emotional['emotional_stability'] +
                    emotional['emotional_regulation_capacity']) / 2

        cog_score = sum(cognitive.values()) / len(cognitive)

        return (phys_score + emo_score + cog_score) / 3

    def _generate_wellness_recommendations(self, wellness_score: float, risk_factors: List[str]) -> List[str]:
        """Generate wellness recommendations"""

        recommendations = []

        if wellness_score < 0.4:
            recommendations.append('Consider comprehensive stress management program')
        elif wellness_score < 0.6:
            recommendations.append('Implement targeted wellness interventions')
        else:
            recommendations.append('Maintain current wellness practices')

        for risk_factor in risk_factors:
            if risk_factor == 'high_stress_level':
                recommendations.append('Priority: stress level reduction')
            elif risk_factor == 'elevated_cortisol':
                recommendations.append('Focus on cortisol regulation techniques')

        return recommendations
