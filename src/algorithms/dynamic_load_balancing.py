#!/usr/bin/env python3
"""
动态负载均衡算法 (Dynamic Load Balancing Algorithm)
为多智能体协作系统设计的智能负载均衡机制

核心创新:
1. 自适应权重分配算法 (Adaptive Weight Assignment)
2. 预测性负载调度 (Predictive Load Scheduling) 
3. 多目标优化均衡策略 (Multi-Objective Optimization Balancing)
4. 实时性能监控与调整 (Real-time Performance Monitoring)
5. 故障转移与自愈机制 (Fault Tolerance and Self-Healing)

理论基础:
- 排队论与随机过程
- 多目标优化理论
- 机器学习预测模型
- 分布式系统理论

Copyright (c) 2024 Advanced AI Research Lab
"""

import asyncio
import numpy as np
import heapq
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set, Any, Union, Callable
from collections import defaultdict, deque
import logging
import time
import json
import threading
from concurrent.futures import ThreadPoolExecutor
import math
from scipy import optimize
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
import hashlib


class LoadBalancingStrategy(Enum):
    """负载均衡策略枚举"""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    ADAPTIVE_WEIGHTED = "adaptive_weighted"
    PREDICTIVE_SCHEDULING = "predictive_scheduling"
    MULTI_OBJECTIVE_OPTIMIZATION = "multi_objective_optimization"
    CAPABILITY_BASED = "capability_based"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5


class AgentStatus(Enum):
    """智能体状态"""
    IDLE = "idle"
    BUSY = "busy"
    OVERLOADED = "overloaded"
    UNAVAILABLE = "unavailable"
    MAINTENANCE = "maintenance"


@dataclass
class Task:
    """任务数据结构"""
    task_id: str
    task_type: str
    priority: TaskPriority
    estimated_duration: float
    required_capabilities: Set[str]
    resource_requirements: Dict[str, float]
    deadline: Optional[float] = None
    dependencies: Set[str] = field(default_factory=set)
    complexity_score: float = 1.0
    creation_time: float = field(default_factory=time.time)
    
    def __post_init__(self):
        if not self.task_id:
            self.task_id = self._generate_id()
    
    def _generate_id(self) -> str:
        """生成任务ID"""
        content_hash = hashlib.md5(f"{self.task_type}_{self.creation_time}".encode()).hexdigest()[:8]
        return f"task_{content_hash}_{int(self.creation_time)}"


@dataclass
class AgentPerformanceMetrics:
    """智能体性能指标"""
    agent_id: str
    current_load: float = 0.0
    max_capacity: float = 100.0
    average_response_time: float = 0.0
    success_rate: float = 1.0
    throughput: float = 0.0
    error_rate: float = 0.0
    last_update: float = field(default_factory=time.time)
    
    # 历史性能数据
    response_time_history: deque = field(default_factory=lambda: deque(maxlen=100))
    load_history: deque = field(default_factory=lambda: deque(maxlen=100))
    throughput_history: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def update_metrics(self, response_time: float, success: bool, load: float):
        """更新性能指标"""
        self.response_time_history.append(response_time)
        self.load_history.append(load)
        self.current_load = load
        
        # 更新平均响应时间
        if self.response_time_history:
            self.average_response_time = np.mean(list(self.response_time_history))
        
        # 更新成功率
        recent_successes = [1 if s else 0 for s in list(self.response_time_history)[-20:]]
        if recent_successes:
            self.success_rate = np.mean(recent_successes)
        
        # 更新吞吐量
        if len(self.response_time_history) > 1:
            time_window = 60.0  # 1分钟窗口
            recent_tasks = len([t for t in self.response_time_history if time.time() - t < time_window])
            self.throughput = recent_tasks / time_window
            self.throughput_history.append(self.throughput)
        
        self.last_update = time.time()


