"""
OpenAI Embedding Service with Built-in Cache
OpenAI嵌入服务（集成缓存功能）

Provides embedding functionality using OpenAI's text-embedding-3-small API
使用OpenAI的text-embedding-3-small API提供嵌入功能
"""

import os
import asyncio
import hashlib
import json
from typing import List, Dict, Any, Union, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import openai
from openai import AsyncOpenAI
import numpy as np
from ..utils.config import get_logger, get_env, get_absolute_path
from .shared_openai_client import shared_client_manager

logger = get_logger(__name__)

class EmbeddingFailureError(Exception):
    """嵌入向量计算失败异常"""
    pass

class EmbeddingCache:
    """嵌入向量缓存 - 内置实现"""
    
    def __init__(self, cache_dir: str = "data/embedding_cache", max_size: int = 10000, ttl_hours: int = 24):
        self.cache_dir = get_absolute_path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "embeddings.json"
        self.max_size = max_size
        self.ttl = timedelta(hours=ttl_hours)
        self._cache = {}
        self._load_cache()
    
    def _get_cache_key(self, text: str) -> str:
        """生成缓存键"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def _load_cache(self):
        """加载缓存"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self._cache = data.get('cache', {})
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
                self._cache = {}
    
    def _save_cache(self):
        """保存缓存"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump({'cache': self._cache}, f)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    def get(self, text: str) -> Optional[List[float]]:
        """获取缓存的嵌入"""
        key = self._get_cache_key(text)
        if key in self._cache:
            entry = self._cache[key]
            if datetime.fromisoformat(entry['timestamp']) + self.ttl > datetime.now():
                return entry['embedding']
        return None
    
    def put(self, text: str, embedding: List[float]):
        """存储嵌入到缓存"""
        key = self._get_cache_key(text)
        self._cache[key] = {
            'embedding': embedding,
            'timestamp': datetime.now().isoformat()
        }
        
        # 简单的LRU清理
        if len(self._cache) > self.max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]['timestamp'])
            del self._cache[oldest_key]
        
        self._save_cache()
    
    async def get_embedding(self, text: str, compute_func):
        """获取嵌入向量，使用缓存或计算新的"""
        # 先检查缓存
        cached = self.get(text)
        if cached is not None:
            return np.array(cached)
        
        # 缓存中没有，计算新的
        embedding = await compute_func(text)
        
        # 存储到缓存
        if isinstance(embedding, np.ndarray):
            self.put(text, embedding.tolist())
        else:
            self.put(text, embedding)
        
        return embedding
    
    async def get_batch_embeddings(self, texts: List[str], compute_func):
        """批量获取嵌入向量，使用缓存或计算新的"""
        results = []
        uncached_texts = []
        uncached_indices = []
        
        # 检查哪些文本已经缓存
        for i, text in enumerate(texts):
            cached = self.get(text)
            if cached is not None:
                results.append(np.array(cached))
            else:
                results.append(None)  # 占位符
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # 如果有未缓存的文本，批量计算
        if uncached_texts:
            new_embeddings = await compute_func(uncached_texts)
            
            # 存储到缓存并填充结果
            for j, idx in enumerate(uncached_indices):
                embedding = new_embeddings[j]
                if isinstance(embedding, np.ndarray):
                    self.put(texts[idx], embedding.tolist())
                else:
                    self.put(texts[idx], embedding)
                results[idx] = embedding
        
        return results


class OpenAIEmbeddingService:
    """OpenAI embedding service for text vectorization"""
    
    def __init__(self, use_cache: bool = True):
        # 使用共享客户端管理器，避免多个实例创建重复连接
        # 移除客户端缓存，每次调用时动态获取避免跨事件循环问题
        self.model = get_env("EMBEDDING_MODEL", "text-embedding-3-small")
        self.dimension = int(get_env("EMBEDDING_DIMENSION", "1536"))
        self.max_length = int(get_env("EMBEDDING_MAX_LENGTH", "8191"))
        
        # Initialize built-in cache
        self.use_cache = use_cache
        self.cache = EmbeddingCache() if use_cache else None
        
        logger.info(f"Initialized OpenAI embedding service with model: {self.model}")
        logger.info(f"Embedding dimension: {self.dimension}")
        logger.info(f"Cache enabled: {use_cache}")
    
    async def encode_text(self, text: str) -> np.ndarray:
        """
        Encode single text into embedding vector
        将单个文本编码为嵌入向量
        
        Args:
            text: Input text to encode
            
        Returns:
            numpy array of embedding vector
        
        Raises:
            EmbeddingFailureError: When API fails and fallback is disabled
        """
        
        if not text or not text.strip():
            # Return zero vector for empty text
            return np.zeros(self.dimension, dtype=np.float32)
        
        # Truncate text if too long
        if len(text) > self.max_length:
            text = text[:self.max_length]
            logger.warning(f"Text truncated to {self.max_length} characters")
        
        # Use cache if enabled
        if self.use_cache and self.cache:
            try:
                return await self.cache.get_embedding(text, self._compute_embedding)
            except EmbeddingFailureError:
                logger.warning(f"Embedding failed for text: '{text[:50]}...', skipping to prevent pollution")
                raise
        else:
            return await self._compute_embedding(text)
    
    async def _compute_embedding(self, text: str) -> np.ndarray:
        """
        Actually compute embedding from OpenAI API
        实际调用OpenAI API计算嵌入向量
        """
        try:
            # 每次都动态获取客户端，避免跨事件循环问题
            client = await shared_client_manager.get_embedding_client()
                
            # 让OpenAI客户端自己处理重试，我们不再手动重试
            response = await client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimension
            )
            
            embedding = response.data[0].embedding
            return np.array(embedding, dtype=np.float32)
            
        except Exception as e:
            # 准确记录异常类型和详细信息，避免misleading日志
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"Embedding API failed: {error_type}: {error_msg}")
            
            # 记录更多调试信息
            if hasattr(e, '__cause__'):
                logger.error(f"Caused by: {e.__cause__}")
            logger.error(f"Text length: {len(text)} chars")
            
            # 更精确的异常类型判断
            import openai
            if isinstance(e, (openai.APIConnectionError, ConnectionError)):
                logger.warning(f"网络连接异常，为文本 '{text[:30]}...' 抛出异常以避免污染向量库")
            elif isinstance(e, openai.RateLimitError) or "rate limit" in error_msg.lower():
                logger.warning("API调用频率限制，抛出异常以避免污染向量库")
            elif isinstance(e, openai.APITimeoutError):
                logger.warning("API调用超时，抛出异常以避免污染向量库")
            else:
                logger.warning(f"其他API错误 ({error_type})，抛出异常以避免污染向量库")
            
            # 不再返回fallback向量，而是抛出异常，防止污染FAISS
            raise EmbeddingFailureError(f"OpenAI embedding failed: {error_msg}") from e
    
    async def encode_batch(self, texts: List[str], batch_size: int = 100) -> List[np.ndarray]:
        """
        Encode multiple texts in batches with caching support
        批量编码多个文本，支持缓存
        
        Args:
            texts: List of texts to encode
            batch_size: Number of texts to process in each batch
            
        Returns:
            List of embedding vectors
            
        Raises:
            EmbeddingFailureError: When API fails and fallback is disabled
        """
        
        if not texts:
            return []
        
        # Use cache if enabled
        if self.use_cache and self.cache:
            try:
                return await self.cache.get_batch_embeddings(texts, 
                    lambda uncached_texts: self._compute_batch_embeddings(uncached_texts, batch_size))
            except EmbeddingFailureError:
                logger.warning("Batch embedding failed, skipping to prevent vector pollution")
                raise
        else:
            return await self._compute_batch_embeddings(texts, batch_size)
    
    async def _compute_batch_embeddings(self, texts: List[str], batch_size: int = 100) -> List[np.ndarray]:
        """
        Actually compute batch embeddings from OpenAI API
        实际调用OpenAI API批量计算嵌入向量
        """
        embeddings = []
        
        # Process in batches to avoid API limits
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            # Track empty inputs to preserve alignment with original order
            empties = [not text or not text.strip() for text in batch]
            valid_texts = [text for text, is_empty in zip(batch, empties) if not is_empty]

            try:
                batch_embeddings: List[np.ndarray] = []

                if valid_texts:
                    # 每次都动态获取客户端，避免跨事件循环问题
                    client = await shared_client_manager.get_embedding_client()

                    response = await client.embeddings.create(
                        model=self.model,
                        input=valid_texts,
                        dimensions=self.dimension
                    )

                    for data in response.data:
                        embedding = np.array(data.embedding, dtype=np.float32)
                        batch_embeddings.append(embedding)

                valid_iter = iter(batch_embeddings)
                for is_empty in empties:
                    if is_empty:
                        embeddings.append(np.zeros(self.dimension, dtype=np.float32))
                    else:
                        embeddings.append(next(valid_iter))

                # Add some delay between batches to respect rate limits
                if i + batch_size < len(texts):
                    await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error generating batch embeddings: {e}")
                # 不再添加fallback向量，而是抛出异常防止污染FAISS
                raise EmbeddingFailureError(f"Batch embedding failed: {e}") from e
        
        return embeddings
    
    async def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute cosine similarity between two texts
        计算两个文本之间的余弦相似度
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Cosine similarity score (0-1)
        """
        
        try:
            # Get embeddings for both texts
            emb1, emb2 = await asyncio.gather(
                self.encode_text(text1),
                self.encode_text(text2)
            )
            
            # Compute cosine similarity
            dot_product = np.dot(emb1, emb2)
            norm1 = np.linalg.norm(emb1)
            norm2 = np.linalg.norm(emb2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            
            # Ensure similarity is between 0 and 1
            similarity = max(0.0, min(1.0, (similarity + 1.0) / 2.0))
            
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error computing similarity: {e}")
            return 0.0
    
    async def find_similar_texts(self, query: str, texts: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find most similar texts to query
        查找与查询最相似的文本
        
        Args:
            query: Query text
            texts: List of texts to search
            top_k: Number of top similar texts to return
            
        Returns:
            List of dicts with 'text', 'similarity', and 'index' keys
        """
        
        if not texts or not query:
            return []
        
        try:
            # Get query embedding
            query_embedding = await self.encode_text(query)
            
            # Get embeddings for all texts
            text_embeddings = await self.encode_batch(texts)
            
            # Compute similarities
            similarities = []
            for i, text_emb in enumerate(text_embeddings):
                # Compute cosine similarity
                dot_product = np.dot(query_embedding, text_emb)
                norm1 = np.linalg.norm(query_embedding)
                norm2 = np.linalg.norm(text_emb)
                
                if norm1 == 0 or norm2 == 0:
                    similarity = 0.0
                else:
                    similarity = dot_product / (norm1 * norm2)
                    # Normalize to 0-1 range
                    similarity = max(0.0, min(1.0, (similarity + 1.0) / 2.0))
                
                similarities.append({
                    'text': texts[i],
                    'similarity': float(similarity),
                    'index': i
                })
            
            # Sort by similarity and return top k
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"Error finding similar texts: {e}")
            return []
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current embedding model"""
        
        info = {
            'model_name': self.model,
            'dimension': self.dimension,
            'max_length': self.max_length,
            'provider': 'OpenAI',
            'api_based': True,
            'cache_enabled': self.use_cache
        }
        
        # Add cache stats if enabled
        if self.use_cache and self.cache:
            info['cache_stats'] = self.cache.get_cache_stats()
        
        return info

# Global instance for easy import
embedding_service = None

def get_embedding_service() -> OpenAIEmbeddingService:
    """Get or create the global embedding service instance"""
    global embedding_service
    
    if embedding_service is None:
        embedding_service = OpenAIEmbeddingService()
    
    return embedding_service

async def encode_text_simple(text: str) -> np.ndarray:
    """Simple function to encode text using the global service"""
    service = get_embedding_service()
    return await service.encode_text(text)

async def compute_similarity_simple(text1: str, text2: str) -> float:
    """Simple function to compute similarity using the global service"""
    service = get_embedding_service()
    return await service.compute_similarity(text1, text2)
