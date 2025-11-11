"""
Search Strategy Interfaces
搜索策略接口

Defines contracts for memory search strategies
定义记忆搜索策略的契约
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class ISearchStrategy(ABC):
    """
    Base Search Strategy Interface
    基础搜索策略接口

    All search strategies implement this
    所有搜索策略实现此接口
    """

    @abstractmethod
    async def search(
        self,
        query: str,
        k: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Execute search with this strategy
        使用此策略执行搜索

        Args:
            query: Search query / 搜索查询
            k: Number of results / 结果数量
            **kwargs: Strategy-specific parameters / 策略特定参数

        Returns:
            List of search results / 搜索结果列表
        """
        pass

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """
        Strategy identifier
        策略标识符
        """
        pass


class ISemanticSearch(ISearchStrategy):
    """
    Semantic (vector similarity) search
    语义（向量相似度）搜索
    """

    @abstractmethod
    async def semantic_search(
        self,
        query: str,
        k: int = 10,
        threshold: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Vector-based semantic search
        基于向量的语义搜索
        """
        pass


class IHybridSearch(ISearchStrategy):
    """
    Hybrid (semantic + metadata) search
    混合（语义 + 元数据）搜索
    """

    @abstractmethod
    async def hybrid_search(
        self,
        query: str,
        k: int = 10,
        threshold: float = 0.1,
        **filters
    ) -> List[Dict[str, Any]]:
        """
        Combined semantic and metadata filtering
        结合语义和元数据过滤
        """
        pass


class IKeywordSearch(ISearchStrategy):
    """
    Keyword-based text search
    基于关键词的文本搜索
    """

    @abstractmethod
    async def keyword_search(
        self,
        query: str,
        limit: int = 10,
        **filters
    ) -> List[Dict[str, Any]]:
        """
        Text-based keyword search
        基于文本的关键词搜索
        """
        pass
