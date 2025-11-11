"""
Embedding Service Adapter
嵌入服务适配器

Adapts existing EmbeddingService to IEmbeddingService interface
将现有EmbeddingService适配到IEmbeddingService接口
"""

from typing import List
import numpy as np
import logging

from ..interfaces import IEmbeddingService

logger = logging.getLogger(__name__)


class EmbeddingServiceAdapter(IEmbeddingService):
    """
    Adapter for EmbeddingService to IEmbeddingService interface
    EmbeddingService到IEmbeddingService接口的适配器

    Bridges the legacy EmbeddingService with the new interface contract.
    桥接遗留的EmbeddingService与新接口契约。

    This adapter allows using the existing EmbeddingService implementation
    while conforming to the IEmbeddingService interface.

    Example:
        from src.memory.memory_system import EmbeddingService
        from src.core.adapters import EmbeddingServiceAdapter

        legacy_service = EmbeddingService()
        adapted_service = EmbeddingServiceAdapter(legacy_service)

        # Now works with IEmbeddingService interface
        embedding = await adapted_service.encode_text("Hello world")
        dimension = adapted_service.dimension
    """

    def __init__(self, legacy_service):
        """
        Initialize adapter with legacy embedding service

        Args:
            legacy_service: EmbeddingService instance
        """
        self._legacy = legacy_service
        logger.debug(f"EmbeddingServiceAdapter initialized with {type(legacy_service).__name__}")

    async def encode_text(self, text: str) -> np.ndarray:
        """
        Encode text to embedding vector

        Args:
            text: Input text

        Returns:
            Numpy array of embedding vector
        """
        try:
            # Legacy service may use different method names
            if hasattr(self._legacy, 'encode_text'):
                return await self._legacy.encode_text(text)
            elif hasattr(self._legacy, 'get_embedding'):
                result = await self._legacy.get_embedding(text)
                # Ensure it's a numpy array
                if isinstance(result, list):
                    return np.array(result)
                return result
            elif hasattr(self._legacy, 'embed'):
                result = await self._legacy.embed(text)
                if isinstance(result, list):
                    return np.array(result)
                return result
            else:
                # Try synchronous version
                if hasattr(self._legacy, 'encode'):
                    result = self._legacy.encode(text)
                    if isinstance(result, list):
                        return np.array(result)
                    return result
                else:
                    raise AttributeError(
                        f"Legacy service {type(self._legacy).__name__} has no compatible encode method"
                    )
        except Exception as e:
            logger.error(f"Error encoding text: {e}")
            raise

    async def encode_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Encode multiple texts in batch

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        try:
            # Check if legacy has batch encoding
            if hasattr(self._legacy, 'encode_batch') and callable(getattr(self._legacy, 'encode_batch', None)):
                results = await self._legacy.encode_batch(texts)
                # Ensure all are numpy arrays
                return [
                    np.array(r) if isinstance(r, list) else r
                    for r in results
                ]
            elif hasattr(self._legacy, 'get_embeddings') and callable(getattr(self._legacy, 'get_embeddings', None)):
                results = await self._legacy.get_embeddings(texts)
                return [
                    np.array(r) if isinstance(r, list) else r
                    for r in results
                ]
            else:
                # Fallback: encode one by one
                logger.debug("Using fallback sequential encoding for batch")
                results = []
                for text in texts:
                    embedding = await self.encode_text(text)
                    results.append(embedding)
                return results
        except Exception as e:
            logger.error(f"Error encoding batch: {e}")
            raise

    @property
    def dimension(self) -> int:
        """
        Embedding vector dimension

        Returns:
            Dimension of embedding vectors
        """
        try:
            # Try various attribute names
            if hasattr(self._legacy, 'dimension'):
                return self._legacy.dimension
            elif hasattr(self._legacy, 'embedding_dimension'):
                return self._legacy.embedding_dimension
            elif hasattr(self._legacy, 'dim'):
                return self._legacy.dim
            elif hasattr(self._legacy, 'embedding_dim'):
                return self._legacy.embedding_dim
            else:
                # Try to infer from a test encoding
                logger.warning("Could not find dimension attribute, inferring from test encoding")
                import asyncio
                try:
                    # Create event loop if needed
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    # Get dimension from test encoding
                    test_embedding = loop.run_until_complete(self.encode_text("test"))
                    return len(test_embedding)
                except Exception as e:
                    logger.error(f"Could not infer dimension: {e}")
                    # Default to common dimension
                    return 1536
        except Exception as e:
            logger.error(f"Error getting dimension: {e}")
            return 1536  # Default OpenAI dimension

    @property
    def legacy_service(self):
        """Access to underlying legacy service for advanced operations"""
        return self._legacy
