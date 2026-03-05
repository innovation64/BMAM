"""
Pattern Completion Strategy
模式补全策略 - 基于部分线索补全完整模式
"""

from .base import RetrievalStrategy
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class PatternCompletionStrategy(RetrievalStrategy):
    """
    模式补全策略

    功能:
    - 基于部分线索补全完整记忆
    - 支持模糊匹配
    - 计算补全置信度
    
    应用场景:
    - 用户只记得部分信息
    - 提示词触发完整记忆
    """

    @property
    def strategy_name(self) -> str:
        return "pattern"

    async def retrieve(
        self,
        partial_cue: str,
        k: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        模式补全检索

        Args:
            partial_cue: 部分线索文本
            k: 返回数量

        Returns:
            补全的记忆列表
        """
        if not self.db_manager or not partial_cue:
            return {'memories': [], 'total_count': 0, 'strategy': self.strategy_name}

        logger.info(f"Pattern completion: partial_cue='{partial_cue[:50]}...'")

        # 1. 使用向量搜索找到候选记忆
        candidates = []
        
        if self.embedding_service and self.vector_db:
            try:
                # 生成部分线索的embedding
                partial_embedding = await self.embedding_service.encode_text(partial_cue)
                
                # 向量搜索 (较低阈值以获取更多候选)
                similar_memories = self.vector_db.search(
                    partial_embedding,
                    k=k * 3,  # 获取3倍候选
                    threshold=0.2
                )
                
                # 加载记忆对象
                for memory_id, similarity in similar_memories:
                    memory = self.db_manager.load_memory(memory_id)
                    if memory:
                        candidates.append((memory, similarity))
                        
            except Exception as e:
                logger.error(f"Vector search failed: {e}")

        # 2. 如果向量搜索失败，使用关键词搜索
        if not candidates:
            all_memories = self.db_manager.search_memories(limit=100)
            for memory in all_memories:
                # 简单的文本包含检查
                if partial_cue.lower() in memory.content.lower():
                    candidates.append((memory, 0.5))

        # 3. 计算补全置信度
        completed_memories = []
        for memory, similarity in candidates:
            completion_confidence = self._calculate_completion_confidence(
                partial_cue,
                memory,
                similarity
            )
            
            # 尝试补全模式
            completed_pattern = await self._complete_pattern(partial_cue, memory)
            
            completed_memories.append({
                'memory': memory.to_dict(),
                'similarity': similarity,
                'completion_confidence': completion_confidence,
                'retrieval_confidence': completion_confidence,
                'retrieval_method': 'pattern',
                'completed_pattern': completed_pattern,
                'partial_cue': partial_cue
            })

        # 4. 排序并返回top-k
        completed_memories.sort(
            key=lambda m: m['completion_confidence'],
            reverse=True
        )

        return {
            'memories': completed_memories[:k],
            'total_count': len(completed_memories),
            'strategy': self.strategy_name,
            'partial_cue': partial_cue
        }

    def _calculate_completion_confidence(
        self,
        partial: str,
        memory,
        similarity: float
    ) -> float:
        """
        计算补全置信度

        考虑因素:
        - 向量相似度
        - 文本重叠度
        - 记忆重要性
        """
        # 基础相似度
        base_confidence = similarity

        # 文本重叠度
        partial_lower = partial.lower()
        content_lower = memory.content.lower()
        
        overlap_score = 0.0
        if partial_lower in content_lower:
            # 完全包含
            overlap_score = 0.3
        else:
            # 部分匹配
            partial_words = set(partial_lower.split())
            content_words = set(content_lower.split())
            if partial_words and content_words:
                overlap_ratio = len(partial_words & content_words) / len(partial_words)
                overlap_score = 0.2 * overlap_ratio

        # 记忆重要性加成
        importance_bonus = memory.importance * 0.1 if hasattr(memory, 'importance') else 0.0

        # 综合置信度
        confidence = base_confidence + overlap_score + importance_bonus

        return min(confidence, 1.0)

    async def _complete_pattern(self, partial: str, memory) -> str:
        """
        补全模式

        从记忆中提取完整模式

        Args:
            partial: 部分线索
            memory: 记忆对象

        Returns:
            补全的完整文本
        """
        # 简化版: 返回记忆的完整内容
        # 在实际应用中，可以使用LLM进行智能补全
        
        content = memory.content if hasattr(memory, 'content') else ''
        
        # 如果部分线索在内容中，返回完整内容
        if partial.lower() in content.lower():
            return content
        
        # 否则返回部分线索 + 记忆内容的组合
        return f"{partial} → {content[:200]}"