@dataclass
class LoadBalancingDecision:
    """负载均衡决策"""
    selected_agent: str
    decision_confidence: float
    estimated_completion_time: float
    load_distribution: Dict[str, float]
    decision_metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class LoadPredictor:
    """负载预测器"""
    
    def __init__(self, prediction_window: int = 60):
        self.prediction_window = prediction_window
        self.models = {}
        self.feature_history = defaultdict(list)
        self.prediction_accuracy = defaultdict(list)
    
    async def predict_agent_load(self, 
                                agent_id: str,
                                historical_metrics: AgentPerformanceMetrics,
                                upcoming_tasks: List[Task]) -> float:
        """预测智能体负载"""
        # 准备特征
        features = self._extract_features(historical_metrics, upcoming_tasks)
        
        # 获取或创建模型
        if agent_id not in self.models:
            self.models[agent_id] = self._create_prediction_model()
        
        model = self.models[agent_id]
        
        # 如果有足够的历史数据，进行预测
        if len(self.feature_history[agent_id]) > 10:
            predicted_load = model.predict([features])[0]
        else:
            # 使用启发式方法
            predicted_load = self._heuristic_prediction(historical_metrics, upcoming_tasks)
        
        # 记录特征用于模型训练
        self.feature_history[agent_id].append(features)
        if len(self.feature_history[agent_id]) > 1000:
            self.feature_history[agent_id] = self.feature_history[agent_id][-500:]
        
        return max(0.0, min(1.0, predicted_load))
    
    def _extract_features(self, 
                         metrics: AgentPerformanceMetrics,
                         upcoming_tasks: List[Task]) -> List[float]:
        """提取特征"""
        features = []
        
        # 当前性能特征
        features.extend([
            metrics.current_load,
            metrics.average_response_time,
            metrics.success_rate,
            metrics.throughput,
            metrics.error_rate
        ])
        
        # 历史趋势特征
        if len(metrics.load_history) > 1:
            load_trend = np.polyfit(range(len(metrics.load_history)), 
                                  list(metrics.load_history), 1)[0]
            features.append(load_trend)
        else:
            features.append(0.0)
        
        if len(metrics.response_time_history) > 1:
            response_time_trend = np.polyfit(range(len(metrics.response_time_history)), 
                                           list(metrics.response_time_history), 1)[0]
            features.append(response_time_trend)
        else:
            features.append(0.0)
        
        # 即将到来的任务特征
        if upcoming_tasks:
            total_estimated_duration = sum(task.estimated_duration for task in upcoming_tasks)
            avg_complexity = np.mean([task.complexity_score for task in upcoming_tasks])
            high_priority_count = sum(1 for task in upcoming_tasks 
                                    if task.priority.value >= TaskPriority.HIGH.value)
        else:
            total_estimated_duration = 0.0
            avg_complexity = 0.0
            high_priority_count = 0
        
        features.extend([
            len(upcoming_tasks),
            total_estimated_duration,
            avg_complexity,
            high_priority_count
        ])
        
        # 时间特征
        current_hour = time.localtime().tm_hour
        features.extend([
            math.sin(2 * math.pi * current_hour / 24),  # 小时的周期性表示
            math.cos(2 * math.pi * current_hour / 24)
        ])
        
        return features
    
    def _create_prediction_model(self):
        """创建预测模型"""
        # 使用随机森林回归器
        return RandomForestRegressor(n_estimators=50, max_depth=10, random_state=42)
    
    def _heuristic_prediction(self, 
                            metrics: AgentPerformanceMetrics,
                            upcoming_tasks: List[Task]) -> float:
        """启发式预测"""
        base_load = metrics.current_load
        
        # 基于即将到来的任务调整
        if upcoming_tasks:
            task_load_impact = sum(task.estimated_duration * task.complexity_score 
                                 for task in upcoming_tasks) / 10.0
            base_load += task_load_impact
        
        # 基于历史趋势调整
        if len(metrics.load_history) > 3:
            recent_trend = np.mean(list(metrics.load_history)[-3:]) - np.mean(list(metrics.load_history)[-6:-3])
            base_load += recent_trend * 0.5
        
        return base_load
    
    async def update_model(self, agent_id: str, actual_load: float):
        """更新预测模型"""
        if agent_id not in self.models or len(self.feature_history[agent_id]) < 10:
            return
        
        # 获取最近的特征和实际负载
        features = self.feature_history[agent_id][-10:]
        targets = [actual_load] * len(features)  # 简化处理
        
        # 重新训练模型
        try:
            self.models[agent_id].fit(features, targets)
        except Exception as e:
            logging.warning(f"Failed to update prediction model for {agent_id}: {e}")


