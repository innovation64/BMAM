"""
OpenAI Embedding Service
OpenAI嵌入服务

Provides embedding functionality using OpenAI's text-embedding-3-small API
使用OpenAI的text-embedding-3-small API提供嵌入功能
"""

import os
import asyncio
from typing import List, Dict, Any, Union
import openai
from openai import AsyncOpenAI
import numpy as np
from ..utils.config import get_logger, get_env
from .embedding_cache import get_embedding_cache
from .shared_openai_client import shared_client_manager

logger = get_logger(__name__)

class OpenAIEmbeddingService:
    """OpenAI embedding service for text vectorization"""
    
    def __init__(self, use_cache: bool = True):
        # 使用共享客户端管理器，避免多个实例创建重复连接
        self.client = shared_client_manager.get_embedding_client()
        self.model = get_env("EMBEDDING_MODEL", "text-embedding-3-small")
        self.dimension = int(get_env("EMBEDDING_DIMENSION", "1536"))
        self.max_length = int(get_env("EMBEDDING_MAX_LENGTH", "8191"))
        
        # Initialize cache
        self.use_cache = use_cache
        self.cache = get_embedding_cache() if use_cache else None
        
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
            return await self.cache.get_embedding(text, self._compute_embedding)
        else:
            return await self._compute_embedding(text)
    
    async def _compute_embedding(self, text: str) -> np.ndarray:
        """
        Actually compute embedding from OpenAI API
        实际调用OpenAI API计算嵌入向量
        """
        try:
            # 让OpenAI客户端自己处理重试，我们不再手动重试
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimension
            )
            
            embedding = response.data[0].embedding
            return np.array(embedding, dtype=np.float32)
            
        except Exception as e:
            logger.warning(f"Embedding API failed: {e}")
            
            # 根据错误类型提供更好的备用方案
            if "Connection error" in str(e):
                logger.warning(f"网络连接问题，为文本 '{text[:30]}...' 使用备用向量")
                # 使用基于文本内容的伪随机向量，保证相同文本产生相同向量
                import hashlib
                text_hash = hashlib.md5(text.encode()).hexdigest()
                np.random.seed(int(text_hash[:8], 16))
                fallback_vector = np.random.normal(0, 0.1, self.dimension).astype(np.float32)
                np.random.seed()  # 重置随机种子
                return fallback_vector
            elif "rate limit" in str(e).lower():
                logger.warning("API调用频率限制，使用零向量备用方案")
                return np.zeros(self.dimension, dtype=np.float32)
            else:
                # 其他错误，使用基于内容的确定性向量
                logger.warning(f"API调用失败: {e}")
                import hashlib
                text_hash = hashlib.md5(text.encode()).hexdigest()
                np.random.seed(int(text_hash[:8], 16))
                fallback_vector = np.random.normal(0, 0.1, self.dimension).astype(np.float32)
                np.random.seed()
                return fallback_vector
    
    async def encode_batch(self, texts: List[str], batch_size: int = 100) -> List[np.ndarray]:
        """
        Encode multiple texts in batches with caching support
        批量编码多个文本，支持缓存
        
        Args:
            texts: List of texts to encode
            batch_size: Number of texts to process in each batch
            
        Returns:
            List of embedding vectors
        """
        
        if not texts:
            return []
        
        # Use cache if enabled
        if self.use_cache and self.cache:
            return await self.cache.get_batch_embeddings(texts, 
                lambda uncached_texts: self._compute_batch_embeddings(uncached_texts, batch_size))
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
            
            # Filter out empty texts
            valid_texts = [text for text in batch if text and text.strip()]
            
            if not valid_texts:
                # Add zero vectors for empty batch
                embeddings.extend([np.zeros(self.dimension, dtype=np.float32)] * len(batch))
                continue
            
            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=valid_texts,
                    dimensions=self.dimension
                )
                
                batch_embeddings = []
                for data in response.data:
                    embedding = np.array(data.embedding, dtype=np.float32)
                    batch_embeddings.append(embedding)
                
                embeddings.extend(batch_embeddings)
                
                # Add some delay between batches to respect rate limits
                if i + batch_size < len(texts):
                    await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error generating batch embeddings: {e}")
                # Add random vectors as fallback
                fallback_embeddings = [
                    np.random.rand(self.dimension).astype(np.float32) 
                    for _ in range(len(batch))
                ]
                embeddings.extend(fallback_embeddings)
        
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