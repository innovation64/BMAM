"""
Vector Database Adapter
向量数据库适配器

Adapts FAISSVectorDatabase to IVectorDatabase interface
将FAISSVectorDatabase适配到IVectorDatabase接口
"""

from typing import List, Dict, Any
import numpy as np
import logging

from ..interfaces import IVectorDatabase

logger = logging.getLogger(__name__)


class VectorDatabaseAdapter(IVectorDatabase):
    """
    Adapter for FAISSVectorDatabase to IVectorDatabase interface
    FAISSVectorDatabase到IVectorDatabase接口的适配器

    Bridges the legacy FAISSVectorDatabase with the new interface contract.
    桥接遗留的FAISSVectorDatabase与新接口契约。

    This adapter allows using the existing FAISS implementation
    while conforming to the IVectorDatabase interface.

    Example:
        from src.memory.memory_system import FAISSVectorDatabase
        from src.core.adapters import VectorDatabaseAdapter

        legacy_db = FAISSVectorDatabase(dimension=1536)
        adapted_db = VectorDatabaseAdapter(legacy_db)

        # Now works with IVectorDatabase interface
        ids = await adapted_db.add_vectors(vectors, metadata)
        results = await adapted_db.search(query_vector, k=10)
    """

    def __init__(self, legacy_database):
        """
        Initialize adapter with legacy vector database

        Args:
            legacy_database: FAISSVectorDatabase instance
        """
        self._legacy = legacy_database
        logger.debug(f"VectorDatabaseAdapter initialized with {type(legacy_database).__name__}")

    async def add_vectors(
        self,
        vectors: List[np.ndarray],
        metadata: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Add vectors to the database

        Args:
            vectors: List of embedding vectors
            metadata: List of metadata dicts

        Returns:
            List of assigned IDs
        """
        try:
            # Legacy FAISS may use different method names
            if hasattr(self._legacy, 'add_vectors'):
                return await self._legacy.add_vectors(vectors, metadata)
            elif hasattr(self._legacy, 'add'):
                return await self._legacy.add(vectors, metadata)
            elif hasattr(self._legacy, 'add_items'):
                return await self._legacy.add_items(vectors, metadata)
            else:
                # Try synchronous version
                if hasattr(self._legacy, 'add_vectors_sync'):
                    return self._legacy.add_vectors_sync(vectors, metadata)
                else:
                    raise AttributeError(
                        f"Legacy database {type(self._legacy).__name__} has no compatible add method"
                    )
        except Exception as e:
            logger.error(f"Error adding vectors: {e}")
            raise

    async def search(
        self,
        query_vector: np.ndarray,
        k: int = 10,
        threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors

        Args:
            query_vector: Query embedding
            k: Number of results
            threshold: Minimum similarity threshold

        Returns:
            List of search results with scores
        """
        try:
            # Legacy FAISS may use different method names
            if hasattr(self._legacy, 'search'):
                results = await self._legacy.search(query_vector, k=k, threshold=threshold)
            elif hasattr(self._legacy, 'query'):
                results = await self._legacy.query(query_vector, k=k, threshold=threshold)
            elif hasattr(self._legacy, 'search_similar'):
                results = await self._legacy.search_similar(query_vector, k=k, threshold=threshold)
            else:
                # Try synchronous version
                if hasattr(self._legacy, 'search_sync'):
                    results = self._legacy.search_sync(query_vector, k=k)
                else:
                    raise AttributeError(
                        f"Legacy database {type(self._legacy).__name__} has no compatible search method"
                    )

            # Ensure results are in the correct format
            if isinstance(results, list):
                formatted_results = []
                for result in results:
                    if isinstance(result, dict):
                        formatted_results.append(result)
                    else:
                        # Handle tuple format (id, score, metadata)
                        formatted_results.append({
                            'id': result[0] if len(result) > 0 else '',
                            'similarity': result[1] if len(result) > 1 else 0.0,
                            'metadata': result[2] if len(result) > 2 else {}
                        })
                return formatted_results
            return results

        except Exception as e:
            logger.error(f"Error searching vectors: {e}")
            raise

    async def delete_vectors(self, ids: List[str]) -> int:
        """
        Delete vectors by IDs

        Args:
            ids: List of vector IDs to delete

        Returns:
            Number of vectors deleted
        """
        try:
            if hasattr(self._legacy, 'delete_vectors'):
                return await self._legacy.delete_vectors(ids)
            elif hasattr(self._legacy, 'delete'):
                return await self._legacy.delete(ids)
            elif hasattr(self._legacy, 'remove'):
                return await self._legacy.remove(ids)
            else:
                # FAISS may not support deletion
                logger.warning("Legacy database does not support vector deletion")
                return 0
        except Exception as e:
            logger.error(f"Error deleting vectors: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics

        Returns:
            Statistics dictionary
        """
        try:
            if hasattr(self._legacy, 'get_stats'):
                return self._legacy.get_stats()
            elif hasattr(self._legacy, 'stats'):
                return self._legacy.stats
            elif hasattr(self._legacy, 'get_statistics'):
                return self._legacy.get_statistics()
            else:
                # Return basic stats
                stats = {
                    'adapter': 'VectorDatabaseAdapter',
                    'legacy_type': type(self._legacy).__name__
                }

                # Try to get common attributes
                if hasattr(self._legacy, 'ntotal'):
                    stats['total_vectors'] = self._legacy.ntotal
                elif hasattr(self._legacy, 'size'):
                    stats['total_vectors'] = self._legacy.size
                elif hasattr(self._legacy, '__len__'):
                    stats['total_vectors'] = len(self._legacy)

                if hasattr(self._legacy, 'd'):
                    stats['dimension'] = self._legacy.d
                elif hasattr(self._legacy, 'dimension'):
                    stats['dimension'] = self._legacy.dimension

                return stats
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'error': str(e)}

    @property
    def legacy_database(self):
        """Access to underlying legacy database for advanced operations"""
        return self._legacy
