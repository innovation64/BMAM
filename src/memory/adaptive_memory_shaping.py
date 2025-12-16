"""
Adaptive Memory Shaping Manager
自适应记忆塑造管理器

自动根据记忆系统状态触发巩固/反思/遗忘机制
不依赖时间或手动触发，而是基于信息量、容量、重要度等指标
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MemorySystemMetrics:
    """记忆系统指标"""
    # 容量指标
    hippocampus_capacity_ratio: float  # 海马体容量占比
    temporal_lobe_capacity_ratio: float  # 颞叶容量占比

    # 信息量指标
    new_memories_since_last_consolidation: int  # 距上次巩固的新记忆数
    high_importance_memory_count: int  # 高重要度记忆数

    # 知识图谱指标
    kg_relations_accumulated: int  # 累积的KG关系数

    # 情绪指标
    emotional_memories_ratio: float  # 情绪记忆占比

    # 时间指标 (辅助)
    last_consolidation_memory_count: int
    last_reflection_memory_count: int
    last_forgetting_memory_count: int


class AdaptiveMemoryShapingManager:
    """
    自适应记忆塑造管理器

    核心原则:
    1. 基于信息量自动触发巩固 (累积够了就巩固)
    2. 基于容量自动触发遗忘 (快满了就清理)
    3. 基于模式识别触发反思 (发现重复模式时反思)
    4. 基于重要度即时处理 (重要记忆立即巩固)
    """

    def __init__(self, brain_coordinator):
        self.coordinator = brain_coordinator

        # 触发阈值配置
        # 设计理念: 多条件触发，确保记忆及时巩固
        # 1. 累积触发 - 每5条新记忆
        # 2. 重要性触发 - 高重要度记忆立即巩固
        # 3. 容量触发 - Hippocampus快满时强制巩固
        self.config = {
            # 巩固触发条件（降低阈值，提高响应性）
            'consolidation_memory_threshold': 5,   # 累积5条新记忆触发（从15降低）
            'consolidation_kg_threshold': 10,      # 或累积10个KG关系触发（从30降低）
            'high_importance_threshold': 0.6,      # 重要度>0.6立即巩固（从0.7降低）

            # 反思触发条件
            'reflection_memory_threshold': 10,     # 累积10条记忆触发模式分析（从20降低）
            'reflection_similarity_threshold': 0.6,  # 或发现相似度>0.6的模式

            # 遗忘触发条件
            'forgetting_capacity_threshold': 0.75,  # 容量超过75%触发
            'forgetting_low_importance_threshold': 0.3,  # 重要度<0.3可遗忘

            # 情绪调节
            'emotional_memory_consolidation_bonus': 0.2,  # 情绪记忆巩固加成
        }

        # 上次触发的记忆计数
        self.last_consolidation_at = 0
        self.last_reflection_at = 0
        self.last_forgetting_at = 0

        # 累积的KG关系数
        self.accumulated_kg_relations = 0

        logger.info("✅ AdaptiveMemoryShapingManager initialized")

    async def on_new_memory_stored(self, memory_id: str, memory_data: Dict[str, Any]):
        """
        新记忆存储后的回调 - 检查是否触发塑造机制

        这是核心入口点，每次存储新记忆都会调用
        """
        # 1. 获取当前系统指标
        metrics = self._collect_metrics()

        # 2. 检查即时巩固 (高重要度)
        await self._check_immediate_consolidation(memory_id, memory_data, metrics)

        # 3. 检查批量巩固 (信息量累积)
        await self._check_batch_consolidation(metrics)

        # 4. 检查模式反思 (累积足够样本)
        await self._check_pattern_reflection(metrics)

        # 5. 检查容量遗忘 (空间压力)
        await self._check_capacity_forgetting(metrics)

    def _collect_metrics(self) -> MemorySystemMetrics:
        """收集记忆系统指标"""
        hippocampus_count = 0
        hippocampus_capacity = 20000
        temporal_lobe_count = 0
        temporal_lobe_capacity = 70000
        high_importance_count = 0
        emotional_count = 0

        # Hippocampus
        if hasattr(self.coordinator, 'hippocampus'):
            hippocampus_count = len(self.coordinator.hippocampus.memories)
            hippocampus_capacity = self.coordinator.hippocampus.capacity

            # 统计高重要度记忆
            for mem in self.coordinator.hippocampus.memories:
                if getattr(mem, 'importance', 0.5) > self.config['high_importance_threshold']:
                    high_importance_count += 1

        # Temporal Lobe
        if hasattr(self.coordinator, 'temporal_lobe'):
            temporal_lobe_count = len(self.coordinator.temporal_lobe.memories)

        # Amygdala
        if hasattr(self.coordinator, 'amygdala'):
            emotional_count = len(self.coordinator.amygdala.memories)

        return MemorySystemMetrics(
            hippocampus_capacity_ratio=hippocampus_count / hippocampus_capacity,
            temporal_lobe_capacity_ratio=temporal_lobe_count / temporal_lobe_capacity,
            new_memories_since_last_consolidation=hippocampus_count - self.last_consolidation_at,
            high_importance_memory_count=high_importance_count,
            kg_relations_accumulated=self.accumulated_kg_relations,
            emotional_memories_ratio=emotional_count / max(hippocampus_count, 1),
            last_consolidation_memory_count=self.last_consolidation_at,
            last_reflection_memory_count=self.last_reflection_at,
            last_forgetting_memory_count=self.last_forgetting_at
        )

    async def _check_immediate_consolidation(self, memory_id: str, memory_data: Dict[str, Any], metrics: MemorySystemMetrics):
        """检查是否需要即时巩固 (高重要度记忆)"""
        importance = memory_data.get('importance', 0.5)

        # 高重要度 OR 高情绪强度 → 立即巩固
        if importance > self.config['high_importance_threshold']:
            logger.info(f"🔄 [Immediate Consolidation] High importance ({importance:.2f}) → consolidating memory {memory_id[:8]}")
            await self._trigger_consolidation(memory_id, reason='high_importance')

    async def _check_batch_consolidation(self, metrics: MemorySystemMetrics):
        """检查是否需要批量巩固 (信息量累积够了)"""
        # 条件1: 新记忆累积超过阈值
        memory_trigger = metrics.new_memories_since_last_consolidation >= self.config['consolidation_memory_threshold']

        # 条件2: KG关系累积超过阈值
        kg_trigger = metrics.kg_relations_accumulated >= self.config['consolidation_kg_threshold']

        if memory_trigger or kg_trigger:
            reason = 'memory_accumulation' if memory_trigger else 'kg_accumulation'
            logger.info(f"🔄 [Batch Consolidation] Triggered by {reason} → consolidating recent memories")
            await self._trigger_batch_consolidation(reason)

            # 更新计数器
            if hasattr(self.coordinator, 'hippocampus'):
                self.last_consolidation_at = len(self.coordinator.hippocampus.memories)
            self.accumulated_kg_relations = 0

    async def _check_pattern_reflection(self, metrics: MemorySystemMetrics):
        """检查是否需要模式反思 (累积足够样本发现模式)"""
        new_samples = metrics.new_memories_since_last_consolidation + (metrics.last_consolidation_memory_count - metrics.last_reflection_memory_count)

        if new_samples >= self.config['reflection_memory_threshold']:
            logger.info(f"🔍 [Pattern Reflection] {new_samples} new samples → analyzing patterns")
            await self._trigger_reflection(reason='sample_accumulation')

            # 更新计数器
            if hasattr(self.coordinator, 'hippocampus'):
                self.last_reflection_at = len(self.coordinator.hippocampus.memories)

    async def _check_capacity_forgetting(self, metrics: MemorySystemMetrics):
        """检查是否需要容量遗忘 (空间压力)"""
        if metrics.hippocampus_capacity_ratio > self.config['forgetting_capacity_threshold']:
            logger.info(f"🗑️  [Capacity Forgetting] Hippocampus at {metrics.hippocampus_capacity_ratio*100:.1f}% → forgetting low-importance memories")
            await self._trigger_forgetting(reason='capacity_pressure')

            # 更新计数器
            if hasattr(self.coordinator, 'hippocampus'):
                self.last_forgetting_at = len(self.coordinator.hippocampus.memories)

    async def _trigger_consolidation(self, memory_id: str, reason: str):
        """触发单条记忆巩固"""
        try:
            if hasattr(self.coordinator, 'consolidation'):
                from ..coordination.clean_agent_system import AgentMessage
                msg = AgentMessage(
                    sender='adaptive_shaping',
                    receiver='consolidation',
                    message_type='request',
                    content={'action': 'consolidate_memory', 'memory_id': memory_id, 'reason': reason}
                )
                result = await self.coordinator._activate_agent('consolidation', msg)
                logger.info(f"   ✅ Consolidation completed for {memory_id[:8]}")

                # 🔥 2025-12-14: 巩固闭环 - 将巩固结果反馈到脑区连接强度
                if result and hasattr(self.coordinator, 'learning_manager'):
                    try:
                        strengthened = result.get('strengthened', False)
                        learning_manager = self.coordinator.learning_manager
                        if strengthened and learning_manager and hasattr(learning_manager, 'routing_manager'):
                            # 记忆被强化说明检索策略有效
                            learning_manager.routing_manager.update_strategy_weight('hybrid', 0.01)
                            logger.debug(f"   🔄 Consolidation feedback: memory strengthened, +0.01 to hybrid")
                    except Exception as fe:
                        logger.debug(f"   Consolidation feedback failed: {fe}")
        except Exception as e:
            logger.warning(f"   ❌ Consolidation failed: {e}")

    async def _trigger_batch_consolidation(self, reason: str):
        """触发批量记忆巩固"""
        try:
            if hasattr(self.coordinator, 'background_processes'):
                await self.coordinator.background_processes._run_consolidation()
                logger.info(f"   ✅ Batch consolidation completed")
        except Exception as e:
            logger.warning(f"   ❌ Batch consolidation failed: {e}")

    async def _trigger_reflection(self, reason: str):
        """触发模式反思"""
        try:
            if hasattr(self.coordinator, 'reflection') and hasattr(self.coordinator, 'hippocampus'):
                from ..coordination.clean_agent_system import AgentMessage
                recent_memories = self.coordinator.hippocampus.memories[-20:]
                msg = AgentMessage(
                    sender='adaptive_shaping',
                    receiver='reflection',
                    message_type='request',
                    content={
                        'action': 'analyze_recent_patterns',
                        'recent_memories': recent_memories,
                        'context': {'trigger': reason}
                    }
                )
                result = await self.coordinator._activate_agent('reflection', msg)
                insights = result.get('insights_generated', 0)
                logger.info(f"   ✅ Reflection completed, {insights} insights generated")

                # 🔥 2025-12-14: 反思闭环 - 将insights反馈到策略权重
                if insights > 0 and hasattr(self.coordinator, 'learning_manager'):
                    try:
                        # 反思成功意味着当前策略有效，给正反馈
                        learning_manager = self.coordinator.learning_manager
                        if learning_manager and hasattr(learning_manager, 'routing_manager'):
                            # 根据 insights 数量调整反馈强度
                            feedback_strength = min(0.1, insights * 0.02)  # 每个insight +0.02，最多+0.1
                            learning_manager.routing_manager.update_strategy_weight('hybrid', feedback_strength)
                            logger.info(f"   🔄 Reflection feedback applied: +{feedback_strength:.3f} to hybrid strategy")
                    except Exception as fe:
                        logger.debug(f"   Reflection feedback failed: {fe}")
        except Exception as e:
            logger.warning(f"   ❌ Reflection failed: {e}")

    async def _trigger_forgetting(self, reason: str):
        """触发选择性遗忘"""
        try:
            if hasattr(self.coordinator, 'forgetting'):
                from ..coordination.clean_agent_system import AgentMessage
                msg = AgentMessage(
                    sender='adaptive_shaping',
                    receiver='forgetting',
                    message_type='request',
                    content={'action': 'forget_low_importance', 'reason': reason}
                )
                await self.coordinator._activate_agent('forgetting', msg)
                logger.info(f"   ✅ Forgetting completed")
        except Exception as e:
            logger.warning(f"   ❌ Forgetting failed: {e}")

    def on_kg_relation_added(self, relation_count: int = 1):
        """KG关系添加的回调"""
        self.accumulated_kg_relations += relation_count
