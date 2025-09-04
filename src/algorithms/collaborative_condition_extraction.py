#!/usr/bin/env python3
"""
协作式条件提取算法 (Collaborative Condition Extraction Algorithm)
基于多智能体协作的新型条件提取方法

核心创新:
1. 多阶段协作提取策略
2. 智能体间的交叉验证机制
3. 动态置信度调整算法
4. 条件间关联性分析
5. 实时学习与适应机制

理论基础:
- 分布式认知理论
- 集体智能原理
- 贝叶斯推理框架
- 图神经网络方法

Copyright (c) 2024 Advanced AI Research Lab
"""

import asyncio
import numpy as np
import networkx as nx
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set, Any, Union
from collections import defaultdict, deque
import logging
import time
import json
import re
from scipy import sparse
from sklearn.metrics.pairwise import cosine_similarity
import hashlib


class ConditionType(Enum):
    """条件类型枚举"""
    EXPLICIT = "explicit"          # 显式条件
    IMPLICIT = "implicit"          # 隐式条件
    CONTEXTUAL = "contextual"      # 上下文条件
    TEMPORAL = "temporal"          # 时间条件
    CAUSAL = "causal"             # 因果条件
    PROBABILISTIC = "probabilistic" # 概率条件


class ExtractionStrategy(Enum):
    """提取策略枚举"""
    SYNTACTIC_ANALYSIS = "syntactic"
    SEMANTIC_ANALYSIS = "semantic"
    PRAGMATIC_ANALYSIS = "pragmatic"
    CONTEXTUAL_INFERENCE = "contextual"
    PATTERN_MATCHING = "pattern"
    NEURAL_EXTRACTION = "neural"


@dataclass
class Condition:
    """条件数据结构"""
    condition_id: str
    condition_type: ConditionType
    content: str
    confidence: float
    evidence: List[str] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)
    temporal_info: Optional[Dict[str, Any]] = None
    semantic_embedding: Optional[np.ndarray] = None
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """后初始化处理"""
        if not self.condition_id:
            self.condition_id = self._generate_id()
        
        if self.confidence < 0 or self.confidence > 1:
            raise ValueError("Confidence must be between 0 and 1")
    
    def _generate_id(self) -> str:
        """生成条件ID"""
        content_hash = hashlib.md5(self.content.encode()).hexdigest()[:8]
        return f"{self.condition_type.value}_{content_hash}_{int(time.time())}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'condition_id': self.condition_id,
            'condition_type': self.condition_type.value,
            'content': self.content,
            'confidence': self.confidence,
            'evidence': self.evidence,
            'dependencies': list(self.dependencies),
            'temporal_info': self.temporal_info,
            'extraction_metadata': self.extraction_metadata
        }


@dataclass
class ExtractionContext:
    """提取上下文"""
    query: str
    conversation_history: List[str] = field(default_factory=list)
    user_profile: Dict[str, Any] = field(default_factory=dict)
    domain_knowledge: Dict[str, Any] = field(default_factory=dict)
    temporal_context: Dict[str, Any] = field(default_factory=dict)
    environmental_factors: Dict[str, Any] = field(default_factory=dict)
    
    def get_context_signature(self) -> str:
        """获取上下文签名"""
        context_str = f"{self.query}_{len(self.conversation_history)}_{hash(str(self.user_profile))}"
        return hashlib.md5(context_str.encode()).hexdigest()


@dataclass
class CollaborationResult:
    """协作结果"""
    primary_conditions: List[Condition]
    cross_validated_conditions: List[Condition]
    consensus_conditions: List[Condition]
    conflicting_conditions: List[Tuple[Condition, Condition, float]]
    collaboration_metrics: Dict[str, float]
    extraction_graph: Optional[nx.DiGraph] = None


class ConditionExtractor(ABC):
    """条件提取器抽象基类"""
    
    def __init__(self, extractor_id: str, strategy: ExtractionStrategy):
        self.extractor_id = extractor_id
        self.strategy = strategy
        self.performance_history = deque(maxlen=100)
        self.specialization_score = 0.0
        self.collaboration_weights = {}
    
    @abstractmethod
    async def extract_conditions(self, 
                               context: ExtractionContext) -> List[Condition]:
        """提取条件"""
        pass
    
    @abstractmethod
    async def validate_condition(self, 
                               condition: Condition,
                               context: ExtractionContext) -> float:
        """验证条件"""
        pass
    
    async def cross_validate(self, 
                           conditions: List[Condition],
                           other_extractors: List['ConditionExtractor'],
                           context: ExtractionContext) -> List[Condition]:
        """交叉验证条件"""
        validated_conditions = []
        
        for condition in conditions:
            validation_scores = []
            
            # 自验证
            self_score = await self.validate_condition(condition, context)
            validation_scores.append(self_score)
            
            # 其他提取器验证
            for extractor in other_extractors:
                try:
                    score = await extractor.validate_condition(condition, context)
                    validation_scores.append(score)
                except Exception as e:
                    logging.warning(f"Cross-validation failed with {extractor.extractor_id}: {e}")
            
            # 计算协作置信度
            if validation_scores:
                collaborative_confidence = self._calculate_collaborative_confidence(
                    condition.confidence, validation_scores
                )
                
                # 更新条件置信度
                updated_condition = Condition(
                    condition_id=condition.condition_id,
                    condition_type=condition.condition_type,
                    content=condition.content,
                    confidence=collaborative_confidence,
                    evidence=condition.evidence + [f"cross_validated_by_{len(validation_scores)}_extractors"],
                    dependencies=condition.dependencies,
                    temporal_info=condition.temporal_info,
                    semantic_embedding=condition.semantic_embedding,
                    extraction_metadata={
                        **condition.extraction_metadata,
                        'cross_validation_scores': validation_scores,
                        'collaborative_confidence': collaborative_confidence
                    }
                )
                
                validated_conditions.append(updated_condition)
        
        return validated_conditions
    
    def _calculate_collaborative_confidence(self, 
                                          original_confidence: float,
                                          validation_scores: List[float]) -> float:
        """计算协作置信度"""
        if not validation_scores:
            return original_confidence
        
        # 加权平均，给予原始置信度更高权重
        weights = [2.0] + [1.0] * (len(validation_scores) - 1)
        weighted_sum = sum(score * weight for score, weight in zip(validation_scores, weights))
        total_weight = sum(weights)
        
        collaborative_confidence = weighted_sum / total_weight
        
        # 应用置信度增强
        if len(validation_scores) > 2:  # 多个验证器同意
            avg_validation = np.mean(validation_scores[1:])  # 排除自验证
            if avg_validation > 0.7:  # 高一致性
                collaborative_confidence = min(collaborative_confidence * 1.1, 1.0)
        
        return collaborative_confidence


