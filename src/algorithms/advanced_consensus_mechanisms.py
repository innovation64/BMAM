#!/usr/bin/env python3
"""
高级共识机制算法 (Advanced Consensus Mechanisms)
为多智能体系统设计的新型共识算法

核心创新:
1. 自适应权重共识算法 (Adaptive Weight Consensus)
2. 置信度传播网络 (Confidence Propagation Network)
3. 分层共识决策树 (Hierarchical Consensus Decision Tree)
4. 动态法定人数调整 (Dynamic Quorum Adjustment)
5. 拜占庭容错增强机制 (Enhanced Byzantine Fault Tolerance)

理论基础:
- 分布式系统理论
- 图神经网络
- 信息论与熵优化
- 博弈论均衡

Copyright (c) 2024 Advanced AI Research Lab
"""

import asyncio
import numpy as np
import networkx as nx
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set, Any, Union, Callable
from collections import defaultdict, deque
import logging
import time
import json
import math
import heapq
from scipy import stats
from scipy.special import softmax
import hashlib


class ConsensusType(Enum):
    """共识类型枚举"""
    SIMPLE_MAJORITY = "simple_majority"
    WEIGHTED_VOTING = "weighted_voting"
    ADAPTIVE_CONSENSUS = "adaptive_consensus"
    CONFIDENCE_PROPAGATION = "confidence_propagation"
    HIERARCHICAL_CONSENSUS = "hierarchical_consensus"
    BYZANTINE_FAULT_TOLERANT = "byzantine_fault_tolerant"
    DYNAMIC_QUORUM = "dynamic_quorum"
    PROBABILISTIC_CONSENSUS = "probabilistic_consensus"


class AgentTrustLevel(Enum):
    """智能体信任级别"""
    UNTRUSTED = 0.0
    LOW_TRUST = 0.3
    MEDIUM_TRUST = 0.6
    HIGH_TRUST = 0.8
    FULL_TRUST = 1.0


@dataclass
class ConsensusProposal:
    """共识提案"""
    proposal_id: str
    proposer_id: str
    proposal_type: str
    content: Dict[str, Any]
    confidence: float
    priority: int = 1
    deadline: Optional[float] = None
    dependencies: Set[str] = field(default_factory=set)
    supporting_evidence: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def __post_init__(self):
        if not self.proposal_id:
            self.proposal_id = self._generate_id()
    
    def _generate_id(self) -> str:
        """生成提案ID"""
        content_hash = hashlib.md5(str(self.content).encode()).hexdigest()[:8]
        return f"proposal_{self.proposer_id}_{content_hash}_{int(self.timestamp)}"


@dataclass
class AgentVote:
    """智能体投票"""
    agent_id: str
    vote_value: float  # 0.0-1.0, 支持程度
    confidence: float  # 投票置信度
    reasoning: str = ""
    vote_weight: float = 1.0
    timestamp: float = field(default_factory=time.time)
    evidence: List[str] = field(default_factory=list)


@dataclass
class ConsensusResult:
    """共识结果"""
    proposal_id: str
    consensus_achieved: bool
    final_decision: Any
    confidence_level: float
    participating_agents: Set[str]
    votes: Dict[str, AgentVote]
    consensus_type: ConsensusType
    execution_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    dissenting_opinions: List[str] = field(default_factory=list)
    consensus_quality_score: float = 0.0


@dataclass
class AgentProfile:
    """智能体档案"""
    agent_id: str
    expertise_domains: Set[str]
    trust_level: AgentTrustLevel
    historical_accuracy: float
    response_time_avg: float
    collaboration_score: float
    reputation_score: float = 0.5
    voting_history: List[Dict] = field(default_factory=list)
    
    def update_reputation(self, outcome_accuracy: float, weight: float = 0.1):
        """更新声誉分数"""
        self.reputation_score = (1 - weight) * self.reputation_score + weight * outcome_accuracy
        self.reputation_score = max(0.0, min(1.0, self.reputation_score))


class ConsensusAlgorithm(ABC):
    """共识算法抽象基类"""
    
    def __init__(self, algorithm_name: str):
        self.algorithm_name = algorithm_name
        self.execution_history = []
        self.performance_metrics = defaultdict(list)
    
    @abstractmethod
    async def reach_consensus(self, 
                            proposal: ConsensusProposal,
                            agent_profiles: Dict[str, AgentProfile],
                            votes: Dict[str, AgentVote]) -> ConsensusResult:
        """达成共识"""
        pass
    
    async def evaluate_consensus_quality(self, result: ConsensusResult) -> float:
        """评估共识质量"""
        if not result.consensus_achieved:
            return 0.0
        
        # 参与度评分
        participation_score = len(result.participating_agents) / max(len(result.votes), 1)
        
        # 置信度评分
        confidence_score = result.confidence_level
        
        # 一致性评分
        vote_values = [vote.vote_value for vote in result.votes.values()]
        if vote_values:
            consistency_score = 1 - np.std(vote_values) if len(vote_values) > 1 else 1.0
        else:
            consistency_score = 0.0
        
        # 质量评分
        quality_score = (participation_score + confidence_score + consistency_score) / 3
        
        return quality_score
    
    def record_execution(self, result: ConsensusResult):
        """记录执行历史"""
        execution_record = {
            'timestamp': time.time(),
            'proposal_id': result.proposal_id,
            'consensus_achieved': result.consensus_achieved,
            'confidence_level': result.confidence_level,
            'execution_time': result.execution_time,
            'participating_agents': len(result.participating_agents),
            'consensus_quality': result.consensus_quality_score
        }
        
        self.execution_history.append(execution_record)
        
        # 更新性能指标
        for metric, value in execution_record.items():
            if isinstance(value, (int, float)):
                self.performance_metrics[metric].append(value)


