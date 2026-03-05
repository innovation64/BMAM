"""
LLM Service Interface
LLM服务接口 - 解耦核心逻辑与LLM调用
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from ..agents.base import BrainAgent


class LLMServiceInterface(ABC):
    """LLM服务接口 - 抽象层"""
    
    @abstractmethod
    async def call_llm(self, prompt: str, context: Dict[str, Any] = None, 
                      max_tokens: int = None, temperature: float = None) -> str:
        """调用LLM服务"""
        pass


class BrainAgentLLMService(LLMServiceInterface):
    """基于BrainAgent的LLM服务实现"""
    
    def __init__(self, agent: BrainAgent):
        self.agent = agent
    
    async def call_llm(self, prompt: str, context: Dict[str, Any] = None,
                      max_tokens: int = None, temperature: float = None) -> str:
        """委托给BrainAgent的统一LLM调用"""
        return await self.agent.call_llm(prompt, context, max_tokens, temperature)


class MockLLMService(LLMServiceInterface):
    """模拟LLM服务 - 用于测试或降级"""
    
    def __init__(self, default_response: str = "模拟LLM响应"):
        self.default_response = default_response
        self.call_count = 0
    
    async def call_llm(self, prompt: str, context: Dict[str, Any] = None,
                      max_tokens: int = None, temperature: float = None) -> str:
        """返回模拟响应"""
        self.call_count += 1
        return f"{self.default_response} (调用次数: {self.call_count})"


class CachingLLMService(LLMServiceInterface):
    """带缓存的LLM服务装饰器"""
    
    def __init__(self, inner_service: LLMServiceInterface, cache_size: int = 100):
        self.inner_service = inner_service
        self.cache = {}
        self.cache_size = cache_size
        
    def _get_cache_key(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """生成缓存键"""
        import hashlib
        content = f"{prompt}_{str(context or {})}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def call_llm(self, prompt: str, context: Dict[str, Any] = None,
                      max_tokens: int = None, temperature: float = None) -> str:
        """带缓存的LLM调用"""
        cache_key = self._get_cache_key(prompt, context)
        
        # 检查缓存
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # 调用内部服务
        result = await self.inner_service.call_llm(prompt, context, max_tokens, temperature)
        
        # 更新缓存
        if len(self.cache) >= self.cache_size:
            # 简单LRU - 移除第一个条目
            first_key = next(iter(self.cache))
            del self.cache[first_key]
            
        self.cache[cache_key] = result
        return result


def create_llm_service(agent: BrainAgent, enable_cache: bool = True) -> LLMServiceInterface:
    """工厂方法创建LLM服务"""
    base_service = BrainAgentLLMService(agent)
    
    if enable_cache:
        return CachingLLMService(base_service)
    else:
        return base_service