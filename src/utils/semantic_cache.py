"""
Semantic Caching for LLM and Retrieval Results
语义缓存 - 用于 LLM 响应和检索结果的智能缓存

Based on STEP3_PERFORMANCE_ANALYSIS_REPORT.md Phase 1 optimization:
- LLM Semantic Cache: 1 hour TTL, similarity threshold 0.95
- Retrieval Cache: 5 minutes TTL, query-based caching

Expected impact:
- LLM cache: 1.5-2x speedup for similar queries
- Retrieval cache: 1.1-1.2x speedup for repeated queries
"""

import time
import hashlib
import json
import numpy as np
from collections import OrderedDict
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from ..utils.config import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with timestamp and metadata"""
    value: Any
    timestamp: float
    embedding: Optional[np.ndarray] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMResponseCache:
    """
    Semantic cache for LLM responses

    Uses embedding similarity to match queries and return cached responses.
    Prevents redundant LLM calls for similar questions.
    """

    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: int = 3600,  # 1 hour
        similarity_threshold: float = 0.95,
        enable_cache: bool = True
    ):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.similarity_threshold = similarity_threshold
        self.enable_cache = enable_cache

        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

        logger.info(
            f"LLMResponseCache initialized: "
            f"max_size={max_size}, ttl={ttl_seconds}s, "
            f"threshold={similarity_threshold}, enabled={enable_cache}"
        )

    def _compute_key(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Compute cache key from query and context"""
        payload = {
            'query': query,
            'context': context or {}
        }
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.md5(serialized.encode('utf-8')).hexdigest()

    def _compute_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings"""
        if emb1 is None or emb2 is None:
            return 0.0

        # Normalize
        emb1_norm = emb1 / (np.linalg.norm(emb1) + 1e-8)
        emb2_norm = emb2 / (np.linalg.norm(emb2) + 1e-8)

        # Cosine similarity
        similarity = np.dot(emb1_norm, emb2_norm)
        return float(similarity)

    def _find_similar_entry(
        self,
        query_embedding: np.ndarray
    ) -> Optional[Tuple[str, CacheEntry]]:
        """
        Find the most similar cached entry

        Returns (key, entry) if similarity > threshold, else None
        """
        if query_embedding is None:
            return None

        best_key = None
        best_entry = None
        best_similarity = 0.0

        current_time = time.time()

        for key, entry in self.cache.items():
            # Skip expired entries
            if current_time - entry.timestamp > self.ttl_seconds:
                continue

            if entry.embedding is None:
                continue

            similarity = self._compute_similarity(query_embedding, entry.embedding)

            if similarity > best_similarity:
                best_similarity = similarity
                best_key = key
                best_entry = entry

        # Check if meets threshold
        if best_similarity >= self.similarity_threshold:
            logger.debug(
                f"Found similar cached entry: similarity={best_similarity:.3f}, "
                f"threshold={self.similarity_threshold}"
            )
            return (best_key, best_entry)

        return None

    def get(
        self,
        query: str,
        query_embedding: Optional[np.ndarray] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Get cached LLM response

        Args:
            query: The user query
            query_embedding: Optional embedding of the query for semantic matching
            context: Optional context dictionary

        Returns:
            Cached response if found, else None
        """
        if not self.enable_cache:
            return None

        # First try exact key match
        key = self._compute_key(query, context)

        current_time = time.time()

        if key in self.cache:
            entry = self.cache[key]

            # Check if expired
            if current_time - entry.timestamp > self.ttl_seconds:
                logger.debug(f"Cache entry expired: age={current_time - entry.timestamp:.1f}s")
                del self.cache[key]
                self.misses += 1
                return None

            # Move to end (LRU)
            self.cache.move_to_end(key)
            self.hits += 1

            logger.debug(
                f"LLM cache HIT (exact): query='{query[:50]}...', "
                f"age={current_time - entry.timestamp:.1f}s"
            )
            return entry.value

        # Try semantic similarity match
        if query_embedding is not None:
            similar = self._find_similar_entry(query_embedding)

            if similar:
                similar_key, similar_entry = similar

                # Move to end (LRU)
                self.cache.move_to_end(similar_key)
                self.hits += 1

                logger.debug(
                    f"LLM cache HIT (semantic): query='{query[:50]}...', "
                    f"age={current_time - similar_entry.timestamp:.1f}s"
                )
                return similar_entry.value

        self.misses += 1
        return None

    def put(
        self,
        query: str,
        response: str,
        query_embedding: Optional[np.ndarray] = None,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Store LLM response in cache

        Args:
            query: The user query
            response: The LLM response to cache
            query_embedding: Optional embedding for semantic matching
            context: Optional context dictionary
            metadata: Optional metadata
        """
        if not self.enable_cache:
            return

        key = self._compute_key(query, context)

        # Create cache entry
        entry = CacheEntry(
            value=response,
            timestamp=time.time(),
            embedding=query_embedding,
            metadata=metadata
        )

        # Add to cache
        self.cache[key] = entry
        self.cache.move_to_end(key)

        # Evict oldest if over capacity
        while len(self.cache) > self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            self.evictions += 1
            logger.debug(f"Evicted oldest cache entry: total_evictions={self.evictions}")

        logger.debug(
            f"LLM cache PUT: query='{query[:50]}...', "
            f"cache_size={len(self.cache)}/{self.max_size}"
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0

        # Count expired entries
        current_time = time.time()
        expired_count = sum(
            1 for entry in self.cache.values()
            if current_time - entry.timestamp > self.ttl_seconds
        )

        return {
            'enabled': self.enable_cache,
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'hit_rate': hit_rate,
            'expired_entries': expired_count,
            'ttl_seconds': self.ttl_seconds,
            'similarity_threshold': self.similarity_threshold
        }

    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        logger.info("LLM cache cleared")


class RetrievalCache:
    """
    Cache for memory retrieval results

    Stores retrieval results for identical or similar queries
    to avoid redundant FAISS searches and cross-region retrievals.
    """

    def __init__(
        self,
        max_size: int = 2000,
        ttl_seconds: int = 300,  # 5 minutes
        enable_cache: bool = True
    ):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.enable_cache = enable_cache

        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

        logger.info(
            f"RetrievalCache initialized: "
            f"max_size={max_size}, ttl={ttl_seconds}s, enabled={enable_cache}"
        )

    def _compute_key(
        self,
        query: str,
        k: int = 10,
        strategy: str = 'hybrid',
        regions: Optional[List[str]] = None
    ) -> str:
        """Compute cache key from retrieval parameters"""
        payload = {
            'query': query,
            'k': k,
            'strategy': strategy,
            'regions': sorted(regions) if regions else []
        }
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.md5(serialized.encode('utf-8')).hexdigest()

    def get(
        self,
        query: str,
        k: int = 10,
        strategy: str = 'hybrid',
        regions: Optional[List[str]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached retrieval results

        Args:
            query: The search query
            k: Number of results
            strategy: Retrieval strategy
            regions: Brain regions to search

        Returns:
            Cached results if found, else None
        """
        if not self.enable_cache:
            return None

        key = self._compute_key(query, k, strategy, regions)

        if key not in self.cache:
            self.misses += 1
            return None

        entry = self.cache[key]
        current_time = time.time()

        # Check if expired
        if current_time - entry.timestamp > self.ttl_seconds:
            logger.debug(f"Retrieval cache entry expired: age={current_time - entry.timestamp:.1f}s")
            del self.cache[key]
            self.misses += 1
            return None

        # Move to end (LRU)
        self.cache.move_to_end(key)
        self.hits += 1

        logger.debug(
            f"Retrieval cache HIT: query='{query[:50]}...', "
            f"k={k}, age={current_time - entry.timestamp:.1f}s"
        )

        return entry.value

    def put(
        self,
        query: str,
        results: List[Dict[str, Any]],
        k: int = 10,
        strategy: str = 'hybrid',
        regions: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Store retrieval results in cache

        Args:
            query: The search query
            results: The retrieval results to cache
            k: Number of results
            strategy: Retrieval strategy
            regions: Brain regions searched
            metadata: Optional metadata
        """
        if not self.enable_cache:
            return

        key = self._compute_key(query, k, strategy, regions)

        # Create cache entry
        entry = CacheEntry(
            value=results,
            timestamp=time.time(),
            metadata=metadata
        )

        # Add to cache
        self.cache[key] = entry
        self.cache.move_to_end(key)

        # Evict oldest if over capacity
        while len(self.cache) > self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            self.evictions += 1
            logger.debug(f"Evicted oldest retrieval cache entry: total_evictions={self.evictions}")

        logger.debug(
            f"Retrieval cache PUT: query='{query[:50]}...', "
            f"k={k}, results={len(results)}, cache_size={len(self.cache)}/{self.max_size}"
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0

        # Count expired entries
        current_time = time.time()
        expired_count = sum(
            1 for entry in self.cache.values()
            if current_time - entry.timestamp > self.ttl_seconds
        )

        return {
            'enabled': self.enable_cache,
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'hit_rate': hit_rate,
            'expired_entries': expired_count,
            'ttl_seconds': self.ttl_seconds
        }

    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        logger.info("Retrieval cache cleared")


class KGQueryCache:
    """
    Cache for Knowledge Graph query results

    Caches KG triple lookups and entity-based searches to avoid
    redundant database queries and LLM entity extraction calls.
    """

    def __init__(
        self,
        max_size: int = 500,
        ttl_seconds: int = 600,  # 10 minutes
        enable_cache: bool = True
    ):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.enable_cache = enable_cache

        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

        logger.info(
            f"KGQueryCache initialized: "
            f"max_size={max_size}, ttl={ttl_seconds}s, enabled={enable_cache}"
        )

    def _compute_key(self, query: str, entities: Optional[List[str]] = None) -> str:
        """Compute cache key from query and entities"""
        payload = {
            'query': query.lower().strip(),
            'entities': sorted([e.lower() for e in entities]) if entities else []
        }
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.md5(serialized.encode('utf-8')).hexdigest()

    def get(
        self,
        query: str,
        entities: Optional[List[str]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached KG query results"""
        if not self.enable_cache:
            return None

        key = self._compute_key(query, entities)

        if key not in self.cache:
            self.misses += 1
            return None

        entry = self.cache[key]
        current_time = time.time()

        if current_time - entry.timestamp > self.ttl_seconds:
            del self.cache[key]
            self.misses += 1
            return None

        self.cache.move_to_end(key)
        self.hits += 1

        logger.debug(f"KG cache HIT: query='{query[:40]}...', entities={entities}")
        return entry.value

    def put(
        self,
        query: str,
        results: List[Dict[str, Any]],
        entities: Optional[List[str]] = None
    ):
        """Store KG query results in cache"""
        if not self.enable_cache:
            return

        key = self._compute_key(query, entities)

        entry = CacheEntry(
            value=results,
            timestamp=time.time(),
            metadata={'entities': entities}
        )

        self.cache[key] = entry
        self.cache.move_to_end(key)

        while len(self.cache) > self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            self.evictions += 1

        logger.debug(f"KG cache PUT: query='{query[:40]}...', results={len(results)}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.hits + self.misses
        return {
            'enabled': self.enable_cache,
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': self.hits / total if total > 0 else 0.0,
            'evictions': self.evictions,
            'ttl_seconds': self.ttl_seconds
        }

    def clear(self):
        """Clear cache"""
        self.cache.clear()
        logger.info("KG cache cleared")


class EntityExtractionCache:
    """
    Cache for entity extraction results

    Caches LLM-based entity extraction to avoid redundant API calls
    for similar text patterns.
    """

    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: int = 1800,  # 30 minutes
        enable_cache: bool = True
    ):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.enable_cache = enable_cache

        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

        logger.info(
            f"EntityExtractionCache initialized: "
            f"max_size={max_size}, ttl={ttl_seconds}s, enabled={enable_cache}"
        )

    def _compute_key(self, text: str) -> str:
        """Compute cache key from text"""
        # Normalize text for better cache hits
        normalized = ' '.join(text.lower().split())
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()

    def get(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Get cached entity extraction result

        Returns dict with 'entities', 'actions', 'relations' if cached
        """
        if not self.enable_cache:
            return None

        key = self._compute_key(text)

        if key not in self.cache:
            self.misses += 1
            return None

        entry = self.cache[key]
        current_time = time.time()

        if current_time - entry.timestamp > self.ttl_seconds:
            del self.cache[key]
            self.misses += 1
            return None

        self.cache.move_to_end(key)
        self.hits += 1

        logger.debug(f"Entity cache HIT: text='{text[:40]}...'")
        return entry.value

    def put(self, text: str, extraction_result: Dict[str, Any]):
        """
        Store entity extraction result

        Args:
            text: The source text
            extraction_result: Dict with 'entities', 'actions', 'relations'
        """
        if not self.enable_cache:
            return

        key = self._compute_key(text)

        entry = CacheEntry(
            value=extraction_result,
            timestamp=time.time()
        )

        self.cache[key] = entry
        self.cache.move_to_end(key)

        while len(self.cache) > self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            self.evictions += 1

        entity_count = len(extraction_result.get('entities', []))
        logger.debug(f"Entity cache PUT: text='{text[:40]}...', entities={entity_count}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.hits + self.misses
        return {
            'enabled': self.enable_cache,
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': self.hits / total if total > 0 else 0.0,
            'evictions': self.evictions,
            'ttl_seconds': self.ttl_seconds
        }

    def clear(self):
        """Clear cache"""
        self.cache.clear()
        logger.info("Entity extraction cache cleared")


# Global cache instances (lazy initialization)
_llm_cache: Optional[LLMResponseCache] = None
_retrieval_cache: Optional[RetrievalCache] = None
_kg_cache: Optional[KGQueryCache] = None
_entity_cache: Optional[EntityExtractionCache] = None


def get_llm_cache() -> LLMResponseCache:
    """
    Get or create global LLM cache instance

    缓存配置从 SystemSettings 读取，支持通过环境变量控制：
    - ENABLE_LLM_CACHE=true/false - 开启/关闭缓存
    - LLM_CACHE_MAX_SIZE=1000 - 最大缓存条目数
    - LLM_CACHE_TTL_SECONDS=3600 - 缓存过期时间（秒）
    - LLM_CACHE_SIMILARITY_THRESHOLD=0.95 - 语义相似度阈值

    Example:
        # 关闭 LLM 缓存（用于 A/B 测试或故障排查）
        export ENABLE_LLM_CACHE=false

        # 缩短 TTL 到 10 分钟
        export LLM_CACHE_TTL_SECONDS=600
    """
    global _llm_cache

    if _llm_cache is None:
        from ..utils.config import get_settings
        settings = get_settings()

        _llm_cache = LLMResponseCache(
            max_size=settings.llm_cache_max_size,
            ttl_seconds=settings.llm_cache_ttl_seconds,
            similarity_threshold=settings.llm_cache_similarity_threshold,
            enable_cache=settings.enable_llm_cache
        )

    return _llm_cache


def get_retrieval_cache() -> RetrievalCache:
    """
    Get or create global retrieval cache instance

    缓存配置从 SystemSettings 读取，支持通过环境变量控制：
    - ENABLE_RETRIEVAL_CACHE=true/false - 开启/关闭缓存
    - RETRIEVAL_CACHE_MAX_SIZE=2000 - 最大缓存条目数
    - RETRIEVAL_CACHE_TTL_SECONDS=300 - 缓存过期时间（秒）

    Example:
        # 关闭检索缓存
        export ENABLE_RETRIEVAL_CACHE=false

        # 增加缓存容量到 5000
        export RETRIEVAL_CACHE_MAX_SIZE=5000
    """
    global _retrieval_cache

    if _retrieval_cache is None:
        from ..utils.config import get_settings
        settings = get_settings()

        _retrieval_cache = RetrievalCache(
            max_size=settings.retrieval_cache_max_size,
            ttl_seconds=settings.retrieval_cache_ttl_seconds,
            enable_cache=settings.enable_retrieval_cache
        )

    return _retrieval_cache


def reset_caches():
    """Reset all global cache instances"""
    global _llm_cache, _retrieval_cache

    if _llm_cache:
        _llm_cache.clear()
    if _retrieval_cache:
        _retrieval_cache.clear()

    logger.info("All caches reset")


def get_kg_cache() -> KGQueryCache:
    """Get or create global KG query cache instance"""
    global _kg_cache

    if _kg_cache is None:
        _kg_cache = KGQueryCache(
            max_size=500,
            ttl_seconds=600,  # 10 minutes
            enable_cache=True
        )

    return _kg_cache


def get_entity_cache() -> EntityExtractionCache:
    """Get or create global entity extraction cache instance"""
    global _entity_cache

    if _entity_cache is None:
        _entity_cache = EntityExtractionCache(
            max_size=1000,
            ttl_seconds=1800,  # 30 minutes
            enable_cache=True
        )

    return _entity_cache


def get_all_cache_stats() -> Dict[str, Any]:
    """Get statistics for all caches"""
    stats = {}

    if _llm_cache:
        stats['llm_cache'] = _llm_cache.get_stats()

    if _retrieval_cache:
        stats['retrieval_cache'] = _retrieval_cache.get_stats()

    if _kg_cache:
        stats['kg_cache'] = _kg_cache.get_stats()

    if _entity_cache:
        stats['entity_cache'] = _entity_cache.get_stats()

    return stats
