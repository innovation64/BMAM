"""
Lightweight Knowledge Graph System
轻量级知识图谱系统 - 基于NetworkX
"""

import json
import networkx as nx
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import pickle

from ..utils.config import get_logger, get_absolute_path

logger = get_logger(__name__)


class EntityType:
    """实体类型枚举"""
    PERSON = "person"
    CONCEPT = "concept"
    EVENT = "event"
    OBJECT = "object"
    LOCATION = "location"
    TIME = "time"
    MEMORY = "memory"


class RelationType:
    """关系类型枚举"""
    RELATED_TO = "related_to"          # 通用关联
    CAUSES = "causes"                  # 因果关系
    PART_OF = "part_of"               # 部分-整体
    HAPPENED_AT = "happened_at"        # 发生时间
    LOCATED_AT = "located_at"         # 位置关系
    INVOLVES = "involves"              # 涉及
    SIMILAR_TO = "similar_to"         # 相似
    DERIVED_FROM = "derived_from"     # 派生自
    CO_OCCURS = "co_occurs"           # 共现


class KnowledgeGraphNode:
    """知识图谱节点"""
    def __init__(self, node_id: str, entity_type: str,
                 content: str, properties: Dict[str, Any] = None):
        self.node_id = node_id
        self.entity_type = entity_type
        self.content = content
        self.properties = properties or {}
        self.created_at = datetime.now()
        self.access_count = 0
        self.importance = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            'node_id': self.node_id,
            'entity_type': self.entity_type,
            'content': self.content,
            'properties': self.properties,
            'created_at': self.created_at.isoformat(),
            'access_count': self.access_count,
            'importance': self.importance
        }


class KnowledgeGraphEdge:
    """知识图谱边"""
    def __init__(self, source_id: str, target_id: str,
                 relation_type: str, strength: float = 0.5,
                 properties: Dict[str, Any] = None):
        self.source_id = source_id
        self.target_id = target_id
        self.relation_type = relation_type
        self.strength = strength  # 0-1
        self.properties = properties or {}
        self.created_at = datetime.now()
        self.access_count = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'source_id': self.source_id,
            'target_id': self.target_id,
            'relation_type': self.relation_type,
            'strength': self.strength,
            'properties': self.properties,
            'created_at': self.created_at.isoformat(),
            'access_count': self.access_count
        }


