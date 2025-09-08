"""
Embedding Cache Service
嵌入向量缓存服务

Provides caching for OpenAI embeddings to reduce API calls
提供OpenAI嵌入向量的缓存以减少API调用
"""

import hashlib
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import numpy as np
import asyncio
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class EmbeddingCache:
    """
    Cache for embeddings to avoid redundant API calls
    嵌入向量缓存，避免重复的API调用
    """
    
    def __init__(self, cache_dir: str = "data/embedding_cache", max_cache_size: int = 10000, ttl_hours: int = 24):
        """
        Initialize embedding cache
        
        Args:
            cache_dir: Directory to store cache files
            max_cache_size: Maximum number of cached embeddings
            ttl_hours: Time-to-live for cached items in hours
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_cache_size = max_cache_size
        self.ttl = timedelta(hours=ttl_hours)
        
        # In-memory cache for fast access
        self.memory_cache: Dict[str, Tuple[np.ndarray, datetime]] = {}
        
        # Cache metadata
        self.cache_metadata_file = self.cache_dir / "cache_metadata.json"
        self.cache_data_file = self.cache_dir / "cache_data.json"
        
        # Load existing cache
        self._load_cache()
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.api_calls_saved = 0
        
        logger.info(f"Initialized embedding cache with {len(self.memory_cache)} existing entries")
    
    def _get_text_hash(self, text: str) -> str:
        """Generate a unique hash for text"""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def _load_cache(self):
        """Load cache from disk"""
        try:
            if self.cache_data_file.exists() and self.cache_metadata_file.exists():
                # Load metadata
                with open(self.cache_metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                # Load embeddings
                with open(self.cache_data_file, 'r') as f:
                    cache_data = json.load(f)
                
                # Reconstruct memory cache with datetime objects
                current_time = datetime.now()
                for text_hash, entry in cache_data.items():
                    embedding = np.array(entry['embedding'])
                    timestamp = datetime.fromisoformat(entry['timestamp'])
                    
                    # Only load non-expired entries
                    if current_time - timestamp < self.ttl:
                        self.memory_cache[text_hash] = (embedding, timestamp)
                
                logger.info(f"Loaded {len(self.memory_cache)} valid cache entries from disk")
                
        except Exception as e:
            logger.warning(f"Could not load cache: {e}")
            self.memory_cache = {}
    
    def _save_cache(self):
        """Save cache to disk"""
        try:
            # Prepare data for serialization
            cache_data = {}
            for text_hash, (embedding, timestamp) in self.memory_cache.items():
                cache_data[text_hash] = {
                    'embedding': embedding.tolist(),
                    'timestamp': timestamp.isoformat()
                }
            
            # Save embeddings
            with open(self.cache_data_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            # Save metadata
            metadata = {
                'total_entries': len(self.memory_cache),
                'last_updated': datetime.now().isoformat(),
                'cache_hits': self.hits,
                'cache_misses': self.misses,
                'api_calls_saved': self.api_calls_saved
            }
            
            with open(self.cache_metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            logger.error(f"Could not save cache: {e}")
    
    def _cleanup_expired(self):
        """Remove expired entries from cache"""
        current_time = datetime.now()
        expired_keys = []
        
        for text_hash, (_, timestamp) in self.memory_cache.items():
            if current_time - timestamp > self.ttl:
                expired_keys.append(text_hash)
        
        for key in expired_keys:
            del self.memory_cache[key]
        
        if expired_keys:
            logger.info(f"Removed {len(expired_keys)} expired cache entries")
    
    def _enforce_size_limit(self):
        """Enforce maximum cache size by removing oldest entries"""
        if len(self.memory_cache) > self.max_cache_size:
            # Sort by timestamp and keep only the newest entries
            sorted_items = sorted(
                self.memory_cache.items(),
                key=lambda x: x[1][1],  # Sort by timestamp
                reverse=True  # Newest first
            )
            
            # Keep only max_cache_size items
            self.memory_cache = dict(sorted_items[:self.max_cache_size])
            logger.info(f"Cache size limited to {self.max_cache_size} entries")
    
    async def get_embedding(self, text: str, compute_fn) -> np.ndarray:
        """
        Get embedding from cache or compute if not cached
        
        Args:
            text: Text to get embedding for
            compute_fn: Async function to compute embedding if not cached
            
        Returns:
            Embedding vector
        """
        text_hash = self._get_text_hash(text)
        current_time = datetime.now()
        
        # Check if in cache and not expired
        if text_hash in self.memory_cache:
            embedding, timestamp = self.memory_cache[text_hash]
            
            if current_time - timestamp < self.ttl:
                self.hits += 1
                self.api_calls_saved += 1
                logger.debug(f"Cache hit for text hash {text_hash[:8]}...")
                return embedding
            else:
                # Expired, remove from cache
                del self.memory_cache[text_hash]
        
        # Not in cache or expired, compute new embedding
        self.misses += 1
        logger.debug(f"Cache miss for text hash {text_hash[:8]}..., computing embedding")
        
        try:
            embedding = await compute_fn(text)
            
            # Add to cache
            self.memory_cache[text_hash] = (embedding, current_time)
            
            # Cleanup and enforce limits periodically
            if len(self.memory_cache) % 100 == 0:
                self._cleanup_expired()
                self._enforce_size_limit()
                self._save_cache()
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error computing embedding: {e}")
            raise
    
    async def get_batch_embeddings(self, texts: List[str], compute_batch_fn) -> List[np.ndarray]:
        """
        Get embeddings for multiple texts, using cache where possible
        
        Args:
            texts: List of texts to get embeddings for
            compute_batch_fn: Async function to compute embeddings for uncached texts
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        uncached_texts = []
        uncached_indices = []
        current_time = datetime.now()
        
        # Check cache for each text
        for i, text in enumerate(texts):
            text_hash = self._get_text_hash(text)
            
            if text_hash in self.memory_cache:
                embedding, timestamp = self.memory_cache[text_hash]
                
                if current_time - timestamp < self.ttl:
                    self.hits += 1
                    self.api_calls_saved += 1
                    embeddings.append(embedding)
                else:
                    # Expired
                    del self.memory_cache[text_hash]
                    uncached_texts.append(text)
                    uncached_indices.append(i)
                    embeddings.append(None)  # Placeholder
            else:
                self.misses += 1
                uncached_texts.append(text)
                uncached_indices.append(i)
                embeddings.append(None)  # Placeholder
        
        # Compute embeddings for uncached texts
        if uncached_texts:
            logger.info(f"Computing {len(uncached_texts)} embeddings (cached: {len(texts) - len(uncached_texts)})")
            
            try:
                new_embeddings = await compute_batch_fn(uncached_texts)
                
                # Update cache and results
                for text, embedding, index in zip(uncached_texts, new_embeddings, uncached_indices):
                    text_hash = self._get_text_hash(text)
                    self.memory_cache[text_hash] = (embedding, current_time)
                    embeddings[index] = embedding
                
                # Save cache periodically
                if len(uncached_texts) > 10:
                    self._cleanup_expired()
                    self._enforce_size_limit()
                    self._save_cache()
                    
            except Exception as e:
                logger.error(f"Error computing batch embeddings: {e}")
                raise
        
        return embeddings
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / max(1, total_requests)
        
        return {
            'total_cached': len(self.memory_cache),
            'cache_hits': self.hits,
            'cache_misses': self.misses,
            'hit_rate': f"{hit_rate:.1%}",
            'api_calls_saved': self.api_calls_saved,
            'estimated_cost_saved': f"${self.api_calls_saved * 0.00002:.4f}",  # Embedding API cost
            'cache_size_mb': sum(em.nbytes for em, _ in self.memory_cache.values()) / (1024 * 1024)
        }
    
    def clear_cache(self):
        """Clear all cached embeddings"""
        self.memory_cache.clear()
        self.hits = 0
        self.misses = 0
        self.api_calls_saved = 0
        
        # Remove cache files
        try:
            if self.cache_data_file.exists():
                self.cache_data_file.unlink()
            if self.cache_metadata_file.exists():
                self.cache_metadata_file.unlink()
        except Exception as e:
            logger.error(f"Error clearing cache files: {e}")
        
        logger.info("Cache cleared")

# Global cache instance
_embedding_cache: Optional[EmbeddingCache] = None

def get_embedding_cache() -> EmbeddingCache:
    """Get or create global embedding cache instance"""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache()
    return _embedding_cache