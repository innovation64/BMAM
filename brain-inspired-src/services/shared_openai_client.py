"""
共享OpenAI客户端管理器
Shared OpenAI Client Manager

避免多个智能体创建重复的客户端连接
"""

import os
import time
from typing import Optional
from openai import AsyncOpenAI
import httpx
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class SharedOpenAIClientManager:
    """共享的OpenAI客户端管理器 - 定期刷新连接池"""
    
    _instance: Optional['SharedOpenAIClientManager'] = None
    _client: Optional[AsyncOpenAI] = None
    _embedding_client: Optional[AsyncOpenAI] = None
    _request_semaphore: Optional[asyncio.Semaphore] = None  # 限制并发请求
    _client_lock = asyncio.Lock()  # 客户端创建锁
    _last_refresh = 0  # 上次刷新时间
    _refresh_interval = 300  # 5分钟刷新一次
    _request_count = 0  # 请求计数
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_chat_client(self) -> AsyncOpenAI:
        """获取对话客户端 - 定期刷新连接池"""
        current_time = time.time()
        
        # 检查是否需要刷新连接池
        if (self._client is None or 
            current_time - self._last_refresh > self._refresh_interval or
            self._request_count > 100):  # 或者请求数过多
            
            if self._client is not None:
                logger.info(f"刷新连接池（{self._request_count}个请求后）")
                try:
                    # 关闭旧连接
                    if hasattr(self._client, 'http_client') and self._client.http_client:
                        # 不等待关闭，直接创建新的
                        pass
                except:
                    pass
            
            # 创建新的优化连接池
            http_client = httpx.AsyncClient(
                limits=httpx.Limits(
                    max_keepalive_connections=15,  # 适中的连接数
                    max_connections=30,            # 适中的最大连接数  
                    keepalive_expiry=120           # 2分钟连接保持
                ),
                timeout=httpx.Timeout(60.0, connect=10.0),
                http2=True,
                follow_redirects=True
            )
            
            self._client = AsyncOpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                timeout=60.0,
                max_retries=2,
                http_client=http_client
            )
            
            # 重置计数器
            self._last_refresh = current_time
            self._request_count = 0
            
            # 初始化请求信号量
            if self._request_semaphore is None:
                self._request_semaphore = asyncio.Semaphore(3)  # 降低并发数
            
            logger.info("创建/刷新优化的共享客户端")
        
        # 增加请求计数
        self._request_count += 1
        return self._client
    
    async def get_chat_client_safe(self) -> AsyncOpenAI:
        """线程安全地获取客户端"""
        async with self._client_lock:
            return self.get_chat_client()
    
    def get_request_semaphore(self) -> asyncio.Semaphore:
        """获取请求信号量用于限流"""
        if self._request_semaphore is None:
            self._request_semaphore = asyncio.Semaphore(3)  # 更低的并发限制
        return self._request_semaphore
    
    def get_stats(self) -> dict:
        """获取连接统计信息"""
        return {
            "request_count": self._request_count,
            "last_refresh": self._last_refresh,
            "time_since_refresh": time.time() - self._last_refresh,
            "next_refresh_in": self._refresh_interval - (time.time() - self._last_refresh)
        }
    
    def get_embedding_client(self) -> AsyncOpenAI:
        """获取embedding客户端"""
        if self._embedding_client is None:
            self._embedding_client = AsyncOpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                timeout=45.0,
                max_retries=2
            )
        return self._embedding_client
    
    async def close(self):
        """关闭所有客户端连接"""
        try:
            if self._client and self._client.http_client:
                await self._client.http_client.aclose()
        except Exception as e:
            print(f"关闭chat客户端时出错: {e}")
        
        try:
            if self._embedding_client and self._embedding_client.http_client:
                await self._embedding_client.http_client.aclose()
        except Exception as e:
            print(f"关闭embedding客户端时出错: {e}")
        
        self._client = None
        self._embedding_client = None
    
    async def reset_client_safe(self):
        """安全地重置客户端（异步版本）"""
        async with self._client_lock:
            if self._client and hasattr(self._client, 'http_client') and self._client.http_client:
                try:
                    await self._client.http_client.aclose()
                except Exception as e:
                    logger.error(f"关闭客户端失败: {e}")
            self._client = None
            logger.info("客户端已安全重置")
    
    def reset_clients(self):
        """重置客户端连接，强制创建新连接"""
        try:
            if self._client and self._client.http_client:
                # 同步关闭，避免异步问题
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 如果在事件循环中，创建任务
                        loop.create_task(self._client.http_client.aclose())
                    else:
                        # 如果不在事件循环中，同步运行
                        loop.run_until_complete(self._client.http_client.aclose())
                except:
                    pass
        except Exception:
            pass
            
        try:
            if self._embedding_client and self._embedding_client.http_client:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self._embedding_client.http_client.aclose())
                    else:
                        loop.run_until_complete(self._embedding_client.http_client.aclose())
                except:
                    pass
        except Exception:
            pass
        
        # 强制重置
        self._client = None
        self._embedding_client = None

# 全局单例实例
shared_client_manager = SharedOpenAIClientManager()