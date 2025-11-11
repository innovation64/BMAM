"""
Source Confusion Mixin
来源混淆模块
"""

from typing import Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SourceConfusionMixin:
    """来源混淆Mixin"""

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

    def _check_modification_history(self, memory) -> Dict[str, Any]:
        """Check memory modification history"""
        return {
            'access_frequency': memory.access_frequency,
            'modification_count': memory.metadata.get('modifications', 0),
            'last_modified': memory.metadata.get('last_modified', memory.timestamp.isoformat())
        }

    async def _check_cross_references(self, memory) -> bool:
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

    async def _verify_source_type(self, memory) -> float:
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

    def _assess_perceptual_details(self, memory) -> float:
        """Assess richness of perceptual details"""
        # Simple heuristic based on content length and descriptive words
        content = memory.content.lower()
        perceptual_words = ['see', 'hear', 'feel', 'touch', 'smell', 'taste', 'color', 'sound', 'texture']

        perceptual_count = sum(1 for word in perceptual_words if word in content)
        return min(1.0, perceptual_count * 0.2)

    def _assess_contextual_information(self, memory) -> float:
        """Assess richness of contextual information"""
        return min(1.0, len(memory.context_tags) * 0.3)

    def _assess_semantic_details(self, memory) -> float:
        """Assess semantic detail richness"""
        # Heuristic based on content complexity
        word_count = len(memory.content.split())
        return min(1.0, word_count / 50)  # Normalize by typical sentence length

    def _assess_affective_information(self, memory) -> float:
        """Assess emotional/affective information"""
        return memory.emotion_intensity

    def _assess_cognitive_operations(self, memory) -> float:
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
