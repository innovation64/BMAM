"""
Services Module
服务模块

Provides various services for the brain-inspired memory system
为类脑记忆系统提供各种服务
"""

from .openai_embedding_service import (
    OpenAIEmbeddingService,
    get_embedding_service,
    encode_text_simple,
    compute_similarity_simple
)

__all__ = [
    'OpenAIEmbeddingService',
    'get_embedding_service', 
    'encode_text_simple',
    'compute_similarity_simple'
]