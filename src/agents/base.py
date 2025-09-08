"""
Base Agent Class for Brain-Inspired Memory System
基础智能体类 - 所有智能体的父类
"""

import asyncio
import json
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod
import openai
from ..utils.config import get_logger, get_env
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
    timestamp: datetime = field(default_factory=datetime.now)
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
    """Base class for brain-inspired agents"""
    
    def __init__(self, agent_id: str, brain_region: str, system_prompt: str):
        self.agent_id = agent_id
        self.brain_region = brain_region
        self.system_prompt = system_prompt
        
        # OpenAI client - 每个智能体独立创建，简单可靠
        self.client = openai.AsyncOpenAI(
            api_key=get_env("OPENAI_API_KEY"),
            timeout=float(get_env("AGENT_TIMEOUT", "30.0"))
        )
        self.model = get_env("DEFAULT_MODEL", "gpt-4o-mini")
        
        # Agent state
        self.is_active = True
        self.message_queue = asyncio.Queue()
        self.response_cache = {}
        self.lock = asyncio.Lock()
        
        # Brain-inspired properties
        self.activation_level = 0.5  # Current activation (0-1)
        self.fatigue_level = 0.0     # Mental fatigue (0-1)
        self.attention_focus = []    # Current focus items
        
        logger.info(f"Initialized {agent_id} ({brain_region})")
    
    @abstractmethod
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process incoming message - to be implemented by subclasses"""
        raise NotImplementedError
    
    async def call_llm(self, prompt: str, context: Dict[str, Any] = None, max_tokens: int = None, temperature: float = None) -> str:
        """Call LLM with brain region context"""
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                messages = [{"role": "system", "content": self.system_prompt}]
                
                if context:
                    context_str = json.dumps(context, indent=2, default=str)
                    messages.append({"role": "system", "content": f"Context: {context_str}"})
                
                messages.append({"role": "user", "content": prompt})
                
                # Use provided parameters or fall back to environment defaults
                actual_max_tokens = max_tokens if max_tokens is not None else int(get_env("MAX_TOKENS", "1500"))
                actual_temperature = temperature if temperature is not None else float(get_env("TEMPERATURE", "0.7"))
                
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=actual_max_tokens,
                    temperature=actual_temperature,
                    timeout=30  # 添加超时设置
                )
                
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                logger.warning(f"LLM attempt {attempt + 1}/{max_retries} failed in {self.agent_id}: {e}")
                
                # 如果是最后一次尝试，记录错误并抛出异常让上层处理
                if attempt == max_retries - 1:
                    logger.error(f"LLM all attempts failed in {self.agent_id}: {e}")
                    raise e
                
                # 等待后重试
                await asyncio.sleep(retry_delay * (attempt + 1))  # 指数退避
        
        raise Exception("LLM调用失败")
    
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
        logger.info(f"Agent {self.agent_id} initialized")
    
    async def shutdown(self):
        """Cleanup agent resources"""
        logger.info(f"Agent {self.agent_id} shutting down")