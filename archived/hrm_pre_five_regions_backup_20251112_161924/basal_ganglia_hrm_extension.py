"""
Basal Ganglia Agent HRM Extension - 基底节智能体HRM扩展
Hierarchical Reasoning Model (HRM) Enhancements for Basal Ganglia

Adds HRM's fixed-point detection capabilities:
1. Detect when system reaches stable state (fixed point)
2. Monitor convergence across brain regions
3. Habit formation through repeated patterns
4. Procedural optimization based on convergence patterns

Key Design:
- Monitors system state across iterations
- Detects fixed points (stable states)
- Learns procedural patterns from convergence
- Optimizes future iterations based on history
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
from dataclasses import dataclass
from collections import deque
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class SystemState:
    """
    System State Snapshot
    系统状态快照
    """
    step: int
    region_states: Dict[str, Any]
    state_hash: str
    converged_regions: List[str]


@dataclass
class FixedPoint:
    """
    Fixed Point (Stable State)
    不动点（稳定状态）
    """
    state_hash: str
    first_occurrence: int  # Step when first reached
    occurrences: int  # Number of times reached
    region_states: Dict[str, Any]
    convergence_pattern: Dict[str, bool]


@dataclass
class ConvergencePattern:
    """
    Convergence Pattern (Learned Habit)
    收敛模式（学习到的习惯）
    """
    pattern_id: str
    query_type: str  # Type of query that triggers this pattern
    typical_convergence_steps: int
    typical_fixed_point: str
    confidence: float
    usage_count: int


class BasalGangliaHRMExtension:
    """
    HRM Extension for Basal Ganglia Agent
    基底节智能体的HRM扩展

    Mixin class that adds HRM fixed-point detection to
    the existing BasalGangliaAgent.

    Usage:
        class BasalGangliaAgentV2(BasalGangliaHRMExtension, BasalGangliaAgent):
            pass

    HRM Features:
    1. detect_fixed_point() - Detect stable system states
    2. monitor_convergence() - Track convergence patterns
    3. learn_convergence_patterns() - Learn from repeated patterns
    4. predict_convergence() - Predict when convergence will occur
    """

    def __init__(self, *args, **kwargs):
        """Initialize HRM extension"""
        super().__init__(*args, **kwargs)

        # Fixed-point detection state
        self.state_history: deque = deque(maxlen=20)  # Recent system states
        self.fixed_points: Dict[str, FixedPoint] = {}  # Discovered fixed points

        # Convergence pattern learning
        self.convergence_patterns: Dict[str, ConvergencePattern] = {}  # Learned patterns
        self.current_session_states: List[SystemState] = []  # States in current session

        # Detection parameters
        self.fixed_point_threshold = 3  # Must occur 3+ times to be fixed point
        self.convergence_window = 5  # Check stability over 5 steps

        # Performance metrics
        self.hrm_metrics = {
            'fixed_points_detected': 0,
            'patterns_learned': 0,
            'successful_predictions': 0,
            'total_predictions': 0
        }

        logger.info("BasalGangliaHRMExtension initialized (fixed-point detection)")

    async def monitor_convergence(
        self,
        step: int,
        region_outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Monitor Convergence Across Brain Regions
        监控各脑区的收敛情况

        Called by Thalamus at each step to monitor system state.

        Args:
            step: Current step number
            region_outputs: Outputs from all brain regions

        Returns:
            Dictionary with:
            - is_fixed_point: Whether current state is a fixed point
            - fixed_point_id: ID of fixed point (if detected)
            - convergence_prediction: Predicted steps to convergence
            - stability_score: How stable the system is
        """
        # Create system state snapshot
        state = self._create_state_snapshot(step, region_outputs)

        # Add to history
        self.state_history.append(state)
        self.current_session_states.append(state)

        # Check for fixed point
        is_fixed_point, fixed_point_id = self._detect_fixed_point(state)

        # Calculate stability score
        stability_score = self._calculate_stability_score()

        # Predict convergence
        predicted_steps = self._predict_convergence_steps(state)

        result = {
            'step': step,
            'is_fixed_point': is_fixed_point,
            'fixed_point_id': fixed_point_id,
            'stability_score': stability_score,
            'predicted_convergence_steps': predicted_steps,
            'converged_regions': state.converged_regions
        }

        logger.debug(f"Basal Ganglia monitoring step {step}: "
                    f"fixed_point={is_fixed_point}, stability={stability_score:.2f}")

        return result

    def _create_state_snapshot(
        self,
        step: int,
        region_outputs: Dict[str, Any]
    ) -> SystemState:
        """
        Create snapshot of current system state
        创建当前系统状态的快照

        Args:
            step: Current step
            region_outputs: Outputs from regions

        Returns:
            SystemState object
        """
        # Extract region states
        region_states = {}
        converged_regions = []

        for region_name, output in region_outputs.items():
            if isinstance(output, dict):
                # Extract key indicators
                region_states[region_name] = {
                    'converged': output.get('converged', False),
                    'has_output': bool(output.get('response') or output.get('memories')),
                    'output_size': len(str(output))
                }

                if output.get('converged'):
                    converged_regions.append(region_name)
            else:
                region_states[region_name] = {
                    'converged': False,
                    'has_output': bool(output),
                    'output_size': len(str(output))
                }

        # Create state hash for fixed-point detection
        state_hash = self._hash_state(region_states)

        return SystemState(
            step=step,
            region_states=region_states,
            state_hash=state_hash,
            converged_regions=converged_regions
        )

    def _hash_state(self, region_states: Dict[str, Any]) -> str:
        """
        Create hash of system state
        创建系统状态的哈希值

        Args:
            region_states: Region states dictionary

        Returns:
            State hash string
        """
        # Create stable string representation
        state_str = ""

        for region_name in sorted(region_states.keys()):
            state = region_states[region_name]
            state_str += f"{region_name}:"
            state_str += f"converged={state.get('converged')},"
            state_str += f"has_output={state.get('has_output')};"

        # Hash it
        return hashlib.md5(state_str.encode()).hexdigest()[:12]

    def _detect_fixed_point(self, current_state: SystemState) -> Tuple[bool, Optional[str]]:
        """
        Detect if current state is a fixed point
        检测当前状态是否为不动点

        A state is a fixed point if:
        1. It has occurred multiple times
        2. System returns to it repeatedly
        3. It's stable (persists across steps)

        Args:
            current_state: Current system state

        Returns:
            Tuple of (is_fixed_point, fixed_point_id)
        """
        state_hash = current_state.state_hash

        # Check if this state exists in fixed points
        if state_hash in self.fixed_points:
            fixed_point = self.fixed_points[state_hash]
            fixed_point.occurrences += 1

            logger.info(f"Returned to fixed point {state_hash} "
                       f"(occurrence #{fixed_point.occurrences})")

            return True, state_hash

        # Check if this state has occurred recently
        recent_occurrences = sum(
            1 for s in self.state_history
            if s.state_hash == state_hash
        )

        if recent_occurrences >= self.fixed_point_threshold:
            # New fixed point detected!
            self._register_fixed_point(current_state, recent_occurrences)
            return True, state_hash

        return False, None

    def _register_fixed_point(
        self,
        state: SystemState,
        occurrences: int
    ) -> None:
        """
        Register a newly discovered fixed point
        注册新发现的不动点

        Args:
            state: System state
            occurrences: Number of times it occurred
        """
        state_hash = state.state_hash

        convergence_pattern = {
            region: state.region_states[region].get('converged', False)
            for region in state.region_states.keys()
        }

        fixed_point = FixedPoint(
            state_hash=state_hash,
            first_occurrence=state.step - occurrences + 1,
            occurrences=occurrences,
            region_states=state.region_states,
            convergence_pattern=convergence_pattern
        )

        self.fixed_points[state_hash] = fixed_point
        self.hrm_metrics['fixed_points_detected'] += 1

        logger.info(f"✅ Fixed point detected: {state_hash} "
                   f"(first at step {fixed_point.first_occurrence}, "
                   f"{occurrences} occurrences)")

    def _calculate_stability_score(self) -> float:
        """
        Calculate stability score based on recent history
        基于近期历史计算稳定性分数

        Returns:
            Stability score (0.0 to 1.0)
        """
        if len(self.state_history) < 2:
            return 0.0

        # Check how many unique states in recent history
        recent_states = list(self.state_history)[-self.convergence_window:]
        unique_hashes = set(s.state_hash for s in recent_states)

        # Fewer unique states = more stable
        stability = 1.0 - (len(unique_hashes) - 1) / max(1, len(recent_states))

        return max(0.0, min(1.0, stability))

    def _predict_convergence_steps(self, current_state: SystemState) -> Optional[int]:
        """
        Predict how many steps until convergence
        预测到收敛还需多少步

        Uses learned patterns to predict convergence.

        Args:
            current_state: Current system state

        Returns:
            Predicted steps (or None if can't predict)
        """
        self.hrm_metrics['total_predictions'] += 1

        # Check if we've seen similar patterns before
        matching_pattern = self._find_matching_pattern(current_state)

        if matching_pattern:
            # Use learned pattern to predict
            current_step = current_state.step
            typical_steps = matching_pattern.typical_convergence_steps

            # Predict remaining steps
            if current_step < typical_steps:
                predicted = typical_steps - current_step
                self.hrm_metrics['successful_predictions'] += 1
                return predicted

        # No matching pattern - use heuristics
        num_converged = len(current_state.converged_regions)
        total_regions = len(current_state.region_states)

        if total_regions == 0:
            return None

        convergence_ratio = num_converged / total_regions

        if convergence_ratio > 0.8:
            return 1  # Almost done
        elif convergence_ratio > 0.5:
            return 3  # Halfway there
        else:
            return 5  # Still early

    def _find_matching_pattern(
        self,
        current_state: SystemState
    ) -> Optional[ConvergencePattern]:
        """
        Find matching convergence pattern from learned patterns
        从学习到的模式中找到匹配的收敛模式

        Args:
            current_state: Current system state

        Returns:
            Matching ConvergencePattern or None
        """
        # Simple matching: check if convergence pattern is similar
        current_convergence = {
            region: state.get('converged', False)
            for region, state in current_state.region_states.items()
        }

        best_match = None
        best_similarity = 0.0

        for pattern_id, pattern in self.convergence_patterns.items():
            # Compare convergence patterns
            # (In production, use more sophisticated matching)

            similarity = 0.5  # Placeholder

            if similarity > best_similarity and similarity > 0.7:
                best_similarity = similarity
                best_match = pattern

        return best_match

    async def learn_convergence_pattern(
        self,
        query_type: str,
        convergence_step: int
    ) -> None:
        """
        Learn convergence pattern from completed session
        从完成的会话中学习收敛模式

        Called at end of successful convergence to learn pattern.

        Args:
            query_type: Type of query that was processed
            convergence_step: Step at which convergence occurred
        """
        if not self.current_session_states:
            return

        # Extract pattern from session
        final_state = self.current_session_states[-1]

        # Create pattern ID based on convergence characteristics
        pattern_id = self._generate_pattern_id(query_type, final_state)

        # Check if pattern exists
        if pattern_id in self.convergence_patterns:
            # Update existing pattern
            pattern = self.convergence_patterns[pattern_id]
            pattern.usage_count += 1

            # Update typical steps (moving average)
            alpha = 0.3  # Learning rate
            pattern.typical_convergence_steps = int(
                alpha * convergence_step +
                (1 - alpha) * pattern.typical_convergence_steps
            )

            # Update confidence
            pattern.confidence = min(1.0, pattern.confidence + 0.05)

            logger.debug(f"Updated convergence pattern {pattern_id} "
                        f"(usage #{pattern.usage_count})")
        else:
            # Create new pattern
            pattern = ConvergencePattern(
                pattern_id=pattern_id,
                query_type=query_type,
                typical_convergence_steps=convergence_step,
                typical_fixed_point=final_state.state_hash,
                confidence=0.5,  # Initial confidence
                usage_count=1
            )

            self.convergence_patterns[pattern_id] = pattern
            self.hrm_metrics['patterns_learned'] += 1

            logger.info(f"✅ Learned new convergence pattern: {pattern_id} "
                       f"(converges at ~{convergence_step} steps)")

        # Clear session states
        self.current_session_states = []

    def _generate_pattern_id(
        self,
        query_type: str,
        final_state: SystemState
    ) -> str:
        """
        Generate pattern ID from query type and final state
        从查询类型和最终状态生成模式ID

        Args:
            query_type: Type of query
            final_state: Final system state

        Returns:
            Pattern ID string
        """
        # Create pattern signature
        converged = sorted(final_state.converged_regions)
        signature = f"{query_type}:{'_'.join(converged)}"

        # Hash it for compact ID
        return hashlib.md5(signature.encode()).hexdigest()[:8]

    def get_hrm_status(self) -> Dict[str, Any]:
        """
        Get HRM-specific status
        获取HRM特定状态

        Returns:
            Status dictionary
        """
        return {
            'num_fixed_points': len(self.fixed_points),
            'num_learned_patterns': len(self.convergence_patterns),
            'current_stability': self._calculate_stability_score(),
            'metrics': self.hrm_metrics,
            'fixed_points': [
                {
                    'id': fp.state_hash,
                    'occurrences': fp.occurrences,
                    'first_at_step': fp.first_occurrence
                }
                for fp in list(self.fixed_points.values())[:5]  # Top 5
            ],
            'learned_patterns': [
                {
                    'id': p.pattern_id,
                    'query_type': p.query_type,
                    'typical_steps': p.typical_convergence_steps,
                    'confidence': p.confidence,
                    'usage': p.usage_count
                }
                for p in list(self.convergence_patterns.values())[:5]  # Top 5
            ]
        }

    def reset_session(self) -> None:
        """Reset session state for new query"""
        self.current_session_states = []
        logger.debug("Basal Ganglia session reset")
