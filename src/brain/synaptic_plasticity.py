"""
Synaptic Plasticity System  
突触可塑性系统 - 实现记忆间的动态关联强度
"""

import numpy as np
import json
from typing import Dict, List, Tuple, Optional, Set, Any
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib
from ..utils.config import get_logger, get_absolute_path

logger = get_logger(__name__)


class SynapticPlasticity:
    """
    突触可塑性系统 - 管理记忆间的关联强度
    
    实现功能：
    1. 长期增强 (LTP) - 共同激活的记忆连接加强
    2. 长期抑制 (LTD) - 竞争性记忆连接减弱  
    3. 关联性记忆检索 - 基于连接强度的记忆传播
    4. 记忆巩固 - 重要连接的长期保持
    """
    
    def __init__(self, save_path: str = "data/brain/synaptic_plasticity.json"):
        # 记忆间连接强度 {memory_id: {connected_memory_id: strength}}
        self.memory_connections = defaultdict(dict)
        
        # 记忆激活历史
        self.activation_history = defaultdict(list)
        self.co_activation_count = defaultdict(int)
        
        # 可塑性参数
        self.ltp_threshold = 0.3      # LTP阈值 - 共同激活阈值
        self.ltd_threshold = 0.1      # LTD阈值 - 竞争抑制阈值
        self.learning_rate = 0.15     # 学习率
        self.decay_rate = 0.02        # 自然衰减率
        self.min_strength = 0.05      # 最小连接强度
        self.max_strength = 1.0       # 最大连接强度
        self.consolidation_threshold = 0.7  # 巩固阈值
        
        # 时间窗口参数
        self.co_activation_window = timedelta(minutes=5)  # 共激活时间窗口
        self.memory_lifetime = timedelta(days=30)         # 记忆连接生存期
        
        # 保存路径
        self.save_path = get_absolute_path(save_path)
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载已有数据
        self._load_plasticity_data()
        
        logger.info("突触可塑性系统初始化完成")
    
    def record_memory_activation(self, memory_id: str, activation_strength: float = 1.0, 
                                context: Dict[str, Any] = None):
        """
        记录记忆激活事件
        
        Args:
            memory_id: 记忆ID
            activation_strength: 激活强度 (0-1)
            context: 激活上下文
        """
        activation_event = {
            'timestamp': datetime.now().isoformat(),
            'strength': activation_strength,
            'context': context or {}
        }
        
        self.activation_history[memory_id].append(activation_event)
        
        # 保持激活历史不超过100条
        if len(self.activation_history[memory_id]) > 100:
            self.activation_history[memory_id] = self.activation_history[memory_id][-100:]
        
        logger.debug(f"记录记忆激活: {memory_id} (强度: {activation_strength:.3f})")
    
    def process_co_activation(self, memory_ids: List[str], activation_strengths: List[float] = None):
        """
        处理记忆共同激活 - 实现Hebbian学习
        
        Args:
            memory_ids: 共同激活的记忆ID列表
            activation_strengths: 对应的激活强度
        """
        if len(memory_ids) < 2:
            return
        
        if activation_strengths is None:
            activation_strengths = [1.0] * len(memory_ids)
        
        current_time = datetime.now()
        
        # 处理所有记忆对
        for i in range(len(memory_ids)):
            for j in range(i + 1, len(memory_ids)):
                memory_a = memory_ids[i]
                memory_b = memory_ids[j]
                strength_a = activation_strengths[i]
                strength_b = activation_strengths[j]
                
                # 记录共激活
                co_key = self._get_connection_key(memory_a, memory_b)
                self.co_activation_count[co_key] += 1
                
                # Hebbian学习：共同激活强化连接
                self._strengthen_connection(memory_a, memory_b, strength_a, strength_b)
        
        # 记录各个记忆的激活
        for memory_id, strength in zip(memory_ids, activation_strengths):
            self.record_memory_activation(memory_id, strength, {'co_activated_with': memory_ids})
    
    def _strengthen_connection(self, memory_a: str, memory_b: str, 
                             strength_a: float, strength_b: float):
        """强化记忆间连接 - LTP机制"""
        # 计算连接强度增量
        combined_strength = (strength_a + strength_b) / 2
        
        # 只有当组合强度超过LTP阈值时才强化
        if combined_strength < self.ltp_threshold:
            return
        
        delta = self.learning_rate * combined_strength * combined_strength
        
        # 更新双向连接
        current_strength_ab = self.memory_connections[memory_a].get(memory_b, 0.0)
        current_strength_ba = self.memory_connections[memory_b].get(memory_a, 0.0)
        
        new_strength = min(max(current_strength_ab, current_strength_ba) + delta, self.max_strength)
        
        self.memory_connections[memory_a][memory_b] = new_strength
        self.memory_connections[memory_b][memory_a] = new_strength
        
        logger.debug(f"强化记忆连接 {memory_a} ↔ {memory_b}: {max(current_strength_ab, current_strength_ba):.3f} → {new_strength:.3f}")
    
    def apply_competitive_inhibition(self, target_memory: str, competing_memories: List[str]):
        """
        应用竞争性抑制 - LTD机制
        
        当一个记忆被强烈激活时，与其竞争的记忆连接会被抑制
        """
        for competing_memory in competing_memories:
            current_strength = self.memory_connections[target_memory].get(competing_memory, 0.0)
            
            if current_strength > self.ltd_threshold:
                # 计算抑制强度
                inhibition = self.learning_rate * 0.5  # LTD比LTP弱
                new_strength = max(current_strength - inhibition, self.min_strength)
                
                # 更新双向连接
                self.memory_connections[target_memory][competing_memory] = new_strength
                self.memory_connections[competing_memory][target_memory] = new_strength
                
                logger.debug(f"竞争抑制 {target_memory} ↔ {competing_memory}: {current_strength:.3f} → {new_strength:.3f}")
    
    def get_associated_memories(self, memory_id: str, min_strength: float = 0.1, 
                              top_k: int = 10) -> List[Tuple[str, float]]:
        """
        获取与指定记忆关联的其他记忆
        
        Returns:
            List of (associated_memory_id, connection_strength)
        """
        if memory_id not in self.memory_connections:
            return []
        
        associations = []
        for connected_memory, strength in self.memory_connections[memory_id].items():
            if strength >= min_strength:
                associations.append((connected_memory, strength))
        
        # 按连接强度排序
        associations.sort(key=lambda x: x[1], reverse=True)
        return associations[:top_k]
    
    def predict_next_memories(self, current_memories: List[str], 
                            prediction_strength: float = 0.3) -> List[Tuple[str, float]]:
        """
        基于当前激活记忆预测可能的下一个记忆
        
        Args:
            current_memories: 当前激活的记忆列表
            prediction_strength: 预测强度阈值
            
        Returns:
            List of (predicted_memory_id, combined_strength)
        """
        prediction_scores = defaultdict(float)
        
        for memory_id in current_memories:
            associations = self.get_associated_memories(memory_id, min_strength=prediction_strength)
            for associated_memory, strength in associations:
                if associated_memory not in current_memories:
                    prediction_scores[associated_memory] += strength
        
        # 转换为列表并排序
        predictions = list(prediction_scores.items())
        predictions.sort(key=lambda x: x[1], reverse=True)
        
        return predictions
    
    def consolidate_strong_connections(self):
        """巩固强连接 - 模拟睡眠中的记忆巩固"""
        consolidated_count = 0
        
        for memory_a in self.memory_connections:
            for memory_b, strength in self.memory_connections[memory_a].items():
                if strength > self.consolidation_threshold:
                    # 巩固：轻微增强并增加抗衰减性
                    consolidation_boost = 0.05
                    new_strength = min(strength + consolidation_boost, self.max_strength)
                    
                    self.memory_connections[memory_a][memory_b] = new_strength
                    self.memory_connections[memory_b][memory_a] = new_strength
                    
                    consolidated_count += 1
        
        if consolidated_count > 0:
            logger.info(f"巩固了 {consolidated_count // 2} 个强连接")  # 除以2因为是双向的
    
    def decay_weak_connections(self):
        """衰减弱连接 - 自然遗忘过程"""
        decayed_count = 0
        to_remove = []
        
        for memory_a in self.memory_connections:
            for memory_b, strength in list(self.memory_connections[memory_a].items()):
                if strength > self.min_strength:
                    new_strength = strength * (1 - self.decay_rate)
                    
                    if new_strength < self.min_strength:
                        # 连接太弱，移除
                        to_remove.append((memory_a, memory_b))
                    else:
                        self.memory_connections[memory_a][memory_b] = new_strength
                        decayed_count += 1
        
        # 移除弱连接
        for memory_a, memory_b in to_remove:
            if memory_b in self.memory_connections[memory_a]:
                del self.memory_connections[memory_a][memory_b]
            if memory_a in self.memory_connections[memory_b]:
                del self.memory_connections[memory_b][memory_a]
        
        if decayed_count > 0 or to_remove:
            logger.info(f"衰减了 {decayed_count} 个连接，移除了 {len(to_remove)} 个弱连接")
    
    def get_plasticity_stats(self) -> Dict[str, Any]:
        """获取可塑性统计信息"""
        total_memories = len(self.memory_connections)
        total_connections = sum(len(connections) for connections in self.memory_connections.values()) // 2
        
        if total_connections == 0:
            return {
                'total_memories': total_memories,
                'total_connections': 0,
                'average_strength': 0.0,
                'strong_connections': 0,
                'plasticity_active': False
            }
        
        # 计算连接强度统计
        all_strengths = []
        strong_connections = 0
        
        for memory_a in self.memory_connections:
            for memory_b, strength in self.memory_connections[memory_a].items():
                if memory_a < memory_b:  # 避免重复计算双向连接
                    all_strengths.append(strength)
                    if strength > 0.6:
                        strong_connections += 1
        
        avg_strength = np.mean(all_strengths) if all_strengths else 0.0
        
        return {
            'total_memories': total_memories,
            'total_connections': len(all_strengths),
            'average_strength': float(avg_strength),
            'strong_connections': strong_connections,
            'consolidation_candidates': sum(1 for s in all_strengths if s > self.consolidation_threshold),
            'plasticity_active': len(self.co_activation_count) > 0,
            'most_connected_memory': self._get_most_connected_memory()
        }
    
    def _get_most_connected_memory(self) -> Optional[Tuple[str, int]]:
        """获取连接数最多的记忆"""
        if not self.memory_connections:
            return None
        
        max_connections = 0
        most_connected = None
        
        for memory_id, connections in self.memory_connections.items():
            if len(connections) > max_connections:
                max_connections = len(connections)
                most_connected = memory_id
        
        return (most_connected, max_connections) if most_connected else None
    
    def _get_connection_key(self, memory_a: str, memory_b: str) -> str:
        """生成连接键（标准化顺序）"""
        return f"{min(memory_a, memory_b)}-{max(memory_a, memory_b)}"
    
    def _save_plasticity_data(self):
        """保存可塑性数据"""
        try:
            # 转换datetime对象为字符串
            activation_history_serializable = {}
            for memory_id, events in self.activation_history.items():
                activation_history_serializable[memory_id] = [
                    {
                        'timestamp': event['timestamp'].isoformat(),
                        'strength': event['strength'],
                        'context': event['context']
                    }
                    for event in events
                ]
            
            data = {
                'memory_connections': dict(self.memory_connections),
                'activation_history': activation_history_serializable,
                'co_activation_count': dict(self.co_activation_count),
                'parameters': {
                    'ltp_threshold': self.ltp_threshold,
                    'ltd_threshold': self.ltd_threshold,
                    'learning_rate': self.learning_rate,
                    'decay_rate': self.decay_rate,
                    'min_strength': self.min_strength,
                    'max_strength': self.max_strength
                },
                'saved_at': datetime.now().isoformat()
            }
            
            with open(self.save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"突触可塑性数据已保存到 {self.save_path}")
        except Exception as e:
            logger.error(f"保存突触可塑性数据失败: {e}")
    
    def _load_plasticity_data(self):
        """加载可塑性数据"""
        if not self.save_path.exists():
            logger.info("突触可塑性数据文件不存在，使用默认初始化")
            return
        
        try:
            with open(self.save_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 加载连接数据
            self.memory_connections = defaultdict(dict, data.get('memory_connections', {}))
            self.co_activation_count = defaultdict(int, data.get('co_activation_count', {}))
            
            # 恢复激活历史
            activation_history_data = data.get('activation_history', {})
            for memory_id, events in activation_history_data.items():
                self.activation_history[memory_id] = [
                    {
                        'timestamp': datetime.fromisoformat(event['timestamp']),
                        'strength': event['strength'],
                        'context': event['context']
                    }
                    for event in events
                ]
            
            # 更新参数
            params = data.get('parameters', {})
            self.learning_rate = params.get('learning_rate', self.learning_rate)
            self.decay_rate = params.get('decay_rate', self.decay_rate)
            
            connections_count = sum(len(conns) for conns in self.memory_connections.values()) // 2
            logger.info(f"成功加载突触可塑性数据，包含 {connections_count} 个记忆连接")
            
        except Exception as e:
            logger.error(f"加载突触可塑性数据失败: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._save_plasticity_data()