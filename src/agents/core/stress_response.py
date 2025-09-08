"""
Stress Response Agent
应激反应智能体 - 对应杏仁核+HPA轴
"""

from collections import deque
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

from ..base import BrainAgent, AgentMessage, BrainRegion
from ...memory.memory_item import MemoryItem

logger = logging.getLogger(__name__)


class StressResponseAgent(BrainAgent):
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
            system_prompt="""You are the stress response and threat detection system of a brain-inspired AI.
            Your role is to:
            1. Detect threats and dangerous situations in input stimuli
            2. Process and encode emotional memories with appropriate intensity
            3. Modulate stress responses and their effects on memory systems
            4. Handle traumatic memories with specialized processing
            5. Regulate emotional states and their impact on cognition"""
        )
        
        # External services
        self.db_manager = db_manager
        
        # Stress and emotional state
        self.stress_level = 0.3  # Current stress level (0-1)
        self.emotional_state = {
            'valence': 0.0,      # -1 (negative) to +1 (positive)
            'arousal': 0.3,      # 0 (calm) to 1 (excited)
            'dominance': 0.5     # 0 (submissive) to 1 (dominant)
        }
        
        # Threat detection parameters
        self.threat_keywords = {
            'danger': 0.8,
            'risk': 0.6,
            'threat': 0.9,
            'fear': 0.7,
            'panic': 0.9,
            'emergency': 0.8,
            'critical': 0.7,
            'urgent': 0.6,
            'crisis': 0.8,
            'warning': 0.5,
            'alarm': 0.7,
            'hazard': 0.7
        }
        
        # Emotional categories and intensities
        self.emotion_categories = {
            'positive': ['joy', 'happiness', 'satisfaction', 'excitement', 'love', 'gratitude', 'pride', 'relief'],
            'negative': ['sadness', 'anger', 'fear', 'anxiety', 'frustration', 'disappointment', 'disgust', 'shame'],
            'neutral': ['calm', 'neutral', 'indifferent', 'contemplative']
        }
        
        # Stress response buffers
        self.threat_history = deque(maxlen=20)
        self.emotional_buffer = deque(maxlen=15)
        self.stress_events = deque(maxlen=10)
        
        # HPA axis simulation parameters
        self.cortisol_level = 0.3        # Simulated cortisol level
        self.adrenaline_level = 0.2      # Simulated adrenaline level
        self.recovery_rate = 0.05        # Stress recovery rate per cycle
        
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
    
    async def _detect_threat(self, stimulus: Dict[str, Any]) -> Dict[str, Any]:
        """Detect potential threats in stimuli using amygdala-like processing"""
        
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
            'timestamp': datetime.now(),
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
    
    async def _emotional_memory_encoding(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Encode memory with emotional enhancement (amygdala modulation)"""
        
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
            'timestamp': datetime.now()
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
                'timestamp': datetime.now(),
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
    
    async def _process_traumatic_memory(self, trauma_data: Dict[str, Any]) -> Dict[str, Any]:
        """Special processing for traumatic memories with protective mechanisms"""
        
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
    
    async def _trigger_fight_flight_freeze(self, threat_level: float) -> Dict[str, Any]:
        """Trigger fight-flight-freeze response based on threat level"""
        
        # Determine response type based on threat characteristics
        if threat_level > 0.8:
            response_type = 'freeze'  # Overwhelming threat
        elif threat_level > 0.6:
            # Choose between fight or flight based on context
            response_type = 'flight' if self.emotional_state['dominance'] < 0.5 else 'fight'
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
        self.emotional_state['valence'] += (source_valence - self.emotional_state['valence']) * contagion_effect
        self.emotional_state['arousal'] += (source_intensity - self.emotional_state['arousal']) * contagion_effect * 0.5
        
        # Clamp values
        self.emotional_state['valence'] = max(-1.0, min(1.0, self.emotional_state['valence']))
        self.emotional_state['arousal'] = max(0.0, min(1.0, self.emotional_state['arousal']))
        
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
    
    # Helper methods for threat detection
    
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
            threat_analysis = await self.call_llm(prompt)
            
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
            self.emotional_state['valence'] -= threat_score * 0.5
            self.emotional_state['valence'] = max(-1.0, self.emotional_state['valence'])
            
            # Increased arousal from threat
            self.emotional_state['arousal'] += threat_score * 0.6
            self.emotional_state['arousal'] = min(1.0, self.emotional_state['arousal'])
            
            # Decreased dominance (feeling of control)
            self.emotional_state['dominance'] -= threat_score * 0.3
            self.emotional_state['dominance'] = max(0.0, self.emotional_state['dominance'])
    
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
    
    # Helper methods for emotional encoding
    
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
    
    # Helper methods for stress modulation
    
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
        self.emotional_state['valence'] += (0.0 - self.emotional_state['valence']) * 0.05
        self.emotional_state['arousal'] *= 0.98
        self.emotional_state['dominance'] += (0.5 - self.emotional_state['dominance']) * 0.03
    
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
    
    # Helper methods for trauma processing
    
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
    
    # Additional helper methods would continue here...
    # Due to length constraints, I'm including the essential structure
    
    def _apply_cognitive_reappraisal(self, regulation_strategy: Dict) -> float:
        """Apply cognitive reappraisal regulation"""
        # Implementation for cognitive reappraisal
        return 0.6  # Placeholder
    
    def _apply_emotional_suppression(self, regulation_strategy: Dict) -> float:
        """Apply emotional suppression regulation"""
        # Implementation for emotional suppression
        return 0.4  # Placeholder
    
    def _apply_mindfulness_regulation(self, regulation_strategy: Dict) -> float:
        """Apply mindfulness-based regulation"""
        # Implementation for mindfulness regulation
        return 0.7  # Placeholder
    
    def _apply_distraction_regulation(self, regulation_strategy: Dict) -> float:
        """Apply distraction-based regulation"""
        # Implementation for distraction regulation
        return 0.5  # Placeholder
    
    def _calculate_emotional_stability(self) -> float:
        """Calculate emotional stability metric"""
        # Analyze recent emotional buffer for stability
        return 0.6  # Placeholder
    
    def _analyze_mood_trend(self) -> str:
        """Analyze recent mood trend"""
        # Analyze emotional buffer for trends
        return "stable"  # Placeholder
    
    def _assess_regulation_capacity(self) -> float:
        """Assess current emotional regulation capacity"""
        return max(0.2, 1.0 - self.stress_level * 0.6)
    
    def _assess_stress_risk_factors(self) -> List[str]:
        """Assess current stress risk factors"""
        risk_factors = []
        
        if self.stress_level > 0.7:
            risk_factors.append('high_stress_level')
        
        if self.cortisol_level > 0.7:
            risk_factors.append('elevated_cortisol')
        
        if len([event for event in self.stress_events if (datetime.now() - event['timestamp']).days < 7]) > 3:
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
    
    # Fight-flight-freeze helper methods (simplified implementations)
    
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
    
    def _calculate_contagion_susceptibility(self) -> float:
        """Calculate susceptibility to emotional contagion"""
        base_susceptibility = 0.5
        
        # High stress increases susceptibility
        stress_modifier = self.stress_level * 0.3
        
        # Current emotional arousal affects susceptibility
        arousal_modifier = self.emotional_state['arousal'] * 0.2
        
        return min(1.0, base_susceptibility + stress_modifier + arousal_modifier)