class AdaptiveWeightConsensus(ConsensusAlgorithm):
    """自适应权重共识算法"""
    
    def __init__(self):
        super().__init__("adaptive_weight_consensus")
        self.weight_adaptation_rate = 0.1
        self.min_participation_threshold = 0.5
        self.confidence_threshold = 0.7
    
    async def reach_consensus(self, 
                            proposal: ConsensusProposal,
                            agent_profiles: Dict[str, AgentProfile],
                            votes: Dict[str, AgentVote]) -> ConsensusResult:
        """自适应权重共识"""
        start_time = time.time()
        
        # 计算自适应权重
        adaptive_weights = await self._calculate_adaptive_weights(
            proposal, agent_profiles, votes
        )
        
        # 应用权重到投票
        weighted_votes = self._apply_weights_to_votes(votes, adaptive_weights)
        
        # 计算加权共识
        consensus_score, consensus_confidence = self._calculate_weighted_consensus(
            weighted_votes
        )
        
        # 判断是否达成共识
        consensus_achieved = (
            consensus_score > 0.5 and 
            consensus_confidence > self.confidence_threshold and
            len(votes) / max(len(agent_profiles), 1) > self.min_participation_threshold
        )
        
        # 构造结果
        execution_time = time.time() - start_time
        
        result = ConsensusResult(
            proposal_id=proposal.proposal_id,
            consensus_achieved=consensus_achieved,
            final_decision=proposal.content if consensus_achieved else None,
            confidence_level=consensus_confidence,
            participating_agents=set(votes.keys()),
            votes=votes,
            consensus_type=ConsensusType.ADAPTIVE_CONSENSUS,
            execution_time=execution_time,
            metadata={
                'adaptive_weights': adaptive_weights,
                'weighted_consensus_score': consensus_score,
                'participation_rate': len(votes) / max(len(agent_profiles), 1)
            }
        )
        
        # 评估共识质量
        result.consensus_quality_score = await self.evaluate_consensus_quality(result)
        
        # 记录执行
        self.record_execution(result)
        
        return result
    
    async def _calculate_adaptive_weights(self, 
                                        proposal: ConsensusProposal,
                                        agent_profiles: Dict[str, AgentProfile],
                                        votes: Dict[str, AgentVote]) -> Dict[str, float]:
        """计算自适应权重"""
        weights = {}
        
        for agent_id, vote in votes.items():
            if agent_id not in agent_profiles:
                weights[agent_id] = 0.5  # 默认权重
                continue
            
            profile = agent_profiles[agent_id]
            
            # 基础权重组件
            trust_weight = profile.trust_level.value
            expertise_weight = self._calculate_expertise_weight(profile, proposal)
            accuracy_weight = profile.historical_accuracy
            reputation_weight = profile.reputation_score
            confidence_weight = vote.confidence
            
            # 自适应权重计算
            adaptive_weight = self._compute_adaptive_weight(
                trust_weight, expertise_weight, accuracy_weight, 
                reputation_weight, confidence_weight
            )
            
            weights[agent_id] = adaptive_weight
        
        # 权重归一化
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {agent_id: weight / total_weight for agent_id, weight in weights.items()}
        
        return weights
    
    def _calculate_expertise_weight(self, 
                                  profile: AgentProfile,
                                  proposal: ConsensusProposal) -> float:
        """计算专业知识权重"""
        proposal_domains = set()
        
        # 从提案内容中推断相关领域
        content_str = str(proposal.content).lower()
        domain_keywords = {
            'natural_language': ['text', 'language', 'nlp', 'semantic'],
            'machine_learning': ['model', 'training', 'prediction', 'learning'],
            'data_processing': ['data', 'processing', 'analysis', 'computation'],
            'system_architecture': ['system', 'architecture', 'design', 'structure'],
            'security': ['security', 'encryption', 'authentication', 'privacy']
        }
        
        for domain, keywords in domain_keywords.items():
            if any(keyword in content_str for keyword in keywords):
                proposal_domains.add(domain)
        
        if not proposal_domains:
            return 0.5  # 中性权重
        
        # 计算专业知识匹配度
        expertise_overlap = len(profile.expertise_domains & proposal_domains)
        total_relevant_domains = len(proposal_domains)
        
        if total_relevant_domains == 0:
            return 0.5
        
        expertise_weight = expertise_overlap / total_relevant_domains
        return expertise_weight
    
    def _compute_adaptive_weight(self, 
                               trust: float,
                               expertise: float,
                               accuracy: float,
                               reputation: float,
                               confidence: float) -> float:
        """计算自适应权重"""
        # 权重组合策略
        weights = np.array([trust, expertise, accuracy, reputation, confidence])
        
        # 自适应权重系数
        coefficients = np.array([0.25, 0.30, 0.20, 0.15, 0.10])
        
        # 计算加权平均
        adaptive_weight = np.dot(weights, coefficients)
        
        # 应用非线性变换增强差异
        adaptive_weight = self._apply_nonlinear_transformation(adaptive_weight)
        
        return max(0.1, min(1.0, adaptive_weight))  # 限制在合理范围内
    
    def _apply_nonlinear_transformation(self, weight: float) -> float:
        """应用非线性变换"""
        # 使用sigmoid函数增强权重差异
        transformed = 1 / (1 + np.exp(-10 * (weight - 0.5)))
        return transformed
    
    def _apply_weights_to_votes(self, 
                              votes: Dict[str, AgentVote],
                              weights: Dict[str, float]) -> Dict[str, AgentVote]:
        """应用权重到投票"""
        weighted_votes = {}
        
        for agent_id, vote in votes.items():
            weight = weights.get(agent_id, 0.5)
            
            # 创建加权投票
            weighted_vote = AgentVote(
                agent_id=vote.agent_id,
                vote_value=vote.vote_value,
                confidence=vote.confidence,
                reasoning=vote.reasoning,
                vote_weight=weight,
                timestamp=vote.timestamp,
                evidence=vote.evidence
            )
            
            weighted_votes[agent_id] = weighted_vote
        
        return weighted_votes
    
    def _calculate_weighted_consensus(self, 
                                    weighted_votes: Dict[str, AgentVote]) -> Tuple[float, float]:
        """计算加权共识"""
        if not weighted_votes:
            return 0.0, 0.0
        
        # 加权投票值
        weighted_sum = sum(vote.vote_value * vote.vote_weight for vote in weighted_votes.values())
        total_weight = sum(vote.vote_weight for vote in weighted_votes.values())
        
        consensus_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        # 加权置信度
        weighted_confidence_sum = sum(vote.confidence * vote.vote_weight for vote in weighted_votes.values())
        consensus_confidence = weighted_confidence_sum / total_weight if total_weight > 0 else 0.0
        
        return consensus_score, consensus_confidence


