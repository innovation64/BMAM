"""
Distortion Detection Mixin
扭曲检测模块
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class DistortionDetectionMixin:
    """扭曲检测Mixin"""

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

    def _calculate_age_distortion(self, memory) -> float:
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

    async def _check_schema_consistency(self, memory) -> float:
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

    def _check_temporal_displacement(self, memory) -> float:
        """Check for temporal displacement indicators"""
        # Simple heuristic based on access patterns
        if memory.last_accessed and memory.timestamp:
            time_gap = memory.last_accessed - memory.timestamp
            if time_gap.days > 30:
                return 0.6  # Higher chance of temporal displacement
            elif time_gap.days > 7:
                return 0.3

        return 0.1  # Low temporal displacement risk

    async def _check_detail_consistency(self, memory) -> float:
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

    def _analyze_age_distribution(self, memories: List) -> Dict[str, int]:
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

    def _analyze_importance_distribution(self, memories: List) -> Dict[str, int]:
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

    def _analyze_emotional_correlation(self, memories: List) -> float:
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
