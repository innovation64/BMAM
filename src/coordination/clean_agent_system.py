"""
Clean Agent System - 简洁的12智能体系统
移除冗余包装器，直接使用核心智能体
"""

import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..utils.config import get_logger
from ..agents.base import BrainAgent

# 直接导入核心智能体，无需包装器
from ..agents.core.short_term_memory import ShortTermMemoryAgent
from ..agents.core.long_term_memory import LongTermMemoryAgent
from ..agents.core.memory_retrieval import MemoryRetrievalAgent  
from ..agents.core.consolidation import ConsolidationAgent
from ..agents.core.memory_distortion import MemoryDistortionAgent
from ..agents.core.reflection import ReflectionAgent
from ..agents.core.forgetting import ForgettingAgent
from ..agents.core.stress_response import StressResponseAgent
from ..agents.core.personality import PersonalityAgent
from ..agents.core.persona_memory import PersonaMemoryAgent

logger = get_logger(__name__)

# 全局并发控制
_global_semaphore = asyncio.Semaphore(4)


class BrainRegion(Enum):
    """脑区枚举"""
    HIPPOCAMPUS = "hippocampus"
    NEOCORTEX = "neocortex"  
    PREFRONTAL = "prefrontal"
    AMYGDALA = "amygdala"
    THALAMUS = "thalamus"
    BASAL_GANGLIA = "basal_ganglia"
    DEFAULT_MODE = "default_mode"
    INHIBITION = "inhibition"
    BROCA_WERNICKE = "broca_wernicke"
    ACC = "acc"
    MOTOR_CORTEX = "motor_cortex"
    SENSORY_CORTEX = "sensory_cortex"


@dataclass
class AgentMessage:
    """智能体间通信消息"""
    sender: str
    receiver: str
    message_type: str
    content: Dict[str, Any]
    priority: str = "medium"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    correlation_id: str = field(default_factory=lambda: str(__import__('uuid').uuid4()))


# ========================================
# 辅助智能体 - 简单实现
# ========================================

class ConversationAgent(BrainAgent):
    """对话智能体"""
    
    def __init__(self):
        super().__init__(
            "conversation",
            BrainRegion.BROCA_WERNICKE.value,
            "你是语言理解和生成系统，负责自然语言交互和对话管理。"
        )
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        action = message.content.get('action')
        
        if action == 'generate_response':
            return await self._generate_response(
                message.content['user_input'],
                message.content.get('context', {}),
                message.content.get('memories', [])
            )
        
        return {'error': 'Unknown action', 'action': action}
    
    async def _generate_response(self, user_input: str, context: Dict, memories: List[Dict]) -> Dict[str, Any]:
        """生成对话响应"""
        # 构建记忆上下文
        memory_context = ""
        if memories:
            memory_context = "\n相关记忆：\n"
            for i, memory in enumerate(memories[:3], 1):
                memory_context += f"{i}. {memory.get('content', '')[:100]}...\n"

        prompt = f"""基于记忆生成自然回复：

用户输入：{user_input}
{memory_context}

请生成一个自然、有帮助的中文回复，体现对用户的了解。"""
        
        llm_failed = False
        response = await self.call_llm(
            prompt,
            context,
            max_tokens=600,
            quick_fail=False  # allow full timeout window for primary response
        )

        if self._looks_like_llm_error(response):
            llm_failed = True
            response = self._build_memory_fallback(user_input, memories, context)

        return {
            'response': response,
            'memories_used': len(memories),
            'context_applied': bool(context),
            'llm_failed': llm_failed
        }

    def _looks_like_llm_error(self, response: str) -> bool:
        if not response:
            return True
        error_markers = ['⚠️', 'API异常', 'API连接问题', '⏱️']
        return any(marker in response for marker in error_markers)

    def _build_memory_fallback(self, user_input: str, memories: List[Dict], context: Dict) -> str:
        if memories:
            important = memories[0].get('content', '')
            preference = ""
            for mem in memories:
                content = mem.get('content', '')
                if any(keyword in content for keyword in ['喜欢', '偏好', '记住', '咖啡', '茶']):
                    preference = content
                    break
            fallback_parts = [
                "抱歉，刚才思考得有点慢，不过我记得我们聊过：",
                preference or important[:120],
            ]
            return "".join(fallback_parts)

        # 没有记忆时仍给出友好回应
        return "我刚刚反应慢了一点，不过我会继续记得你告诉我的事情。可以再说说你的想法吗？"


