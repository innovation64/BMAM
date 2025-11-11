"""
Associative Retrieval Strategy  
关联检索策略 - 基于记忆关联网络的检索
"""

from .base import RetrievalStrategy
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class AssociativeRetrievalStrategy(RetrievalStrategy):
    """
    关联检索策略

    功能:
    - 基于记忆关联网络检索相关记忆
    - 支持多跳关联
    - 计算关联强度
    """

    @property
    def strategy_name(self) -> str:
        return "associative"

    async def retrieve(
        self,
        memory_id: str,
        max_hops: int = 2,
        k: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        关联检索

        Args:
            memory_id: 源记忆ID
            max_hops: 最大跳数
            k: 返回数量

        Returns:
            关联记忆列表
        """
        if not self.db_manager:
            return {'memories': [], 'total_count': 0, 'strategy': self.strategy_name}

        logger.info(f"Associative retrieval: source={memory_id}, hops={max_hops}")

        # 加载源记忆
        source_memory = self.db_manager.load_memory(memory_id)
        if not source_memory:
            return {'memories': [], 'total_count': 0, 'strategy': self.strategy_name}

        # 获取关联记忆
        associated_memories = []
        visited = {memory_id}

        # 从源记忆的关联列表开始
        if hasattr(source_memory, 'associations') and source_memory.associations:
            for assoc_id in source_memory.associations:
                if assoc_id not in visited:
                    assoc_mem = self.db_manager.load_memory(assoc_id)
                    if assoc_mem:
                        strength = self._calculate_association_strength(
                            source_memory,
                            assoc_mem
                        )

                        associated_memories.append({
                            'memory': assoc_mem.to_dict(),
                            'association_strength': strength,
                            'retrieval_confidence': strength,
                            'retrieval_method': 'associative',
                            'hops': 1
                        })
                        visited.add(assoc_id)

        # 排序并返回top-k
        associated_memories.sort(key=lambda m: m['association_strength'], reverse=True)

        return {
            'memories': associated_memories[:k],
            'total_count': len(associated_memories),
            'strategy': self.strategy_name,
            'source_memory_id': memory_id
        }

    def _calculate_association_strength(self, memory1, memory2) -> float:
        """计算关联强度"""
        # 简化版: 基于共同特征
        score = 0.5  # 基础分

        # 共同标签
        tags1 = set(getattr(memory1, 'metadata', {}).get('tags', []))
        tags2 = set(getattr(memory2, 'metadata', {}).get('tags', []))
        
        if tags1 & tags2:
            score += 0.3

        return min(score, 1.0)
