"""
Learning Manager Module
Handles continuous learning loops, plasticity management, and weight optimization
"""

import asyncio
from typing import Dict, Any, List
from datetime import datetime

from ..utils.config import get_logger

logger = get_logger(__name__)


class LearningManager:
    """Manages continuous learning, plasticity, and system optimization"""

    def __init__(self, plasticity_engine, continuous_learner, conflict_detector,
                 brain_network=None):
        """
        Initialize Learning Manager

        Args:
            plasticity_engine: Neural plasticity engine instance
            continuous_learner: Continuous learner instance
            conflict_detector: Conflict detector instance
            brain_network: Optional brain network for routing optimization
        """
        self.plasticity_engine = plasticity_engine
        self.continuous_learner = continuous_learner
        self.conflict_detector = conflict_detector
        self.brain_network = brain_network

        self._learning_loop_task = None
        self._learning_loop_interval = 1800  # 30 minutes default
        self._last_learning_cycle = None
        self.is_running = False


    async def start_continuous_learning_loop(self, interval_seconds: int = None):
        """
        Start continuous learning loop

        Args:
            interval_seconds: Learning cycle interval (default: 1800s = 30min)
        """
        if interval_seconds:
            self._learning_loop_interval = interval_seconds

        if self._learning_loop_task is None:
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

        # Note: This method needs coordinator reference to access hippocampus
        # Will be called from coordinator context
        while self.is_running:
            try:
                # 等待指定间隔
                await asyncio.sleep(self._learning_loop_interval)

                if not self.is_running:
                    break


                # This will be called by coordinator with proper context
                # Placeholder for now

            except asyncio.CancelledError:
                break
            except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                logger.error(f"❌ Error in continuous learning loop: {e}", exc_info=True)
                # 继续运行，不因单次错误而停止
                await asyncio.sleep(60)  # 错误后等待1分钟再试

    async def apply_learning_to_weights(self, learning_result: Dict[str, Any]):
        """
        应用学习结果到权重系统

        将持续学习循环的优化结果应用到:
        1. NeuralPlasticityEngine - 智能体间连接权重
        2. BrainNetwork - 脑区激活路由权重

        Args:
            learning_result: run_continuous_learning_cycle 的返回结果
        """
        try:
            adjustments = learning_result.get('adjustments', {})
            recommendations = adjustments.get('recommendations', [])

            if not recommendations:
                return

            # Plasticity engine removed (Hebbian learning no longer used)
            # Skip plasticity-related weight updates

            # Extract routing optimizations
            routing_optimizations = [
                rec for rec in recommendations
                if rec.get('type') == 'routing_optimization'
            ]

            # Apply routing optimization to BrainNetwork
            if routing_optimizations and self.brain_network:
                await self.optimize_brain_network_routing(routing_optimizations)

            logger.debug(f"Learning applied: {len(recommendations)} recommendations processed")


        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            logger.error(f"❌ Failed to apply learning to weights: {e}", exc_info=True)

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
