"""
Simple Knowledge Graph for Temporal Lobe Agent
简单知识图谱实现
"""

from collections import defaultdict
from typing import Dict, List, Any, Tuple


class SimpleKnowledgeGraph:
    """
    简单知识图谱

    存储: {entity: {relation: [target_entities]}}
    例如: {'李阳': {'likes': ['绿茶', '咖啡'], 'lives_in': ['北京']}}
    """

    def __init__(self):
        self.graph: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        self.reverse_index: Dict[str, List[Tuple[str, str]]] = defaultdict(list)  # {target: [(source, relation)]}

    def add_triple(self, source: str, relation: str, target: str):
        """添加三元组"""
        if target not in self.graph[source][relation]:
            self.graph[source][relation].append(target)
            self.reverse_index[target].append((source, relation))

    def query_relations(self, entity: str, relation: str = None) -> List[Tuple[str, str, str]]:
        """
        查询实体的关系

        Args:
            entity: 实体名称
            relation: 关系类型 (None = 所有关系)

        Returns:
            List of (source, relation, target) triples
        """
        results = []

        if entity in self.graph:
            if relation:
                # 指定关系
                targets = self.graph[entity].get(relation, [])
                results.extend([(entity, relation, t) for t in targets])
            else:
                # 所有关系
                for rel, targets in self.graph[entity].items():
                    results.extend([(entity, rel, t) for t in targets])

        return results

    def multi_hop_query(self, start_entity: str, max_depth: int = 2) -> List[List[Tuple[str, str, str]]]:
        """
        多跳推理

        Args:
            start_entity: 起始实体
            max_depth: 最大跳数

        Returns:
            List of paths (each path is a list of triples)
        """
        paths = []

        def dfs(entity, path, depth):
            if depth >= max_depth:
                if path:
                    paths.append(path[:])
                return

            # 获取当前实体的所有关系
            for relation, targets in self.graph.get(entity, {}).items():
                for target in targets:
                    path.append((entity, relation, target))
                    dfs(target, path, depth + 1)
                    path.pop()

        dfs(start_entity, [], 0)
        return paths

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_entities = len(self.graph)
        total_triples = sum(len(targets) for relations in self.graph.values() for targets in relations.values())

        return {
            'total_entities': total_entities,
            'total_triples': total_triples
        }