class ConfidencePropagationConsensus(ConsensusAlgorithm):
    """置信度传播共识算法"""
    
    def __init__(self):
        super().__init__("confidence_propagation_consensus")
        self.propagation_iterations = 5
        self.damping_factor = 0.85
        self.convergence_threshold = 0.001
    
    async def reach_consensus(self, 
                            proposal: ConsensusProposal,
                            agent_profiles: Dict[str, AgentProfile],
                            votes: Dict[str, AgentVote]) -> ConsensusResult:
        """置信度传播共识"""
        start_time = time.time()
        
        # 构建智能体信任网络
        trust_network = self._build_trust_network(agent_profiles)
        
        # 初始化置信度
        initial_confidences = {agent_id: vote.confidence for agent_id, vote in votes.items()}
        
        # 执行置信度传播
        propagated_confidences = await self._propagate_confidence(
            trust_network, initial_confidences
        )
        
        # 基于传播后的置信度计算共识
        consensus_score, final_confidence = self._calculate_propagation_consensus(
            votes, propagated_confidences
        )
        
        # 判断共识
        consensus_achieved = consensus_score > 0.6 and final_confidence > 0.7
        
        execution_time = time.time() - start_time
        
        result = ConsensusResult(
            proposal_id=proposal.proposal_id,
            consensus_achieved=consensus_achieved,
            final_decision=proposal.content if consensus_achieved else None,
            confidence_level=final_confidence,
            participating_agents=set(votes.keys()),
            votes=votes,
            consensus_type=ConsensusType.CONFIDENCE_PROPAGATION,
            execution_time=execution_time,
            metadata={
                'initial_confidences': initial_confidences,
                'propagated_confidences': propagated_confidences,
                'trust_network_nodes': trust_network.number_of_nodes(),
                'trust_network_edges': trust_network.number_of_edges(),
                'propagation_consensus_score': consensus_score
            }
        )
        
        result.consensus_quality_score = await self.evaluate_consensus_quality(result)
        self.record_execution(result)
        
        return result
    
    def _build_trust_network(self, agent_profiles: Dict[str, AgentProfile]) -> nx.DiGraph:
        """构建智能体信任网络"""
        G = nx.DiGraph()
        
        # 添加节点
        for agent_id, profile in agent_profiles.items():
            G.add_node(agent_id, 
                      trust_level=profile.trust_level.value,
                      reputation=profile.reputation_score,
                      accuracy=profile.historical_accuracy)
        
        # 添加信任边
        agents = list(agent_profiles.keys())
        for i, agent1 in enumerate(agents):
            for agent2 in agents[i+1:]:
                # 基于相似性和历史协作计算信任度
                trust_weight = self._calculate_trust_weight(
                    agent_profiles[agent1], agent_profiles[agent2]
                )
                
                if trust_weight > 0.3:  # 信任阈值
                    G.add_edge(agent1, agent2, weight=trust_weight)
                    G.add_edge(agent2, agent1, weight=trust_weight)
        
        return G
    
    def _calculate_trust_weight(self, 
                              profile1: AgentProfile,
                              profile2: AgentProfile) -> float:
        """计算智能体间的信任权重"""
        # 专业领域相似性
        domain_similarity = len(profile1.expertise_domains & profile2.expertise_domains) / \
                           max(len(profile1.expertise_domains | profile2.expertise_domains), 1)
        
        # 声誉相似性
        reputation_similarity = 1 - abs(profile1.reputation_score - profile2.reputation_score)
        
        # 历史准确性相似性
        accuracy_similarity = 1 - abs(profile1.historical_accuracy - profile2.historical_accuracy)
        
        # 协作分数相似性
        collaboration_similarity = 1 - abs(profile1.collaboration_score - profile2.collaboration_score)
        
        # 综合信任权重
        trust_weight = (domain_similarity * 0.4 + 
                       reputation_similarity * 0.3 + 
                       accuracy_similarity * 0.2 + 
                       collaboration_similarity * 0.1)
        
        return trust_weight
    
    async def _propagate_confidence(self, 
                                  trust_network: nx.DiGraph,
                                  initial_confidences: Dict[str, float]) -> Dict[str, float]:
        """执行置信度传播"""
        current_confidences = initial_confidences.copy()
        
        for iteration in range(self.propagation_iterations):
            new_confidences = {}
            
            for agent_id in trust_network.nodes():
                if agent_id not in current_confidences:
                    continue
                
                # 获取邻居节点
                neighbors = list(trust_network.neighbors(agent_id))
                
                if not neighbors:
                    new_confidences[agent_id] = current_confidences[agent_id]
                    continue
                
                # 计算传播的置信度
                propagated_confidence = self._calculate_propagated_confidence(
                    agent_id, neighbors, trust_network, current_confidences
                )
                
                # 阻尼更新
                new_confidences[agent_id] = (
                    self.damping_factor * propagated_confidence + 
                    (1 - self.damping_factor) * current_confidences[agent_id]
                )
            
            # 检查收敛
            if self._check_convergence(current_confidences, new_confidences):
                break
            
            current_confidences = new_confidences
        
        return current_confidences
    
    def _calculate_propagated_confidence(self, 
                                       agent_id: str,
                                       neighbors: List[str],
                                       trust_network: nx.DiGraph,
                                       confidences: Dict[str, float]) -> float:
        """计算传播的置信度"""
        weighted_confidence_sum = 0.0
        total_weight = 0.0
        
        for neighbor in neighbors:
            if neighbor in confidences:
                edge_data = trust_network.get_edge_data(agent_id, neighbor, {})
                trust_weight = edge_data.get('weight', 0.5)
                
                weighted_confidence_sum += confidences[neighbor] * trust_weight
                total_weight += trust_weight
        
        if total_weight > 0:
            return weighted_confidence_sum / total_weight
        else:
            return confidences.get(agent_id, 0.5)
    
    def _check_convergence(self, 
                         old_confidences: Dict[str, float],
                         new_confidences: Dict[str, float]) -> bool:
        """检查收敛"""
        for agent_id in old_confidences:
            if agent_id in new_confidences:
                diff = abs(old_confidences[agent_id] - new_confidences[agent_id])
                if diff > self.convergence_threshold:
                    return False
        return True
    
    def _calculate_propagation_consensus(self, 
                                       votes: Dict[str, AgentVote],
                                       propagated_confidences: Dict[str, float]) -> Tuple[float, float]:
        """基于传播置信度计算共识"""
        if not votes:
            return 0.0, 0.0
        
        # 使用传播后的置信度作为权重
        weighted_vote_sum = 0.0
        weighted_confidence_sum = 0.0
        total_weight = 0.0
        
        for agent_id, vote in votes.items():
            propagated_conf = propagated_confidences.get(agent_id, vote.confidence)
            
            weighted_vote_sum += vote.vote_value * propagated_conf
            weighted_confidence_sum += propagated_conf * propagated_conf
            total_weight += propagated_conf
        
        consensus_score = weighted_vote_sum / total_weight if total_weight > 0 else 0.0
        final_confidence = weighted_confidence_sum / total_weight if total_weight > 0 else 0.0
        
        return consensus_score, final_confidence