class SyntacticConditionExtractor(ConditionExtractor):
    """句法条件提取器"""
    
    def __init__(self, extractor_id: str = "syntactic_extractor"):
        super().__init__(extractor_id, ExtractionStrategy.SYNTACTIC_ANALYSIS)
        self.syntactic_patterns = self._initialize_patterns()
        self.dependency_parser = self._initialize_parser()
    
    def _initialize_patterns(self) -> Dict[ConditionType, List[str]]:
        """初始化句法模式"""
        return {
            ConditionType.EXPLICIT: [
                r'\bif\s+(.+?)\s+then\b',
                r'\bwhen\s+(.+?)\s+,\s*(.+)',
                r'\bunless\s+(.+?)\s+,\s*(.+)',
                r'\bprovided\s+that\s+(.+?)\s+,\s*(.+)',
                r'\bgiven\s+that\s+(.+?)\s+,\s*(.+)',
            ],
            ConditionType.TEMPORAL: [
                r'\bafter\s+(.+?)\s+,\s*(.+)',
                r'\bbefore\s+(.+?)\s+,\s*(.+)',
                r'\bwhile\s+(.+?)\s+,\s*(.+)',
                r'\bduring\s+(.+?)\s+,\s*(.+)',
                r'\bonce\s+(.+?)\s+,\s*(.+)',
            ],
            ConditionType.CAUSAL: [
                r'\bbecause\s+(.+?)\s+,\s*(.+)',
                r'\bsince\s+(.+?)\s+,\s*(.+)',
                r'\bas\s+a\s+result\s+of\s+(.+?)\s+,\s*(.+)',
                r'\bdue\s+to\s+(.+?)\s+,\s*(.+)',
            ]
        }
    
    def _initialize_parser(self):
        """初始化依存句法分析器"""
        # 这里应该初始化真实的依存分析器
        # 为了演示，返回一个模拟对象
        class MockParser:
            def parse(self, text):
                return {"dependencies": [], "pos_tags": []}
        
        return MockParser()
    
    async def extract_conditions(self, context: ExtractionContext) -> List[Condition]:
        """提取句法条件"""
        conditions = []
        text = context.query
        
        # 句法模式匹配
        for condition_type, patterns in self.syntactic_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    condition_content = match.group(1) if match.groups() else match.group(0)
                    
                    condition = Condition(
                        condition_id="",
                        condition_type=condition_type,
                        content=condition_content.strip(),
                        confidence=0.8,  # 句法匹配的基础置信度
                        evidence=[f"syntactic_pattern_{pattern}"],
                        extraction_metadata={
                            'extraction_method': 'syntactic_pattern_matching',
                            'pattern_used': pattern,
                            'match_position': (match.start(), match.end())
                        }
                    )
                    
                    conditions.append(condition)
        
        # 依存句法分析
        dependency_conditions = await self._extract_dependency_conditions(text)
        conditions.extend(dependency_conditions)
        
        # 后处理和去重
        conditions = self._post_process_conditions(conditions)
        
        return conditions
    
    async def _extract_dependency_conditions(self, text: str) -> List[Condition]:
        """基于依存关系提取条件"""
        conditions = []
        
        # 模拟依存分析
        parse_result = self.dependency_parser.parse(text)
        
        # 查找条件关系
        conditional_dependencies = ['advcl', 'ccomp', 'xcomp']
        
        for dep_type in conditional_dependencies:
            # 模拟找到条件依存关系
            condition = Condition(
                condition_id="",
                condition_type=ConditionType.IMPLICIT,
                content=f"dependency_based_condition_{dep_type}",
                confidence=0.6,
                evidence=[f"dependency_relation_{dep_type}"],
                extraction_metadata={
                    'extraction_method': 'dependency_parsing',
                    'dependency_type': dep_type
                }
            )
            conditions.append(condition)
        
        return conditions
    
    async def validate_condition(self, 
                               condition: Condition,
                               context: ExtractionContext) -> float:
        """验证条件的句法合理性"""
        # 检查条件的句法结构
        syntactic_score = self._evaluate_syntactic_structure(condition.content)
        
        # 检查与上下文的句法一致性
        context_consistency = self._evaluate_context_consistency(
            condition.content, context.query
        )
        
        # 综合评分
        validation_score = (syntactic_score + context_consistency) / 2
        
        return validation_score
    
    def _evaluate_syntactic_structure(self, text: str) -> float:
        """评估句法结构"""
        # 简化的句法结构评估
        structure_indicators = [
            len(text.split()) > 3,  # 基本长度
            any(punct in text for punct in [',', '.', ';']),  # 标点符号
            any(word in text.lower() for word in ['if', 'when', 'while']),  # 条件词
        ]
        
        return sum(structure_indicators) / len(structure_indicators)
    
    def _evaluate_context_consistency(self, condition: str, query: str) -> float:
        """评估与上下文的一致性"""
        condition_words = set(condition.lower().split())
        query_words = set(query.lower().split())
        
        if not condition_words or not query_words:
            return 0.0
        
        # 计算词汇重叠
        overlap = len(condition_words & query_words)
        total_unique = len(condition_words | query_words)
        
        return overlap / total_unique if total_unique > 0 else 0.0
    
    def _post_process_conditions(self, conditions: List[Condition]) -> List[Condition]:
        """后处理条件"""
        if not conditions:
            return conditions
        
        # 去重
        unique_conditions = []
        seen_contents = set()
        
        for condition in conditions:
            content_key = condition.content.lower().strip()
            if content_key not in seen_contents:
                seen_contents.add(content_key)
                unique_conditions.append(condition)
        
        # 按置信度排序
        unique_conditions.sort(key=lambda x: x.confidence, reverse=True)
        
        return unique_conditions


