"""
Neural Connection Matrix
神经连接矩阵 - 实现智能体间的动态连接强度
"""

import numpy as np
import json
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta
import asyncio
from ..utils.config import get_logger, get_absolute_path

logger = get_logger(__name__)


class ConnectionMatrix:
    """
    智能体间连接矩阵 - 模拟神经元间的突触连接强度
    
    基于Hebbian学习原理：
    - "Neurons that fire together, wire together"
    - 共同激活的智能体连接强度增加
    - 长期不用的连接逐渐衰减
    """
    
    def __init__(self, agents: List[str], save_path: str = "data/brain/connection_matrix.json"):
        self.agents = agents
        self.n_agents = len(agents)
        self.agent_to_idx = {agent: i for i, agent in enumerate(agents)}
        self.idx_to_agent = {i: agent for i, agent in enumerate(agents)}
        
        # 连接强度矩阵 (对称矩阵)
        self.connections = np.ones((self.n_agents, self.n_agents)) * 0.5  # 初始强度0.5
        np.fill_diagonal(self.connections, 1.0)  # 自连接强度为1.0
        
        # 连接使用历史
        self.usage_history = {}
        self.last_activation_time = {}
        
        # 可塑性参数
        self.learning_rate = 0.1      # Hebbian学习率
        self.decay_rate = 0.01        # 连接衰减率
        self.min_strength = 0.1       # 最小连接强度
        self.max_strength = 1.0       # 最大连接强度
        self.consolidation_threshold = 0.8  # 连接巩固阈值
        
        # 保存路径
        self.save_path = get_absolute_path(save_path)
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载已有连接数据
        self._load_connections()
        
        logger.info(f"初始化连接矩阵：{self.n_agents} 个智能体，{self.n_agents**2} 个连接")
    
    def get_connection_strength(self, agent_a: str, agent_b: str) -> float:
        """获取两个智能体间的连接强度"""
        if agent_a not in self.agent_to_idx or agent_b not in self.agent_to_idx:
            return 0.5  # 默认强度
        
        idx_a = self.agent_to_idx[agent_a]
        idx_b = self.agent_to_idx[agent_b]
        return float(self.connections[idx_a, idx_b])
    
    def strengthen_connection(self, agent_a: str, agent_b: str, activation_strength: float = 1.0):
        """
        强化连接 - Hebbian学习
        
        Args:
            agent_a: 智能体A
            agent_b: 智能体B  
            activation_strength: 激活强度 (0-1)
        """
        if agent_a not in self.agent_to_idx or agent_b not in self.agent_to_idx:
            return
        
        idx_a = self.agent_to_idx[agent_a]
        idx_b = self.agent_to_idx[agent_b]
        
        # Hebbian学习：Δw = η * a_i * a_j
        current_strength = self.connections[idx_a, idx_b]
        delta = self.learning_rate * activation_strength * activation_strength
        
        # 更新连接强度（对称）
        new_strength = min(current_strength + delta, self.max_strength)
        self.connections[idx_a, idx_b] = new_strength
        self.connections[idx_b, idx_a] = new_strength
        
        # 记录使用历史
        connection_key = f"{min(agent_a, agent_b)}-{max(agent_a, agent_b)}"
        if connection_key not in self.usage_history:
            self.usage_history[connection_key] = []
        
        self.usage_history[connection_key].append({
            'timestamp': datetime.now().isoformat(),
            'strength_change': delta,
            'new_strength': new_strength,
            'activation_strength': activation_strength
        })
        
        # 保持历史记录不超过100条
        if len(self.usage_history[connection_key]) > 100:
            self.usage_history[connection_key] = self.usage_history[connection_key][-100:]
        
        self.last_activation_time[connection_key] = datetime.now().isoformat()
        
        logger.debug(f"强化连接 {agent_a} ↔ {agent_b}: {current_strength:.3f} → {new_strength:.3f} (+{delta:.3f})")
    
    def weaken_unused_connections(self, time_threshold: timedelta = timedelta(hours=24)):
        """衰减长期未使用的连接"""
        current_time = datetime.now()
        weakened_count = 0
        
        for i in range(self.n_agents):
            for j in range(i + 1, self.n_agents):  # 只处理上三角，保持对称性
                agent_a = self.idx_to_agent[i]
                agent_b = self.idx_to_agent[j]
                connection_key = f"{min(agent_a, agent_b)}-{max(agent_a, agent_b)}"
                
                # 检查是否长期未使用
                last_used = self.last_activation_time.get(connection_key)
                if last_used is None:
                    time_diff = time_threshold  # Force weakening if never used
                else:
                    last_used_dt = datetime.fromisoformat(last_used) if isinstance(last_used, str) else last_used
                    time_diff = current_time - last_used_dt
                
                if last_used is None or time_diff > time_threshold:
                    current_strength = self.connections[i, j]
                    if current_strength > self.min_strength:
                        # 指数衰减
                        new_strength = max(current_strength * (1 - self.decay_rate), self.min_strength)
                        self.connections[i, j] = new_strength
                        self.connections[j, i] = new_strength
                        weakened_count += 1
                        
                        logger.debug(f"衰减连接 {agent_a} ↔ {agent_b}: {current_strength:.3f} → {new_strength:.3f}")
        
        if weakened_count > 0:
            logger.info(f"衰减了 {weakened_count} 个长期未使用的连接")
    
    def get_strongest_connections(self, agent: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """获取与指定智能体连接最强的其他智能体"""
        if agent not in self.agent_to_idx:
            return []
        
        idx = self.agent_to_idx[agent]
        strengths = self.connections[idx, :]
        
        # 排序并排除自己
        indices = np.argsort(strengths)[::-1]
        strongest = []
        
        for idx_other in indices:
            if idx_other != idx and len(strongest) < top_k:
                other_agent = self.idx_to_agent[idx_other]
                strength = strengths[idx_other]
                strongest.append((other_agent, float(strength)))
        
        return strongest
    
    def get_activation_pathway(self, agents_activated: List[str]) -> List[Tuple[str, str, float]]:
        """
        获取智能体激活路径的连接强度
        
        Returns:
            List of (agent_a, agent_b, connection_strength)
        """
        pathway = []
        
        for i in range(len(agents_activated)):
            for j in range(i + 1, len(agents_activated)):
                agent_a = agents_activated[i]
                agent_b = agents_activated[j]
                strength = self.get_connection_strength(agent_a, agent_b)
                pathway.append((agent_a, agent_b, strength))
        
        return sorted(pathway, key=lambda x: x[2], reverse=True)
    
    def suggest_next_agents(self, currently_active: List[str], exclude: List[str] = None) -> List[Tuple[str, float]]:
        """
        基于连接强度建议下一步应该激活的智能体
        
        Args:
            currently_active: 当前激活的智能体
            exclude: 要排除的智能体
            
        Returns:
            List of (suggested_agent, combined_strength)
        """
        if not currently_active:
            return []
        
        exclude = exclude or []
        suggestions = {}
        
        for active_agent in currently_active:
            if active_agent not in self.agent_to_idx:
                continue
                
            strongest = self.get_strongest_connections(active_agent, top_k=5)
            for suggested_agent, strength in strongest:
                if suggested_agent not in exclude and suggested_agent not in currently_active:
                    if suggested_agent not in suggestions:
                        suggestions[suggested_agent] = 0
                    suggestions[suggested_agent] += strength
        
        # 按综合强度排序
        return sorted(suggestions.items(), key=lambda x: x[1], reverse=True)
    
    def get_network_metrics(self) -> Dict[str, Any]:
        """获取网络拓扑指标"""
        # 平均连接强度
        avg_strength = np.mean(self.connections[np.triu_indices(self.n_agents, k=1)])
        
        # 连接强度分布
        strengths = self.connections[np.triu_indices(self.n_agents, k=1)]
        strong_connections = np.sum(strengths > 0.7)
        weak_connections = np.sum(strengths < 0.3)
        
        # 最强连接
        max_idx = np.unravel_index(np.argmax(self.connections - np.eye(self.n_agents)), self.connections.shape)
        strongest_pair = (self.idx_to_agent[max_idx[0]], self.idx_to_agent[max_idx[1]])
        strongest_value = self.connections[max_idx]
        
        return {
            'average_strength': float(avg_strength),
            'strong_connections': int(strong_connections),
            'weak_connections': int(weak_connections),
            'total_connections': len(strengths),
            'strongest_connection': {
                'agents': strongest_pair,
                'strength': float(strongest_value)
            },
            'network_density': float(avg_strength),
            'plasticity_active': len(self.usage_history) > 0
        }
    
    def _save_connections(self):
        """保存连接矩阵到文件"""
        try:
            data = {
                'agents': self.agents,
                'connections': self.connections.tolist(),
                'usage_history': self.usage_history,
                'last_activation_time': {k: v.isoformat() for k, v in self.last_activation_time.items()},
                'parameters': {
                    'learning_rate': self.learning_rate,
                    'decay_rate': self.decay_rate,
                    'min_strength': self.min_strength,
                    'max_strength': self.max_strength
                },
                'saved_at': datetime.now().isoformat()
            }
            
            with open(self.save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logger.debug(f"连接矩阵已保存到 {self.save_path}")
        except Exception as e:
            logger.error(f"保存连接矩阵失败: {e}")
    
    def _load_connections(self):
        """从文件加载连接矩阵"""
        if not self.save_path.exists():
            logger.info("连接矩阵文件不存在，使用默认初始化")
            return
        
        try:
            with open(self.save_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查智能体列表是否匹配
            if data.get('agents') == self.agents:
                self.connections = np.array(data['connections'])
                self.usage_history = data.get('usage_history', {})
                
                # 恢复时间戳
                last_times = data.get('last_activation_time', {})
                self.last_activation_time = {}
                for k, v in last_times.items():
                    try:
                        self.last_activation_time[k] = datetime.fromisoformat(v)
                    except:
                        pass
                
                # 更新参数
                params = data.get('parameters', {})
                self.learning_rate = params.get('learning_rate', self.learning_rate)
                self.decay_rate = params.get('decay_rate', self.decay_rate)
                
                logger.info(f"成功加载连接矩阵，包含 {len(self.usage_history)} 个连接历史记录")
            else:
                logger.warning("智能体列表不匹配，使用默认初始化")
                
        except Exception as e:
            logger.error(f"加载连接矩阵失败: {e}")
    
    async def auto_save_loop(self, interval_minutes: int = 10):
        """自动保存连接矩阵"""
        while True:
            await asyncio.sleep(interval_minutes * 60)
            self._save_connections()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._save_connections()