"""
Context Window Limiter for Reasoning
推理上下文限制器 - 保证推理上下文始终在合理容量内

核心功能:
1. 限制传递给LLM的记忆数量
2. 智能选择最相关的记忆
3. 防止context overflow导致的性能下降
4. Token counting for precise control

设计原则: 人脑前额叶working memory容量有限(7±2 items)
"""

from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class ContextLimiter:
    """
    上下文限制器

    功能:
    - 限制检索结果数量
    - 智能排序和过滤
    - Token budget管理
    - 分层context assembly
    """

    def __init__(
        self,
        max_episodic_items: int = 50,
        max_semantic_items: int = 100,
        max_kg_triples: int = 20,
        max_tokens: int = 8000,  # Safe limit for LLM context
        min_relevance: float = 0.3
    ):
        self.max_episodic_items = max_episodic_items
        self.max_semantic_items = max_semantic_items
        self.max_kg_triples = max_kg_triples
        self.max_tokens = max_tokens
        self.min_relevance = min_relevance

        self.stats = {
            'total_items_received': 0,
            'total_items_filtered': 0,
            'total_tokens_saved': 0
        }


    def limit_context(
        self,
        episodic_memories: List[Dict[str, Any]],
        semantic_memories: List[Dict[str, Any]],
        kg_triples: List[tuple],
        query: str
    ) -> Dict[str, Any]:
        """
        限制推理上下文到合理大小

        Returns:
            {
                'episodic': List[Dict],  # 过滤后的情节记忆
                'semantic': List[Dict],  # 过滤后的语义记忆
                'kg_triples': List[tuple],  # 过滤后的KG三元组
                'stats': Dict,  # 统计信息
                'token_estimate': int
            }
        """

        original_counts = {
            'episodic': len(episodic_memories),
            'semantic': len(semantic_memories),
            'kg_triples': len(kg_triples)
        }

        # 1️⃣ Filter by relevance
        filtered_episodic = self._filter_by_relevance(episodic_memories)
        filtered_semantic = self._filter_by_relevance(semantic_memories)

        # 2️⃣ Sort by importance
        filtered_episodic = self._sort_by_priority(filtered_episodic)
        filtered_semantic = self._sort_by_priority(filtered_semantic)

        # 3️⃣ Limit by count
        limited_episodic = filtered_episodic[:self.max_episodic_items]
        limited_semantic = filtered_semantic[:self.max_semantic_items]
        limited_kg = kg_triples[:self.max_kg_triples]

        # 4️⃣ Estimate tokens and adjust if needed
        token_estimate = self._estimate_tokens(limited_episodic, limited_semantic, limited_kg, query)

        if token_estimate > self.max_tokens:
            # Further reduction needed
            limited_episodic, limited_semantic, limited_kg = self._reduce_by_tokens(
                limited_episodic, limited_semantic, limited_kg, query
            )
            token_estimate = self._estimate_tokens(limited_episodic, limited_semantic, limited_kg, query)

        # Update stats
        self.stats['total_items_received'] += sum(original_counts.values())
        final_count = len(limited_episodic) + len(limited_semantic) + len(limited_kg)
        self.stats['total_items_filtered'] += (sum(original_counts.values()) - final_count)

        logger.info(
            f"📊 Context limited: episodic {original_counts['episodic']}→{len(limited_episodic)}, "
            f"semantic {original_counts['semantic']}→{len(limited_semantic)}, "
            f"kg {original_counts['kg_triples']}→{len(limited_kg)}, "
            f"tokens≈{token_estimate}"
        )

        return {
            'episodic': limited_episodic,
            'semantic': limited_semantic,
            'kg_triples': limited_kg,
            'stats': {
                'original': original_counts,
                'filtered': {
                    'episodic': len(limited_episodic),
                    'semantic': len(limited_semantic),
                    'kg_triples': len(limited_kg)
                },
                'reduction_rate': round((1 - final_count / sum(original_counts.values())) * 100, 1) if sum(original_counts.values()) > 0 else 0
            },
            'token_estimate': token_estimate
        }

    def _filter_by_relevance(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤低相关性记忆"""
        return [
            m for m in memories
            if m.get('relevance', 0) >= self.min_relevance
        ]

    def _sort_by_priority(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按优先级排序 (relevance * importance * recency)"""
        def priority_score(mem: Dict[str, Any]) -> float:
            relevance = mem.get('relevance', 0.5)
            importance = mem.get('importance', 0.5)

            # Recency bonus (if timestamp available)
            recency_score = 1.0
            if 'timestamp' in mem:
                from datetime import datetime
                try:
                    if isinstance(mem['timestamp'], str):
                        timestamp = datetime.fromisoformat(mem['timestamp'])
                    else:
                        timestamp = mem['timestamp']

                    age_hours = (datetime.now() - timestamp).total_seconds() / 3600
                    # Decay: 1.0 for recent, 0.5 for 24h+
                    recency_score = max(0.5, 1.0 - (age_hours / 48))
                except (ValueError, TypeError, AttributeError) as e:
                    logger.debug(f"Failed to calculate recency score: {e}")

            return relevance * importance * recency_score

        return sorted(memories, key=priority_score, reverse=True)

    def _estimate_tokens(
        self,
        episodic: List[Dict[str, Any]],
        semantic: List[Dict[str, Any]],
        kg_triples: List[tuple],
        query: str
    ) -> int:
        """估算token数量 (rough estimate: 1 token ≈ 4 characters)"""
        total_chars = len(query)

        for mem in episodic:
            total_chars += len(mem.get('content', ''))

        for mem in semantic:
            total_chars += len(mem.get('content', ''))

        for triple in kg_triples:
            total_chars += sum(len(str(x)) for x in triple)

        # Add overhead for formatting
        total_chars = int(total_chars * 1.2)

        # Convert to tokens (rough estimate)
        return total_chars // 4

    def _reduce_by_tokens(
        self,
        episodic: List[Dict[str, Any]],
        semantic: List[Dict[str, Any]],
        kg_triples: List[tuple],
        query: str
    ) -> tuple:
        """进一步减少items以满足token budget"""

        # Progressive reduction strategy
        while self._estimate_tokens(episodic, semantic, kg_triples, query) > self.max_tokens:
            # Reduce in order: semantic > kg > episodic (keep episodic as most important)
            if len(semantic) > 20:
                semantic = semantic[:-1]
            elif len(kg_triples) > 5:
                kg_triples = kg_triples[:-1]
            elif len(episodic) > 10:
                episodic = episodic[:-1]
            else:
                break  # Can't reduce further

        return episodic, semantic, kg_triples

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_items_received': self.stats['total_items_received'],
            'total_items_filtered': self.stats['total_items_filtered'],
            'filter_rate': round(
                (self.stats['total_items_filtered'] / self.stats['total_items_received'] * 100)
                if self.stats['total_items_received'] > 0 else 0,
                1
            )
        }


# ============================================================
# Singleton Pattern with Thread Safety
# ============================================================
import threading

class ContextLimiterSingleton:
    """
    Thread-safe singleton for ContextLimiter

    Pattern: Singleton with lazy initialization and thread safety
    Why: Stateful service tracking context limitation statistics
    """
    _instance: Optional['ContextLimiter'] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, **kwargs) -> 'ContextLimiter':
        """
        获取全局context limiter实例 (thread-safe)

        Args:
            **kwargs: Configuration parameters (only used on first initialization)
                - max_episodic_items: int
                - max_semantic_items: int
                - max_kg_triples: int
                - max_tokens: int
                - min_relevance: float
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = ContextLimiter(**kwargs)
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset singleton instance (mainly for testing)"""
        with cls._lock:
            cls._instance = None


def get_context_limiter(**kwargs) -> ContextLimiter:
    """
    获取全局context limiter实例 (backward compatible)

    Args:
        **kwargs: Configuration parameters (only used on first initialization)
    """
    return ContextLimiterSingleton.get_instance(**kwargs)
