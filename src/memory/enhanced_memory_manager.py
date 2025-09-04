"""增强的条件记忆管理器，优化对话延续性和反馈学习"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from sentence_transformers import SentenceTransformer
import torch
from .condition_memory import ConditionalMemory


class EnhancedMemoryManager:
    """增强的记忆管理器，提供更好的上下文感知和自适应学习"""
    
    def __init__(self):
        self.memory = ConditionalMemory()
        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # 对话历史缓存
        self.dialogue_cache = []
        self.max_dialogue_history = 10
        
        # 反馈学习历史
        self.feedback_history = []
        
        # 记忆激活阈值
        self.activation_threshold = 0.5
        
    def add_dialogue_turn(self, user_input: str, system_response: str, turn_id: int):
        """添加对话轮次到历史记录并提取条件"""
        turn_data = {
            "turn_id": turn_id,
            "user_input": user_input,
            "system_response": system_response,
            "timestamp": datetime.now(),
            "embedding": self.sentence_model.encode(user_input + " " + system_response)
        }
        
        self.dialogue_cache.append(turn_data)
        
        # 保持缓存大小
        if len(self.dialogue_cache) > self.max_dialogue_history:
            self.dialogue_cache.pop(0)
        
        # 提取并存储重要条件
        self._extract_conditions_from_turn(turn_data)
        
    def _extract_conditions_from_turn(self, turn_data: Dict[str, Any]):
        """从对话轮次中提取条件"""
        # 简化的条件提取逻辑
        user_input = turn_data["user_input"].lower()
        
        # 提取硬约束
        if any(word in user_input for word in ["must", "always", "never", "require"]):
            condition = {
                "text": turn_data["user_input"],
                "source_turn": turn_data["turn_id"],
                "confidence": 0.9,
                "embedding": turn_data["embedding"]
            }
            self.memory.add_condition(condition, "hard_constraints", importance_score=0.9)
        
        # 提取软偏好
        elif any(word in user_input for word in ["prefer", "like", "want", "hope"]):
            condition = {
                "text": turn_data["user_input"],
                "source_turn": turn_data["turn_id"],
                "confidence": 0.7,
                "embedding": turn_data["embedding"]
            }
            self.memory.add_condition(condition, "soft_preferences", importance_score=0.7)
    
    def get_relevant_context(self, current_query: str, top_k: int = 5) -> Dict[str, Any]:
        """获取与当前查询相关的上下文"""
        query_embedding = self.sentence_model.encode(current_query)
        
        # 1. 获取相关的历史对话
        dialogue_context = self._get_relevant_dialogue_turns(query_embedding, top_k=3)
        
        # 2. 获取相关的条件记忆
        relevant_conditions = self._get_relevant_conditions(query_embedding, top_k=top_k)
        
        # 3. 计算上下文连贯性分数
        coherence_score = self._calculate_coherence_score(dialogue_context, relevant_conditions)
        
        return {
            "dialogue_history": dialogue_context,
            "active_conditions": relevant_conditions,
            "coherence_score": coherence_score,
            "should_continue_context": coherence_score > self.activation_threshold
        }
    
    def _get_relevant_dialogue_turns(self, query_embedding: np.ndarray, top_k: int = 3) -> List[Dict[str, Any]]:
        """获取最相关的对话轮次"""
        if not self.dialogue_cache:
            return []
        
        # 计算相似度
        similarities = []
        for turn in self.dialogue_cache:
            similarity = np.dot(query_embedding, turn["embedding"]) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(turn["embedding"])
            )
            similarities.append((similarity, turn))
        
        # 排序并返回top_k
        similarities.sort(key=lambda x: x[0], reverse=True)
        return [turn for _, turn in similarities[:top_k]]
    
    def _get_relevant_conditions(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        """获取最相关的条件"""
        all_conditions = self.memory.get_all_conditions(min_importance=0.3)
        
        if not all_conditions:
            return []
        
        # 计算相似度（如果条件有embedding）
        relevant_conditions = []
        for condition in all_conditions:
            if "embedding" in condition:
                similarity = np.dot(query_embedding, condition["embedding"]) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(condition["embedding"])
                )
                condition["current_relevance"] = similarity
                relevant_conditions.append(condition)
        
        # 排序并返回top_k
        relevant_conditions.sort(key=lambda x: x["current_relevance"], reverse=True)
        return relevant_conditions[:top_k]
    
    def _calculate_coherence_score(self, dialogue_context: List[Dict], conditions: List[Dict]) -> float:
        """计算上下文连贯性分数"""
        if not dialogue_context and not conditions:
            return 0.0
        
        # 基于多个因素计算连贯性
        scores = []
        
        # 1. 时间连贯性（最近的对话权重更高）
        if dialogue_context:
            time_scores = []
            current_time = datetime.now()
            for turn in dialogue_context:
                time_diff = (current_time - turn["timestamp"]).total_seconds() / 3600  # 小时
                time_score = np.exp(-time_diff / 24)  # 24小时衰减
                time_scores.append(time_score)
            scores.append(np.mean(time_scores))
        
        # 2. 条件激活度
        if conditions:
            activation_scores = [c.get("current_relevance", 0) * c.get("importance_score", 0.5) 
                               for c in conditions]
            scores.append(np.mean(activation_scores))
        
        return np.mean(scores) if scores else 0.0
    
    def learn_from_feedback(self, original_response: str, feedback: str, improved_response: str):
        """从人类反馈中学习"""
        feedback_entry = {
            "timestamp": datetime.now(),
            "original": original_response,
            "feedback": feedback,
            "improved": improved_response,
            "feedback_embedding": self.sentence_model.encode(feedback),
            "improvement_embedding": self.sentence_model.encode(improved_response)
        }
        
        self.feedback_history.append(feedback_entry)
        
        # 提取反馈中的新条件
        self._extract_conditions_from_feedback(feedback, feedback_entry)
        
        # 更新相关条件的重要性
        self._update_condition_importance_from_feedback(feedback_entry)
    
    def _extract_conditions_from_feedback(self, feedback: str, feedback_entry: Dict[str, Any]):
        """从反馈中提取新条件"""
        feedback_lower = feedback.lower()
        
        # 检测纠正性反馈
        if any(word in feedback_lower for word in ["should", "better", "instead", "actually"]):
            condition = {
                "text": feedback,
                "source_turn": -1,  # 特殊标记表示来自反馈
                "confidence": 0.85,
                "feedback_derived": True,
                "embedding": feedback_entry["feedback_embedding"]
            }
            self.memory.add_condition(condition, "hard_constraints", importance_score=0.85)
    
    def _update_condition_importance_from_feedback(self, feedback_entry: Dict[str, Any]):
        """根据反馈更新条件重要性"""
        # 找到与反馈相关的条件
        feedback_embedding = feedback_entry["feedback_embedding"]
        all_conditions = self.memory.get_all_conditions()
        
        updates = {}
        for condition in all_conditions:
            if "embedding" in condition:
                similarity = np.dot(feedback_embedding, condition["embedding"]) / (
                    np.linalg.norm(feedback_embedding) * np.linalg.norm(condition["embedding"])
                )
                
                # 如果条件与反馈高度相关，增加其重要性
                if similarity > 0.7:
                    new_score = min(1.0, condition["importance_score"] + 0.1)
                    updates[condition["id"]] = new_score
        
        if updates:
            self.memory.update_importance_scores(updates)
    
    def apply_adaptive_compression(self, compression_ratio: float = 0.7):
        """应用自适应记忆压缩"""
        # 1. 应用时间衰减
        self.memory.decay_importance_scores(decay_factor=0.95)
        
        # 2. 移除低重要性条件
        all_conditions = self.memory.get_all_conditions()
        total_conditions = len(all_conditions)
        target_size = int(total_conditions * compression_ratio)
        
        if total_conditions > target_size:
            # 按重要性排序
            all_conditions.sort(key=lambda x: x["importance_score"], reverse=True)
            
            # 移除最不重要的条件
            to_remove = all_conditions[target_size:]
            for condition in to_remove:
                self.memory.remove_condition(condition["id"])
        
        # 3. 清理过期的对话缓存
        current_time = datetime.now()
        self.dialogue_cache = [
            turn for turn in self.dialogue_cache 
            if (current_time - turn["timestamp"]).total_seconds() < 86400  # 24小时
        ]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        stats = self.memory.get_memory_stats()
        
        # 添加额外指标
        stats["dialogue_cache_size"] = len(self.dialogue_cache)
        stats["feedback_history_size"] = len(self.feedback_history)
        stats["average_coherence_score"] = self._calculate_average_coherence()
        
        return stats
    
    def _calculate_average_coherence(self) -> float:
        """计算平均连贯性分数"""
        if not self.dialogue_cache:
            return 0.0
        
        scores = []
        for i in range(min(5, len(self.dialogue_cache))):
            turn = self.dialogue_cache[-(i+1)]
            context = self.get_relevant_context(turn["user_input"])
            scores.append(context["coherence_score"])
        
        return np.mean(scores) if scores else 0.0