class LightweightKnowledgeGraph:
    """
    轻量级知识图谱系统

    基于NetworkX的内存图存储，支持：
    1. 实体-关系-实体三元组
    2. 图遍历和路径查询
    3. 社区检测和聚类
    4. PageRank中心性分析
    5. 持久化存储
    """

    def __init__(self, save_dir: str = "data/knowledge_graph"):
        """初始化知识图谱"""
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

        # 主图结构 (有向多重图)
        self.graph = nx.MultiDiGraph()

        # 节点和边的详细信息
        self.nodes: Dict[str, KnowledgeGraphNode] = {}
        self.edges: Dict[str, KnowledgeGraphEdge] = {}

        # 索引
        self.entity_type_index: Dict[str, Set[str]] = defaultdict(set)
        self.relation_type_index: Dict[str, Set[Tuple[str, str]]] = defaultdict(set)

        # 统计信息
        self.stats = {
            'total_nodes': 0,
            'total_edges': 0,
            'entity_types': defaultdict(int),
            'relation_types': defaultdict(int)
        }

        # 加载已有数据
        self._load_graph()

        logger.info(f"知识图谱初始化完成: {self.stats['total_nodes']}节点, "
                   f"{self.stats['total_edges']}边")

    # ==================== 基本操作 ====================

    def add_node(self, node_id: str, entity_type: str,
                 content: str, properties: Dict[str, Any] = None) -> bool:
        """添加节点"""
        if node_id in self.nodes:
            logger.debug(f"节点已存在: {node_id}")
            return False

        # 创建节点对象
        node = KnowledgeGraphNode(node_id, entity_type, content, properties)
        self.nodes[node_id] = node

        # 添加到NetworkX图
        self.graph.add_node(node_id, **node.to_dict())

        # 更新索引
        self.entity_type_index[entity_type].add(node_id)

        # 更新统计
        self.stats['total_nodes'] += 1
        self.stats['entity_types'][entity_type] += 1

        logger.debug(f"添加节点: {node_id} ({entity_type})")
        return True

    def add_edge(self, source_id: str, target_id: str,
                 relation_type: str, strength: float = 0.5,
                 properties: Dict[str, Any] = None) -> bool:
        """添加边(关系)"""
        # 检查节点是否存在
        if source_id not in self.nodes or target_id not in self.nodes:
            logger.warning(f"节点不存在: {source_id} -> {target_id}")
            return False

        # 创建边对象
        edge_key = f"{source_id}-{relation_type}-{target_id}"
        edge = KnowledgeGraphEdge(source_id, target_id, relation_type,
                                  strength, properties)
        self.edges[edge_key] = edge

        # 添加到NetworkX图
        self.graph.add_edge(source_id, target_id,
                           key=relation_type,
                           **edge.to_dict())

        # 更新索引
        self.relation_type_index[relation_type].add((source_id, target_id))

        # 更新统计
        self.stats['total_edges'] += 1
        self.stats['relation_types'][relation_type] += 1

        logger.debug(f"添加边: {source_id} -[{relation_type}]-> {target_id}")
        return True

    def add_triple(self, source: str, relation: str, target: str,
                   source_type: str = 'Entity', target_type: str = 'Entity',
                   strength: float = 0.5) -> bool:
        """
        添加三元组 (source, relation, target)

        兼容层方法，用于适配 SimpleKnowledgeGraph 的 API
        自动创建节点（如果不存在）并添加边

        Args:
            source: 源实体
            relation: 关系类型
            target: 目标实体
            source_type: 源实体类型
            target_type: 目标实体类型
            strength: 关系强度

        Returns:
            是否成功添加
        """
        # 自动创建源节点（如果不存在）
        if source not in self.nodes:
            self.add_node(source, source_type, source, {})

        # 自动创建目标节点（如果不存在）
        if target not in self.nodes:
            self.add_node(target, target_type, target, {})

        # 添加边
        return self.add_edge(source, target, relation, strength)

    def remove_node(self, node_id: str) -> bool:
        """删除节点"""
        if node_id not in self.nodes:
            return False

        node = self.nodes[node_id]

        # 从图中删除
        self.graph.remove_node(node_id)

        # 更新索引
        self.entity_type_index[node.entity_type].discard(node_id)

        # 删除节点对象
        del self.nodes[node_id]

        # 更新统计
        self.stats['total_nodes'] -= 1
        self.stats['entity_types'][node.entity_type] -= 1

        logger.debug(f"删除节点: {node_id}")
        return True

    def update_node(self, node_id: str, properties: Dict[str, Any]) -> bool:
        """更新节点属性"""
        if node_id not in self.nodes:
            return False

        node = self.nodes[node_id]
        node.properties.update(properties)

        # 更新图中的属性
        self.graph.nodes[node_id].update(properties)

        return True

    def update_edge_strength(self, source_id: str, target_id: str,
                            relation_type: str, strength: float) -> bool:
        """更新边的强度"""
        edge_key = f"{source_id}-{relation_type}-{target_id}"

        if edge_key not in self.edges:
            return False

        self.edges[edge_key].strength = strength

        # 更新图中的属性
        if self.graph.has_edge(source_id, target_id, key=relation_type):
            self.graph[source_id][target_id][relation_type]['strength'] = strength

        return True

    # ==================== 查询操作 ====================

    def get_node(self, node_id: str) -> Optional[KnowledgeGraphNode]:
        """获取节点"""
        return self.nodes.get(node_id)

    def get_neighbors(self, node_id: str,
                     relation_type: Optional[str] = None) -> List[str]:
        """获取邻居节点"""
        if node_id not in self.graph:
            return []

        if relation_type:
            # 指定关系类型的邻居
            neighbors = []
            for neighbor in self.graph.successors(node_id):
                edges = self.graph[node_id][neighbor]
                if relation_type in edges:
                    neighbors.append(neighbor)
            return neighbors
        else:
            # 所有邻居
            return list(self.graph.successors(node_id))

    def get_edges_from(self, node_id: str,
                       relation_type: Optional[str] = None) -> List[Tuple[str, str, str]]:
        """获取从某节点出发的所有边"""
        if node_id not in self.graph:
            return []

        edges = []
        for target in self.graph.successors(node_id):
            for rel_type in self.graph[node_id][target]:
                if relation_type is None or rel_type == relation_type:
                    edges.append((node_id, target, rel_type))

        return edges

    def find_paths(self, source_id: str, target_id: str,
                   max_depth: int = 3) -> List[List[str]]:
        """查找两个节点之间的路径"""
        if source_id not in self.graph or target_id not in self.graph:
            return []

        try:
            # 使用NetworkX的所有简单路径算法
            paths = list(nx.all_simple_paths(
                self.graph, source_id, target_id, cutoff=max_depth
            ))
            return paths
        except nx.NetworkXNoPath:
            return []

    def find_shortest_path(self, source_id: str, target_id: str) -> Optional[List[str]]:
        """查找最短路径"""
        if source_id not in self.graph or target_id not in self.graph:
            return None

        try:
            return nx.shortest_path(self.graph, source_id, target_id)
        except nx.NetworkXNoPath:
            return None

    def get_subgraph(self, node_ids: List[str]) -> nx.MultiDiGraph:
        """获取子图"""
        return self.graph.subgraph(node_ids).copy()

    def get_nodes_by_type(self, entity_type: str) -> List[KnowledgeGraphNode]:
        """根据实体类型获取节点"""
        node_ids = self.entity_type_index.get(entity_type, set())
        return [self.nodes[nid] for nid in node_ids]

    def search_nodes(self, keyword: str, entity_type: Optional[str] = None) -> List[KnowledgeGraphNode]:
        """搜索节点(关键词匹配)"""
        results = []

        for node in self.nodes.values():
            # 类型过滤
            if entity_type and node.entity_type != entity_type:
                continue

            # 关键词匹配
            if keyword.lower() in node.content.lower():
                results.append(node)

        return results

    # ==================== 图算法 ====================

    def compute_pagerank(self, alpha: float = 0.85) -> Dict[str, float]:
        """计算PageRank中心性"""
        try:
            return nx.pagerank(self.graph, alpha=alpha)
        except Exception as e:
            logger.error(f"PageRank计算失败: {e}")
            return {}

    def compute_centrality(self) -> Dict[str, Dict[str, float]]:
        """计算多种中心性指标"""
        centrality = {}

        try:
            centrality['degree'] = dict(self.graph.degree())
            centrality['in_degree'] = dict(self.graph.in_degree())
            centrality['out_degree'] = dict(self.graph.out_degree())

            if len(self.graph) > 0:
                centrality['pagerank'] = self.compute_pagerank()

                # 只对连通图计算
                if nx.is_weakly_connected(self.graph):
                    centrality['betweenness'] = nx.betweenness_centrality(self.graph)
                    centrality['closeness'] = nx.closeness_centrality(self.graph)

        except Exception as e:
            logger.error(f"中心性计算失败: {e}")

        return centrality

    def detect_communities(self) -> List[Set[str]]:
        """社区检测(使用Louvain算法的变体)"""
        try:
            # 转换为无向图
            undirected = self.graph.to_undirected()

            # 使用贪心模块度最大化算法
            communities = nx.community.greedy_modularity_communities(undirected)

            return [set(community) for community in communities]

        except Exception as e:
            logger.error(f"社区检测失败: {e}")
            return []

    def find_strongly_connected_components(self) -> List[Set[str]]:
        """查找强连通分量"""
        return [set(component) for component in
                nx.strongly_connected_components(self.graph)]

    def get_node_importance(self, node_id: str) -> float:
        """计算节点重要性(综合多个指标)"""
        if node_id not in self.nodes:
            return 0.0

        # 度中心性
        degree = self.graph.degree(node_id)

        # PageRank
        pagerank_scores = self.compute_pagerank()
        pagerank = pagerank_scores.get(node_id, 0.0)

        # 访问频率
        access_count = self.nodes[node_id].access_count

        # 综合得分
        importance = (
            0.3 * (degree / max(dict(self.graph.degree()).values() or {node_id: 1}.values())) +
            0.5 * pagerank +
            0.2 * min(1.0, access_count / 100)
        )

        return importance

    # ==================== 高级功能 ====================

    def expand_context(self, node_id: str, depth: int = 2) -> Set[str]:
        """扩展上下文(获取k-hop邻居)"""
        if node_id not in self.graph:
            return set()

        context_nodes = {node_id}
        current_layer = {node_id}

        for _ in range(depth):
            next_layer = set()
            for node in current_layer:
                neighbors = set(self.graph.successors(node))
                next_layer.update(neighbors)

            context_nodes.update(next_layer)
            current_layer = next_layer

        return context_nodes

    def find_similar_nodes(self, node_id: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """查找相似节点(基于共同邻居)"""
        if node_id not in self.graph:
            return []

        node_neighbors = set(self.graph.successors(node_id))

        similarity_scores = []

        for other_id in self.nodes:
            if other_id == node_id:
                continue

            other_neighbors = set(self.graph.successors(other_id))

            # Jaccard相似度
            intersection = node_neighbors & other_neighbors
            union = node_neighbors | other_neighbors

            if union:
                similarity = len(intersection) / len(union)
                if similarity > 0:
                    similarity_scores.append((other_id, similarity))

        # 按相似度排序
        similarity_scores.sort(key=lambda x: x[1], reverse=True)

        return similarity_scores[:top_k]

    def merge_nodes(self, node_id1: str, node_id2: str,
                    merged_id: Optional[str] = None) -> Optional[str]:
        """合并两个节点"""
        if node_id1 not in self.nodes or node_id2 not in self.nodes:
            return None

        # 使用第一个节点或自定义ID
        merged_id = merged_id or node_id1

        node1 = self.nodes[node_id1]
        node2 = self.nodes[node_id2]

        # 合并内容
        merged_content = f"{node1.content}; {node2.content}"

        # 合并属性
        merged_properties = {**node1.properties, **node2.properties}

        # 创建新节点或更新节点
        if merged_id not in self.nodes:
            self.add_node(merged_id, node1.entity_type,
                         merged_content, merged_properties)

        # 转移所有边
        for source, target, rel_type in self.graph.edges(node_id1, keys=True):
            if target != node_id2:
                self.add_edge(merged_id, target, rel_type)

        for source, target, rel_type in self.graph.edges(node_id2, keys=True):
            if target != node_id1:
                self.add_edge(merged_id, target, rel_type)

        # 删除原节点
        if merged_id != node_id1:
            self.remove_node(node_id1)
        if merged_id != node_id2:
            self.remove_node(node_id2)

        return merged_id

    # ==================== 持久化 ====================

    def _load_graph(self):
        """加载图数据"""
        graph_file = self.save_dir / "graph.pkl"
        nodes_file = self.save_dir / "nodes.json"
        edges_file = self.save_dir / "edges.json"

        try:
            # 加载NetworkX图
            if graph_file.exists():
                with open(graph_file, 'rb') as f:
                    self.graph = pickle.load(f)

            # 加载节点
            if nodes_file.exists():
                with open(nodes_file, 'r', encoding='utf-8') as f:
                    nodes_data = json.load(f)
                    for node_data in nodes_data:
                        node = KnowledgeGraphNode(
                            node_data['node_id'],
                            node_data['entity_type'],
                            node_data['content'],
                            node_data.get('properties', {})
                        )
                        node.created_at = datetime.fromisoformat(node_data['created_at'])
                        node.access_count = node_data.get('access_count', 0)
                        node.importance = node_data.get('importance', 0.5)

                        self.nodes[node.node_id] = node
                        self.entity_type_index[node.entity_type].add(node.node_id)

            # 加载边
            if edges_file.exists():
                with open(edges_file, 'r', encoding='utf-8') as f:
                    edges_data = json.load(f)
                    for edge_data in edges_data:
                        edge = KnowledgeGraphEdge(
                            edge_data['source_id'],
                            edge_data['target_id'],
                            edge_data['relation_type'],
                            edge_data.get('strength', 0.5),
                            edge_data.get('properties', {})
                        )
                        edge.created_at = datetime.fromisoformat(edge_data['created_at'])
                        edge.access_count = edge_data.get('access_count', 0)

                        edge_key = f"{edge.source_id}-{edge.relation_type}-{edge.target_id}"
                        self.edges[edge_key] = edge
                        self.relation_type_index[edge.relation_type].add(
                            (edge.source_id, edge.target_id)
                        )

            # 更新统计
            self._update_stats()

            logger.info(f"加载知识图谱: {self.stats['total_nodes']}节点, "
                       f"{self.stats['total_edges']}边")

        except Exception as e:
            logger.warning(f"加载图数据失败: {e}")

    def save_graph(self):
        """保存图数据"""
        try:
            # 保存NetworkX图
            graph_file = self.save_dir / "graph.pkl"
            with open(graph_file, 'wb') as f:
                pickle.dump(self.graph, f)

            # 保存节点
            nodes_file = self.save_dir / "nodes.json"
            with open(nodes_file, 'w', encoding='utf-8') as f:
                nodes_data = [node.to_dict() for node in self.nodes.values()]
                json.dump(nodes_data, f, ensure_ascii=False, indent=2)

            # 保存边
            edges_file = self.save_dir / "edges.json"
            with open(edges_file, 'w', encoding='utf-8') as f:
                edges_data = [edge.to_dict() for edge in self.edges.values()]
                json.dump(edges_data, f, ensure_ascii=False, indent=2)

            logger.info(f"保存知识图谱: {self.stats['total_nodes']}节点, "
                       f"{self.stats['total_edges']}边")

        except Exception as e:
            logger.error(f"保存图数据失败: {e}")

    def _update_stats(self):
        """更新统计信息"""
        self.stats['total_nodes'] = len(self.nodes)
        self.stats['total_edges'] = len(self.edges)

        self.stats['entity_types'] = defaultdict(int)
        for node in self.nodes.values():
            self.stats['entity_types'][node.entity_type] += 1

        self.stats['relation_types'] = defaultdict(int)
        for edge in self.edges.values():
            self.stats['relation_types'][edge.relation_type] += 1

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        centrality = self.compute_centrality()

        return {
            'basic': dict(self.stats),
            'centrality': {
                'top_pagerank': sorted(
                    centrality.get('pagerank', {}).items(),
                    key=lambda x: x[1], reverse=True
                )[:10],
                'top_degree': sorted(
                    centrality.get('degree', {}).items(),
                    key=lambda x: x[1], reverse=True
                )[:10]
            },
            'graph_properties': {
                'is_connected': nx.is_weakly_connected(self.graph) if len(self.graph) > 0 else False,
                'num_components': nx.number_weakly_connected_components(self.graph) if len(self.graph) > 0 else 0,
                'density': nx.density(self.graph) if len(self.graph) > 0 else 0.0,
                'avg_degree': sum(dict(self.graph.degree()).values()) / max(len(self.graph), 1) if len(self.graph) > 0 else 0.0
            }
        }

    def export_to_json(self, output_path: str):
        """导出为JSON格式"""
        data = {
            'nodes': [node.to_dict() for node in self.nodes.values()],
            'edges': [edge.to_dict() for edge in self.edges.values()],
            'statistics': self.get_statistics()
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"导出知识图谱到: {output_path}")


# 全局KG实例
knowledge_graph = LightweightKnowledgeGraph()