"""
Memory tracing operations for Temporal Lobe Agent
记忆溯源模块(语义→情节)
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class TracingMixin:
    """Memory tracing operations mixin for TemporalLobeAgent"""

    async def get_memory_by_id(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        通过ID获取单个记忆

        P0硬编码清除：协调层需要这个基础接口来实现反向溯源
        存储层只提供简单的ID查询，不涉及跨脑区调用

        Args:
            memory_id: 记忆ID

        Returns:
            记忆字典，如果不存在返回None
        """
        if memory_id in self.memory_dict:
            mem = self.memory_dict[memory_id]
            mem.access_count += 1
            mem.last_accessed = datetime.now()
            return self._memory_to_dict(mem)
        else:
            return None

    async def trace_semantic_to_episodic(
        self,
        semantic_memory_id: str,
        hippocampus_agent
    ) -> Dict[str, Any]:
        """
        Phase 2核心功能: 反向溯源 (语义记忆 → 源情节记忆)

        理论依据:
        - Moscovitch et al. (2005) - 记忆痕迹理论 (MTT)
        - 语义记忆源于情节记忆的抽象化和巩固

        Phase 2增强:
        - 支持从语义记忆反向追溯到源情节记忆
        - 用于解释"我为什么知道这个知识?"

        Args:
            semantic_memory_id: 语义记忆ID
            hippocampus_agent: Hippocampus智能体实例

        Returns:
            {
                'semantic_memory': Dict,
                'source_episodic_memories': List[Dict],
                'trace_successful': bool
            }
        """

        # Step 1: 获取语义记忆
        if semantic_memory_id not in self.memory_dict:
            logger.warning(f"⚠️ Semantic memory not found: {semantic_memory_id}")
            return {
                'semantic_memory': None,
                'source_episodic_memories': [],
                'trace_successful': False,
                'error': 'semantic_memory_not_found'
            }

        semantic_mem = self.memory_dict[semantic_memory_id]

        # Step 2: 从metadata中查找源情节记忆ID
        source_ids = semantic_mem.metadata.get('source_episodic_ids', [])

        if not source_ids:
            # Fallback: 使用实体和时间搜索海马体
            if semantic_mem.entities and hippocampus_agent:
                # 算法: 实体匹配 + 时间接近
                episodic_results = await hippocampus_agent.search_memories(
                    query=" ".join(semantic_mem.entities),
                    k=5,
                    time_range=(
                        semantic_mem.event_time.isoformat() if semantic_mem.event_time else None,
                        semantic_mem.timestamp.isoformat()
                    ) if semantic_mem.event_time else None
                )

                source_memories = episodic_results.get('memories', [])
            else:
                source_memories = []
        else:
            # Step 3: 从Hippocampus检索源记忆
            source_memories = []

            if hippocampus_agent:
                for ep_id in source_ids:
                    ep_mem = await hippocampus_agent.retrieve_memory_by_id(ep_id)
                    if ep_mem:
                        source_memories.append(ep_mem)

        return {
            'semantic_memory': self._memory_to_dict(semantic_mem),
            'source_episodic_memories': source_memories,
            'trace_successful': len(source_memories) > 0,
            'trace_method': 'metadata' if source_ids else 'entity_search'
        }