class MultiObjectiveOptimizer:
    """多目标优化器"""
    
    def __init__(self):
        self.objectives = {
            'minimize_response_time': 0.3,
            'maximize_throughput': 0.25,
            'minimize_load_variance': 0.2,
            'maximize_resource_utilization': 0.15,
            'minimize_failure_rate': 0.1
        }
    
    async def optimize_assignment(self, 
                                task: Task,
                                available_agents: Dict[str, AgentPerformanceMetrics],
                                predicted_loads: Dict[str, float]) -> Tuple[str, float]:
        """优化任务分配"""
        if not available_agents:
            raise ValueError("No available agents for optimization")
        
        # 计算每个智能体的目标函数值
        agent_scores = {}
        
        for agent_id, metrics in available_agents.items():
            predicted_load = predicted_loads.get(agent_id, metrics.current_load)
            
            # 计算各个目标的值
            objectives_values = self._calculate_objectives(task, metrics, predicted_load)
            
            # 加权组合
            total_score = sum(self.objectives[obj] * value for obj, value in objectives_values.items())
            
            agent_scores[agent_id] = {
                'total_score': total_score,
                'objectives': objectives_values
            }
        
        # 选择最优智能体
        best_agent = max(agent_scores.keys(), key=lambda x: agent_scores[x]['total_score'])
        best_score = agent_scores[best_agent]['total_score']
        
        return best_agent, best_score
    
    def _calculate_objectives(self, 
                            task: Task,
                            metrics: AgentPerformanceMetrics,
                            predicted_load: float) -> Dict[str, float]:
        """计算目标函数值"""
        objectives = {}
        
        # 最小化响应时间 (转换为最大化)
        response_time_score = 1 / (1 + metrics.average_response_time)
        objectives['minimize_response_time'] = response_time_score
        
        # 最大化吞吐量
        throughput_score = min(metrics.throughput / 10.0, 1.0)  # 归一化
        objectives['maximize_throughput'] = throughput_score
        
        # 最小化负载方差 (选择负载较低的智能体)
        load_score = 1 - predicted_load
        objectives['minimize_load_variance'] = load_score
        
        # 最大化资源利用率 (避免过度空闲或过载)
        optimal_load = 0.7  # 最优负载率
        utilization_score = 1 - abs(predicted_load - optimal_load)
        objectives['maximize_resource_utilization'] = max(0, utilization_score)
        
        # 最小化失败率
        failure_score = metrics.success_rate
        objectives['minimize_failure_rate'] = failure_score
        
        return objectives
    
    def update_objective_weights(self, performance_feedback: Dict[str, float]):
        """基于性能反馈更新目标权重"""
        # 简化的权重调整策略
        for objective, current_weight in self.objectives.items():
            if objective in performance_feedback:
                feedback = performance_feedback[objective]
                # 如果目标表现良好，略微增加权重
                if feedback > 0.8:
                    self.objectives[objective] = min(current_weight * 1.05, 0.5)
                # 如果目标表现不佳，略微降低权重
                elif feedback < 0.5:
                    self.objectives[objective] = max(current_weight * 0.95, 0.05)
        
        # 重新归一化权重
        total_weight = sum(self.objectives.values())
        for objective in self.objectives:
            self.objectives[objective] /= total_weight


class LoadBalancer(ABC):
    """负载均衡器抽象基类"""
    
    def __init__(self, strategy_name: str):
        self.strategy_name = strategy_name
        self.assignment_history = []
        self.performance_metrics = defaultdict(list)
    
    @abstractmethod
    async def select_agent(self, 
                          task: Task,
                          available_agents: Dict[str, AgentPerformanceMetrics]) -> LoadBalancingDecision:
        """选择智能体"""
        pass
    
    def record_assignment(self, decision: LoadBalancingDecision, actual_performance: Dict[str, float]):
        """记录分配决策和实际性能"""
        assignment_record = {
            'timestamp': decision.timestamp,
            'selected_agent': decision.selected_agent,
            'decision_confidence': decision.decision_confidence,
            'estimated_completion_time': decision.estimated_completion_time,
            'actual_performance': actual_performance
        }
        
        self.assignment_history.append(assignment_record)
        
        # 更新性能指标
        for metric, value in actual_performance.items():
            self.performance_metrics[metric].append(value)


