"""
Base Agent Class for Brain-Inspired Memory System
基础智能体类 - 所有智能体的父类
"""

import asyncio
import json
import uuid
import hashlib
from collections import OrderedDict
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod
import openai
from ..utils.config import get_logger, get_env, get_settings
from ..services.shared_openai_client import shared_client_manager
# 移除了shared_client_manager依赖，直接使用openai.AsyncOpenAI

# Configure logging
logger = get_logger(__name__)


@dataclass
class AgentMessage:
    """Inter-agent communication message"""
    sender: str
    receiver: str
    message_type: str  # request, response, notification
    content: Dict[str, Any]
    priority: str = "medium"  # high, medium, low
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class BrainRegion:
    """Brain region constants and functions"""
    HIPPOCAMPUS = "hippocampus"  # Memory formation and retrieval
    NEOCORTEX = "neocortex"     # Long-term storage and semantic memory
    PREFRONTAL = "prefrontal"    # Working memory and executive control
    AMYGDALA = "amygdala"       # Emotional memory processing
    THALAMUS = "thalamus"       # Sensory relay and encoding
    BASAL_GANGLIA = "basal_ganglia"  # Procedural memory
    DEFAULT_MODE = "default_mode"    # Reflection and introspection
    INHIBITION = "inhibition"    # Active forgetting
    
    @staticmethod
    def get_memory_type_mapping() -> Dict[str, str]:
        return {
            "episodic": BrainRegion.HIPPOCAMPUS,
            "semantic": BrainRegion.NEOCORTEX,
            "working": BrainRegion.PREFRONTAL,
            "emotional": BrainRegion.AMYGDALA,
            "procedural": BrainRegion.BASAL_GANGLIA
        }


