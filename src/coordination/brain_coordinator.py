"""
Brain-Inspired 12-Agent Coordinator System
12智能体协调器：实现真正的并行处理和智能体通信
"""

import os
import asyncio
from typing import Dict, List, Any, Optional, Coroutine
from dataclasses import dataclass
from datetime import datetime
import json

from ..utils.config import get_logger, get_settings

from .clean_agent_system import (
    BrainRegion, AgentMessage,
    # Core agents - directly imported
    ShortTermMemoryAgent, LongTermMemoryAgent, MemoryRetrievalAgent,
    ConsolidationAgent, MemoryDistortionAgent, ReflectionAgent,
    ForgettingAgent, StressResponseAgent, PersonalityAgent, PersonaMemoryAgent,
    # Auxiliary agents - clean implementation
    ConversationAgent, ExecutiveControlAgent,
    PerceptionEncodingAgent, ActionExecutionAgent
)
from ..agents.core.reasoning_validator import ReasoningValidatorAgent
from ..memory.memory_system import memory_system
from ..agents.agent_buffer_system import agent_buffer_system
from ..brain.neural_plasticity import NeuralPlasticityEngine

# Configure logging
logger = get_logger(__name__)


class _LegacyMemoryManagerAdapter:
    """Compatibility layer exposing legacy memory_manager interface."""

    def __init__(self, coordinator: "BrainInspiredCoordinator", memory_system_ref):
        self._coordinator = coordinator
        self._memory_system = memory_system_ref

    async def retrieve_memories(self, query: str, k: int = 5, **kwargs):
        return await self._memory_system.search_memories(query, k=k, **kwargs)

    async def store_memory(self, content: str, metadata: Optional[Dict[str, Any]] = None, **kwargs):
        return await self._memory_system.store_memory(
            content,
            metadata=metadata or {},
            **kwargs
        )

    async def consolidate_memories(self):
        return await self._coordinator._activate_agent(
            'consolidation',
            AgentMessage(
                sender='evaluation_adapter',
                receiver='consolidation',
                message_type='request',
                content={'action': 'system_consolidation'}
            )
        )


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
        self._task_counter = 0
        self.is_running = False
        
        # Processing statistics (initialize before agents)
        self.processing_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'agent_activations': {},
            'memory_operations': 0
        }

        self.settings = get_settings()

        # Core memory system reference for legacy integrations
        self.memory_system = memory_system
        self.memory_manager = _LegacyMemoryManagerAdapter(self, memory_system)

        # Initialize all 12 agents
        self._initialize_agents()
        
        # Initialize Neural Plasticity Engine
        agent_names = list(self.agents.keys())
        self.plasticity_engine = NeuralPlasticityEngine(agent_names)
        
        logger.info(f"Successfully initialized 12-agent system with {len(self.agents)} agents")
        logger.info("Neural Plasticity Engine integrated - system now has adaptive learning!")

    async def initialize(self):
        """Public initializer kept for backwards compatibility (see main())."""
        if not self.is_running:
            await self.start_system()
        return self

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

        # Reasoning & Validation Agent
        self.reasoning_validator = ReasoningValidatorAgent(
            reflection_agent=self.reflection,
            consolidation_agent=self.consolidation
        )

        # 4 Auxiliary Functional Agents
        self.persona_memory = PersonaMemoryAgent(db_manager=db, embedding_service=emb, vector_db=vec)
        self.personality = PersonalityAgent(persona_memory_agent=self.persona_memory)  # 人格智能体 - 摇光明明
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
            'reasoning_validator': self.reasoning_validator,

            # Auxiliary agents
            'persona_memory': self.persona_memory,
            'personality': self.personality,  # 人格智能体 - 摇光明明
            'conversation': self.conversation,
            'executive_control': self.executive_control,
            'perception_encoding': self.perception_encoding,
            'action_execution': self.action_execution
        }
        
        # Initialize agent statistics
        for agent_id in self.agents:
            self.processing_stats['agent_activations'][agent_id] = 0

        # 🧠 BrainNetwork initialization
        import os
        self.use_brain_network = os.getenv('USE_BRAIN_NETWORK', 'true').lower() == 'true'

        if self.use_brain_network:
            from src.brain.brain_network import BrainNetwork
            self.brain_network = BrainNetwork(agents=self.agents)
            logger.info("🧠 BrainNetwork initialized (graph topology mode enabled)")
        else:
            self.brain_network = None
            logger.info("⚙️ BrainNetwork disabled (using pipeline mode)")
    
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
        for task in list(self.agent_tasks.values()):
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

            base_context = dict(context) if isinstance(context, dict) else {}

            # 🧠 BrainNetwork模式: 图拓扑激活扩散 + CapabilityOrchestrator
            if self.use_brain_network:
                logger.info("🧠 Using BrainNetwork (Parallel Activation)")
                return await self._process_with_brain_network(user_input, base_context, start_time)

            # ⚙️ Pipeline模式: 传统串行流水线(fallback)
            logger.info("⚙️ Using Pipeline (Sequential Execution)")

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
                            'context': base_context
                        }
                    }
                )
            )
            
            encoded_input = perception_result.get('encoded_input', {})
            requires_chunked_storage = perception_result.get('requires_chunked_storage', False)

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
                            'context': base_context,
                            'optimal_sequence': optimal_agents[:3]  # Top 3 from plasticity
                        }
                    }
                )
            )
            
            coordination_plan = routing_result.get('coordination_plan', {})
            # Use plasticity-optimized agents if executive control doesn't override
            primary_agents = coordination_plan.get('primary_agents', optimal_agents[:2])
            secondary_agents = coordination_plan.get('secondary_agents', optimal_agents[2:4])
            
            # Phase 3: Selective Agent Activation (选择性智能体激活)
            parallel_tasks = {}
            activated_agents = []

            # Always retrieve memories - this is essential for context
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
            activated_agents.append('memory_retrieval')

            # Selective Stress/Threat Detection - only for potentially concerning content
            if self._requires_stress_analysis(user_input):
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
                activated_agents.append('stress_response')
            
            # Activate primary agents based on routing
            for agent_name in primary_agents:
                agent_id = self._map_agent_name(agent_name)
                if agent_id and agent_id in self.agents:
                    parallel_tasks[agent_id] = self._create_primary_agent_task(agent_id, user_input, base_context)
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
                    timeout=self.settings.parallel_phase_timeout
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
            # Only get threat info if stress_response was actually activated
            threat_info = parallel_results.get('stress_response', {}) if 'stress_response' in parallel_results else {'threat_score': 0.0, 'threat_level': 'none'}

            base_context['retrieved_memories'] = memories

            personality_result = parallel_results.get('personality')
            if (not personality_result) or personality_result.get('error'):
                try:
                    personality_result = await self._activate_agent(
                        'personality',
                        AgentMessage(
                            sender='coordinator',
                            receiver='personality',
                            message_type='request',
                            content={
                                'action': 'generate_personality_response',
                                'user_input': user_input,
                                'retrieved_memories': memories
                            }
                        )
                    )
                except Exception as exc:
                    logger.warning(f"Personality agent invocation failed: {exc}")
                    personality_result = None

            if personality_result and not personality_result.get('error'):
                base_context['personality_context'] = personality_result.get('personality_context', {})
                base_context['current_personality_emotion'] = personality_result.get('current_emotion')
                base_context['persona_memories_used'] = personality_result.get('persona_memories_used')

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
                        timeout=self.settings.buffer_exchange_timeout
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
                        'context': base_context,
                        'memories': memories[:5],  # Top 5 most relevant
                        'plasticity_memories': plasticity_memories,
                        'threat_info': threat_info,
                        'primary_results': {k: v for k, v in parallel_results.items() if k not in ['memory_retrieval', 'stress_response']}
                    }
                )
            )
            
            main_response = response_result.get('response', '抱歉，我现在无法处理您的请求。')

            # Persona-aware refinement
            personality_result = parallel_results.get('personality')
            if personality_result and personality_result.get('error'):
                personality_result = None

            if personality_result is None:
                try:
                    personality_result = await self._activate_agent(
                        'personality',
                        AgentMessage(
                            sender='coordinator',
                            receiver='personality',
                            message_type='request',
                            content={
                                'action': 'generate_personality_response',
                                'user_input': user_input,
                                'retrieved_memories': memories[:5],
                                'base_response': main_response
                            }
                        )
                    )
                except Exception as exc:
                    logger.warning(f"Personality agent invocation failed: {exc}")
                    personality_result = None

            if personality_result and not personality_result.get('error'):
                base_context['personality_context'] = personality_result.get('personality_context', {})
                base_context['persona_memories_used'] = personality_result.get('persona_memories_used', 0)
                base_context['personality_current_emotion'] = personality_result.get('current_emotion')

                # Only use personality response if no relevant memories were found
                # When memories are available, preserve the memory-based conversation response
                if len(memories) == 0 or not response_result.get('memories_used', 0):
                    main_response = personality_result.get('personality_response', main_response)
                else:
                    # Keep memory-based response, but add personality context for logging
                    logger.info(f"Preserving memory-based response from conversation agent ({len(memories)} memories used)")
            
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
                            await self._activate_agent(
                                'persona_memory',
                                AgentMessage(
                                    sender='coordinator',
                                    receiver='persona_memory',
                                    message_type='request',
                                    content={
                                        'action': 'store_persona_memory',
                                        'memory': {
                                            'content': f"用户偏好：{user_input}",
                                            'category': 'preference',
                                            'importance': 0.85,
                                            'context_tags': ['persona', 'preference', 'value_alignment'],
                                            'emotion_tags': ['positive'],
                                            'metadata': {
                                                'preference_type': 'user_input',
                                                'value_alignment': base_context.get('user_values', 'neutral')
                                            }
                                        }
                                    }
                                )
                            )
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
                self._create_background_task("store_user_preference", store_preference_background())
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
            
            # Phase 6: Memory Strategy (短期存储 + 长期候选)
            memory_stored = False
            memory_storage_error = None
            memory_strategy = 'skipped'

            # Handle chunked text if needed
            if requires_chunked_storage and encoded_input.get('segments'):
                await self._handle_chunked_text_storage(
                    encoded_input=encoded_input,
                    user_input=user_input,
                    assistant_response=main_response,
                    context=base_context
                )
                memory_strategy = 'chunked_storage'

            # Always keep a short-term snapshot for immediate context reuse
            await self._store_short_term_memory_snapshot(
                user_input=user_input,
                assistant_response=main_response,
                context=base_context
            )

            if self._should_consider_long_term(user_input, base_context):
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

                conversation_content = f"用户说：{user_input}\n助手回复：{main_response}"

                explicit_memory_intent = self._has_explicit_memory_request(user_input) or preference_processed

                async def store_conversation_memory():
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
                    return memory_id

                async def handle_success(memory_id: str):
                    self.processing_stats['memory_operations'] += 1
                    logger.info(f"Long-term memory stored: {memory_id}")

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

                # Record existing memory activation immediately
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

                if explicit_memory_intent:
                    memory_strategy = 'stored_immediately'
                    try:
                        memory_id = await asyncio.wait_for(
                            store_conversation_memory(),
                            timeout=self.settings.memory_storage_timeout
                        )

                        if memory_id:
                            memory_stored = True
                            await handle_success(memory_id)
                        else:
                            memory_storage_error = "Memory storage returned None - possible embedding failure"
                            logger.warning(memory_storage_error)
                    except asyncio.TimeoutError:
                        memory_storage_error = f"Memory storage timeout after {self.settings.memory_storage_timeout}s"
                        logger.warning(memory_storage_error)
                    except Exception as e:
                        memory_storage_error = f"Memory storage failed: {str(e)}"
                        logger.error(memory_storage_error)
                else:
                    memory_strategy = 'queued_for_consolidation'

                    async def background_store():
                        try:
                            memory_id = await store_conversation_memory()
                            if memory_id:
                                await handle_success(memory_id)
                            else:
                                logger.warning("Background memory storage returned None - possible embedding failure")
                        except Exception as exc:
                            logger.error(f"Background memory storage failed: {exc}")

                    await self._queue_memory_candidate(
                        user_input=user_input,
                        assistant_response=main_response,
                        importance=importance,
                        emotion_tags=emotion_tags,
                        threat_info=threat_info
                    )
                    self._create_background_task("store_conversation_memory", background_store())

            else:
                memory_strategy = 'short_term_only'
            
            # Phase 7: Background Processing (后台处理)
            background_tasks = []
            
            # Reflection and insights
            if len(memories) > 3:
                background_tasks.append(
                    self._create_background_task(
                        "background_reflection",
                        self._trigger_background_reflection(memories)
                    )
                )
            
            # Memory consolidation
            if memory_stored and importance > 0.7:
                background_tasks.append(
                    self._create_background_task(
                        "background_consolidation",
                        self._trigger_background_consolidation()
                    )
                )

            # Process chunked text queue periodically
            if self.processing_stats['total_requests'] % 10 == 0:
                background_tasks.append(
                    self._create_background_task(
                        "process_chunked_queue",
                        self._trigger_chunked_queue_processing()
                    )
                )
            
            # Forgetting (higher frequency for buffer maintenance)
            if self.processing_stats['total_requests'] % 5 == 0:
                background_tasks.append(
                    self._create_background_task(
                        "background_forgetting",
                        self._trigger_background_forgetting()
                    )
                )

            if self.processing_stats['total_requests'] % self.settings.buffer_cleanup_frequency == 0:
                background_tasks.append(
                    self._create_background_task(
                        "buffer_cleanup",
                        agent_buffer_system.cleanup_stale_entries(
                            max_age_hours=self.settings.buffer_retention_hours
                        )
                    )
                )

            if self.processing_stats['total_requests'] % self.settings.faiss_compaction_frequency == 0:
                background_tasks.append(
                    self._create_background_task(
                        "faiss_compaction",
                        memory_system.enforce_storage_limits(
                            max_vectors=self.settings.max_faiss_vectors
                        )
                    )
                )
            
            # Background tasks run independently - don't wait for them to avoid blocking
            insights = {
                'status': 'background_processing',
                'tasks_started': len(background_tasks),
                'memory_strategy': memory_strategy
            }
            if 'personality_context' in base_context:
                insights['personality_context'] = base_context.get('personality_context', {})
                insights['persona_memories_used'] = base_context.get('persona_memories_used', 0)
                insights['current_personality_emotion'] = base_context.get('personality_current_emotion')

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Collect agent logs
            agent_logs = {}
            for agent_id, agent in self.agents.items():
                if agent.execution_log:
                    agent_logs[agent_id] = agent.execution_log[-5:]  # Last 5 entries
            
            # 检查响应是否包含错误标志
            has_error = False
            error_message = None

            # 检查是否有API异常或其他错误标志
            if main_response.startswith('⚠️') or 'API异常' in main_response:
                has_error = True
                error_message = f"Response contains error: {main_response[:100]}"
                self.processing_stats['failed_requests'] += 1
            else:
                # 检查并行结果中是否有错误
                for agent_id, result_data in parallel_results.items():
                    if isinstance(result_data, dict) and result_data.get('error'):
                        has_error = True
                        error_message = f"Agent {agent_id} error: {result_data['error']}"
                        self.processing_stats['failed_requests'] += 1
                        break

                if not has_error:
                    self.processing_stats['successful_requests'] += 1

            # Include memory storage error in final error reporting
            final_error_message = error_message
            if memory_storage_error and not final_error_message:
                final_error_message = memory_storage_error
                has_error = True

            result = ProcessingResult(
                response=main_response,
                routing_decision=coordination_plan,
                agents_involved=list(parallel_results.keys()),
                memories_retrieved=memories,
                memory_stored=memory_stored,
                processing_time=processing_time,
                agent_logs=agent_logs,
                insights=insights,
                success=not has_error,
                error=final_error_message
            )
            
            if has_error:
                logger.warning(f"Processed request with errors in {processing_time:.2f}s with {len(memories)} memories")
            else:
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

    async def process_input(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Legacy compatibility wrapper returning plain response text."""
        result = await self.process_user_input(user_input, context)
        if isinstance(result, ProcessingResult):
            return result.response
        return result
    
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

    def _requires_stress_analysis(self, user_input: str) -> bool:
        """判断是否需要进行压力/威胁分析"""
        # Skip stress analysis for simple greetings and preferences
        simple_patterns = ['你好', 'hello', 'hi', '谢谢', 'thank', '再见', 'bye']
        if any(pattern in user_input.lower() for pattern in simple_patterns):
            return False

        # Skip for preference expressions (they're usually positive)
        if self._contains_user_preference(user_input):
            return False

        # Require stress analysis for potentially emotional content
        stress_indicators = [
            '担心', '害怕', '愤怒', '沮丧', '焦虑', '紧张', '压力', '困难', '问题',
            'worry', 'afraid', 'angry', 'frustrated', 'anxious', 'stress', 'problem'
        ]

        # Also analyze longer inputs (might contain complex emotions)
        return (any(indicator in user_input.lower() for indicator in stress_indicators) or
                len(user_input) > 50)
    
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
        elif agent_id == 'personality':
            return await self._activate_agent(
                agent_id,
                AgentMessage(
                    sender='coordinator',
                    receiver=agent_id,
                    message_type='request',
                    content={
                        'action': 'generate_personality_response',
                        'user_input': user_input,
                        'retrieved_memories': context.get('retrieved_memories', []) if context else []
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
    
    def _should_consider_long_term(self, user_input: str, context: Dict) -> bool:
        """Decide whether the conversation should be evaluated for long-term storage."""
        cleaned = user_input.strip()
        if len(cleaned) < 5:
            return False

        simple_greetings = ['hi', 'hello', 'bye', '谢谢', '再见']
        if cleaned.lower() in simple_greetings:
            return False

        # Explicit memory intents always qualify
        if self._has_explicit_memory_request(cleaned):
            return True

        # Prefer storing if the input carries descriptive content beyond trivial chat
        descriptive_tokens = len([w for w in cleaned.split() if len(w) > 2])
        if descriptive_tokens >= 4:
            return True

        # Fall back to context or routing decisions (e.g. preference flag) if provided
        if context.get('retrieved_memories') or context.get('persona_memories_used'):
            return True

        return False

    def _has_explicit_memory_request(self, user_input: str) -> bool:
        """Detect whether user explicitly asks the system to remember information."""
        memory_keywords = ['记住', '记录', '保存', '记下', '牢记', 'remember', 'save', 'store']
        lowered = user_input.lower()
        return any(keyword in lowered for keyword in memory_keywords)

    async def _store_short_term_memory_snapshot(self, user_input: str, assistant_response: str, context: Dict) -> None:
        """Persist the latest exchange in short-term structures without blocking."""
        snapshot = {
            'user_input': user_input,
            'assistant_response': assistant_response,
            'timestamp': datetime.now().isoformat()
        }

        try:
            await self._activate_agent(
                'short_term_memory',
                AgentMessage(
                    sender='coordinator',
                    receiver='short_term_memory',
                    message_type='request',
                    content={
                        'action': 'store_short_term',
                        'item': {
                            'content': f"用户: {user_input}\n助手: {assistant_response}",
                            'modality': 'verbal'
                        }
                    }
                )
            )
        except Exception as exc:
            logger.warning(f"Unable to update short-term memory agent: {exc}")

        try:
            # Apply buffer size limits
            buffer_content = await agent_buffer_system.read_buffer('short_term_memory')
            recent_conversations = buffer_content.get('recent_conversations', [])

            # Limit buffer size according to settings
            max_items = self.settings.max_short_term_buffer_size // 500  # ~500 chars per conversation
            if len(recent_conversations) >= max_items:
                # Keep only the most recent items
                recent_conversations = recent_conversations[-(max_items-1):]

            # Add new conversation
            recent_conversations.append({
                'snapshot': snapshot,
                'context_tags': context.get('context_tags', []),
                'timestamp': snapshot['timestamp']
            })

            await agent_buffer_system.write_buffer(
                'short_term_memory',
                'recent_conversations',
                recent_conversations
            )

        except Exception as exc:
            logger.debug(f"Failed to persist short-term snapshot buffer: {exc}")

    async def _handle_chunked_text_storage(
        self,
        encoded_input: Dict[str, Any],
        user_input: str,
        assistant_response: str,
        context: Dict[str, Any]
    ) -> None:
        """Handle storage of chunked long text"""
        segments = encoded_input.get('segments', [])
        overview = encoded_input.get('overview', {})

        logger.info(f"Handling chunked text storage: {len(segments)} segments")

        # Store overview in short-term memory
        try:
            await self._activate_agent(
                'short_term_memory',
                AgentMessage(
                    sender='coordinator',
                    receiver='short_term_memory',
                    message_type='request',
                    content={
                        'action': 'store_short_term',
                        'item': {
                            'content': f"Long text overview: {overview.get('theme', 'N/A')}",
                            'type': 'text_overview',
                            'metadata': overview
                        }
                    }
                )
            )
        except Exception as e:
            logger.warning(f"Failed to store text overview: {e}")

        # Check for explicit memory request
        if self._has_explicit_memory_request(user_input):
            # Store ALL segments immediately for explicit requests, using batched approach
            storage_priority = overview.get('storage_priority', 'medium')

            if storage_priority in ['high', 'medium']:
                # Store segments in batches to avoid overwhelming the system
                await self._store_all_segments_batched(segments, overview, immediate=True)
        else:
            # Queue ALL segments for background consolidation
            await self._queue_all_segments_for_consolidation(segments, overview)

    async def _store_all_segments_batched(
        self,
        segments: List[Dict],
        overview: Dict,
        immediate: bool = False
    ) -> None:
        """Store all segments using batched approach with overflow handling"""
        max_segments = self.settings.max_segments_immediate if immediate else self.settings.max_segments_background

        if len(segments) > max_segments:
            logger.warning(f"Large text with {len(segments)} segments exceeds limit of {max_segments}")

            # Handle overflow
            if self.settings.enable_segment_serialization:
                await self._handle_segment_overflow(segments[max_segments:], overview)
            else:
                logger.warning(f"Truncating to {max_segments} segments - {len(segments) - max_segments} segments will be lost")

            # Process only up to the limit
            segments = segments[:max_segments]

        batch_size = 3  # Process 3 segments at a time
        total_stored = 0

        logger.info(f"Storing {len(segments)} segments in batches of {batch_size}")

        for i in range(0, len(segments), batch_size):
            batch = segments[i:i + batch_size]

            for seg in batch:
                try:
                    importance = 0.7 if immediate else 0.5
                    # Reduce importance for later segments to maintain priority
                    if seg['index'] > 10:
                        importance *= 0.8

                    await memory_system.store_memory(
                        content=seg['summary'],
                        memory_type='episodic',
                        importance=importance,
                        context_tags=['chunked_text', 'segment', 'complete_set'],
                        metadata={
                            'segment_index': seg['index'],
                            'total_segments': len(segments),
                            'batch_number': i // batch_size + 1,
                            'keywords': seg.get('keywords', []),
                            'parent_overview': overview.get('theme', ''),
                            'processing_method': seg.get('processing_method', 'local'),
                            'stored_at': datetime.now().isoformat()
                        }
                    )
                    total_stored += 1

                except Exception as e:
                    logger.error(f"Failed to store segment {seg['index']}: {e}")
                    # Don't break the loop - continue with other segments

            # Small delay between batches to avoid overwhelming the system
            if i + batch_size < len(segments):
                await asyncio.sleep(0.1)

        logger.info(f"Batch storage completed: {total_stored}/{len(segments)} segments stored")

    async def _handle_segment_overflow(self, overflow_segments: List[Dict], overview: Dict) -> None:
        """Handle segments that exceed the storage limit by serializing to disk"""
        try:
            import json
            from pathlib import Path

            # Create overflow directory
            overflow_dir = Path("data/segment_overflow")
            overflow_dir.mkdir(parents=True, exist_ok=True)

            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            theme_key = overview.get('theme', 'unknown')[:20].replace(' ', '_')
            filename = f"overflow_{theme_key}_{timestamp}.json"
            filepath = overflow_dir / filename

            # Serialize overflow segments
            overflow_data = {
                'overview': overview,
                'total_overflow_segments': len(overflow_segments),
                'segments': [
                    {
                        'index': seg['index'],
                        'summary': seg['summary'],
                        'keywords': seg.get('keywords', []),
                        'token_count': seg['token_count'],
                        'processing_method': seg.get('processing_method', 'local')
                    }
                    for seg in overflow_segments
                ],
                'serialized_at': datetime.now().isoformat(),
                'note': 'These segments exceeded immediate storage limits and were serialized for later processing'
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(overflow_data, f, ensure_ascii=False, indent=2)

            logger.info(f"Serialized {len(overflow_segments)} overflow segments to {filepath}")

            # Create a reference memory to the serialized file
            await memory_system.store_memory(
                content=f"Large text overflow: {len(overflow_segments)} additional segments saved to disk",
                memory_type='procedural',
                importance=0.4,
                context_tags=['overflow', 'serialized', 'reference'],
                metadata={
                    'overflow_file': str(filepath),
                    'overflow_count': len(overflow_segments),
                    'parent_theme': overview.get('theme', ''),
                    'serialization_method': 'disk_storage',
                    'can_be_loaded': True
                }
            )

        except Exception as e:
            logger.error(f"Failed to serialize overflow segments: {e}")
            # At least log the overflow for manual recovery
            logger.warning(f"LOST SEGMENTS: {len(overflow_segments)} segments from '{overview.get('theme', 'unknown')}' could not be stored or serialized")

    async def _queue_all_segments_for_consolidation(
        self,
        segments: List[Dict],
        overview: Dict
    ) -> None:
        """Queue ALL segments for background consolidation with intelligent batching"""
        # Instead of limiting segments, create multiple queue entries for large texts
        batch_size = 5
        batch_count = 0

        for i in range(0, len(segments), batch_size):
            batch = segments[i:i + batch_size]
            batch_count += 1

            consolidation_data = {
                'type': 'chunked_text_batch',
                'overview': overview,
                'total_segments': len(segments),
                'batch_number': batch_count,
                'batch_start_index': i,
                'segments': [
                    {
                        'index': seg['index'],
                        'summary': seg['summary'],
                        'keywords': seg.get('keywords', []),
                        'token_count': seg['token_count'],
                        'processing_method': seg.get('processing_method', 'local')
                    }
                    for seg in batch
                ],
                'queued_at': datetime.now().isoformat()
            }

            try:
                await agent_buffer_system.write_buffer(
                    'consolidation',
                    'chunked_text_queue',
                    consolidation_data,
                    append=True
                )

            except Exception as e:
                logger.warning(f"Failed to queue batch {batch_count}: {e}")

        logger.info(f"Queued {len(segments)} segments in {batch_count} batches")

        # Apply intelligent queue management
        await self._manage_consolidation_queue_size()

    async def _manage_consolidation_queue_size(self) -> None:
        """Intelligently manage queue size with prioritized eviction"""
        try:
            buffer_content = await agent_buffer_system.read_buffer('consolidation')
            queue = buffer_content.get('chunked_text_queue', [])

            max_queue_size = 20  # Allow more items but still cap it

            if len(queue) > max_queue_size:
                # Sort by priority: recent items and high-priority overviews first
                def get_priority(item):
                    overview = item.get('overview', {})
                    priority = overview.get('storage_priority', 'low')
                    queued_time = item.get('queued_at', '')

                    priority_score = {'high': 3, 'medium': 2, 'low': 1}.get(priority, 1)
                    # Recent items get slight boost
                    time_score = 1 if queued_time else 0

                    return priority_score + time_score

                # Keep highest priority items
                sorted_queue = sorted(queue, key=get_priority, reverse=True)
                kept_queue = sorted_queue[:max_queue_size]

                await agent_buffer_system.write_buffer(
                    'consolidation',
                    'chunked_text_queue',
                    kept_queue
                )

                evicted_count = len(queue) - len(kept_queue)
                logger.info(f"Queue management: kept {len(kept_queue)}, evicted {evicted_count} low-priority items")

        except Exception as e:
            logger.warning(f"Queue management failed: {e}")

    async def _queue_chunked_segments_for_consolidation(
        self,
        segments: List[Dict],
        overview: Dict
    ) -> None:
        """Legacy method - redirect to new implementation"""
        await self._queue_all_segments_for_consolidation(segments, overview)

    async def _queue_memory_candidate(
        self,
        user_input: str,
        assistant_response: str,
        importance: float,
        emotion_tags: List[str],
        threat_info: Dict
    ) -> None:
        """Queue conversation as long-term candidate for consolidation agents."""
        candidate = {
            'user_input': user_input,
            'assistant_response': assistant_response,
            'importance': importance,
            'emotion_tags': emotion_tags,
            'threat_score': threat_info.get('threat_score'),
            'queued_at': datetime.now().isoformat()
        }

        try:
            await agent_buffer_system.write_buffer(
                'consolidation',
                'pending_candidates',
                candidate,
                append=True
            )
        except Exception as exc:
            logger.debug(f"Failed to queue memory candidate: {exc}")
    
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

    async def _trigger_chunked_queue_processing(self):
        """Trigger processing of queued chunked text segments"""
        try:
            await self._activate_agent(
                'consolidation',
                AgentMessage(
                    sender='coordinator',
                    receiver='consolidation',
                    message_type='request',
                    content={'action': 'process_chunked_queue'}
                )
            )
        except Exception as e:
            logger.error(f"Chunked queue processing error: {e}")
    
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

    def _create_background_task(self, label: str, coro: Coroutine[Any, Any, Any]) -> asyncio.Task:
        """Trackable helper for background tasks to ensure clean shutdown."""
        self._task_counter += 1
        task_name = f"{label}_{self._task_counter}"
        task = asyncio.create_task(coro)
        self.agent_tasks[task_name] = task

        def _cleanup(_: asyncio.Task, name: str = task_name):
            self.agent_tasks.pop(name, None)

        task.add_done_callback(_cleanup)
        return task
    
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



    async def _process_with_brain_network(
        self,
        user_input: str,
        context: Dict[str, Any],
        start_time: datetime
    ) -> ProcessingResult:
        """
        使用BrainNetwork图拓扑 + CapabilityOrchestrator处理输入

        流程:
        1. CapabilityAnalyzer分析需要的推理能力
        2. 记忆检索 (带时间范围过滤)
        3. 分布式记忆分配到脑区
        4. CapabilityOrchestrator编排推理 OR BrainNetwork激活扩散
        """
        # 步骤1: 语言检测
        perception_result = await self._activate_agent(
            'perception_encoding',
            AgentMessage(
                sender='coordinator',
                receiver='perception_encoding',
                message_type='request',
                content={'action': 'detect_language', 'text': user_input}
            )
        )

        detected_language = perception_result.get('language', 'en')
        language_confidence = perception_result.get('confidence', 0.9)
        context['detected_language'] = detected_language
        context['language_confidence'] = language_confidence

        logger.info(f"🌐 Detected language: {detected_language} (confidence: {language_confidence:.2f})")

        # 🔥 步骤2: 使用CapabilityAnalyzer分析推理能力
        from src.reasoning.capability_analyzer import CapabilityAnalyzer
        analyzer = CapabilityAnalyzer()

        try:
            capability_analysis = await analyzer.analyze(user_input)
            capabilities = capability_analysis.get('capabilities', [])
            execution_plan = capability_analysis.get('execution_plan', 'Sequential execution')

            logger.info(f"🧠 Detected capabilities: {[c['name'] for c in capabilities]}")
            logger.info(f"📋 Execution plan: {execution_plan}")

            # 简化的复杂度检测
            if len(capabilities) == 0:
                complexity_level = 0
                max_iterations = 0
            elif len(capabilities) <= 2 and not any(c['name'] == 'multi_hop_inference' for c in capabilities):
                complexity_level = 1
                max_iterations = 1
            elif len(capabilities) <= 3:
                complexity_level = 2
                max_iterations = 2
            else:
                complexity_level = 3
                max_iterations = 3

            logger.info(f"🎯 Complexity: Level {complexity_level}, Capabilities: {len(capabilities)}, Iterations: {max_iterations}")

        except Exception as e:
            logger.warning(f"⚠️ CapabilityAnalyzer failed: {e}, using default complexity")
            capabilities = []
            execution_plan = 'Default execution'
            complexity_level = 1
            max_iterations = 1

        # 🔥 步骤3: 如果是temporal问题,提取时间范围
        time_range = None
        cap_names = [c['name'] for c in capabilities]
        if 'temporal_calculation' in cap_names or 'duration_inference' in cap_names:
            from src.utils.date_extractor import DateExtractor
            time_range = DateExtractor.extract_time_range(user_input)
            if time_range:
                logger.info(f"⏰ Extracted time_range: {time_range}")

        # 步骤4: 记忆检索 (带时间过滤)
        memories = []
        try:
            retrieval_result = await self._activate_agent(
                'memory_retrieval',
                AgentMessage(
                    sender='brain_network_coordinator',
                    receiver='memory_retrieval',
                    message_type='request',
                    content={
                        'action': 'semantic_search',
                        'query': user_input,
                        'k': 20,
                        'time_range': time_range  # 🔥 传递时间范围参数!
                    }
                )
            )

            retrieved_memories = retrieval_result.get('memories', [])
            logger.info(f"🔍 Vector retrieval: {len(retrieved_memories)} memories from FAISS")

            # 分布式分配记忆到脑区
            for mem_data in retrieved_memories:
                if 'memory' in mem_data:
                    content = mem_data['memory'].get('content', '')
                    content_lower = content.lower()

                    regions = []

                    # 情节记忆: 海马体
                    if any(kw in content_lower for kw in ['用户:', '助手:', 'user:', 'assistant:', 'yesterday', 'today', 'on ', 'may', 'attended', 'went to']):
                        regions.append('hippocampus')

                    # 语义记忆: 颞叶
                    if any(kw in content_lower for kw in ['concept', 'knowledge', 'fact', '概念', '知识']):
                        regions.append('temporal')

                    # 情绪记忆: 杏仁核
                    if any(kw in content_lower for kw in ['fear', 'happy', 'sad', 'angry', '害怕', '开心', '难过']):
                        regions.append('amygdala')

                    if not regions:
                        regions = ['hippocampus']  # 默认海马体

                    for region in regions:
                        memories.append({
                            **mem_data,
                            'region': region
                        })

            # 统计分布
            region_counts = {}
            for m in memories:
                region_counts[m['region']] = region_counts.get(m['region'], 0) + 1

            logger.info(f"✅ Distributed to regions: " + ", ".join(f"{r}={c}" for r, c in sorted(region_counts.items())))

        except Exception as e:
            logger.warning(f"Retrieval failed: {e}")

        # 🔥🔥🔥 步骤5: 决策路径

        # 路径A: 如果有特殊推理能力,使用CapabilityOrchestrator
        if len(capabilities) > 0:
            logger.info(f"🎯 Using CapabilityOrchestrator to execute {len(capabilities)} capabilities")

            try:
                from src.reasoning.capability_orchestrator import CapabilityOrchestrator

                agents_dict = {
                    'memory_retrieval': self.memory_retrieval,
                    'reasoning_validator': self.reasoning_validator,
                    'consolidation': self.consolidation,
                    'reflection': self.reflection,
                    'conversation': self.conversation
                }
                # 🔥 NEW: 传递memory_system以启用HippocampalPrefrontalLoop
                orchestrator = CapabilityOrchestrator(
                    brain_agents=agents_dict,
                    memory_system=self.memory_system
                )

                orchestrator_result = await orchestrator.execute(
                    query=user_input,
                    capabilities=capabilities,
                    memories=memories,
                    execution_plan=execution_plan
                )

                response = orchestrator_result.get('answer') or 'No answer generated'
                confidence = orchestrator_result.get('confidence', 0.7)
                reasoning_chain = orchestrator_result.get('reasoning_chain', [])

                response_preview = response[:100] if len(response) > 100 else response
                logger.info(f"✅ CapabilityOrchestrator completed: {response_preview} (confidence={confidence:.2f})")

                processing_time = (datetime.now() - start_time).total_seconds()
                self.processing_stats['successful_requests'] += 1

                # 存储记忆
                memory_stored = await self._store_memory_if_needed(user_input, response)

                return ProcessingResult(
                    response=response,
                    routing_decision={
                        'mode': 'capability_orchestrator',
                        'complexity_level': complexity_level,
                        'capabilities': [c['name'] for c in capabilities],
                        'execution_plan': execution_plan
                    },
                    agents_involved=orchestrator_result.get('capabilities_used', []),
                    memories_retrieved=memories,
                    memory_stored=memory_stored,
                    processing_time=processing_time,
                    agent_logs={'reasoning_chain': reasoning_chain},
                    insights={
                        'complexity_level': complexity_level,
                        'confidence': confidence,
                        'capabilities_executed': len(capabilities)
                    },
                    success=True
                )
            except Exception as e:
                logger.error(f"❌ CapabilityOrchestrator failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Fallback to BrainNetwork

        # 路径B: 使用BrainNetwork图拓扑激活扩散
        logger.info(f"🧠 Using BrainNetwork: {max_iterations} iterations for Level {complexity_level}")

        network_result = await self.brain_network.process(
            stimulus=user_input,
            context={
                'memories': memories,
                'detected_language': detected_language,
                'complexity': complexity_level
            },
            max_iterations=max_iterations or 5,
            convergence_threshold=0.8
        )

        processing_time = (datetime.now() - start_time).total_seconds()
        self.processing_stats['successful_requests'] += 1

        # 存储记忆
        memory_stored = await self._store_memory_if_needed(user_input, network_result['response'])

        return ProcessingResult(
            response=network_result['response'],
            routing_decision={
                'mode': 'brain_network',
                'converged': network_result['converged'],
                'iterations': network_result.get('convergence_iteration', -1)
            },
            agents_involved=list(network_result.get('workspace', {}).keys()),
            memories_retrieved=memories,
            memory_stored=memory_stored,
            processing_time=processing_time,
            agent_logs=network_result.get('workspace', {}),
            insights={
                'convergence_iteration': network_result.get('convergence_iteration', -1),
                'final_activation': network_result.get('final_activation', {}),
                'confidence': network_result.get('confidence', 0.0),
                'architecture': 'brain_network'
            },
            success=True
        )


    async def _store_memory_if_needed(self, user_input: str, response: str) -> bool:
        """辅助方法: 根据输入类型存储记忆"""
        try:
            is_learning = any(kw in user_input.lower() for kw in [
                'on ', 'may', 'attended', 'researched', 'learned', 'studied'
            ])

            if is_learning:
                memory_id = await self.memory_system.store_memory(
                    content=user_input,
                    importance=0.9,
                    context_tags=['learning', 'event', 'brain_network']
                )
                logger.info(f"📚 Stored learning event: {memory_id}")
                return True
            else:
                conversation_content = f"用户: {user_input}\\n助手: {response}"
                memory_id = await self.memory_system.store_memory(
                    content=conversation_content,
                    importance=0.5,
                    context_tags=['brain_network', 'conversation']
                )
                logger.info(f"💬 Stored conversation: {memory_id}")
                return True
        except Exception as e:
            logger.warning(f"Memory storage failed: {e}")
            return False


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
