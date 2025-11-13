"""
Anterior Cingulate Cortex Agent: Adaptive Computation Time
前扣带回皮层智能体：自适应计算时间

Inspired by HRM's ACT (Adaptive Computation Time) mechanism, the ACC decides
when to stop iterative thinking processes based on cost-benefit analysis.

Key Features:
1. Confidence evaluation (how certain is the current answer?)
2. Expected gain estimation (how much will more thinking help?)
3. Cost calculation (computational cost of continuing)
4. Halting decision (should we stop or continue?)
"""

from typing import Dict, Any, Optional, Tuple, List
import logging
import math
from dataclasses import dataclass
from enum import Enum

from src.core.interfaces.agent_interface import IAgent

logger = logging.getLogger(__name__)


class ThinkingMode(Enum):
    """
    Thinking Mode Classification
    思考模式分类
    """
    FAST_RESPONSE = "fast"           # Quick, intuitive answers
    DELIBERATE = "deliberate"        # Careful, analytical thinking
    CREATIVE = "creative"            # Open-ended exploration
    VERIFICATION = "verification"    # Double-checking results


@dataclass
class ThinkingState:
    """
    Current Thinking State
    当前思考状态
    """
    iteration: int
    confidence: float
    expected_gain: float
    cost: float
    converged: bool
    mode: ThinkingMode
    evidence: Dict[str, Any]


