"""
Learning Manager Module
Handles continuous learning loops, plasticity management, and weight optimization
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..utils.config import get_logger

logger = get_logger(__name__)


class LearningManager:
    """Manages continuous learning, plasticity, and system optimization"""

    def __init__(self, plasticity_engine, continuous_learner, conflict_detector,
                 brain_network=None, hippocampus=None, routing_manager=None, coordinator=None):
        """
        Initialize Learning Manager

        Args:
            plasticity_engine: Neural plasticity engine instance
            continuous_learner: Continuous learner instance
            conflict_detector: Conflict detector instance
            brain_network: Optional brain network for routing optimization
            hippocampus: Hippocampus agent instance for memory access
            routing_manager: 🔥 NEW: RoutingManager for strategy weight updates
            coordinator: 🔥 2025-12-15: BrainInspiredCoordinator for accessing memory systems
        """
        self.plasticity_engine = plasticity_engine
        self.continuous_learner = continuous_learner
        self.conflict_detector = conflict_detector
        self.brain_network = brain_network
        self.hippocampus = hippocampus
        self.routing_manager = routing_manager  # 🔥 NEW
        self._coordinator = coordinator  # 🔥 2025-12-15: 用于访问 adaptive_shaping 等

        self._learning_loop_task = None
        self._learning_loop_interval = 1800  # 30 minutes default
        self._last_learning_cycle: Optional[datetime] = None
        self.is_running = False

        # 🔥 NEW: Track retrieval outcomes for learning
        self.retrieval_history: List[Dict[str, Any]] = []
        self._max_history_size = 1000


    async def start_continuous_learning_loop(self, interval_seconds: int = None):
        """
        Start continuous learning loop

        Args:
            interval_seconds: Learning cycle interval (default: 1800s = 30min)
        """
        if interval_seconds:
            self._learning_loop_interval = interval_seconds

        if self._learning_loop_task is None:
            if not self.continuous_learner:
                logger.warning("⚠️ Continuous learner not available, skipping learning loop startup")
                return
            self.is_running = True
            self._learning_loop_task = asyncio.create_task(self._continuous_learning_loop())

    async def stop_continuous_learning_loop(self):
        """Stop continuous learning loop"""
        self.is_running = False

        if self._learning_loop_task:
            self._learning_loop_task.cancel()
            try:
                await self._learning_loop_task
            except asyncio.CancelledError:
                pass
            self._learning_loop_task = None

    async def run_continuous_learning_cycle(self, hippocampus) -> Dict[str, Any]:
        """
        Execute one continuous learning cycle

        Args:
            hippocampus: Hippocampus agent instance for memory access

        Returns:
            Learning cycle result dict
        """
        if not self.continuous_learner or not hippocampus:
            return {
                'cycle_complete': False,
                'error': 'missing_continuous_learner_or_hippocampus'
            }
        try:
            # 1. 收集记忆和交互历史
            memories = hippocampus.memories
            interactions = []  # 可以从日志或历史中提取

            memory_dicts = [hippocampus._memory_to_dict(m) for m in memories]

            # 2. 反思阶段 (Reflect)
            reflection = await self.continuous_learner.reflect(memory_dicts, interactions)

            # 3. 冲突检测
            conflicts = self.conflict_detector.detect_conflicts(memory_dicts)
            reflection['conflicts'] = conflicts

            # 4. 调整阶段 (Adjust)
            adjustments = self.continuous_learner.adjust(reflection)

            # 5. 优化阶段 (Optimize)
            optimization = self.continuous_learner.optimize(adjustments)

            result = {
                'cycle_complete': True,
                'timestamp': datetime.now().isoformat(),
                'reflection': reflection,
                'adjustments': adjustments,
                'optimization': optimization
            }

            logger.info(f"✅ Learning cycle complete: "
                       f"{len(adjustments.get('recommendations', []))} adjustments, "
                       f"{len(conflicts)} conflicts detected")

            return result

        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            logger.error(f"❌ Continuous learning cycle failed: {e}", exc_info=True)
            return {
                'cycle_complete': False,
                'error': str(e)
            }

    async def _continuous_learning_loop(self):
        """
        持续学习循环后台任务
        定期执行反思-调整-优化循环，并将结果写回权重
        """
        logger.info("🔄 Continuous learning loop started")

        while self.is_running:
            try:
                # 等待指定间隔
                await asyncio.sleep(self._learning_loop_interval)

                if not self.is_running:
                    break

                # 检查是否有 hippocampus 可用
                if self.hippocampus is None:
                    logger.warning("⚠️ Hippocampus not available, skipping learning cycle")
                    continue

                # 检查是否有 continuous_learner 可用
                if self.continuous_learner is None:
                    logger.warning("⚠️ ContinuousLearner not available, skipping learning cycle")
                    continue

                # 🔥 真正执行学习循环
                logger.info("🧠 Running continuous learning cycle...")
                result = await self.run_continuous_learning_cycle(self.hippocampus)

                if result.get('cycle_complete'):
                    self._last_learning_cycle = datetime.now()

                    # 应用学习结果到权重
                    await self.apply_learning_to_weights(result)

                    logger.info(f"✅ Learning cycle completed at {self._last_learning_cycle}")
                else:
                    logger.warning(f"⚠️ Learning cycle incomplete: {result.get('error', 'unknown')}")

            except asyncio.CancelledError:
                logger.info("🛑 Continuous learning loop cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in continuous learning loop: {e}", exc_info=True)
                # 继续运行，不因单次错误而停止
                await asyncio.sleep(60)  # 错误后等待1分钟再试

        logger.info("🔄 Continuous learning loop stopped")

    def record_retrieval_outcome(
        self,
        strategy: str,
        query: str,
        success: bool,
        confidence: float,
        memory_count: int = 0
    ) -> None:
        """
        Record retrieval outcome for learning feedback
        记录检索结果用于学习反馈

        This should be called after each retrieval to track strategy effectiveness.

        Args:
            strategy: Strategy used for retrieval
            query: The query text
            success: Whether retrieval was successful (e.g., confidence > threshold)
            confidence: Confidence score of the result
            memory_count: Number of memories retrieved
        """
        outcome = {
            'strategy': strategy,
            'query': query[:100],  # Truncate for storage
            'success': success,
            'confidence': confidence,
            'memory_count': memory_count,
            'timestamp': datetime.now().isoformat()
        }

        self.retrieval_history.append(outcome)

        # Trim history if too large
        if len(self.retrieval_history) > self._max_history_size:
            self.retrieval_history = self.retrieval_history[-self._max_history_size:]

        # 🔥 Also record in RoutingManager for immediate tracking
        if self.routing_manager:
            self.routing_manager.record_strategy_outcome(strategy, success, confidence)

    async def apply_learning_to_weights(self, learning_result: Dict[str, Any]):
        """
        应用学习结果到权重系统

        将持续学习循环的优化结果应用到:
        1. NeuralPlasticityEngine - 智能体间连接权重
        2. BrainNetwork - 脑区激活路由权重
        3. 🔥 NEW: RoutingManager - 检索策略权重
        4. 🔥 2025-12-15: 实际触发巩固/冲突解决

        Args:
            learning_result: run_continuous_learning_cycle 的返回结果
        """
        try:
            adjustments = learning_result.get('adjustments', {})
            recommendations = adjustments.get('recommendations', [])

            weights_updated = 0
            optimizations_applied = []

            # 🔥 NEW: Apply learning to RoutingManager strategy weights
            if self.routing_manager and self.retrieval_history:
                weights_updated = await self._update_routing_weights_from_history()

            # 🔥 2025-12-15: 实际应用优化建议 (不再是simulated)
            for rec in recommendations:
                rec_type = rec.get('type', '')
                priority = rec.get('priority', 'low')

                if rec_type == 'confidence_improvement':
                    # 低置信度 → 触发记忆巩固
                    # 通过 AdaptiveMemoryShaping 或直接调用 consolidation
                    if hasattr(self, '_coordinator') and self._coordinator:
                        try:
                            # 使用 AdaptiveShaping 触发巩固
                            if hasattr(self._coordinator, 'adaptive_shaping') and self._coordinator.adaptive_shaping:
                                await self._coordinator.adaptive_shaping.trigger_adaptive_consolidation(
                                    trigger_type='low_confidence',
                                    confidence=learning_result.get('reflection', {}).get('average_confidence', 0.4)
                                )
                                optimizations_applied.append({
                                    'type': rec_type,
                                    'action': 'triggered_consolidation',
                                    'status': 'applied'
                                })
                                logger.info(f"🧠 Applied confidence_improvement: triggered consolidation")
                            elif hasattr(self._coordinator, 'memory_coordinator'):
                                # Fallback: 直接触发巩固
                                await self._coordinator.memory_coordinator.trigger_consolidation(
                                    strategy='batch', batch_size=30
                                )
                                optimizations_applied.append({
                                    'type': rec_type,
                                    'action': 'triggered_batch_consolidation',
                                    'status': 'applied'
                                })
                                logger.info(f"🧠 Applied confidence_improvement: batch consolidation")
                        except Exception as e:
                            logger.warning(f"⚠️ confidence_improvement failed: {e}")
                            optimizations_applied.append({
                                'type': rec_type,
                                'action': rec.get('action'),
                                'status': 'failed',
                                'error': str(e)
                            })

                elif rec_type == 'conflict_resolution':
                    # 检测到冲突 → 尝试解决
                    conflicts = rec.get('conflicts', [])
                    if conflicts and self.conflict_detector:
                        try:
                            # 记录冲突供后续处理
                            for conflict in conflicts[:5]:  # 最多处理5个冲突
                                logger.warning(
                                    f"⚠️ Memory conflict: {conflict.get('description', 'Unknown conflict')}"
                                )
                            # TODO: 实现自动冲突解决 (需要LLM支持)
                            # 目前只是记录，后续可以扩展为自动解决
                            optimizations_applied.append({
                                'type': rec_type,
                                'action': 'conflicts_logged',
                                'conflict_count': len(conflicts),
                                'status': 'partial'  # 只记录了，没有自动解决
                            })
                        except Exception as e:
                            logger.warning(f"⚠️ conflict_resolution failed: {e}")

                elif rec_type == 'personalization':
                    # 偏好调整 → 更新路由权重
                    preferences = rec.get('preferences', {})
                    if preferences and self.routing_manager:
                        try:
                            # 根据用户偏好调整某些策略的权重
                            likes = preferences.get('likes', [])
                            if likes:
                                # 如果用户喜欢某些主题，增加语义检索权重
                                self.routing_manager.update_strategy_weight('semantic', 0.05)
                            optimizations_applied.append({
                                'type': rec_type,
                                'action': 'routing_weights_adjusted',
                                'status': 'applied'
                            })
                        except Exception as e:
                            logger.warning(f"⚠️ personalization failed: {e}")

                elif rec_type == 'routing_optimization':
                    # 路由优化
                    agents = rec.get('agents') or rec.get('suggested_agents') or []
                    if agents and self.plasticity_engine:
                        self.plasticity_engine.record_agent_activation(agents)
                        optimizations_applied.append({
                            'type': rec_type,
                            'action': 'agent_activation_recorded',
                            'agents': agents,
                            'status': 'applied'
                        })

            # Extract routing optimizations
            routing_optimizations = [
                rec for rec in recommendations
                if rec.get('type') == 'routing_optimization'
            ]

            # Apply routing optimization to BrainNetwork
            if routing_optimizations and self.brain_network:
                await self.optimize_brain_network_routing(routing_optimizations)

            # 统计应用结果
            applied_count = sum(1 for opt in optimizations_applied if opt.get('status') == 'applied')
            partial_count = sum(1 for opt in optimizations_applied if opt.get('status') == 'partial')
            failed_count = sum(1 for opt in optimizations_applied if opt.get('status') == 'failed')

            logger.info(
                f"✅ Learning applied: {len(recommendations)} recommendations, "
                f"{weights_updated} strategy weights updated, "
                f"{applied_count} applied, {partial_count} partial, {failed_count} failed"
            )

        except Exception as e:
            logger.error(f"❌ Failed to apply learning to weights: {e}", exc_info=True)

    async def _update_routing_weights_from_history(self) -> int:
        """
        Update RoutingManager weights based on retrieval history
        基于检索历史更新路由权重

        Returns:
            Number of weights updated
        """
        if not self.routing_manager:
            return 0

        # Calculate success rate per strategy from recent history
        recent_history = self.retrieval_history[-200:]  # Last 200 retrievals
        strategy_stats: Dict[str, Dict[str, Any]] = {}

        for outcome in recent_history:
            strategy = outcome.get('strategy', 'unknown')
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {
                    'success': 0,
                    'failure': 0,
                    'total_confidence': 0.0
                }

            if outcome.get('success'):
                strategy_stats[strategy]['success'] += 1
            else:
                strategy_stats[strategy]['failure'] += 1
            strategy_stats[strategy]['total_confidence'] += outcome.get('confidence', 0)

        # Update weights based on success rate vs baseline
        weights_updated = 0
        baseline_success_rate = 0.5  # Neutral baseline

        for strategy, stats in strategy_stats.items():
            total = stats['success'] + stats['failure']
            if total < 5:  # Need at least 5 samples
                continue

            success_rate = stats['success'] / total
            avg_confidence = stats['total_confidence'] / total

            # Calculate weight adjustment
            # If success rate > baseline, increase weight; if < baseline, decrease
            rate_delta = success_rate - baseline_success_rate
            confidence_factor = avg_confidence  # Higher confidence = more trust in outcome

            # Combined delta: rate improvement weighted by confidence
            weight_delta = rate_delta * confidence_factor

            # Apply update
            self.routing_manager.update_strategy_weight(strategy, weight_delta)
            weights_updated += 1

            logger.debug(
                f"Strategy '{strategy}': success_rate={success_rate:.2f}, "
                f"avg_conf={avg_confidence:.2f}, weight_delta={weight_delta:.3f}"
            )

        return weights_updated

    async def optimize_brain_network_routing(self, optimizations: List[Dict[str, Any]]):
        """
        根据学习结果优化 BrainNetwork 路由策略

        Args:
            optimizations: 路由优化建议列表
        """
        if not self.brain_network:
            logger.warning("BrainNetwork not available for routing optimization")
            return

        try:
            # 从反思中提取性能指标
            # Note: This would need access to learning logger
            # Placeholder implementation
            pass

        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            logger.error(f"❌ Failed to optimize routing: {e}", exc_info=True)

    def get_learning_status(self) -> Dict[str, Any]:
        """
        Get current learning system status

        Returns:
            Status dict with learning metrics
        """
        return {
            'is_running': self.is_running,
            'interval_seconds': self._learning_loop_interval,
            'last_cycle': self._last_learning_cycle.isoformat() if self._last_learning_cycle else None,
            'task_active': self._learning_loop_task is not None and not self._learning_loop_task.done()
        }