class BrainAgent(ABC):
    """统一的脑启发智能体基类 - 消除双轨架构"""
    
    def __init__(self, agent_id: str, brain_region: str, system_prompt: str, client=None):
        self.agent_id = agent_id
        self.brain_region = brain_region
        self.system_prompt = system_prompt

        # 🔥 FIX: Initialize settings FIRST before using it
        self.settings = get_settings()

        # 移除客户端缓存，每次调用时动态获取以避免跨事件循环问题
        # client参数保留用于向后兼容，但不再缓存
        self.model = self.settings.default_llm_model

        # Agent state
        self.is_active = True
        self.message_queue = asyncio.Queue()
        self.response_cache: OrderedDict[str, str] = OrderedDict()
        self._fallback_cache_size = self.settings.fallback_cache_size
        self.lock = asyncio.Lock()
        self._memory_write_lock = asyncio.Lock()  # 保护 self.memories / self.memory_dict 的写操作
        self.execution_log = []  # 统一执行日志
        
        # Brain-inspired properties
        self.activation_level = 0.5  # Current activation (0-1)
        self.fatigue_level = 0.0     # Mental fatigue (0-1)  
        self.attention_focus = []    # Current focus items
        
        logger.debug(f"Initialized {agent_id} ({brain_region})")
    
    def log_execution(self, action: str, details: Any = None, status: str = "info"):
        """统一执行日志记录"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'agent_id': self.agent_id,
            'action': action,
            'details': details,
            'status': status
        }
        self.execution_log.append(log_entry)
        if len(self.execution_log) > 100:
            self.execution_log = self.execution_log[-100:]
    
    @abstractmethod
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process incoming message - to be implemented by subclasses"""
        raise NotImplementedError
    
    async def call_llm(self, prompt: str, context: Dict[str, Any] = None, max_tokens: int = None, temperature: float = None, quick_fail: bool = False, system_prompt: str = None) -> str:
        """统一的LLM调用接口 - 集成限流、统一重试策略和错误处理 + 语义缓存"""
        # 使用全局信号量进行并发控制，避免连接池竞态
        from ..coordination.clean_agent_system import _global_semaphore
        async with _global_semaphore:

            # P0-1: 尝试从语义缓存获取（需要 embedding 才能真正语义匹配）
            from ..utils.semantic_cache import get_llm_cache
            llm_cache = get_llm_cache()

            # 计算 query embedding 用于语义相似度匹配
            query_embedding = None
            if llm_cache.enable_cache and llm_cache.similarity_threshold > 0:
                try:
                    from ..services.shared_openai_client import shared_client_manager
                    from ..core.constants import DEFAULT_EMBEDDING_MODEL
                    embedding_client = await shared_client_manager.get_embedding_client()
                    embed_response = await embedding_client.embeddings.create(
                        model=DEFAULT_EMBEDDING_MODEL,
                        input=prompt
                    )
                    import numpy as np
                    query_embedding = np.array(embed_response.data[0].embedding)
                except Exception as e:
                    logger.debug(f"Failed to compute query embedding for cache: {e}")
                    query_embedding = None

            cached_response = llm_cache.get(query=prompt, query_embedding=query_embedding, context=context)
            if cached_response:
                self.log_execution("LLM cache hit", {"query_length": len(prompt)}, "success")
                return cached_response

            # 统一应用层重试策略（增加重试次数以应对网络波动和长时间断网）
            # 🔥 2025-12-26: 提高到15次重试以应对长时间断网（10分钟+）
            max_retries = 0 if quick_fail else 15
            timeout_override = 5.0 if quick_fail else None  # 5s timeout for quick_fail
            base_delay = 2.0  # 增加基础延迟
            cache_key = self._build_cache_key(prompt, context)

            for attempt in range(max_retries + 1):
                try:
                    self.log_execution("Calling LLM", {"model": self.model, "attempt": attempt + 1})
                    
                    # 每次都动态获取共享客户端，避免跨事件循环问题
                    from ..services.shared_openai_client import shared_client_manager
                    client = await shared_client_manager.get_chat_client()
                    
                    messages = [{"role": "system", "content": self.system_prompt}]
                    
                    if context:
                        context_str = json.dumps(context, indent=2, default=str)
                        messages.append({"role": "system", "content": f"Context: {context_str}"})
                    
                    messages.append({"role": "user", "content": prompt})
                    
                    # 统一参数设置
                    actual_max_tokens = max_tokens if max_tokens is not None else int(get_env("MAX_TOKENS", "1500"))
                    actual_temperature = temperature if temperature is not None else float(get_env("TEMPERATURE", "0.7"))
                    
                    # Apply timeout for all LLM calls with configurable limits
                    llm_call = client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        max_tokens=actual_max_tokens,
                        temperature=actual_temperature
                    )

                    # Use specific timeout for quick_fail or global timeout for normal calls
                    if timeout_override:
                        response = await asyncio.wait_for(llm_call, timeout=timeout_override)
                    else:
                        from ..utils.config import get_settings
                        settings = get_settings()
                        response = await asyncio.wait_for(llm_call, timeout=settings.llm_call_timeout)
                    
                    result = response.choices[0].message.content.strip()
                    self.log_execution("LLM call success", {
                        "response_length": len(result),
                        "attempt": attempt + 1
                    }, "success")

                    # 报告连接成功
                    from ..services.shared_openai_client import shared_client_manager
                    shared_client_manager.report_connection_success()

                    # 存入旧缓存（向后兼容）
                    self._store_cached_response(cache_key, result)

                    # P0-1: 存入语义缓存（带 embedding 以支持语义匹配）
                    llm_cache.put(query=prompt, response=result, query_embedding=query_embedding, context=context)

                    return result

                except Exception as e:
                    import traceback
                    error_trace = traceback.format_exc()
                    self.log_execution("LLM call error", {
                        "error": str(e), 
                        "attempt": attempt + 1,
                        "trace": error_trace
                    }, "error")
                    
                    # 判断是否为可重试的错误（扩展错误类型检测）
                    error_str = str(e).lower()
                    error_type = type(e).__name__
                    is_retryable = any(keyword in error_str for keyword in [
                        'tcptransport', 'connection error', 'connection pool',
                        'closed=true', 'unable to perform', 'timeout',
                        '520', '502', '503', '504',  # HTTP错误码
                        'internal server error', 'bad gateway', 'service unavailable',
                        'gateway timeout', 'cloudflare'
                    ]) or error_type in ['TimeoutError', 'asyncio.TimeoutError']
                    
                    if is_retryable and attempt < max_retries:
                        # 指数退避重试（限制最大等待时间为120秒，应对长时间断网）
                        delay = min(base_delay * (2 ** attempt), 120)  # 2s, 4s, 8s, 16s, 32s, 64s, 120s...
                        logger.warning(f"Agent {self.agent_id} retrying after {delay}s, attempt {attempt + 1}/{max_retries}")

                        # 连接错误时报告给管理器
                        if any(kw in error_str for kw in ['connection error', 'connection pool']):
                            from ..services.shared_openai_client import shared_client_manager
                            shared_client_manager.report_connection_error()
                        
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # 最终失败处理
                        logger.error(f"LLM call failed permanently in {self.agent_id}: {type(e).__name__}: {e}")

                        cached = self._get_cached_response(cache_key)
                        if cached:
                            logger.debug("Serving cached response for %s after LLM failure", self.agent_id)
                            return f"[缓存响应]\n{cached}"

                        # 智能降级处理
                        if "Connection error" in str(e) or "timeout" in str(e).lower():
                            return f"[API连接问题，使用缓存响应] 基于记忆的智能回答..."
                        elif "rate limit" in str(e).lower():
                            return f"⏱️ API调用频率限制，{self.agent_id}已排队等待处理..."
                        else:
                            return f"⚠️ API异常: {type(e).__name__}: {str(e)}"

    def _build_cache_key(self, prompt: str, context: Optional[Dict[str, Any]]) -> str:
        payload = {
            'prompt': prompt,
            'context': context or {}
        }
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.md5(serialized.encode('utf-8')).hexdigest()

    def _store_cached_response(self, cache_key: str, response: str):
        if not response:
            return
        self.response_cache[cache_key] = response
        self.response_cache.move_to_end(cache_key)
        while len(self.response_cache) > self._fallback_cache_size:
            self.response_cache.popitem(last=False)

    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        if cache_key in self.response_cache:
            self.response_cache.move_to_end(cache_key)
            return self.response_cache[cache_key]
        return None
    
    async def send_message(self, receiver: str, message_type: str, content: Dict[str, Any], priority: str = "medium") -> str:
        """Send message to another agent"""
        message = AgentMessage(
            sender=self.agent_id,
            receiver=receiver,
            message_type=message_type,
            content=content,
            priority=priority
        )
        # This would be handled by the coordinator
        return message.correlation_id
    
    def update_activation(self, delta: float):
        """Update activation level (brain fatigue simulation)"""
        self.activation_level = max(0.0, min(1.0, self.activation_level + delta))
        if delta < 0:  # Fatigue increases when activation decreases
            self.fatigue_level = min(1.0, self.fatigue_level + abs(delta) * 0.1)
    
    async def initialize(self):
        """Initialize agent resources"""
        logger.debug(f"Agent {self.agent_id} initialized")
    
    async def shutdown(self):
        """Cleanup agent resources"""
        logger.debug(f"Agent {self.agent_id} shutting down")