class AdaptiveWeightedLoadBalancer(LoadBalancer):
    """自适应权重负载均衡器"""
    
    def __init__(self):
        super().__init__("adaptive_weighted")
        self.weight_adaptation_rate = 0.1
        self.performance_window = 50
        self.agent_weights = defaultdict(lambda: 1.0)
    
    async def select_agent(self, 
                          task: Task,
                          available_agents: Dict[str, AgentPerformanceMetrics]) -> LoadBalancingDecision:
        """自适应权重选择智能体"""
        if not available_agents:
            raise ValueError("No available agents")
        
        # 更新智能体权重
        self._update_agent_weights(available_agents)
        
        # 计算每个智能体的评分
        agent_scores = {}
        
        for agent_id, metrics in available_agents.items():
            # 基础评分组件
            load_score = 1 - metrics.current_load  # 负载越低评分越高
            response_time_score = 1 / (1 + metrics.average_response_time)
            success_rate_score = metrics.success_rate
            throughput_score = min(metrics.throughput / 5.0, 1.0)
            
            # 能力匹配评分
            capability_score = self._calculate_capability_match(task, agent_id)
            
            # 综合评分
            base_score = (load_score * 0.3 + 
                         response_time_score * 0.25 + 
                         success_rate_score * 0.2 + 
                         throughput_score * 0.15 + 
                         capability_score * 0.1)
            
            # 应用自适应权重
            weighted_score = base_score * self.agent_weights[agent_id]
            
            agent_scores[agent_id] = {
                'weighted_score': weighted_score,
                'base_score': base_score,
                'components': {
                    'load_score': load_score,
                    'response_time_score': response_time_score,
                    'success_rate_score': success_rate_score,
                    'throughput_score': throughput_score,
                    'capability_score': capability_score
                }
            }
        
        # 选择最高评分的智能体
        best_agent = max(agent_scores.keys(), key=lambda x: agent_scores[x]['weighted_score'])
        best_score = agent_scores[best_agent]['weighted_score']
        
        # 估算完成时间
        estimated_completion_time = task.estimated_duration / max(best_score, 0.1)
        
        # 计算负载分布
        current_loads = {agent_id: metrics.current_load for agent_id, metrics in available_agents.items()}
        
        decision = LoadBalancingDecision(
            selected_agent=best_agent,
            decision_confidence=best_score,
            estimated_completion_time=estimated_completion_time,
            load_distribution=current_loads,
            decision_metadata={
                'strategy': 'adaptive_weighted',
                'agent_scores': agent_scores,
                'agent_weights': dict(self.agent_weights)
            }
        )
        
        return decision
    
    def _update_agent_weights(self, available_agents: Dict[str, AgentPerformanceMetrics]):
        """更新智能体权重"""
        # 基于最近的性能表现调整权重
        for agent_id, metrics in available_agents.items():
            recent_assignments = [record for record in self.assignment_history[-self.performance_window:]
                                if record['selected_agent'] == agent_id]
            
            if recent_assignments:
                # 计算平均性能
                avg_actual_time = np.mean([r['actual_performance'].get('completion_time', 0) 
                                         for r in recent_assignments])
                avg_estimated_time = np.mean([r['estimated_completion_time'] 
                                            for r in recent_assignments])
                
                # 权重调整基于预测准确性和实际性能
                if avg_estimated_time > 0:
                    accuracy_ratio = min(avg_estimated_time / max(avg_actual_time, 0.1), 2.0)
                    
                    if accuracy_ratio > 1.2:  # 实际表现超出预期
                        self.agent_weights[agent_id] *= (1 + self.weight_adaptation_rate)
                    elif accuracy_ratio < 0.8:  # 实际表现低于预期
                        self.agent_weights[agent_id] *= (1 - self.weight_adaptation_rate)
                
                # 限制权重范围
                self.agent_weights[agent_id] = max(0.1, min(2.0, self.agent_weights[agent_id]))
    
    def _calculate_capability_match(self, task: Task, agent_id: str) -> float:
        """计算能力匹配度"""
        # 简化的能力匹配计算
        # 在实际实现中，这应该基于智能体的实际能力配置
        
        # 基于任务类型的匹配度
        task_type_preferences = {
            'condition_extraction': {'agent_001': 0.9, 'agent_002': 0.7, 'agent_003': 0.8},
            'memory_retrieval': {'agent_001': 0.8, 'agent_002': 0.9, 'agent_003': 0.7},
            'conflict_resolution': {'agent_001': 0.7, 'agent_002': 0.8, 'agent_003': 0.9},
        }
        
        return task_type_preferences.get(task.task_type, {}).get(agent_id, 0.5)


