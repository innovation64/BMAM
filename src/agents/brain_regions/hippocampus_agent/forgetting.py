"""
Hippocampus Agent - 海马体智能体
对应脑区: 海马体 (Hippocampus)
主要功能: 情节记忆存储+检索+巩固

优化更新 (2025-11-30):
- 实现沉默印迹机制 (Silent Engram)
- 遗忘不再删除记忆，而是转为沉默状态
- 强线索可以重新激活沉默印迹

基于论文: "Key-value memory in the brain" (Benna & Fusi, 2024)
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
import uuid
import numpy as np

logger = logging.getLogger(__name__)


from .core import EpisodicMemory, HippocampusAgentCore
from ....memory.silent_engram import SilentEngramStore, SilentEngram
import asyncio


class ForgettingMixin:
    """
    遗忘机制功能

    核心改进：沉默印迹机制
    - 遗忘 ≠ 删除，而是转为沉默状态
    - 沉默印迹保留检索键，但需要更强线索激活
    - 支持记忆的重新激活

    神经科学依据:
    - Richards & Frankland (2017): 遗忘是检索失败，非信息删除
    - Tonegawa实验室: 光遗传学可激活"遗忘"的记忆
    """

    def _init_silent_engram_store(self):
        """初始化沉默印迹存储（在__init__中调用）"""
        if not hasattr(self, 'silent_engram_store'):
            # 获取持久化路径
            persistence_path = None
            if hasattr(self, 'data_dir') and self.data_dir:
                import os
                persistence_path = os.path.join(self.data_dir, 'silent_engrams.json')

            self.silent_engram_store = SilentEngramStore(
                max_engrams=getattr(self, 'capacity', 20000) // 2,  # 沉默容量为活跃容量的一半
                default_threshold=0.85,
                threshold_decay_rate=0.005,  # 每天降低0.5%
                min_threshold=0.6,
                persistence_path=persistence_path
            )
            logger.info("SilentEngramStore initialized for Hippocampus")

    async def _trigger_forgetting(self):
        """
        触发遗忘机制 - 转为沉默印迹而非删除

        改进：
        1. 被遗忘的记忆转为沉默印迹
        2. 保留检索键（向量、实体、时间）
        3. 强线索可以重新激活

        神经科学依据:
        - 海马体的遗忘是选择性的,不是简单的时间或阈值决策
        - 综合考虑重要性、情绪、访问频率、时间衰减

        文献: Richards & Frankland (2017) "The Persistence and Transience of Memory"
        """
        # 确保沉默印迹存储已初始化
        self._init_silent_engram_store()

        now = datetime.now()

        # LLM决策保护策略
        protected = []
        forgettable = []

        # 对每个记忆进行保护判断
        for mem in self.memories:
            # 基本保护: 最近记忆总是保护 (时间衰减曲线)
            time_ago_hours = (now - mem.timestamp).total_seconds() / 3600
            if time_ago_hours < 24:  # 24小时内必保护
                protected.append(mem)
                continue

            # LLM决策是否保护 (综合判断,非硬编码阈值)
            should_protect = await self._should_protect_from_forgetting(mem, time_ago_hours)

            if should_protect:
                protected.append(mem)
            else:
                forgettable.append(mem)

        # 如果没有可遗忘的,直接返回
        if not forgettable:
            return

        # 从forgettable中选择遗忘的记忆 (动态比例)
        # 不是固定20%,而是根据容量压力动态调整
        capacity_pressure = len(self.memories) / self.capacity
        if capacity_pressure > 0.9:
            forget_ratio = 0.3  # 高压力: 遗忘30%
        elif capacity_pressure > 0.7:
            forget_ratio = 0.2  # 中压力: 遗忘20%
        else:
            forget_ratio = 0.1  # 低压力: 遗忘10%

        forgettable.sort(
            key=lambda m: (m.importance, m.access_count, m.timestamp),
            reverse=False  # 升序 - 最不重要的在前
        )

        forget_count = max(1, int(len(forgettable) * forget_ratio))
        to_silence = forgettable[:forget_count]
        kept_forgettable = forgettable[forget_count:]

        # ========== 核心改进：转为沉默印迹而非删除 ==========
        silenced_count = 0
        for mem in to_silence:
            # 获取记忆的embedding
            embedding = None
            if hasattr(mem, 'embedding') and mem.embedding is not None:
                embedding = mem.embedding
            elif hasattr(self, 'embedding_service') and self.embedding_service:
                try:
                    embedding = await self.embedding_service.get_embedding(mem.content)
                    if embedding:
                        embedding = np.array(embedding)
                except Exception as e:
                    logger.debug(f"Failed to get embedding for silencing: {e}")

            # 获取实体
            entities = []
            if hasattr(mem, 'entities') and mem.entities:
                entities = mem.entities
            elif hasattr(mem, 'metadata') and mem.metadata:
                entities = mem.metadata.get('entities', [])

            # 转为沉默印迹
            self.silent_engram_store.silence_memory(
                memory_id=mem.id,
                content=mem.content,
                embedding=embedding,
                entities=entities,
                timestamp=mem.timestamp,
                importance=mem.importance,
                emotion_intensity=getattr(mem, 'emotion_intensity', 0.0),
                reason="capacity_pressure" if capacity_pressure > 0.7 else "low_importance"
            )
            silenced_count += 1

            # 从活跃存储中移除
            if mem.id in self.memory_dict:
                del self.memory_dict[mem.id]

        # 更新memories列表
        self.memories = protected + kept_forgettable

        # 重建索引
        self._rebuild_indexes()

        self.total_forgotten += silenced_count

        logger.info(
            f"Forgetting triggered: {silenced_count} memories silenced "
            f"(not deleted), capacity_pressure={capacity_pressure:.2f}"
        )

    async def _should_protect_from_forgetting(self, memory: EpisodicMemory, time_ago_hours: float) -> bool:
        """
        LLM决策是否保护记忆免于遗忘

        考虑因素:
        - 重要性
        - 访问频率
        - 情绪强度
        - 时间衰减
        """

        # 快速规则: 高访问频率或强情绪总是保护
        if memory.access_count >= 3 or memory.emotion_intensity > 0.8:
            return True

        # 使用LLM综合判断 (采样决策,不是每个都调用LLM)
        # 对于边界情况才调用LLM
        if 0.4 < memory.importance < 0.7:
            try:
                decision_prompt = f"""判断是否保护以下记忆免于遗忘:

记忆: {memory.content[:100]}
- 重要性: {memory.importance}
- 访问次数: {memory.access_count}
- 距今时间: {time_ago_hours:.1f}小时
- 情绪强度: {memory.emotion_intensity}

考虑艾宾浩斯遗忘曲线和记忆特征,判断是否保留。

返回JSON: {{"protect": true/false, "reason": "简短理由"}}"""

                response = await self.call_llm(decision_prompt, max_tokens=100, temperature=0.3, quick_fail=True)

                import json
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    decision = json.loads(json_match.group())
                    return decision.get('protect', memory.importance >= 0.5)

            except (json.JSONDecodeError) as e:
                # LLM失败,使用简化规则
                pass

        # Fallback规则
        return memory.importance >= 0.5

    async def get_forgetting_candidates(
        self,
        bottom_percentile: float = 0.2
    ) -> List[Dict[str, Any]]:
        """
        获取遗忘候选记忆

        用于协调层的遗忘流程:
        - 返回重要性和访问频率最低的记忆
        - 由ForgettingAgent评估是否真正遗忘

        Args:
            bottom_percentile: 底部百分比 (默认0.2 = 20%)

        Returns:
            候选记忆列表 (字典格式)
        """
        if not self.memories:
            return []

        # 按重要性、访问次数、时间排序
        sorted_memories = sorted(
            self.memories,
            key=lambda m: (m.importance, m.access_count, m.timestamp),
            reverse=False  # 升序 - 最低价值的在前
        )

        # 取底部百分比
        candidate_count = max(1, int(len(sorted_memories) * bottom_percentile))
        candidates = sorted_memories[:candidate_count]

        logger.info(f"Low-access memory candidates: {len(candidates)} memories "
                   f"(bottom {bottom_percentile*100:.0f}%)")

        return [self._memory_to_dict(mem) for mem in candidates]

    async def forget_memories(self, memory_ids: List[str]) -> int:
        """
        执行记忆遗忘 - 转为沉默印迹

        由协调层在ForgettingAgent评估后调用

        Args:
            memory_ids: 要遗忘的记忆ID列表

        Returns:
            实际遗忘(沉默化)的记忆数量
        """
        # 确保沉默印迹存储已初始化
        self._init_silent_engram_store()

        silenced_count = 0
        forgotten_ids = set(memory_ids)

        # 找到要遗忘的记忆
        to_silence = [m for m in self.memories if m.id in forgotten_ids]

        for mem in to_silence:
            # 获取embedding
            embedding = None
            if hasattr(mem, 'embedding') and mem.embedding is not None:
                embedding = mem.embedding

            # 获取实体
            entities = []
            if hasattr(mem, 'entities') and mem.entities:
                entities = mem.entities
            elif hasattr(mem, 'metadata') and mem.metadata:
                entities = mem.metadata.get('entities', [])

            # 转为沉默印迹
            self.silent_engram_store.silence_memory(
                memory_id=mem.id,
                content=mem.content,
                embedding=embedding,
                entities=entities,
                timestamp=mem.timestamp,
                importance=mem.importance,
                emotion_intensity=getattr(mem, 'emotion_intensity', 0.0),
                reason="explicit_forget"
            )
            silenced_count += 1

        # 从列表中移除
        self.memories = [m for m in self.memories if m.id not in forgotten_ids]

        # 从字典中移除
        for mem_id in memory_ids:
            if mem_id in self.memory_dict:
                del self.memory_dict[mem_id]

        # 重建索引
        self._rebuild_indexes()

        self.total_forgotten += silenced_count

        logger.info(f"Memories silenced: {silenced_count} (converted to silent engrams)")

        return silenced_count

    async def try_reactivate_silent_memories(
        self,
        query_vector: Optional[np.ndarray] = None,
        query_entities: Optional[List[str]] = None,
        query_time_range: Optional[Tuple[datetime, datetime]] = None,
        boost_factor: float = 1.0,
        max_reactivations: int = 3
    ) -> List[Dict[str, Any]]:
        """
        尝试重新激活沉默印迹

        在检索时调用，尝试激活匹配的沉默记忆

        Args:
            query_vector: 查询向量
            query_entities: 查询实体
            query_time_range: 查询时间范围
            boost_factor: 激活增强因子（强线索时增大）
            max_reactivations: 最大激活数量

        Returns:
            重新激活的记忆列表
        """
        # 确保沉默印迹存储已初始化
        self._init_silent_engram_store()

        # 尝试激活
        activated = self.silent_engram_store.try_reactivate(
            query_vector=query_vector,
            query_entities=query_entities,
            query_time_range=query_time_range,
            boost_factor=boost_factor
        )

        if not activated:
            return []

        reactivated_memories = []

        # 限制激活数量
        for memory_id, score, engram in activated[:max_reactivations]:
            # 尝试恢复完整记忆
            # 注意：这里需要从外部存储（如ValueStore）恢复内容
            # 目前返回基本信息，完整恢复由调用方处理

            reactivated_info = {
                'memory_id': memory_id,
                'activation_score': score,
                'entities': engram.key_entities,
                'timestamp': engram.key_timestamp.isoformat(),
                'original_importance': engram.original_importance,
                'silence_reason': engram.silence_reason,
                'silence_timestamp': engram.silence_timestamp.isoformat(),
                'needs_full_restoration': True  # 标记需要完整恢复
            }

            reactivated_memories.append(reactivated_info)

            logger.info(
                f"Silent engram reactivated: {memory_id}, "
                f"score={score:.3f}, entities={engram.key_entities}"
            )

        return reactivated_memories

    async def restore_silent_memory(
        self,
        memory_id: str,
        content: str,
        embedding: Optional[np.ndarray] = None
    ) -> Optional[EpisodicMemory]:
        """
        完全恢复沉默印迹为活跃记忆

        当沉默印迹被成功激活后，调用此方法恢复完整记忆

        Args:
            memory_id: 记忆ID
            content: 记忆内容（从ValueStore恢复）
            embedding: 记忆向量

        Returns:
            恢复的记忆对象，如果失败返回None
        """
        self._init_silent_engram_store()

        if memory_id not in self.silent_engram_store.engrams:
            logger.warning(f"Silent engram not found: {memory_id}")
            return None

        engram = self.silent_engram_store.engrams[memory_id]

        # 创建新的活跃记忆
        restored_memory = EpisodicMemory(
            id=memory_id,
            content=content,
            timestamp=engram.key_timestamp,
            importance=engram.original_importance * 1.1,  # 重新激活的记忆重要性提升
            emotion_intensity=engram.original_emotion_intensity,
            access_count=1,  # 重置访问计数
            entities=engram.key_entities,
            metadata={
                'reactivated': True,
                'reactivation_time': datetime.now().isoformat(),
                'original_silence_reason': engram.silence_reason
            }
        )

        if embedding is not None:
            restored_memory.embedding = embedding

        # 添加到活跃存储
        self.memories.append(restored_memory)
        self.memory_dict[memory_id] = restored_memory

        # 从沉默印迹存储中移除
        self.silent_engram_store.mark_reactivated(memory_id)

        # 重建索引
        self._rebuild_indexes()

        logger.info(f"Silent memory fully restored: {memory_id}")

        return restored_memory

    def get_silent_engram_statistics(self) -> Dict[str, Any]:
        """获取沉默印迹统计信息"""
        self._init_silent_engram_store()
        return self.silent_engram_store.get_statistics()

    def save_silent_engrams(self):
        """持久化沉默印迹"""
        if hasattr(self, 'silent_engram_store'):
            self.silent_engram_store.save_to_disk()
