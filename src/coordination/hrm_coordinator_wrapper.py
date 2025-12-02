"""
HRM Coordinator Wrapper
HRM协调器包装层

Adds Hierarchical Reasoning Model capabilities to BrainInspiredCoordinator
without modifying the core coordinator code.

Strategy:
- Wrap existing BrainInspiredCoordinator
- Add Thalamus for multi-timescale coordination
- Add Anterior Cingulate for adaptive computation time
- Maintain 100% backward compatibility

Usage:
    # Standard mode
    coordinator = BrainInspiredCoordinator()

    # HRM mode
    coordinator = HRMCoordinatorWrapper(BrainInspiredCoordinator())
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .brain_coordinator_refactored import BrainInspiredCoordinator
from .adaptive_consolidation import AdaptiveConsolidationManager
from ..agents.brain_regions.thalamus_agent import ThalamusAgent, Timescale
from ..agents.brain_regions.anterior_cingulate_agent import AnteriorCingulateAgent, ThinkingMode, MemoryQualityMonitor
from ..agents.brain_regions.anterior_cingulate_agent import AnteriorCingulateAgent, ThinkingMode, MemoryQualityMonitor
from ..utils.performance_profiler import get_profiler
from ..monitoring.feedback_stats import FeedbackStatsLogger  # 🔥 NEW: Feedback quantification

logger = logging.getLogger(__name__)


@dataclass
class HRMConfig:
    """HRM Configuration"""
    enable_multi_timescale: bool = True
    enable_act: bool = True
    min_iterations: int = 3
    max_iterations: int = 20
    confidence_threshold: float = 0.90
    timescales: Dict[str, int] = None

    # 🔥 Feedback Loop Configuration
    enable_quality_monitor: bool = True  # 启用记忆质量监控
    enable_adaptive_consolidation: bool = True  # 启用自适应巩固（完整闭环）
    quality_monitor_config: Dict[str, Any] = None  # MemoryQualityMonitor 配置
    consolidation_config: Dict[str, Any] = None  # AdaptiveConsolidationManager 配置

    def __post_init__(self):
        if self.timescales is None:
            self.timescales = {
                'prefrontal': Timescale.PREFRONTAL,
                'basal_ganglia': Timescale.BASAL_GANGLIA,
                'hippocampus': Timescale.HIPPOCAMPUS,
                'amygdala': Timescale.AMYGDALA,
                'temporal_lobe': 1,  # Fast semantic retrieval
            }
        if self.quality_monitor_config is None:
            self.quality_monitor_config = {
                'base_threshold': 0.15,  # Lowered from 0.3 to trigger on moderate gaps
                'min_retrieval_count': 10,  # Raised to filter noise
                'enable_llm_inference': True
            }
        if self.consolidation_config is None:
            self.consolidation_config = {
                'max_consolidation_rounds': 3,
                'batch_size': 10,
                'min_urgency_for_immediate': 0.8
            }


class HRMCoordinatorWrapper:
    """
    HRM Coordinator Wrapper
    HRM协调器包装层

    Wraps BrainInspiredCoordinator with HRM capabilities:
    1. Multi-timescale coordination (Thalamus)
    2. Adaptive computation time (Anterior Cingulate)
    3. Hierarchical convergence

    Maintains full backward compatibility with standard coordinator.
    """

    def __init__(
        self,
        base_coordinator: BrainInspiredCoordinator,
        hrm_config: Optional[HRMConfig] = None
    ):
        """
        Initialize HRM Wrapper

        Args:
            base_coordinator: The base BrainInspiredCoordinator to wrap
            hrm_config: HRM configuration
        """
        self.base_coordinator = base_coordinator
        self.hrm_config = hrm_config or HRMConfig()

        logger.info("🧠 Initializing HRM Coordinator Wrapper...")

        # HRM components
        self.thalamus: Optional[ThalamusAgent] = None
        self.anterior_cingulate: Optional[AnteriorCingulateAgent] = None

        # 🔥 Feedback Loop components
        self.memory_quality_monitor: Optional[MemoryQualityMonitor] = None
        self.consolidation_manager: Optional[AdaptiveConsolidationManager] = None
        self.feedback_logger = FeedbackStatsLogger()  # 🔥 NEW: Feedback quantification

        # Initialize HRM components
        self._initialize_hrm_components()

        # HRM state
        self.current_iteration = 0
        self.global_step = 0
        self.hrm_active = False

        # 🔥 Feedback signals collected during processing
        self.pending_feedback_signals: List[Dict[str, Any]] = []

        # Performance metrics
        self.hrm_metrics = {
            'queries_with_hrm': 0,
            'avg_iterations': 0.0,
            'early_stops': 0,
            'max_iteration_stops': 0,
            'fast_responses': 0,
            # 🔥 Feedback loop metrics
            'quality_issues_detected': 0,
            'feedback_signals_generated': 0,
        }

        logger.info("✅ HRM Coordinator Wrapper initialized")

    def _initialize_hrm_components(self):
        """Initialize Thalamus and Anterior Cingulate"""

        if self.hrm_config.enable_multi_timescale:
            # Create brain regions dict for Thalamus
            brain_regions = {
                'hippocampus': self.base_coordinator.hippocampus,
                'temporal_lobe': self.base_coordinator.temporal_lobe,
                'prefrontal': self.base_coordinator.prefrontal_storage,
                'amygdala': self.base_coordinator.amygdala,
                'basal_ganglia': self.base_coordinator.basal_ganglia,
            }

            thalamus_config = {
                'timescales': self.hrm_config.timescales,
                'convergence_threshold': 0.95,
            }

            self.thalamus = ThalamusAgent(brain_regions, thalamus_config)
            logger.info("✅ Thalamus Agent initialized (multi-timescale coordination)")

        if self.hrm_config.enable_act:
            act_config = {
                'confidence_threshold': self.hrm_config.confidence_threshold,
                'min_iterations': self.hrm_config.min_iterations,
                'max_iterations': self.hrm_config.max_iterations,
                'cost_weight': 0.1,
            }

            self.anterior_cingulate = AnteriorCingulateAgent(act_config)
            logger.info("✅ Anterior Cingulate Agent initialized (adaptive computation time)")

        # 🔥 Initialize Memory Quality Monitor (Feedback Loop)
        if self.hrm_config.enable_quality_monitor:
            self.memory_quality_monitor = MemoryQualityMonitor(
                config=self.hrm_config.quality_monitor_config
            )
            logger.info("✅ Memory Quality Monitor initialized (feedback loop enabled)")

        # 🔥 Initialize Adaptive Consolidation Manager (Complete Feedback Loop)
        if self.hrm_config.enable_adaptive_consolidation:
            self.consolidation_manager = AdaptiveConsolidationManager(
                hippocampus=self.base_coordinator.hippocampus,
                temporal_lobe=self.base_coordinator.temporal_lobe,
                memory_coordinator=getattr(self.base_coordinator, 'memory_coordinator', None),
                config=self.hrm_config.consolidation_config
            )
            logger.info("✅ Adaptive Consolidation Manager initialized (complete feedback loop)")

    async def start_system(self):
        """Start the system (delegates to base coordinator)"""
        await self.base_coordinator.start_system()

    async def stop_system(self):
        """Stop the system (delegates to base coordinator)"""
        await self.base_coordinator.stop_system()

    async def process_user_input(
        self,
        user_input: str,
        metadata: Optional[Dict[str, Any]] = None,
        use_hrm: bool = True
    ) -> Dict[str, Any]:
        """
        Process user input with optional HRM enhancement

        Args:
            user_input: User's input text
            metadata: Optional metadata
            use_hrm: Whether to use HRM (default: True)

        Returns:
            Dict containing response and HRM metrics
        """
        profiler = get_profiler()

        with profiler.track("hrm_process_user_input_total"):
            if not use_hrm or (not self.hrm_config.enable_multi_timescale and not self.hrm_config.enable_act):
                # Fall back to standard processing
                # Base coordinator returns ProcessingResult, convert to dict for consistency
                with profiler.track("standard_processing"):
                    result = await self.base_coordinator.process_user_input(user_input, metadata)
                return {
                    'response': result.response,
                    'routing_decision': result.routing_decision,
                    'agents_involved': result.agents_involved,
                    'memories_retrieved': result.memories_retrieved,
                    'memory_stored': result.memory_stored,
                    'processing_time': result.processing_time,
                    'agent_logs': result.agent_logs,
                    'insights': result.insights,
                    'success': result.success,
                    'error': result.error,
                }

            # HRM-enhanced processing
            logger.info(f"🧠 HRM-enhanced processing: {user_input[:50]}...")
            self.hrm_active = True
            self.current_iteration = 0

            result = await self._hrm_iterative_processing(user_input, metadata)

            self.hrm_active = False
            return result

    async def _hrm_iterative_processing(
        self,
        user_input: str,
        metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        HRM Iterative Processing Loop

        Implements:
        1. Multi-timescale coordination (if enabled)
        2. Adaptive computation time (if enabled)
        3. Hierarchical convergence
        """

        iteration_states = []
        best_response = None
        best_confidence = 0.0

        for iteration in range(self.hrm_config.max_iterations):
            self.current_iteration = iteration
            self.global_step += 1

            logger.info(f"  HRM Iteration {iteration + 1}/{self.hrm_config.max_iterations}")

            # Determine which regions should update this step (multi-timescale)
            active_regions = self._get_active_regions(self.global_step)

            # Process with base coordinator
            # (In HRM mode, we'd selectively activate regions, but for simplicity
            #  we use the full processing and track iterations)
            iteration_result = await self.base_coordinator.process_user_input(
                user_input,
                metadata
            )

            # Extract state for ACT decision
            # iteration_result is a ProcessingResult dataclass
            memories = iteration_result.memories_retrieved if hasattr(iteration_result, 'memories_retrieved') else []
            current_state = {
                'response': iteration_result.response if hasattr(iteration_result, 'response') else '',
                'memories_retrieved': memories,
                'memories': memories,  # For AnteriorCingulateAgent compatibility
                'agents_involved': iteration_result.agents_involved if hasattr(iteration_result, 'agents_involved') else [],
                'iteration': iteration,
                'active_regions': active_regions,
                'region_outputs': {
                    'response': iteration_result.response if hasattr(iteration_result, 'response') else '',
                    'success': iteration_result.success if hasattr(iteration_result, 'success') else False,
                }
            }

            iteration_states.append(current_state)

            # ACT Decision: Should we continue thinking?
            if self.anterior_cingulate and iteration >= self.hrm_config.min_iterations - 1:
                should_continue, confidence, reasoning = await self._act_decision(
                    iteration_states,
                    iteration
                )

                logger.info(f"    ACT Decision: confidence={confidence:.2f}, continue={should_continue}")
                logger.info(f"    Reasoning: {reasoning}")

                # Update best response if confidence is higher
                # Use actual confidence from ACC instead of fixed formula
                if confidence > best_confidence:
                    best_response = iteration_result
                    best_confidence = confidence

                # 🔥 Feedback Loop: Evaluate memory quality
                if self.memory_quality_monitor and not should_continue:
                    # Only evaluate when we're about to stop - this is when quality matters
                    feedback_signal = await self.memory_quality_monitor.evaluate_memory_quality(
                        query=user_input,
                        retrieval_result=memories,
                        acc_confidence=confidence,
                        current_state=current_state
                    )

                    if feedback_signal:
                        # Quality issue detected! Store signal for later processing
                        self.pending_feedback_signals.append({
                            'signal': feedback_signal,
                            'query': user_input,
                            'iteration': iteration,
                            'timestamp': __import__('datetime').datetime.now().isoformat()
                        })
                        self.hrm_metrics['quality_issues_detected'] += 1
                        self.hrm_metrics['feedback_signals_generated'] += 1

                        logger.warning(
                            f"    🔔 Quality issue detected! type={feedback_signal.get('feedback_type')}, "
                            f"entities={feedback_signal.get('query_entities')}, "
                            f"urgency={feedback_signal.get('urgency', 0):.2f}"
                        )

                if not should_continue:
                    self.hrm_metrics['early_stops'] += 1
                    logger.info(f"  ✅ HRM converged at iteration {iteration + 1}")
                    break

            # Check maximum iterations
            if iteration == self.hrm_config.max_iterations - 1:
                self.hrm_metrics['max_iteration_stops'] += 1
                logger.info(f"  ⏱️  HRM reached max iterations ({self.hrm_config.max_iterations})")

        # Update metrics
        self.hrm_metrics['queries_with_hrm'] += 1
        total_queries = self.hrm_metrics['queries_with_hrm']
        self.hrm_metrics['avg_iterations'] = (
            (self.hrm_metrics['avg_iterations'] * (total_queries - 1) + (iteration + 1)) / total_queries
        )

        # 🔥 Process pending feedback signals (Complete Feedback Loop)
        # 关键修复：处理所有检测到的质量问题，不只是紧急的
        # 涌现原理：每一次质量检测都是学习机会，不应该被忽略
        consolidation_result = None
        if self.consolidation_manager and self.pending_feedback_signals:
            try:
                # 处理所有待处理的反馈信号（不再只处理紧急的）
                logger.info(f"🔄 Processing {len(self.pending_feedback_signals)} feedback signals (closing the loop)")
                consolidation_result = await self._process_feedback_loop()
            except Exception as e:
                logger.error(f"Failed to process feedback loop: {e}")
                consolidation_result = {'error': str(e)}

        # Add HRM metadata to result
        # Convert ProcessingResult to dict and add HRM metadata
        if best_response:
            result_dict = {
                'response': best_response.response,
                'routing_decision': best_response.routing_decision,
                'agents_involved': best_response.agents_involved,
                'memories_retrieved': best_response.memories_retrieved,
                'memory_stored': best_response.memory_stored,
                'processing_time': best_response.processing_time,
                'agent_logs': best_response.agent_logs,
                'insights': best_response.insights,
                'success': best_response.success,
                'error': best_response.error,
                'hrm_metadata': {
                    'iterations': iteration + 1,
                    'convergence_type': 'early_stop' if iteration < self.hrm_config.max_iterations - 1 else 'max_iterations',
                    'final_confidence': best_confidence,
                    'hrm_active': True,
                    # 🔥 Feedback loop metadata
                    'quality_issues_detected': len([s for s in self.pending_feedback_signals if s.get('query') == user_input]),
                    'pending_feedback_signals': len(self.pending_feedback_signals),
                    'consolidation_result': consolidation_result,
                }
            }
            return result_dict

        # Fallback to iteration_result
        return {
            'response': iteration_result.response,
            'routing_decision': iteration_result.routing_decision,
            'agents_involved': iteration_result.agents_involved,
            'memories_retrieved': iteration_result.memories_retrieved,
            'memory_stored': iteration_result.memory_stored,
            'processing_time': iteration_result.processing_time,
            'agent_logs': iteration_result.agent_logs,
            'insights': iteration_result.insights,
            'success': iteration_result.success,
            'error': iteration_result.error,
            'hrm_metadata': {
                'hrm_active': False,
                'pending_feedback_signals': len(self.pending_feedback_signals),
                'consolidation_result': consolidation_result,
            }
        }

    def _get_active_regions(self, global_step: int) -> List[str]:
        """
        Determine which brain regions should update at this step

        Based on multi-timescale coordination:
        - Fast regions (Hippocampus, Amygdala): Every step
        - Medium regions (Basal Ganglia): Every 3 steps
        - Slow regions (Prefrontal): Every 10 steps
        """

        if not self.thalamus or not self.hrm_config.enable_multi_timescale:
            # All regions active if multi-timescale is disabled
            return ['hippocampus', 'temporal_lobe', 'prefrontal', 'amygdala', 'basal_ganglia']

        active = []

        # Fast regions: always active
        active.extend(['hippocampus', 'amygdala', 'temporal_lobe'])

        # Medium regions: every 3 steps
        if global_step % Timescale.BASAL_GANGLIA == 0:
            active.append('basal_ganglia')

        # Slow regions: every 10 steps
        if global_step % Timescale.PREFRONTAL == 0:
            active.append('prefrontal')

        return active

    async def _act_decision(
        self,
        iteration_states: List[Dict[str, Any]],
        current_iteration: int
    ) -> tuple[bool, float, str]:
        """
        ACT Decision: Should we continue thinking?

        Returns:
            (should_continue, confidence, reasoning)
        """

        if not self.anterior_cingulate:
            # Default: continue until max iterations
            return True, 0.5, "ACT disabled, using max iterations"

        # 🔥 Use AnteriorCingulateAgent's full ACT logic with dynamic confidence
        # Get current state from latest iteration
        current_state = iteration_states[-1] if iteration_states else {}

        # Call ACC's should_continue_thinking method
        # This uses vector similarity, region agreement, stability, and evidence quality
        should_continue, confidence, reasoning = await self.anterior_cingulate.should_continue_thinking(
            current_state=current_state,
            iteration=current_iteration,
            max_iterations=self.hrm_config.max_iterations
        )

        return should_continue, confidence, reasoning

    async def _process_feedback_loop(self) -> Dict[str, Any]:
        """
        处理完整的反馈闭环

        数据流:
        pending_feedback_signals → AdaptiveConsolidationManager → KG/Temporal Lobe

        Returns:
            处理结果统计
        """
        if not self.consolidation_manager:
            return {'status': 'skipped', 'reason': 'no_consolidation_manager'}

        if not self.pending_feedback_signals:
            return {'status': 'skipped', 'reason': 'no_pending_signals'}

        total_processed = 0
        total_facts = 0
        total_triples = 0
        errors = []

        # 按紧迫度排序处理
        sorted_signals = sorted(
            self.pending_feedback_signals,
            key=lambda x: x.get('signal', {}).get('urgency', 0),
            reverse=True
        )

        query_contexts = []
        entities_seen = set()

        for signal_wrapper in sorted_signals:
            signal = signal_wrapper.get('signal', {})
            try:
                # 发送到 AdaptiveConsolidationManager
                result = await self.consolidation_manager.receive_feedback(signal)

                if result.get('status') == 'completed':
                    total_processed += 1
                    total_facts += result.get('facts_extracted', 0)
                    total_triples += result.get('triples_extracted', 0)
                    if signal.get('failed_query'):
                        query_contexts.append(signal.get('failed_query'))
                    entities_seen.update(signal.get('query_entities') or [])

                    logger.info(
                        f"✅ Feedback processed: entities={signal.get('query_entities')}, "
                        f"facts={result.get('facts_extracted', 0)}, "
                        f"triples={result.get('triples_extracted', 0)}"
                    )

            except Exception as e:
                logger.error(f"Failed to process feedback signal: {e}")
                errors.append(str(e))

        # 清空已处理的信号
        self.pending_feedback_signals.clear()

        # 更新指标
        self.hrm_metrics['feedback_signals_generated'] = total_processed

        # 🔥 闭环修复：评估反馈效果并更新自适应阈值
        # 涌现原理：每次反馈处理的结果都应该影响未来的行为
        if self.memory_quality_monitor and total_processed > 0:
            # 计算反馈效果：基于提取的事实和三元组数量
            # 效果好 = 提取了有用信息，效果差 = 没提取到什么
            effectiveness = min(1.0, (total_facts + total_triples) / (total_processed * 3))

            # 调用自适应阈值更新
            self.memory_quality_monitor.update_adaptive_threshold(effectiveness)

            # 记录效果到反馈历史
            stats_data = {
                'signals_processed': total_processed,
                'facts_extracted': total_facts,
                'triples_extracted': total_triples,
                'effectiveness': effectiveness,
                'errors': len(errors),
                'queries': query_contexts[-5:],  # 最多记录最近5个查询
                'entities': list(entities_seen)
            }
            self.memory_quality_monitor.record_feedback_result(stats_data)
            
            # 🔥 Log to persistent stats file
            self.feedback_logger.log_feedback_event({
                'query': 'batch_processing', # Context lost in batch, but captured in signals
                'feedback_type': 'consolidation_loop',
                **stats_data
            })

            logger.info(
                f"🎯 Feedback effectiveness: {effectiveness:.2f}, "
                f"adaptive threshold updated"
            )

        return {
            'status': 'completed',
            'signals_processed': total_processed,
            'facts_extracted': total_facts,
            'triples_extracted': total_triples,
            'errors': errors if errors else None
        }

    def get_hrm_metrics(self) -> Dict[str, Any]:
        """Get HRM performance metrics"""
        return {
            **self.hrm_metrics,
            'thalamus_enabled': self.thalamus is not None,
            'act_enabled': self.anterior_cingulate is not None,
            'quality_monitor_enabled': self.memory_quality_monitor is not None,
            'consolidation_manager_enabled': self.consolidation_manager is not None,
        }

    # =========================================================================
    # 🔥 Feedback Loop API
    # =========================================================================

    def get_pending_feedback_signals(self) -> List[Dict[str, Any]]:
        """
        获取待处理的反馈信号

        这些信号应该被 AdaptiveConsolidationManager 处理以触发重新巩固

        Returns:
            List of pending feedback signals
        """
        return self.pending_feedback_signals.copy()

    def get_urgent_feedback_signals(self, min_urgency: float = 0.7) -> List[Dict[str, Any]]:
        """
        获取紧急反馈信号

        Args:
            min_urgency: 最小紧迫度阈值

        Returns:
            List of urgent feedback signals (sorted by urgency)
        """
        urgent = [
            s for s in self.pending_feedback_signals
            if s.get('signal', {}).get('urgency', 0) >= min_urgency
        ]
        return sorted(urgent, key=lambda x: x.get('signal', {}).get('urgency', 0), reverse=True)

    def mark_feedback_processed(self, signal_index: int) -> bool:
        """
        标记反馈信号为已处理

        Args:
            signal_index: Index of the signal in pending_feedback_signals

        Returns:
            True if successful
        """
        if 0 <= signal_index < len(self.pending_feedback_signals):
            self.pending_feedback_signals.pop(signal_index)
            return True
        return False

    def clear_processed_feedback(self):
        """
        清空所有待处理的反馈信号

        通常在 AdaptiveConsolidationManager 处理完所有信号后调用
        """
        count = len(self.pending_feedback_signals)
        self.pending_feedback_signals.clear()
        logger.info(f"🧹 Cleared {count} processed feedback signals")

    async def process_pending_feedback(self, consolidation_manager=None) -> Dict[str, Any]:
        """
        处理待处理的反馈信号

        这是连接 HRM 和 AdaptiveConsolidationManager 的桥梁

        Args:
            consolidation_manager: AdaptiveConsolidationManager 实例（可选）

        Returns:
            处理结果统计
        """
        if not self.pending_feedback_signals:
            return {'processed': 0, 'skipped': 0, 'errors': 0}

        processed = 0
        skipped = 0
        errors = 0

        # Process by urgency (highest first)
        sorted_signals = sorted(
            self.pending_feedback_signals,
            key=lambda x: x.get('signal', {}).get('urgency', 0),
            reverse=True
        )

        for signal_wrapper in sorted_signals:
            signal = signal_wrapper.get('signal', {})
            try:
                if consolidation_manager:
                    # Delegate to AdaptiveConsolidationManager
                    await consolidation_manager.receive_feedback(signal)
                    processed += 1
                else:
                    # Just log for now (no consolidation manager available)
                    logger.info(
                        f"📋 Feedback signal logged (no consolidation manager): "
                        f"type={signal.get('feedback_type')}, "
                        f"entities={signal.get('query_entities')}, "
                        f"hints={signal.get('missing_fact_hints')}"
                    )
                    skipped += 1

            except Exception as e:
                logger.error(f"Failed to process feedback signal: {e}")
                errors += 1

        # Clear processed signals
        self.pending_feedback_signals.clear()

        return {
            'processed': processed,
            'skipped': skipped,
            'errors': errors,
            'total': processed + skipped + errors
        }

    def get_quality_monitor_stats(self) -> Dict[str, Any]:
        """获取记忆质量监控统计"""
        if not self.memory_quality_monitor:
            return {'enabled': False}

        return {
            'enabled': True,
            **self.memory_quality_monitor.get_statistics()
        }

    # Delegate all other attributes to base coordinator
    def __getattr__(self, name):
        """Delegate attribute access to base coordinator"""
        return getattr(self.base_coordinator, name)
