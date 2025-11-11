"""
Prefrontal Agent HRM Extension - 前额叶智能体HRM扩展
Hierarchical Reasoning Model (HRM) Enhancements for Prefrontal Cortex

Adds HRM's H module (slow, strategic) capabilities:
1. Slow timescale updates (every T steps)
2. Strategic planning and high-level reasoning
3. State reset signals to fast regions (L module)
4. Hierarchical dimensionality (abstract representations)

Key Design:
- H module: Updates every T=10 steps with strategic planning
- Sends reset signals to L modules (Hippocampus, Amygdala)
- Provides high-level guidance to fast regions
- Maintains abstract task representations
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StrategicPlan:
    """
    Strategic Plan (H Module Output)
    战略规划（H模块输出）
    """
    goal: str
    subgoals: List[str]
    guidance_for_hippocampus: Dict[str, Any]
    guidance_for_amygdala: Dict[str, Any]
    expected_duration: int  # Expected steps to completion
    confidence: float


@dataclass
class ResetSignal:
    """
    Reset Signal from H to L Module
    从H模块到L模块的重置信号
    """
    target_region: str
    action: str  # 'reset_working_memory', 'reset_emotional_state', etc.
    guidance: Dict[str, Any]
    priority: int


class PrefrontalHRMExtension:
    """
    HRM Extension for Prefrontal Cortex Agent
    前额叶智能体的HRM扩展

    Mixin class that adds HRM H module (slow) capabilities to
    the existing PrefrontalAgent.

    Usage:
        class PrefrontalAgentV2(PrefrontalHRMExtension, PrefrontalAgent):
            pass

    HRM Features:
    1. strategic_update() - Slow timescale strategic planning
    2. generate_reset_signals() - Send guidance to fast regions
    3. abstract_representation() - Hierarchical dimensionality
    4. evaluate_global_progress() - Monitor overall task progress
    """

    def __init__(self, *args, **kwargs):
        """Initialize HRM extension"""
        super().__init__(*args, **kwargs)

        # HRM-specific state
        self.strategic_plan: Optional[StrategicPlan] = None
        self.last_strategic_update_step = -1
        self.strategic_update_interval = 10  # T = 10 steps (H module timescale)

        # Abstract task representation
        self.abstract_task_state: Dict[str, Any] = {
            'current_goal': None,
            'subgoals_completed': [],
            'subgoals_remaining': [],
            'global_progress': 0.0
        }

        # Reset signals history
        self.reset_signals_sent: List[ResetSignal] = []

        logger.info("PrefrontalHRMExtension initialized (H module, slow timescale)")

    async def strategic_update(
        self,
        global_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Strategic Update (H Module - Slow Timescale)
        战略更新（H模块 - 慢时间尺度）

        Called every T=10 steps by Thalamus.
        Performs high-level reasoning and planning.

        Args:
            global_context: Context from all brain regions

        Returns:
            Dictionary with:
            - strategy: StrategicPlan
            - reset_signals: Dict of reset signals to send to L modules
            - abstract_state: Updated abstract task state
        """
        current_step = global_context.get('step', 0)
        logger.info(f"Prefrontal H module strategic update at step {current_step}")

        # Step 1: Analyze global situation
        situation_analysis = await self._analyze_global_situation(global_context)

        # Step 2: Generate strategic plan
        strategy = await self._generate_strategic_plan(situation_analysis, global_context)
        self.strategic_plan = strategy

        # Step 3: Generate reset signals for L modules
        reset_signals = self._generate_reset_signals(strategy)

        # Step 4: Update abstract task representation
        self._update_abstract_state(strategy, global_context)

        # Step 5: Record update
        self.last_strategic_update_step = current_step

        return {
            'strategy': {
                'goal': strategy.goal,
                'subgoals': strategy.subgoals,
                'expected_duration': strategy.expected_duration,
                'confidence': strategy.confidence
            },
            'reset_signals': reset_signals,
            'abstract_state': self.abstract_task_state.copy(),
            'situation_analysis': situation_analysis
        }

    async def _analyze_global_situation(
        self,
        global_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze global situation across all brain regions
        分析所有脑区的全局情况

        Args:
            global_context: Context from all regions

        Returns:
            Situation analysis dictionary
        """
        region_outputs = global_context.get('region_outputs', {})

        # Analyze each region's state
        hippocampus_state = self._extract_region_state(
            region_outputs.get('hippocampus', {}),
            'memory_retrieval'
        )

        amygdala_state = self._extract_region_state(
            region_outputs.get('amygdala', {}),
            'emotional_processing'
        )

        basal_ganglia_state = self._extract_region_state(
            region_outputs.get('basal_ganglia', {}),
            'habit_formation'
        )

        # Identify bottlenecks and opportunities
        bottlenecks = []
        if hippocampus_state.get('converged') == False:
            bottlenecks.append('memory_retrieval_incomplete')

        if amygdala_state.get('emotional_conflict'):
            bottlenecks.append('emotional_conflict')

        # Assess overall progress
        overall_progress = self._assess_overall_progress(global_context)

        return {
            'hippocampus': hippocampus_state,
            'amygdala': amygdala_state,
            'basal_ganglia': basal_ganglia_state,
            'bottlenecks': bottlenecks,
            'overall_progress': overall_progress,
            'step': global_context.get('step', 0)
        }

    def _extract_region_state(
        self,
        region_output: Dict[str, Any],
        region_type: str
    ) -> Dict[str, Any]:
        """
        Extract state from region output
        从脑区输出中提取状态

        Args:
            region_output: Output from brain region
            region_type: Type of region

        Returns:
            Extracted state dictionary
        """
        if not region_output:
            return {'active': False}

        state = {
            'active': True,
            'converged': region_output.get('converged', False),
            'output_length': len(str(region_output)),
            'has_response': 'response' in region_output
        }

        # Region-specific extraction
        if region_type == 'memory_retrieval':
            state['memories_retrieved'] = 'memories' in region_output
            state['num_memories'] = len(region_output.get('memories', []))

        elif region_type == 'emotional_processing':
            state['emotional_conflict'] = 'conflict' in str(region_output).lower()
            state['emotional_valence'] = region_output.get('valence', 0.0)

        return state

    def _assess_overall_progress(self, global_context: Dict[str, Any]) -> float:
        """
        Assess overall task progress
        评估整体任务进展

        Args:
            global_context: Global context

        Returns:
            Progress score (0.0 to 1.0)
        """
        # Check convergence of fast regions
        converged_regions = global_context.get('converged_regions', [])
        total_regions = len(global_context.get('region_outputs', {}))

        if total_regions == 0:
            return 0.0

        convergence_ratio = len(converged_regions) / total_regions

        # Check subgoal completion
        if self.abstract_task_state['subgoals_remaining']:
            total_subgoals = (len(self.abstract_task_state['subgoals_completed']) +
                            len(self.abstract_task_state['subgoals_remaining']))
            subgoal_ratio = len(self.abstract_task_state['subgoals_completed']) / max(1, total_subgoals)
        else:
            subgoal_ratio = 0.5  # No subgoals defined yet

        # Combine metrics
        overall = (convergence_ratio * 0.6 + subgoal_ratio * 0.4)

        return overall

    async def _generate_strategic_plan(
        self,
        situation_analysis: Dict[str, Any],
        global_context: Dict[str, Any]
    ) -> StrategicPlan:
        """
        Generate strategic plan based on situation analysis
        基于情况分析生成战略规划

        Args:
            situation_analysis: Analysis of current situation
            global_context: Global context

        Returns:
            StrategicPlan object
        """
        query = global_context.get('query', '')

        # Extract current goal from query or existing state
        if self.abstract_task_state['current_goal']:
            goal = self.abstract_task_state['current_goal']
        else:
            goal = self._extract_goal_from_query(query)

        # Generate subgoals based on bottlenecks and progress
        subgoals = self._generate_subgoals(goal, situation_analysis)

        # Determine guidance for each L module
        guidance_hippocampus = {
            'search_strategy': self._determine_search_strategy(situation_analysis),
            'focus_areas': self._identify_focus_areas(query),
            'confidence_threshold': 0.8
        }

        guidance_amygdala = {
            'emotional_regulation': 'high' if situation_analysis.get('bottlenecks') else 'normal',
            'priority_signals': self._identify_priority_signals(situation_analysis)
        }

        # Estimate expected duration
        expected_duration = len(subgoals) * 3  # ~3 fast steps per subgoal

        # Confidence based on situation clarity
        confidence = self._calculate_strategy_confidence(situation_analysis)

        return StrategicPlan(
            goal=goal,
            subgoals=subgoals,
            guidance_for_hippocampus=guidance_hippocampus,
            guidance_for_amygdala=guidance_amygdala,
            expected_duration=expected_duration,
            confidence=confidence
        )

    def _extract_goal_from_query(self, query: str) -> str:
        """
        Extract high-level goal from query
        从查询中提取高级目标

        Args:
            query: User query

        Returns:
            Extracted goal string
        """
        # Simple extraction - in production use NLP
        if '?' in query:
            return f"Answer question: {query[:50]}"
        elif any(word in query.lower() for word in ['create', 'generate', 'make']):
            return f"Create: {query[:50]}"
        elif any(word in query.lower() for word in ['find', 'search', 'retrieve']):
            return f"Retrieve: {query[:50]}"
        else:
            return f"Process: {query[:50]}"

    def _generate_subgoals(
        self,
        goal: str,
        situation_analysis: Dict[str, Any]
    ) -> List[str]:
        """
        Generate subgoals for achieving main goal
        生成达成主目标的子目标

        Args:
            goal: Main goal
            situation_analysis: Situation analysis

        Returns:
            List of subgoals
        """
        subgoals = []

        # Based on bottlenecks
        bottlenecks = situation_analysis.get('bottlenecks', [])

        if 'memory_retrieval_incomplete' in bottlenecks:
            subgoals.append("Retrieve relevant memories")

        if 'emotional_conflict' in bottlenecks:
            subgoals.append("Resolve emotional conflicts")

        # Always add response generation as final subgoal
        if 'Answer' in goal:
            subgoals.extend([
                "Gather information",
                "Synthesize answer",
                "Verify accuracy"
            ])
        elif 'Create' in goal:
            subgoals.extend([
                "Plan structure",
                "Generate content",
                "Review output"
            ])
        else:
            subgoals.append("Complete primary objective")

        return subgoals[:5]  # Limit to 5 subgoals

    def _determine_search_strategy(self, situation_analysis: Dict[str, Any]) -> str:
        """
        Determine search strategy for hippocampus
        确定海马体的搜索策略

        Args:
            situation_analysis: Situation analysis

        Returns:
            Strategy string
        """
        hippocampus_state = situation_analysis.get('hippocampus', {})

        if hippocampus_state.get('num_memories', 0) < 3:
            return 'broad_search'  # Need more memories
        elif not hippocampus_state.get('converged'):
            return 'focused_refinement'  # Narrow down
        else:
            return 'verification'  # Double-check

    def _identify_focus_areas(self, query: str) -> List[str]:
        """
        Identify focus areas for memory retrieval
        识别记忆检索的焦点区域

        Args:
            query: User query

        Returns:
            List of focus areas
        """
        # Simple keyword extraction - in production use NLP
        focus_areas = []

        keywords = query.lower().split()
        important_words = [w for w in keywords if len(w) > 4]

        return important_words[:3]  # Top 3 important words

    def _identify_priority_signals(self, situation_analysis: Dict[str, Any]) -> List[str]:
        """
        Identify priority signals for amygdala
        识别杏仁核的优先信号

        Args:
            situation_analysis: Situation analysis

        Returns:
            List of priority signals
        """
        signals = []

        if 'emotional_conflict' in situation_analysis.get('bottlenecks', []):
            signals.append('resolve_conflict')

        if situation_analysis.get('overall_progress', 0) < 0.3:
            signals.append('increase_attention')

        return signals

    def _calculate_strategy_confidence(self, situation_analysis: Dict[str, Any]) -> float:
        """
        Calculate confidence in strategic plan
        计算战略规划的置信度

        Args:
            situation_analysis: Situation analysis

        Returns:
            Confidence score (0.0 to 1.0)
        """
        # High confidence if few bottlenecks and good progress
        num_bottlenecks = len(situation_analysis.get('bottlenecks', []))
        progress = situation_analysis.get('overall_progress', 0.0)

        confidence = max(0.3, min(1.0, (progress * 0.6 + (1 - num_bottlenecks * 0.2) * 0.4)))

        return confidence

    def _generate_reset_signals(self, strategy: StrategicPlan) -> Dict[str, Dict[str, Any]]:
        """
        Generate reset signals for L modules
        为L模块生成重置信号

        Args:
            strategy: Strategic plan

        Returns:
            Dictionary of reset signals
        """
        reset_signals = {}

        # Reset signal for hippocampus
        hippocampus_signal = ResetSignal(
            target_region='hippocampus',
            action='reset_working_memory',
            guidance=strategy.guidance_for_hippocampus,
            priority=1
        )

        reset_signals['hippocampus'] = {
            'action': hippocampus_signal.action,
            'guidance': hippocampus_signal.guidance,
            'priority': hippocampus_signal.priority
        }

        # Reset signal for amygdala
        amygdala_signal = ResetSignal(
            target_region='amygdala',
            action='reset_emotional_state',
            guidance=strategy.guidance_for_amygdala,
            priority=1
        )

        reset_signals['amygdala'] = {
            'action': amygdala_signal.action,
            'guidance': amygdala_signal.guidance,
            'priority': amygdala_signal.priority
        }

        # Record signals
        self.reset_signals_sent.extend([hippocampus_signal, amygdala_signal])

        logger.debug(f"Generated {len(reset_signals)} reset signals")

        return reset_signals

    def _update_abstract_state(
        self,
        strategy: StrategicPlan,
        global_context: Dict[str, Any]
    ) -> None:
        """
        Update abstract task state
        更新抽象任务状态

        Args:
            strategy: Strategic plan
            global_context: Global context
        """
        self.abstract_task_state['current_goal'] = strategy.goal

        # Check which subgoals are completed
        completed = []
        remaining = []

        for subgoal in strategy.subgoals:
            if self._is_subgoal_completed(subgoal, global_context):
                completed.append(subgoal)
            else:
                remaining.append(subgoal)

        self.abstract_task_state['subgoals_completed'] = completed
        self.abstract_task_state['subgoals_remaining'] = remaining
        self.abstract_task_state['global_progress'] = len(completed) / max(1, len(strategy.subgoals))

    def _is_subgoal_completed(self, subgoal: str, global_context: Dict[str, Any]) -> bool:
        """
        Check if subgoal is completed
        检查子目标是否完成

        Args:
            subgoal: Subgoal string
            global_context: Global context

        Returns:
            True if completed
        """
        # Simple heuristic - in production use more sophisticated check
        converged_regions = global_context.get('converged_regions', [])

        if 'memories' in subgoal.lower():
            return 'hippocampus' in converged_regions

        if 'emotional' in subgoal.lower():
            return 'amygdala' in converged_regions

        # Default: check overall convergence
        return len(converged_regions) > len(global_context.get('region_outputs', {})) // 2

    def get_hrm_status(self) -> Dict[str, Any]:
        """
        Get HRM-specific status
        获取HRM特定状态

        Returns:
            Status dictionary
        """
        return {
            'last_strategic_update': self.last_strategic_update_step,
            'strategic_update_interval': self.strategic_update_interval,
            'current_strategy': {
                'goal': self.strategic_plan.goal if self.strategic_plan else None,
                'subgoals': self.strategic_plan.subgoals if self.strategic_plan else [],
                'confidence': self.strategic_plan.confidence if self.strategic_plan else 0.0
            } if self.strategic_plan else None,
            'abstract_task_state': self.abstract_task_state,
            'reset_signals_sent': len(self.reset_signals_sent)
        }