class HierarchicalConsensus(ConsensusAlgorithm):
    """分层共识算法"""
    
    def __init__(self):
        super().__init__("hierarchical_consensus")
        self.hierarchy_levels = 3
        self.level_thresholds = [0.5, 0.7, 0.9]  # 各层级的共识阈值
    
    async def reach_consensus(self, 
                            proposal: ConsensusProposal,
                            agent_profiles: Dict[str, AgentProfile],
                            votes: Dict[str, AgentVote]) -> ConsensusResult:
        """分层共识"""
        start_time = time.time()
        
        # 根据信任级别分层
        agent_hierarchy = self._create_agent_hierarchy(agent_profiles)
        
        # 分层次进行共识
        level_results = []
        final_consensus = False
        final_confidence = 0.0
        final_decision = None
        
        for level in range(self.hierarchy_levels):
            level_agents = agent_hierarchy.get(level, [])
            level_votes = {aid: votes[aid] for aid in level_agents if aid in votes}
            
            if not level_votes:
                level_results.append({
                    'level': level,
                    'consensus': False,
                    'confidence': 0.0,
                    'agents': level_agents
                })
                continue
            
            # 计算当前层级的共识
            level_consensus, level_confidence = self._calculate_level_consensus(
                level_votes, self.level_thresholds[level]
            )
            
            level_results.append({
                'level': level,
                'consensus': level_consensus,
                'confidence': level_confidence,
                'agents': level_agents,
                'votes': len(level_votes)
            })
            
            # 检查是否达成共识
            if level_consensus:
                final_consensus = True
                final_confidence = level_confidence
                final_decision = proposal.content
                break
        
        execution_time = time.time() - start_time
        
        result = ConsensusResult(
            proposal_id=proposal.proposal_id,
            consensus_achieved=final_consensus,
            final_decision=final_decision,
            confidence_level=final_confidence,
            participating_agents=set(votes.keys()),
            votes=votes,
            consensus_type=ConsensusType.HIERARCHICAL_CONSENSUS,
            execution_time=execution_time,
            metadata={
                'hierarchy_levels': self.hierarchy_levels,
                'level_results': level_results,
                'agent_hierarchy': agent_hierarchy
            }
        )
        
        result.consensus_quality_score = await self.evaluate_consensus_quality(result)
        self.record_execution(result)
        
        return result
    
    def _create_agent_hierarchy(self, agent_profiles: Dict[str, AgentProfile]) -> Dict[int, List[str]]:
        """创建智能体层级"""
        hierarchy = defaultdict(list)
        
        for agent_id, profile in agent_profiles.items():
            # 基于信任级别和声誉分数确定层级
            trust_score = profile.trust_level.value
            reputation_score = profile.reputation_score
            accuracy_score = profile.historical_accuracy
            
            # 综合评分
            overall_score = (trust_score + reputation_score + accuracy_score) / 3
            
            # 分配到层级
            if overall_score >= 0.8:
                hierarchy[0].append(agent_id)  # 最高层级
            elif overall_score >= 0.6:
                hierarchy[1].append(agent_id)  # 中等层级
            else:
                hierarchy[2].append(agent_id)  # 基础层级
        
        return dict(hierarchy)
    
    def _calculate_level_consensus(self, 
                                 level_votes: Dict[str, AgentVote],
                                 threshold: float) -> Tuple[bool, float]:
        """计算层级共识"""
        if not level_votes:
            return False, 0.0
        
        # 计算平均投票值和置信度
        vote_values = [vote.vote_value for vote in level_votes.values()]
        confidences = [vote.confidence for vote in level_votes.values()]
        
        avg_vote = np.mean(vote_values)
        avg_confidence = np.mean(confidences)
        
        # 检查是否达到阈值
        consensus_achieved = avg_vote >= threshold and avg_confidence >= 0.6
        
        return consensus_achieved, avg_confidence


