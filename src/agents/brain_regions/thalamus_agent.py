"""
Thalamus Agent: Hierarchical Timing Coordinator
丘脑智能体：分层时序协调器

Inspired by HRM's hierarchical timing mechanism, the Thalamus coordinates
multi-timescale updates across different brain regions:
- Slow regions (Prefrontal): Strategic planning every T steps
- Fast regions (Hippocampus, Amygdala): Immediate processing every step
- Medium regions (Basal Ganglia): Habit formation every few steps

Key Features:
1. Multi-timescale coordination (HRM's H/L module timing)
2. Global convergence detection
3. State reset signaling from slow to fast regions
4. Adaptive timescale adjustment based on task complexity
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
import asyncio
from dataclasses import dataclass
from enum import IntEnum

from src.core.interfaces.agent_interface import IAgent

logger = logging.getLogger(__name__)


class Timescale(IntEnum):
    """
    Brain Region Timescales
    脑区时间尺度

    Based on neuroscience evidence and HRM architecture:
    - Prefrontal: 10 steps (strategic, slow)
    - Basal Ganglia: 3 steps (habit formation, medium)
    - Hippocampus/Amygdala: 1 step (memory/emotion, fast)
    """
    PREFRONTAL = 10      # Strategic planning
    BASAL_GANGLIA = 3    # Habit formation
    HIPPOCAMPUS = 1      # Fast memory retrieval
    AMYGDALA = 1         # Fast emotional response
    CEREBELLUM = 2       # Motor coordination


@dataclass
class RegionState:
    """
    Brain Region State Tracking
    脑区状态跟踪
    """
    name: str
    timescale: int
    last_update_step: int
    is_converged: bool
    output: Optional[Dict[str, Any]] = None


class ThalamusAgent(IAgent):
    """
    Thalamus Agent: Hierarchical Timing Coordinator
    丘脑智能体：分层时序协调器

    Implements HRM's hierarchical timing mechanism:
    1. Coordinates multi-timescale updates
    2. Detects global convergence
    3. Manages state reset from slow to fast regions
    4. Adapts timescales based on task complexity

    Architecture:
        - H module (slow) → Prefrontal Cortex (every 10 steps)
        - L module (fast) → Hippocampus + Amygdala (every step)
        - Coordinator → Thalamus (this agent)

    Example:
        >>> thalamus = ThalamusAgent(brain_regions)
        >>> result = await thalamus.coordinate_step(input_data)
        >>> active_regions = result['active_regions']
        >>> convergence_status = result['global_convergence']
    """

    def __init__(
        self,
        brain_regions: Dict[str, IAgent],
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Thalamus Agent
        初始化丘脑智能体

        Args:
            brain_regions: Dictionary of brain region agents
            config: Optional configuration for timescales and thresholds
        """
        self.brain_regions = brain_regions
        self.config = config or {}

        # Global step counter
        self.global_step = 0

        # Configure timescales for each region
        self.timescales = self._initialize_timescales()

        # Track state for each region
        self.region_states: Dict[str, RegionState] = {
            name: RegionState(
                name=name,
                timescale=self.timescales[name],
                last_update_step=-1,
                is_converged=False
            )
            for name in brain_regions.keys()
        }

        # Convergence tracking
        self.convergence_threshold = self.config.get('convergence_threshold', 0.95)
        self.max_iterations = self.config.get('max_iterations', 50)
        self.global_converged = False

        # Performance metrics
        self.metrics = {
            'total_steps': 0,
            'slow_updates': 0,
            'fast_updates': 0,
            'reset_signals': 0,
            'convergence_achieved': False
        }

        logger.info(f"ThalamusAgent initialized with {len(brain_regions)} brain regions")

    # ========================================================================
    # IAgent 接口实现
    # ========================================================================

    @property
    def agent_id(self) -> str:
        """唯一智能体标识符"""
        return "thalamus"

    @property
    def brain_region(self) -> str:
        """关联的大脑区域"""
        return "thalamus"

    async def process_message(self, message) -> Dict[str, Any]:
        """处理传入消息"""
        # 提取查询内容
        query = message.content.get('query', '') if hasattr(message, 'content') else str(message)
        # 使用 process 方法处理
        result = await self.process(query)
        return {'response': result, 'status': 'success'}

    async def initialize(self):
        """初始化智能体资源"""
        logger.info("ThalamusAgent initialized")
        return True

    async def shutdown(self):
        """清理智能体资源"""
        logger.info("ThalamusAgent shutdown")
        return True

    # ========================================================================
    # 原有方法
    # ========================================================================

    def register_brain_region(
        self,
        region_name: str,
        region_agent: IAgent,
        timescale: Optional[int] = None
    ) -> bool:
        """
        Dynamically register a new brain region
        动态注册新脑区

        Args:
            region_name: Name of the brain region
            region_agent: Brain region agent instance
            timescale: Optional custom timescale (auto-detected if None)

        Returns:
            True if registration successful, False otherwise
        """
        if region_name in self.brain_regions:
            logger.warning(f"Brain region '{region_name}' already registered")
            return False

        # Register the region
        self.brain_regions[region_name] = region_agent

        # Determine timescale
        if timescale is not None:
            detected_timescale = timescale
        elif 'prefrontal' in region_name.lower():
            detected_timescale = Timescale.PREFRONTAL
        elif 'basal_ganglia' in region_name.lower():
            detected_timescale = Timescale.BASAL_GANGLIA
        elif 'hippocampus' in region_name.lower():
            detected_timescale = Timescale.HIPPOCAMPUS
        elif 'amygdala' in region_name.lower():
            detected_timescale = Timescale.AMYGDALA
        elif 'temporal' in region_name.lower():
            detected_timescale = Timescale.PREFRONTAL  # Temporal Lobe is slow (H module)
        else:
            detected_timescale = 1  # Default fast

        self.timescales[region_name] = detected_timescale

        # Create state tracking
        self.region_states[region_name] = RegionState(
            name=region_name,
            timescale=detected_timescale,
            last_update_step=-1,
            is_converged=False
        )

        logger.info(f"✅ Registered brain region '{region_name}' with timescale={detected_timescale}")
        return True

    def unregister_brain_region(self, region_name: str) -> bool:
        """
        Dynamically unregister a brain region
        动态注销脑区

        Args:
            region_name: Name of the brain region to remove

        Returns:
            True if unregistration successful, False otherwise
        """
        if region_name not in self.brain_regions:
            logger.warning(f"Brain region '{region_name}' not found")
            return False

        # Remove from all tracking dictionaries
        del self.brain_regions[region_name]
        del self.timescales[region_name]
        del self.region_states[region_name]

        logger.info(f"✅ Unregistered brain region '{region_name}'")
        return True

    def _initialize_timescales(self) -> Dict[str, int]:
        """
        Initialize timescales for each brain region
        初始化各脑区时间尺度

        Returns:
            Dictionary mapping region names to timescales
        """
        timescales = {}

        for region_name in self.brain_regions.keys():
            # Use config override or default based on region type
            if region_name in self.config.get('custom_timescales', {}):
                timescales[region_name] = self.config['custom_timescales'][region_name]
            elif 'prefrontal' in region_name.lower():
                timescales[region_name] = Timescale.PREFRONTAL
            elif 'basal_ganglia' in region_name.lower():
                timescales[region_name] = Timescale.BASAL_GANGLIA
            elif 'hippocampus' in region_name.lower():
                timescales[region_name] = Timescale.HIPPOCAMPUS
            elif 'amygdala' in region_name.lower():
                timescales[region_name] = Timescale.AMYGDALA
            elif 'cerebellum' in region_name.lower():
                timescales[region_name] = Timescale.CEREBELLUM
            else:
                # Default to fast timescale
                timescales[region_name] = 1
                logger.warning(f"Unknown region '{region_name}', using default timescale=1")

        return timescales

    async def process(self, user_input: str) -> str:
        """
        Process user input through hierarchical coordination
        通过分层协调处理用户输入

        Args:
            user_input: User query or command

        Returns:
            Final response string
        """
        logger.info(f"Thalamus processing: {user_input[:50]}...")

        # Reset state for new query
        self.global_step = 0
        self.global_converged = False

        # 🔥 2025-12-11 修复: 计算任务复杂度用于动态脑区激活
        # 简单启发式：基于查询长度和特征
        task_complexity = min(1.0, len(user_input) / 200)
        # 检测复杂查询特征
        user_lower = user_input.lower()
        if any(w in user_lower for w in ['when', 'before', 'after', 'during', 'how long']):
            task_complexity = max(task_complexity, 0.5)  # 时间推理查询
        if any(w in user_lower for w in ['why', 'explain', 'analyze', 'compare']):
            task_complexity = max(task_complexity, 0.6)  # 需要深度推理

        # Convert to dict format for coordination
        input_data = {
            'query': user_input,
            'step': 0,
            'context': {},
            'task_complexity': task_complexity  # 🔥 添加任务复杂度
        }

        # Coordinate until convergence or max iterations
        final_result = None

        while not self.global_converged and self.global_step < self.max_iterations:
            result = await self.coordinate_step(input_data)

            if result['global_convergence']:
                final_result = result
                break

            # Update input_data with latest context
            input_data['step'] = self.global_step
            input_data['context'] = result.get('context', {})

        # Extract final response
        if final_result:
            return self._extract_final_response(final_result)
        else:
            logger.warning(f"Max iterations ({self.max_iterations}) reached without convergence")
            return "Processing timeout: Unable to reach convergence"

    async def coordinate_step(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coordinate one timestep across all brain regions
        协调所有脑区的一个时间步

        Implements HRM's hierarchical timing:
        1. Determine which regions should update this step
        2. Execute slow region updates (prefrontal)
        3. Send reset signals from slow to fast regions
        4. Execute fast region updates (hippocampus, amygdala)
        5. Check for global convergence

        Args:
            input_data: Input dictionary with query, step, context

        Returns:
            Dictionary with coordination results
        """
        self.global_step += 1
        self.metrics['total_steps'] += 1

        logger.debug(f"Thalamus Step {self.global_step}: Coordinating brain regions")

        # Step 1: Determine active regions this step
        # 🔥 2025-12-11 修复: 从 input_data 中提取 query 和 task_complexity
        query = input_data.get('query', input_data.get('input', ''))
        task_complexity = input_data.get('task_complexity', input_data.get('complexity'))
        active_regions = self._get_active_regions(query=query, task_complexity=task_complexity)

        results = {
            'step': self.global_step,
            'active_regions': active_regions,
            'region_outputs': {},
            'reset_signals': {},
            'global_convergence': False,
            'context': {}
        }

        # Step 2: Execute slow region updates first (H module, τ>=10)
        slow_regions = [r for r in active_regions if self.timescales[r] >= Timescale.PREFRONTAL]

        for region_name in slow_regions:
            try:
                region_output = await self._update_region(region_name, input_data)
                results['region_outputs'][region_name] = region_output

                # Check if slow region sends reset signals
                if 'reset_signals' in region_output:
                    results['reset_signals'].update(region_output['reset_signals'])
                    self.metrics['reset_signals'] += len(region_output['reset_signals'])
                    logger.debug(f"Slow region '{region_name}' sent {len(region_output['reset_signals'])} reset signals")

                self.metrics['slow_updates'] += 1
            except Exception as e:
                logger.error(f"Error updating slow region '{region_name}': {e}")

        # Step 3: Execute medium-band region updates (M module, 2<=τ<10)
        medium_regions = [r for r in active_regions if 2 <= self.timescales[r] < Timescale.PREFRONTAL]

        for region_name in medium_regions:
            try:
                region_output = await self._update_region(region_name, input_data)
                results['region_outputs'][region_name] = region_output
                logger.debug(f"Medium-band region '{region_name}' (τ={self.timescales[region_name]}) updated")
            except Exception as e:
                logger.error(f"Error updating medium region '{region_name}': {e}")

        # Step 4: Apply reset signals to fast regions
        if results['reset_signals']:
            await self._apply_reset_signals(results['reset_signals'])

        # Step 5: Execute fast region updates (L module, τ=1)
        fast_regions = [r for r in active_regions if self.timescales[r] == 1]

        for region_name in fast_regions:
            try:
                # Pass reset guidance if available
                region_input = input_data.copy()
                if region_name in results['reset_signals']:
                    region_input['reset_guidance'] = results['reset_signals'][region_name]

                region_output = await self._update_region(region_name, region_input)
                results['region_outputs'][region_name] = region_output

                self.metrics['fast_updates'] += 1
            except Exception as e:
                logger.error(f"Error updating fast region '{region_name}': {e}")

        # Step 5: Check for convergence
        results['global_convergence'] = self._check_global_convergence(results)

        if results['global_convergence']:
            self.global_converged = True
            self.metrics['convergence_achieved'] = True
            logger.info(f"Global convergence achieved at step {self.global_step}")

        # Step 6: Build context for next iteration
        results['context'] = self._build_context(results)

        return results

    def _get_active_regions(self, query: str = None, task_complexity: float = None) -> List[str]:
        """
        Determine which regions should update this step
        确定本步骤应更新的脑区

        🔥 2025-12-11 优化: 不仅考虑时间尺度，还考虑任务复杂度和查询类型

        Args:
            query: 当前查询（可选，用于根据查询类型动态调整）
            task_complexity: 任务复杂度 0-1（可选，高复杂度激活更多脑区）

        Returns:
            List of region names to update
        """
        active = []

        # 基于时间尺度的默认激活
        for region_name, state in self.region_states.items():
            steps_since_update = self.global_step - state.last_update_step

            if steps_since_update >= state.timescale:
                active.append(region_name)

        # 🔥 基于查询类型的动态激活（从配置文件加载，不硬编码）
        if query:
            query_lower = query.lower()
            gating_cues = self._load_gating_cues()

            for target_regions, cues in gating_cues.items():
                if any(kw in query_lower for kw in cues):
                    for region in target_regions.split('+'):
                        region = region.strip()
                        if region in self.region_states and region not in active:
                            active.append(region)

        # 🔥 高复杂度任务激活所有脑区
        if task_complexity and task_complexity > 0.7:
            for region_name in self.region_states.keys():
                if region_name not in active:
                    active.append(region_name)

        logger.debug(f"Active regions at step {self.global_step}: {active}")
        return active

    def _load_gating_cues(self) -> Dict[str, List[str]]:
        """Load gating cues from config/thalamus_gating.json. Cached after first load."""
        if hasattr(self, '_gating_cues_cache') and self._gating_cues_cache:
            return self._gating_cues_cache

        import json
        from pathlib import Path
        config_path = Path(__file__).parent.parent.parent.parent / 'config' / 'thalamus_gating.json'
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._gating_cues_cache = data.get('activation_cues', {})
            logger.debug(f"Loaded thalamus gating cues from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to load thalamus gating config: {e}, using defaults")
            self._gating_cues_cache = {
                'hippocampus': ['when', 'how long', 'date', 'time', 'yesterday', 'ago'],
                'amygdala': ['feel', 'emotion', 'happy', 'sad', 'angry', 'love'],
                'basal_ganglia': ['how to', 'steps', 'procedure', 'method'],
                'prefrontal+temporal_lobe': ['prefer', 'favorite', 'who is', 'hobby'],
            }
        return self._gating_cues_cache

    async def _update_region(
        self,
        region_name: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a single brain region
        更新单个脑区

        Args:
            region_name: Name of region to update
            input_data: Input data for region

        Returns:
            Region output dictionary
        """
        region = self.brain_regions[region_name]
        state = self.region_states[region_name]
        query = str(input_data.get('query', ''))

        # 🔥 2025-12-16 修复: 智能检测脑区可用方法
        # Call region's process method based on available interfaces
        try:
            if hasattr(region, 'fast_iteration'):
                # Fast region with HRM support (e.g., HippocampusHRMExtension)
                output = await region.fast_iteration(input_data)
            elif hasattr(region, 'strategic_update'):
                # Slow region with HRM support (e.g., PrefrontalAgent)
                output = await region.strategic_update(input_data)
            elif hasattr(region, 'search_memories'):
                # Memory-based region (Hippocampus, Temporal Lobe, Amygdala)
                result = await region.search_memories(query, k=5)
                memories = result.get('memories', [])
                output = {
                    'response': f"Retrieved {len(memories)} memories",
                    'memories': memories,
                    'converged': len(memories) > 0
                }
            elif hasattr(region, 'process'):
                # Legacy region with process method
                response = await region.process(query)
                output = {'response': response}
            elif hasattr(region, 'process_message'):
                # Agent with process_message (most IAgent implementations)
                from src.core.interfaces.agent_interface import AgentMessage
                message = AgentMessage(
                    sender="thalamus",
                    receiver=region_name,
                    content={'query': query, 'action': 'search_episodes'},
                    message_type="request"
                )
                output = await region.process_message(message)
            else:
                # Last resort: just log and return empty
                logger.warning(f"Region '{region_name}' has no compatible method")
                output = {'response': None, 'error': 'no_compatible_method'}
        except Exception as e:
            logger.error(f"Error calling region '{region_name}': {e}")
            output = {'response': None, 'error': str(e)}

        # Update region state
        state.last_update_step = self.global_step
        state.output = output
        state.is_converged = output.get('converged', False)

        return output

    async def _apply_reset_signals(self, reset_signals: Dict[str, Dict]) -> None:
        """
        Apply reset signals from slow to fast regions
        应用从慢脑区到快脑区的重置信号

        Args:
            reset_signals: Dictionary of region_name -> reset_data
        """
        for target_region, reset_data in reset_signals.items():
            if target_region not in self.brain_regions:
                logger.warning(f"Reset target '{target_region}' not found")
                continue

            region = self.brain_regions[target_region]

            # Call region's reset method if available
            if hasattr(region, 'reset_from_prefrontal'):
                await region.reset_from_prefrontal(reset_data.get('guidance'))
                logger.debug(f"Applied reset signal to '{target_region}'")
            else:
                logger.debug(f"Region '{target_region}' does not support reset")

    def _check_global_convergence(self, step_results: Dict[str, Any]) -> bool:
        """
        Check if global convergence is achieved
        检查是否达到全局收敛

        Convergence criteria:
        1. All fast regions report local convergence
        2. Slow regions have completed at least one update
        3. System has run for minimum steps

        Args:
            step_results: Results from current step

        Returns:
            True if converged, False otherwise
        """
        # Minimum steps before convergence
        min_steps = self.config.get('min_steps_before_convergence', 5)
        if self.global_step < min_steps:
            return False

        # Check if all fast regions converged
        fast_converged = all(
            state.is_converged
            for name, state in self.region_states.items()
            if self.timescales[name] == 1
        )

        # Check if slow regions updated at least once
        slow_updated = any(
            state.last_update_step >= 0
            for name, state in self.region_states.items()
            if self.timescales[name] >= Timescale.PREFRONTAL
        )

        return fast_converged and slow_updated

    def _build_context(self, step_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build context for next iteration
        构建下一轮迭代的上下文

        Args:
            step_results: Results from current step

        Returns:
            Context dictionary
        """
        return {
            'previous_outputs': step_results['region_outputs'],
            'step': self.global_step,
            'converged_regions': [
                name for name, state in self.region_states.items()
                if state.is_converged
            ]
        }

    def _extract_final_response(self, final_result: Dict[str, Any]) -> str:
        """
        Extract final response from coordination result
        从协调结果中提取最终响应

        Args:
            final_result: Final coordination result

        Returns:
            Response string
        """
        # Combine outputs from all regions
        outputs = final_result.get('region_outputs', {})

        # Prefer output from specific regions in priority order
        priority = ['prefrontal', 'hippocampus', 'amygdala']

        for region_type in priority:
            for region_name, output in outputs.items():
                if region_type in region_name.lower():
                    if 'response' in output:
                        return output['response']
                    elif 'strategy' in output:
                        return str(output['strategy'])

        # Fallback: combine all responses
        responses = [
            str(output.get('response', output))
            for output in outputs.values()
        ]

        return '\n'.join(responses) if responses else "No response generated"

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get Thalamus system status
        获取丘脑系统状态

        Returns:
            Status dictionary
        """
        return {
            'global_step': self.global_step,
            'global_converged': self.global_converged,
            'region_states': {
                name: {
                    'timescale': state.timescale,
                    'last_update': state.last_update_step,
                    'converged': state.is_converged
                }
                for name, state in self.region_states.items()
            },
            'metrics': self.metrics,
            'num_brain_regions': len(self.brain_regions)
        }

    def adapt_timescales(self, task_complexity: float) -> None:
        """
        Adapt timescales based on task complexity
        根据任务复杂度调整时间尺度

        For complex tasks, slow down strategic updates to allow more
        fast iterations between slow updates.

        Args:
            task_complexity: Complexity score (0.0 to 1.0)
        """
        if task_complexity > 0.8:
            # Very complex: slow down prefrontal even more
            adjustment_factor = 1.5
        elif task_complexity < 0.3:
            # Simple: speed up prefrontal
            adjustment_factor = 0.7
        else:
            # Normal complexity
            adjustment_factor = 1.0

        for region_name in self.brain_regions.keys():
            if 'prefrontal' in region_name.lower():
                base_timescale = Timescale.PREFRONTAL
                new_timescale = int(base_timescale * adjustment_factor)
                self.timescales[region_name] = max(1, new_timescale)
                self.region_states[region_name].timescale = new_timescale

                logger.info(f"Adapted {region_name} timescale to {new_timescale} (complexity={task_complexity:.2f})")

    def __repr__(self) -> str:
        """String representation"""
        return (f"ThalamusAgent(regions={len(self.brain_regions)}, "
                f"step={self.global_step}, converged={self.global_converged})")