class SemanticConditionExtractor(ConditionExtractor):
    """语义条件提取器"""
    
    def __init__(self, extractor_id: str = "semantic_extractor"):
        super().__init__(extractor_id, ExtractionStrategy.SEMANTIC_ANALYSIS)
        self.semantic_model = self._initialize_semantic_model()
        self.concept_graph = self._build_concept_graph()
        self.embedding_cache = {}
    
    def _initialize_semantic_model(self):
        """初始化语义模型"""
        # 模拟语义模型
        class MockSemanticModel:
            def encode(self, texts):
                # 返回随机嵌入向量
                if isinstance(texts, str):
                    texts = [texts]
                return np.random.randn(len(texts), 384)
            
            def similarity(self, text1, text2):
                return np.random.uniform(0.4, 0.9)
        
        return MockSemanticModel()
    
    def _build_concept_graph(self) -> nx.Graph:
        """构建概念图"""
        G = nx.Graph()
        
        # 添加条件相关的概念节点
        condition_concepts = [
            'requirement', 'constraint', 'prerequisite', 'dependency',
            'assumption', 'limitation', 'specification', 'criteria'
        ]
        
        for concept in condition_concepts:
            G.add_node(concept, node_type='concept')
        
        # 添加概念间的关系
        concept_relations = [
            ('requirement', 'constraint', 0.8),
            ('prerequisite', 'dependency', 0.9),
            ('assumption', 'limitation', 0.7),
            ('specification', 'criteria', 0.8),
        ]
        
        for concept1, concept2, weight in concept_relations:
            G.add_edge(concept1, concept2, weight=weight)
        
        return G
    
    async def extract_conditions(self, context: ExtractionContext) -> List[Condition]:
        """提取语义条件"""
        conditions = []
        
        # 语义分割
        segments = await self._semantic_segmentation(context.query)
        
        # 为每个段落提取条件
        for segment in segments:
            segment_conditions = await self._extract_segment_conditions(segment, context)
            conditions.extend(segment_conditions)
        
        # 语义聚类
        clustered_conditions = await self._semantic_clustering(conditions)
        
        # 概念图推理
        enriched_conditions = await self._concept_graph_reasoning(clustered_conditions, context)
        
        return enriched_conditions
    
    async def _semantic_segmentation(self, text: str) -> List[str]:
        """语义分割"""
        # 简化的语义分割
        sentences = re.split(r'[.!?]+', text)
        segments = [s.strip() for s in sentences if s.strip()]
        
        # 基于语义相似性合并相关段落
        if len(segments) > 1:
            merged_segments = []
            current_segment = segments[0]
            
            for i in range(1, len(segments)):
                similarity = self.semantic_model.similarity(current_segment, segments[i])
                
                if similarity > 0.7:  # 高相似性，合并
                    current_segment += " " + segments[i]
                else:
                    merged_segments.append(current_segment)
                    current_segment = segments[i]
            
            merged_segments.append(current_segment)
            return merged_segments
        
        return segments
    
    async def _extract_segment_conditions(self, 
                                        segment: str,
                                        context: ExtractionContext) -> List[Condition]:
        """从段落中提取条件"""
        conditions = []
        
        # 获取语义嵌入
        embedding = self._get_embedding(segment)
        
        # 语义模式匹配
        semantic_patterns = await self._identify_semantic_patterns(segment, embedding)
        
        for pattern_type, confidence in semantic_patterns.items():
            if confidence > 0.5:  # 阈值
                condition = Condition(
                    condition_id="",
                    condition_type=self._map_pattern_to_condition_type(pattern_type),
                    content=segment,
                    confidence=confidence,
                    evidence=[f"semantic_pattern_{pattern_type}"],
                    semantic_embedding=embedding,
                    extraction_metadata={
                        'extraction_method': 'semantic_pattern_matching',
                        'pattern_type': pattern_type,
                        'semantic_confidence': confidence
                    }
                )
                conditions.append(condition)
        
        return conditions
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """获取文本嵌入"""
        text_key = hashlib.md5(text.encode()).hexdigest()
        
        if text_key not in self.embedding_cache:
            embedding = self.semantic_model.encode([text])[0]
            self.embedding_cache[text_key] = embedding
        
        return self.embedding_cache[text_key]
    
    async def _identify_semantic_patterns(self, 
                                        text: str,
                                        embedding: np.ndarray) -> Dict[str, float]:
        """识别语义模式"""
        patterns = {}
        
        # 条件性语义模式
        conditional_keywords = ['require', 'need', 'must', 'should', 'depend', 'assume']
        conditional_score = sum(1 for keyword in conditional_keywords 
                              if keyword in text.lower()) / len(conditional_keywords)
        patterns['conditional'] = conditional_score
        
        # 时间性语义模式
        temporal_keywords = ['when', 'after', 'before', 'during', 'while', 'until']
        temporal_score = sum(1 for keyword in temporal_keywords 
                           if keyword in text.lower()) / len(temporal_keywords)
        patterns['temporal'] = temporal_score
        
        # 因果性语义模式
        causal_keywords = ['because', 'since', 'due to', 'result', 'cause', 'lead to']
        causal_score = sum(1 for keyword in causal_keywords 
                         if keyword in text.lower()) / len(causal_keywords)
        patterns['causal'] = causal_score
        
        # 上下文相关性模式
        contextual_score = self._calculate_contextual_relevance(text, embedding)
        patterns['contextual'] = contextual_score
        
        return patterns
    
    def _calculate_contextual_relevance(self, text: str, embedding: np.ndarray) -> float:
        """计算上下文相关性"""
        # 简化的上下文相关性计算
        context_indicators = ['system', 'user', 'interface', 'function', 'feature']
        relevance_score = sum(1 for indicator in context_indicators 
                            if indicator in text.lower()) / len(context_indicators)
        
        return min(relevance_score, 1.0)
    
    def _map_pattern_to_condition_type(self, pattern_type: str) -> ConditionType:
        """映射模式到条件类型"""
        mapping = {
            'conditional': ConditionType.EXPLICIT,
            'temporal': ConditionType.TEMPORAL,
            'causal': ConditionType.CAUSAL,
            'contextual': ConditionType.CONTEXTUAL
        }
        return mapping.get(pattern_type, ConditionType.IMPLICIT)
    
    async def _semantic_clustering(self, conditions: List[Condition]) -> List[Condition]:
        """语义聚类"""
        if len(conditions) <= 1:
            return conditions
        
        # 计算条件间的语义相似性
        embeddings = []
        for condition in conditions:
            if condition.semantic_embedding is not None:
                embeddings.append(condition.semantic_embedding)
            else:
                embedding = self._get_embedding(condition.content)
                condition.semantic_embedding = embedding
                embeddings.append(embedding)
        
        # 相似性矩阵
        embeddings_matrix = np.array(embeddings)
        similarity_matrix = cosine_similarity(embeddings_matrix)
        
        # 简化的聚类：合并高相似性条件
        clustered_conditions = []
        processed = set()
        
        for i, condition in enumerate(conditions):
            if i in processed:
                continue
            
            # 找到相似的条件
            similar_indices = [j for j in range(len(conditions)) 
                             if j != i and similarity_matrix[i][j] > 0.8 and j not in processed]
            
            if similar_indices:
                # 合并相似条件
                merged_condition = self._merge_similar_conditions(
                    [condition] + [conditions[j] for j in similar_indices]
                )
                clustered_conditions.append(merged_condition)
                
                processed.add(i)
                processed.update(similar_indices)
            else:
                clustered_conditions.append(condition)
                processed.add(i)
        
        return clustered_conditions
    
    def _merge_similar_conditions(self, similar_conditions: List[Condition]) -> Condition:
        """合并相似条件"""
        if len(similar_conditions) == 1:
            return similar_conditions[0]
        
        # 合并内容
        merged_content = " | ".join(c.content for c in similar_conditions)
        
        # 计算平均置信度
        avg_confidence = np.mean([c.confidence for c in similar_conditions])
        
        # 合并证据
        merged_evidence = []
        for condition in similar_conditions:
            merged_evidence.extend(condition.evidence)
        
        # 合并依赖
        merged_dependencies = set()
        for condition in similar_conditions:
            merged_dependencies.update(condition.dependencies)
        
        return Condition(
            condition_id="",
            condition_type=similar_conditions[0].condition_type,
            content=merged_content,
            confidence=avg_confidence,
            evidence=merged_evidence,
            dependencies=merged_dependencies,
            semantic_embedding=np.mean([c.semantic_embedding for c in similar_conditions], axis=0),
            extraction_metadata={
                'extraction_method': 'semantic_clustering',
                'merged_conditions': len(similar_conditions),
                'original_confidences': [c.confidence for c in similar_conditions]
            }
        )
    
    async def _concept_graph_reasoning(self, 
                                     conditions: List[Condition],
                                     context: ExtractionContext) -> List[Condition]:
        """基于概念图的推理"""
        enriched_conditions = []
        
        for condition in conditions:
            # 在概念图中查找相关概念
            related_concepts = self._find_related_concepts(condition.content)
            
            # 基于相关概念增强条件
            if related_concepts:
                enhanced_condition = self._enhance_condition_with_concepts(
                    condition, related_concepts
                )
                enriched_conditions.append(enhanced_condition)
            else:
                enriched_conditions.append(condition)
        
        return enriched_conditions
    
    def _find_related_concepts(self, text: str) -> List[str]:
        """在概念图中查找相关概念"""
        related_concepts = []
        
        for concept in self.concept_graph.nodes():
            if concept in text.lower():
                # 找到直接相关的概念
                related_concepts.append(concept)
                
                # 找到间接相关的概念
                neighbors = list(self.concept_graph.neighbors(concept))
                related_concepts.extend(neighbors)
        
        return list(set(related_concepts))
    
    def _enhance_condition_with_concepts(self, 
                                       condition: Condition,
                                       concepts: List[str]) -> Condition:
        """基于概念增强条件"""
        # 计算概念增强的置信度提升
        concept_boost = min(len(concepts) * 0.05, 0.2)  # 最多提升20%
        enhanced_confidence = min(condition.confidence + concept_boost, 1.0)
        
        # 添加概念信息到元数据
        enhanced_metadata = {
            **condition.extraction_metadata,
            'related_concepts': concepts,
            'concept_enhancement': concept_boost
        }
        
        return Condition(
            condition_id=condition.condition_id,
            condition_type=condition.condition_type,
            content=condition.content,
            confidence=enhanced_confidence,
            evidence=condition.evidence + [f"concept_enhanced_with_{len(concepts)}_concepts"],
            dependencies=condition.dependencies,
            temporal_info=condition.temporal_info,
            semantic_embedding=condition.semantic_embedding,
            extraction_metadata=enhanced_metadata
        )
    
    async def validate_condition(self, 
                               condition: Condition,
                               context: ExtractionContext) -> float:
        """验证条件的语义合理性"""
        # 语义一致性验证
        semantic_consistency = await self._validate_semantic_consistency(condition, context)
        
        # 概念图验证
        concept_validity = self._validate_concept_consistency(condition)
        
        # 上下文相关性验证
        context_relevance = self._validate_context_relevance(condition, context)
        
        # 综合验证分数
        validation_score = (semantic_consistency + concept_validity + context_relevance) / 3
        
        return validation_score
    
    async def _validate_semantic_consistency(self, 
                                           condition: Condition,
                                           context: ExtractionContext) -> float:
        """验证语义一致性"""
        if condition.semantic_embedding is None:
            condition.semantic_embedding = self._get_embedding(condition.content)
        
        # 与查询的语义相似性
        query_embedding = self._get_embedding(context.query)
        query_similarity = cosine_similarity(
            condition.semantic_embedding.reshape(1, -1),
            query_embedding.reshape(1, -1)
        )[0][0]
        
        # 与历史对话的语义相似性
        history_similarities = []
        for history_item in context.conversation_history[-3:]:  # 最近3轮
            history_embedding = self._get_embedding(history_item)
            similarity = cosine_similarity(
                condition.semantic_embedding.reshape(1, -1),
                history_embedding.reshape(1, -1)
            )[0][0]
            history_similarities.append(similarity)
        
        avg_history_similarity = np.mean(history_similarities) if history_similarities else 0.0
        
        # 综合语义一致性
        semantic_score = (query_similarity * 0.7 + avg_history_similarity * 0.3)
        
        return semantic_score
    
    def _validate_concept_consistency(self, condition: Condition) -> float:
        """验证概念一致性"""
        related_concepts = self._find_related_concepts(condition.content)
        
        if not related_concepts:
            return 0.5  # 中性分数
        
        # 检查概念之间的一致性
        consistency_scores = []
        for i, concept1 in enumerate(related_concepts):
            for concept2 in related_concepts[i+1:]:
                if self.concept_graph.has_edge(concept1, concept2):
                    edge_weight = self.concept_graph[concept1][concept2].get('weight', 0.5)
                    consistency_scores.append(edge_weight)
        
        if consistency_scores:
            return np.mean(consistency_scores)
        else:
            return 0.6  # 基础一致性分数
    
    def _validate_context_relevance(self, 
                                  condition: Condition,
                                  context: ExtractionContext) -> float:
        """验证上下文相关性"""
        relevance_score = 0.0
        
        # 用户档案相关性
        if context.user_profile:
            profile_keywords = []
            for value in context.user_profile.values():
                if isinstance(value, str):
                    profile_keywords.extend(value.lower().split())
            
            condition_words = set(condition.content.lower().split())
            profile_overlap = len(condition_words & set(profile_keywords))
            profile_relevance = profile_overlap / max(len(condition_words), 1)
            relevance_score += profile_relevance * 0.3
        
        # 领域知识相关性
        if context.domain_knowledge:
            domain_terms = []
            for value in context.domain_knowledge.values():
                if isinstance(value, (list, tuple)):
                    domain_terms.extend(str(item).lower() for item in value)
                elif isinstance(value, str):
                    domain_terms.extend(value.lower().split())
            
            condition_words = set(condition.content.lower().split())
            domain_overlap = len(condition_words & set(domain_terms))
            domain_relevance = domain_overlap / max(len(condition_words), 1)
            relevance_score += domain_relevance * 0.4
        
        # 时间上下文相关性
        if context.temporal_context and condition.condition_type == ConditionType.TEMPORAL:
            relevance_score += 0.3
        
        return min(relevance_score, 1.0)


