"""
FAISS Vector Database for Semantic Memory Retrieval
基于FAISS的语义记忆检索向量数据库

Provides high-performance vector similarity search using Facebook's FAISS
library with persistent storage and thread-safe operations.
"""

import os
import json
import threading
from typing import Dict, List, Tuple
from pathlib import Path
import logging

import numpy as np
import faiss

from ...utils.config import get_absolute_path

logger = logging.getLogger(__name__)


class FAISSVectorDatabase:
    """
    FAISS-based Vector Database for Semantic Search
    基于FAISS的语义搜索向量数据库

    Manages vector embeddings using FAISS (Facebook AI Similarity Search)
    with persistent storage and memory ID mapping.

    Attributes:
        dimension: Vector embedding dimension
        index_path: Path to persistent index file
        index: FAISS index for similarity search
        id_mapping: Maps FAISS index -> memory ID
        reverse_mapping: Maps memory ID -> FAISS index
        lock: Thread lock for concurrent access safety

    Example:
        >>> db = FAISSVectorDatabase(dimension=1536)
        >>> faiss_id = db.add_vector("mem_001", embedding)
        >>> results = db.search(query_vector, k=10, threshold=0.3)
    """

    def __init__(
        self,
        dimension: int = None,
        index_path: str = None
    ) -> None:
        """
        Initialize FAISS Vector Database
        初始化FAISS向量数据库

        Args:
            dimension: Vector dimension (default: 1536 for OpenAI)
            index_path: Path to index file (default: from env/config)
        """
        self.dimension = dimension or 1536
        # 使用 BMAMPaths 支持并行测试
        from src.utils.paths import BMAMPaths
        default_index_path = str(BMAMPaths.MEMORY_VECTORS_INDEX)
        self.index_path = str(get_absolute_path(
            index_path or os.getenv(
                "VECTOR_INDEX_PATH",
                default_index_path
            )
        ))

        # Ensure data directory exists
        Path(self.index_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize FAISS index (Inner Product for cosine similarity)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.id_mapping: Dict[int, str] = {}
        self.reverse_mapping: Dict[str, int] = {}
        self.user_id_mapping: Dict[str, str] = {}  # memory_id -> user_id
        self.lock = threading.Lock()

        logger.info(
            f"Initializing FAISS vector database "
            f"(dimension: {self.dimension})"
        )
        self.load_index()

    def add_vector(
        self, memory_id: str, vector: np.ndarray, user_id: str = 'default'
    ) -> int:
        """
        Add Vector to FAISS Index with Memory ID Mapping
        添加向量到FAISS索引（带记忆ID映射）

        Args:
            memory_id: Unique memory identifier
            vector: Embedding vector (will be normalized)
            user_id: Owner user ID for isolation filtering

        Returns:
            FAISS index ID for the added vector
        """
        with self.lock:
            if memory_id in self.reverse_mapping:
                # Update user_id even for existing vectors
                self.user_id_mapping[memory_id] = user_id
                return self.reverse_mapping[memory_id]

            # Normalize vector for cosine similarity
            vector = vector / np.linalg.norm(vector)
            vector = vector.reshape(1, -1).astype(np.float32)

            # Add to FAISS index
            faiss_id = self.index.ntotal
            self.index.add(vector)

            # Update mappings
            self.id_mapping[faiss_id] = memory_id
            self.reverse_mapping[memory_id] = faiss_id
            self.user_id_mapping[memory_id] = user_id

            logger.debug(
                f"Added vector for memory {memory_id} "
                f"at FAISS index {faiss_id}"
            )
            return faiss_id

    def search(
        self,
        query_vector: np.ndarray,
        k: int = 10,
        threshold: float = 0.3,
        user_id: str = None
    ) -> List[Tuple[str, float]]:
        """
        Search for Similar Vectors using FAISS
        使用FAISS搜索相似向量

        Args:
            query_vector: Query embedding vector
            k: Number of results to return
            threshold: Minimum similarity threshold
            user_id: Filter results to this user (and 'default')

        Returns:
            List of (memory_id, similarity_score) tuples
        """
        with self.lock:
            if self.index.ntotal == 0:
                return []

            # Normalize query vector
            query_vector = query_vector / np.linalg.norm(query_vector)
            query_vector = query_vector.reshape(1, -1).astype(np.float32)

            # Over-fetch when filtering by user_id to compensate for filtering
            fetch_k = min(k * 3, self.index.ntotal) if user_id else min(k, self.index.ntotal)

            # Search with FAISS
            similarities, indices = self.index.search(
                query_vector,
                fetch_k
            )

            results = []
            for sim, idx in zip(similarities[0], indices[0]):
                if sim >= threshold and idx in self.id_mapping:
                    memory_id = self.id_mapping[idx]
                    # Filter by user_id if specified
                    if user_id:
                        mem_uid = self.user_id_mapping.get(memory_id, 'default')
                        if mem_uid != user_id and mem_uid != 'default':
                            continue
                    results.append((memory_id, float(sim)))
                    if len(results) >= k:
                        break

            logger.debug(
                f"Vector search found {len(results)} results "
                f"above threshold {threshold}"
            )
            return results

    def remove_vector(self, memory_id: str) -> None:
        """
        Remove Vector from Index (Logical Deletion)
        从索引中删除向量（逻辑删除）

        Args:
            memory_id: Memory ID to remove
        """
        with self.lock:
            if memory_id in self.reverse_mapping:
                faiss_id = self.reverse_mapping[memory_id]
                del self.id_mapping[faiss_id]
                del self.reverse_mapping[memory_id]
                logger.debug(f"Removed vector for memory {memory_id}")

    def reset(self) -> None:
        """
        Rebuild FAISS Structures from Scratch
        从头重建FAISS结构
        """
        with self.lock:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.id_mapping.clear()
            self.reverse_mapping.clear()
            self.user_id_mapping.clear()
            logger.info("FAISS index reset; mappings cleared")

    def save_index(self) -> None:
        """
        Persist FAISS Index and Mappings to Disk
        将FAISS索引和映射持久化到磁盘
        """
        with self.lock:
            try:
                faiss.write_index(self.index, self.index_path)

                # Save mappings separately
                mapping_path = self.index_path.replace('.index', '_mappings.json')
                with open(mapping_path, 'w') as f:
                    json.dump({
                        'id_mapping': self.id_mapping,
                        'reverse_mapping': self.reverse_mapping,
                        'user_id_mapping': self.user_id_mapping
                    }, f, indent=2)

                logger.info(
                    f"Saved FAISS index with {self.index.ntotal} vectors "
                    f"to {self.index_path}"
                )
            except Exception as e:
                logger.error(f"Failed to save FAISS index: {e}")

    def load_index(self) -> None:
        """Load FAISS Index and Mappings from Disk 从磁盘加载FAISS索引和映射"""
        try:
            if not os.path.exists(self.index_path):
                logger.debug("No existing FAISS index found, starting empty")
                return

            loaded_index = faiss.read_index(self.index_path)

            # Validate dimension compatibility
            if loaded_index.d != self.dimension:
                logger.warning(
                    f"FAISS dimension mismatch: expected {self.dimension}, "
                    f"got {loaded_index.d}. Rebuilding with correct dimension."
                )
                self.index = faiss.IndexFlatIP(self.dimension)
                return

            self.index = loaded_index

            # Load mappings
            mapping_path = self.index_path.replace('.index', '_mappings.json')
            if os.path.exists(mapping_path):
                with open(mapping_path, 'r') as f:
                    mappings = json.load(f)
                    # Convert string keys back to integers
                    self.id_mapping = {
                        int(k): v for k, v in mappings['id_mapping'].items()
                    }
                    self.reverse_mapping = mappings['reverse_mapping']
                    self.user_id_mapping = mappings.get('user_id_mapping', {})

            logger.info(
                f"Loaded FAISS index with {self.index.ntotal} vectors "
                f"from {self.index_path}"
            )
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}")
            logger.info("Starting with empty FAISS index")
            self.index = faiss.IndexFlatIP(self.dimension)
