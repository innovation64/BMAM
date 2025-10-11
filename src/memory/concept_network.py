"""
Concept Network - 概念网络
模拟人脑的语义记忆网络,存储概念间的关联关系

核心功能:
1. 概念关联存储 - 类似WordNet/ConceptNet
2. 激活扩散 - 从源概念扩散到相关概念
3. 动态学习 - 从对话中学习新概念和关联

神经科学基础:
- Semantic Memory Network (Tulving, 1972)
- Spreading Activation (Collins & Loftus, 1975)
- Concept Cells in MTL (Quiroga et al., 2005)

Author: Claude
Date: 2025-01-09
"""

import networkx as nx
import logging
from typing import Dict, List, Tuple, Set, Optional
from collections import defaultdict
import json
from pathlib import Path

from ..utils.config import get_logger

logger = get_logger(__name__)


class ConceptNetwork:
    """
    概念网络: 语义记忆的图结构表示

    节点 = 概念 (e.g., "transgender", "lgbtq", "support_group")
    边 = 关联强度 (0.0-1.0)

    用途:
    - 激活扩散: 从"LGBTQ"扩散到"transgender", "gender_identity"等
    - 模式识别: 识别"support_group + transgender stories → likely transgender"
    - 推理增强: 补充显式推理无法处理的联想推理
    """

    def __init__(self, concept_file: Optional[str] = None):
        """
        初始化概念网络

        Args:
            concept_file: 预加载的概念文件路径(JSON格式)
        """
        self.graph = nx.Graph()  # 使用无向图(双向关联)
        self.concept_embeddings = {}  # 概念的向量表示(可选)

        # 加载基础概念
        if concept_file and Path(concept_file).exists():
            self._load_from_file(concept_file)
        else:
            self._initialize_base_concepts()

        logger.info(f"📚 ConceptNetwork initialized: {self.graph.number_of_nodes()} concepts, {self.graph.number_of_edges()} edges")


    def _initialize_base_concepts(self):
        """
        初始化基础概念网络

        包含常见的身份、情感、社会概念
        这些可以从外部知识库加载,这里先hardcode关键概念
        """
        # Identity & Gender概念簇
        identity_concepts = [
            ("lgbtq", "transgender", 0.85),
            ("lgbtq", "gay", 0.75),
            ("lgbtq", "lesbian", 0.75),
            ("lgbtq", "bisexual", 0.75),
            ("lgbtq", "queer", 0.80),
            ("lgbtq", "non_binary", 0.80),

            ("transgender", "gender_identity", 0.95),
            ("transgender", "transition", 0.85),
            ("transgender", "coming_out", 0.75),
            ("transgender", "gender_dysphoria", 0.80),

            ("gender_identity", "self_identity", 0.90),
            ("gender_identity", "identity_exploration", 0.85),
        ]

        # Social & Community概念簇
        social_concepts = [
            ("support_group", "community", 0.85),
            ("support_group", "peer_support", 0.90),
            ("support_group", "identity_exploration", 0.75),
            ("support_group", "belonging", 0.80),

            ("community", "belonging", 0.85),
            ("community", "acceptance", 0.80),
            ("community", "social_support", 0.85),
        ]

        # Emotional & Psychological概念簇
        emotion_concepts = [
            ("inspiring", "motivation", 0.85),
            ("inspiring", "resonance", 0.80),
            ("inspiring", "identification", 0.75),

            ("resonance", "identification", 0.90),
            ("resonance", "empathy", 0.85),
            ("resonance", "connection", 0.80),

            ("identification", "self_recognition", 0.95),
            ("identification", "belonging", 0.80),
        ]

        # Research & Education概念簇
        research_concepts = [
            ("research", "information_seeking", 0.85),
            ("research", "learning", 0.80),
            ("research", "exploration", 0.75),

            ("adoption", "parenting", 0.90),
            ("adoption", "family", 0.85),
            ("adoption", "caregiving", 0.80),

            ("psychology", "mental_health", 0.85),
            ("psychology", "counseling", 0.90),
            ("psychology", "therapy", 0.85),

            ("social_work", "helping_profession", 0.90),
            ("social_work", "community_service", 0.85),
            ("social_work", "advocacy", 0.80),
        ]

        # 添加所有概念和边
        all_concepts = (
            identity_concepts +
            social_concepts +
            emotion_concepts +
            research_concepts
        )

        for source, target, weight in all_concepts:
            self.add_concept_relation(source, target, weight)

        # 添加跨簇连接(更符合真实语义网络)
        cross_cluster = [
            ("lgbtq", "support_group", 0.85),
            ("transgender", "support_group", 0.80),
            ("identity_exploration", "self_recognition", 0.85),
            ("coming_out", "support_group", 0.75),
            ("social_work", "lgbtq", 0.60),
            ("psychology", "identity_exploration", 0.70),
            ("counseling", "support_group", 0.75),
        ]

        for source, target, weight in cross_cluster:
            self.add_concept_relation(source, target, weight)


    def add_concept_relation(self, concept1: str, concept2: str, weight: float = 0.5):
        """
        添加概念关联

        Args:
            concept1, concept2: 两个概念
            weight: 关联强度 (0.0-1.0)
        """
        # 规范化概念名称(小写,下划线)
        c1 = self._normalize_concept(concept1)
        c2 = self._normalize_concept(concept2)

        # 添加节点(如果不存在)
        if c1 not in self.graph:
            self.graph.add_node(c1)
        if c2 not in self.graph:
            self.graph.add_node(c2)

        # 添加或更新边
        if self.graph.has_edge(c1, c2):
            # 如果已存在,取较大权重
            old_weight = self.graph[c1][c2]['weight']
            self.graph[c1][c2]['weight'] = max(old_weight, weight)
        else:
            self.graph.add_edge(c1, c2, weight=weight)


    def spreading_activation(
        self,
        seed_concepts: List[str],
        decay_factor: float = 0.8,
        max_distance: int = 3,
        top_k: int = 20
    ) -> Dict[str, float]:
        """
        激活扩散: 从种子概念扩散激活

        模拟: 神经元激活通过突触传播
        - 激活从种子概念开始
        - 通过边传播到相邻概念
        - 激活强度随距离衰减

        Args:
            seed_concepts: 初始激活的概念列表
            decay_factor: 激活衰减因子 (每跳衰减)
            max_distance: 最大扩散距离
            top_k: 返回激活最高的k个概念

        Returns:
            {concept: activation_score}

        Example:
            seeds = ["lgbtq", "support_group"]
            activated = spreading_activation(seeds)
            # -> {"transgender": 0.85, "gender_identity": 0.72, ...}
        """
        # 规范化种子概念
        seeds = [self._normalize_concept(c) for c in seed_concepts]

        # 初始化激活
        activation = defaultdict(float)
        for seed in seeds:
            if seed in self.graph:
                activation[seed] = 1.0

        # BFS扩散激活
        visited = set()
        queue = [(seed, 0) for seed in seeds if seed in self.graph]

        while queue:
            current, distance = queue.pop(0)

            if current in visited or distance >= max_distance:
                continue

            visited.add(current)

            # 获取邻居
            neighbors = self.graph.neighbors(current)

            for neighbor in neighbors:
                if neighbor not in visited:
                    # 计算传播的激活
                    edge_weight = self.graph[current][neighbor]['weight']
                    propagated_activation = activation[current] * edge_weight * (decay_factor ** distance)

                    # 累加激活(多条路径可以累加)
                    activation[neighbor] += propagated_activation

                    # 添加到队列
                    queue.append((neighbor, distance + 1))

        # 归一化激活(可选)
        total_activation = sum(activation.values())
        if total_activation > 0:
            activation = {k: v / total_activation for k, v in activation.items()}

        # 返回Top-K
        sorted_concepts = sorted(
            activation.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return dict(sorted_concepts[:top_k])


    def get_related_concepts(
        self,
        concept: str,
        max_distance: int = 2,
        min_weight: float = 0.5
    ) -> List[Tuple[str, float, int]]:
        """
        获取相关概念

        Args:
            concept: 查询概念
            max_distance: 最大距离
            min_weight: 最小边权重

        Returns:
            [(concept, cumulative_weight, distance), ...]
        """
        concept = self._normalize_concept(concept)

        if concept not in self.graph:
            return []

        # BFS搜索
        related = []
        visited = set()
        queue = [(concept, 1.0, 0)]  # (concept, weight, distance)

        while queue:
            current, cum_weight, distance = queue.pop(0)

            if current in visited or distance > max_distance:
                continue

            visited.add(current)

            # 记录(排除自己)
            if current != concept:
                related.append((current, cum_weight, distance))

            # 扩展邻居
            if distance < max_distance:
                for neighbor in self.graph.neighbors(current):
                    edge_weight = self.graph[current][neighbor]['weight']
                    if edge_weight >= min_weight:
                        new_weight = cum_weight * edge_weight
                        queue.append((neighbor, new_weight, distance + 1))

        # 按权重排序
        related.sort(key=lambda x: x[1], reverse=True)
        return related


    def find_path_concepts(self, concept1: str, concept2: str) -> Optional[List[str]]:
        """
        找到两个概念间的最短路径

        用途: 解释为什么两个概念相关
        Example: "lgbtq" → "gender_identity"
        Path: ["lgbtq", "transgender", "gender_identity"]
        """
        c1 = self._normalize_concept(concept1)
        c2 = self._normalize_concept(concept2)

        if c1 not in self.graph or c2 not in self.graph:
            return None

        try:
            path = nx.shortest_path(self.graph, c1, c2)
            return path
        except nx.NetworkXNoPath:
            return None


    def compute_concept_similarity(self, concept1: str, concept2: str) -> float:
        """
        计算两个概念的语义相似度

        基于:
        1. 是否直接连接(边权重)
        2. 最短路径距离
        3. 共同邻居数量
        """
        c1 = self._normalize_concept(concept1)
        c2 = self._normalize_concept(concept2)

        if c1 not in self.graph or c2 not in self.graph:
            return 0.0

        # 1. 直接连接
        if self.graph.has_edge(c1, c2):
            return self.graph[c1][c2]['weight']

        # 2. 基于路径距离
        try:
            path_length = nx.shortest_path_length(self.graph, c1, c2)
            path_similarity = 1.0 / (1.0 + path_length)
        except nx.NetworkXNoPath:
            path_similarity = 0.0

        # 3. 共同邻居(Jaccard系数)
        neighbors1 = set(self.graph.neighbors(c1))
        neighbors2 = set(self.graph.neighbors(c2))
        if len(neighbors1) + len(neighbors2) > 0:
            jaccard = len(neighbors1 & neighbors2) / len(neighbors1 | neighbors2)
        else:
            jaccard = 0.0

        # 组合
        similarity = 0.5 * path_similarity + 0.5 * jaccard
        return similarity


    def learn_from_context(self, context_text: str, concepts: List[str]):
        """
        从上下文中学习新的概念关联

        当用户提到多个概念在同一上下文,增强它们之间的关联
        Example: "transgender stories inspiring" → 增强 transgender ↔ inspiring
        """
        # 规范化概念
        concepts = [self._normalize_concept(c) for c in concepts]

        # 为所有概念对增加关联
        for i, c1 in enumerate(concepts):
            for c2 in concepts[i+1:]:
                # 如果已存在,增强关联
                if self.graph.has_edge(c1, c2):
                    current_weight = self.graph[c1][c2]['weight']
                    new_weight = min(1.0, current_weight + 0.05)  # 小幅增强
                    self.graph[c1][c2]['weight'] = new_weight
                else:
                    # 新关联
                    self.add_concept_relation(c1, c2, 0.3)

        logger.debug(f"Learned {len(concepts)} concept co-occurrences from context")


    def _normalize_concept(self, concept: str) -> str:
        """规范化概念名称"""
        return concept.lower().strip().replace(' ', '_').replace('-', '_')


    def _load_from_file(self, filepath: str):
        """从JSON文件加载概念网络"""
        with open(filepath, 'r') as f:
            data = json.load(f)

        for edge in data.get('edges', []):
            self.add_concept_relation(
                edge['source'],
                edge['target'],
                edge.get('weight', 0.5)
            )

        logger.info(f"Loaded concept network from {filepath}")


    def save_to_file(self, filepath: str):
        """保存概念网络到JSON文件"""
        edges = []
        for source, target, data in self.graph.edges(data=True):
            edges.append({
                'source': source,
                'target': target,
                'weight': data.get('weight', 0.5)
            })

        output = {
            'nodes': list(self.graph.nodes()),
            'edges': edges,
            'metadata': {
                'num_concepts': self.graph.number_of_nodes(),
                'num_relations': self.graph.number_of_edges()
            }
        }

        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)

        logger.info(f"Saved concept network to {filepath}")


    def get_statistics(self) -> Dict[str, Any]:
        """获取网络统计信息"""
        return {
            'num_concepts': self.graph.number_of_nodes(),
            'num_relations': self.graph.number_of_edges(),
            'avg_degree': sum(dict(self.graph.degree()).values()) / self.graph.number_of_nodes() if self.graph.number_of_nodes() > 0 else 0,
            'density': nx.density(self.graph),
            'is_connected': nx.is_connected(self.graph)
        }
