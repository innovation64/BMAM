"""
Environment Agent - 环境智能体
Phase 4: 增强环境Agent (状态/奖励/反馈)

Main Functions:
1. State Management - 状态管理 (track environment state changes)
2. Reward System - 奖励系统 (provide reward signals for learning)
3. Feedback Mechanism - 反馈机制 (feedback for agent performance)
4. Context Awareness - 上下文感知 (understand current context)

Design Philosophy:
- Acts as the interface between the agent system and external environment
- Provides reward signals that modulate memory importance
- Tracks state transitions for episodic memory encoding
- Delivers feedback for learning and adaptation
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid
import asyncio

from ..base import BrainAgent, AgentMessage, BrainRegion
from .data_sources import (
    DataSource, DataSourceType, DataSourcePriority,
    ExplorationQuery, ExplorationResult,
    MockDataSource, WebSearchDataSource, KnowledgeBaseDataSource,
    DataSourceRegistry, data_source_registry, initialize_default_sources
)

logger = logging.getLogger(__name__)


class StateType(Enum):
    """环境状态类型"""
    CONVERSATION = "conversation"  # 对话状态
    TASK_EXECUTION = "task_execution"  # 任务执行
    LEARNING = "learning"  # 学习状态
    IDLE = "idle"  # 空闲状态
    ERROR = "error"  # 错误状态


class RewardType(Enum):
    """奖励类型"""
    POSITIVE = "positive"  # 正向奖励 (成功、正确)
    NEGATIVE = "negative"  # 负向奖励 (失败、错误)
    NEUTRAL = "neutral"  # 中性 (无明确反馈)


@dataclass
class EnvironmentState:
    """环境状态"""
    state_id: str
    state_type: StateType
    timestamp: datetime
    context: Dict[str, Any]  # 上下文信息
    previous_state_id: Optional[str] = None
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RewardSignal:
    """奖励信号"""
    reward_id: str
    reward_type: RewardType
    reward_value: float  # -1.0 to 1.0
    reason: str  # 奖励原因
    timestamp: datetime
    associated_memory_id: Optional[str] = None  # 关联的记忆ID
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeedbackEvent:
    """反馈事件"""
    feedback_id: str
    feedback_type: str  # "correction", "reinforcement", "suggestion"
    content: str  # 反馈内容
    timestamp: datetime
    target_agent: Optional[str] = None  # 目标智能体
    severity: str = "info"  # "info", "warning", "error"
    metadata: Dict[str, Any] = field(default_factory=dict)


class EnvironmentAgent(BrainAgent):
    """
    环境智能体 - 管理环境状态、奖励和反馈

    Responsibilities:
    1. Track environment state transitions
    2. Generate reward signals based on outcomes
    3. Provide feedback for learning
    4. Maintain context awareness
    5. Interface with external systems
    """

    def __init__(self, brain_coordinator=None, client=None, data_source_config: Optional[Dict[str, Any]] = None):
        super().__init__(
            agent_id="environment",
            brain_region=BrainRegion.PREFRONTAL,  # 环境感知涉及多个区域,归类为前额叶
            system_prompt="""You are the Environment agent, responsible for managing environment state, rewards, and feedback.
            You track state transitions, generate reward signals for learning, and provide feedback for agent improvement.
            You act as the interface between the internal brain system and the external world.""",
            client=client
        )

        # Brain coordinator reference
        self.brain_coordinator = brain_coordinator

        # State management
        self.current_state: Optional[EnvironmentState] = None
        self.state_history: List[EnvironmentState] = []
        self.max_history_length = 1000

        # Reward system
        self.reward_history: List[RewardSignal] = []
        self.cumulative_reward = 0.0
        self.reward_window = timedelta(hours=1)  # 1小时内的奖励窗口

        # Feedback system
        self.feedback_history: List[FeedbackEvent] = []
        self.pending_feedback: List[FeedbackEvent] = []

        # Statistics
        self.total_state_transitions = 0
        self.total_rewards_issued = 0
        self.total_feedback_issued = 0

        # 🔥 External Data Sources (Phase 4 Enhancement)
        self.data_source_registry = data_source_registry
        self.exploration_count = 0

        # Initialize data sources
        initialize_default_sources(config=data_source_config)


    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """处理消息"""
        action = message.content.get('action')

        # State management actions
        if action == 'update_state':
            return await self.update_state(
                state_type=StateType(message.content['state_type']),
                context=message.content.get('context', {})
            )

        elif action == 'get_current_state':
            return self.get_current_state()

        # Reward system actions
        elif action == 'issue_reward':
            return await self.issue_reward(
                reward_type=RewardType(message.content['reward_type']),
                reward_value=message.content['reward_value'],
                reason=message.content['reason'],
                associated_memory_id=message.content.get('associated_memory_id')
            )

        elif action == 'get_recent_rewards':
            return self.get_recent_rewards(
                time_window_seconds=message.content.get('time_window_seconds', 3600)
            )

        # Feedback system actions
        elif action == 'provide_feedback':
            return await self.provide_feedback(
                feedback_type=message.content['feedback_type'],
                content=message.content['content'],
                target_agent=message.content.get('target_agent'),
                severity=message.content.get('severity', 'info')
            )

        elif action == 'get_pending_feedback':
            return self.get_pending_feedback()

        # Statistics
        elif action == 'get_statistics':
            return self.get_statistics()

        return {'error': f'Unknown action: {action}'}

    # ==================== State Management ====================

    async def update_state(
        self,
        state_type: StateType,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新环境状态

        Args:
            state_type: 状态类型
            context: 上下文信息

        Returns:
            {'state_id': str, 'transition': bool}
        """
        # Calculate duration of previous state
        previous_state_id = None
        duration = 0.0

        if self.current_state:
            previous_state_id = self.current_state.state_id
            duration = (datetime.now() - self.current_state.timestamp).total_seconds()
            self.current_state.duration_seconds = duration

            # Archive to history
            self.state_history.append(self.current_state)

            # Trim history if needed
            if len(self.state_history) > self.max_history_length:
                self.state_history = self.state_history[-self.max_history_length:]

        # Create new state
        new_state = EnvironmentState(
            state_id=uuid.uuid4().hex,
            state_type=state_type,
            timestamp=datetime.now(),
            context=context,
            previous_state_id=previous_state_id
        )

        # Update current state
        old_state_type = self.current_state.state_type if self.current_state else None
        self.current_state = new_state
        self.total_state_transitions += 1

        # Log state transition

        # 🔥 Trigger memory encoding for important state transitions
        if state_type != StateType.IDLE and self.brain_coordinator:
            await self._encode_state_transition_to_memory(new_state, old_state_type)

        return {
            'state_id': new_state.state_id,
            'transition': True,
            'previous_state': old_state_type.value if old_state_type else None,
            'current_state': state_type.value,
            'duration_previous': duration
        }

    async def _encode_state_transition_to_memory(
        self,
        new_state: EnvironmentState,
        old_state_type: Optional[StateType]
    ):
        """
        将重要的状态转换编码到记忆中 (Phase 4 功能)

        Args:
            new_state: 新状态
            old_state_type: 旧状态类型
        """
        try:
            # Store state transition in Hippocampus as episodic memory
            if hasattr(self.brain_coordinator, 'hippocampus'):
                hippocampus = self.brain_coordinator.hippocampus

                # Create memory content
                if old_state_type:
                    content = f"State transition: {old_state_type.value} → {new_state.state_type.value}"
                else:
                    content = f"Initial state: {new_state.state_type.value}"

                # Add context details
                if new_state.context:
                    context_str = ", ".join([f"{k}={v}" for k, v in list(new_state.context.items())[:3]])
                    content += f" ({context_str})"

                # Determine importance based on state type
                importance_map = {
                    StateType.TASK_EXECUTION: 0.7,
                    StateType.LEARNING: 0.8,
                    StateType.ERROR: 0.9,
                    StateType.CONVERSATION: 0.5,
                    StateType.IDLE: 0.2
                }
                importance = importance_map.get(new_state.state_type, 0.5)

                # Store in Hippocampus
                await hippocampus.store_memory(
                    content=content,
                    entities=[new_state.state_type.value],
                    importance=importance,
                    emotion_tags=[],
                    emotion_intensity=0.3,
                    metadata={
                        'state_id': new_state.state_id,
                        'state_type': new_state.state_type.value,
                        'source': 'environment'
                    }
                )


        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            logger.error(f"Failed to encode state transition to memory: {e}")

    def get_current_state(self) -> Dict[str, Any]:
        """获取当前状态"""
        if not self.current_state:
            return {'current_state': None}

        return {
            'state_id': self.current_state.state_id,
            'state_type': self.current_state.state_type.value,
            'timestamp': self.current_state.timestamp.isoformat(),
            'context': self.current_state.context,
            'duration_seconds': (datetime.now() - self.current_state.timestamp).total_seconds()
        }

    # ==================== Reward System ====================

    async def issue_reward(
        self,
        reward_type: RewardType,
        reward_value: float,
        reason: str,
        associated_memory_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        发布奖励信号

        Args:
            reward_type: 奖励类型
            reward_value: 奖励值 (-1.0 to 1.0)
            reason: 奖励原因
            associated_memory_id: 关联的记忆ID

        Returns:
            {'reward_id': str, 'modulation_applied': bool}
        """
        # Clamp reward value
        reward_value = max(-1.0, min(1.0, reward_value))

        # Create reward signal
        reward = RewardSignal(
            reward_id=uuid.uuid4().hex,
            reward_type=reward_type,
            reward_value=reward_value,
            reason=reason,
            timestamp=datetime.now(),
            associated_memory_id=associated_memory_id
        )

        # Store reward
        self.reward_history.append(reward)
        self.cumulative_reward += reward_value
        self.total_rewards_issued += 1

        # Log reward

        # 🔥 Apply reward modulation to memory encoding
        modulation_applied = False
        if associated_memory_id and self.brain_coordinator:
            modulation_applied = await self._apply_reward_modulation(reward, associated_memory_id)

        return {
            'reward_id': reward.reward_id,
            'reward_type': reward_type.value,
            'reward_value': reward_value,
            'cumulative_reward': self.cumulative_reward,
            'modulation_applied': modulation_applied
        }

    async def _apply_reward_modulation(
        self,
        reward: RewardSignal,
        memory_id: str
    ) -> bool:
        """
        应用奖励调节到记忆编码 (Phase 4 功能)

        正向奖励 → 增强记忆重要性
        负向奖励 → 降低记忆重要性或标记为需要修正

        Args:
            reward: 奖励信号
            memory_id: 记忆ID

        Returns:
            bool: 是否成功应用调节
        """
        try:
            # Access Amygdala for emotion modulation (reward as emotion)
            if hasattr(self.brain_coordinator, 'amygdala'):
                amygdala = self.brain_coordinator.amygdala

                # Map reward to emotion intensity
                emotion_intensity = abs(reward.reward_value)

                # Map reward type to emotion tags
                emotion_tags = []
                if reward.reward_type == RewardType.POSITIVE:
                    emotion_tags = ["success", "satisfaction"]
                elif reward.reward_type == RewardType.NEGATIVE:
                    emotion_tags = ["failure", "disappointment"]
                else:
                    emotion_tags = ["neutral"]

                # Apply emotion modulation
                modulation_result = await amygdala.modulate_memory_encoding(
                    memory_id=memory_id,
                    emotion_intensity=emotion_intensity,
                    emotion_tags=emotion_tags
                )


                return modulation_result.get('modulated', False)

        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            logger.error(f"Failed to apply reward modulation: {e}")
            return False

    def get_recent_rewards(self, time_window_seconds: int = 3600) -> Dict[str, Any]:
        """
        获取最近的奖励信号

        Args:
            time_window_seconds: 时间窗口（秒）

        Returns:
            {'rewards': List[Dict], 'average_reward': float, 'count': int}
        """
        cutoff_time = datetime.now() - timedelta(seconds=time_window_seconds)

        recent_rewards = [
            r for r in self.reward_history
            if r.timestamp >= cutoff_time
        ]

        # Calculate average
        avg_reward = 0.0
        if recent_rewards:
            avg_reward = sum(r.reward_value for r in recent_rewards) / len(recent_rewards)

        return {
            'rewards': [
                {
                    'reward_id': r.reward_id,
                    'reward_type': r.reward_type.value,
                    'reward_value': r.reward_value,
                    'reason': r.reason,
                    'timestamp': r.timestamp.isoformat()
                }
                for r in recent_rewards
            ],
            'average_reward': avg_reward,
            'count': len(recent_rewards),
            'time_window_seconds': time_window_seconds
        }

    # ==================== Feedback System ====================

    async def provide_feedback(
        self,
        feedback_type: str,
        content: str,
        target_agent: Optional[str] = None,
        severity: str = "info"
    ) -> Dict[str, Any]:
        """
        提供反馈

        Args:
            feedback_type: 反馈类型 ("correction", "reinforcement", "suggestion")
            content: 反馈内容
            target_agent: 目标智能体
            severity: 严重程度 ("info", "warning", "error")

        Returns:
            {'feedback_id': str, 'delivered': bool}
        """
        # Create feedback event
        feedback = FeedbackEvent(
            feedback_id=uuid.uuid4().hex,
            feedback_type=feedback_type,
            content=content,
            timestamp=datetime.now(),
            target_agent=target_agent,
            severity=severity
        )

        # Store feedback
        self.feedback_history.append(feedback)
        self.pending_feedback.append(feedback)
        self.total_feedback_issued += 1

        # Log feedback

        # 🔥 Deliver feedback to target agent if specified
        delivered = False
        if target_agent and self.brain_coordinator:
            delivered = await self._deliver_feedback_to_agent(feedback, target_agent)

        return {
            'feedback_id': feedback.feedback_id,
            'feedback_type': feedback_type,
            'severity': severity,
            'delivered': delivered
        }

    async def _deliver_feedback_to_agent(
        self,
        feedback: FeedbackEvent,
        target_agent: str
    ) -> bool:
        """
        将反馈传递给目标智能体 (Phase 4 功能)

        Args:
            feedback: 反馈事件
            target_agent: 目标智能体ID

        Returns:
            bool: 是否成功传递
        """
        try:
            if hasattr(self.brain_coordinator, 'agents'):
                agents = self.brain_coordinator.agents

                if target_agent in agents:
                    agent = agents[target_agent]

                    # Send feedback as a message
                    message = AgentMessage(
                        sender='environment',
                        receiver=target_agent,
                        message_type='feedback',
                        content={
                            'feedback_id': feedback.feedback_id,
                            'feedback_type': feedback.feedback_type,
                            'content': feedback.content,
                            'severity': feedback.severity,
                            'timestamp': feedback.timestamp.isoformat()
                        }
                    )

                    # Note: Actual delivery depends on agent's process_message implementation
                    return True

        except (Exception) as e:
            logger.error(f"Failed to deliver feedback to agent: {e}")
            return False

    def get_pending_feedback(self) -> Dict[str, Any]:
        """获取待处理的反馈"""
        feedback_list = [
            {
                'feedback_id': f.feedback_id,
                'feedback_type': f.feedback_type,
                'content': f.content,
                'target_agent': f.target_agent,
                'severity': f.severity,
                'timestamp': f.timestamp.isoformat()
            }
            for f in self.pending_feedback
        ]

        return {
            'pending_feedback': feedback_list,
            'count': len(feedback_list)
        }

    def clear_pending_feedback(self):
        """清空待处理反馈"""
        count = len(self.pending_feedback)
        self.pending_feedback.clear()
        return {'cleared': count}

    # ==================== Statistics & Utilities ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'agent_id': self.agent_id,
            'current_state': self.current_state.state_type.value if self.current_state else None,
            'total_state_transitions': self.total_state_transitions,
            'state_history_length': len(self.state_history),
            'total_rewards_issued': self.total_rewards_issued,
            'cumulative_reward': self.cumulative_reward,
            'reward_history_length': len(self.reward_history),
            'total_feedback_issued': self.total_feedback_issued,
            'pending_feedback_count': len(self.pending_feedback),
            'feedback_history_length': len(self.feedback_history)
        }

    def get_context_summary(self) -> Dict[str, Any]:
        """
        获取当前环境上下文摘要

        用于其他智能体了解当前环境状况
        """
        # Recent rewards
        recent_rewards = self.get_recent_rewards(time_window_seconds=3600)

        # Current state
        current_state_info = self.get_current_state()

        return {
            'current_state': current_state_info,
            'recent_rewards': {
                'average': recent_rewards['average_reward'],
                'count': recent_rewards['count']
            },
            'pending_feedback_count': len(self.pending_feedback),
            'cumulative_reward': self.cumulative_reward
        }

    # ==================== External Exploration (Phase 4 Task 2 - Enhanced) ====================

    async def explore_external(
        self,
        query: str,
        exploration_type: str = "web_search",
        metadata: Optional[Dict[str, Any]] = None,
        source_name: Optional[str] = None,
        max_results: int = 5,
        use_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        外部探索功能 - 从外部数据源获取信息 (支持多数据源)

        当内部记忆检索不足时，触发外部探索

        Args:
            query: 查询内容
            exploration_type: 探索类型 ("web_search", "knowledge_base", "database", "api_service")
            metadata: 额外元数据
            source_name: 指定数据源名称 (None则使用默认或智能选择)
            max_results: 最大结果数量
            use_fallback: 是否在主数据源失败时使用fallback

        Returns:
            {
                'exploration_id': str,
                'query': str,
                'exploration_type': str,
                'results': List[Dict],
                'source': str,
                'source_type': str,
                'timestamp': str,
                'result_count': int,
                'metadata': Dict,
                'duration_ms': float,
                'storage_success': bool
            }
        """
        exploration_id = uuid.uuid4().hex
        start_time = datetime.now()
        self.exploration_count += 1


        # 🎯 Step 1: 选择数据源
        data_source = await self._select_data_source(
            exploration_type=exploration_type,
            source_name=source_name,
            use_fallback=use_fallback
        )

        if not data_source:
            logger.warning("No available data source found")
            return {
                'exploration_id': exploration_id,
                'query': query,
                'exploration_type': exploration_type,
                'results': [],
                'source': 'none',
                'source_type': 'none',
                'timestamp': start_time.isoformat(),
                'result_count': 0,
                'metadata': metadata or {},
                'duration_ms': (datetime.now() - start_time).total_seconds() * 1000,
                'storage_success': False,
                'error': 'No available data source'
            }

        # 🔍 Step 2: 构建查询并执行搜索
        exploration_query = ExplorationQuery(
            query=query,
            max_results=max_results,
            metadata=metadata or {}
        )

        try:
            exploration_results = await data_source.search(exploration_query)

        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            logger.error(f"   ❌ {data_source.source_name} search failed: {e}")
            exploration_results = []

        # 📦 Step 3: 格式化结果
        formatted_results = [result.to_dict() for result in exploration_results]

        # 构建探索结果
        exploration_result = {
            'exploration_id': exploration_id,
            'query': query,
            'exploration_type': exploration_type,
            'results': formatted_results,
            'source': data_source.source_name,
            'source_type': data_source.source_type.value,
            'timestamp': start_time.isoformat(),
            'result_count': len(formatted_results),
            'metadata': metadata or {},
            'duration_ms': (datetime.now() - start_time).total_seconds() * 1000
        }

        # 🔥 Step 4: 写回记忆系统
        storage_success = False
        if self.brain_coordinator and formatted_results:
            storage_success = await self._store_exploration_to_memory(exploration_result)

        exploration_result['storage_success'] = storage_success

        # 📝 Step 5: 记录探索日志
        await self._log_exploration_event(exploration_result, storage_success)


        return exploration_result

    async def _select_data_source(
        self,
        exploration_type: str,
        source_name: Optional[str] = None,
        use_fallback: bool = True
    ) -> Optional[DataSource]:
        """
        智能选择数据源

        策略:
        1. 如果指定了 source_name，直接使用
        2. 否则根据 exploration_type 智能选择
        3. 如果主数据源不可用，使用fallback

        Args:
            exploration_type: 探索类型
            source_name: 指定的数据源名称
            use_fallback: 是否使用fallback

        Returns:
            DataSource实例或None
        """
        # 1. 如果指定了数据源，直接使用
        if source_name:
            source = self.data_source_registry.get_source(source_name)
            if source and source.is_available:
                return source
            else:
                logger.warning(f"   ⚠️ Specified source '{source_name}' not available")

        # 2. 根据 exploration_type 映射到 DataSourceType
        type_mapping = {
            'web_search': DataSourceType.WEB_SEARCH,
            'knowledge_base': DataSourceType.KNOWLEDGE_BASE,
            'database': DataSourceType.DATABASE,
            'api_service': DataSourceType.API_SERVICE,
            'mock': DataSourceType.MOCK
        }

        target_type = type_mapping.get(exploration_type, DataSourceType.MOCK)

        # 3. 查找匹配类型的可用数据源（按优先级排序）
        available_sources = self.data_source_registry.get_available_sources()
        matching_sources = [s for s in available_sources if s.source_type == target_type]

        if matching_sources:
            # 按优先级和成功率排序
            matching_sources.sort(key=lambda s: (s.priority.value, s.get_success_rate()), reverse=True)
            selected = matching_sources[0]
            return selected

        # 4. 如果没有匹配类型的数据源，使用fallback
        if use_fallback:
            default_source = self.data_source_registry.get_default_source()
            if default_source and default_source.is_available:
                return default_source

        logger.warning("   ❌ No suitable data source found")
        return None

    async def get_data_source_statistics(self) -> Dict[str, Any]:
        """
        获取所有数据源的统计信息

        Returns:
            Dict: 包含所有数据源统计的字典
        """
        return self.data_source_registry.get_statistics()

    async def health_check_data_sources(self) -> Dict[str, bool]:
        """
        对所有数据源进行健康检查

        Returns:
            Dict[str, bool]: 数据源名称到健康状态的映射
        """
        return await self.data_source_registry.health_check_all()

    async def _store_exploration_to_memory(
        self,
        exploration_result: Dict[str, Any]
    ) -> bool:
        """
        将外部探索结果存入记忆系统

        存储策略：
        1. 每个探索结果作为独立记忆存入 Hippocampus
        2. 标记来源为 'external_exploration'
        3. 重要性根据相关度动态设置
        """
        try:
            if not hasattr(self.brain_coordinator, 'hippocampus'):
                logger.warning("Hippocampus not available, skipping memory storage")
                return False

            hippocampus = self.brain_coordinator.hippocampus
            stored_count = 0

            for result in exploration_result['results']:
                # 构建记忆内容
                content = f"External exploration result: {result['title']}\n{result['content']}\n[Source: {result['source']}]"

                # 根据相关度设置重要性
                importance = result.get('relevance', 0.7)

                # 存入 Hippocampus
                memory_id = await hippocampus.store_memory(
                    content=content,
                    entities=[exploration_result['query'], result['title']],
                    importance=importance,
                    emotion_tags=['exploration', 'external'],
                    emotion_intensity=0.5,
                    metadata={
                        'exploration_id': exploration_result['exploration_id'],
                        'exploration_type': exploration_result['exploration_type'],
                        'source': result['source'],
                        'original_query': exploration_result['query'],
                        'external_exploration': True
                    }
                )

                if memory_id:
                    stored_count += 1

            return stored_count > 0

        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            logger.error(f"Failed to store exploration results to memory: {e}")
            return False

    async def _log_exploration_event(
        self,
        exploration_result: Dict[str, Any],
        storage_success: bool
    ):
        """
        记录探索事件到日志

        日志格式: JSONL (JSON Lines)
        每行一个JSON对象，便于后续分析

        Args:
            exploration_result: 探索结果
            storage_success: 是否成功存储到记忆
        """
        import json
        from pathlib import Path

        try:
            # 日志路径
            log_dir = Path('logs/exploration')
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / 'external_exploration.jsonl'

            # 构建日志条目
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'event_type': 'external_exploration',
                'exploration_id': exploration_result['exploration_id'],
                'query': exploration_result['query'],
                'exploration_type': exploration_result['exploration_type'],
                'result_count': exploration_result['result_count'],
                'duration_ms': exploration_result['duration_ms'],
                'storage_success': storage_success,
                'metadata': exploration_result.get('metadata', {}),
                'results_summary': [
                    {
                        'title': result.get('title', 'N/A'),
                        'source': result.get('source', 'N/A'),
                        'relevance': result.get('relevance', 0.0)
                    }
                    for result in exploration_result['results']
                ]
            }

            # 写入日志文件 (追加模式)
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')


        except (json.JSONDecodeError) as e:
            logger.error(f"Failed to log exploration event: {e}")