class DynamicQuorumConsensus(ConsensusAlgorithm):
    """动态法定人数共识算法"""
    
    def __init__(self):
        super().__init__("dynamic_quorum_consensus")
        self.base_quorum_ratio = 0.5
        self.max_quorum_ratio = 0.8
        self.min_quorum_ratio = 0.3
    
    async def reach_consensus(self, 
                            proposal: ConsensusProposal,
                            agent_profiles: Dict[str, AgentProfile],
                            votes: Dict[str, AgentVote]) -> ConsensusResult:
        """动态法定人数共识"""
        start_time = time.time()
        
        # 计算动态法定人数
        dynamic_quorum = self._calculate_dynamic_quorum(proposal, agent_profiles, votes)
        
        # 检查参与度
        participation_rate = len(votes) / max(len(agent_profiles), 1)
        
        # 计算投票结果
        positive_votes = sum(1 for vote in votes.values() if vote.vote_value > 0.5)
        negative_votes = len(votes) - positive_votes
        
        # 计算加权投票结果
        weighted_positive = sum(vote.vote_value * vote.confidence for vote in votes.values() if vote.vote_value > 0.5)
        weighted_total = sum(vote.confidence for vote in votes.values())
        
        # 判断共识
        quorum_met = participation_rate >= dynamic_quorum
        majority_achieved = positive_votes > negative_votes
        confidence_sufficient = (weighted_positive / max(weighted_total, 1)) > 0.6
        
        consensus_achieved = quorum_met and majority_achieved and confidence_sufficient
        
        # 计算最终置信度
        final_confidence = (weighted_positive / max(weighted_total, 1)) if consensus_achieved else 0.0
        
        execution_time = time.time() - start_time
        
        result = ConsensusResult(
            proposal_id=proposal.proposal_id,
            consensus_achieved=consensus_achieved,
            final_decision=proposal.content if consensus_achieved else None,
            confidence_level=final_confidence,
            participating_agents=set(votes.keys()),
            votes=votes,
            consensus_type=ConsensusType.DYNAMIC_QUORUM,
            execution_time=execution_time,
            metadata={
                'dynamic_quorum': dynamic_quorum,
                'participation_rate': participation_rate,
                'positive_votes': positive_votes,
                'negative_votes': negative_votes,
                'quorum_met': quorum_met,
                'majority_achieved': majority_achieved,
                'confidence_sufficient': confidence_sufficient
            }
        )
        
        result.consensus_quality_score = await self.evaluate_consensus_quality(result)
        self.record_execution(result)
        
        return result
    
    def _calculate_dynamic_quorum(self, 
                                proposal: ConsensusProposal,
                                agent_profiles: Dict[str, AgentProfile],
                                votes: Dict[str, AgentVote]) -> float:
        """计算动态法定人数"""
        # 基于提案重要性调整
        importance_factor = proposal.priority / 5.0  # 假设优先级1-5
        
        # 基于提案置信度调整
        confidence_factor = proposal.confidence
        
        # 基于参与智能体的平均信任度调整
        participating_trust = []
        for agent_id in votes.keys():
            if agent_id in agent_profiles:
                participating_trust.append(agent_profiles[agent_id].trust_level.value)
        
        avg_trust = np.mean(participating_trust) if participating_trust else 0.5
        
        # 计算动态法定人数
        base_quorum = self.base_quorum_ratio
        
        # 重要性越高，需要更多参与
        importance_adjustment = (importance_factor - 0.5) * 0.2
        
        # 置信度越高，可以适当降低要求
        confidence_adjustment = -(confidence_factor - 0.5) * 0.1
        
        # 信任度越高，可以适当降低要求
        trust_adjustment = -(avg_trust - 0.5) * 0.15
        
        dynamic_quorum = base_quorum + importance_adjustment + confidence_adjustment + trust_adjustment
        
        # 限制在合理范围内
        dynamic_quorum = max(self.min_quorum_ratio, min(self.max_quorum_ratio, dynamic_quorum))
        
        return dynamic_quorum