class CollaborativeConditionExtractor:
    """协作式条件提取器主类"""
    
    def __init__(self):
        self.extractors: List[ConditionExtractor] = []
        self.collaboration_history = []
        self.performance_metrics = defaultdict(list)
        self.condition_graph = nx.DiGraph()
        
        # 初始化提取器
        self._initialize_extractors()
    
    def _initialize_extractors(self):
        """初始化提取器"""
        self.extractors = [
            SyntacticConditionExtractor("syntactic_001"),
            SemanticConditionExtractor("semantic_001"),
            # 可以添加更多提取器
        ]
    
    async def extract_conditions_collaboratively(self, 
                                               context: ExtractionContext) -> CollaborationResult:
        """协作式条件提取"""
        start_time = time.time()
        
        # 第一阶段：并行提取
        primary_extraction_tasks = [
            extractor.extract_conditions(context) for extractor in self.extractors
        ]
        
        primary_results = await asyncio.gather(*primary_extraction_tasks, return_exceptions=True)
        
        # 处理提取结果
        all_primary_conditions = []
        successful_extractors = []
        
        for i, result in enumerate(primary_results):
            if isinstance(result, Exception):
                logging.error(f"Extractor {self.extractors[i].extractor_id} failed: {result}")
            else:
                all_primary_conditions.extend(result)
                successful_extractors.append(self.extractors[i])
        
        # 第二阶段：交叉验证
        cross_validated_conditions = []
        for extractor in successful_extractors:
            other_extractors = [e for e in successful_extractors if e != extractor]
            extractor_conditions = [c for c in all_primary_conditions 
                                  if c.extraction_metadata.get('extraction_method', '').startswith(
                                      extractor.strategy.value)]
            
            if extractor_conditions and other_extractors:
                validated = await extractor.cross_validate(
                    extractor_conditions, other_extractors, context
                )
                cross_validated_conditions.extend(validated)
        
        # 第三阶段：共识形成
        consensus_conditions = await self._form_consensus(
            cross_validated_conditions, context
        )
        
        # 第四阶段：冲突检测
        conflicting_conditions = await self._detect_conflicts(consensus_conditions)
        
        # 构建提取图
        extraction_graph = self._build_extraction_graph(consensus_conditions)
        
        # 计算协作指标
        collaboration_metrics = self._calculate_collaboration_metrics(
            all_primary_conditions, cross_validated_conditions, 
            consensus_conditions, start_time
        )
        
        # 记录协作历史
        self._record_collaboration(context, collaboration_metrics)
        
        return CollaborationResult(
            primary_conditions=all_primary_conditions,
            cross_validated_conditions=cross_validated_conditions,
            consensus_conditions=consensus_conditions,
            conflicting_conditions=conflicting_conditions,
            collaboration_metrics=collaboration_metrics,
            extraction_graph=extraction_graph
        )
    
    async def _form_consensus(self, 
                            conditions: List[Condition],
                            context: ExtractionContext) -> List[Condition]:
        """形成共识条件"""
        if not conditions:
            return []
        
        # 按类型分组
        conditions_by_type = defaultdict(list)
        for condition in conditions:
            conditions_by_type[condition.condition_type].append(condition)
        
        consensus_conditions = []
        
        for condition_type, type_conditions in conditions_by_type.items():
            if len(type_conditions) == 1:
                consensus_conditions.extend(type_conditions)
            else:
                # 多个同类型条件需要形成共识
                consensus = await self._consensus_among_similar_conditions(
                    type_conditions, context
                )
                consensus_conditions.extend(consensus)
        
        # 按置信度排序
        consensus_conditions.sort(key=lambda x: x.confidence, reverse=True)
        
        return consensus_conditions
    
    async def _consensus_among_similar_conditions(self, 
                                                conditions: List[Condition],
                                                context: ExtractionContext) -> List[Condition]:
        """在相似条件间形成共识"""
        # 计算条件间的相似性
        similarity_matrix = self._calculate_condition_similarities(conditions)
        
        # 基于相似性进行聚类
        clusters = self._cluster_similar_conditions(conditions, similarity_matrix)
        
        consensus_conditions = []
        for cluster in clusters:
            if len(cluster) == 1:
                consensus_conditions.append(cluster[0])
            else:
                # 多个条件形成共识
                consensus_condition = self._merge_conditions_to_consensus(cluster)
                consensus_conditions.append(consensus_condition)
        
        return consensus_conditions
    
    def _calculate_condition_similarities(self, conditions: List[Condition]) -> np.ndarray:
        """计算条件间的相似性"""
        n = len(conditions)
        similarity_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i, n):
                if i == j:
                    similarity_matrix[i][j] = 1.0
                else:
                    # 计算多维相似性
                    content_sim = self._content_similarity(conditions[i], conditions[j])
                    type_sim = 1.0 if conditions[i].condition_type == conditions[j].condition_type else 0.5
                    confidence_sim = 1 - abs(conditions[i].confidence - conditions[j].confidence)
                    
                    overall_sim = (content_sim * 0.5 + type_sim * 0.3 + confidence_sim * 0.2)
                    similarity_matrix[i][j] = overall_sim
                    similarity_matrix[j][i] = overall_sim
        
        return similarity_matrix
    
    def _content_similarity(self, condition1: Condition, condition2: Condition) -> float:
        """计算内容相似性"""
        # 词汇重叠相似性
        words1 = set(condition1.content.lower().split())
        words2 = set(condition2.content.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        jaccard_sim = intersection / union if union > 0 else 0.0
        
        # 如果有语义嵌入，使用余弦相似性
        if (condition1.semantic_embedding is not None and 
            condition2.semantic_embedding is not None):
            cosine_sim = cosine_similarity(
                condition1.semantic_embedding.reshape(1, -1),
                condition2.semantic_embedding.reshape(1, -1)
            )[0][0]
            
            # 综合相似性
            return (jaccard_sim + cosine_sim) / 2
        
        return jaccard_sim
    
    def _cluster_similar_conditions(self, 
                                  conditions: List[Condition],
                                  similarity_matrix: np.ndarray,
                                  threshold: float = 0.7) -> List[List[Condition]]:
        """聚类相似条件"""
        n = len(conditions)
        clusters = []
        processed = set()
        
        for i in range(n):
            if i in processed:
                continue
            
            # 找到相似的条件
            similar_indices = [j for j in range(n) 
                             if similarity_matrix[i][j] >= threshold and j not in processed]
            
            cluster = [conditions[idx] for idx in similar_indices]
            clusters.append(cluster)
            processed.update(similar_indices)
        
        return clusters
    
    def _merge_conditions_to_consensus(self, conditions: List[Condition]) -> Condition:
        """将多个条件合并为共识条件"""
        if len(conditions) == 1:
            return conditions[0]
        
        # 选择置信度最高的作为基础
        base_condition = max(conditions, key=lambda x: x.confidence)
        
        # 计算共识置信度
        confidences = [c.confidence for c in conditions]
        consensus_confidence = np.mean(confidences)
        
        # 如果多数条件同意，提升置信度
        if len([c for c in conditions if c.confidence > 0.7]) > len(conditions) / 2:
            consensus_confidence = min(consensus_confidence * 1.1, 1.0)
        
        # 合并证据
        all_evidence = []
        for condition in conditions:
            all_evidence.extend(condition.evidence)
        all_evidence.append(f"consensus_from_{len(conditions)}_conditions")
        
        # 合并依赖
        all_dependencies = set()
        for condition in conditions:
            all_dependencies.update(condition.dependencies)
        
        return Condition(
            condition_id="",
            condition_type=base_condition.condition_type,
            content=base_condition.content,
            confidence=consensus_confidence,
            evidence=all_evidence,
            dependencies=all_dependencies,
            temporal_info=base_condition.temporal_info,
            semantic_embedding=base_condition.semantic_embedding,
            extraction_metadata={
                'extraction_method': 'collaborative_consensus',
                'merged_conditions_count': len(conditions),
                'original_confidences': confidences,
                'consensus_confidence': consensus_confidence
            }
        )
    
    async def _detect_conflicts(self, 
                              conditions: List[Condition]) -> List[Tuple[Condition, Condition, float]]:
        """检测条件冲突"""
        conflicts = []
        n = len(conditions)
        
        for i in range(n):
            for j in range(i + 1, n):
                conflict_score = await self._calculate_conflict_score(
                    conditions[i], conditions[j]
                )
                
                if conflict_score > 0.5:  # 冲突阈值
                    conflicts.append((conditions[i], conditions[j], conflict_score))
        
        # 按冲突严重程度排序
        conflicts.sort(key=lambda x: x[2], reverse=True)
        
        return conflicts
    
    async def _calculate_conflict_score(self, 
                                      condition1: Condition,
                                      condition2: Condition) -> float:
        """计算条件间的冲突分数"""
        conflict_score = 0.0
        
        # 类型冲突检测
        if condition1.condition_type != condition2.condition_type:
            conflict_score += 0.2
        
        # 内容矛盾检测
        content_conflict = self._detect_content_contradiction(
            condition1.content, condition2.content
        )
        conflict_score += content_conflict * 0.4
        
        # 置信度差异
        confidence_diff = abs(condition1.confidence - condition2.confidence)
        if confidence_diff > 0.5:
            conflict_score += confidence_diff * 0.2
        
        # 依赖冲突
        if condition1.dependencies & condition2.dependencies:
            shared_deps = len(condition1.dependencies & condition2.dependencies)
            total_deps = len(condition1.dependencies | condition2.dependencies)
            if shared_deps / total_deps > 0.5:  # 共享依赖但可能冲突
                conflict_score += 0.2
        
        return min(conflict_score, 1.0)
    
    def _detect_content_contradiction(self, content1: str, content2: str) -> float:
        """检测内容矛盾"""
        # 简化的矛盾检测
        contradiction_pairs = [
            (['not', 'no', 'never'], ['yes', 'always', 'must']),
            (['before', 'prior'], ['after', 'following']),
            (['include', 'contain'], ['exclude', 'omit']),
            (['require', 'need'], ['optional', 'unnecessary']),
        ]
        
        content1_lower = content1.lower()
        content2_lower = content2.lower()
        
        contradiction_score = 0.0
        
        for negative_words, positive_words in contradiction_pairs:
            has_negative_1 = any(word in content1_lower for word in negative_words)
            has_positive_1 = any(word in content1_lower for word in positive_words)
            
            has_negative_2 = any(word in content2_lower for word in negative_words)
            has_positive_2 = any(word in content2_lower for word in positive_words)
            
            # 检测矛盾
            if (has_negative_1 and has_positive_2) or (has_positive_1 and has_negative_2):
                contradiction_score += 0.5
        
        return min(contradiction_score, 1.0)
    
    def _build_extraction_graph(self, conditions: List[Condition]) -> nx.DiGraph:
        """构建条件提取图"""
        G = nx.DiGraph()
        
        # 添加条件节点
        for condition in conditions:
            G.add_node(condition.condition_id, 
                      condition_type=condition.condition_type.value,
                      content=condition.content,
                      confidence=condition.confidence)
        
        # 添加依赖边
        for condition in conditions:
            for dep_id in condition.dependencies:
                if dep_id in G.nodes():
                    G.add_edge(dep_id, condition.condition_id, 
                             relation_type='dependency')
        
        # 添加相似性边
        for i, condition1 in enumerate(conditions):
            for j, condition2 in enumerate(conditions[i+1:], i+1):
                similarity = self._content_similarity(condition1, condition2)
                if similarity > 0.6:
                    G.add_edge(condition1.condition_id, condition2.condition_id,
                             relation_type='similarity',
                             weight=similarity)
        
        return G
    
    def _calculate_collaboration_metrics(self, 
                                       primary_conditions: List[Condition],
                                       cross_validated_conditions: List[Condition],
                                       consensus_conditions: List[Condition],
                                       start_time: float) -> Dict[str, float]:
        """计算协作指标"""
        execution_time = time.time() - start_time
        
        metrics = {
            'execution_time': execution_time,
            'primary_extraction_count': len(primary_conditions),
            'cross_validated_count': len(cross_validated_conditions),
            'consensus_count': len(consensus_conditions),
            'extraction_efficiency': len(consensus_conditions) / max(len(primary_conditions), 1),
            'validation_rate': len(cross_validated_conditions) / max(len(primary_conditions), 1),
            'consensus_rate': len(consensus_conditions) / max(len(cross_validated_conditions), 1),
            'avg_confidence': np.mean([c.confidence for c in consensus_conditions]) if consensus_conditions else 0.0,
            'collaboration_overhead': execution_time / max(len(consensus_conditions), 1),
            'extractor_participation': len(self.extractors),
        }
        
        # 质量指标
        if consensus_conditions:
            high_confidence_count = len([c for c in consensus_conditions if c.confidence > 0.8])
            metrics['high_confidence_ratio'] = high_confidence_count / len(consensus_conditions)
            
            type_diversity = len(set(c.condition_type for c in consensus_conditions))
            metrics['type_diversity'] = type_diversity / len(ConditionType)
        
        return metrics
    
    def _record_collaboration(self, 
                            context: ExtractionContext,
                            metrics: Dict[str, float]):
        """记录协作历史"""
        collaboration_record = {
            'timestamp': time.time(),
            'context_signature': context.get_context_signature(),
            'metrics': metrics,
            'extractor_count': len(self.extractors)
        }
        
        self.collaboration_history.append(collaboration_record)
        
        # 保持历史记录在合理范围内
        if len(self.collaboration_history) > 1000:
            self.collaboration_history = self.collaboration_history[-1000:]
        
        # 更新性能指标
        for metric_name, value in metrics.items():
            self.performance_metrics[metric_name].append(value)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.performance_metrics:
            return {'message': 'No performance data available'}
        
        summary = {}
        for metric_name, values in self.performance_metrics.items():
            if values:
                summary[metric_name] = {
                    'mean': np.mean(values),
                    'std': np.std(values),
                    'min': np.min(values),
                    'max': np.max(values),
                    'count': len(values)
                }
        
        summary['total_collaborations'] = len(self.collaboration_history)
        summary['active_extractors'] = len(self.extractors)
        
        return summary


# 使用示例
async def main():
    """演示协作式条件提取"""
    # 创建协作式条件提取器
    collaborative_extractor = CollaborativeConditionExtractor()
    
    # 创建提取上下文
    context = ExtractionContext(
        query="When implementing the new user authentication system, ensure that all user data is encrypted and the system can handle at least 1000 concurrent users.",
        conversation_history=[
            "We need to upgrade our authentication system",
            "Security is a top priority for this project",
            "The system should be scalable"
        ],
        user_profile={
            'role': 'system_architect',
            'experience': 'senior',
            'domain': 'security'
        },
        domain_knowledge={
            'security_requirements': ['encryption', 'authentication', 'authorization'],
            'performance_requirements': ['scalability', 'concurrent_users', 'response_time']
        }
    )
    
    # 执行协作式条件提取
    result = await collaborative_extractor.extract_conditions_collaboratively(context)
    
    # 输出结果
    print("=== 协作式条件提取结果 ===")
    print(f"主要条件数量: {len(result.primary_conditions)}")
    print(f"交叉验证条件数量: {len(result.cross_validated_conditions)}")
    print(f"共识条件数量: {len(result.consensus_conditions)}")
    print(f"冲突条件数量: {len(result.conflicting_conditions)}")
    
    print("\n=== 共识条件 ===")
    for i, condition in enumerate(result.consensus_conditions, 1):
        print(f"{i}. [{condition.condition_type.value}] {condition.content}")
        print(f"   置信度: {condition.confidence:.3f}")
        print(f"   证据: {', '.join(condition.evidence[:3])}...")
        print()
    
    print("=== 协作指标 ===")
    for metric, value in result.collaboration_metrics.items():
        print(f"{metric}: {value:.3f}")
    
    # 获取性能摘要
    performance_summary = collaborative_extractor.get_performance_summary()
    print("\n=== 性能摘要 ===")
    print(json.dumps(performance_summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())