"""
Brain-Inspired 12-Agent Coordinator System
12智能体协调器：实现真正的并行处理和智能体通信
"""

import os
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json

from ..utils.config import get_logger

from .clean_agent_system import (
    BrainRegion, AgentMessage,
    # Core agents - directly imported
    ShortTermMemoryAgent, LongTermMemoryAgent, MemoryRetrievalAgent,
    ConsolidationAgent, MemoryDistortionAgent, ReflectionAgent,
    ForgettingAgent, StressResponseAgent, PersonalityAgent,
    # Auxiliary agents - clean implementation
    ConversationAgent, ExecutiveControlAgent,
    PerceptionEncodingAgent, ActionExecutionAgent
)
from ..memory.memory_system import memory_system
from ..agents.agent_buffer_system import agent_buffer_system
from ..brain.neural_plasticity import NeuralPlasticityEngine

# Configure logging
logger = get_logger(__name__)


@dataclass
class ProcessingResult:
    """Result from brain-inspired processing"""
    response: str
    routing_decision: Dict[str, Any]
    agents_involved: List[str]
    memories_retrieved: List[Dict[str, Any]]
    memory_stored: bool
    processing_time: float
    agent_logs: Dict[str, List[Dict]]
    insights: Dict[str, Any]
    success: bool
    error: Optional[str] = None


