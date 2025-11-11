"""
Brain Inspired Coordinator V3 with HRM Integration
大脑启发式协调器V3：集成HRM机制

Integrates Hierarchical Reasoning Model (HRM) mechanisms:
1. Thalamus: Multi-timescale coordination
2. Anterior Cingulate: Adaptive computation time (ACT)
3. Prefrontal (H module): Slow strategic updates
4. Hippocampus (L module): Fast memory retrieval
5. Basal Ganglia: Fixed-point detection and pattern learning

This is the culmination of the HRM integration, bringing together
all the brain regions with their HRM enhancements for hierarchical,
adaptive reasoning.
"""

from typing import Dict, Any, Optional, List
import logging
import asyncio

from src.core.container import Container as DependencyContainer
from src.core.config import BMAMConfig
from src.core.interfaces.memory_interface import IMemorySystem
from src.core.interfaces.agent_interface import IAgent

from src.agents.brain_regions.thalamus_agent import ThalamusAgent
from src.agents.brain_regions.anterior_cingulate_agent import AnteriorCingulateAgent

logger = logging.getLogger(__name__)


class BrainInspiredCoordinatorV3_HRM:
    """
    Brain Inspired Coordinator V3 with HRM
    大脑启发式协调器V3（HRM集成版）

    Implements full Hierarchical Reasoning Model architecture:

    Architecture:
        - Thalamus: Coordinates multi-timescale updates
          - H module (Prefrontal): Slow strategic updates every T=10 steps
          - L modules (Hippocampus, Amygdala): Fast updates every step
        - Anterior Cingulate: Decides when to stop thinking (ACT)
        - Basal Ganglia: Detects fixed points and learns patterns
        - Message Bus: Asynchronous inter-region communication

    Key Features:
    1. Hierarchical timing (slow/fast brain regions)
    2. Adaptive computation (stop when confident)
    3. State reset from slow to fast regions
    4. Fixed-point detection for efficiency
    5. Pattern learning for future optimization

    Example:
        >>> coordinator = BrainInspiredCoordinatorV3_HRM(
        ...     container=container,
        ...     config=config,
        ...     components=components
        ... )
        >>> await coordinator.initialize()
        >>> result = await coordinator.process("What is consciousness?")
    """

    def __init__(
        self,
        container: DependencyContainer,
        config: BMAMConfig,
        components: Dict[str, Any]
    ):
        """
        Initialize Coordinator V3 with HRM
        初始化协调器V3（HRM版）

        Args:
            container: DI container
            config: BMAM configuration
            components: Pre-configured components dict with:
                - memory_system: IMemorySystem
                - agents: Dict of brain region agents
                - message_bus: Optional IMessageBus
        """
        logger.info("Creating BrainInspiredCoordinatorV3_HRM...")

        self._container = container
        self._config = config
        self._components = components

        # Core components
        self.memory_system: IMemorySystem = components['memory_system']
        self.brain_regions: Dict[str, IAgent] = components['agents']
        self.message_bus = components.get('message_bus')

        # HRM components
        self.thalamus: Optional[ThalamusAgent] = None
        self.anterior_cingulate: Optional[AnteriorCingulateAgent] = None

        # Initialization state
        self._initialized = False
        self._init_lock = asyncio.Lock()

        # Processing state
        self._current_query: Optional[str] = None
        self._processing_active = False

        # Performance metrics
        self.metrics = {
            'queries_processed': 0,
            'avg_convergence_steps': 0.0,
            'early_stops': 0,
            'max_iteration_stops': 0,
            'total_steps': 0
        }

        logger.info(f"CoordinatorV3_HRM created with {len(self.brain_regions)} brain regions")

    async def initialize(self) -> None:
        """
        Initialize Coordinator V3 with HRM Components
        初始化协调器V3（HRM组件）

        Sets up the HRM architecture:
        1. Create Thalamus (timing coordinator)
        2. Create Anterior Cingulate (ACT decision maker)
        3. Verify brain regions have HRM capabilities
        4. Initialize background tasks
        """
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:
                return

            logger.info("Initializing BrainInspiredCoordinatorV3_HRM...")

            # Step 1: Create Thalamus for timing coordination
            self._initialize_thalamus()

            # Step 2: Create Anterior Cingulate for ACT
            self._initialize_anterior_cingulate()

            # Step 3: Verify HRM capabilities in brain regions
            self._verify_hrm_capabilities()

            # Step 4: Initialize brain regions
            await self._initialize_brain_regions()

            self._initialized = True
            logger.info("✅ BrainInspiredCoordinatorV3_HRM initialized successfully")

    def _initialize_thalamus(self) -> None:
        """Initialize Thalamus agent for timing coordination"""
        logger.info("Initializing Thalamus (timing coordinator)...")

        # Configure timescales for brain regions
        thalamus_config = {
            'convergence_threshold': 0.95,
            'max_iterations': 50,
            'min_steps_before_convergence': 3,
            'custom_timescales': {}  # Use defaults based on region names
        }

        self.thalamus = ThalamusAgent(
            brain_regions=self.brain_regions,
            config=thalamus_config
        )

        logger.info("✅ Thalamus initialized")

    def _initialize_anterior_cingulate(self) -> None:
        """Initialize Anterior Cingulate agent for ACT"""
        logger.info("Initializing Anterior Cingulate (ACT decision maker)...")

        acc_config = {
            'confidence_threshold': 0.90,
            'min_iterations': 3,
            'max_iterations': 20,
            'cost_weight': 0.1
        }

        self.anterior_cingulate = AnteriorCingulateAgent(config=acc_config)

        logger.info("✅ Anterior Cingulate initialized")

    def _verify_hrm_capabilities(self) -> None:
        """
        Verify that brain regions have HRM capabilities
        验证脑区是否具有HRM能力
        """
        logger.info("Verifying HRM capabilities in brain regions...")

        capabilities = {}

        for region_name, agent in self.brain_regions.items():
            has_strategic_update = hasattr(agent, 'strategic_update')
            has_fast_iteration = hasattr(agent, 'fast_iteration')
            has_reset = hasattr(agent, 'reset_from_prefrontal')
            has_monitor = hasattr(agent, 'monitor_convergence')

            capabilities[region_name] = {
                'strategic_update': has_strategic_update,
                'fast_iteration': has_fast_iteration,
                'reset_from_prefrontal': has_reset,
                'monitor_convergence': has_monitor
            }

            # Log capabilities
            hrm_methods = [k for k, v in capabilities[region_name].items() if v]
            if hrm_methods:
                logger.info(f"  {region_name}: HRM-enabled ({', '.join(hrm_methods)})")
            else:
                logger.warning(f"  {region_name}: No HRM capabilities (legacy agent)")

        self._hrm_capabilities = capabilities

    async def _initialize_brain_regions(self) -> None:
        """Initialize brain region agents if needed"""
        for region_name, agent in self.brain_regions.items():
            if hasattr(agent, 'initialize'):
                try:
                    await agent.initialize()
                    logger.debug(f"Initialized {region_name}")
                except Exception as e:
                    logger.error(f"Failed to initialize {region_name}: {e}")

    async def process(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process User Input with HRM
        使用HRM处理用户输入

        Orchestrates hierarchical reasoning:
        1. Thalamus coordinates multi-timescale updates
        2. ACC monitors confidence and decides when to stop
        3. Prefrontal provides strategic guidance (slow)
        4. Hippocampus/Amygdala execute fast retrieval
        5. Basal Ganglia monitors for fixed points

        Args:
            user_input: User query
            context: Optional context

        Returns:
            Response string
        """
        await self.initialize()  # Ensure initialized

        logger.info(f"Processing query with HRM: {user_input[:50]}...")

        self._current_query = user_input
        self._processing_active = True

        try:
            # Use Thalamus to coordinate hierarchical processing
            result = await self.thalamus.process(user_input)

            # Update metrics
            self._update_metrics(result)

            return result

        except Exception as e:
            logger.error(f"Error in HRM processing: {e}", exc_info=True)
            return f"Processing error: {str(e)}"

        finally:
            self._processing_active = False
            self._current_query = None

    async def process_with_monitoring(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process with Detailed Monitoring
        带详细监控的处理

        Same as process() but returns detailed execution information.

        Args:
            user_input: User query
            context: Optional context

        Returns:
            Dictionary with:
            - response: Final response string
            - steps: Number of steps taken
            - convergence_achieved: Whether convergence was reached
            - thinking_history: ACC thinking history
            - fixed_points: Fixed points detected
            - region_outputs: Outputs from each brain region
        """
        await self.initialize()

        logger.info(f"Processing with monitoring: {user_input[:50]}...")

        self._current_query = user_input
        self._processing_active = True

        # Reset ACC history
        self.anterior_cingulate.reset_history()

        # Reset Basal Ganglia session
        for agent in self.brain_regions.values():
            if hasattr(agent, 'reset_session'):
                agent.reset_session()

        try:
            # Coordinate step-by-step with monitoring
            step = 0
            max_steps = 50
            converged = False
            coordination_history = []

            input_data = {
                'query': user_input,
                'step': step,
                'context': context or {}
            }

            while not converged and step < max_steps:
                # Thalamus coordinates one step
                coord_result = await self.thalamus.coordinate_step(input_data)

                # ACC evaluates whether to continue
                should_continue, confidence, reasoning = await self.anterior_cingulate.should_continue_thinking(
                    current_state=coord_result,
                    iteration=step
                )

                # Basal Ganglia monitors convergence
                bg_agent = self._get_basal_ganglia_agent()
                if bg_agent and hasattr(bg_agent, 'monitor_convergence'):
                    bg_result = await bg_agent.monitor_convergence(
                        step=step,
                        region_outputs=coord_result.get('region_outputs', {})
                    )
                    coord_result['basal_ganglia_monitoring'] = bg_result

                # Record step
                coordination_history.append({
                    'step': step,
                    'coordination': coord_result,
                    'acc_decision': {
                        'continue': should_continue,
                        'confidence': confidence,
                        'reasoning': reasoning
                    }
                })

                # Check for convergence
                converged = coord_result.get('global_convergence') or not should_continue

                if converged:
                    logger.info(f"Convergence achieved at step {step}")
                    # Learn pattern
                    if bg_agent and hasattr(bg_agent, 'learn_convergence_pattern'):
                        await bg_agent.learn_convergence_pattern(
                            query_type=self._classify_query(user_input),
                            convergence_step=step
                        )
                    break

                # Update for next iteration
                step += 1
                input_data['step'] = step
                input_data['context'] = coord_result.get('context', {})

            # Extract final response
            final_response = self._extract_response_from_history(coordination_history)

            # Collect monitoring data
            return {
                'response': final_response,
                'steps': step,
                'convergence_achieved': converged,
                'final_confidence': coordination_history[-1]['acc_decision']['confidence'] if coordination_history else 0.0,
                'thinking_history': self.anterior_cingulate.get_thinking_history(),
                'coordination_history': coordination_history,
                'thalamus_status': self.thalamus.get_system_status(),
                'acc_status': self.anterior_cingulate.get_system_status(),
                'basal_ganglia_status': self._get_basal_ganglia_status()
            }

        except Exception as e:
            logger.error(f"Error in monitored processing: {e}", exc_info=True)
            return {
                'response': f"Processing error: {str(e)}",
                'error': str(e),
                'steps': 0,
                'convergence_achieved': False
            }

        finally:
            self._processing_active = False
            self._current_query = None

    def _get_basal_ganglia_agent(self) -> Optional[IAgent]:
        """Get Basal Ganglia agent if available"""
        for name, agent in self.brain_regions.items():
            if 'basal_ganglia' in name.lower():
                return agent
        return None

    def _get_basal_ganglia_status(self) -> Dict[str, Any]:
        """Get Basal Ganglia HRM status"""
        bg_agent = self._get_basal_ganglia_agent()
        if bg_agent and hasattr(bg_agent, 'get_hrm_status'):
            return bg_agent.get_hrm_status()
        return {}

    def _classify_query(self, query: str) -> str:
        """
        Classify query type for pattern learning
        分类查询类型用于模式学习

        Args:
            query: User query

        Returns:
            Query type string
        """
        query_lower = query.lower()

        if '?' in query:
            return 'question'
        elif any(w in query_lower for w in ['create', 'generate', 'make', 'write']):
            return 'creation'
        elif any(w in query_lower for w in ['find', 'search', 'retrieve', 'get']):
            return 'retrieval'
        elif any(w in query_lower for w in ['analyze', 'explain', 'why', 'how']):
            return 'analysis'
        else:
            return 'general'

    def _extract_response_from_history(
        self,
        coordination_history: List[Dict[str, Any]]
    ) -> str:
        """
        Extract final response from coordination history
        从协调历史中提取最终响应

        Args:
            coordination_history: List of coordination steps

        Returns:
            Final response string
        """
        if not coordination_history:
            return "No response generated"

        # Get last coordination result
        last_coord = coordination_history[-1]['coordination']
        region_outputs = last_coord.get('region_outputs', {})

        # Priority order for response sources
        priority = ['prefrontal', 'hippocampus', 'temporal_lobe', 'amygdala']

        for region_type in priority:
            for region_name, output in region_outputs.items():
                if region_type in region_name.lower():
                    if isinstance(output, dict):
                        if 'response' in output:
                            return output['response']
                        elif 'strategy' in output:
                            return str(output['strategy'])
                    else:
                        return str(output)

        # Fallback: combine all responses
        responses = []
        for output in region_outputs.values():
            if isinstance(output, dict):
                resp = output.get('response') or output.get('strategy')
                if resp:
                    responses.append(str(resp))
            else:
                responses.append(str(output))

        return '\n'.join(responses) if responses else "Processing complete"

    def _update_metrics(self, result: str) -> None:
        """
        Update performance metrics
        更新性能指标

        Args:
            result: Processing result
        """
        self.metrics['queries_processed'] += 1

        # Get stats from components
        thalamus_status = self.thalamus.get_system_status()
        acc_status = self.anterior_cingulate.get_system_status()

        # Update convergence metrics
        steps = thalamus_status.get('global_step', 0)
        self.metrics['total_steps'] += steps

        if self.metrics['queries_processed'] > 0:
            self.metrics['avg_convergence_steps'] = (
                self.metrics['total_steps'] / self.metrics['queries_processed']
            )

        # Update stop metrics
        self.metrics['early_stops'] = acc_status['metrics']['early_stops']
        self.metrics['max_iteration_stops'] = acc_status['metrics']['max_iteration_stops']

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get Comprehensive System Status
        获取综合系统状态

        Returns:
            Status dictionary with all components
        """
        status = {
            'initialized': self._initialized,
            'processing_active': self._processing_active,
            'current_query': self._current_query,
            'brain_regions': list(self.brain_regions.keys()),
            'metrics': self.metrics
        }

        if self.thalamus:
            status['thalamus'] = self.thalamus.get_system_status()

        if self.anterior_cingulate:
            status['anterior_cingulate'] = self.anterior_cingulate.get_system_status()

        # HRM capabilities summary
        hrm_summary = {
            'strategic_update_capable': sum(
                1 for caps in self._hrm_capabilities.values()
                if caps.get('strategic_update')
            ),
            'fast_iteration_capable': sum(
                1 for caps in self._hrm_capabilities.values()
                if caps.get('fast_iteration')
            ),
            'reset_capable': sum(
                1 for caps in self._hrm_capabilities.values()
                if caps.get('reset_from_prefrontal')
            )
        }
        status['hrm_capabilities'] = hrm_summary

        # Basal Ganglia status
        status['basal_ganglia'] = self._get_basal_ganglia_status()

        return status

    async def stop_system(self) -> None:
        """
        Stop Coordinator and Cleanup
        停止协调器并清理
        """
        logger.info("Stopping BrainInspiredCoordinatorV3_HRM...")

        # Stop Thalamus (which stops brain regions)
        if self.thalamus:
            await self.thalamus.stop_system()

        self._initialized = False
        logger.info("✅ BrainInspiredCoordinatorV3_HRM stopped")

    def __repr__(self) -> str:
        """String representation"""
        status = "initialized" if self._initialized else "not initialized"
        return (f"BrainInspiredCoordinatorV3_HRM({status}, "
                f"{len(self.brain_regions)} regions, HRM-enabled)")
