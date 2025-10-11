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

        # 🧠 BrainNetwork initialization (always enabled - brain-inspired architecture)
        from src.brain.brain_network import BrainNetwork
        self.brain_network = BrainNetwork(agents=self.agents)
        logger.info("🧠 BrainNetwork initialized (graph topology activation mode)")
    
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
        Main processing using brain-inspired BrainNetwork architecture
        实现类脑信息处理流程 (图拓扑激活扩散)
        """
        start_time = datetime.now()

        try:
            self.processing_stats['total_requests'] += 1

            if not self.is_running:
                await self.start_system()

            logger.info(f"Processing user input: {user_input[:50]}...")

            base_context = dict(context) if isinstance(context, dict) else {}

            # 🧠 BrainNetwork模式: 图拓扑激活扩散 + CapabilityOrchestrator
            logger.info("🧠 Using BrainNetwork (Parallel Activation)")
            return await self._process_with_brain_network(user_input, base_context, start_time)

        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            return ProcessingResult(
                success=False,
                response=f"处理请求时发生错误: {str(e)}",
                metadata={'error': str(e)}
            )

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
                        'action': 'multi_strategy_search',  # ✅ 使用混合检索策略
                        'query': user_input,
                        'k': 20,
                        'time_range': time_range  # 🔥 传递时间范围参数!
                    }
                )
            )

            retrieved_memories = retrieval_result.get('memories', [])
            logger.info(f"🔍 Vector retrieval: {len(retrieved_memories)} memories from FAISS")

            # 分布式分配记忆到脑区 - 基于记忆类型而非硬编码关键词
            memory_type_to_region = {
                'episodic': 'hippocampus',      # 情节记忆 -> 海马体
                'semantic': 'temporal',          # 语义记忆 -> 颞叶
                'procedural': 'cerebellum',      # 程序记忆 -> 小脑
                'working': 'prefrontal',         # 工作记忆 -> 前额叶
                'emotional': 'amygdala'          # 情绪记忆 -> 杏仁核
            }

            for mem_data in retrieved_memories:
                if 'memory' in mem_data:
                    memory_type = mem_data['memory'].get('memory_type', 'episodic')
                    emotion_tags = mem_data['memory'].get('emotion_tags', [])

                    # 根据记忆类型分配脑区
                    regions = []

                    # 主要脑区: 根据memory_type
                    primary_region = memory_type_to_region.get(memory_type, 'hippocampus')
                    regions.append(primary_region)

                    # 次要脑区: 如果有强烈情绪标签,也存入杏仁核
                    if emotion_tags and primary_region != 'amygdala':
                        regions.append('amygdala')

                    # 添加到记忆列表
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
