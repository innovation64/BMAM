"""
Embedding Service for Text Vectorization
文本向量化嵌入服务

Provides high-quality text embeddings using OpenAI's models with
intelligent caching for performance optimization.
"""

from typing import List
import logging

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Advanced Embedding Service with Caching
    带缓存的高级嵌入服务

    Generates vector embeddings for text using OpenAI's embedding models.
    Features intelligent caching to minimize API calls and costs.

    Attributes:
        service: Underlying OpenAI embedding service with cache
        dimension: Embedding vector dimension (1536 for OpenAI)
        model_name: Name of the embedding model being used

    Example:
        >>> service = EmbeddingService()
        >>> embedding = await service.encode_text("Hello world")
        >>> print(embedding.shape)  # (1536,)
    """

    def __init__(self) -> None:
        """Initialize embedding service with caching enabled."""
        from ...services.openai_embedding_service import OpenAIEmbeddingService

        self.service = OpenAIEmbeddingService(use_cache=True)
        self.dimension = self.service.dimension
        self.model_name = self.service.model

        logger.info(
            f"Initializing embedding service: {self.model_name} "
            f"(dimension: {self.dimension}) with caching enabled"
        )

    async def encode_text(self, text: str) -> np.ndarray:
        """
        Encode Single Text to Vector Embedding
        编码单个文本为向量嵌入

        Args:
            text: Input text to encode

        Returns:
            numpy array of shape (dimension,)

        Raises:
            Exception: If embedding generation fails
        """
        try:
            result = await self.service.encode_text(text)
            return np.array(result, dtype=np.float32)
        except Exception as e:
            logger.warning(f"Embedding service failed for text: {e}")
            raise

    async def encode_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Encode Multiple Texts in Batch with Caching
        批量编码多个文本（带缓存）

        Attempts batch encoding first, falls back to individual encoding
        for failed items to prevent corrupting the entire batch.

        Args:
            texts: List of input texts to encode

        Returns:
            List of numpy arrays, one per successfully encoded text

        Note:
            Failed encodings are skipped, not replaced with zeros
        """
        try:
            results = await self.service.encode_batch(texts)
            return [np.array(result, dtype=np.float32) for result in results]
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            return await self._encode_batch_fallback(texts)

    async def _encode_batch_fallback(self, texts: List[str]) -> List[np.ndarray]:
        """
        Fallback: Encode Texts Individually
        后备方案：逐个编码文本

        Processes texts one by one when batch encoding fails.
        Returns None for failed items to preserve alignment.

        Returns:
            List with same length as input, None for failed embeddings
        """
        results = []
        for i, text in enumerate(texts):
            try:
                embedding = await self.encode_text(text)
                results.append(embedding)
            except Exception as embed_error:
                logger.warning(
                    f"Failed to encode text at index {i}: {embed_error}"
                )
                # Return None to preserve alignment with input list
                results.append(None)
        return results
