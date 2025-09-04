"""
基础适配器类
提供Agent接口适配的基础框架
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)


class AgentAdapter(ABC):
    """
    Agent适配器基类
    用于包装现有Agent，添加或修改功能而不影响原有接口
    """
    
    def __init__(self, agent, config: Optional[Dict] = None):
        """
        初始化适配器
        
        Args:
            agent: 被适配的原始Agent实例
            config: 适配器配置
        """
        self.agent = agent
        self.config = config or {}
        self._original_process = agent.process_message
        self._setup_adapter()
    
    def _setup_adapter(self):
        """设置适配器，子类可覆盖"""
        pass
    
    @abstractmethod
    def adapt_input(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        适配输入消息格式
        
        Args:
            message: 原始输入消息
            
        Returns:
            适配后的消息
        """
        pass
    
    @abstractmethod
    def adapt_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        适配输出结果格式
        
        Args:
            result: 原始输出结果
            
        Returns:
            适配后的结果
        """
        pass
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理消息的适配器方法
        
        Args:
            message: 输入消息
            
        Returns:
            处理结果
        """
        try:
            # 1. 适配输入
            adapted_input = self.adapt_input(message)
            
            # 2. 调用原始方法
            if asyncio.iscoroutinefunction(self._original_process):
                result = await self._original_process(adapted_input)
            else:
                result = self._original_process(adapted_input)
            
            # 3. 适配输出
            adapted_output = self.adapt_output(result)
            
            return adapted_output
            
        except Exception as e:
            logger.error(f"Adapter processing error: {e}")
            return self._handle_error(e, message)
    
    def _handle_error(self, error: Exception, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        错误处理
        
        Args:
            error: 异常
            message: 原始消息
            
        Returns:
            错误响应
        """
        return {
            'success': False,
            'error': str(error),
            'original_message': message
        }
    
    def __getattr__(self, name):
        """代理未定义的方法到原始agent"""
        return getattr(self.agent, name)


class MessageAdapter:
    """
    消息格式适配器
    用于在不同版本或格式的消息间转换
    """
    
    def __init__(self, source_version: str = "1.0", target_version: str = "1.0"):
        """
        初始化消息适配器
        
        Args:
            source_version: 源消息版本
            target_version: 目标消息版本
        """
        self.source_version = source_version
        self.target_version = target_version
        self._adapters = self._init_adapters()
    
    def _init_adapters(self) -> Dict[tuple, callable]:
        """初始化版本转换器"""
        return {
            ("1.0", "2.0"): self._adapt_v1_to_v2,
            ("2.0", "1.0"): self._adapt_v2_to_v1,
        }
    
    def adapt(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        适配消息格式
        
        Args:
            message: 输入消息
            
        Returns:
            适配后的消息
        """
        if self.source_version == self.target_version:
            return message
        
        adapter_key = (self.source_version, self.target_version)
        adapter = self._adapters.get(adapter_key)
        
        if not adapter:
            logger.warning(f"No adapter found for {adapter_key}, returning original message")
            return message
        
        return adapter(message)
    
    def _adapt_v1_to_v2(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """V1到V2的消息格式转换"""
        adapted = {
            'version': '2.0',
            'action': message.get('action'),
            'payload': message.get('content', {}),
            'metadata': {
                'source_version': '1.0',
                'timestamp': message.get('timestamp')
            }
        }
        return adapted
    
    def _adapt_v2_to_v1(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """V2到V1的消息格式转换"""
        adapted = {
            'action': message.get('action'),
            'content': message.get('payload', {}),
            'timestamp': message.get('metadata', {}).get('timestamp')
        }
        return adapted


class FeatureToggleAdapter(AgentAdapter):
    """
    功能开关适配器
    用于控制Agent的功能启用/禁用
    """
    
    def __init__(self, agent, features: Optional[Dict[str, bool]] = None):
        """
        初始化功能开关适配器
        
        Args:
            agent: 被适配的Agent
            features: 功能开关配置
        """
        self.features = features or {}
        super().__init__(agent)
    
    def adapt_input(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """根据功能开关调整输入"""
        # 添加功能标记
        message['enabled_features'] = self.features
        return message
    
    def adapt_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """根据功能开关过滤输出"""
        # 移除被禁用功能的输出
        filtered_result = result.copy()
        
        for feature, enabled in self.features.items():
            if not enabled and feature in filtered_result:
                del filtered_result[feature]
        
        return filtered_result


class LoggingAdapter(AgentAdapter):
    """
    日志记录适配器
    为Agent添加详细的日志记录
    """
    
    def adapt_input(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """记录输入"""
        logger.info(f"Agent {self.agent.agent_id} received: {message}")
        return message
    
    def adapt_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """记录输出"""
        logger.info(f"Agent {self.agent.agent_id} returned: {result}")
        return result


class CachingAdapter(AgentAdapter):
    """
    缓存适配器
    为Agent添加结果缓存功能
    """
    
    def __init__(self, agent, cache_size: int = 100):
        super().__init__(agent)
        self.cache = {}
        self.cache_size = cache_size
    
    def _get_cache_key(self, message: Dict[str, Any]) -> str:
        """生成缓存键"""
        import hashlib
        import json
        
        message_str = json.dumps(message, sort_keys=True)
        return hashlib.md5(message_str.encode()).hexdigest()
    
    def adapt_input(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """检查缓存"""
        cache_key = self._get_cache_key(message)
        
        if cache_key in self.cache:
            logger.info(f"Cache hit for agent {self.agent.agent_id}")
            message['_cached_result'] = self.cache[cache_key]
        
        message['_cache_key'] = cache_key
        return message
    
    def adapt_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """更新缓存"""
        if '_cache_key' in result:
            cache_key = result.pop('_cache_key')
            
            # 维护缓存大小
            if len(self.cache) >= self.cache_size:
                # 简单的FIFO策略
                self.cache.pop(next(iter(self.cache)))
            
            self.cache[cache_key] = result
        
        return result