class EnhancedByzantineFaultTolerantConsensus(ConsensusAlgorithm):
    """增强拜占庭容错共识算法"""
    
    def __init__(self):
        super().__init__("enhanced_byzantine_fault_tolerant")
        self.fault_tolerance_ratio = 1/3  # 最多容忍1/3的恶意节点
        self.outlier_detection_threshold = 2.0  # 异常值检测阈值(标准差倍数)
    
    async def reach_consensus(self, 
                            proposal: ConsensusProposal,
                            agent_profiles: Dict[str, AgentProfile],
                            votes: Dict[str, AgentVote]) -> ConsensusResult:
        """增强拜占庭容错共识"""
        start_time = time.time()
        
        # 异常值检测
        outliers = self._detect_outliers(votes)
        
        # 过滤可能的恶意投票
        filtered_votes = self._filter_malicious_votes(votes, agent_profiles, outliers)
        
        # 计算容错阈值
        n = len(filtered_votes)
        f = int(n * self.fault_tolerance_ratio)  # 最多容忍的恶意节点数
        
        # 需要至少2f+1个诚实节点达成共识
        min_honest_nodes = 2 * f + 1
        
        if len(filtered_votes) < min_honest_nodes:
            # 无法达成拜占庭容错共识
            execution_time = time.time() - start_time
            return ConsensusResult(
                proposal_id=proposal.proposal_id,
                consensus_achieved=False,
                final_decision=None,
                confidence_level=0.0,
                participating_agents=set(votes.keys()),
                votes=votes,
                consensus_type=ConsensusType.BYZANTINE_FAULT_TOLERANT,
                execution_time=execution_time,
                metadata={
                    'insufficient_honest_nodes': True,
                    'required_honest_nodes': min_honest_nodes,
                    'available_nodes': len(filtered_votes),
                    'outliers': outliers,
                    'filtered_out': len(votes) - len(filtered_votes)
                }
            )
        
        # 执行拜占庭容错算法
        consensus_result = self._byzantine_consensus_algorithm(filtered_votes, f)
        
        execution_time = time.time() - start_time
        
        result = ConsensusResult(
            proposal_id=proposal.proposal_id,
            consensus_achieved=consensus_result['consensus'],
            final_decision=proposal.content if consensus_result['consensus'] else None,
            confidence_level=consensus_result['confidence'],
            participating_agents=set(votes.keys()),
            votes=votes,
            consensus_type=ConsensusType.BYZANTINE_FAULT_TOLERANT,
            execution_time=execution_time,
            metadata={
                'fault_tolerance_ratio': self.fault_tolerance_ratio,
                'max_faulty_nodes': f,
                'min_honest_nodes': min_honest_nodes,
                'outliers_detected': outliers,
                'votes_filtered': len(votes) - len(filtered_votes),
                'byzantine_algorithm_result': consensus_result
            }
        )
        
        result.consensus_quality_score = await self.evaluate_consensus_quality(result)
        self.record_execution(result)
        
        return result
    
    def _detect_outliers(self, votes: Dict[str, AgentVote]) -> List[str]:
        """检测异常投票"""
        if len(votes) < 3:
            return []
        
        vote_values = [vote.vote_value for vote in votes.values()]
        confidences = [vote.confidence for vote in votes.values()]
        
        # 检测投票值异常
        vote_mean = np.mean(vote_values)
        vote_std = np.std(vote_values)
        
        # 检测置信度异常
        conf_mean = np.mean(confidences)
        conf_std = np.std(confidences)
        
        outliers = []
        
        for agent_id, vote in votes.items():
            # 投票值异常检测
            vote_z_score = abs(vote.vote_value - vote_mean) / max(vote_std, 0.1)
            
            # 置信度异常检测
            conf_z_score = abs(vote.confidence - conf_mean) / max(conf_std, 0.1)
            
            # 如果任一指标异常
            if (vote_z_score > self.outlier_detection_threshold or 
                conf_z_score > self.outlier_detection_threshold):
                outliers.append(agent_id)
        
        return outliers
    
    def _filter_malicious_votes(self, 
                              votes: Dict[str, AgentVote],
                              agent_profiles: Dict[str, AgentProfile],
                              outliers: List[str]) -> Dict[str, AgentVote]:
        """过滤恶意投票"""
        filtered_votes = {}
        
        for agent_id, vote in votes.items():
            # 检查是否为异常值
            if agent_id in outliers:
                continue
            
            # 检查智能体信任度
            if agent_id in agent_profiles:
                profile = agent_profiles[agent_id]
                
                # 信任度过低的智能体
                if profile.trust_level.value < 0.3:
                    continue
                
                # 历史准确性过低
                if profile.historical_accuracy < 0.4:
                    continue
                
                # 声誉分数过低
                if profile.reputation_score < 0.3:
                    continue
            
            # 投票置信度过低
            if vote.confidence < 0.3:
                continue
            
            filtered_votes[agent_id] = vote
        
        return filtered_votes
    
    def _byzantine_consensus_algorithm(self, 
                                     votes: Dict[str, AgentVote],
                                     f: int) -> Dict[str, Any]:
        """拜占庭容错共识算法"""
        vote_values = [vote.vote_value for vote in votes.values()]
        confidences = [vote.confidence for vote in votes.values()]
        
        # 排序投票值
        sorted_votes = sorted(vote_values)
        n = len(sorted_votes)
        
        # 去除最大和最小的f个值(潜在的恶意投票)
        if n > 2 * f:
            trimmed_votes = sorted_votes[f:n-f]
        else:
            trimmed_votes = sorted_votes
        
        # 计算修剪后的平均值
        if trimmed_votes:
            consensus_value = np.mean(trimmed_votes)
            consensus_confidence = np.mean([confidences[i] for i in range(len(vote_values)) 
                                          if sorted_votes[f] <= vote_values[i] <= sorted_votes[n-f-1]])
        else:
            consensus_value = 0.5
            consensus_confidence = 0.0
        
        # 判断是否达成共识
        consensus_achieved = (consensus_value > 0.5 and 
                            consensus_confidence > 0.6 and 
                            len(trimmed_votes) >= (2 * f + 1))
        
        return {
            'consensus': consensus_achieved,
            'value': consensus_value,
            'confidence': consensus_confidence,
            'trimmed_votes_count': len(trimmed_votes),
            'original_votes_count': n
        }