class PredictiveLoadBalancer(LoadBalancer):
    """预测性负载均衡器"""
    
    def __init__(self):
        super().__init__("predictive")
        self.load_predictor = LoadPredictor()
        self.task_queue = deque()
        self.prediction_horizon = 300  # 5分钟预测窗口
    
    async def select_agent(self, 
                          task: Task,
                          available_agents: Dict[str, AgentPerformanceMetrics]) -> LoadBalancingDecision:
        """基于预测的智能体选择"""
        if not available_agents:
            raise ValueError("No available agents")
        
        # 获取即将到来的任务
        upcoming_tasks = list(self.task_queue)
        
        # 预测每个智能体的未来负载
        predicted_loads = {}
        for agent_id, metrics in available_agents.items():
            predicted_load = await self.load_predictor.predict_agent_load(
                agent_id, metrics, upcoming_tasks
            )
            predicted_loads[agent_id] = predicted_load
        
        # 基于预测负载选择最优智能体
        best_agent = None
        best_score = float('-inf')
        
        for agent_id, predicted_load in predicted_loads.items():
            metrics = available_agents[agent_id]
            
            # 综合评分考虑当前和预测负载
            current_score = 1 - metrics.current_load
            predicted_score = 1 - predicted_load
            response_time_score = 1 / (1 + metrics.average_response_time)
            reliability_score = metrics.success_rate
            
            # 权重组合
            total_score = (current_score * 0.3 + 
                          predicted_score * 0.4 + 
                          response_time_score * 0.2 + 
                          reliability_score * 0.1)
            
            if total_score > best_score:
                best_score = total_score
                best_agent = agent_id
        
        # 估算完成时间
        selected_metrics = available_agents[best_agent]
        estimated_completion_time = (task.estimated_duration * 
                                   (1 + predicted_loads[best_agent]) * 
                                   (1 + selected_metrics.average_response_time / 10))
        
        decision = LoadBalancingDecision(
            selected_agent=best_agent,
            decision_confidence=best_score,
            estimated_completion_time=estimated_completion_time,
            load_distribution=predicted_loads,
            decision_metadata={
                'strategy': 'predictive',
                'predicted_loads': predicted_loads,
                'upcoming_tasks_count': len(upcoming_tasks)
            }
        )
        
        return decision
    
    def add_upcoming_task(self, task: Task):
        """添加即将到来的任务"""
        self.task_queue.append(task)
        
        # 保持队列在合理大小
        if len(self.task_queue) > 100:
            self.task_queue.popleft()
    
    async def update_predictions(self, agent_id: str, actual_load: float):
        """更新预测模型"""
        await self.load_predictor.update_model(agent_id, actual_load)


class MultiObjectiveLoadBalancer(LoadBalancer):
    """多目标优化负载均衡器"""
    
    def __init__(self):
        super().__init__("multi_objective")
        self.optimizer = MultiObjectiveOptimizer()
        self.load_predictor = LoadPredictor()
    
    async def select_agent(self, 
                          task: Task,
                          available_agents: Dict[str, AgentPerformanceMetrics]) -> LoadBalancingDecision:
        """多目标优化智能体选择"""
        if not available_agents:
            raise ValueError("No available agents")
        
        # 预测负载
        predicted_loads = {}
        for agent_id, metrics in available_agents.items():
            predicted_load = await self.load_predictor.predict_agent_load(
                agent_id, metrics, []
            )
            predicted_loads[agent_id] = predicted_load
        
        # 多目标优化选择
        best_agent, optimization_score = await self.optimizer.optimize_assignment(
            task, available_agents, predicted_loads
        )
        
        # 估算完成时间
        selected_metrics = available_agents[best_agent]
        estimated_completion_time = task.estimated_duration * (1 + predicted_loads[best_agent])
        
        decision = LoadBalancingDecision(
            selected_agent=best_agent,
            decision_confidence=optimization_score,
            estimated_completion_time=estimated_completion_time,
            load_distribution=predicted_loads,
            decision_metadata={
                'strategy': 'multi_objective',
                'optimization_score': optimization_score,
                'objective_weights': self.optimizer.objectives
            }
        )
        
        return decision


