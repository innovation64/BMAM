"""
Query Cache System for Fast Response
查询缓存系统 - 避免重复推理,加速回答

核心功能:
1. 缓存recent queries的推理结果
2. 语义相似query直接返回cached结果
3. TTL过期机制 (避免stale answers)
4. LRU淘汰策略 (容量限制)

脑区对应: BasalGanglia (程序性记忆 - 自动化反应)
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class CachedQuery:
    """缓存的查询结果"""
    query: str
    query_hash: str
    response: str
    confidence: float
    embedding: Optional[List[float]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)


class QueryCache:
    """
    查询缓存 - 基于语义相似度的intelligent cache

    特性:
    - 完全相同query → 直接命中 (hash match)
    - 语义相似query → 近似命中 (embedding similarity)
    - TTL过期 (default 1 hour)
    - LRU淘汰 (max 1000 entries)
    """

    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: int = 3600,
        similarity_threshold: float = 0.85,
        embedding_service=None
    ):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.similarity_threshold = similarity_threshold
        self.embedding_service = embedding_service

        # Hash-based cache (exact match)
        self.hash_cache: OrderedDict[str, CachedQuery] = OrderedDict()

        # Semantic cache (similarity match)
        self.semantic_cache: List[CachedQuery] = []

        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0
        }


    def _compute_hash(self, query: str) -> str:
        """计算query的hash"""
        return hashlib.md5(query.lower().strip().encode('utf-8')).hexdigest()

    async def get(self, query: str, query_embedding: Optional[List[float]] = None) -> Optional[Tuple[str, float, str]]:
        """
        获取缓存的响应

        Returns:
            (response, confidence, cache_type) if hit, else None
            cache_type: 'exact' or 'semantic'
        """
        query_hash = self._compute_hash(query)

        # 1️⃣ Try exact match (hash cache)
        if query_hash in self.hash_cache:
            cached = self.hash_cache[query_hash]

            # Check TTL
            age = (datetime.now() - cached.timestamp).total_seconds()
            if age > self.ttl_seconds:
                # Expired
                del self.hash_cache[query_hash]
                self.stats['expirations'] += 1
            else:
                # Hit!
                cached.access_count += 1
                cached.last_accessed = datetime.now()
                self.hash_cache.move_to_end(query_hash)  # LRU update
                self.stats['hits'] += 1
                return (cached.response, cached.confidence, 'exact')

        # 2️⃣ Try semantic match (if embedding available)
        if query_embedding and self.semantic_cache:
            best_match, best_similarity = await self._find_semantic_match(query_embedding)

            if best_match and best_similarity >= self.similarity_threshold:
                # Check TTL
                age = (datetime.now() - best_match.timestamp).total_seconds()
                if age > self.ttl_seconds:
                    self.semantic_cache.remove(best_match)
                    self.stats['expirations'] += 1
                else:
                    # Semantic hit!
                    best_match.access_count += 1
                    best_match.last_accessed = datetime.now()
                    self.stats['hits'] += 1
                    return (best_match.response, best_match.confidence, 'semantic')

        # Miss
        self.stats['misses'] += 1
        return None

    async def _find_semantic_match(self, query_embedding: List[float]) -> Tuple[Optional[CachedQuery], float]:
        """在semantic cache中查找最相似的query"""
        if not self.semantic_cache:
            return None, 0.0

        import numpy as np
        query_vec = np.array(query_embedding)

        best_match = None
        best_similarity = 0.0

        for cached in self.semantic_cache:
            if cached.embedding is None:
                continue

            cached_vec = np.array(cached.embedding)
            similarity = self._cosine_similarity(query_vec, cached_vec)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = cached

        return best_match, best_similarity

    def _cosine_similarity(self, vec1, vec2) -> float:
        """计算余弦相似度"""
        import numpy as np
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    async def put(
        self,
        query: str,
        response: str,
        confidence: float,
        query_embedding: Optional[List[float]] = None
    ):
        """
        存储query结果到缓存

        Args:
            query: 用户query
            response: 系统响应
            confidence: 响应confidence (0-1)
            query_embedding: query的语义embedding
        """
        query_hash = self._compute_hash(query)

        cached = CachedQuery(
            query=query,
            query_hash=query_hash,
            response=response,
            confidence=confidence,
            embedding=query_embedding
        )

        # Store in hash cache
        self.hash_cache[query_hash] = cached
        self.hash_cache.move_to_end(query_hash)

        # Store in semantic cache (if embedding available)
        if query_embedding:
            self.semantic_cache.append(cached)

        # Evict if over capacity
        while len(self.hash_cache) > self.max_size:
            evicted_hash, evicted_cached = self.hash_cache.popitem(last=False)
            if evicted_cached in self.semantic_cache:
                self.semantic_cache.remove(evicted_cached)
            self.stats['evictions'] += 1


    def clear(self):
        """清空缓存"""
        count = len(self.hash_cache)
        self.hash_cache.clear()
        self.semantic_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0.0

        return {
            'size': len(self.hash_cache),
            'max_size': self.max_size,
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'hit_rate': round(hit_rate, 1),
            'evictions': self.stats['evictions'],
            'expirations': self.stats['expirations']
        }


# ============================================================
# Singleton Pattern with Thread Safety
# ============================================================
import threading

class QueryCacheSingleton:
    """
    Thread-safe singleton for QueryCache

    Pattern: Singleton with lazy initialization and thread safety
    Why: Global cache with stateful storage of query results
    """
    _instance: Optional['QueryCache'] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(
        cls,
        max_size: int = 1000,
        ttl_seconds: int = 3600,
        similarity_threshold: float = 0.85,
        embedding_service=None
    ) -> 'QueryCache':
        """
        获取全局query cache实例 (thread-safe)

        Args:
            max_size: Maximum cache size (only used on first initialization)
            ttl_seconds: Time-to-live in seconds (only used on first initialization)
            similarity_threshold: Similarity threshold for semantic matching (only used on first initialization)
            embedding_service: Embedding service instance (only used on first initialization)
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = QueryCache(
                        max_size=max_size,
                        ttl_seconds=ttl_seconds,
                        similarity_threshold=similarity_threshold,
                        embedding_service=embedding_service
                    )
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset singleton instance (mainly for testing)"""
        with cls._lock:
            if cls._instance:
                cls._instance.clear()
            cls._instance = None


def get_query_cache(
    max_size: int = 1000,
    ttl_seconds: int = 3600,
    similarity_threshold: float = 0.85,
    embedding_service=None
) -> QueryCache:
    """
    获取全局query cache实例 (backward compatible)

    Args:
        max_size: Maximum cache size (only used on first initialization)
        ttl_seconds: Time-to-live in seconds (only used on first initialization)
        similarity_threshold: Similarity threshold (only used on first initialization)
        embedding_service: Embedding service instance (only used on first initialization)
    """
    return QueryCacheSingleton.get_instance(
        max_size=max_size,
        ttl_seconds=ttl_seconds,
        similarity_threshold=similarity_threshold,
        embedding_service=embedding_service
    )
