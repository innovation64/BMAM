"""
Memory Optimizer - MMR去冗和统一记忆要点系统
内存优化器 - 实现Maximal Marginal Relevance (MMR) 去重和统一Prompt模式
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import hashlib


@dataclass
class MemoryItem:
    """优化的记忆项结构"""
    id: str
    content: str
    embedding: Optional[np.ndarray] = None
    importance: float = 0.5
    timestamp: datetime = None
    memory_type: str = "episodic"
    emotion_tags: List[str] = None
    context_tags: List[str] = None
    similarity_hash: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.emotion_tags is None:
            self.emotion_tags = []
        if self.context_tags is None:
            self.context_tags = []
        if self.similarity_hash is None:
            self.similarity_hash = self._compute_similarity_hash()
    
    def _compute_similarity_hash(self) -> str:
        """计算相似性哈希用于去重"""
        # 提取关键特征用于去重
        content_words = set(self.content.lower().split())
        # 移除常见停用词
        stop_words = {'的', '是', '在', '有', '和', '我', '你', '他', '她', '它', 'the', 'is', 'in', 'and', 'a', 'to'}
        key_words = content_words - stop_words
        
        # 创建特征向量
        feature_string = f"{sorted(key_words)}_{self.memory_type}_{sorted(self.context_tags)}"
        return hashlib.md5(feature_string.encode()).hexdigest()[:8]


class MMROptimizer:
    """Maximal Marginal Relevance 优化器"""
    
    def __init__(self, lambda_param: float = 0.7):
        """
        初始化MMR优化器
        
        Args:
            lambda_param: 平衡相关性和多样性的参数 (0-1)
                         1.0 = 只考虑相关性, 0.0 = 只考虑多样性
        """
        self.lambda_param = lambda_param
    
    def compute_cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        if vec1 is None or vec2 is None:
            return 0.0
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def select_diverse_memories(self, 
                              query_embedding: np.ndarray,
                              candidate_memories: List[MemoryItem],
                              k: int = 5) -> List[MemoryItem]:
        """
        使用MMR选择多样化的记忆项
        
        Args:
            query_embedding: 查询的嵌入向量
            candidate_memories: 候选记忆列表
            k: 选择的记忆数量
            
        Returns:
            选择的多样化记忆列表
        """
        if not candidate_memories or k <= 0:
            return []
        
        selected_memories = []
        remaining_memories = candidate_memories.copy()
        
        # 1. 选择与查询最相关的第一个记忆
        if remaining_memories:
            best_similarity = -1
            best_memory = None
            
            for memory in remaining_memories:
                if memory.embedding is not None:
                    similarity = self.compute_cosine_similarity(query_embedding, memory.embedding)
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_memory = memory
            
            if best_memory:
                selected_memories.append(best_memory)
                remaining_memories.remove(best_memory)
        
        # 2. 迭代选择剩余记忆，平衡相关性和多样性
        while len(selected_memories) < k and remaining_memories:
            best_score = -1
            best_memory = None
            
            for memory in remaining_memories:
                if memory.embedding is None:
                    continue
                
                # 计算与查询的相关性
                relevance = self.compute_cosine_similarity(query_embedding, memory.embedding)
                
                # 计算与已选记忆的最大相似度 (多样性惩罚)
                max_similarity = 0
                for selected in selected_memories:
                    if selected.embedding is not None:
                        similarity = self.compute_cosine_similarity(memory.embedding, selected.embedding)
                        max_similarity = max(max_similarity, similarity)
                
                # MMR评分
                mmr_score = (self.lambda_param * relevance - 
                           (1 - self.lambda_param) * max_similarity)
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_memory = memory
            
            if best_memory:
                selected_memories.append(best_memory)
                remaining_memories.remove(best_memory)
            else:
                break
        
        return selected_memories


class MemoryDeduplicator:
    """记忆去重器"""
    
    def __init__(self, similarity_threshold: float = 0.85):
        """
        初始化去重器
        
        Args:
            similarity_threshold: 相似度阈值，超过此值认为是重复
        """
        self.similarity_threshold = similarity_threshold
    
    def deduplicate_by_hash(self, memories: List[MemoryItem]) -> List[MemoryItem]:
        """基于相似性哈希的快速去重"""
        seen_hashes = set()
        unique_memories = []
        
        # 按重要性和时间排序，保留最重要最新的
        sorted_memories = sorted(
            memories, 
            key=lambda m: (m.importance, m.timestamp),
            reverse=True
        )
        
        for memory in sorted_memories:
            if memory.similarity_hash not in seen_hashes:
                seen_hashes.add(memory.similarity_hash)
                unique_memories.append(memory)
        
        return unique_memories
    
    def deduplicate_by_embedding(self, memories: List[MemoryItem]) -> List[MemoryItem]:
        """基于嵌入向量的精确去重"""
        unique_memories = []
        
        for memory in memories:
            if memory.embedding is None:
                unique_memories.append(memory)
                continue
            
            is_duplicate = False
            for existing in unique_memories:
                if existing.embedding is not None:
                    similarity = MMROptimizer().compute_cosine_similarity(
                        memory.embedding, existing.embedding
                    )
                    if similarity >= self.similarity_threshold:
                        # 保留更重要或更新的记忆
                        if memory.importance > existing.importance or \
                           (memory.importance == existing.importance and 
                            memory.timestamp > existing.timestamp):
                            unique_memories.remove(existing)
                            unique_memories.append(memory)
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                unique_memories.append(memory)
        
        return unique_memories


class UnifiedMemoryPromptBuilder:
    """统一记忆要点Prompt构建器"""
    
    def __init__(self):
        self.prompt_templates = {
            'episodic': """
相关经历记忆：
{memories}
""",
            'semantic': """  