class AnteriorCingulateAgent(IAgent):
    """
    Anterior Cingulate Cortex Agent: Adaptive Computation Control
    前扣带回皮层智能体：自适应计算控制

    Implements HRM's ACT mechanism - decides when to stop thinking.

    Neuroscience Background:
    - ACC monitors conflicts and errors
    - Signals when more cognitive control is needed
    - Modulates effort allocation

    Computational Role:
    1. Evaluate confidence in current answer
    2. Estimate expected gain from more thinking
    3. Calculate cost of continuing
    4. Make halting decision

    Architecture:
        - Input: Current system state from all brain regions
        - Output: continue_thinking (bool), confidence (float), reasoning (str)

    Example:
        >>> acc = AnteriorCingulateAgent()
        >>> should_continue, confidence = await acc.should_continue_thinking(
        ...     current_state={'hippocampus_output': ..., 'prefrontal_output': ...},
        ...     iteration=5
        ... )
        >>> if not should_continue:
        ...     # Stop thinking, return current answer
        ...     pass
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Anterior Cingulate Agent
        初始化前扣带回智能体

        Args:
            config: Optional configuration for thresholds and parameters
        """
        self.config = config or {}

        # ACT parameters
        self.confidence_threshold = self.config.get('confidence_threshold', 0.90)
        self.min_iterations = self.config.get('min_iterations', 3)
        self.max_iterations = self.config.get('max_iterations', 20)
        self.cost_weight = self.config.get('cost_weight', 0.1)

        # Thinking state history
        self.history: List[ThinkingState] = []

        # Performance metrics
        self.metrics = {
            'total_decisions': 0,
            'early_stops': 0,
            'max_iteration_stops': 0,
            'confidence_stops': 0,
            'avg_iterations': 0.0
        }

        logger.info("AnteriorCingulateAgent initialized with ACT mechanism")

    async def process(self, user_input: str) -> str:
        """
        Process user input (for compatibility)
        处理用户输入（兼容性）

        Args:
            user_input: User query

        Returns:
            Response string
        """
        # ACC doesn't directly process queries - it monitors other regions
        return "ACC: Monitoring cognitive control"

    async def should_continue_thinking(
        self,
        current_state: Dict[str, Any],
        iteration: int,
        max_iterations: Optional[int] = None
    ) -> Tuple[bool, float, str]:
        """
        Decide whether to continue thinking (HRM's ACT)
        决定是否继续思考（HRM的ACT机制）

        Implements the core ACT decision:
        continue = (expected_gain > cost) AND (iteration < max) AND (confidence < threshold)

        Args:
            current_state: Current system state from all brain regions
            iteration: Current iteration number
            max_iterations: Override max iterations

        Returns:
            Tuple of (should_continue, confidence, reasoning)
        """
        self.metrics['total_decisions'] += 1
        max_iter = max_iterations or self.max_iterations

        logger.debug(f"ACC evaluating at iteration {iteration}")

        # Step 1: Evaluate confidence in current answer
        confidence = await self._evaluate_confidence(current_state)

        # Step 2: Estimate expected gain from more thinking
        expected_gain = await self._estimate_expected_gain(
            current_state, iteration, confidence
        )

        # Step 3: Calculate cost of continuing
        cost = self._calculate_cost(iteration, max_iter)

        # Step 4: Make halting decision
        should_continue, reasoning = self._make_halting_decision(
            confidence, expected_gain, cost, iteration, max_iter
        )

        # Step 5: Record thinking state
        thinking_mode = self._classify_thinking_mode(current_state)
        state = ThinkingState(
            iteration=iteration,
            confidence=confidence,
            expected_gain=expected_gain,
            cost=cost,
            converged=not should_continue,
            mode=thinking_mode,
            evidence=self._extract_evidence(current_state)
        )
        self.history.append(state)

        # Update metrics
        if not should_continue:
            self._update_stop_metrics(reasoning)

        logger.info(f"ACC Decision at iter {iteration}: continue={should_continue}, "
                   f"confidence={confidence:.3f}, gain={expected_gain:.3f}, cost={cost:.3f}")

        return should_continue, confidence, reasoning

    async def _evaluate_confidence(self, current_state: Dict[str, Any]) -> float:
        """
        Evaluate confidence in current answer
        评估当前答案的置信度

        Confidence indicators:
        1. Agreement between brain regions (inter-region consistency)
        2. Stability of outputs over recent iterations
        3. Presence of clear evidence/memories
        4. Absence of conflicts or ambiguities

        Args:
            current_state: Current system state

        Returns:
            Confidence score (0.0 to 1.0)
        """
        confidence_scores = []

        # 1. Inter-region agreement
        region_agreement = self._measure_region_agreement(current_state)
        confidence_scores.append(region_agreement)

        # 2. Output stability (if we have history)
        if len(self.history) >= 2:
            stability = self._measure_output_stability()
            confidence_scores.append(stability)
        else:
            # Early iterations: lower confidence
            confidence_scores.append(0.5)

        # 3. Evidence quality
        evidence_quality = self._measure_evidence_quality(current_state)
        confidence_scores.append(evidence_quality)

        # 4. Conflict detection
        has_conflicts = self._detect_conflicts(current_state)
        conflict_penalty = 0.3 if has_conflicts else 0.0
        confidence_scores.append(1.0 - conflict_penalty)

        # Combine scores (weighted average)
        weights = [0.35, 0.25, 0.25, 0.15]  # Agreement > Stability > Evidence > Conflicts
        confidence = sum(s * w for s, w in zip(confidence_scores, weights))

        return max(0.0, min(1.0, confidence))

    def _measure_region_agreement(self, current_state: Dict[str, Any]) -> float:
        """
        Measure agreement between brain regions
        测量脑区间的一致性

        Args:
            current_state: Current system state

        Returns:
            Agreement score (0.0 to 1.0)
        """
        region_outputs = current_state.get('region_outputs', {})

        if len(region_outputs) < 2:
            return 0.5  # Need at least 2 regions to measure agreement

        # Extract responses/outputs
        responses = []
        for region_name, output in region_outputs.items():
            if isinstance(output, dict):
                response = output.get('response') or output.get('strategy') or str(output)
            else:
                response = str(output)
            responses.append(response)

        # Simple agreement heuristic: check for common keywords
        # In production, use semantic similarity (embeddings)
        if not responses:
            return 0.5

        # Count common words across responses
        word_sets = [set(str(r).lower().split()) for r in responses]
        if not word_sets:
            return 0.5

        common_words = set.intersection(*word_sets)
        total_unique_words = len(set.union(*word_sets))

        if total_unique_words == 0:
            return 0.5

        agreement = len(common_words) / total_unique_words
        return min(1.0, agreement * 2)  # Scale up (common words are usually small fraction)

    def _measure_output_stability(self) -> float:
        """
        Measure stability of outputs over recent iterations
        测量近期迭代输出的稳定性

        Returns:
            Stability score (0.0 to 1.0)
        """
        if len(self.history) < 2:
            return 0.5

        # Look at last 3 iterations
        recent = self.history[-3:]

        # Check if confidence is increasing or plateauing
        confidences = [state.confidence for state in recent]

        if len(confidences) < 2:
            return 0.5

        # Stability = low variance + positive or flat trend
        variance = sum((c - sum(confidences)/len(confidences))**2 for c in confidences) / len(confidences)
        stability_from_variance = max(0, 1.0 - variance * 5)  # Scale variance

        # Check if converging (confidence increasing)
        trend = confidences[-1] - confidences[0]
        stability_from_trend = 0.5 + trend * 0.5  # Range: 0 to 1

        return (stability_from_variance + stability_from_trend) / 2

    def _measure_evidence_quality(self, current_state: Dict[str, Any]) -> float:
        """
        Measure quality of evidence in current state
        测量当前状态中证据的质量

        Args:
            current_state: Current system state

        Returns:
            Evidence quality score (0.0 to 1.0)
        """
        region_outputs = current_state.get('region_outputs', {})

        # Check for specific evidence types
        has_memories = any(
            'memories' in str(output).lower() or 'retrieved' in str(output).lower()
            for output in region_outputs.values()
        )

        has_strategy = any(
            'strategy' in output or 'plan' in str(output).lower()
            for output in region_outputs.values()
            if isinstance(output, dict)
        )

        has_detailed_response = any(
            len(str(output)) > 50  # Non-trivial outputs
            for output in region_outputs.values()
        )

        # Combine indicators
        quality_score = sum([has_memories, has_strategy, has_detailed_response]) / 3.0

        return quality_score

    def _detect_conflicts(self, current_state: Dict[str, Any]) -> bool:
        """
        Detect conflicts or contradictions in current state
        检测当前状态中的冲突或矛盾

        Args:
            current_state: Current system state

        Returns:
            True if conflicts detected
        """
        region_outputs = current_state.get('region_outputs', {})

        # Check for explicit error messages
        has_errors = any(
            'error' in str(output).lower() or 'fail' in str(output).lower()
            for output in region_outputs.values()
        )

        # Check for contradictory signals (e.g., high emotion + logical processing)
        # This is simplified - in production, use more sophisticated conflict detection

        return has_errors

    async def _estimate_expected_gain(
        self,
        current_state: Dict[str, Any],
        iteration: int,
        confidence: float
    ) -> float:
        """
        Estimate expected gain from more thinking
        估计更多思考的预期收益

        Expected gain depends on:
        1. Current confidence (low confidence → high potential gain)
        2. Iteration number (early iterations → high gain)
        3. Evidence of progress (improving → high gain)

        Args:
            current_state: Current system state
            iteration: Current iteration
            confidence: Current confidence level

        Returns:
            Expected gain score (0.0 to 1.0)
        """
        # 1. Gain from confidence gap
        confidence_gap = 1.0 - confidence
        gain_from_confidence = confidence_gap * 0.7  # High weight

        # 2. Gain decreases with iterations (diminishing returns)
        iteration_factor = math.exp(-iteration / 10.0)  # Exponential decay
        gain_from_iteration = iteration_factor * 0.3

        # 3. Check if making progress (if we have history)
        if len(self.history) >= 2:
            recent_confidence_increase = self.history[-1].confidence - self.history[-2].confidence
            if recent_confidence_increase > 0.05:
                # Making good progress → expect more gain
                progress_bonus = 0.2
            else:
                # Plateauing → lower expected gain
                progress_bonus = 0.0
        else:
            progress_bonus = 0.1  # Early on, assume moderate potential

        expected_gain = gain_from_confidence + gain_from_iteration + progress_bonus

        return max(0.0, min(1.0, expected_gain))

    def _calculate_cost(self, iteration: int, max_iterations: int) -> float:
        """
        Calculate cost of continuing thinking
        计算继续思考的成本

        Cost increases with:
        1. Number of iterations (computational cost)
        2. Proximity to max iterations (time pressure)

        Args:
            iteration: Current iteration
            max_iterations: Maximum allowed iterations

        Returns:
            Cost score (0.0 to 1.0)
        """
        # Linear cost increase with iterations
        iteration_cost = iteration / max_iterations

        # Quadratic increase near max iterations (urgency)
        urgency_multiplier = (iteration / max_iterations) ** 2

        total_cost = (iteration_cost * 0.6 + urgency_multiplier * 0.4) * self.cost_weight

        return max(0.0, min(1.0, total_cost))

    def _make_halting_decision(
        self,
        confidence: float,
        expected_gain: float,
        cost: float,
        iteration: int,
        max_iterations: int
    ) -> Tuple[bool, str]:
        """
        Make halting decision based on ACT criterion
        基于ACT准则做出停止决策

        ACT criterion: continue = (expected_gain > cost) AND (iteration < max) AND (confidence < threshold)

        Args:
            confidence: Current confidence
            expected_gain: Expected gain from continuing
            cost: Cost of continuing
            iteration: Current iteration
            max_iterations: Max iterations

        Returns:
            Tuple of (should_continue, reasoning)
        """
        # Minimum iterations check
        if iteration < self.min_iterations:
            return True, f"Below minimum iterations ({self.min_iterations})"

        # Maximum iterations check
        if iteration >= max_iterations:
            self.metrics['max_iteration_stops'] += 1
            return False, f"Reached maximum iterations ({max_iterations})"

        # Confidence check
        if confidence >= self.confidence_threshold:
            self.metrics['confidence_stops'] += 1
            return False, f"High confidence ({confidence:.3f} >= {self.confidence_threshold})"

        # ACT cost-benefit check
        net_benefit = expected_gain - cost

        if net_benefit <= 0:
            self.metrics['early_stops'] += 1
            return False, f"Low net benefit ({net_benefit:.3f} <= 0)"

        # Continue thinking
        return True, f"Net benefit positive ({net_benefit:.3f} > 0)"

    def _classify_thinking_mode(self, current_state: Dict[str, Any]) -> ThinkingMode:
        """
        Classify current thinking mode
        分类当前思考模式

        Args:
            current_state: Current system state

        Returns:
            ThinkingMode enum
        """
        # Simple heuristics for now
        # In production, use more sophisticated classification

        region_outputs = current_state.get('region_outputs', {})

        # Check for prefrontal activity (strategic thinking)
        has_prefrontal = any('prefrontal' in name.lower() for name in region_outputs.keys())

        # Check for hippocampus activity (memory retrieval)
        has_hippocampus = any('hippocampus' in name.lower() for name in region_outputs.keys())

        # Check for amygdala activity (emotional processing)
        has_amygdala = any('amygdala' in name.lower() for name in region_outputs.keys())

        if has_prefrontal and not has_hippocampus:
            return ThinkingMode.DELIBERATE
        elif has_hippocampus and has_amygdala:
            return ThinkingMode.FAST_RESPONSE
        elif len(region_outputs) > 3:
            return ThinkingMode.CREATIVE
        else:
            return ThinkingMode.VERIFICATION

    def _extract_evidence(self, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract evidence from current state for record-keeping
        从当前状态提取证据用于记录

        Args:
            current_state: Current system state

        Returns:
            Evidence dictionary
        """
        region_outputs = current_state.get('region_outputs', {})

        return {
            'num_regions_active': len(region_outputs),
            'regions': list(region_outputs.keys()),
            'has_memories': any('memories' in str(o).lower() for o in region_outputs.values()),
            'has_strategy': any('strategy' in str(o).lower() for o in region_outputs.values())
        }

    def _update_stop_metrics(self, reasoning: str) -> None:
        """
        Update stop metrics based on reasoning
        基于推理原因更新停止指标

        Args:
            reasoning: Stop reasoning string
        """
        # Metrics already updated in _make_halting_decision
        # Update average iterations
        total_stops = (self.metrics['early_stops'] +
                      self.metrics['max_iteration_stops'] +
                      self.metrics['confidence_stops'])

        if total_stops > 0:
            total_iterations = sum(state.iteration for state in self.history if state.converged)
            self.metrics['avg_iterations'] = total_iterations / total_stops

    def get_thinking_history(self) -> List[Dict[str, Any]]:
        """
        Get thinking history for analysis
        获取思考历史用于分析

        Returns:
            List of thinking state dictionaries
        """
        return [
            {
                'iteration': state.iteration,
                'confidence': state.confidence,
                'expected_gain': state.expected_gain,
                'cost': state.cost,
                'converged': state.converged,
                'mode': state.mode.value,
                'evidence': state.evidence
            }
            for state in self.history
        ]

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get ACC system status
        获取ACC系统状态

        Returns:
            Status dictionary
        """
        return {
            'metrics': self.metrics,
            'history_length': len(self.history),
            'current_confidence': self.history[-1].confidence if self.history else 0.0,
            'config': {
                'confidence_threshold': self.confidence_threshold,
                'min_iterations': self.min_iterations,
                'max_iterations': self.max_iterations,
                'cost_weight': self.cost_weight
            }
        }

    def reset_history(self) -> None:
        """Reset thinking history for new query"""
        self.history = []

    def __repr__(self) -> str:
        """String representation"""
        return (f"AnteriorCingulateAgent(threshold={self.confidence_threshold}, "
                f"history={len(self.history)})")
