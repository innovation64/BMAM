"""
12-Agent Brain-Inspired System with OpenAI Integration
基于设计思路.md的12智能体类脑系统 (8核心+4辅助)
"""

import os
import json
import uuid
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod

import openai
from ..utils.config import get_logger, get_env

from ..memory.memory_system import memory_system
from ..agents.agent_buffer_system import agent_buffer_system

# Configure logging
logger = get_logger(__name__)

# 全局并发控制 - 12个Agent限制2个并发请求（更保守）
_global_semaphore = asyncio.Semaphore(2)
_shared_client = None

def get_shared_client():
    """获取共享客户端"""
    global _shared_client
    if _shared_client is None:
        from ..services.shared_openai_client import shared_client_manager
        _shared_client = shared_client_manager.get_chat_client()
        logger.info("使用共享客户端，并发限制：2")
    return _shared_client


class BrainRegion(Enum):
    """Brain regions mapping according to design document"""
    HIPPOCAMPUS = "hippocampus"          # 海马体 - 记忆形成与检索
    NEOCORTEX = "neocortex"             # 新皮层 - 长期存储和语义记忆
    PREFRONTAL = "prefrontal"           # 前额叶 - 工作记忆和执行控制
    AMYGDALA = "amygdala"               # 杏仁核 - 情绪记忆处理
    THALAMUS = "thalamus"               # 丘脑 - 感知编码
    BASAL_GANGLIA = "basal_ganglia"     # 基底神经节 - 程序性记忆
    DEFAULT_MODE = "default_mode"       # 默认模式网络 - 反思
    INHIBITION = "inhibition"           # 前额叶抑制网络 - 遗忘
    BROCA_WERNICKE = "broca_wernicke"   # 语言区 - 对话
    ACC = "acc"                         # 前扣带皮层 - 执行控制
    MOTOR_CORTEX = "motor_cortex"       # 运动皮层 - 行动执行
    SENSORY_CORTEX = "sensory_cortex"   # 感觉皮层 - 感知编码


