"""
Hippocampus Agent - 海马体智能体
对应脑区: 海马体 (Hippocampus)
主要功能: 情节记忆存储+检索+巩固
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)


from .core import EpisodicMemory, HippocampusAgentCore
import asyncio


class ForgettingMixin:
    """遗忘机制功能"""
    async def _trigger_forgetting(self):
        """
        触发遗忘机制 - 使用LLM动态决策保护策略

        神经科学依据:
        - 海马体的遗忘是选择性的,不是简单的时间或阈值决策
        - 综合考虑重要性、情绪、访问频率、时间衰减

        文献: Richards & Frankland (2017) "The Persistence and Transience of Memory"
        """
        from datetime import datetime, timedelta

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
        forgotten = forgettable[:forget_count]
        kept_forgettable = forgettable[forget_count:]

        # 更新memories列表
        self.memories = protected + kept_forgettable

        # 更新memory_dict
        for mem in forgotten:
            if mem.id in self.memory_dict:
                del self.memory_dict[mem.id]

        # 重建索引
        self._rebuild_indexes()

        self.total_forgotten += forget_count



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
        执行记忆遗忘

        由协调层在ForgettingAgent评估后调用

        Args:
            memory_ids: 要遗忘的记忆ID列表

        Returns:
            实际遗忘的记忆数量
        """
        forgotten_count = 0
        forgotten_ids = set(memory_ids)

        # 从列表中移除
        self.memories = [m for m in self.memories if m.id not in forgotten_ids]

        # 从字典中移除
        for mem_id in memory_ids:
            if mem_id in self.memory_dict:
                del self.memory_dict[mem_id]
                forgotten_count += 1

        # 重建索引
        self._rebuild_indexes()

        self.total_forgotten += forgotten_count


        return forgotten_count

