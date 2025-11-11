"""
Memory Distortion Agent
记忆失真智能体 - 对应内侧颞叶+前额叶
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging
import hashlib

from ..base import BrainAgent, AgentMessage, BrainRegion
from ...memory.memory_item import MemoryItem

logger = logging.getLogger(__name__)


class MemoryDistortionAgent(BrainAgent):
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
    
    async def _detect_memory_distortion(self, memory_id: str) -> Dict[str, Any]:
        """Detect potential memory distortions using multiple indicators"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        memory = self.db_manager.load_memory(memory_id)
        if not memory:
            return {'error': f'Memory {memory_id} not found'}
        
        # Multiple distortion indicators
        distortion_indicators = {
            'source_reliability': memory.source_reliability,
            'reconstruction_count': memory.access_frequency,
            'age_factor': self._calculate_age_distortion(memory),
            'emotional_bias': memory.emotion_intensity,
            'schema_consistency': await self._check_schema_consistency(memory),
            'temporal_displacement': self._check_temporal_displacement(memory),
            'detail_inconsistency': await self._check_detail_consistency(memory)
        }
        
        # Calculate overall distortion risk using weighted factors
        distortion_risk = self._calculate_distortion_risk(distortion_indicators)
        
        # Determine distortion type
        distortion_type = self._identify_distortion_type(distortion_indicators)
        
        is_distorted = distortion_risk > self.distortion_threshold
        
        if is_distorted:
            # Mark memory as potentially distorted
            memory.metadata['distortion_detected'] = True
            memory.metadata['distortion_risk'] = distortion_risk
            memory.metadata['distortion_type'] = distortion_type
            memory.metadata['detection_timestamp'] = datetime.now().isoformat()
            
            # Reduce source reliability
            reliability_penalty = min(0.3, distortion_risk * 0.5)
            memory.source_reliability = max(0.1, memory.source_reliability - reliability_penalty)
            
            self.db_manager.save_memory(memory)
            self.distortions_detected += 1
            
            # Track distortion patterns
            if distortion_type not in self.distortion_patterns:
                self.distortion_patterns[distortion_type] = 0
            self.distortion_patterns[distortion_type] += 1
        
        return {
            'memory_id': memory_id,
            'distortion_detected': is_distorted,
            'distortion_risk': distortion_risk,
            'distortion_type': distortion_type,
            'indicators': distortion_indicators,
            'new_reliability': memory.source_reliability,
            'recommendation': self._get_distortion_recommendation(distortion_risk, distortion_type)
        }
    
    async def _verify_memory_source(self, memory_id: str) -> Dict[str, Any]:
        """Verify the source and authenticity of a memory (source monitoring)"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        memory = self.db_manager.load_memory(memory_id)
        if not memory:
            return {'error': f'Memory {memory_id} not found'}
        
        # Source monitoring checks
        source_checks = {
            'has_metadata': bool(memory.metadata),
            'has_timestamp': bool(memory.timestamp),
            'has_associations': len(memory.associations) > 0,
            'consolidation_appropriate': memory.consolidation_level > 0,
            'context_consistency': len(memory.context_tags) > 0,
            'modification_history': self._check_modification_history(memory),
            'cross_reference_available': await self._check_cross_references(memory)
        }
        
        # Calculate source confidence
        source_confidence = self._calculate_source_confidence(source_checks)
        
        # Additional checks for specific source types
        if 'source_type' in memory.metadata:
            source_type_confidence = await self._verify_source_type(memory)
            source_confidence = (source_confidence + source_type_confidence) / 2
        
        # Update source reliability based on verification
        old_reliability = memory.source_reliability
        memory.source_reliability = source_confidence
        
        # Add verification metadata
        memory.metadata['source_verified'] = True
        memory.metadata['verification_timestamp'] = datetime.now().isoformat()
        memory.metadata['verification_confidence'] = source_confidence
        
        self.db_manager.save_memory(memory)
        self.source_verifications += 1
        
        # Cache result for future use
        self.source_reliability_cache[memory_id] = {
            'confidence': source_confidence,
            'timestamp': datetime.now().isoformat()
        }
        
        return {
            'memory_id': memory_id,
            'source_verified': True,
            'old_reliability': old_reliability,
            'new_reliability': source_confidence,
            'source_checks': source_checks,
            'is_authentic': source_confidence > 0.6,
            'verification_details': self._get_verification_details(source_checks, source_confidence)
        }
    
    async def _handle_false_memory(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle detected false memories with appropriate containment"""
        
        # Create a marked false memory record
        false_memory = MemoryItem(
            content=memory_data['content'],
            memory_type='false_memory',
            brain_region=BrainRegion.HIPPOCAMPUS,
            source_reliability=0.0,  # Mark as completely unreliable
            importance=0.1,  # Minimal importance
            decay_rate=0.9,  # High decay rate for quick forgetting
            metadata={
                'false_memory': True,
                'detection_reason': memory_data.get('reason', 'Unknown'),
                'original_context': memory_data.get('context', {}),
                'detection_confidence': memory_data.get('confidence', 0.5),
                'containment_timestamp': datetime.now().isoformat()
            }
        )
        
        # Apply containment strategies
        containment_strategies = self._apply_containment_strategies(false_memory, memory_data)
        
        # Store with special isolation
        if self.db_manager:
            self.db_manager.save_memory(false_memory)
        
        self.false_memory_markers.append(false_memory.id)
        self.false_memories_handled += 1
        
        return {
            'false_memory_handled': True,
            'memory_id': false_memory.id,
            'containment_strategies': containment_strategies,
            'decay_rate': false_memory.decay_rate,
            'isolation_level': 'high',
            'monitoring_required': True
        }
    
    async def _reconstruct_memory(self, partial_memory: Dict[str, Any]) -> Dict[str, Any]:
        """Reconstruct memory from partial information with distortion awareness"""
        
        reconstruction = {
            'original_fragment': partial_memory.get('fragment', ''),
            'context_cues': partial_memory.get('context', []),
            'emotional_state': partial_memory.get('emotion', 'neutral'),
            'reconstruction_confidence': 0.0,
            'reconstructed_content': '',
            'distortion_warnings': [],
            'reliability_estimate': 0.5
        }
        
        # Check for common reconstruction biases
        bias_warnings = self._check_reconstruction_biases(partial_memory)
        reconstruction['distortion_warnings'].extend(bias_warnings)
        
        # Use LLM with distortion-aware prompting
        prompt = f"""
        Carefully reconstruct a memory from these fragments, being aware of potential distortions:
        
        Fragment: {reconstruction['original_fragment']}
        Context: {', '.join(reconstruction['context_cues'])}
        Emotional state: {reconstruction['emotional_state']}
        
        IMPORTANT: 
        - Indicate uncertainty where appropriate
        - Note potential biases or distortions
        - Distinguish between likely accurate elements and uncertain details
        - Provide confidence levels for different parts
        """
        
        reconstructed = await self.call_llm(prompt)
        reconstruction['reconstructed_content'] = reconstructed
        
        # Calculate reconstruction confidence based on available cues
        confidence = self._calculate_reconstruction_confidence(reconstruction)
        reconstruction['reconstruction_confidence'] = confidence
        
        # Estimate reliability of reconstruction
        reliability = self._estimate_reconstruction_reliability(partial_memory, reconstruction)
        reconstruction['reliability_estimate'] = reliability
        
        # Create reconstructed memory with appropriate warnings
        reconstructed_memory = MemoryItem(
            content=reconstructed,
            memory_type='reconstructed',
            source_reliability=reliability,
            importance=partial_memory.get('importance', 0.5),
            metadata={
                'reconstructed': True,
                'original_fragment': reconstruction['original_fragment'],
                'reconstruction_confidence': confidence,
                'distortion_warnings': reconstruction['distortion_warnings'],
                'reconstruction_method': 'llm_assisted'
            }
        )
        
        if self.db_manager:
            self.db_manager.save_memory(reconstructed_memory)
        
        return {
            'reconstruction_complete': True,
            'reconstruction': reconstruction,
            'memory_id': reconstructed_memory.id,
            'confidence': confidence,
            'reliability': reliability,
            'warnings': reconstruction['distortion_warnings']
        }
    
    async def _check_memory_contamination(self, memory_ids: List[str]) -> Dict[str, Any]:
        """Check for cross-contamination between memories"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        memories = []
        for memory_id in memory_ids:
            memory = self.db_manager.load_memory(memory_id)
            if memory:
                memories.append(memory)
        
        if len(memories) < 2:
            return {'error': 'Need at least 2 memories to check contamination'}
        
        contamination_results = []
        
        # Check pairwise contamination
        for i in range(len(memories)):
            for j in range(i + 1, len(memories)):
                mem1, mem2 = memories[i], memories[j]
                
                contamination_score = self._calculate_contamination_score(mem1, mem2)
                
                if contamination_score > 0.4:  # Contamination threshold
                    contamination_results.append({
                        'memory1_id': mem1.id,
                        'memory2_id': mem2.id,
                        'contamination_score': contamination_score,
                        'contamination_type': self._identify_contamination_type(mem1, mem2),
                        'recommended_action': self._get_contamination_action(contamination_score)
                    })
        
        return {
            'contamination_check_complete': True,
            'memories_checked': len(memories),
            'contaminations_found': len(contamination_results),
            'contamination_details': contamination_results,
            'overall_contamination_risk': len(contamination_results) / (len(memories) * (len(memories) - 1) / 2)
        }
    
    async def _perform_source_monitoring(self, memory_id: str) -> Dict[str, Any]:
        """Perform comprehensive source monitoring"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        memory = self.db_manager.load_memory(memory_id)
        if not memory:
            return {'error': f'Memory {memory_id} not found'}
        
        # Source monitoring dimensions (Johnson & Raye, 1981)
        monitoring_results = {
            'perceptual_details': self._assess_perceptual_details(memory),
            'contextual_information': self._assess_contextual_information(memory),
            'semantic_details': self._assess_semantic_details(memory),
            'affective_information': self._assess_affective_information(memory),
            'cognitive_operations': self._assess_cognitive_operations(memory)
        }
        
        # Overall source monitoring score
        source_score = sum(monitoring_results.values()) / len(monitoring_results)
        
        # Determine most likely source
        source_classification = self._classify_memory_source(monitoring_results, source_score)
        
        return {
            'source_monitoring_complete': True,
            'memory_id': memory_id,
            'monitoring_results': monitoring_results,
            'source_score': source_score,
            'source_classification': source_classification,
            'confidence': source_score,
            'recommendations': self._get_source_monitoring_recommendations(source_classification, source_score)
        }
    
    async def _analyze_distortion_patterns(self) -> Dict[str, Any]:
        """Analyze system-wide distortion patterns"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        # Load all memories with distortion markers
        all_memories = self.db_manager.load_memories_by_criteria()
        distorted_memories = [
            mem for mem in all_memories 
            if mem.metadata.get('distortion_detected', False)
        ]
        
        # Analyze patterns
        patterns = {
            'total_memories': len(all_memories),
            'distorted_memories': len(distorted_memories),
            'distortion_rate': len(distorted_memories) / len(all_memories) if all_memories else 0,
            'distortion_types': self.distortion_patterns.copy(),
            'age_distribution': self._analyze_age_distribution(distorted_memories),
            'importance_distribution': self._analyze_importance_distribution(distorted_memories),
            'emotional_correlation': self._analyze_emotional_correlation(distorted_memories)
        }
        
        # Generate insights
        insights = self._generate_distortion_insights(patterns)
        
        return {
            'analysis_complete': True,
            'patterns': patterns,
            'insights': insights,
            'total_distortions_detected': self.distortions_detected,
            'false_memories_handled': self.false_memories_handled
        }
    
    def _calculate_age_distortion(self, memory: MemoryItem) -> float:
        """Calculate age-related distortion factor"""
        age_days = (datetime.now() - memory.timestamp).days
        
        # Older memories are more prone to distortion
        if age_days < 1:
            return 0.1
        elif age_days < 7:
            return 0.2
        elif age_days < 30:
            return 0.4
        elif age_days < 365:
            return 0.6
        else:
            return 0.8
    
    async def _check_schema_consistency(self, memory: MemoryItem) -> float:
        """Check consistency with existing schemas"""
        # Use LLM to check schema consistency
        prompt = f"Rate the consistency of this memory with common knowledge (0-1): {memory.content}"
        try:
            consistency_str = await self.call_llm(prompt)
            # Extract numerical value
            import re
            match = re.search(r'(\d*\.?\d+)', consistency_str)
            if match:
                return min(1.0, max(0.0, float(match.group(1))))
        except (ValueError, AttributeError, Exception) as e:
            logger.debug(f"Failed to check schema consistency: {e}")
        
        return 0.5  # Default neutral consistency
    
    def _check_temporal_displacement(self, memory: MemoryItem) -> float:
        """Check for temporal displacement indicators"""
        # Simple heuristic based on access patterns
        if memory.last_accessed and memory.timestamp:
            time_gap = memory.last_accessed - memory.timestamp
            if time_gap.days > 30:
                return 0.6  # Higher chance of temporal displacement
            elif time_gap.days > 7:
                return 0.3
        
        return 0.1  # Low temporal displacement risk
    
    async def _check_detail_consistency(self, memory: MemoryItem) -> float:
        """Check internal consistency of memory details"""
        # Use LLM to check internal consistency
        prompt = f"Rate internal consistency of details in this memory (0-1): {memory.content}"
        try:
            consistency_str = await self.call_llm(prompt)
            import re
            match = re.search(r'(\d*\.?\d+)', consistency_str)
            if match:
                return min(1.0, max(0.0, float(match.group(1))))
        except (ValueError, AttributeError, Exception) as e:
            logger.debug(f"Failed to check detail consistency: {e}")
        
        return 0.7  # Default assumption of consistency
    
    def _calculate_distortion_risk(self, indicators: Dict[str, float]) -> float:
        """Calculate overall distortion risk from indicators"""
        weights = {
            'source_reliability': -0.3,  # Lower reliability = higher risk
            'reconstruction_count': 0.2,   # More reconstructions = higher risk
            'age_factor': 0.2,
            'emotional_bias': 0.15,
            'schema_consistency': -0.1,   # Lower consistency = higher risk
            'temporal_displacement': 0.1,
            'detail_inconsistency': 0.15
        }
        
        risk = 0.0
        for indicator, value in indicators.items():
            if indicator in weights:
                if weights[indicator] < 0:
                    # Inverse relationship
                    risk += abs(weights[indicator]) * (1.0 - value)
                else:
                    # Direct relationship
                    risk += weights[indicator] * value
        
        return min(1.0, max(0.0, risk))
    
    def _identify_distortion_type(self, indicators: Dict[str, float]) -> str:
        """Identify the most likely type of distortion"""
        if indicators['temporal_displacement'] > 0.5:
            return 'temporal'
        elif indicators['source_reliability'] < 0.3:
            return 'source'
        elif indicators['detail_inconsistency'] > 0.6:
            return 'detail'
        elif indicators['emotional_bias'] > 0.7:
            return 'emotional'
        elif indicators['schema_consistency'] < 0.3:
            return 'schema'
        elif indicators['reconstruction_count'] > 0.7:
            return 'interference'
        else:
            return 'general'
    
    def _get_distortion_recommendation(self, risk: float, distortion_type: str) -> str:
        """Get recommendation based on distortion risk and type"""
        if risk > 0.8:
            return f"High {distortion_type} distortion risk - Consider memory isolation"
        elif risk > 0.5:
            return f"Moderate {distortion_type} distortion risk - Verify with corroborating evidence"
        elif risk > 0.3:
            return f"Low {distortion_type} distortion risk - Monitor for changes"
        else:
            return "Memory appears reliable"
    
    def _check_modification_history(self, memory: MemoryItem) -> Dict[str, Any]:
        """Check memory modification history"""
        return {
            'access_frequency': memory.access_frequency,
            'modification_count': memory.metadata.get('modifications', 0),
            'last_modified': memory.metadata.get('last_modified', memory.timestamp.isoformat())
        }
    
    async def _check_cross_references(self, memory: MemoryItem) -> bool:
        """Check if memory has cross-references for verification"""
        return len(memory.associations) > 0
    
    def _calculate_source_confidence(self, checks: Dict[str, Any]) -> float:
        """Calculate overall source confidence"""
        score = 0.0
        
        if checks['has_metadata']:
            score += 0.2
        if checks['has_timestamp']:
            score += 0.15
        if checks['has_associations']:
            score += 0.2
        if checks['consolidation_appropriate']:
            score += 0.15
        if checks['context_consistency']:
            score += 0.15
        if checks['cross_reference_available']:
            score += 0.15
        
        return min(1.0, score)
    
    async def _verify_source_type(self, memory: MemoryItem) -> float:
        """Verify specific source type claims"""
        # This would implement specific verification logic
        # For now, return a moderate confidence
        return 0.6
    
    def _get_verification_details(self, checks: Dict, confidence: float) -> Dict[str, Any]:
        """Get detailed verification information"""
        return {
            'primary_indicators': [k for k, v in checks.items() if v],
            'missing_indicators': [k for k, v in checks.items() if not v],
            'confidence_level': 'high' if confidence > 0.7 else 'medium' if confidence > 0.4 else 'low'
        }
    
    def _apply_containment_strategies(self, false_memory: MemoryItem, memory_data: Dict) -> List[str]:
        """Apply containment strategies for false memories"""
        strategies = []
        
        # Isolation strategy
        false_memory.metadata['isolated'] = True
        strategies.append('isolation')
        
        # Rapid decay strategy
        false_memory.decay_rate = 0.95
        strategies.append('rapid_decay')
        
        # Warning tags
        false_memory.context_tags.append('false_memory_warning')
        strategies.append('warning_tags')
        
        # Prevent association formation
        false_memory.metadata['association_blocked'] = True
        strategies.append('association_blocking')
        
        return strategies
    
    def _check_reconstruction_biases(self, partial_memory: Dict) -> List[str]:
        """Check for common reconstruction biases"""
        warnings = []
        
        # Availability heuristic
        if len(partial_memory.get('context', [])) < 2:
            warnings.append('Limited context may lead to availability bias')
        
        # Emotional bias
        if partial_memory.get('emotion', 'neutral') != 'neutral':
            warnings.append('Strong emotions may bias reconstruction')
        
        # Confirmation bias
        if 'expectation' in partial_memory:
            warnings.append('Expectations may lead to confirmation bias')
        
        # Hindsight bias
        if 'outcome_known' in partial_memory:
            warnings.append('Known outcomes may create hindsight bias')
        
        return warnings
    
    def _calculate_reconstruction_confidence(self, reconstruction: Dict) -> float:
        """Calculate confidence in memory reconstruction"""
        confidence = 0.3  # Base confidence
        
        # More context cues increase confidence
        if len(reconstruction['context_cues']) > 2:
            confidence += 0.3
        elif len(reconstruction['context_cues']) > 0:
            confidence += 0.2
        
        # Specific emotional states can increase confidence
        if reconstruction['emotional_state'] != 'neutral':
            confidence += 0.2
        
        # Longer fragments provide more anchoring
        if len(reconstruction['original_fragment']) > 50:
            confidence += 0.2
        
        # Reduce confidence based on warnings
        warning_penalty = len(reconstruction['distortion_warnings']) * 0.1
        confidence -= warning_penalty
        
        return min(1.0, max(0.1, confidence))
    
    def _estimate_reconstruction_reliability(self, partial_memory: Dict, reconstruction: Dict) -> float:
        """Estimate reliability of reconstructed memory"""
        # Start with reconstruction confidence
        reliability = reconstruction['reconstruction_confidence']
        
        # Adjust based on known biases
        if len(reconstruction['distortion_warnings']) > 2:
            reliability *= 0.7
        elif len(reconstruction['distortion_warnings']) > 0:
            reliability *= 0.85
        
        # Consider source of partial memory
        if partial_memory.get('source_reliability', 1.0) < 0.5:
            reliability *= 0.8
        
        return min(1.0, max(0.1, reliability))
    
    def _calculate_contamination_score(self, mem1: MemoryItem, mem2: MemoryItem) -> float:
        """Calculate contamination score between two memories"""
        score = 0.0
        
        # Temporal proximity
        if mem1.timestamp and mem2.timestamp:
            time_diff = abs((mem1.timestamp - mem2.timestamp).total_seconds())
            if time_diff < 3600:  # Within an hour
                score += 0.4
            elif time_diff < 86400:  # Within a day
                score += 0.2
        
        # Content similarity (simple heuristic)
        common_words = set(mem1.content.lower().split()) & set(mem2.content.lower().split())
        if common_words:
            score += min(0.3, len(common_words) * 0.05)
        
        # Context overlap
        common_context = set(mem1.context_tags) & set(mem2.context_tags)
        if common_context:
            score += min(0.2, len(common_context) * 0.1)
        
        # Emotional state similarity
        if mem1.emotion_tags and mem2.emotion_tags:
            common_emotions = set(mem1.emotion_tags) & set(mem2.emotion_tags)
            if common_emotions:
                score += 0.1
        
        return score
    
    def _identify_contamination_type(self, mem1: MemoryItem, mem2: MemoryItem) -> str:
        """Identify type of contamination between memories"""
        # Simple heuristics for contamination type
        time_diff = abs((mem1.timestamp - mem2.timestamp).total_seconds()) if mem1.timestamp and mem2.timestamp else float('inf')
        
        if time_diff < 3600:
            return 'temporal_proximity'
        elif set(mem1.context_tags) & set(mem2.context_tags):
            return 'contextual_overlap'
        elif set(mem1.emotion_tags) & set(mem2.emotion_tags):
            return 'emotional_similarity'
        else:
            return 'content_similarity'
    
    def _get_contamination_action(self, score: float) -> str:
        """Get recommended action for contamination"""
        if score > 0.7:
            return 'Isolate memories to prevent further contamination'
        elif score > 0.5:
            return 'Monitor for contamination effects'
        else:
            return 'Low contamination risk - continue monitoring'
    
    def _assess_perceptual_details(self, memory: MemoryItem) -> float:
        """Assess richness of perceptual details"""
        # Simple heuristic based on content length and descriptive words
        content = memory.content.lower()
        perceptual_words = ['see', 'hear', 'feel', 'touch', 'smell', 'taste', 'color', 'sound', 'texture']
        
        perceptual_count = sum(1 for word in perceptual_words if word in content)
        return min(1.0, perceptual_count * 0.2)
    
    def _assess_contextual_information(self, memory: MemoryItem) -> float:
        """Assess richness of contextual information"""
        return min(1.0, len(memory.context_tags) * 0.3)
    
    def _assess_semantic_details(self, memory: MemoryItem) -> float:
        """Assess semantic detail richness"""
        # Heuristic based on content complexity
        word_count = len(memory.content.split())
        return min(1.0, word_count / 50)  # Normalize by typical sentence length
    
    def _assess_affective_information(self, memory: MemoryItem) -> float:
        """Assess emotional/affective information"""
        return memory.emotion_intensity
    
    def _assess_cognitive_operations(self, memory: MemoryItem) -> float:
        """Assess evidence of cognitive operations"""
        # Check for metacognitive markers
        operations = memory.metadata.get('cognitive_operations', 0)
        return min(1.0, operations * 0.25)
    
    def _classify_memory_source(self, monitoring_results: Dict, score: float) -> str:
        """Classify the most likely source of the memory"""
        if score > 0.8:
            return 'direct_experience'
        elif score > 0.6:
            return 'probable_experience'
        elif score > 0.4:
            return 'uncertain_source'
        elif score > 0.2:
            return 'likely_imagined'
        else:
            return 'false_memory'
    
    def _get_source_monitoring_recommendations(self, classification: str, score: float) -> List[str]:
        """Get recommendations based on source monitoring results"""
        recommendations = []
        
        if classification == 'false_memory':
            recommendations.append('Consider memory isolation')
            recommendations.append('Investigate source of false information')
        elif classification == 'likely_imagined':
            recommendations.append('Verify with external sources if possible')
            recommendations.append('Reduce reliability rating')
        elif classification == 'uncertain_source':
            recommendations.append('Seek corroborating evidence')
            recommendations.append('Monitor for consistency over time')
        elif score > 0.8:
            recommendations.append('Memory appears highly reliable')
        
        return recommendations
    
    def _analyze_age_distribution(self, memories: List[MemoryItem]) -> Dict[str, int]:
        """Analyze age distribution of distorted memories"""
        distribution = {'recent': 0, 'medium': 0, 'old': 0}
        
        for memory in memories:
            age_days = (datetime.now() - memory.timestamp).days
            if age_days < 7:
                distribution['recent'] += 1
            elif age_days < 30:
                distribution['medium'] += 1
            else:
                distribution['old'] += 1
        
        return distribution
    
    def _analyze_importance_distribution(self, memories: List[MemoryItem]) -> Dict[str, int]:
        """Analyze importance distribution of distorted memories"""
        distribution = {'low': 0, 'medium': 0, 'high': 0}
        
        for memory in memories:
            if memory.importance < 0.3:
                distribution['low'] += 1
            elif memory.importance < 0.7:
                distribution['medium'] += 1
            else:
                distribution['high'] += 1
        
        return distribution
    
    def _analyze_emotional_correlation(self, memories: List[MemoryItem]) -> float:
        """Analyze correlation between emotion and distortion"""
        if not memories:
            return 0.0
        
        high_emotion_distorted = sum(1 for mem in memories if mem.emotion_intensity > 0.7)
        return high_emotion_distorted / len(memories)
    
    def _generate_distortion_insights(self, patterns: Dict) -> List[str]:
        """Generate insights from distortion patterns"""
        insights = []
        
        if patterns['distortion_rate'] > 0.2:
            insights.append(f"High distortion rate detected: {patterns['distortion_rate']:.2%}")
        
        if patterns['emotional_correlation'] > 0.5:
            insights.append("Strong correlation between high emotion and distortion")
        
        # Most common distortion type
        if patterns['distortion_types']:
            most_common = max(patterns['distortion_types'], key=patterns['distortion_types'].get)
            insights.append(f"Most common distortion type: {most_common}")
        
        return insights