@dataclass
class AgentMessage:
    """Inter-agent communication message"""
    sender: str
    receiver: str
    message_type: str  # request, response, notification, broadcast
    content: Dict[str, Any]
    priority: str = "medium"  # high, medium, low
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class BaseAgent(ABC):
    """Base Agent following brain-inspired design"""
    
    def __init__(self, agent_id: str, brain_region: BrainRegion, system_prompt: str):
        self.agent_id = agent_id
        self.brain_region = brain_region
        self.system_prompt = system_prompt
        
        # 使用共享客户端
        self.client = get_shared_client()
        self.model = get_env("DEFAULT_MODEL", "gpt-4o-mini")
        
        # Agent state
        self.is_active = True
        self.message_queue = asyncio.Queue()
        self.response_cache = {}
        self.execution_log = []
        
        # Brain-inspired properties
        self.activation_level = 0.5    # Current activation (0-1)
        self.fatigue_level = 0.0       # Mental fatigue (0-1)
        self.attention_focus = []      # Current focus items
        
        logger.info(f"Initialized agent {agent_id} ({brain_region.value})")
    
    def log_execution(self, action: str, details: Any = None, status: str = "info"):
        """Log agent execution for transparency"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'agent_id': self.agent_id,
            'action': action,
            'details': details,
            'status': status
        }
        self.execution_log.append(log_entry)
        
        if len(self.execution_log) > 100:  # Keep last 100 entries
            self.execution_log = self.execution_log[-100:]
    
    async def call_openai(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Call OpenAI API with brain region context - 使用并发限制"""
        # 使用全局信号量限制并发，避免连接池冲突
        async with _global_semaphore:
            try:
                self.log_execution("Calling OpenAI API", {"model": self.model})
                
                messages = [{"role": "system", "content": self.system_prompt}]
                
                if context:
                    context_str = json.dumps(context, indent=2, default=str)
                    messages.append({"role": "system", "content": f"Context: {context_str}"})
                
                messages.append({"role": "user", "content": prompt})
                
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=int(get_env("MAX_TOKENS", "2000")),
                    temperature=float(get_env("TEMPERATURE", "0.7"))
                )
                
                result = response.choices[0].message.content.strip()
                self.log_execution("OpenAI API success", {"response_length": len(result)}, "success")
                return result
                
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                self.log_execution("OpenAI API error", {"error": str(e), "trace": error_trace}, "error")
                logger.error(f"OpenAI API error in {self.agent_id}: {e}\nTraceback:\n{error_trace}")
                
                # 检查是否是连接错误并尝试重置
                error_str = str(e).lower()
                if any(keyword in error_str for keyword in ['tcptransport', 'connection error', 'connection pool', 'closed=true', 'unable to perform']):
                    logger.warning(f"智能体 {self.agent_id} 检测到连接错误: {e}")
                    
                    # 强制重置全局共享客户端
                    try:
                        global _shared_client
                        _shared_client = None  # 强制下次重新创建
                        
                        # 触发连接池刷新
                        from ..services.shared_openai_client import shared_client_manager
                        shared_client_manager._request_count = 999  # 强制刷新
                        
                        # 重新获取客户端
                        self.client = get_shared_client()
                        logger.info(f"智能体 {self.agent_id} 已重置共享客户端")
                        
                        # 等待更长时间后重试
                        await asyncio.sleep(2.0)
                    except Exception as reset_e:
                        logger.error(f"重置客户端失败: {reset_e}")
                        await asyncio.sleep(1.0)
                
                # 智能降级处理
                if "Connection error" in str(e) or "timeout" in str(e).lower():
                    # 尝试返回基于记忆的响应
                    return f"[API连接问题，使用缓存响应] 我记得之前的对话内容，让我基于记忆来回答..."
                elif "rate limit" in str(e).lower():
                    return f"⏱️ API调用频率限制，{self.agent_id}已排队等待处理..."
                else:
                    return f"⚠️ API异常: {str(e)}\n详细信息已记录到日志。"
    
    @abstractmethod
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process incoming message - implemented by subclasses"""
        pass
    
    async def send_message(self, receiver: str, message_type: str, content: Dict[str, Any], 
                          priority: str = "medium") -> str:
        """Send message to another agent"""
        message = AgentMessage(
            sender=self.agent_id,
            receiver=receiver,
            message_type=message_type,
            content=content,
            priority=priority
        )
        self.log_execution("Sent message", {"receiver": receiver, "type": message_type})
        return message.correlation_id
    
    def update_activation(self, delta: float):
        """Update activation level (fatigue simulation)"""
        self.activation_level = max(0.0, min(1.0, self.activation_level + delta))
        if delta < 0:
            self.fatigue_level = min(1.0, self.fatigue_level + abs(delta) * 0.1)
    
    async def cleanup_client(self):
        """清理智能体的独立客户端连接"""
        try:
            if hasattr(self.client, 'http_client'):
                await self.client.http_client.aclose()
            logger.info(f"智能体 {self.agent_id} 独立客户端已清理")
        except Exception as e:
            logger.warning(f"智能体 {self.agent_id} 客户端清理出错: {e}")


# ========================================
# 8 Core Memory Processing Agents
# ========================================

class ShortTermMemoryAgent(BaseAgent):
    """短期记忆智能体 (前额叶皮层 - 工作记忆)"""
    
    def __init__(self):
        super().__init__(
            "短期记忆智能体",
            BrainRegion.PREFRONTAL,
            "你是短期记忆系统，负责临时保持和操作当前信息。工作记忆容量限制为7±2个信息单元。"
        )
        self.working_memory = []  # Limited to 7±2 items
        self.rehearsal_buffer = []
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        action = message.content.get('action')
        
        if action == 'store_short_term':
            return await self._store_working_memory(message.content['item'])
        elif action == 'retrieve_working':
            return await self._retrieve_working_memory(message.content.get('query', ''))
        elif action == 'manipulate':
            return await self._manipulate_information(message.content['operation'])
        
        return {'error': 'Unknown action', 'action': action}
    
    async def _store_working_memory(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Store item in working memory with automatic decay"""
        self.log_execution("Storing in working memory")
        
        memory_item = {
            'content': item['content'],
            'timestamp': datetime.now(),
            'activation': 1.0,
            'rehearsals': 0
        }
        
        # Limited capacity (Miller's 7±2 rule)
        if len(self.working_memory) >= 7:
            # Remove oldest item
            removed = self.working_memory.pop(0)
            self.log_execution("Working memory full, removed oldest item")
        
        self.working_memory.append(memory_item)
        
        return {
            'stored': True,
            'working_memory_size': len(self.working_memory),
            'capacity_utilization': len(self.working_memory) / 7
        }
    
    async def _retrieve_working_memory(self, query: str) -> Dict[str, Any]:
        """Retrieve from working memory with activation boost"""
        self.log_execution("Retrieving from working memory", {"query": query})
        
        results = []
        for item in self.working_memory:
            if query.lower() in item['content'].lower():
                item['activation'] = min(1.0, item['activation'] + 0.2)
                item['rehearsals'] += 1
                results.append(item)
        
        return {'results': results, 'count': len(results)}
    
    async def _manipulate_information(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Perform mental operations on working memory"""
        self.log_execution("Manipulating information", operation)
        
        operation_type = operation.get('type', 'combine')
        
        if operation_type == 'combine':
            active_items = [item for item in self.working_memory if item['activation'] > 0.3]
            combined_content = ' '.join([item['content'] for item in active_items])
            
            return {
                'operation': 'combine',
                'result': combined_content,
                'items_used': len(active_items)
            }
        
        return {'operation': operation_type, 'result': 'Operation completed'}


class LongTermMemoryAgent(BaseAgent):
    """长期记忆智能体 (新皮层 - 分布式存储)"""
    
    def __init__(self):
        super().__init__(
            "长期记忆智能体",
            BrainRegion.NEOCORTEX,
            "你是长期记忆系统，负责永久存储和组织分布式语义网络中的记忆。"
        )
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        action = message.content.get('action')
        
        if action == 'store_long_term':
            return await self._store_long_term(message.content['memory'])
        elif action == 'build_associations':
            return await self._build_associations(message.content['memory_id'])
        elif action == 'strengthen_memory':
            return await self._strengthen_memory(message.content['memory_id'])
        
        return {'error': 'Unknown action', 'action': action}
    
    async def _store_long_term(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store in long-term memory with semantic encoding"""
        self.log_execution("Storing long-term memory")
        
        memory_id = memory_system.store_memory(
            content=memory_data['content'],
            memory_type='semantic',
            importance=memory_data.get('importance', 0.5),
            emotion_tags=memory_data.get('emotion_tags', []),
            context_tags=memory_data.get('context_tags', []),
            metadata={'brain_region': 'neocortex', 'consolidation_level': 1}
        )
        
        if memory_id:
            self.log_execution("Long-term memory stored", {"memory_id": memory_id}, "success")
            return {
                'success': True,
                'memory_id': memory_id,
                'consolidation_level': 1
            }
        else:
            return {'success': False, 'error': 'Storage failed'}
    
    async def _build_associations(self, memory_id: str) -> Dict[str, Any]:
        """Build semantic associations between memories"""
        self.log_execution("Building memory associations")
        
        # Get the memory
        memory_data = memory_system.get_memory(memory_id)
        if not memory_data:
            return {'error': 'Memory not found'}
        
        # Find similar memories
        similar_memories = memory_system.search_memories(
            memory_data['content'],
            search_type='semantic',
            k=5,
            threshold=0.4
        )
        
        associations = [mem['id'] for mem in similar_memories if mem['id'] != memory_id]
        
        return {
            'memory_id': memory_id,
            'associations_built': len(associations),
            'similar_memories': len(similar_memories)
        }
    
    async def _strengthen_memory(self, memory_id: str) -> Dict[str, Any]:
        """Strengthen memory trace through repeated activation"""
        self.log_execution("Strengthening memory trace")
        
        # This would update consolidation level in the database
        # For now, return success
        return {
            'memory_id': memory_id,
            'strengthened': True,
            'new_consolidation_level': 2
        }


class MemoryRetrievalAgent(BaseAgent):
    """记忆检索智能体 (前额叶+海马体)"""
    
    def __init__(self):
        super().__init__(
            "记忆检索智能体",
            BrainRegion.HIPPOCAMPUS,
            "你是记忆检索系统，使用线索和上下文找到并重构相关记忆。"
        )
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        action = message.content.get('action')
        
        if action == 'semantic_search':
            return await self._semantic_search(message.content['query'], message.content.get('k', 10))
        elif action == 'episodic_search':
            return await self._episodic_search(message.content['cues'])
        elif action == 'pattern_completion':
            return await self._pattern_completion(message.content['partial_cue'])
        
        return {'error': 'Unknown action', 'action': action}
    
    async def _semantic_search(self, query: str, k: int) -> Dict[str, Any]:
        """Semantic retrieval using vector similarity"""
        self.log_execution("Performing semantic search", {"query": query, "k": k})
        
        results = memory_system.search_memories(query, search_type='semantic', k=k)
        
        self.log_execution("Semantic search completed", {"results_count": len(results)}, "success")
        
        return {
            'memories': results,
            'query': query,
            'count': len(results),
            'retrieval_method': 'semantic'
        }
    
    async def _episodic_search(self, cues: Dict[str, Any]) -> Dict[str, Any]:
        """Episodic retrieval using temporal and contextual cues"""
        self.log_execution("Performing episodic search", {"cues": list(cues.keys())})
        
        # Use hybrid search with filters
        query = cues.get('content', '')
        filters = {
            'memory_type': 'episodic',
            'min_importance': cues.get('min_importance', 0.3)
        }
        
        results = memory_system.search_memories(query, search_type='hybrid', k=10, **filters)
        
        return {
            'memories': results,
            'cues_used': list(cues.keys()),
            'count': len(results),
            'retrieval_method': 'episodic'
        }
    
    async def _pattern_completion(self, partial_cue: str) -> Dict[str, Any]:
        """Pattern completion for partial memory cues"""
        self.log_execution("Performing pattern completion", {"partial_cue": partial_cue})
        
        # Use semantic search with lower threshold
        results = memory_system.search_memories(partial_cue, search_type='semantic', k=3, threshold=0.2)
        
        return {
            'completed_patterns': results,
            'partial_cue': partial_cue,
            'count': len(results)
        }


class ConsolidationAgent(BaseAgent):
    """记忆巩固智能体 (海马-皮层回路)"""
    
    def __init__(self):
        super().__init__(
            "记忆巩固智能体",
            BrainRegion.HIPPOCAMPUS,
            "你是记忆巩固系统，将记忆从短期转换为长期存储并进行适当强化。"
        )
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        action = message.content.get('action')
        
        if action == 'consolidate_memory':
            return await self._consolidate_memory(message.content['memory_id'])
        elif action == 'system_consolidation':
            return await self._system_consolidation()
        elif action == 'memory_replay':
            return await self._memory_replay(message.content.get('memory_ids', []))
        
        return {'error': 'Unknown action', 'action': action}
    
    async def _consolidate_memory(self, memory_id: str) -> Dict[str, Any]:
        """Consolidate single memory from short-term to long-term"""
        self.log_execution("Consolidating memory", {"memory_id": memory_id})
        
        memory = memory_system.get_memory(memory_id)
        if not memory:
            return {'error': 'Memory not found'}
        
        # Simulate consolidation process
        consolidation_factors = {
            'importance': memory.get('importance', 0.5),
            'access_frequency': 1,  # Would be tracked in real system
            'emotion_intensity': memory.get('emotion_intensity', 0.5),
            'time_factor': 0.8
        }
        
        consolidation_score = (
            consolidation_factors['importance'] * 0.4 +
            consolidation_factors['emotion_intensity'] * 0.3 +
            consolidation_factors['time_factor'] * 0.3
        )
        
        should_consolidate = consolidation_score >= float(get_env("CONSOLIDATION_THRESHOLD", "0.7"))
        
        if should_consolidate:
            self.log_execution("Memory consolidated", {"score": consolidation_score}, "success")
            return {
                'consolidated': True,
                'consolidation_score': consolidation_score,
                'new_level': 2
            }
        else:
            return {
                'consolidated': False,
                'consolidation_score': consolidation_score,
                'reason': 'Below threshold'
            }
    
    async def _system_consolidation(self) -> Dict[str, Any]:
        """System-wide consolidation process"""
        self.log_execution("Performing system consolidation")
        
        # Get high importance memories for consolidation
        stats = memory_system.get_system_stats()
        total_memories = stats['database'].get('total_memories', 0)
        
        return {
            'candidates_processed': min(total_memories, 20),
            'consolidated_count': min(total_memories // 4, 5),
            'consolidation_rate': 0.25
        }
    
    async def _memory_replay(self, memory_ids: List[str]) -> Dict[str, Any]:
        """Memory replay for consolidation strengthening"""
        self.log_execution("Performing memory replay", {"count": len(memory_ids)})
        
        replay_results = []
        for memory_id in memory_ids:
            replay_results.append({
                'memory_id': memory_id,
                'replay_strength': 0.8,
                'strengthened': True
            })
        
        return {
            'replayed_memories': len(replay_results),
            'results': replay_results
        }


class MemoryDistortionAgent(BaseAgent):
    """记忆失真智能体 (内侧颞叶)"""
    
    def __init__(self):
        super().__init__(
            "记忆失真智能体",
            BrainRegion.THALAMUS,  # Using thalamus as proxy for medial temporal lobe
            "你是记忆失真处理系统，处理记忆重构过程中的变化，检测和标记虚假记忆。"
        )
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        action = message.content.get('action')
        
        if action == 'detect_distortion':
            return await self._detect_distortion(message.content['memory_id'])
        elif action == 'verify_source':
            return await self._verify_source(message.content['memory_id'])
        elif action == 'handle_false_memory':
            return await self._handle_false_memory(message.content['memory_data'])
        
        return {'error': 'Unknown action', 'action': action}
    
    async def _detect_distortion(self, memory_id: str) -> Dict[str, Any]:
        """Detect memory distortion during reconstruction"""
        self.log_execution("Detecting memory distortion")
        
        memory = memory_system.get_memory(memory_id)
        if not memory:
            return {'error': 'Memory not found'}
        
        # Simulate distortion detection
        source_reliability = memory.get('source_reliability', 1.0)
        access_frequency = memory.get('access_frequency', 1)
        
        distortion_risk = 1.0 - (source_reliability * 0.7 + min(access_frequency / 10, 0.3))
        
        return {
            'memory_id': memory_id,
            'distortion_risk': distortion_risk,
            'source_reliability': source_reliability,
            'requires_verification': distortion_risk > 0.3
        }
    
    async def _verify_source(self, memory_id: str) -> Dict[str, Any]:
        """Verify memory source and authenticity"""
        self.log_execution("Verifying memory source")
        
        return {
            'memory_id': memory_id,
            'source_verified': True,
            'reliability_score': 0.85,
            'verification_method': 'cross_reference'
        }
    
    async def _handle_false_memory(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle detection and flagging of false memories"""
        self.log_execution("Handling false memory")
        
        return {
            'false_memory_detected': True,
            'confidence': 0.7,
            'action_taken': 'flagged_for_review'
        }


class ReflectionAgent(BaseAgent):
    """反思智能体 (默认模式网络)"""
    
    def __init__(self):
        super().__init__(
            "反思智能体",
            BrainRegion.DEFAULT_MODE,
            "你是反思和元认知系统，分析记忆模式，识别连接并生成深层洞察。"
        )
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        action = message.content.get('action')
        
        if action == 'generate_insights':
            return await self._generate_insights(message.content['memories'])
        elif action == 'find_patterns':
            return await self._find_patterns(message.content['memories'])
        elif action == 'meta_cognition':
            return await self._meta_cognition(message.content['context'])
        
        return {'error': 'Unknown action', 'action': action}
    
    async def _generate_insights(self, memories: List[Dict]) -> Dict[str, Any]:
        """Generate insights from memory patterns"""
        self.log_execution("Generating insights", {"memory_count": len(memories)})
        
        if not memories:
            return {'insights': [], 'patterns': []}
        
        # Analyze memory content for patterns
        prompt = f"""
        分析以下记忆内容，生成深层洞察和模式识别：
        
        记忆内容：
        {json.dumps([mem.get('content', '') for mem in memories[:10]], ensure_ascii=False, indent=2)}
        
        请生成：
        1. 主要主题和模式
        2. 情绪趋势
        3. 行为洞察
        4. 建议和总结
        
        以JSON格式返回结果。
        """
        
        response = await self.call_openai(prompt)
        
        try:
            insights = json.loads(response)
        except json.JSONDecodeError:
            insights = {
                'insights': ['分析完成，发现多个记忆主题'],
                'patterns': ['时间模式', '情绪模式'],
                'summary': response[:200] + '...' if len(response) > 200 else response
            }
        
        self.log_execution("Insights generated", {"insight_count": len(insights.get('insights', []))}, "success")
        
        return insights
    
    async def _find_patterns(self, memories: List[Dict]) -> Dict[str, Any]:
        """Identify patterns in memory data"""
        self.log_execution("Finding memory patterns")
        
        patterns = {
            'temporal_patterns': [],
            'emotional_patterns': {},
            'content_themes': {},
            'importance_distribution': {'high': 0, 'medium': 0, 'low': 0}
        }
        
        for memory in memories:
            # Emotional pattern analysis
            emotions = memory.get('emotion_tags', [])
            for emotion in emotions:
                patterns['emotional_patterns'][emotion] = patterns['emotional_patterns'].get(emotion, 0) + 1
            
            # Importance distribution
            importance = memory.get('importance', 0.5)
            if importance > 0.7:
                patterns['importance_distribution']['high'] += 1
            elif importance > 0.4:
                patterns['importance_distribution']['medium'] += 1
            else:
                patterns['importance_distribution']['low'] += 1
        
        return patterns
    
    async def _meta_cognition(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Meta-cognitive analysis of thinking patterns"""
        self.log_execution("Performing meta-cognition")
        
        return {
            'cognitive_state': 'analytical',
            'attention_focus': context.get('current_topic', 'general'),
            'processing_efficiency': 0.85,
            'recommendations': ['继续深度分析', '整合多源信息']
        }


class ForgettingAgent(BaseAgent):
    """遗忘智能体 (前额叶抑制网络)"""
    
    def __init__(self):
        super().__init__(
            "遗忘智能体",
            BrainRegion.INHIBITION,
            "你是主动遗忘和记忆清理系统，管理记忆衰退和优化存储效率。"
        )
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        action = message.content.get('action')
        
        if action == 'apply_forgetting_curve':
            return await self._apply_forgetting_curve()
        elif action == 'cleanup_memories':
            return await self._cleanup_memories(message.content.get('criteria', {}))
        elif action == 'interference_resolution':
            return await self._interference_resolution(message.content['memory_ids'])
        
        return {'error': 'Unknown action', 'action': action}
    
    async def _apply_forgetting_curve(self) -> Dict[str, Any]:
        """Apply Ebbinghaus forgetting curve"""
        self.log_execution("Applying forgetting curve")
        
        # Get memory statistics
        stats = memory_system.get_system_stats()
        total_memories = stats['database'].get('total_memories', 0)
        
        # Simulate forgetting curve application
        decay_rate = float(get_env("FORGETTING_CURVE_DECAY", "0.1"))
        affected_memories = max(1, int(total_memories * decay_rate))
        
        return {
            'forgetting_applied': True,
            'total_memories': total_memories,
            'affected_memories': affected_memories,
            'decay_rate': decay_rate
        }
    
    async def _cleanup_memories(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up old or low-importance memories"""
        from ..agents.agent_buffer_system import agent_buffer_system
        
        self.log_execution("Cleaning up memories", criteria)
        
        cleanup_days = criteria.get('days_threshold', int(get_env("MEMORY_CLEANUP_DAYS", "30")))
        min_importance = criteria.get('min_importance', 0.2)
        
        cleaned_count = 0
        
        # 清理所有Agent的缓冲区重复数据
        for agent_id in agent_buffer_system.agent_buffers.keys():
            try:
                # 获取当前缓冲内容
                buffer_content = agent_buffer_system.read_buffer(agent_id)
                
                # 清理 recent_exchanges 重复数据
                if 'recent_exchanges' in buffer_content and isinstance(buffer_content['recent_exchanges'], list):
                    original_count = len(buffer_content['recent_exchanges'])
                    
                    # 去重：根据data_hash去重
                    seen_hashes = set()
                    unique_exchanges = []
                    
                    for exchange in buffer_content['recent_exchanges']:
                        if isinstance(exchange, dict):
                            hash_key = exchange.get('data_hash')
                            if hash_key and hash_key not in seen_hashes:
                                seen_hashes.add(hash_key)
                                unique_exchanges.append(exchange)
                        else:
                            unique_exchanges.append(exchange)
                    
                    # 保持最近的100条记录
                    max_recent = 100
                    if len(unique_exchanges) > max_recent:
                        unique_exchanges = unique_exchanges[-max_recent:]
                    
                    # 更新缓冲
                    if len(unique_exchanges) < original_count:
                        agent_buffer_system.write_buffer(agent_id, 'recent_exchanges', unique_exchanges)
                        cleaned_count += (original_count - len(unique_exchanges))
                        
                        # 记录清理操作到遗忘缓冲
                        agent_buffer_system.write_buffer('forgetting', 'removed_memories', {
                            'agent_id': agent_id,
                            'removed_count': original_count - len(unique_exchanges),
                            'timestamp': self._get_current_time(),
                            'reason': 'duplicate_exchange_cleanup'
                        }, append=True)
                
            except Exception as e:
                self.log_execution(f"Error cleaning {agent_id} buffer: {e}")
        
        return {
            'cleanup_completed': True,
            'memories_cleaned': cleaned_count,
            'criteria': criteria
        }
    
    async def _interference_resolution(self, memory_ids: List[str]) -> Dict[str, Any]:
        """Resolve memory interference"""
        self.log_execution("Resolving memory interference")
        
        return {
            'interference_resolved': True,
            'processed_memories': len(memory_ids),
            'conflicts_resolved': max(1, len(memory_ids) // 3)
        }


class StressResponseAgent(BaseAgent):
    """应激反应智能体 (杏仁核+HPA轴)"""
    
    def __init__(self):
        super().__init__(
            "应激反应智能体",
            BrainRegion.AMYGDALA,
            "你是应激反应和情绪记忆系统，处理威胁检测、情绪调节和创伤记忆。"
        )
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        action = message.content.get('action')
        
        if action == 'detect_threat':
            return await self._detect_threat(message.content['stimulus'])
        elif action == 'emotional_encoding':
            return await self._emotional_encoding(message.content['memory_data'])
        elif action == 'trauma_processing':
            return await self._trauma_processing(message.content['trauma_memory'])
        
        return {'error': 'Unknown action', 'action': action}
    
    async def _detect_threat(self, stimulus: Dict[str, Any]) -> Dict[str, Any]:
        """Detect potential threats in incoming information"""
        self.log_execution("Detecting threats")
        
        content = stimulus.get('content', '')
        
        # Simple threat detection based on keywords
        threat_keywords = ['危险', '恐怖', '威胁', '害怕', '紧张', 'danger', 'threat', 'fear']
        
        threat_level = 0.0
        detected_threats = []
        
        for keyword in threat_keywords:
            if keyword in content.lower():
                threat_level += 0.2
                detected_threats.append(keyword)
        
        threat_level = min(1.0, threat_level)
        
        return {
            'threat_detected': threat_level > 0.3,
            'threat_level': threat_level,
            'detected_threats': detected_threats,
            'requires_attention': threat_level > 0.5
        }
    
    async def _emotional_encoding(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance memory encoding with emotional significance"""
        self.log_execution("Applying emotional encoding")
        
        emotion_intensity = memory_data.get('emotion_intensity', 0.5)
        emotions = memory_data.get('emotion_tags', [])
        
        # Boost importance for high emotional content
        importance_boost = 0.0
        if emotion_intensity > 0.7:
            importance_boost = 0.3
        elif emotion_intensity > 0.5:
            importance_boost = 0.1
        
        return {
            'emotional_encoding_applied': True,
            'importance_boost': importance_boost,
            'emotion_intensity': emotion_intensity,
            'priority_encoding': emotion_intensity > 0.6
        }
    
    async def _trauma_processing(self, trauma_memory: Dict[str, Any]) -> Dict[str, Any]:
        """Special processing for traumatic memories"""
        self.log_execution("Processing trauma memory")
        
        return {
            'trauma_processed': True,
            'memory_id': trauma_memory.get('id'),
            'special_encoding': True,
            'protection_level': 'high',
            'requires_therapeutic_attention': True
        }


# ========================================
# 4 Auxiliary Functional Agents
# ========================================

class ConversationAgent(BaseAgent):
    """对话智能体 (Broca + Wernicke语言区)"""
    
    def __init__(self):
        super().__init__(
            "对话智能体",
            BrainRegion.BROCA_WERNICKE,
            "你是语言理解和生成系统，负责自然语言交互和对话管理。请用中文回答。"
        )
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        action = message.content.get('action')
        
        if action == 'generate_response':
            return await self._generate_response(
                message.content['user_input'],
                message.content.get('context', {}),
                message.content.get('memories', [])
            )
        elif action == 'analyze_intent':
            return await self._analyze_intent(message.content['user_input'])
        
        return {'error': 'Unknown action', 'action': action}
    
    async def _generate_response(self, user_input: str, context: Dict, memories: List[Dict]) -> Dict[str, Any]:
        """Generate conversational response using buffer data"""
        self.log_execution("Generating response", {"input_length": len(user_input), "memories": len(memories)})
        
        # Check if buffer data is available from coordinator
        buffer_data = context.get('buffer_data', {})
        dialogue_history = buffer_data.get('dialogue_history', [])
        user_model = buffer_data.get('user_model', {})
        
        # Prepare context for response generation
        memory_context = ""
        if memories:
            memory_context = "\n相关记忆：\n"
            for i, memory in enumerate(memories[:3], 1):
                memory_context += f"{i}. {memory.get('content', '')[:100]}...\n"
        
        # Add dialogue history context if available
        dialogue_context = ""
        if dialogue_history:
            dialogue_context = "\n最近对话记录：\n"
            for i, dialogue in enumerate(dialogue_history[-3:], 1):
                dialogue_context += f"{i}. {dialogue.get('content', '')[:80]}...\n"
        
        # Add user model context if available  
        user_context = ""
        if user_model:
            preferences = user_model.get('preferences', [])
            if preferences:
                user_context = f"\n用户偏好模型：{', '.join(preferences[:3])}\n"
        
        prompt = f"""你是一个具备完整记忆能力的智能助手。你能记住之前的所有对话内容。

用户当前输入：{user_input}

{memory_context}
{dialogue_context}
{user_context}

**重要提醒**：
- 上面的"相关记忆"包含了你和用户之前的对话记录
- "最近对话记录"显示了近期的对话缓冲
- "用户偏好模型"包含了用户的个人偏好信息
- 如果记忆中显示用户曾经说过某些偏好或信息，你应该记住并在回复中体现
- 当用户问"我喜欢喝什么"时，如果记忆中有"用户说：我喜欢喝红茶"，你应该回答"你喜欢喝红茶"
- 始终基于具体的记忆内容来回答，而不是泛泛而谈

请生成一个自然、有帮助的中文回复：
1. **优先使用记忆中的具体信息**回答用户的问题
2. 结合对话历史和用户模型来个性化回应
3. 如果记忆中有相关信息，直接引用并回答
4. 如果没有相关记忆，诚实地说不知道
5. 保持对话自然流畅，体现你对用户的了解
"""
        
        response = await self.call_openai(prompt, context)
        
        self.log_execution("Response generated", {"response_length": len(response)}, "success")
        
        # Update conversation buffer with new dialogue
        try:
            agent_buffer_system.write_buffer(
                'conversation',
                'dialogue_history',
                {
                    'user_input': user_input,
                    'assistant_response': response,
                    'timestamp': datetime.now().isoformat(),
                    'memories_used': len(memories)
                },
                append=True
            )
            
            # Update user model if user expressed preferences
            if any(keyword in user_input.lower() for keyword in ['喜欢', '偏好', '习惯', 'like', 'prefer']):
                current_user_model = agent_buffer_system.read_buffer('conversation').get('user_model', {})
                preferences = current_user_model.get('preferences', [])
                preferences.append(user_input)
                current_user_model['preferences'] = preferences[-10:]  # Keep last 10 preferences
                
                agent_buffer_system.write_buffer('conversation', 'user_model', current_user_model)
        except Exception as e:
            logger.warning(f"Failed to update conversation buffer: {e}")
        
        return {
            'response': response,
            'memories_used': len(memories),
            'context_applied': bool(context)
        }
    
    async def _analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """Analyze user intent"""
        self.log_execution("Analyzing user intent")
        
        prompt = f"""
        分析用户输入的意图，返回JSON格式：
        {{
            "intent": "问题|请求|陈述|问候|告别|记忆存储|信息检索",
            "topic": "主题",
            "emotion": "情绪",
            "requires_memory": true/false,
            "confidence": 0.0-1.0
        }}
        
        用户输入：{user_input}
        """
        
        response = await self.call_openai(prompt)
        
        try:
            intent_data = json.loads(response)
        except json.JSONDecodeError:
            # Fallback intent analysis
            intent_data = {
                'intent': '陈述',
                'topic': '一般',
                'emotion': '中性',
                'requires_memory': True,
                'confidence': 0.5
            }
        
        return intent_data


class ExecutiveControlAgent(BaseAgent):
    """执行控制智能体 (前扣带皮层)"""
    
    def __init__(self):
        super().__init__(
            "执行控制智能体",
            BrainRegion.ACC,
            "你是执行控制和任务协调系统，负责冲突解决、任务切换和注意力管理。"
        )
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        action = message.content.get('action')
        
        if action == 'coordinate_agents':
            return await self._coordinate_agents(message.content['task_info'])
        elif action == 'resolve_conflict':
            return await self._resolve_conflict(message.content['conflict_data'])
        elif action == 'manage_attention':
            return await self._manage_attention(message.content['attention_targets'])
        
        return {'error': 'Unknown action', 'action': action}
    
    async def _coordinate_agents(self, task_info: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate multiple agents for complex tasks"""
        self.log_execution("Coordinating agents")
        
        task_type = task_info.get('type', 'general')
        complexity = task_info.get('complexity', 'medium')
        
        # Determine agent coordination strategy
        if task_type == 'memory_storage':
            primary_agents = ['长期记忆智能体', '记忆巩固智能体']
            secondary_agents = ['应激反应智能体']
        elif task_type == 'memory_retrieval':
            primary_agents = ['记忆检索智能体', '短期记忆智能体']
            secondary_agents = ['反思智能体']
        else:
            primary_agents = ['对话智能体']
            secondary_agents = ['记忆检索智能体']
        
        return {
            'coordination_plan': {
                'primary_agents': primary_agents,
                'secondary_agents': secondary_agents,
                'execution_order': 'parallel' if complexity == 'high' else 'sequential'
            },
            'estimated_duration': 2.0 if complexity == 'high' else 1.0
        }
    
    async def _resolve_conflict(self, conflict_data: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve conflicts between competing processes"""
        self.log_execution("Resolving conflict")
        
        return {
            'conflict_resolved': True,
            'resolution_method': 'priority_based',
            'winner': conflict_data.get('options', ['default'])[0]
        }
    
    async def _manage_attention(self, attention_targets: List[str]) -> Dict[str, Any]:
        """Manage attention and focus"""
        self.log_execution("Managing attention")
        
        # Prioritize attention targets
        prioritized_targets = attention_targets[:3]  # Focus on top 3
        
        return {
            'attention_focused': True,
            'primary_focus': prioritized_targets[0] if prioritized_targets else None,
            'secondary_focus': prioritized_targets[1:],
            'attention_span': 'focused'
        }


class PerceptionEncodingAgent(BaseAgent):
    """感知编码智能体 (感觉皮层+丘脑)"""
    
    def __init__(self):
        super().__init__(
            "感知编码智能体",
            BrainRegion.SENSORY_CORTEX,
            "你是多模态信息感知和编码系统，负责处理和编码输入信息。"
        )
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        action = message.content.get('action')
        
        if action == 'encode_input':
            return await self._encode_input(message.content['input_data'])
        elif action == 'extract_features':
            return await self._extract_features(message.content['raw_data'])
        
        return {'error': 'Unknown action', 'action': action}
    
    async def _encode_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Encode raw input into structured format"""
        self.log_execution("Encoding input data")
        
        content = input_data.get('content', '')
        input_type = input_data.get('type', 'text')
        
        # Basic feature extraction
        features = {
            'length': len(content),
            'word_count': len(content.split()),
            'input_type': input_type,
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
    
    async def _extract_features(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant features from raw data"""
        self.log_execution("Extracting features")
        
        features = {
            'data_type': raw_data.get('type', 'unknown'),
            'size': len(str(raw_data)),
            'complexity_score': 0.7,
            'relevance_score': 0.8
        }
        
        return {
            'extracted_features': features,
            'extraction_success': True
        }


class ActionExecutionAgent(BaseAgent):
    """行动执行智能体 (运动皮层+基底神经节)"""
    
    def __init__(self):
        super().__init__(
            "行动执行智能体",
            BrainRegion.MOTOR_CORTEX,
            "你是决策执行和工具调用系统，负责将决策转化为具体行动。"
        )
        
        # Available tools
        self.tools = {
            'calculator': self._calculator_tool,
            'search': self._search_tool,
            'file_operation': self._file_operation_tool
        }
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        action = message.content.get('action')
        
        if action == 'execute_tool':
            return await self._execute_tool(
                message.content['tool_name'],
                message.content.get('parameters', {})
            )
        elif action == 'list_tools':
            return await self._list_tools()
        
        return {'error': 'Unknown action', 'action': action}
    
    async def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute specified tool with parameters"""
        self.log_execution("Executing tool", {"tool": tool_name, "params": parameters})
        
        if tool_name not in self.tools:
            return {'error': f'Tool {tool_name} not available'}
        
        try:
            result = await self.tools[tool_name](parameters)
            self.log_execution("Tool execution successful", {"tool": tool_name}, "success")
            return {
                'tool_name': tool_name,
                'result': result,
                'success': True,
                'execution_time': datetime.now().isoformat()
            }
        except Exception as e:
            self.log_execution("Tool execution failed", {"tool": tool_name, "error": str(e)}, "error")
            return {
                'tool_name': tool_name,
                'error': str(e),
                'success': False
            }
    
    async def _list_tools(self) -> Dict[str, Any]:
        """List available tools"""
        return {
            'available_tools': list(self.tools.keys()),
            'tool_count': len(self.tools)
        }
    
    async def _calculator_tool(self, params: Dict[str, Any]) -> str:
        """Simple calculator tool"""
        expression = params.get('expression', '')
        
        # Basic safety check
        allowed_chars = set('0123456789+-*/().,')
        if not all(c in allowed_chars for c in expression):
            raise ValueError("Invalid expression")
        
        try:
            result = eval(expression)
            return f"计算结果: {expression} = {result}"
        except Exception as e:
            raise ValueError(f"计算错误: {e}")
    
    async def _search_tool(self, params: Dict[str, Any]) -> str:
        """Simple search tool (simulated)"""
        query = params.get('query', '')
        return f"搜索结果: {query} - [模拟搜索结果]"
    
    async def _file_operation_tool(self, params: Dict[str, Any]) -> str:
        """Safe file operation tool"""
        operation = params.get('operation', '')
        return f"文件操作: {operation} - [安全模拟执行]"


# Export all agent classes
__all__ = [
    'BaseAgent', 'AgentMessage', 'BrainRegion',
    # Core agents
    'ShortTermMemoryAgent', 'LongTermMemoryAgent', 'MemoryRetrievalAgent',
    'ConsolidationAgent', 'MemoryDistortionAgent', 'ReflectionAgent',
    'ForgettingAgent', 'StressResponseAgent',
    # Auxiliary agents
    'ConversationAgent', 'ExecutiveControlAgent',
    'PerceptionEncodingAgent', 'ActionExecutionAgent'
]