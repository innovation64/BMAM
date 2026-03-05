"""
简化的OpenAI客户端管理器
Simplified OpenAI Client Manager

替换原来复杂的连接池管理，使用最简单可靠的方案
"""

import os
import asyncio
from typing import Optional, List, Dict, Any
from openai import AsyncOpenAI
from ..utils.config import get_logger
from ..core.constants import DEFAULT_LLM_MODEL
from .circuit_breaker import get_circuit_breaker, CircuitBreakerError

logger = get_logger(__name__)

class SharedOpenAIClientManager:
    """简化的OpenAI客户端管理器"""
    
    _instance: Optional['SharedOpenAIClientManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._chat_client = None
            cls._instance._embedding_client = None
            cls._instance._lock = asyncio.Lock()
            cls._instance._request_semaphore = None
            cls._instance._semaphore_loop = None
        return cls._instance
    
    async def get_chat_client(self) -> AsyncOpenAI:
        """获取聊天客户端"""
        if self._chat_client is None:
            # 确保锁存在
            if self._lock is None:
                self._lock = asyncio.Lock()
            
            async with self._lock:
                if self._chat_client is None:
                    self._chat_client = AsyncOpenAI(
                        api_key=os.getenv("OPENAI_API_KEY"),
                        timeout=30.0,  # 统一超时30秒
                        max_retries=0  # 禁用SDK重试，由应用层统一处理
                    )
                    logger.info("创建简化聊天客户端")
        return self._chat_client
    
    async def get_embedding_client(self) -> AsyncOpenAI:
        """获取嵌入客户端"""
        if self._embedding_client is None:
            # 确保锁存在
            if self._lock is None:
                self._lock = asyncio.Lock()
            
            async with self._lock:
                if self._embedding_client is None:
                    self._embedding_client = AsyncOpenAI(
                        api_key=os.getenv("OPENAI_API_KEY"),
                        timeout=30.0,  # 统一超时30秒
                        max_retries=0  # 禁用SDK重试，由应用层统一处理
                    )
                    logger.info("创建简化嵌入客户端")
        return self._embedding_client
    
    def get_request_semaphore(self) -> asyncio.Semaphore:
        """获取请求信号量用于限流（跨调用共享同一个信号量）"""
        limit = int(os.getenv("OPENAI_MAX_CONCURRENCY", "4"))
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        needs_new = (
            self._request_semaphore is None or
            (loop is not None and self._semaphore_loop is not loop)
        )

        if needs_new:
            # 在新事件循环中重新创建信号量，避免跨循环复用导致的异常
            self._request_semaphore = asyncio.Semaphore(limit)
            self._semaphore_loop = loop

        return self._request_semaphore
    
    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        use_circuit_breaker: bool = True,
        **kwargs
    ):
        """
        Make a chat completion call, optionally through the circuit breaker.
        通过熔断器发起聊天补全调用（可选）。

        Args:
            messages: Chat messages list
            model: Model name (defaults to env OPENAI_MODEL or gpt-4o-mini)
            max_tokens: Max tokens for response
            temperature: Sampling temperature
            use_circuit_breaker: Whether to route through circuit breaker
            **kwargs: Additional arguments passed to the OpenAI API

        Returns:
            The OpenAI ChatCompletion response

        Raises:
            CircuitBreakerError: If circuit breaker is open
        """
        client = await self.get_chat_client()

        if model is None:
            model = os.getenv("OPENAI_MODEL", DEFAULT_LLM_MODEL)

        api_kwargs = {"model": model, "messages": messages, **kwargs}
        if max_tokens is not None:
            api_kwargs["max_tokens"] = max_tokens
        if temperature is not None:
            api_kwargs["temperature"] = temperature

        if use_circuit_breaker:
            breaker = get_circuit_breaker()
            return await breaker.call(
                client.chat.completions.create(**api_kwargs)
            )
        else:
            return await client.chat.completions.create(**api_kwargs)

    def get_stats(self) -> dict:
        """获取统计信息（含熔断器状态）"""
        breaker = get_circuit_breaker()
        return {
            "status": "simplified",
            "circuit_breaker": breaker.get_stats(),
        }
    
    def reset_clients(self):
        """重置客户端 - 修复跨事件循环复用问题"""
        logger.info("重置OpenAI客户端以修复事件循环问题")
        
        # 强制清空所有缓存的客户端实例
        self._chat_client = None
        self._embedding_client = None
        self._request_semaphore = None
        self._semaphore_loop = None
        
        # 重新创建异步锁（避免跨事件循环问题）
        try:
            self._lock = asyncio.Lock()
        except Exception as e:
            logger.warning(f"重置异步锁失败: {e}")
            # 如果当前没有运行的事件循环，稍后在get_client时创建
            self._lock = None
    
    def report_connection_error(self):
        """报告连接错误（保持接口兼容）"""
        logger.warning("连接错误报告（简化版本）")
    
    def report_connection_success(self):
        """报告连接成功（保持接口兼容）"""
        pass
    
    async def close(self):
        """关闭所有客户端连接"""
        if self._chat_client:
            await self._chat_client.close()
            self._chat_client = None
        if self._embedding_client:
            await self._embedding_client.close()
            self._embedding_client = None
        logger.info("简化客户端已关闭")

# 全局单例实例
shared_client_manager = SharedOpenAIClientManager()
