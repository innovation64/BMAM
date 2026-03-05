"""
Temporal Lobe Concept Graph - 颞叶概念图 (知识图谱)

功能: 存储语义知识和实体关系
结构: 知识图谱 (Knowledge Graph)
节点: Entity/Concept
边: Relation (带类型)

灵感来源:
- 颞叶负责语义记忆 (semantic memory)
- 存储"what is what" and "what relates to what"
- 实体-关系-实体 三元组
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """实体节点"""
    name: str
    entity_type: str  # Person, Location, Concept, Event
    attributes: Dict[str, Any] = field(default_factory=dict)
    relations: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    # relations格式: {relation_type: [target_entity_names]}
    # 例如: {"attended": ["event_name"], "interested_in": ["topic"]}


class TemporalConceptGraph:
    """
    颞叶概念图 - 存储语义知识和实体关系

    核心特点:
    1. 知识图谱结构 (Entity-Relation-Entity)
    2. 支持多跳推理 (traverse_relations)
    3. 支持关系类型查询
    4. O(1)复杂度的实体查询
    """

    def __init__(self):
        # 核心存储
        self.entities: Dict[str, Entity] = {}  # {entity_name: Entity}
        self.relations: List[Tuple[str, str, str]] = []  # [(source, relation, target)]

        # 反向索引
        self.reverse_relations: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        # {target: [(source, relation)]} - 支持反向查询


    def add_entity(
        self,
        name: str,
        entity_type: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        添加实体

        Args:
            name: 实体名称 "PersonA"
            entity_type: 实体类型 "Person"
            attributes: 属性 {"age": 25}
        """
        if name not in self.entities:
            self.entities[name] = Entity(
                name=name,
                entity_type=entity_type,
                attributes=attributes or {}
            )
        else:
            # 更新属性
            if attributes:
                self.entities[name].attributes.update(attributes)

    def add_relation(
        self,
        source: str,
        relation: str,
        target: str,
        source_type: str = 'Unknown',
        target_type: str = 'Unknown'
    ) -> None:
        """
        添加关系

        Args:
            source: 源实体 "PersonA"
            relation: 关系类型 "attended"
            target: 目标实体 "event_name"
            source_type: 源实体类型 (如果不存在则创建)
            target_type: 目标实体类型 (如果不存在则创建)
        """
        # 确保实体存在
        if source not in self.entities:
            self.add_entity(source, source_type)
        if target not in self.entities:
            self.add_entity(target, target_type)

        # 添加关系 (正向)
        self.entities[source].relations[relation].append(target)

        # 添加到关系列表
        relation_tuple = (source, relation, target)
        if relation_tuple not in self.relations:
            self.relations.append(relation_tuple)

        # 添加反向索引
        self.reverse_relations[target].append((source, relation))


    def get_entity(self, name: str) -> Optional[Entity]:
        """获取实体的所有信息"""
        return self.entities.get(name)

    def get_entity_relations(
        self,
        entity_name: str,
        relation_type: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        获取实体的所有关系

        Args:
            entity_name: 实体名称
            relation_type: 关系类型过滤 (可选)

        Returns:
            {relation_type: [target_entities]}
        """
        entity = self.entities.get(entity_name)
        if not entity:
            return {}

        if relation_type:
            return {relation_type: entity.relations.get(relation_type, [])}
        else:
            return dict(entity.relations)

    def get_reverse_relations(self, entity_name: str) -> List[Tuple[str, str]]:
        """
        获取指向该实体的所有关系 (反向查询)

        Args:
            entity_name: 实体名称

        Returns:
            [(source_entity, relation_type), ...]
        """
        return self.reverse_relations.get(entity_name, [])

    def traverse_relations(
        self,
        start_entity: str,
        max_depth: int = 2,
        relation_filter: Optional[List[str]] = None
    ) -> List[List[Tuple[str, str, str]]]:
        """
        遍历关系 (多跳推理)

        Args:
            start_entity: 起始实体
            max_depth: 最大跳数
            relation_filter: 关系类型过滤 (可选)

        Returns:
            路径列表 [[(entity1, relation, entity2), ...], ...]
        """
        paths = []
        visited = set()

        def dfs(entity: str, path: List[Tuple[str, str, str]], depth: int):
            if depth > max_depth:
                return

            if entity in visited:
                return
            visited.add(entity)

            # 保存当前路径
            if path:
                paths.append(path.copy())

            # 获取实体信息
            entity_data = self.entities.get(entity)
            if not entity_data:
                return

            # 遍历所有关系
            for relation, targets in entity_data.relations.items():
                # 关系过滤
                if relation_filter and relation not in relation_filter:
                    continue

                for target in targets:
                    new_path = path + [(entity, relation, target)]
                    dfs(target, new_path, depth + 1)

            visited.remove(entity)  # 回溯

        dfs(start_entity, [], 0)


        return paths

    def find_path(
        self,
        start_entity: str,
        end_entity: str,
        max_depth: int = 3
    ) -> Optional[List[Tuple[str, str, str]]]:
        """
        找到两个实体之间的路径

        Args:
            start_entity: 起始实体
            end_entity: 目标实体
            max_depth: 最大跳数

        Returns:
            路径 [(entity1, relation, entity2), ...] 或 None
        """
        if start_entity not in self.entities or end_entity not in self.entities:
            return None

        # BFS搜索
        from collections import deque

        queue = deque([(start_entity, [])])
        visited = set()

        while queue:
            current, path = queue.popleft()

            if current == end_entity:
                return path

            if len(path) >= max_depth:
                continue

            if current in visited:
                continue
            visited.add(current)

            # 扩展邻居
            entity = self.entities.get(current)
            if not entity:
                continue

            for relation, targets in entity.relations.items():
                for target in targets:
                    new_path = path + [(current, relation, target)]
                    queue.append((target, new_path))

        return None

    def get_neighbors(self, entity_name: str, depth: int = 1) -> List[str]:
        """
        获取实体的邻居 (直接关联的实体)

        Args:
            entity_name: 实体名称
            depth: 邻居深度

        Returns:
            邻居实体名称列表
        """
        neighbors = set()

        def collect_neighbors(entity: str, current_depth: int):
            if current_depth > depth:
                return

            entity_data = self.entities.get(entity)
            if not entity_data:
                return

            # 正向关系
            for targets in entity_data.relations.values():
                for target in targets:
                    if target not in neighbors and target != entity_name:
                        neighbors.add(target)
                        collect_neighbors(target, current_depth + 1)

            # 反向关系
            for source, _ in self.reverse_relations.get(entity, []):
                if source not in neighbors and source != entity_name:
                    neighbors.add(source)
                    collect_neighbors(source, current_depth + 1)

        collect_neighbors(entity_name, 0)


        return list(neighbors)

    def get_entity_subgraph(self, entity_name: str, radius: int = 1) -> Dict[str, Any]:
        """
        获取实体的子图 (实体及其周围的关系)

        Args:
            entity_name: 实体名称
            radius: 子图半径

        Returns:
            {
                'entities': {name: Entity},
                'relations': [(source, relation, target)]
            }
        """
        if entity_name not in self.entities:
            return {'entities': {}, 'relations': []}

        # 收集相关实体
        relevant_entities = {entity_name}
        neighbors = self.get_neighbors(entity_name, depth=radius)
        relevant_entities.update(neighbors)

        # 收集相关关系
        relevant_relations = [
            (s, r, t) for (s, r, t) in self.relations
            if s in relevant_entities and t in relevant_entities
        ]

        subgraph = {
            'entities': {name: self.entities[name] for name in relevant_entities if name in self.entities},
            'relations': relevant_relations
        }


        return subgraph

    def query_by_pattern(
        self,
        subject_pattern: Optional[str] = None,
        relation_pattern: Optional[str] = None,
        object_pattern: Optional[str] = None
    ) -> List[Tuple[str, str, str]]:
        """
        模式查询 (类似SPARQL)

        Args:
            subject_pattern: 主语模式 (None表示通配符)
            relation_pattern: 关系模式 (None表示通配符)
            object_pattern: 宾语模式 (None表示通配符)

        Returns:
            匹配的三元组列表

        Example:
            query_by_pattern(subject_pattern="PersonA", relation_pattern="attended")
            # 返回所有 PersonA attended X 的关系
        """
        results = []

        for (s, r, o) in self.relations:
            match = True

            if subject_pattern and s != subject_pattern:
                match = False
            if relation_pattern and r != relation_pattern:
                match = False
            if object_pattern and o != object_pattern:
                match = False

            if match:
                results.append((s, r, o))


        return results

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_entities': len(self.entities),
            'total_relations': len(self.relations),
            'entity_types': {
                entity_type: sum(1 for e in self.entities.values() if e.entity_type == entity_type)
                for entity_type in set(e.entity_type for e in self.entities.values())
            },
            'relation_types': {
                relation: sum(1 for (_, r, _) in self.relations if r == relation)
                for relation in set(r for (_, r, _) in self.relations)
            }
        }

    def to_dict(self) -> Dict:
        """序列化为字典"""
        return {
            'entities': {
                name: {
                    'name': e.name,
                    'entity_type': e.entity_type,
                    'attributes': e.attributes,
                    'relations': {k: list(v) for k, v in e.relations.items()}
                }
                for name, e in self.entities.items()
            },
            'relations': self.relations
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'TemporalConceptGraph':
        """从字典反序列化"""
        graph = cls()

        # 恢复实体
        for name, entity_data in data.get('entities', {}).items():
            entity = Entity(
                name=entity_data['name'],
                entity_type=entity_data['entity_type'],
                attributes=entity_data.get('attributes', {}),
                relations=defaultdict(list, {
                    k: list(v) for k, v in entity_data.get('relations', {}).items()
                })
            )
            graph.entities[name] = entity

        # 恢复关系列表和反向索引
        for (source, relation, target) in data.get('relations', []):
            graph.relations.append((source, relation, target))
            graph.reverse_relations[target].append((source, relation))


        return graph