class BrainInspiredCoordinator:
    """
    12-Agent Brain-Inspired Coordinator System
    Implements the design from 设计思路.md with proper agent communication
    """
    
    def __init__(self):
        logger.info("Initializing Brain-Inspired 12-Agent Coordinator...")
        
        # Communication system
        self.message_bus = asyncio.Queue()
        self.agent_tasks = {}
        self.is_running = False
        
        # Processing statistics (initialize before agents)
        self.processing_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'agent_activations': {},
            'memory_operations': 0
        }
        
        # Initialize all 12 agents
        self._initialize_agents()
        
        # Initialize Neural Plasticity Engine
        agent_names = list(self.agents.keys())
        self.plasticity_engine = NeuralPlasticityEngine(agent_names)
        
        logger.info(f"Successfully initialized 12-agent system with {len(self.agents)} agents")
        logger.info("Neural Plasticity Engine integrated - system now has adaptive learning!")
    
    def _initialize_agents(self):
        """Initialize all 12 agents according to design document"""
        
        # Get memory system services
        from src.memory.memory_system import memory_system
        db = memory_system.db_manager
        vec = memory_system.vector_db
        emb = memory_system.embedding_service
        
        # 8 Core Memory Processing Agents
        self.short_term_memory = ShortTermMemoryAgent()
        self.long_term_memory = LongTermMemoryAgent(db_manager=db, embedding_service=emb, vector_db=vec)
        self.memory_retrieval = MemoryRetrievalAgent(db_manager=db, embedding_service=emb, vector_db=vec)
        self.consolidation = ConsolidationAgent(db_manager=db)
        self.memory_distortion = MemoryDistortionAgent(db_manager=db)
        self.reflection = ReflectionAgent(db_manager=db, embedding_service=emb)
        self.forgetting = ForgettingAgent(db_manager=db)
        self.stress_response = StressResponseAgent(db_manager=db)
        
        # 4 Auxiliary Functional Agents  
        self.personality = PersonalityAgent()  # 人格智能体 - 摇光明明
        self.conversation = ConversationAgent()
        self.executive_control = ExecutiveControlAgent()
        self.perception_encoding = PerceptionEncodingAgent()
        self.action_execution = ActionExecutionAgent()
        
        # Agent registry
        self.agents = {
            # Core agents
            'short_term_memory': self.short_term_memory,
            'long_term_memory': self.long_term_memory,
            'memory_retrieval': self.memory_retrieval,
            'consolidation': self.consolidation,
            'memory_distortion': self.memory_distortion,
            'reflection': self.reflection,
            'forgetting': self.forgetting,
            'stress_response': self.stress_response,
            
            # Auxiliary agents
            'personality': self.personality,  # 人格智能体 - 摇光明明  
            'conversation': self.conversation,
            'executive_control': self.executive_control,
            'perception_encoding': self.perception_encoding,
            'action_execution': self.action_execution
        }
        
        # Initialize agent statistics
        for agent_id in self.agents:
            self.processing_stats['agent_activations'][agent_id] = 0
    
    async def start_system(self):
        """Start the coordination system"""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("Brain-Inspired Coordinator System started")
        
        # Start message processing loop
        asyncio.create_task(self._process_message_bus())
    
    async def stop_system(self):
        """Stop the coordination system"""
        self.is_running = False
        
        # Cancel all agent tasks
        for task in self.agent_tasks.values():
            if not task.done():
                task.cancel()
        
        if self.agent_tasks:
            await asyncio.gather(*self.agent_tasks.values(), return_exceptions=True)
        
        self.agent_tasks.clear()
        
        # Stop plasticity engine and save data
        await self.plasticity_engine.stop_plasticity_engine()
        
        logger.info("Brain-Inspired Coordinator System stopped with plasticity data saved")
    
    async def process_user_input(self, user_input: str, context: Dict[str, Any] = None) -> ProcessingResult:
        """
        Main processing pipeline following brain-inspired design
        实现类脑信息处理流程
        """
        start_time = datetime.now()
        
        try:
            self.processing_stats['total_requests'] += 1
            
            if not self.is_running:
                await self.start_system()
            
            logger.info(f"Processing user input: {user_input[:50]}...")
            
            # Phase 1: Perception Encoding (感知编码)
            perception_result = await self._activate_agent(
                'perception_encoding',
                AgentMessage(
                    sender='coordinator',
                    receiver='perception_encoding',
                    message_type='request',
                    content={
                        'action': 'encode_input',
                        'input_data': {
                            'content': user_input,
                            'type': 'text',
                            'context': context or {}
                        }
                    }
                )
            )
            
            encoded_input = perception_result.get('encoded_input', {})
            
            # Phase 2: Executive Control - Task Routing with Plasticity (执行控制 - 任务路由)
            task_type = self._classify_task_type(user_input)
            
            # Get optimal agent sequence from plasticity engine
            optimal_agents = self.plasticity_engine.optimize_routing_strategy(task_type)
            
            routing_result = await self._activate_agent(
                'executive_control',
                AgentMessage(
                    sender='coordinator',
                    receiver='executive_control',
                    message_type='request',
                    content={
                        'action': 'coordinate_agents',
                        'task_info': {
                            'user_input': user_input,
                            'type': task_type,
                            'complexity': encoded_input.get('features', {}).get('complexity', 'medium'),
                            'context': context or {},
                            'optimal_sequence': optimal_agents[:3]  # Top 3 from plasticity
                        }
                    }
                )
            )
            
            coordination_plan = routing_result.get('coordination_plan', {})
            # Use plasticity-optimized agents if executive control doesn't override
            primary_agents = coordination_plan.get('primary_agents', optimal_agents[:2])
            secondary_agents = coordination_plan.get('secondary_agents', optimal_agents[2:4])
            
            # Phase 3: Parallel Agent Activation (并行智能体激活)
            parallel_tasks = {}
            activated_agents = ['memory_retrieval', 'stress_response']
            
            # Always retrieve memories first
            parallel_tasks['memory_retrieval'] = self._activate_agent(
                'memory_retrieval',
                AgentMessage(
                    sender='coordinator',
                    receiver='memory_retrieval',
                    message_type='request',
                    content={
                        'action': 'semantic_search',
                        'query': user_input,
                        'k': 10
                    }
                )
            )
            
            # Stress/Threat Detection
            parallel_tasks['stress_response'] = self._activate_agent(
                'stress_response',
                AgentMessage(
                    sender='coordinator',
                    receiver='stress_response',
                    message_type='request',
                    content={
                        'action': 'threat_detection',
                        'stimulus': {'content': user_input}
                    }
                )
            )
            
            # Activate primary agents based on routing
            for agent_name in primary_agents:
                agent_id = self._map_agent_name(agent_name)
                if agent_id and agent_id in self.agents:
                    parallel_tasks[agent_id] = self._create_primary_agent_task(agent_id, user_input, context)
                    activated_agents.append(agent_id)
            
            # Wait for parallel phase completion - TRUE PARALLEL EXECUTION
            parallel_results = {}
            successful_agents = []
            activation_strengths = []
            
            # Execute all tasks concurrently
            task_names = list(parallel_tasks.keys())
            task_coros = list(parallel_tasks.values())
            
            # Add timeout protection for parallel phase
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*task_coros, return_exceptions=True),
                    timeout=8.0  # 8 seconds max for parallel phase
                )
            except asyncio.TimeoutError:
                logger.warning("并行阶段超时，使用部分结果继续")
                results = [Exception("Parallel phase timeout") for _ in task_coros]
            
            # Process results
            for task_name, result in zip(task_names, results):
                if isinstance(result, Exception):
                    # 检查是否是连接错误
                    error_str = str(result).lower()
                    if any(keyword in error_str for keyword in ['tcptransport', 'connection error', 'connection pool', 'closed=true']):
                        logger.warning(f"智能体 {task_name} 执行失败: {result}")
                    parallel_results[task_name] = {'error': str(result)}
                else:
                    parallel_results[task_name] = result
                    if not result.get('error') and task_name in self.agents:
                        successful_agents.append(task_name)
                        activation_strengths.append(1.0)  # Full activation strength for successful agents
            
            # Record agent activations for plasticity learning
            if len(successful_agents) >= 2:
                await self.plasticity_engine.start_plasticity_engine()
                self.plasticity_engine.record_agent_activation(
                    successful_agents,
                    activation_strengths,
                    context={
                        'user_input': user_input,
                        'task_type': self._classify_task_type(user_input),
                        'timestamp': datetime.now().isoformat()
                    }
                )
            
            # Extract retrieved memories
            memories = parallel_results.get('memory_retrieval', {}).get('memories', [])
            threat_info = parallel_results.get('stress_response', {})
            
            # Initialize memory tracking variables
            memory_ids = []
            memory_strengths = []
            
            # Record memory co-activation for plasticity learning
            if memories:
                memory_ids = [mem.get('id', f"memory_{i}") for i, mem in enumerate(memories)]
                memory_strengths = [mem.get('similarity_score', 0.5) for mem in memories]
                
                self.plasticity_engine.record_memory_co_activation(
                    memory_ids,
                    memory_strengths,
                    context={
                        'query': user_input,
                        'retrieval_context': 'user_query',
                        'timestamp': datetime.now().isoformat()
                    }
                )
            
            # Phase 4: Working Memory Processing (工作记忆处理)
            if memories:
                # Exchange retrieved memories with short-term memory (with timeout protection)
                try:
                    await asyncio.wait_for(
                        agent_buffer_system.exchange_buffers(
                            'memory_retrieval',
                            'short_term_memory',
                            'retrieved_memories',
                            {
                                'memories': memories,
                                'query': user_input,
                                'count': len(memories)
                            }
                        ),
                        timeout=5.0  # 5 seconds max for buffer exchange
                    )
                except asyncio.TimeoutError:
                    logger.warning("缓冲区交换超时，跳过此步骤继续")
                
                await self._activate_agent(
                    'short_term_memory',
                    AgentMessage(
                        sender='coordinator',
                        receiver='short_term_memory',
                        message_type='request',
                        content={
                            'action': 'store_short_term',
                            'item': {
                                'content': f"Retrieved {len(memories)} relevant memories for: {user_input}",
                                'type': 'memory_context'
                            }
                        }
                    )
                )
            
            # Phase 5: Response Generation with Plasticity Insights (响应生成)
            # Get suggested memories from plasticity engine
            plasticity_memories = []
            if memories:
                memory_ids = [mem.get('id', f"memory_{i}") for i, mem in enumerate(memories)]
                associated_memories = self.plasticity_engine.get_associated_memories(
                    memory_ids[:3],  # Top 3 memories for association
                    association_threshold=0.2,
                    max_associations=5
                )
                plasticity_memories = [{'id': mem_id, 'plasticity_strength': strength} 
                                     for mem_id, strength in associated_memories]
            
            response_result = await self._activate_agent(
                'conversation',
                AgentMessage(
                    sender='coordinator',
                    receiver='conversation',
                    message_type='request',
                    content={
                        'action': 'generate_response',
                        'user_input': user_input,
                        'context': context or {},
                        'memories': memories[:5],  # Top 5 most relevant
                        'plasticity_memories': plasticity_memories,
                        'threat_info': threat_info,
                        'primary_results': {k: v for k, v in parallel_results.items() if k not in ['memory_retrieval', 'stress_response']}
                    }
                )
            )
            
            main_response = response_result.get('response', '抱歉，我现在无法处理您的请求。')
            
            # Phase 5.5: User Preference Processing (用户偏好处理) - Background
            preference_processed = False
            if self._contains_user_preference(user_input):
                # Store user preference asynchronously to avoid blocking main response
                async def store_preference_background():
                    try:
                        preference_result = await self._activate_agent(
                            'long_term_memory',
                            AgentMessage(
                                sender='coordinator',
                                receiver='long_term_memory',
                                message_type='request',
                                content={
                                    'action': 'store_long_term',
                                    'memory': {
                                        'content': f"用户偏好：{user_input}",
                                        'importance': 0.9,  # 偏好具有高重要性
                                        'context_tags': ['用户偏好', 'preference', 'personal_info'],
                                        'emotion_tags': ['positive', 'preference']
                                    }
                                }
                            )
                        )
                        if preference_result.get('success', False):
                            logger.info(f"后台存储用户偏好完成: {user_input[:50]}")
                            # Exchange buffer info between long_term_memory and consolidation
                            await agent_buffer_system.exchange_buffers(
                                'long_term_memory',
                                'consolidation', 
                                'user_preference',
                                {'preference': user_input, 'timestamp': datetime.now().isoformat()}
                            )
                    except Exception as e:
                        logger.error(f"后台存储用户偏好失败: {e}")
                
                # Create background task for preference storage
                asyncio.create_task(store_preference_background())
                preference_processed = True  # Always true since we're storing in background
            
            # 触发记忆巩固
            if preference_processed:
                await self._activate_agent(
                    'consolidation',
                    AgentMessage(
                        sender='coordinator',
                        receiver='consolidation',
                        message_type='request',
                        content={
                            'action': 'consolidate_preference',
                            'memory_id': None,  # Will be handled in background
                            'importance_boost': 0.2
                        }
                    )
                )
            
            # Phase 6: Memory Storage (记忆存储)
            memory_stored = False
            if self._should_store_memory(user_input, context):
                # Determine memory properties
                importance = self._calculate_importance(user_input, threat_info, memories)
                emotion_tags = self._extract_emotions(user_input, threat_info)
                
                # Apply emotional encoding if needed
                if threat_info.get('threat_score', 0) > 0.3:
                    emotional_encoding = await self._activate_agent(
                        'stress_response',
                        AgentMessage(
                            sender='coordinator',
                            receiver='stress_response',
                            message_type='request',
                            content={
                                'action': 'emotional_encoding',
                                'memory_data': {
                                    'content': user_input,
                                    'importance': importance,
                                    'emotion_tags': emotion_tags,
                                    'emotion_intensity': threat_info.get('threat_score', 0.5)
                                }
                            }
                        )
                    )
                    importance += emotional_encoding.get('importance_boost', 0.0)
                
                # Store complete conversation memory (not just user input)
                conversation_content = f"用户说：{user_input}\n助手回复：{main_response}"
                
                # Store memory asynchronously in background to avoid blocking main response
                async def store_memory_background():
                    try:
                        memory_id = await memory_system.store_memory(
                            content=conversation_content,
                            importance=min(1.0, importance),
                            emotion_tags=emotion_tags,
                            context_tags=[self._classify_task_type(user_input), "完整对话"],
                            metadata={
                                'source': 'conversation',
                                'user_input': user_input,
                                'assistant_response': main_response,
                                'memories_used': len(memories),
                                'threat_level': threat_info.get('threat_level', 'unknown'),
                                'threat_score': threat_info.get('threat_score', 0.0),
                                'processing_timestamp': datetime.now().isoformat()
                            }
                        )
                        if memory_id:
                            self.processing_stats['memory_operations'] += 1
                            logger.info(f"后台存储记忆完成: {memory_id}")
                            
                            # Record new memory activation with retrieved memories
                            if memory_ids:
                                all_memory_ids = memory_ids + [memory_id]
                                all_strengths = memory_strengths + [importance]
                                
                                self.plasticity_engine.record_memory_co_activation(
                                    all_memory_ids,
                                    all_strengths,
                                    context={
                                        'event': 'new_memory_storage',
                                        'conversation_context': True,
                                        'timestamp': datetime.now().isoformat()
                                    }
                                )
                    except Exception as e:
                        logger.error(f"后台存储记忆失败: {e}")
                
                # Create background task for memory storage
                asyncio.create_task(store_memory_background())
                memory_stored = True  # Always true since we're storing in background
                
                # Record existing memory activation (new memory will be recorded in background)
                if memory_ids:
                    self.plasticity_engine.record_memory_co_activation(
                        memory_ids,
                        memory_strengths,
                        context={
                            'event': 'memory_retrieval',
                            'conversation_context': True,
                            'timestamp': datetime.now().isoformat()
                        }
                    )
            
            # Phase 7: Background Processing (后台处理)
            background_tasks = []
            
            # Reflection and insights
            if len(memories) > 3:
                background_tasks.append(
                    asyncio.create_task(self._trigger_background_reflection(memories))
                )
            
            # Memory consolidation
            if memory_stored and importance > 0.7:
                background_tasks.append(
                    asyncio.create_task(self._trigger_background_consolidation())
                )
            
            # Forgetting (higher frequency for buffer maintenance)
            if self.processing_stats['total_requests'] % 5 == 0:
                background_tasks.append(
                    asyncio.create_task(self._trigger_background_forgetting())
                )
            
            # Background tasks run independently - don't wait for them to avoid blocking
            insights = {'status': 'background_processing', 'tasks_started': len(background_tasks)}
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Collect agent logs
            agent_logs = {}
            for agent_id, agent in self.agents.items():
                if agent.execution_log:
                    agent_logs[agent_id] = agent.execution_log[-5:]  # Last 5 entries
            
            # Success
            self.processing_stats['successful_requests'] += 1
            
            result = ProcessingResult(
                response=main_response,
                routing_decision=coordination_plan,
                agents_involved=list(parallel_results.keys()),
                memories_retrieved=memories,
                memory_stored=memory_stored,
                processing_time=processing_time,
                agent_logs=agent_logs,
                insights=insights,
                success=True
            )
            
            logger.info(f"Successfully processed request in {processing_time:.2f}s with {len(memories)} memories")
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self.processing_stats['failed_requests'] += 1
            
            # 检查是否是连接错误，如果是则重置OpenAI客户端
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ['tcptransport', 'connection error', 'connection pool', 'closed=true']):
                logger.warning(f"检测到连接错误: {e}")
                # 连接错误处理已统一到BrainAgent.call_llm中，避免竞态条件
            
            logger.error(f"Error processing user input: {e}")
            
            return ProcessingResult(
                response=f"系统处理错误：{str(e)}",
                routing_decision={},
                agents_involved=[],
                memories_retrieved=[],
                memory_stored=False,
                processing_time=processing_time,
                agent_logs={},
                insights={},
                success=False,
                error=str(e)
            )
    
    async def _activate_agent(self, agent_id: str, message: AgentMessage) -> Dict[str, Any]:
        """Activate specific agent with message and use buffer system"""
        if agent_id not in self.agents:
            return {'error': f'Agent {agent_id} not found'}
        
        try:
            agent = self.agents[agent_id]
            self.processing_stats['agent_activations'][agent_id] += 1
            
            # Read agent's current buffer state
            try:
                buffer_content = await agent_buffer_system.read_buffer(agent_id)
                # Add ONLY essential buffer data to avoid infinite nesting
                if hasattr(message, 'content') and isinstance(message.content, dict):
                    # Only pass essential data, not the entire buffer including recent_inputs
                    essential_data = {}
                    for key, value in buffer_content.items():
                        if key not in ['recent_inputs', 'recent_exchanges', 'recent_outputs']:
                            essential_data[key] = value
                    message.content['buffer_data'] = essential_data
            except Exception as buffer_e:
                logger.warning(f"Failed to read buffer for {agent_id}: {buffer_e}")
            
            # Process the message
            result = await agent.process_message(message)
            
            # Update agent buffer with processing results
            try:
                # Sanitize function for JSON serialization
                def sanitize_for_json(obj):
                    if isinstance(obj, dict):
                        return {k: sanitize_for_json(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [sanitize_for_json(item) for item in obj]
                    elif hasattr(obj, '__dict__'):
                        return str(obj)  # Convert objects to string representation
                    elif isinstance(obj, (str, int, float, bool)) or obj is None:
                        return obj
                    else:
                        return str(obj)  # Convert everything else to string
                
                # Store ONLY the original message content, not the enriched version
                original_content = {k: v for k, v in message.content.items() if k != 'buffer_data'}
                await agent_buffer_system.write_buffer(
                    agent_id, 
                    'recent_inputs', 
                    {
                        'message': sanitize_for_json(original_content),
                        'timestamp': datetime.now().isoformat(),
                        'sender': message.sender
                    },
                    append=True
                )
                
                # Store processing results if available - sanitize for JSON
                if result and not result.get('error'):
                    await agent_buffer_system.write_buffer(
                        agent_id,
                        'recent_outputs',
                        {
                            'result': sanitize_for_json(result),
                            'timestamp': datetime.now().isoformat(),
                            'processing_success': True
                        },
                        append=True
                    )
            except Exception as buffer_e:
                logger.warning(f"Failed to write buffer for {agent_id}: {buffer_e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error activating agent {agent_id}: {e}")
            return {'error': str(e)}
    
    def _map_agent_name(self, agent_name: str) -> Optional[str]:
        """Map Chinese agent names to agent IDs"""
        name_mapping = {
            '记忆存储智能体': 'long_term_memory',
            '记忆检索智能体': 'memory_retrieval',
            '对话智能体': 'conversation',
            '反思智能体': 'reflection',
            '规划智能体': 'action_execution',
            '工具调用智能体': 'action_execution',
            '记忆巩固智能体': 'consolidation',
            '遗忘智能体': 'forgetting'
        }
        return name_mapping.get(agent_name, agent_name.lower().replace(' ', '_'))
    
    def _classify_task_type(self, user_input: str) -> str:
        """Classify task type for routing decisions"""
        user_lower = user_input.lower()
        
        if any(keyword in user_lower for keyword in ['记住', '保存', 'remember', 'save']):
            return 'memory_storage'
        elif any(keyword in user_lower for keyword in ['搜索', '查找', 'search', 'find']):
            return 'memory_retrieval'
        elif any(keyword in user_lower for keyword in ['计算', '计划', 'calculate', 'plan']):
            return 'tool_execution'
        elif any(keyword in user_lower for keyword in ['分析', '思考', 'analyze', 'think']):
            return 'reflection'
        else:
            return 'conversation'
    
    def _contains_user_preference(self, user_input: str) -> bool:
        """检测用户输入是否包含偏好表达"""
        preference_indicators = [
            '我喜欢', '我不喜欢', '我爱', '我讨厌', '我觉得',
            '我认为', '我希望', '我想要', '我需要', '我偏好',
            '我的兴趣', '我的爱好', '我习惯', '我经常', '我通常',
            '我最爱', '我最喜欢', '我很喜欢', '我特别喜欢'
        ]
        
        return any(indicator in user_input for indicator in preference_indicators)
    
    async def _create_primary_agent_task(self, agent_id: str, user_input: str, context: Dict) -> Dict[str, Any]:
        """Create appropriate task for primary agent"""
        if agent_id == 'long_term_memory':
            return await self._activate_agent(
                agent_id,
                AgentMessage(
                    sender='coordinator',
                    receiver=agent_id,
                    message_type='request',
                    content={
                        'action': 'store_long_term',
                        'memory': {
                            'content': user_input,
                            'importance': 0.7,
                            'emotion_tags': ['neutral'],
                            'context_tags': ['user_input']
                        }
                    }
                )
            )
        elif agent_id == 'action_execution':
            # Check if it's a calculation request
            if '计算' in user_input or 'calculate' in user_input.lower():
                # Extract expression
                import re
                expr_match = re.search(r'[\d\+\-\*/\(\)\s\.]+', user_input)
                expression = expr_match.group(0) if expr_match else user_input
                
                return await self._activate_agent(
                    agent_id,
                    AgentMessage(
                        sender='coordinator',
                        receiver=agent_id,
                        message_type='request',
                        content={
                            'action': 'execute_tool',
                            'tool_name': 'calculator',
                            'parameters': {'expression': expression.strip()}
                        }
                    )
                )
        
        # Default: return empty result
        return {'default_activation': True}
    
    def _should_store_memory(self, user_input: str, context: Dict) -> bool:
        """Determine if input should be stored as memory"""
        # Don't store very short inputs
        if len(user_input.strip()) < 5:
            return False
        
        # 放宽过滤条件：只过滤纯粹的单词问候语
        simple_greetings = ['hi', 'hello', 'bye', '谢谢', '再见']
        if user_input.lower().strip() in simple_greetings:
            return False
        
        # 包含"记住"、"记录"等关键词的一定要存储
        memory_keywords = ['记住', '记录', '保存', '记下', 'remember', 'save', 'store']
        if any(keyword in user_input.lower() for keyword in memory_keywords):
            return True
        
        return True
    
    def _calculate_importance(self, user_input: str, threat_info: Dict, memories: List) -> float:
        """Calculate memory importance score"""
        importance = 0.5  # Base importance
        
        # Boost for emotional content
        if threat_info.get('threat_score', 0) > 0.3:
            importance += 0.2
        
        # Boost for length and complexity
        if len(user_input) > 100:
            importance += 0.1
        
        # Boost if related to existing memories
        if len(memories) > 0:
            avg_similarity = sum(mem.get('similarity_score', 0) for mem in memories) / len(memories)
            if avg_similarity > 0.7:
                importance += 0.1
        
        return min(1.0, importance)
    
    def _extract_emotions(self, user_input: str, threat_info: Dict) -> List[str]:
        """Extract emotion tags from input"""
        emotions = []
        
        # Check threat level
        if threat_info.get('threat_score', 0) > 0.5:
            emotions.append('anxious')
        elif threat_info.get('threat_score', 0) > 0.3:
            emotions.append('concerned')
        
        # Simple emotion detection
        positive_words = ['开心', '喜欢', '爱', '高兴', '兴奋', 'happy', 'love', 'like', 'excited']
        negative_words = ['难过', '担心', '害怕', '愤怒', 'sad', 'worried', 'afraid', 'angry']
        
        user_lower = user_input.lower()
        
        if any(word in user_lower for word in positive_words):
            emotions.append('positive')
        if any(word in user_lower for word in negative_words):
            emotions.append('negative')
        
        return emotions if emotions else ['neutral']
    
    async def _trigger_background_reflection(self, memories: List[Dict]) -> Dict[str, Any]:
        """Trigger reflection process in background"""
        try:
            return await self._activate_agent(
                'reflection',
                AgentMessage(
                    sender='coordinator',
                    receiver='reflection',
                    message_type='request',
                    content={
                        'action': 'generate_insights',
                        'memories': memories
                    }
                )
            )
        except Exception as e:
            return {'background_reflection_error': str(e)}
    
    async def _trigger_background_consolidation(self):
        """Trigger consolidation process in background"""
        try:
            await self._activate_agent(
                'consolidation',
                AgentMessage(
                    sender='coordinator',
                    receiver='consolidation',
                    message_type='request',
                    content={'action': 'system_consolidation'}
                )
            )
        except Exception as e:
            logger.error(f"Background consolidation error: {e}")
    
    async def _trigger_background_forgetting(self):
        """Trigger forgetting process in background"""
        try:
            # 轮流执行不同的遗忘任务
            request_count = self.processing_stats['total_requests']
            
            if request_count % 10 == 0:
                # 每10次请求执行一次选择性遗忘
                action = 'selective_forgetting'
                content = {
                    'action': action,
                    'criteria': {
                        'max_age_days': 7,
                        'max_importance': 0.2,
                        'max_access_frequency': 3,
                        'age_weight': 0.5,
                        'importance_weight': 0.4,
                        'access_weight': 0.2,
                        'importance_reduction': 0.4,
                        'decay_increase': 0.25
                    }
                }
            else:
                # 其他时候应用被动遗忘曲线
                action = 'passive_decay'
                content = {'action': action}
            
            await self._activate_agent(
                'forgetting',
                AgentMessage(
                    sender='coordinator',
                    receiver='forgetting',
                    message_type='request',
                    content=content
                )
            )
        except Exception as e:
            logger.error(f"Background forgetting error: {e}")
    
    async def _process_message_bus(self):
        """Process inter-agent messages"""
        while self.is_running:
            try:
                message = await asyncio.wait_for(self.message_bus.get(), timeout=1.0)
                # Process message routing between agents
                # For now, this is handled directly by the coordinator
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Message bus error: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status including plasticity insights"""
        # Get plasticity insights
        plasticity_insights = self.plasticity_engine.get_plasticity_insights()
        
        return {
            'system': {
                'is_running': self.is_running,
                'total_agents': len(self.agents),
                'active_tasks': len(self.agent_tasks)
            },
            'processing_stats': self.processing_stats,
            'memory_system': memory_system.get_system_stats(),
            'plasticity_system': plasticity_insights,
            'agent_status': {
                agent_id: {
                    'is_active': agent.is_active,
                    'activation_level': getattr(agent, 'activation_level', 0.5),
                    'fatigue_level': getattr(agent, 'fatigue_level', 0.0),
                    'recent_logs': len(agent.execution_log)
                }
                for agent_id, agent in self.agents.items()
            }
        }


# Global coordinator instance removed - to avoid duplicate initialization


async def main():
    """Test the coordinator system"""
    print("Testing Brain-Inspired Coordinator System...")
    
    # 创建协调器实例
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()
    
    # Test cases
    test_inputs = [
        "你好，我想了解这个系统",
        "请记住我喜欢喝咖啡和读书",
        "计算 25 * 4 + 10",
        "我今天感到有些焦虑，工作压力很大",
        "你能帮我分析一下我的记忆模式吗？"
    ]
    
    for i, test_input in enumerate(test_inputs, 1):
        print(f"\n{'='*50}")
        print(f"Test {i}: {test_input}")
        print(f"{'='*50}")
        
        result = await coordinator.process_user_input(test_input)
        
        print(f"Success: {result.success}")
        print(f"Response: {result.response}")
        print(f"Processing time: {result.processing_time:.2f}s")
        print(f"Agents involved: {result.agents_involved}")
        print(f"Memories found: {len(result.memories_retrieved)}")
        print(f"Memory stored: {result.memory_stored}")
        
        if result.insights:
            print(f"Insights: {json.dumps(result.insights, ensure_ascii=False, indent=2)}")
    
    # System status
    print(f"\n{'='*50}")
    print("System Status:")
    print(f"{'='*50}")
    status = coordinator.get_system_status()
    print(json.dumps(status, ensure_ascii=False, indent=2, default=str))
    
    await coordinator.stop_system()


if __name__ == "__main__":
    asyncio.run(main())
