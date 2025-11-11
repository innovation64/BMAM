"""
Threat Detection Mixin
威胁检测功能模块
"""

import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ThreatDetectionMixin:
    """威胁检测Mixin"""

    async def _detect_threat(self, stimulus: Dict[str, Any]) -> Dict[str, Any]:
        """
        威胁检测主方法

        检测以下类型威胁：
        1. 关键词威胁
        2. 上下文威胁
        3. 模式威胁
        4. 情绪威胁
        5. 时间威胁
        """
        content = stimulus.get('content', '').lower()
        context = stimulus.get('context', {})
        metadata = stimulus.get('metadata', {})

        # Multi-level threat analysis
        threat_analysis = {
            'keyword_threats': self._detect_keyword_threats(content),
            'contextual_threats': self._detect_contextual_threats(context),
            'pattern_threats': await self._detect_pattern_threats(content),
            'emotional_threats': self._detect_emotional_threats(content),
            'temporal_threats': self._detect_temporal_threats(metadata)
        }

        # Calculate overall threat score
        threat_score = self._calculate_overall_threat_score(threat_analysis)

        # Determine threat level and response
        threat_level = self._classify_threat_level(threat_score)
        response_type = self._determine_response_type(threat_level, threat_analysis)

        # Update stress level based on threat
        old_stress = self.stress_level
        self._update_stress_level(threat_score, threat_level)

        # Update emotional state
        self._update_emotional_state_from_threat(threat_score, threat_analysis)

        # Record threat detection
        threat_record = {
            'timestamp': datetime.now().isoformat(),
            'threat_score': threat_score,
            'threat_level': threat_level,
            'stimulus': stimulus,
            'analysis': threat_analysis,
            'response_type': response_type
        }

        self.threat_history.append(threat_record)

        if threat_score > 0.3:
            self.threats_detected += 1

        return {
            'threat_detected': threat_score > 0.3,
            'threat_score': threat_score,
            'threat_level': threat_level,
            'response_type': response_type,
            'threat_analysis': threat_analysis,
            'stress_level_before': old_stress,
            'stress_level_after': self.stress_level,
            'emotional_state': self.emotional_state.copy(),
            'recommended_action': self._get_threat_response_recommendation(threat_level)
        }

    def _detect_keyword_threats(self, content: str) -> Dict[str, float]:
        """Detect threats based on keyword analysis"""
        detected_threats = {}
        max_threat = 0.0

        for keyword, threat_level in self.threat_keywords.items():
            if keyword in content:
                detected_threats[keyword] = threat_level
                max_threat = max(max_threat, threat_level)

        return {
            'detected_keywords': detected_threats,
            'max_threat_score': max_threat,
            'total_keywords': len(detected_threats)
        }

    def _detect_contextual_threats(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Detect threats based on contextual information"""
        contextual_threats = {}
        threat_score = 0.0

        # Check context for threat indicators
        if context.get('urgency_level', 0) > 0.7:
            contextual_threats['high_urgency'] = 0.6
            threat_score += 0.6

        if context.get('risk_level', 0) > 0.5:
            contextual_threats['elevated_risk'] = context['risk_level'] * 0.8
            threat_score += context['risk_level'] * 0.8

        if context.get('emotional_intensity', 0) > 0.8:
            contextual_threats['high_emotional_intensity'] = 0.5
            threat_score += 0.5

        return {
            'contextual_indicators': contextual_threats,
            'contextual_threat_score': min(1.0, threat_score)
        }

    async def _detect_pattern_threats(self, content: str) -> Dict[str, float]:
        """Detect threat patterns using advanced analysis"""
        # Use LLM to detect more sophisticated threat patterns
        prompt = f"Analyze this content for potential threats, dangers, or concerning patterns (rate 0-1): {content}"

        try:
            threat_analysis = await self.call_llm(prompt, quick_fail=True)

            # Extract threat score from analysis
            import re
            score_match = re.search(r'(\d*\.?\d+)', threat_analysis)
            if score_match:
                pattern_threat_score = min(1.0, max(0.0, float(score_match.group(1))))
            else:
                pattern_threat_score = 0.3  # Default moderate concern

            return {
                'pattern_analysis': threat_analysis,
                'pattern_threat_score': pattern_threat_score
            }
        except Exception as e:
            logger.error(f"Error in pattern threat detection: {e}")
            return {
                'pattern_analysis': 'Analysis failed',
                'pattern_threat_score': 0.0
            }

    def _detect_emotional_threats(self, content: str) -> Dict[str, float]:
        """Detect emotional threats and distress signals"""
        emotional_threats = {}
        threat_score = 0.0

        # Negative emotion indicators
        negative_words = ['scared', 'terrified', 'panicked', 'overwhelmed', 'helpless', 'trapped', 'hopeless']

        for word in negative_words:
            if word in content.lower():
                emotional_threats[word] = 0.6
                threat_score += 0.2

        # Intensity modifiers
        intensity_words = ['extremely', 'very', 'incredibly', 'absolutely', 'completely']

        for word in intensity_words:
            if word in content.lower():
                threat_score *= 1.2  # Amplify existing threats

        return {
            'emotional_indicators': emotional_threats,
            'emotional_threat_score': min(1.0, threat_score)
        }

    def _detect_temporal_threats(self, metadata: Dict[str, Any]) -> Dict[str, float]:
        """Detect temporal threat indicators"""
        temporal_threats = {}
        threat_score = 0.0

        # Time pressure indicators
        if metadata.get('deadline_proximity', 0) > 0.8:
            temporal_threats['imminent_deadline'] = 0.7
            threat_score += 0.7

        if metadata.get('time_pressure', 0) > 0.6:
            temporal_threats['time_pressure'] = metadata['time_pressure'] * 0.6
            threat_score += metadata['time_pressure'] * 0.6

        return {
            'temporal_indicators': temporal_threats,
            'temporal_threat_score': min(1.0, threat_score)
        }

    def _calculate_overall_threat_score(self, threat_analysis: Dict[str, Any]) -> float:
        """Calculate overall threat score from multiple analyses"""

        # Weight different threat types
        weights = {
            'keyword_threats': 0.3,
            'contextual_threats': 0.2,
            'pattern_threats': 0.25,
            'emotional_threats': 0.15,
            'temporal_threats': 0.1
        }

        total_score = 0.0

        for threat_type, analysis in threat_analysis.items():
            if threat_type in weights:
                if isinstance(analysis, dict):
                    # Extract the main threat score from the analysis
                    if 'max_threat_score' in analysis:
                        score = analysis['max_threat_score']
                    elif f'{threat_type.replace("_threats", "")}_threat_score' in analysis:
                        score = analysis[f'{threat_type.replace("_threats", "")}_threat_score']
                    elif 'pattern_threat_score' in analysis:
                        score = analysis['pattern_threat_score']
                    else:
                        score = 0.0
                else:
                    score = analysis if isinstance(analysis, (int, float)) else 0.0

                total_score += score * weights[threat_type]

        return min(1.0, total_score)

    def _classify_threat_level(self, threat_score: float) -> str:
        """Classify threat level based on score"""
        if threat_score > 0.8:
            return 'critical'
        elif threat_score > 0.6:
            return 'high'
        elif threat_score > 0.4:
            return 'moderate'
        elif threat_score > 0.2:
            return 'low'
        else:
            return 'minimal'

    def _determine_response_type(self, threat_level: str, threat_analysis: Dict) -> str:
        """Determine appropriate response type"""
        if threat_level == 'critical':
            return 'fight_flight_freeze'
        elif threat_level == 'high':
            return 'heightened_alertness'
        elif threat_level == 'moderate':
            return 'increased_attention'
        elif threat_level == 'low':
            return 'monitoring'
        else:
            return 'normal_processing'

    def _update_stress_level(self, threat_score: float, threat_level: str):
        """Update stress level based on threat detection"""
        if threat_level == 'critical':
            self.stress_level = min(1.0, self.stress_level + 0.5)
        elif threat_level == 'high':
            self.stress_level = min(1.0, self.stress_level + 0.3)
        elif threat_level == 'moderate':
            self.stress_level = min(1.0, self.stress_level + 0.2)
        elif threat_level == 'low':
            self.stress_level = min(1.0, self.stress_level + 0.1)
        else:
            # Natural stress decay
            self.stress_level = max(0.1, self.stress_level * 0.98)

    def _update_emotional_state_from_threat(self, threat_score: float, threat_analysis: Dict):
        """Update emotional state based on threat detection"""
        if threat_score > 0.4:
            # Negative valence from threat
            self.emotional_state.valence -= threat_score * 0.5
            self.emotional_state.valence = max(-1.0, self.emotional_state.valence)

            # Increased arousal from threat
            self.emotional_state.arousal += threat_score * 0.6
            self.emotional_state.arousal = min(1.0, self.emotional_state.arousal)

            # Decreased dominance (feeling of control)
            self.emotional_state.dominance -= threat_score * 0.3
            self.emotional_state.dominance = max(0.0, self.emotional_state.dominance)

    def _get_threat_response_recommendation(self, threat_level: str) -> str:
        """Get appropriate response recommendation for threat level"""
        recommendations = {
            'critical': 'Immediate action required - activate emergency protocols',
            'high': 'Heightened vigilance - assess options and prepare response',
            'moderate': 'Increased attention - monitor situation closely',
            'low': 'Routine monitoring - maintain awareness',
            'minimal': 'Normal processing - no special action needed'
        }

        return recommendations.get(threat_level, 'Assess situation and respond appropriately')