class DynamicLoadBalancingManager:
    """动态负载均衡管理器"""
    
    def __init__(self):
        self.load_balancers = {
            LoadBalancingStrategy.ADAPTIVE_WEIGHTED: AdaptiveWeightedLoadBalancer(),
            LoadBalancingStrategy.PREDICTIVE_SCHEDULING: PredictiveLoadBalancer(),
            LoadBalancingStrategy.MULTI_OBJECTIVE_OPTIMIZATION: MultiObjectiveLoadBalancer(),
        }
        
        self.agent_metrics: Dict[str, AgentPerformanceMetrics] = {}
        self.current_strategy = LoadBalancingStrategy.ADAPTIVE_WEIGHTED
        self.strategy_performance = defaultdict(list)
        self.task_queue = asyncio.Queue()
        self.running = False
        
        # 性能监控
        self.monitoring_interval = 30  # 30秒
        self.strategy_evaluation_window = 100
        
    def register_agent(self, agent_id: str, max_capacity: float = 100.0):
        """注册智能体"""
        self.agent_metrics[agent_id] = AgentPerformanceMetrics(
            agent_id=agent_id,
            max_capacity=max_capacity
        )
        
        logging.info(f"Agent {agent_id} registered with capacity {max_capacity}")
    
    async def submit_task(self, task: Task) -> str:
        """提交任务"""
        await self.task_queue.put(task)
        
        # 如果是预测性负载均衡器，添加到即将到来的任务
        if isinstance(self.load_balancers[self.current_strategy], PredictiveLoadBalancer):
            self.load_balancers[self.current_strategy].add_upcoming_task(task)
        
        return task.task_id
    
    async def assign_task(self, task: Task) -> LoadBalancingDecision:
        """分配任务"""
        # 获取可用智能体
        available_agents = self._get_available_agents()
        
        if not available_agents:
            raise RuntimeError("No available agents for task assignment")
        
        # 使用当前策略选择智能体
        balancer = self.load_balancers[self.current_strategy]
        decision = await balancer.select_agent(task, available_agents)
        
        # 更新智能体负载
        selected_metrics = self.agent_metrics[decision.selected_agent]
        estimated_load_increase = task.complexity_score * 10  # 简化计算
        selected_metrics.current_load = min(
            selected_metrics.current_load + estimated_load_increase,
            selected_metrics.max_capacity
        )
        
        return decision
    
    def _get_available_agents(self) -> Dict[str, AgentPerformanceMetrics]:
        """获取可用智能体"""
        available = {}
        
        for agent_id, metrics in self.agent_metrics.items():
            # 检查智能体是否可用（负载未满且状态正常）
            if (metrics.current_load < metrics.max_capacity * 0.95 and 
                metrics.success_rate > 0.3):  # 基本可用性阈值
                available[agent_id] = metrics
        
        return available
    
    async def update_agent_performance(self, 
                                     agent_id: str,
                                     task_completion_time: float,
                                     task_success: bool,
                                     new_load: float):
        """更新智能体性能"""
        if agent_id in self.agent_metrics:
            metrics = self.agent_metrics[agent_id]
            metrics.update_metrics(task_completion_time, task_success, new_load)
            
            # 更新预测模型
            for balancer in self.load_balancers.values():
                if hasattr(balancer, 'load_predictor'):
                    await balancer.load_predictor.update_model(agent_id, new_load)
    
    async def auto_select_strategy(self) -> LoadBalancingStrategy:
        """自动选择最优负载均衡策略"""
        if len(self.strategy_performance) < len(self.load_balancers):
            return self.current_strategy
        
        # 评估各策略的性能
        strategy_scores = {}
        
        for strategy, performance_history in self.strategy_performance.items():
            if len(performance_history) < 10:
                continue
            
            recent_performance = performance_history[-self.strategy_evaluation_window:]
            
            # 计算多个性能指标
            avg_response_time = np.mean([p.get('response_time', 0) for p in recent_performance])
            avg_throughput = np.mean([p.get('throughput', 0) for p in recent_performance])
            avg_success_rate = np.mean([p.get('success_rate', 0) for p in recent_performance])
            load_variance = np.var([p.get('load_distribution_variance', 0) for p in recent_performance])
            
            # 综合评分
            response_time_score = 1 / (1 + avg_response_time)
            throughput_score = min(avg_throughput / 10.0, 1.0)
            success_rate_score = avg_success_rate
            load_balance_score = 1 / (1 + load_variance)
            
            strategy_score = (response_time_score * 0.3 + 
                            throughput_score * 0.25 + 
                            success_rate_score * 0.25 + 
                            load_balance_score * 0.2)
            
            strategy_scores[strategy] = strategy_score
        
        # 选择最佳策略
        if strategy_scores:
            best_strategy = max(strategy_scores.keys(), key=strategy_scores.get)
            
            # 如果新策略明显更好，则切换
            current_score = strategy_scores.get(self.current_strategy, 0)
            best_score = strategy_scores[best_strategy]
            
            if best_score > current_score * 1.1:  # 至少好10%才切换
                logging.info(f"Switching load balancing strategy from {self.current_strategy} to {best_strategy}")
                self.current_strategy = best_strategy
        
        return self.current_strategy
    
    def record_strategy_performance(self, 
                                  strategy: LoadBalancingStrategy,
                                  performance_metrics: Dict[str, float]):
        """记录策略性能"""
        self.strategy_performance[strategy].append(performance_metrics)
        
        # 保持历史记录在合理范围内
        if len(self.strategy_performance[strategy]) > 1000:
            self.strategy_performance[strategy] = self.strategy_performance[strategy][-500:]
    
    async def start_monitoring(self):
        """开始性能监控"""
        self.running = True
        
        while self.running:
            try:
                # 自动选择最优策略
                await self.auto_select_strategy()
                
                # 性能监控和调整
                await self._monitor_and_adjust()
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                logging.error(f"Error in load balancing monitoring: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def _monitor_and_adjust(self):
        """监控和调整"""
        # 检查智能体健康状态
        for agent_id, metrics in self.agent_metrics.items():
            # 检测过载
            if metrics.current_load > metrics.max_capacity * 0.9:
                logging.warning(f"Agent {agent_id} is overloaded: {metrics.current_load}")
            
            # 检测异常
            if metrics.success_rate < 0.5:
                logging.warning(f"Agent {agent_id} has low success rate: {metrics.success_rate}")
        
        # 调整负载均衡参数
        await self._adjust_balancing_parameters()
    
    async def _adjust_balancing_parameters(self):
        """调整负载均衡参数"""
        # 基于系统状态调整参数
        total_load = sum(metrics.current_load for metrics in self.agent_metrics.values())
        avg_load = total_load / max(len(self.agent_metrics), 1)
        
        # 如果系统整体负载过高，调整策略参数
        if avg_load > 80:
            # 更积极的负载均衡
            for balancer in self.load_balancers.values():
                if hasattr(balancer, 'weight_adaptation_rate'):
                    balancer.weight_adaptation_rate = min(balancer.weight_adaptation_rate * 1.1, 0.3)
        elif avg_load < 30:
            # 更保守的负载均衡
            for balancer in self.load_balancers.values():
                if hasattr(balancer, 'weight_adaptation_rate'):
                    balancer.weight_adaptation_rate = max(balancer.weight_adaptation_rate * 0.9, 0.05)
    
    def stop_monitoring(self):
        """停止监控"""
        self.running = False
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status = {
            'current_strategy': self.current_strategy.value,
            'registered_agents': len(self.agent_metrics),
            'agent_status': {},
            'system_load': {},
            'strategy_performance': {}
        }
        
        # 智能体状态
        for agent_id, metrics in self.agent_metrics.items():
            status['agent_status'][agent_id] = {
                'current_load': metrics.current_load,
                'max_capacity': metrics.max_capacity,
                'utilization': metrics.current_load / metrics.max_capacity,
                'average_response_time': metrics.average_response_time,
                'success_rate': metrics.success_rate,
                'throughput': metrics.throughput
            }
        
        # 系统负载
        total_load = sum(metrics.current_load for metrics in self.agent_metrics.values())
        total_capacity = sum(metrics.max_capacity for metrics in self.agent_metrics.values())
        
        status['system_load'] = {
            'total_load': total_load,
            'total_capacity': total_capacity,
            'utilization': total_load / max(total_capacity, 1),
            'available_capacity': total_capacity - total_load
        }
        
        # 策略性能摘要
        for strategy, performance_history in self.strategy_performance.items():
            if performance_history:
                recent_performance = performance_history[-10:]
                status['strategy_performance'][strategy.value] = {
                    'total_executions': len(performance_history),
                    'recent_avg_response_time': np.mean([p.get('response_time', 0) for p in recent_performance]),
                    'recent_avg_success_rate': np.mean([p.get('success_rate', 0) for p in recent_performance])
                }
        
        return status


# 使用示例
async def main():
    """演示动态负载均衡"""
    # 创建负载均衡管理器
    lb_manager = DynamicLoadBalancingManager()
    
    # 注册智能体
    agents = ['agent_001', 'agent_002', 'agent_003']
    for agent_id in agents:
        capacity = np.random.uniform(80, 120)  # 随机容量
        lb_manager.register_agent(agent_id, capacity)
        
        # 初始化一些性能数据
        await lb_manager.update_agent_performance(
            agent_id,
            task_completion_time=np.random.uniform(0.5, 3.0),
            task_success=True,
            new_load=np.random.uniform(10, 40)
        )
    
    print("=== 动态负载均衡演示 ===\n")
    
    # 创建测试任务
    tasks = []
    for i in range(10):
        task = Task(
            task_id="",
            task_type=np.random.choice(['condition_extraction', 'memory_retrieval', 'conflict_resolution']),
            priority=TaskPriority(np.random.randint(1, 6)),
            estimated_duration=np.random.uniform(1, 5),
            required_capabilities={'nlp', 'reasoning'},
            resource_requirements={'cpu': np.random.uniform(0.1, 0.8)},
            complexity_score=np.random.uniform(0.5, 2.0)
        )
        tasks.append(task)
    
    # 测试不同的负载均衡策略
    strategies = [
        LoadBalancingStrategy.ADAPTIVE_WEIGHTED,
        LoadBalancingStrategy.PREDICTIVE_SCHEDULING,
        LoadBalancingStrategy.MULTI_OBJECTIVE_OPTIMIZATION
    ]
    
    for strategy in strategies:
        print(f"--- 测试策略: {strategy.value.upper()} ---")
        lb_manager.current_strategy = strategy
        
        strategy_results = []
        
        for i, task in enumerate(tasks[:5]):  # 测试前5个任务
            try:
                decision = await lb_manager.assign_task(task)
                
                print(f"任务 {i+1}: {task.task_type}")
                print(f"  选择智能体: {decision.selected_agent}")
                print(f"  决策置信度: {decision.decision_confidence:.3f}")
                print(f"  预估完成时间: {decision.estimated_completion_time:.2f}s")
                
                # 模拟任务执行和性能更新
                actual_completion_time = decision.estimated_completion_time * np.random.uniform(0.8, 1.2)
                task_success = np.random.random() > 0.1  # 90%成功率
                
                await lb_manager.update_agent_performance(
                    decision.selected_agent,
                    actual_completion_time,
                    task_success,
                    np.random.uniform(20, 60)  # 新负载
                )
                
                # 记录策略性能
                performance_metrics = {
                    'response_time': actual_completion_time,
                    'success_rate': 1.0 if task_success else 0.0,
                    'throughput': 1.0 / actual_completion_time,
                    'load_distribution_variance': np.var(list(decision.load_distribution.values()))
                }
                
                lb_manager.record_strategy_performance(strategy, performance_metrics)
                strategy_results.append(performance_metrics)
                
            except Exception as e:
                print(f"  错误: {e}")
        
        # 策略性能摘要
        if strategy_results:
            avg_response_time = np.mean([r['response_time'] for r in strategy_results])
            avg_success_rate = np.mean([r['success_rate'] for r in strategy_results])
            avg_throughput = np.mean([r['throughput'] for r in strategy_results])
            
            print(f"\n策略性能摘要:")
            print(f"  平均响应时间: {avg_response_time:.2f}s")
            print(f"  平均成功率: {avg_success_rate:.2%}")
            print(f"  平均吞吐量: {avg_throughput:.2f} tasks/s")
        
        print()
    
    # 自动选择最优策略
    best_strategy = await lb_manager.auto_select_strategy()
    print(f"自动选择的最优策略: {best_strategy.value}")
    
    # 获取系统状态
    system_status = lb_manager.get_system_status()
    print("\n=== 系统状态 ===")
    print(json.dumps(system_status, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())