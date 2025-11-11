"""
Reconstruction Errors Mixin
重构错误模块
"""

from typing import Dict, Any, List
from datetime import datetime


class ReconstructionErrorsMixin:
    """重构错误Mixin"""

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
        from ...memory.memory_item import MemoryItem

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
