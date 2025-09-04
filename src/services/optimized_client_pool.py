"""
优化的客户端池管理器 - 为每个Agent提供独立但高效的客户端
Optimized Client Pool Manager
"""

import os
import asyncio
import logging
from typing import Dict, Optional
from openai import AsyncOpenAI
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class OptimizedClientPool:
    """
    为每个Agent提供独立的客户端，但共享底层连接池
    解决并发冲突同时保持高性能
    """
    
    def __init__(self):
        self._clients: Dict[str, AsyncOpenAI] = {}
        self._lock = asyncio.Lock()
        self._shared_transport = None
        self._create_shared_transport()
    
    def _create_shared_transport(self):
        """创建共享的HTTP传输层"""
        # 创建一个高性能的共享传输层
        self._shared_transport = httpx.AsyncHTTPTransport(
            limits=httpx.Limits(
                max_keepalive_connections=30,  # 总连接池大小
                max_connections=100,           # 最大连接数
                keepalive_expiry=120           # 连接保持时间
            ),
            http2=True,  # 启用HTTP/2
            retries=2    # 自动重试
        )
        logger.info("创建共享传输层，支持高并发")
    
    async def get_agent_client(self, agent_id: str) -> AsyncOpenAI:
        """为特定Agent获取或创建客户端"""
        if agent_id not in self._clients:
            async with self._lock:
                if agent_id not in self._clients:  # 双重检查
                    # 每个Agent独立的客户端，但共享传输层
                    http_client = httpx.AsyncClient(
                        transport=self._shared_transport,
                        timeout=httpx.Timeout(60.0, connect=10.0),
                        follow_redirects=True
                    )
                    
                    self._clients[agent_id] = AsyncOpenAI(
                        api_key=os.getenv("OPENAI_API_KEY"),
                        timeout=60.0,
                        max_retries=2,
                        http_client=http_client
                    )
                    logger.info(f"为Agent {agent_id} 创建独立客户端（共享传输层）")
        
        return self._clients[agent_id]
    
    async def reset_agent_client(self, agent_id: str):
        """重置特定Agent的客户端"""
        async with self._lock:
            if agent_id in self._clients:
                try:
                    client = self._clients[agent_id]
                    if hasattr(client, 'http_client') and client.http_client:
                        await client.http_client.aclose()
                except Exception as e:
                    logger.error(f"关闭Agent {agent_id} 客户端失败: {e}")
                
                del self._clients[agent_id]
                logger.info(f"重置Agent {agent_id} 的客户端")
    
    async def close_all(self):
        """关闭所有客户端"""
        for agent_id in list(self._clients.keys()):
            await self.reset_agent_client(agent_id)
        
        if self._shared_transport:
            await self._shared_transport.aclose()
        
        logger.info("所有客户端已关闭")
    
    def get_stats(self) -> Dict:
        """获取连接池统计"""
        return {
            "active_agents": len(self._clients),
            "agents": list(self._clients.keys())
        }

# 全局实例
optimized_pool = OptimizedClientPool()