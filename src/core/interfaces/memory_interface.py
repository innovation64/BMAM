"""
Memory System Interfaces
记忆系统接口

Defines contracts for memory operations
定义记忆操作的契约
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import numpy as np


@dataclass
class Memory:
    """
    Unified memory representation
    统一的记忆表示
    """
    memory_id: str
    content: str
    embedding: Optional[np.ndarray]
    metadata: Dict[str, Any]
    importance: float
    timestamp: str


class IEmbeddingService(ABC):
    """
    Embedding Service Interface
    嵌入服务接口

    Generates vector embeddings from text
    从文本生成向量嵌入
    """

    @abstractmethod
    async def encode_text(self, text: str) -> np.ndarray:
        """
        Encode text to embedding vector
        将文本编码为嵌入向量

        Args:
            text: Input text / 输入文本

        Returns:
            Numpy array of embedding vector / 嵌入向量的Numpy数组
        """
        pass

    @abstractmethod
    async def encode_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Encode multiple texts in batch
        批量编码多个文本

        Args:
            texts: List of input texts / 输入文本列表

        Returns:
            List of embedding vectors / 嵌入向量列表
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """
        Embedding vector dimension
        嵌入向量维度
        """
        pass


class IVectorDatabase(ABC):
    """
    Vector Database Interface
    向量数据库接口

    Stores and searches vector embeddings
    存储和搜索向量嵌入
    """

    @abstractmethod
    async def add_vectors(
        self,
        vectors: List[np.ndarray],
        metadata: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Add vectors to the database
        向数据库添加向量

        Args:
            vectors: List of embedding vectors / 嵌入向量列表
            metadata: List of metadata dicts / 元数据字典列表

        Returns:
            List of assigned IDs / 分配的ID列表
        """
        pass

    @abstractmethod
    async def search(
        self,
        query_vector: np.ndarray,
        k: int = 10,
        threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors
        搜索相似向量

        Args:
            query_vector: Query embedding / 查询嵌入
            k: Number of results / 结果数量
            threshold: Minimum similarity threshold / 最小相似度阈值

        Returns:
            List of search results with scores / 带分数的搜索结果列表
        """
        pass

    @abstractmethod
    async def delete_vectors(self, ids: List[str]) -> int:
        """
        Delete vectors by IDs
        通过ID删除向量

        Returns:
            Number of vectors deleted / 删除的向量数量
        """
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics
        获取数据库统计信息
        """
        pass


class IMemoryStorer(ABC):
    """
    Memory Storage Interface
    记忆存储接口

    Handles memory persistence
    处理记忆持久化
    """

    @abstractmethod
    async def store_memory(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5
    ) -> str:
        """
        Store a new memory
        存储新记忆

        Args:
            content: Memory content / 记忆内容
            metadata: Optional metadata / 可选元数据
            importance: Importance score (0-1) / 重要性分数 (0-1)

        Returns:
            Memory ID / 记忆ID
        """
        pass

    @abstractmethod
    async def store_batch(
        self,
        memories: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Store multiple memories in batch
        批量存储多个记忆

        Returns:
            List of memory IDs / 记忆ID列表
        """
        pass

    @abstractmethod
    async def update_memory(
        self,
        memory_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update existing memory
        更新现有记忆

        Returns:
            True if successful / 成功返回True
        """
        pass

    @abstractmethod
    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory
        删除记忆

        Returns:
            True if successful / 成功返回True
        """
        pass


class IMemoryRetriever(ABC):
    """
    Memory Retrieval Interface
    记忆检索接口

    Handles memory search and retrieval
    处理记忆搜索和检索
    """

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        k: int = 10,
        **filters
    ) -> List[Memory]:
        """
        Retrieve memories matching query
        检索匹配查询的记忆

        Args:
            query: Search query / 搜索查询
            k: Number of results / 结果数量
            **filters: Additional filters / 额外过滤器

        Returns:
            List of matching memories / 匹配的记忆列表
        """
        pass

    @abstractmethod
    async def retrieve_by_id(self, memory_id: str) -> Optional[Memory]:
        """
        Retrieve a specific memory by ID
        通过ID检索特定记忆
        """
        pass

    @abstractmethod
    async def retrieve_by_ids(self, memory_ids: List[str]) -> List[Memory]:
        """
        Retrieve multiple memories by IDs
        通过ID检索多个记忆
        """
        pass


class IMemorySystem(IMemoryStorer, IMemoryRetriever):
    """
    Unified Memory System Interface
    统一记忆系统接口

    Combines storage and retrieval operations
    结合存储和检索操作
    """

    @abstractmethod
    async def search_memories(
        self,
        query: str,
        search_type: str = "semantic",
        k: int = 10,
        threshold: float = 0.1,
        **filters
    ) -> List[Dict[str, Any]]:
        """
        Unified search interface supporting multiple strategies
        支持多种策略的统一搜索接口

        Args:
            query: Search query / 搜索查询
            search_type: "semantic", "hybrid", or "keyword" / 搜索类型
            k: Number of results / 结果数量
            threshold: Minimum similarity threshold / 最小相似度阈值
            **filters: Additional filters / 额外过滤器

        Returns:
            List of memory dictionaries / 记忆字典列表
        """
        pass

    @abstractmethod
    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get memory system statistics
        获取记忆系统统计信息
        """
        pass