class ExecutiveControlAgent(BrainAgent):
    """执行控制智能体"""
    
    def __init__(self):
        super().__init__(
            "executive_control",
            BrainRegion.ACC.value,
            "你是执行控制和任务协调系统，负责任务规划和智能体协调。"
        )
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        action = message.content.get('action')
        
        if action == 'coordinate_agents':
            return await self._coordinate_agents(message.content['task_info'])
        
        return {'error': 'Unknown action', 'action': action}
    
    async def _coordinate_agents(self, task_info: Dict[str, Any]) -> Dict[str, Any]:
        """协调智能体 - 使用可塑性优化的智能路由"""
        task_type = task_info.get('type', 'general')
        
        # 优先使用可塑性引擎的优化序列
        optimal_sequence = task_info.get('optimal_sequence', [])
        
        if optimal_sequence and len(optimal_sequence) >= 2:
            # 使用可塑性引擎优化的智能体序列
            primary_agents = optimal_sequence[:2]
            secondary_agents = optimal_sequence[2:4] if len(optimal_sequence) > 2 else []
        else:
            # 回退到基础路由规则
            if task_type == 'memory_storage':
                primary_agents = ['long_term_memory', 'consolidation']
                secondary_agents = ['short_term_memory']
            elif task_type == 'memory_retrieval':
                primary_agents = ['memory_retrieval', 'short_term_memory']
                secondary_agents = ['reflection']
            elif task_type == 'conversation':
                primary_agents = ['conversation', 'personality']
                secondary_agents = ['memory_retrieval']
            else:
                primary_agents = ['conversation']
                secondary_agents = ['memory_retrieval']
        
        return {
            'coordination_plan': {
                'primary_agents': primary_agents,
                'secondary_agents': secondary_agents,
                'execution_order': 'parallel',
                'routing_method': 'plasticity_optimized' if optimal_sequence else 'fallback_rules'
            }
        }


# Import the enhanced perception encoding agent (resides under agents.core)
from ..agents.core.perception_encoding import (
    EnhancedPerceptionEncodingAgent as PerceptionEncodingAgent,
)


class ActionExecutionAgent(BrainAgent):
    """行动执行智能体"""
    
    def __init__(self):
        super().__init__(
            "action_execution",
            BrainRegion.MOTOR_CORTEX.value,
            "你是决策执行系统，负责执行具体行动。"
        )
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        action = message.content.get('action')
        
        if action == 'execute_tool':
            return await self._execute_tool(
                message.content['tool_name'],
                message.content.get('parameters', {})
            )
        
        return {'error': 'Unknown action', 'action': action}
    
    async def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具"""
        # 简单的工具执行模拟
        return {
            'tool_name': tool_name,
            'result': f"执行工具 {tool_name} 成功",
            'success': True,
            'execution_time': datetime.now().isoformat()
        }


# ========================================
# 导出清洁的智能体类
# ========================================

__all__ = [
    'BrainRegion', 'AgentMessage',
    # 核心记忆智能体 - 直接导入
    'ShortTermMemoryAgent', 'LongTermMemoryAgent', 'MemoryRetrievalAgent',
    'ConsolidationAgent', 'MemoryDistortionAgent', 'ReflectionAgent',
    'ForgettingAgent', 'StressResponseAgent', 'PersonalityAgent',
    'PersonaMemoryAgent',
    # 辅助智能体 - 简洁实现  
    'ConversationAgent', 'ExecutiveControlAgent',
    'PerceptionEncodingAgent', 'ActionExecutionAgent'
]