class AdvancedConsensusEngine:
    """高级共识引擎"""
    
    def __init__(self):
        self.algorithms = {
            ConsensusType.ADAPTIVE_CONSENSUS: AdaptiveWeightConsensus(),
            ConsensusType.CONFIDENCE_PROPAGATION: ConfidencePropagationConsensus(),
            ConsensusType.HIERARCHICAL_CONSENSUS: HierarchicalConsensus(),
            ConsensusType.DYNAMIC_QUORUM: DynamicQuorumConsensus(),
            ConsensusType.BYZANTINE_FAULT_TOLERANT: EnhancedByzantineFaultTolerantConsensus(),
        }
        
        self.agent_profiles: Dict[str, AgentProfile] = {}
        self.consensus_history = []
        self.performance_metrics = defaultdict(list)
    
    def register_agent(self, agent_profile: AgentProfile):
        """注册智能体档案"""
        self.agent_profiles[agent_profile.agent_id] = agent_profile
    
    async def conduct_consensus(self, 
                              proposal: ConsensusProposal,
                              votes: Dict[str, AgentVote],
                              consensus_type: ConsensusType = ConsensusType.ADAPTIVE_CONSENSUS) -> ConsensusResult:
        """进行共识决策"""
        if consensus_type not in self.algorithms:
            raise ValueError(f"Unsupported consensus type: {consensus_type}")
        
        algorithm = self.algorithms[consensus_type]
        
        # 执行共识算法
        result = await algorithm.reach_consensus(proposal, self.agent_profiles, votes)
        
        # 更新智能体声誉
        await self._update_agent_reputations(result)
        
        # 记录共识历史
        self._record_consensus_history(result)
        
        return result
    
    async def auto_select_consensus_algorithm(self, 
                                            proposal: ConsensusProposal,
                                            votes: Dict[str, AgentVote]) -> ConsensusType:
        """自动选择最适合的共识算法"""
        # 基于多个因素选择算法
        factors = self._analyze_consensus_factors(proposal, votes)
        
        # 算法选择策略
        if factors['trust_variance'] > 0.3:
            return ConsensusType.BYZANTINE_FAULT_TOLERANT
        elif factors['importance_level'] > 0.8:
            return ConsensusType.HIERARCHICAL_CONSENSUS
        elif factors['network_connectivity'] > 0.7:
            return ConsensusType.CONFIDENCE_PROPAGATION
        elif factors['participation_rate'] < 0.6:
            return ConsensusType.DYNAMIC_QUORUM
        else:
            return ConsensusType.ADAPTIVE_CONSENSUS
    
    def _analyze_consensus_factors(self, 
                                 proposal: ConsensusProposal,
                                 votes: Dict[str, AgentVote]) -> Dict[str, float]:
        """分析共识因素"""
        factors = {}
        
        # 信任度方差
        trust_levels = []
        for agent_id in votes.keys():
            if agent_id in self.agent_profiles:
                trust_levels.append(self.agent_profiles[agent_id].trust_level.value)
        
        factors['trust_variance'] = np.var(trust_levels) if trust_levels else 0.5
        
        # 重要性级别
        factors['importance_level'] = proposal.priority / 5.0
        
        # 网络连接性（简化计算）
        factors['network_connectivity'] = min(len(votes) / max(len(self.agent_profiles), 1), 1.0)
        
        # 参与率
        factors['participation_rate'] = len(votes) / max(len(self.agent_profiles), 1)
        
        # 置信度方差
        confidences = [vote.confidence for vote in votes.values()]
        factors['confidence_variance'] = np.var(confidences) if confidences else 0.5
        
        return factors
    
    async def _update_agent_reputations(self, result: ConsensusResult):
        """更新智能体声誉"""
        if not result.consensus_achieved:
            return
        
        # 基于共识结果更新参与智能体的声誉
        consensus_quality = result.consensus_quality_score
        
        for agent_id, vote in result.votes.items():
            if agent_id in self.agent_profiles:
                profile = self.agent_profiles[agent_id]
                
                # 根据投票与最终结果的一致性更新声誉
                vote_accuracy = 1 - abs(vote.vote_value - (1.0 if result.consensus_achieved else 0.0))
                weighted_accuracy = vote_accuracy * consensus_quality
                
                profile.update_reputation(weighted_accuracy)
    
    def _record_consensus_history(self, result: ConsensusResult):
        """记录共识历史"""
        history_record = {
            'timestamp': time.time(),
            'proposal_id': result.proposal_id,
            'consensus_type': result.consensus_type.value,
            'consensus_achieved': result.consensus_achieved,
            'confidence_level': result.confidence_level,
            'execution_time': result.execution_time,
            'participating_agents': len(result.participating_agents),
            'consensus_quality': result.consensus_quality_score
        }
        
        self.consensus_history.append(history_record)
        
        # 保持历史记录在合理范围内
        if len(self.consensus_history) > 1000:
            self.consensus_history = self.consensus_history[-1000:]
        
        # 更新性能指标
        for metric, value in history_record.items():
            if isinstance(value, (int, float)):
                self.performance_metrics[metric].append(value)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.performance_metrics:
            return {'message': 'No performance data available'}
        
        summary = {}
        
        # 算法性能
        for consensus_type, algorithm in self.algorithms.items():
            summary[consensus_type.value] = {
                'executions': len(algorithm.execution_history),
                'performance_metrics': {}
            }
            
            for metric, values in algorithm.performance_metrics.items():
                if values:
                    summary[consensus_type.value]['performance_metrics'][metric] = {
                        'mean': np.mean(values),
                        'std': np.std(values),
                        'min': np.min(values),
                        'max': np.max(values)
                    }
        
        # 整体性能
        summary['overall'] = {
            'total_consensus_attempts': len(self.consensus_history),
            'registered_agents': len(self.agent_profiles)
        }
        
        # 成功率统计
        if self.consensus_history:
            successful_consensus = sum(1 for h in self.consensus_history if h['consensus_achieved'])
            summary['overall']['success_rate'] = successful_consensus / len(self.consensus_history)
        
        return summary