相关知识记忆：
{memories}
""",
            'emotional': """
相关情感记忆：
{memories}
""",
            'procedural': """
相关程序记忆：
{memories}
"""
        }
    
    def build_unified_context(self, 
                            memories: List[MemoryItem],
                            user_query: str,
                            max_length: int = 2000) -> str:
        """构建统一的记忆上下文"""
        if not memories:
            return ""
        
        # 按类型分组
        memory_groups = {}
        for memory in memories:
            memory_type = memory.memory_type
            if memory_type not in memory_groups:
                memory_groups[memory_type] = []
            memory_groups[memory_type].append(memory)
        
        # 构建分类的记忆要点
        context_parts = []
        context_parts.append(f"**用户查询**: {user_query}")
        context_parts.append("")
        
        total_length = len(user_query) + 50  # 留出余量
        
        for memory_type, type_memories in memory_groups.items():
            if total_length >= max_length:
                break
                
            template = self.prompt_templates.get(memory_type, self.prompt_templates['episodic'])
            
            # 构建该类型的记忆要点
            memory_points = []
            for i, memory in enumerate(type_memories, 1):
                if total_length >= max_length:
                    break
                
                # 生成记忆要点
                memory_point = self._format_memory_point(memory, i)
                if total_length + len(memory_point) < max_length:
                    memory_points.append(memory_point)
                    total_length += len(memory_point)
                else:
                    break
            
            if memory_points:
                formatted_section = template.format(memories='\n'.join(memory_points))
                context_parts.append(formatted_section)
        
        # 添加记忆使用指南
        context_parts.append("""
**记忆使用指南**:
- 优先使用最相关和最重要的记忆信息
- 如果记忆中有具体的用户偏好或历史信息，务必体现在回复中
- 保持回答的连贯性，让用户感受到你"记住"了之前的对话
- 当记忆信息不足时，诚实说明并询问更多信息
""")
        
        return '\n'.join(context_parts)
    
    def _format_memory_point(self, memory: MemoryItem, index: int) -> str:
        """格式化单个记忆要点"""
        # 基本信息
        point = f"{index}. {memory.content}"
        
        # 添加重要性指标
        if memory.importance > 0.7:
            point += " [重要]"
        
        # 添加时间信息（相对时间）
        time_desc = self._get_relative_time(memory.timestamp)
        if time_desc:
            point += f" ({time_desc})"
        
        # 添加情感标签
        if memory.emotion_tags:
            emotions = ', '.join(memory.emotion_tags[:2])  # 最多显示2个
            point += f" [情感: {emotions}]"
        
        return point
    
    def _get_relative_time(self, timestamp: datetime) -> str:
        """获取相对时间描述"""
        if not timestamp:
            return ""
        
        now = datetime.now()
        diff = now - timestamp
        
        if diff.days == 0:
            if diff.seconds < 3600:
                return "刚才"
            elif diff.seconds < 7200:
                return "1小时前"
            else:
                return f"{diff.seconds // 3600}小时前"
        elif diff.days == 1:
            return "昨天"
        elif diff.days < 7:
            return f"{diff.days}天前"
        elif diff.days < 30:
            return f"{diff.days // 7}周前"
        else:
            return f"{diff.days // 30}个月前"


class MemoryOptimizer:
    """记忆系统优化器 - 集成MMR和去重功能"""
    
    def __init__(self, 
                 mmr_lambda: float = 0.7,
                 dedup_threshold: float = 0.85):
        self.mmr_optimizer = MMROptimizer(mmr_lambda)
        self.deduplicator = MemoryDeduplicator(dedup_threshold)
        self.prompt_builder = UnifiedMemoryPromptBuilder()
    
    def optimize_memory_retrieval(self,
                                query_embedding: np.ndarray,
                                raw_memories: List[Dict[str, Any]],
                                target_count: int = 5) -> Tuple[List[MemoryItem], str]:
        """
        优化记忆检索 - 完整的处理管道
        
        Args:
            query_embedding: 查询嵌入向量
            raw_memories: 原始记忆数据
            target_count: 目标记忆数量
            
        Returns:
            优化后的记忆列表和统一的上下文文本
        """
        # 1. 转换为MemoryItem对象
        memory_items = []
        for raw_mem in raw_memories:
            item = MemoryItem(
                id=raw_mem.get('id', ''),
                content=raw_mem.get('content', ''),
                embedding=raw_mem.get('embedding'),
                importance=raw_mem.get('importance', 0.5),
                timestamp=raw_mem.get('timestamp', datetime.now()),
                memory_type=raw_mem.get('memory_type', 'episodic'),
                emotion_tags=raw_mem.get('emotion_tags', []),
                context_tags=raw_mem.get('context_tags', [])
            )
            memory_items.append(item)
        
        # 2. 快速哈希去重
        deduped_memories = self.deduplicator.deduplicate_by_hash(memory_items)
        
        # 3. 如果仍然太多，进行嵌入去重
        if len(deduped_memories) > target_count * 2:
            deduped_memories = self.deduplicator.deduplicate_by_embedding(deduped_memories)
        
        # 4. MMR多样性选择
        if len(deduped_memories) > target_count:
            final_memories = self.mmr_optimizer.select_diverse_memories(
                query_embedding, deduped_memories, target_count
            )
        else:
            final_memories = deduped_memories
        
        # 5. 构建统一上下文
        context = self.prompt_builder.build_unified_context(
            final_memories, "用户查询"  # 这里应该传入实际查询
        )
        
        return final_memories, context
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """获取优化统计信息"""
        return {
            'mmr_lambda': self.mmr_optimizer.lambda_param,
            'dedup_threshold': self.deduplicator.similarity_threshold,
            'optimizer_version': '1.0'
        }