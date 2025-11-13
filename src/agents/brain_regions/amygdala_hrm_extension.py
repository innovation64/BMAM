"""
Amygdala Agent HRM Extension - 杏仁核智能体HRM扩展
Hierarchical Reasoning Model (HRM) Enhancements for Amygdala

Adds HRM's L module (fast, reactive) capabilities:
1. Fast timescale emotional tagging (every step)
2. State reset from H module (prefrontal cortex)
3. Guided emotional processing based on strategic guidance
4. Local convergence detection for emotional stability

Key Design:
- L module: Updates every step with fast emotional response
- Receives reset signals from H module (Prefrontal)
- Integrates with AmygdalaEmotionTags for efficient emotion indexing
- Provides emotion-modulated memory enhancement to other regions
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class EmotionalContext:
    """
    Emotional Context (L Module State)
    情绪上下文（L模块状态）
    """
    current_emotion: str
    intensity: float
    guidance: Optional[Dict[str, Any]] = None  # From H module
    emotion_regulation: str = 'normal'  # 'normal', 'suppress', 'enhance'
    stress_level: float = 0.0
    iteration: int = 0


@dataclass
class EmotionalTaggingResult:
    """
    Emotional Tagging Result
    情绪标记结果
    """
    memory_id: str
    emotion_tags: List[str]
    intensity: float
    converged: bool
    iteration: int
    regulation_applied: bool


class AmygdalaHRMExtension:
    """
    HRM Extension for Amygdala Agent
    杏仁核智能体的HRM扩展

    Mixin class that adds HRM L module (fast) capabilities to
    the existing AmygdalaAgent.

    Usage:
        class AmygdalaAgentV2(AmygdalaHRMExtension, AmygdalaAgent):
            pass

    HRM Features:
    1. fast_emotional_tagging() - Fast timescale emotional response
    2. reset_from_prefrontal() - Accept reset signals from H module
    3. check_emotional_convergence() - Detect emotional stability
    4. guided_emotion_regulation() - Regulate emotions with strategic guidance
    """

    def __init__(self, *args, **kwargs):
        """Initialize HRM extension"""
        super().__init__(*args, **kwargs)

        # HRM-specific state
        self.emotional_context: Optional[EmotionalContext] = None
        self.working_emotions: List[Dict[str, Any]] = []  # Current emotional tags
        self.iteration_count = 0
        self.prefrontal_guidance: Optional[Dict[str, Any]] = None

        # Convergence tracking
        self.previous_emotional_states: List[Tuple[str, float]] = []  # [(emotion, intensity), ...]
        self.convergence_window = 3  # Check convergence over last 3 iterations

        # Performance metrics
        self.hrm_metrics = {
            'fast_iterations': 0,
            'resets_received': 0,
            'emotional_convergences': 0,
            'avg_iterations_to_stability': 0.0,
            'emotion_regulations': 0
        }

        logger.info("AmygdalaHRMExtension initialized (L module, fast emotional response)")

    async def fast_emotional_tagging(
        self,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fast Emotional Tagging (L Module - Fast Timescale)
        快速情绪标记（L模块 - 快时间尺度）

        Called every step by Thalamus.
        Performs fast emotional assessment with optional guidance from H module.

        Args:
            input_data: Input dictionary with:
                - memory_id: ID of memory to tag
                - content: Memory content
                - reset_guidance: Optional guidance from prefrontal (after reset)
                - context: Additional context

        Returns:
            Dictionary with:
            - emotion_tags: Detected emotions
            - intensity: Emotional intensity
            - converged: Whether emotional assessment is stable
            - iteration: Current iteration number
        """
        self.iteration_count += 1
        self.hrm_metrics['fast_iterations'] += 1

        memory_id = input_data.get('memory_id', '')
        content = input_data.get('content', '')

        # Check for reset guidance from H module
        if 'reset_guidance' in input_data:
            # H module has provided new guidance - use it
            self.prefrontal_guidance = input_data['reset_guidance']
            logger.debug(f"Amygdala received reset guidance: {self.prefrontal_guidance}")

        # Initialize or update emotional context
        if not self.emotional_context:
            self.emotional_context = EmotionalContext(
                current_emotion='neutral',
                intensity=0.0,
                guidance=self.prefrontal_guidance,
                emotion_regulation=self.prefrontal_guidance.get('emotional_regulation', 'normal') if self.prefrontal_guidance else 'normal',
                stress_level=self.current_stress_level if hasattr(self, 'current_stress_level') else 0.0,
                iteration=self.iteration_count
            )
        else:
            self.emotional_context.iteration = self.iteration_count

        logger.debug(f"Amygdala L module iteration {self.iteration_count} "
                    f"with regulation: {self.emotional_context.emotion_regulation}")

        # Perform guided emotional assessment
        tagging_result = await self._guided_emotional_assessment(
            memory_id=memory_id,
            content=content,
            guidance=self.prefrontal_guidance,
            iteration=self.iteration_count
        )

        # Update working emotions
        self.working_emotions.append({
            'memory_id': memory_id,
            'emotion_tags': tagging_result.emotion_tags,
            'intensity': tagging_result.intensity,
            'timestamp': datetime.now()
        })

        # Track emotional state for convergence detection
        primary_emotion = tagging_result.emotion_tags[0] if tagging_result.emotion_tags else 'neutral'
        self.previous_emotional_states.append((primary_emotion, tagging_result.intensity))
        if len(self.previous_emotional_states) > self.convergence_window:
            self.previous_emotional_states.pop(0)

        # Check for emotional convergence (stability)
        converged = self._check_emotional_convergence()

        if converged:
            self.hrm_metrics['emotional_convergences'] += 1
            logger.info(f"Amygdala achieved emotional stability at iteration {self.iteration_count}")

        return {
            'memory_id': memory_id,
            'emotion_tags': tagging_result.emotion_tags,
            'intensity': tagging_result.intensity,
            'converged': converged,
            'iteration': self.iteration_count,
            'regulation_applied': tagging_result.regulation_applied,
            'stress_level': self.emotional_context.stress_level,
            'response': self._format_emotional_response(tagging_result)
        }

    async def _guided_emotional_assessment(
        self,
        memory_id: str,
        content: str,
        guidance: Optional[Dict[str, Any]],
        iteration: int
    ) -> EmotionalTaggingResult:
        """
        Guided Emotional Assessment
        引导式情绪评估

        Assesses emotional content based on input and strategic guidance from H module.

        Args:
            memory_id: Memory identifier
            content: Memory content
            guidance: Strategic guidance from prefrontal cortex
            iteration: Current iteration number

        Returns:
            EmotionalTaggingResult
        """
        # Determine emotion regulation strategy
        if guidance:
            regulation = guidance.get('emotional_regulation', 'normal')
            priority_signals = guidance.get('priority_signals', [])
        else:
            regulation = 'normal'
            priority_signals = []

        # Detect emotions (using existing tag_emotion logic or LLM)
        emotion_tags, intensity = await self._detect_emotions(content, regulation)

        # Apply regulation
        regulated_intensity = intensity
        regulation_applied = False

        if regulation == 'suppress' and 'resolve_conflict' not in priority_signals:
            # Suppress emotional response
            regulated_intensity = min(intensity * 0.5, 0.7)
            regulation_applied = True
            logger.debug(f"Emotion suppressed: {intensity:.2f} -> {regulated_intensity:.2f}")

        elif regulation == 'enhance' or 'increase_attention' in priority_signals:
            # Enhance emotional response
            regulated_intensity = min(intensity * 1.5, 1.0)
            regulation_applied = True
            logger.debug(f"Emotion enhanced: {intensity:.2f} -> {regulated_intensity:.2f}")

        # Check convergence
        converged = iteration >= 2 and regulated_intensity > 0.5

        return EmotionalTaggingResult(
            memory_id=memory_id,
            emotion_tags=emotion_tags,
            intensity=regulated_intensity,
            converged=converged,
            iteration=iteration,
            regulation_applied=regulation_applied
        )

    async def _detect_emotions(
        self,
        content: str,
        regulation: str = 'normal'
    ) -> Tuple[List[str], float]:
        """
        Detect Emotions from Content
        从内容中检测情绪

        Uses simple keyword matching or LLM-based emotion detection.

        Args:
            content: Memory content
            regulation: Current regulation mode

        Returns:
            Tuple of (emotion_tags, intensity)
        """
        # Simple keyword-based emotion detection
        content_lower = content.lower()

        emotion_keywords = {
            'joy': ['happy', 'excited', 'delighted', 'joyful', 'pleased'],
            'sadness': ['sad', 'unhappy', 'depressed', 'gloomy', 'melancholy'],
            'anger': ['angry', 'furious', 'annoyed', 'irritated', 'mad'],
            'fear': ['afraid', 'scared', 'fearful', 'anxious', 'worried'],
            'surprise': ['surprised', 'amazed', 'astonished', 'shocked'],
            'disgust': ['disgusted', 'revolted', 'repulsed'],
            'acceptance': ['calm', 'peaceful', 'content', 'satisfied'],
            'anticipation': ['anticipate', 'expect', 'hopeful', 'eager']
        }

        detected_emotions = []
        max_intensity = 0.0

        for emotion, keywords in emotion_keywords.items():
            for keyword in keywords:
                if keyword in content_lower:
                    detected_emotions.append(emotion)
                    # Estimate intensity based on keyword presence
                    max_intensity = max(max_intensity, 0.6 + len(keywords) * 0.05)
                    break

        # Default to neutral if no emotions detected
        if not detected_emotions:
            detected_emotions = ['neutral']
            max_intensity = 0.3

        # Ensure intensity is in valid range
        intensity = min(max_intensity, 1.0)

        return detected_emotions, intensity

    def _check_emotional_convergence(self) -> bool:
        """
        Check for Emotional Convergence (Stability)
        检查情绪收敛（稳定性）

        Convergence criteria:
        1. Emotional state stable over convergence window
        2. Intensity variations are small
        3. Minimum iterations reached

        Returns:
            True if emotionally stable
        """
        # Need minimum iterations
        if self.iteration_count < 2:
            return False

        # Need sufficient history
        if len(self.previous_emotional_states) < 2:
            return False

        # Check stability across convergence window
        if len(self.previous_emotional_states) >= self.convergence_window:
            # Check if emotions are consistent
            emotions = [state[0] for state in self.previous_emotional_states]
            intensities = [state[1] for state in self.previous_emotional_states]

            # Check emotion consistency (same primary emotion)
            emotion_consistency = len(set(emotions)) == 1

            # Check intensity stability (low variance)
            if intensities:
                avg_intensity = sum(intensities) / len(intensities)
                intensity_variance = sum((i - avg_intensity) ** 2 for i in intensities) / len(intensities)
                intensity_stable = intensity_variance < 0.05  # Low variance threshold
            else:
                intensity_stable = False

            return emotion_consistency and intensity_stable
        else:
            # Check last two iterations
            if len(self.previous_emotional_states) >= 2:
                last_two = self.previous_emotional_states[-2:]
                return (last_two[0][0] == last_two[1][0] and  # Same emotion
                       abs(last_two[0][1] - last_two[1][1]) < 0.1)  # Similar intensity

        return False

    async def reset_from_prefrontal(self, guidance: Dict[str, Any]) -> None:
        """
        Reset from Prefrontal Cortex (H Module)
        从前额叶皮层重置（H模块）

        Called when H module (prefrontal) sends a reset signal.
        Clears working emotional state and updates guidance.

        Args:
            guidance: Strategic guidance from prefrontal cortex
        """
        self.hrm_metrics['resets_received'] += 1

        logger.info(f"Amygdala receiving reset signal from prefrontal (iteration {self.iteration_count})")

        # Clear working state
        self.working_emotions = []
        self.previous_emotional_states = []
        self.iteration_count = 0
        self.emotional_context = None

        # Update guidance from H module
        self.prefrontal_guidance = guidance

        # Apply emotion regulation if specified
        if 'emotional_regulation' in guidance:
            self.hrm_metrics['emotion_regulations'] += 1

        logger.debug(f"Amygdala reset complete with new guidance: {guidance}")

    def _format_emotional_response(self, result: EmotionalTaggingResult) -> str:
        """
        Format Emotional Tagging Result
        格式化情绪标记结果

        Args:
            result: EmotionalTaggingResult

        Returns:
            Formatted response string
        """
        emotions_str = ', '.join(result.emotion_tags)
        regulation_note = " (regulated)" if result.regulation_applied else ""

        return (f"Emotional assessment: {emotions_str} "
               f"(intensity: {result.intensity:.2f}{regulation_note})")

    def get_hrm_status(self) -> Dict[str, Any]:
        """
        Get HRM-specific status
        获取HRM特定状态

        Returns:
            Status dictionary
        """
        return {
            'iteration_count': self.iteration_count,
            'working_emotions_count': len(self.working_emotions),
            'has_prefrontal_guidance': self.prefrontal_guidance is not None,
            'emotional_convergence': self._check_emotional_convergence(),
            'current_regulation': self.emotional_context.emotion_regulation if self.emotional_context else 'none',
            'stress_level': self.emotional_context.stress_level if self.emotional_context else 0.0,
            'metrics': self.hrm_metrics,
            'emotional_context': {
                'emotion': self.emotional_context.current_emotion if self.emotional_context else 'neutral',
                'intensity': self.emotional_context.intensity if self.emotional_context else 0.0,
                'regulation': self.emotional_context.emotion_regulation if self.emotional_context else 'normal',
                'iteration': self.emotional_context.iteration if self.emotional_context else 0
            } if self.emotional_context else None
        }
