"""
Memory Retrieval Agent Package
记忆检索智能体包

这是一个基于策略模式的优雅记忆检索系统

使用示例:
    from src.agents.core.memory_retrieval import MemoryRetrievalAgent

    agent = MemoryRetrievalAgent(
        db_manager=db,
        embedding_service=embedder,
        vector_db=vector_db
    )

    result = await agent.retrieve(
        query="我昨天做了什么",
        strategy="semantic",
        k=10
    )
"""

from .memory_retrieval import MemoryRetrievalAgent
from .data_models import RetrievalRequest, RetrievalResult, CacheKey

__all__ = [
    'MemoryRetrievalAgent',
    'RetrievalRequest',
    'RetrievalResult',
    'CacheKey',
]
