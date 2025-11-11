"""
Neural Plasticity Engine
神经可塑性引擎 - 整合连接矩阵和突触可塑性，提供统一的可塑性管理
"""

import asyncio
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timedelta
from .connection_matrix import ConnectionMatrix
from .synaptic_plasticity import SynapticPlasticity
from ..utils.config import get_logger

logger = get_logger(__name__)


class NeuralPlasticityEngine:
    """
    神经可塑性引擎 - 类脑学习和适应的核心
    
    整合两个层面的可塑性：
    1. 智能体间连接可塑性 (ConnectionMatrix)
    2. 记忆间关联可塑性 (SynapticPlasticity)
    """
    
    def __init__(self, agents: List[str]):
        self.agents = agents
        
        # 初始化两个可塑性系统
        self.connection_matrix = ConnectionMatrix(agents)
        self.synaptic_plasticity = SynapticPlasticity()
        
        # 学习历史和统计
        self.learning_sessions = []
        self.adaptation_stats = {
            'total_adaptations': 0,
            'connection_updates': 0,
            'memory_associations': 0,
            'routing_optimizations': 0
        }
        
        # 自动维护任务
        self._maintenance_task = None
        self._auto_save_task = None
        
        logger.debug(f"神经可塑性引擎初始化完成，管理 {len(agents)} 个智能体")
    
    async def start_plasticity_engine(self):
        """启动可塑性引擎的后台任务"""
        if self._maintenance_task is None:
            self._maintenance_task = asyncio.create_task(self._maintenance_loop())
        
        if self._auto_save_task is None:
            self._auto_save_task = asyncio.create_task(self._auto_save_loop())
        
        logger.info("神经可塑性引擎后台任务已启动")
    
    async def stop_plasticity_engine(self):
        """停止可塑性引擎的后台任务"""
        if self._maintenance_task:
            self._maintenance_task.cancel()
            self._maintenance_task = None
        
        if self._auto_save_task:
            self._auto_save_task.cancel()
            self._auto_save_task = None
        
        # 最终保存
        self.connection_matrix._save_connections()
        self.synaptic_plasticity._save_plasticity_data()
        
        logger.info("神经可塑性引擎已停止")
    
    def record_agent_activation(self, agents_activated: List[str], 
                              activation_strengths: List[float] = None,
                              context: Dict[str, Any] = None):
        """
        记录智能体激活事件 - 触发连接学习
        
        Args:
            agents_activated: 激活的智能体列表
            activation_strengths: 对应的激活强度
            context: 激活上下文
        """
        if len(agents_activated) < 2:
            return
        
        if activation_strengths is None:
            activation_strengths = [1.0] * len(agents_activated)
        
        # 更新智能体间连接强度
        for i in range(len(agents_activated)):
            for j in range(i + 1, len(agents_activated)):
                agent_a = agents_activated[i]
                agent_b = agents_activated[j]
                strength_combined = (activation_strengths[i] + activation_strengths[j]) / 2
                
                self.connection_matrix.strengthen_connection(agent_a, agent_b, strength_combined)
        
        self.adaptation_stats['connection_updates'] += len(agents_activated) * (len(agents_activated) - 1) // 2
        self.adaptation_stats['total_adaptations'] += 1
        
        logger.debug(f"记录智能体激活: {', '.join(agents_activated)}")
    
    def record_memory_co_activation(self, memory_ids: List[str], 
                                   activation_strengths: List[float] = None,
                                   context: Dict[str, Any] = None):
        """
        记录记忆共激活事件 - 触发突触可塑性
        
        Args:
            memory_ids: 共激活的记忆ID列表
            activation_strengths: 对应的激活强度
            context: 激活上下文
        """
        if len(memory_ids) < 2:
            # 单个记忆激活也要记录
            if memory_ids:
                strength = activation_strengths[0] if activation_strengths else 1.0
                self.synaptic_plasticity.record_memory_activation(memory_ids[0], strength, context)
            return
        
        # 处理记忆间的共激活
        self.synaptic_plasticity.process_co_activation(memory_ids, activation_strengths)
        
        self.adaptation_stats['memory_associations'] += len(memory_ids) * (len(memory_ids) - 1) // 2
        self.adaptation_stats['total_adaptations'] += 1
        
        logger.debug(f"记录记忆共激活: {len(memory_ids)} 个记忆")
    
    def get_optimal_agent_sequence(self, initial_agents: List[str], 
                                  target_count: int = 5,
                                  exclude: List[str] = None) -> List[Tuple[str, float]]:
        """
        基于连接强度获取最优的智能体激活序列
        
        Args:
            initial_agents: 初始激活的智能体
            target_count: 目标智能体数量
            exclude: 要排除的智能体
            
        Returns:
            List of (agent_name, combined_strength)
        """
        return self.connection_matrix.suggest_next_agents(initial_agents, exclude)[:target_count]
    
    def get_associated_memories(self, memory_ids: List[str], 
                              association_threshold: float = 0.2,
                              max_associations: int = 10) -> List[Tuple[str, float]]:
        """
        获取与当前记忆关联的其他记忆
        
        Args:
            memory_ids: 当前记忆ID列表
            association_threshold: 关联强度阈值
            max_associations: 最大关联数量
            
        Returns:
            List of (associated_memory_id, strength)
        """
        all_associations = {}
        
        for memory_id in memory_ids:
            associations = self.synaptic_plasticity.get_associated_memories(
                memory_id, 
                min_strength=association_threshold,
                top_k=max_associations
            )
            
            for assoc_memory, strength in associations:
                if assoc_memory not in memory_ids:  # 排除已有的记忆
                    if assoc_memory not in all_associations:
                        all_associations[assoc_memory] = 0
                    all_associations[assoc_memory] += strength
        
        # 排序并返回
        sorted_associations = sorted(all_associations.items(), key=lambda x: x[1], reverse=True)
        return sorted_associations[:max_associations]
    
    def predict_user_pattern(self, current_agents: List[str], 
                           current_memories: List[str]) -> Dict[str, Any]:
        """
        基于可塑性数据预测用户行为模式
        
        Returns:
            预测结果包含建议的智能体和记忆
        """
        # 预测下一步智能体
        next_agents = self.get_optimal_agent_sequence(current_agents, target_count=3)
        
        # 预测相关记忆
        associated_memories = self.get_associated_memories(current_memories, max_associations=5)
        
        # 预测下一个可能的记忆
        predicted_memories = self.synaptic_plasticity.predict_next_memories(
            current_memories, 
            prediction_strength=0.3
        )
        
        return {
            'suggested_agents': next_agents,
            'associated_memories': associated_memories,
            'predicted_memories': predicted_memories[:5],
            'confidence': self._calculate_prediction_confidence(next_agents, associated_memories)
        }
    
    def optimize_routing_strategy(self, task_type: str, 
                                 historical_performance: Dict[str, float] = None) -> List[str]:
        """
        基于学习历史优化智能体路由策略
        
        Args:
            task_type: 任务类型 (memory_storage, memory_retrieval, conversation, etc.)
            historical_performance: 历史性能数据
            
        Returns:
            优化后的智能体激活顺序
        """
        base_agents = self._get_base_agents_for_task(task_type)
        
        # 获取最强连接的智能体组合
        optimal_sequence = []
        remaining_agents = base_agents.copy()
        
        if remaining_agents:
            # 选择第一个智能体（基于任务类型）
            first_agent = remaining_agents.pop(0)
            optimal_sequence.append(first_agent)
            
            # 基于连接强度选择后续智能体
            while remaining_agents and len(optimal_sequence) < 6:
                suggestions = self.connection_matrix.suggest_next_agents(
                    optimal_sequence, 
                    exclude=[agent for agent in self.agents if agent not in remaining_agents]
                )
                
                if suggestions:
                    next_agent = suggestions[0][0]
                    if next_agent in remaining_agents:
                        optimal_sequence.append(next_agent)
                        remaining_agents.remove(next_agent)
                    else:
                        # 如果建议的智能体不在剩余列表中，选择剩余的第一个
                        if remaining_agents:
                            optimal_sequence.append(remaining_agents.pop(0))
                        break
                else:
                    # 没有建议时，选择剩余的智能体
                    if remaining_agents:
                        optimal_sequence.append(remaining_agents.pop(0))
        
        self.adaptation_stats['routing_optimizations'] += 1
        
        logger.debug(f"为任务 {task_type} 优化路由: {' → '.join(optimal_sequence)}")
        return optimal_sequence
    
    def get_plasticity_insights(self) -> Dict[str, Any]:
        """获取可塑性系统的深度洞察"""
        connection_metrics = self.connection_matrix.get_network_metrics()
        plasticity_stats = self.synaptic_plasticity.get_plasticity_stats()
        
        # 分析学习模式
        learning_velocity = self._calculate_learning_velocity()
        adaptation_patterns = self._analyze_adaptation_patterns()
        
        return {
            'connection_network': connection_metrics,
            'memory_associations': plasticity_stats,
            'learning_velocity': learning_velocity,
            'adaptation_patterns': adaptation_patterns,
            'system_stats': self.adaptation_stats,
            'health_indicators': {
                'network_density': connection_metrics.get('network_density', 0),
                'association_richness': plasticity_stats.get('average_strength', 0),
                'plasticity_activity': self.adaptation_stats['total_adaptations'],
                'learning_efficiency': learning_velocity
            }
        }
    
    def _calculate_prediction_confidence(self, next_agents: List[Tuple[str, float]], 
                                       associated_memories: List[Tuple[str, float]]) -> float:
        """计算预测置信度"""
        if not next_agents and not associated_memories:
            return 0.0
        
        import numpy as np
        agent_confidence = np.mean([strength for _, strength in next_agents]) if next_agents else 0.0
        memory_confidence = np.mean([strength for _, strength in associated_memories]) if associated_memories else 0.0
        
        return (agent_confidence + memory_confidence) / 2
    
    def _get_base_agents_for_task(self, task_type: str) -> List[str]:
        """获取任务类型对应的基础智能体"""
        task_agents = {
            'memory_storage': ['perception_encoding', 'short_term_memory', 'long_term_memory', 'consolidation'],
            'memory_retrieval': ['memory_retrieval', 'short_term_memory', 'reflection', 'conversation'],
            'conversation': ['conversation', 'personality', 'memory_retrieval', 'executive_control'],
            'analysis': ['reflection', 'memory_retrieval', 'consolidation', 'conversation'],
            'emotional_processing': ['stress_response', 'personality', 'memory_distortion', 'consolidation']
        }
        
        return task_agents.get(task_type, ['conversation', 'memory_retrieval', 'executive_control'])
    
    def _calculate_learning_velocity(self) -> float:
        """计算学习速度指标"""
        recent_adaptations = self.adaptation_stats['total_adaptations']
        if recent_adaptations == 0:
            return 0.0
        
        # 简化的学习速度计算
        connection_updates = self.adaptation_stats['connection_updates']
        memory_associations = self.adaptation_stats['memory_associations']
        
        velocity = (connection_updates + memory_associations) / recent_adaptations if recent_adaptations > 0 else 0.0
        return min(velocity / 10, 1.0)  # 归一化到 [0, 1]
    
    def _analyze_adaptation_patterns(self) -> Dict[str, Any]:
        """分析适应模式"""
        strongest_connections = []
        
        # 分析最强的智能体连接
        for agent in self.agents:
            strong_connections = self.connection_matrix.get_strongest_connections(agent, top_k=3)
            if strong_connections:
                strongest_connections.extend([(agent, conn[0], conn[1]) for conn in strong_connections[:1]])
        
        # 排序获取全局最强连接
        strongest_connections.sort(key=lambda x: x[2], reverse=True)
        
        return {
            'dominant_agent_pairs': strongest_connections[:5],
            'adaptation_frequency': self.adaptation_stats['total_adaptations'],
            'plasticity_health': 'active' if self.adaptation_stats['total_adaptations'] > 0 else 'inactive'
        }
    
    async def _maintenance_loop(self):
        """可塑性维护循环 - 模拟大脑的维护机制"""
        while True:
            try:
                await asyncio.sleep(3600)  # 每小时执行一次维护
                
                logger.info("执行神经可塑性维护...")
                
                # 衰减弱连接
                self.connection_matrix.weaken_unused_connections()
                self.synaptic_plasticity.decay_weak_connections()
                
                # 巩固强连接 (模拟睡眠中的记忆巩固)
                self.synaptic_plasticity.consolidate_strong_connections()
                
                logger.info("神经可塑性维护完成")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"可塑性维护出错: {e}")
    
    async def _auto_save_loop(self):
        """自动保存循环"""
        while True:
            try:
                await asyncio.sleep(600)  # 每10分钟保存一次
                
                self.connection_matrix._save_connections()
                self.synaptic_plasticity._save_plasticity_data()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"自动保存出错: {e}")
    
    async def __aenter__(self):
        await self.start_plasticity_engine()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop_plasticity_engine()
