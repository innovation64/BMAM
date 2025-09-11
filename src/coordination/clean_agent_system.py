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
        
        response = await self.call_llm(prompt, context, max_tokens=200, quick_fail=True)
        
        return {
            'response': response,
            'memories_used': len(memories),
            'context_applied': bool(context)
        }


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


class PerceptionEncodingAgent(BrainAgent):
    """感知编码智能体"""
    
    def __init__(self):
        super().__init__(
            "perception_encoding",
            BrainRegion.SENSORY_CORTEX.value,
            "你是信息感知和编码系统，负责处理输入信息。"
        )
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        action = message.content.get('action')
        
        if action == 'encode_input':
            return await self._encode_input(message.content['input_data'])
        
        return {'error': 'Unknown action', 'action': action}
    
    async def _encode_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """编码输入数据"""
        content = input_data.get('content', '')
        
        features = {
            'length': len(content),
            'word_count': len(content.split()),
            'input_type': input_data.get('type', 'text'),
            'complexity': 'high' if len(content) > 100 else 'medium' if len(content) > 50 else 'low'
        }
        
        return {
            'encoded_input': {
                'content': content,
                'features': features,
                'encoding_timestamp': datetime.now().isoformat()
            },
            'encoding_success': True
        }


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
    # 辅助智能体 - 简洁实现  
    'ConversationAgent', 'ExecutiveControlAgent',
    'PerceptionEncodingAgent', 'ActionExecutionAgent'
]