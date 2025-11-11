"""
Brain Network - 真实大脑架构实现
模拟大脑的并行激活、循环反馈、动态收敛机制

核心特性:
1. 并行激活 - 所有脑区同时工作
2. 激活扩散 - 通过连接权重传播激活
3. 循环反馈 - 脑区间双向通信
4. 动态收敛 - 迭代直到达成一致

Author: Claude
Date: 2025-01-09
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime
import numpy as np

from ..agents.base import BrainAgent, AgentMessage
from ..utils.config import get_logger
from .distributed_memory import get_distributed_memory
from .region_activation import RegionActivationDynamics
from .hippocampal_loop import HippocampalPrefrontalLoop
from .collaborative_output import CollaborativeOutput

logger = get_logger(__name__)


class BrainNetwork:
    """
    大脑激活扩散网络

    模拟真实大脑的工作方式:
    - 刺激到达 → 多个脑区同时激活
    - 激活扩散 → 通过连接传播
    - 循环反馈 → 前额叶↔海马体往复
    - 动态收敛 → 达成一致后输出

    架构灵感:
    - Spreading Activation Theory (Anderson, 1983)
    - Parallel Distributed Processing (Rumelhart & McClelland, 1986)
    - Global Workspace Theory (Baars, 1988)
    """

    def __init__(self, agents: Dict[str, BrainAgent], connection_matrix: Optional[np.ndarray] = None):
        """
        初始化大脑网络

        Args:
            agents: {agent_id: BrainAgent} - 所有脑区agents
            connection_matrix: 连接矩阵 (如果None则使用默认连接)
        """
        self.agents = agents
        self.agent_ids = list(agents.keys())
        self.n_agents = len(agents)

        # 激活水平: {agent_id: activation_level (0.0-1.0)}
        self.activation = {aid: 0.0 for aid in self.agent_ids}

        # 连接权重: {(source_id, target_id): weight}
        self.connections = self._initialize_connections(connection_matrix)

        # 执行历史
        self.iteration_history = []

        # 全局工作区 (Global Workspace) - 存储各脑区的输出
        self.workspace = {}

        # 🧠 分布式记忆系统 - 每个脑区存储不同类型记忆
        self.distributed_memory = get_distributed_memory()

        # 🔥 NEW: Brain-region collaboration modules
        self.region_activation = RegionActivationDynamics()
        self.hippocampal_loop = None  # 延迟初始化 (需要memory_system)
        self.collaborative_output = CollaborativeOutput(brain_agents=agents)

        logger.debug(f"🧠 Initialized BrainNetwork with {self.n_agents} regions")
        logger.debug(f"🔗 Total connections: {len(self.connections)}")
        logger.debug(f"💾 Distributed Memory System active")
        logger.info(f"🔥 Brain-region collaboration modules activated")


    def _initialize_connections(self, connection_matrix: Optional[np.ndarray] = None) -> Dict[Tuple[str, str], float]:
        """
        初始化脑区连接

        如果提供connection_matrix则使用,否则使用脑科学启发的默认连接
        """
        connections = {}

        if connection_matrix is not None:
            # 使用提供的连接矩阵
            for i, source_id in enumerate(self.agent_ids):
                for j, target_id in enumerate(self.agent_ids):
                    weight = connection_matrix[i, j]
                    if weight > 0:
                        connections[(source_id, target_id)] = weight
        else:
            # 默认连接: 基于脑科学的典型连接模式
            connections = self._create_default_connections()

        return connections


    def _create_default_connections(self) -> Dict[Tuple[str, str], float]:
        """
        创建默认的脑区连接

        基于神经科学研究的典型连接:
        - Thalamus → 所有皮层区域 (感觉中继)
        - Hippocampus ↔ Prefrontal (记忆-推理双向)
        - Prefrontal → Broca (推理-语言)
        - Amygdala → Prefrontal (情绪-执行控制)
        """
        connections = {}

        # 定义关键连接(基于真实大脑解剖)
        key_connections = [
            # 感知通路
            ('perception_encoding', 'short_term_memory', 0.9),  # 感知→工作记忆
            ('perception_encoding', 'memory_retrieval', 0.7),   # 感知→检索

            # 记忆系统
            ('short_term_memory', 'memory_retrieval', 0.8),     # 工作记忆→检索
            ('memory_retrieval', 'short_term_memory', 0.9),     # 检索→工作记忆(双向)
            ('memory_retrieval', 'reasoning_validator', 0.9),   # 海马体→前额叶
            ('reasoning_validator', 'memory_retrieval', 0.8),   # 前额叶→海马体(双向反馈!)

            # 推理-执行
            ('reasoning_validator', 'executive_control', 0.9),  # 推理→执行控制
            ('reasoning_validator', 'conversation', 0.8),       # 推理→语言生成
            ('executive_control', 'conversation', 0.7),         # 执行控制→语言

            # 反思回路
            ('conversation', 'reflection', 0.6),                # 输出→反思
            ('reflection', 'reasoning_validator', 0.7),         # 反思→推理(元认知)

            # 情绪影响
            ('stress_response', 'executive_control', 0.5),      # 杏仁核→前额叶
            ('stress_response', 'memory_retrieval', 0.4),       # 情绪→记忆检索
        ]

        for source, target, weight in key_connections:
            if source in self.agent_ids and target in self.agent_ids:
                connections[(source, target)] = weight

        # 添加弱连接: 所有脑区与执行控制的微弱连接(模拟ACC的全局监控)
        for agent_id in self.agent_ids:
            if agent_id != 'executive_control':
                connections[(agent_id, 'executive_control', )] = 0.2

        logger.info(f"Created {len(connections)} default brain connections")
        return connections

    def set_memory_system(self, memory_system):
        """设置记忆系统 (用于HippocampalPrefrontalLoop)"""
        self.hippocampal_loop = HippocampalPrefrontalLoop(
            memory_system=memory_system
        )
        logger.debug("🧠 HippocampalPrefrontalLoop initialized with memory system")

    async def process(
        self,
        stimulus: str,
        context: Dict[str, Any] = None,
        max_iterations: int = 5,
        convergence_threshold: float = 0.8
    ) -> Dict[str, Any]:
        """
        处理输入刺激 - 大脑网络的主循环

        模拟真实大脑处理信息的过程:
        1. 初始激活: 刺激到达,激活相关脑区
        2. 扩散传播: 激活通过连接扩散 (迭代5次,模拟50-250ms)
        3. 动态收敛: 关键脑区达成一致
        4. 提取答案: 从全局工作区提取结果

        Args:
            stimulus: 输入刺激(用户问题)
            context: 上下文信息
            max_iterations: 最大迭代次数(每次迭代~50ms)
            convergence_threshold: 收敛阈值(关键脑区激活>此值则收敛)

        Returns:
            {
                'response': 最终答案,
                'activation_history': 激活历史,
                'convergence_iteration': 收敛于第几次迭代,
                'workspace': 全局工作区内容
            }
        """
        start_time = datetime.now()
        context = context or {}

        logger.debug(f"🧠 BrainNetwork processing: {stimulus[:50]}...")

        # 重置状态
        self.activation = {aid: 0.0 for aid in self.agent_ids}
        self.workspace = {}
        self.iteration_history = []

        # 🌐 将语言信息和query写入workspace (供_finalize_response使用)
        self.workspace['detected_language'] = context.get('detected_language', 'en')
        self.workspace['query'] = stimulus
        # 🔥 NEW: Store memories for CollaborativeOutput
        self.workspace['memories'] = context.get('memories', []) if context else []

        # 阶段1: 初始激活 (t=0ms)
        await self._initial_activation(stimulus, context)
        logger.info(f"✨ Initial activation: {self._get_top_activated(3)}")

        # 阶段2: 激活扩散 (t=0-250ms, 每次迭代~50ms)
        converged = False
        convergence_iteration = -1

        for iteration in range(max_iterations):
            logger.debug(f"🔄 Iteration {iteration + 1}/{max_iterations}")

            # 单步扩散激活
            await self._spreading_activation_step(stimulus, context)

            # 记录历史
            self.iteration_history.append({
                'iteration': iteration,
                'activation': self.activation.copy(),
                'workspace': self.workspace.copy(),
                'timestamp': datetime.now()
            })

            # 检查收敛
            if self._is_converged(convergence_threshold):
                converged = True
                convergence_iteration = iteration
                logger.debug(f"✅ Converged at iteration {iteration + 1}")
                break

            # 短暂等待(模拟神经传递延迟)
            await asyncio.sleep(0.01)

        if not converged:
            logger.warning(f"⚠️ Did not converge after {max_iterations} iterations")

        # 阶段3: 提取答案
        result = await self._extract_consensus()

        processing_time = (datetime.now() - start_time).total_seconds()
        logger.debug(f"🎯 BrainNetwork completed in {processing_time:.2f}s")

        return {
            'response': result['response'],
            'confidence': result.get('confidence', 0.0),
            'reasoning_chain': result.get('reasoning_chain', []),
            'activation_history': self.iteration_history,
            'convergence_iteration': convergence_iteration,
            'converged': converged,
            'workspace': self.workspace,
            'processing_time': processing_time,
            'final_activation': self.activation
        }


    async def _initial_activation(self, stimulus: str, context: Dict[str, Any]):
        """
        初始激活: 刺激到达时哪些脑区会立即激活

        模拟: 感觉输入通过丘脑分发到各个皮层区域
        """
        # 1. Perception一定首先激活(接收输入)
        self.activation['perception_encoding'] = 1.0

        # 2. Working Memory立即激活(加载上下文)
        self.activation['short_term_memory'] = 0.8

        # 3. Retrieval Router激活(决定检索策略)
        if 'retrieval_router' in self.agent_ids:
            self.activation['retrieval_router'] = 0.7

        # 4. 如果有记忆上下文,海马体激活
        if context.get('memories') or context.get('has_memories'):
            self.activation['memory_retrieval'] = 0.9

        # 5. Executive Control微弱激活(全局监控)
        self.activation['executive_control'] = 0.5

        # 执行初始激活的agents
        initial_agents = ['perception_encoding', 'short_term_memory']
        for agent_id in initial_agents:
            if agent_id in self.agents:
                await self._activate_agent(agent_id, stimulus, context, activation_level=self.activation[agent_id])


    async def _spreading_activation_step(self, stimulus: str, context: Dict[str, Any]):
        """
        单步激活扩散: 所有脑区并行计算新激活

        模拟: 神经元的突触传递 (真实大脑10-50ms完成一次)

        核心机制:
        1. 每个脑区收集来自其他脑区的输入
        2. 计算新的激活水平 = Σ(source_activation × connection_weight)
        3. 如果激活超过阈值,执行该脑区的功能
        4. 所有脑区并行更新(asyncio.gather)
        """
        # 并行计算所有脑区的新激活
        tasks = []
        for agent_id in self.agent_ids:
            task = self._compute_region_activation(agent_id, stimulus, context)
            tasks.append(task)

        # 🔥 关键: 并行执行,不串行等待
        new_activations = await asyncio.gather(*tasks, return_exceptions=True)

        # 更新激活水平
        for agent_id, new_level in zip(self.agent_ids, new_activations):
            if isinstance(new_level, Exception):
                logger.error(f"Error in {agent_id}: {new_level}")
                continue

            # 激活衰减 + 新输入
            self.activation[agent_id] = 0.7 * self.activation[agent_id] + 0.3 * new_level

            # 限制在[0, 1]
            self.activation[agent_id] = max(0.0, min(1.0, self.activation[agent_id]))


    async def _compute_region_activation(
        self,
        agent_id: str,
        stimulus: str,
        context: Dict[str, Any]
    ) -> float:
        """
        计算单个脑区的新激活水平

        模拟: 神经元的膜电位整合
        Input = Σ (相邻区域激活 × 连接权重)
        """
        # 1. 收集来自其他脑区的输入
        inputs = []
        for (source, target), weight in self.connections.items():
            if target == agent_id:
                source_activation = self.activation.get(source, 0.0)
                inputs.append(source_activation * weight)

        # 2. 整合输入
        total_input = sum(inputs) if inputs else 0.0

        # 3. 如果激活超过阈值,调用agent执行功能
        activation_threshold = 0.5
        if total_input > activation_threshold:
            try:
                # 调用agent的功能
                await self._activate_agent(agent_id, stimulus, context, total_input)

                # 返回高激活
                return min(1.0, total_input)
            except Exception as e:
                logger.error(f"Agent {agent_id} activation failed: {e}")
                return self.activation.get(agent_id, 0.0) * 0.9  # 衰减
        else:
            # 激活不足,休眠状态
            return self.activation.get(agent_id, 0.0) * 0.8  # 快速衰减


    async def _activate_agent(
        self,
        agent_id: str,
        stimulus: str,
        context: Dict[str, Any],
        activation_level: float
    ):
        """
        激活单个agent执行其功能

        将agent的输出存入全局工作区(Global Workspace)
        """
        agent = self.agents.get(agent_id)
        if not agent:
            return

        try:
            # 构建agent的上下文
            agent_context = context.copy()
            agent_context['activation_level'] = activation_level
            agent_context['other_regions'] = self.activation.copy()
            agent_context['workspace'] = self.workspace.copy()

            # 🔥 特殊处理 reasoning_validator: 传递完整的推理信息
            if agent_id == 'reasoning_validator':
                # 🧠 按脑区组织记忆，方便推理器定向查询
                memories_raw = context.get('memories', [])
                memories_by_region = {
                    'hippocampus': [],  # 情节记忆 - 事件+时间
                    'temporal': [],     # 语义记忆 - 知识+事实
                    'amygdala': []      # 情绪记忆 - 感受
                }

                for mem in memories_raw:
                    region = mem.get('region', 'temporal')
                    if region in memories_by_region:
                        memories_by_region[region].append(mem['content'])

                message = AgentMessage(
                    sender='brain_network',
                    receiver=agent_id,
                    message_type='request',
                    content={
                        'action': 'validate_reasoning',
                        'query': stimulus,
                        'memories': memories_raw,  # 保留原始格式兼容
                        'memories_by_region': memories_by_region,  # 🔥 新增：按脑区组织
                        'question_type': context.get('question_type', 'general'),
                        'hippocampus_agent': None  # BrainNetwork内不使用双向反馈
                    }
                )
            else:
                # 其他agent: 使用默认activation消息
                message = AgentMessage(
                    sender='brain_network',
                    receiver=agent_id,
                    message_type='activation',
                    content={
                        'stimulus': stimulus,
                        'context': agent_context
                    }
                )

            result = await agent.process_message(message)

            # 存入全局工作区
            self.workspace[agent_id] = {
                'output': result,
                'activation': activation_level,
                'timestamp': datetime.now()
            }

        except Exception as e:
            logger.error(f"Agent {agent_id} execution error: {e}")


    def _is_converged(self, threshold: float = 0.8) -> bool:
        """
        检查是否收敛: 关键脑区激活稳定

        模拟: 大脑达到一致状态(多个区域激活稳定且高)

        收敛条件:
        - Reasoning (前额叶) 高激活 > 0.8
        - Conversation (语言区) 高激活 > 0.7
        - 两者的输出都已产生
        """
        # 检查关键脑区激活
        reasoning_active = self.activation.get('reasoning_validator', 0.0) > threshold
        conversation_active = self.activation.get('conversation', 0.0) > (threshold - 0.1)

        # 检查是否有输出
        has_reasoning_output = 'reasoning_validator' in self.workspace
        has_conversation_output = 'conversation' in self.workspace

        converged = (
            reasoning_active and conversation_active and
            has_reasoning_output and has_conversation_output
        )

        if converged:
            logger.info(f"🎯 Convergence detected: reasoning={self.activation.get('reasoning_validator', 0):.2f}, conversation={self.activation.get('conversation', 0):.2f}")

        return converged


    async def _extract_consensus(self) -> Dict[str, Any]:
        """
        🔥 NEW: 使用CollaborativeOutput生成协同答案

        从全局工作区提取共识答案 - 多脑区协作生成
        """
        # 从context中提取query和memories
        query = self.workspace.get('query', '')
        memories = self.workspace.get('memories', [])

        # 使用CollaborativeOutput生成答案
        try:
            collab_answer = await self.collaborative_output.generate_answer(
                query=query,
                memories=memories,
                workspace=self.workspace
            )

            logger.info(f"✨ Collaborative answer from {len(collab_answer.contributing_regions)} regions")
            return {
                'response': collab_answer.content,
                'confidence': collab_answer.confidence,
                'reasoning_chain': [collab_answer.reasoning],
                'source': 'collaborative_output',
                'contributing_regions': collab_answer.contributing_regions,
                'answer_type': collab_answer.answer_type.value
            }

        except Exception as e:
            logger.error(f"Collaborative output failed: {e}, falling back to old method")
            import traceback
            logger.error(traceback.format_exc())

            # Fallback: 使用旧方法
            # 优先使用Reasoning Validator的推理结果
            if 'reasoning_validator' in self.workspace:
                reasoning_output = self.workspace['reasoning_validator']['output']

                # 如果有高置信度推理结果,直接使用
                if isinstance(reasoning_output, dict) and reasoning_output.get('confidence', 0) >= 0.7:
                    logger.info("✨ Using Reasoning Validator output (high confidence)")
                    return {
                        'response': reasoning_output.get('answer', reasoning_output.get('response', '')),
                        'confidence': reasoning_output.get('confidence', 0.0),
                        'reasoning_chain': reasoning_output.get('reasoning_chain', []),
                        'source': 'reasoning_validator'
                    }

            # 次选: Conversation Agent的输出
            if 'conversation' in self.workspace:
                conv_output = self.workspace['conversation']['output']
                logger.info("💬 Using Conversation output")

                if isinstance(conv_output, dict):
                    return {
                        'response': conv_output.get('response', str(conv_output)),
                        'confidence': conv_output.get('confidence', 0.6),
                        'reasoning_chain': [],
                    'source': 'conversation'
                }
            else:
                return {
                    'response': str(conv_output),
                    'confidence': 0.5,
                    'reasoning_chain': [],
                    'source': 'conversation'
                }

        # 最后兜底: Executive Control
        if 'executive_control' in self.workspace:
            exec_output = self.workspace['executive_control']['output']
            logger.info("⚙️ Using Executive Control output")
            return {
                'response': str(exec_output),
                'confidence': 0.3,
                'reasoning_chain': [],
                'source': 'executive_control'
            }

        # 如果都没有,尝试从query生成友好回复 (使用detected_language)
        logger.warning("⚠️ No consensus reached, generating friendly response")

        # 从workspace获取语言信息
        detected_language = self.workspace.get('detected_language', 'en')
        query = self.workspace.get('query', '')

        # 根据语言生成友好回复
        if detected_language == 'zh':
            friendly_response = f"抱歉,我暂时没有足够的信息来回答这个问题。您可以提供更多背景信息吗?"
        else:
            friendly_response = "I don't have enough information to answer that question yet. Could you provide more context?"

        return {
            'response': friendly_response,
            'confidence': 0.0,
            'reasoning_chain': [],
            'source': 'default'
        }


    def _get_top_activated(self, k: int = 3) -> List[Tuple[str, float]]:
        """返回激活最高的k个脑区"""
        sorted_activation = sorted(
            self.activation.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_activation[:k]


    def get_activation_summary(self) -> Dict[str, Any]:
        """获取当前激活状态摘要"""
        return {
            'total_regions': self.n_agents,
            'active_regions': sum(1 for v in self.activation.values() if v > 0.5),
            'top_3_activated': self._get_top_activated(3),
            'workspace_size': len(self.workspace),
            'total_connections': len(self.connections)
        }