# 使用示例
async def main():
    """演示高级共识机制"""
    # 创建共识引擎
    consensus_engine = AdvancedConsensusEngine()
    
    # 注册智能体档案
    agent_profiles = [
        AgentProfile(
            agent_id="agent_001",
            expertise_domains={"natural_language", "machine_learning"},
            trust_level=AgentTrustLevel.HIGH_TRUST,
            historical_accuracy=0.85,
            response_time_avg=1.2,
            collaboration_score=0.9,
            reputation_score=0.8
        ),
        AgentProfile(
            agent_id="agent_002",
            expertise_domains={"data_processing", "system_architecture"},
            trust_level=AgentTrustLevel.MEDIUM_TRUST,
            historical_accuracy=0.75,
            response_time_avg=1.5,
            collaboration_score=0.7,
            reputation_score=0.6
        ),
        AgentProfile(
            agent_id="agent_003",
            expertise_domains={"security", "encryption"},
            trust_level=AgentTrustLevel.FULL_TRUST,
            historical_accuracy=0.92,
            response_time_avg=0.8,
            collaboration_score=0.95,
            reputation_score=0.9
        )
    ]
    
    for profile in agent_profiles:
        consensus_engine.register_agent(profile)
    
    # 创建提案
    proposal = ConsensusProposal(
        proposal_id="",
        proposer_id="system",
        proposal_type="condition_extraction_strategy",
        content={
            "strategy": "multi_stage_extraction",
            "confidence_threshold": 0.7,
            "max_conditions": 10
        },
        confidence=0.8,
        priority=3
    )
    
    # 创建投票
    votes = {
        "agent_001": AgentVote(
            agent_id="agent_001",
            vote_value=0.85,
            confidence=0.9,
            reasoning="Strong alignment with NLP expertise"
        ),
        "agent_002": AgentVote(
            agent_id="agent_002",
            vote_value=0.75,
            confidence=0.8,
            reasoning="Good system architecture fit"
        ),
        "agent_003": AgentVote(
            agent_id="agent_003",
            vote_value=0.9,
            confidence=0.95,
            reasoning="Excellent security considerations"
        )
    }
    
    # 测试不同的共识算法
    consensus_types = [
        ConsensusType.ADAPTIVE_CONSENSUS,
        ConsensusType.CONFIDENCE_PROPAGATION,
        ConsensusType.HIERARCHICAL_CONSENSUS,
        ConsensusType.BYZANTINE_FAULT_TOLERANT
    ]
    
    print("=== 高级共识机制测试 ===\n")
    
    for consensus_type in consensus_types:
        print(f"--- {consensus_type.value.upper()} ---")
        
        result = await consensus_engine.conduct_consensus(proposal, votes, consensus_type)
        
        print(f"共识达成: {result.consensus_achieved}")
        print(f"置信度: {result.confidence_level:.3f}")
        print(f"执行时间: {result.execution_time:.3f}s")
        print(f"质量评分: {result.consensus_quality_score:.3f}")
        print(f"参与智能体: {len(result.participating_agents)}")
        
        if result.metadata:
            print("元数据:")
            for key, value in result.metadata.items():
                if isinstance(value, (int, float)):
                    print(f"  {key}: {value:.3f}")
                elif isinstance(value, (list, dict)) and len(str(value)) < 100:
                    print(f"  {key}: {value}")
        
        print()
    
    # 获取性能摘要
    performance_summary = consensus_engine.get_performance_summary()
    print("=== 性能摘要 ===")
    print(json.dumps(performance_summary, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())