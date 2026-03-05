"""
Memory Interface - 内存系统接口
为核心智能体提供解耦的内存访问接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime


class MemorySystemInterface(ABC):
    """内存系统抽象接口"""
    
    @abstractmethod
    async def store_memory(self, content: str, memory_type: str = 'episodic',
                          importance: float = 0.5, emotion_tags: List[str] = None,
                          context_tags: List[str] = None, metadata: Dict = None) -> Optional[str]:
        """存储记忆"""
        pass
    
    @abstractmethod
    async def search_memories(self, query: str, search_type: str = 'semantic',
                             k: int = 10, threshold: float = 0.3, **filters) -> List[Dict[str, Any]]:
        """搜索记忆"""
        pass
    
    @abstractmethod
    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """获取特定记忆"""
        pass
    
    @abstractmethod
    async def get_text_embedding(self, text: str) -> Optional[List[float]]:
        """获取文本嵌入向量"""
        pass
    
    @abstractmethod
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计"""
        pass


class MockMemorySystem(MemorySystemInterface):
    """模拟内存系统 - 用于独立测试"""
    
    def __init__(self):
        self.memories = {}
        self.memory_counter = 0
    
    async def store_memory(self, content: str, memory_type: str = 'episodic',
                          importance: float = 0.5, emotion_tags: List[str] = None,
                          context_tags: List[str] = None, metadata: Dict = None) -> Optional[str]:
        """存储记忆到模拟系统"""
        self.memory_counter += 1
        memory_id = f"mock_mem_{self.memory_counter}"
        
        self.memories[memory_id] = {
            'id': memory_id,
            'content': content,
            'memory_type': memory_type,
            'importance': importance,
            'emotion_tags': emotion_tags or [],
            'context_tags': context_tags or [],
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat(),
            'embedding': [0.1] * 384  # 模拟嵌入向量
        }
        
        return memory_id
    
    async def search_memories(self, query: str, search_type: str = 'semantic',
                             k: int = 10, threshold: float = 0.3, **filters) -> List[Dict[str, Any]]:
        """简单的关键词匹配搜索"""
        results = []
        query_words = set(query.lower().split())
        
        for memory in self.memories.values():
            content_words = set(memory['content'].lower().split())
            overlap = len(query_words & content_words)
            
            if overlap > 0:
                memory_copy = memory.copy()
                memory_copy['score'] = overlap / len(query_words)
                results.append(memory_copy)
        
        # 按分数排序并限制数量
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:k]
    
    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """获取特定记忆"""
        return self.memories.get(memory_id)
    
    async def get_text_embedding(self, text: str) -> Optional[List[float]]:
        """返回模拟嵌入向量"""
        # 基于文本长度和哈希的简单模拟
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()
        
        # 转换为浮点向量
        embedding = []
        for i in range(0, min(len(hash_bytes), 16)):  # 16维向量
            embedding.append((hash_bytes[i] - 128) / 128.0)  # 归一化到 [-1, 1]
        
        # 填充到384维
        while len(embedding) < 384:
            embedding.append(0.0)
            
        return embedding[:384]
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计"""
        return {
            'database': {
                'total_memories': len(self.memories),
                'memory_types': {},
                'avg_importance': 0.5
            },
            'vector_db': {
                'total_vectors': len(self.memories),
                'dimensions': 384
            }
        }


class RealMemorySystemAdapter(MemorySystemInterface):
    """真实内存系统适配器"""
    
    def __init__(self, memory_system):
        self.memory_system = memory_system
    
    async def store_memory(self, content: str, memory_type: str = 'episodic',
                          importance: float = 0.5, emotion_tags: List[str] = None,
                          context_tags: List[str] = None, metadata: Dict = None) -> Optional[str]:
        """委托给真实内存系统"""
        return await self.memory_system.store_memory(
            content, memory_type, importance, emotion_tags, context_tags, metadata
        )
    
    async def search_memories(self, query: str, search_type: str = 'semantic',
                             k: int = 10, threshold: float = 0.3, **filters) -> List[Dict[str, Any]]:
        """委托给真实内存系统"""
        return await self.memory_system.search_memories(
            query, search_type, k, threshold, **filters
        )
    
    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """委托给真实内存系统"""
        return self.memory_system.get_memory(memory_id)
    
    async def get_text_embedding(self, text: str) -> Optional[List[float]]:
        """委托给真实内存系统"""
        return await self.memory_system.get_text_embedding(text)
    
    def get_system_stats(self) -> Dict[str, Any]:
        """委托给真实内存系统"""
        return self.memory_system.get_system_stats()


def create_memory_interface(memory_system=None) -> MemorySystemInterface:
    """工厂方法创建内存接口"""
    if memory_system is None:
        # 返回模拟系统，实现独立性
        return MockMemorySystem()
    else:
        # 返回真实系统适配器
        return RealMemorySystemAdapter(memory_system)