"""
Knowledge Graph Integration with Memory System
知识图谱与记忆系统集成
"""

import asyncio
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from .knowledge_graph import (
    LightweightKnowledgeGraph,
    EntityType,
    RelationType,
    knowledge_graph
)
from .memory_system import memory_system
from ..utils.config import get_logger

logger = get_logger(__name__)


class KGMemoryIntegration:
    """
    知识图谱与记忆系统集成器

    功能：
    1. 从记忆中提取实体和关系
    2. 构建和更新知识图谱
    3. 基于图的记忆检索增强
    4. 上下文扩展和关联发现
    """

    def __init__(self, kg: LightweightKnowledgeGraph, memory_sys):
        self.kg = kg
        self.memory_system = memory_sys

        # 实体识别规则(简单关键词匹配)
        self.entity_patterns = {
            EntityType.PERSON: [
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',  # 英文人名
                r'([\u4e00-\u9fa5]{2,4})'  # 中文姓名
            ],
            EntityType.LOCATION: [
                '北京', '上海', '深圳', '杭州', '广州'  # 常见地点
            ],
            EntityType.TIME: [
                r'(\d{4}年\d{1,2}月\d{1,2}日)',
                r'(昨天|今天|明天|上周|下周)'
            ]
        }

        # 关系识别规则
        self.relation_patterns = {
            RelationType.CAUSES: ['导致', '引起', '造成', 'causes', 'leads to'],
            RelationType.RELATED_TO: ['关于', '相关', '有关', 'about', 'related to'],
            RelationType.PART_OF: ['属于', '是...的一部分', 'part of'],
            RelationType.INVOLVES: ['涉及', '包含', 'involves'],
            RelationType.HAPPENED_AT: ['发生在', '在...时候', 'happened at']
        }

        logger.info("KG-记忆集成器初始化完成")

    # ==================== 实体和关系提取 ====================

    def extract_entities(self, text: str) -> List[Tuple[str, str]]:
        """
        从文本中提取实体

        Returns:
            List of (entity, entity_type) tuples
        """
        entities = []

        # 人名提取
        for pattern in self.entity_patterns[EntityType.PERSON]:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) > 1 and match not in ['什么', '那个', '这个']:
                    entities.append((match, EntityType.PERSON))

        # 地点提取
        for location in self.entity_patterns[EntityType.LOCATION]:
            if location in text:
                entities.append((location, EntityType.LOCATION))

        # 时间提取
        for pattern in self.entity_patterns[EntityType.TIME]:
            matches = re.findall(pattern, text)
            for match in matches:
                entities.append((match, EntityType.TIME))

        # 去重
        entities = list(set(entities))

        return entities

    def extract_relations(self, text: str, entities: List[Tuple[str, str]]) -> List[Tuple[str, str, str]]:
        """
        从文本和实体中提取关系

        Returns:
            List of (entity1, relation_type, entity2) tuples
        """
        relations = []

        if len(entities) < 2:
            return relations

        # 检查关系词
        for relation_type, keywords in self.relation_patterns.items():
            for keyword in keywords:
                if keyword in text:
                    # 简单策略：文本中有关系词，连接相邻实体
                    for i in range(len(entities) - 1):
                        entity1 = entities[i][0]
                        entity2 = entities[i + 1][0]
                        relations.append((entity1, relation_type, entity2))
                    break

        return relations

    # ==================== 记忆到图的转换 ====================

    async def build_kg_from_memory(self, memory_id: str) -> Dict[str, Any]:
        """
        从单个记忆构建KG节点和边

        Args:
            memory_id: 记忆ID

        Returns:
            构建统计信息
        """
        # 使用memory_system的get_memory方法
        memory = self.memory_system.get_memory(memory_id)

        if not memory:
            logger.warning(f"记忆不存在: {memory_id}")
            return {'success': False}

        content = memory.get('content', '')

        # 为记忆本身创建节点
        memory_node_id = f"memory_{memory_id}"
        self.kg.add_node(
            memory_node_id,
            EntityType.MEMORY,
            content,
            properties={
                'memory_id': memory_id,
                'timestamp': memory.get('timestamp', ''),
                'importance': memory.get('importance', 0.5),
                'memory_type': memory.get('memory_type', 'episodic')
            }
        )

        # 提取实体
        entities = self.extract_entities(content)
        nodes_added = 0
        edges_added = 0

        # 为每个实体创建节点
        entity_nodes = []
        for entity, entity_type in entities:
            entity_id = f"{entity_type}_{entity}"

            # 添加实体节点
            if self.kg.add_node(
                entity_id,
                entity_type,
                entity,
                properties={'source_memory': memory_id}
            ):
                nodes_added += 1

            entity_nodes.append(entity_id)

            # 连接实体到记忆
            if self.kg.add_edge(
                memory_node_id,
                entity_id,
                RelationType.INVOLVES,
                strength=0.8
            ):
                edges_added += 1

        # 提取关系
        relations = self.extract_relations(content, entities)

        for entity1, relation_type, entity2 in relations:
            entity1_id = f"{EntityType.CONCEPT}_{entity1}"
            entity2_id = f"{EntityType.CONCEPT}_{entity2}"

            if self.kg.add_edge(
                entity1_id,
                entity2_id,
                relation_type,
                strength=0.6
            ):
                edges_added += 1

        # 连接到已有的相关记忆
        associations = memory.get('associations', [])
        for assoc_id in associations[:5]:  # 限制数量
            assoc_node_id = f"memory_{assoc_id}"
            if self.kg.add_edge(
                memory_node_id,
                assoc_node_id,
                RelationType.RELATED_TO,
                strength=0.7
            ):
                edges_added += 1

        logger.info(f"从记忆 {memory_id} 构建KG: +{nodes_added}节点, +{edges_added}边")

        return {
            'success': True,
            'nodes_added': nodes_added,
            'edges_added': edges_added,
            'entities': entities
        }

    async def batch_build_kg(self, limit: int = 100) -> Dict[str, Any]:
        """
        批量从记忆构建KG

        Args:
            limit: 最多处理的记忆数量
        """
        # 获取最近的记忆
        memories = await self.memory_system.search_memories(
            query="",
            k=limit
        )

        total_nodes = 0
        total_edges = 0
        processed = 0

        for memory in memories:
            memory_id = memory.get('id')
            if not memory_id:
                continue

            result = await self.build_kg_from_memory(memory_id)

            if result.get('success'):
                total_nodes += result.get('nodes_added', 0)
                total_edges += result.get('edges_added', 0)
                processed += 1

        # 保存图
        self.kg.save_graph()

        logger.info(f"批量构建KG完成: 处理{processed}条记忆, "
                   f"+{total_nodes}节点, +{edges_added}边")

        return {
            'processed': processed,
            'total_nodes': total_nodes,
            'total_edges': total_edges
        }

    # ==================== 基于图的检索增强 ====================

    async def graph_enhanced_retrieval(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
        """
        基于知识图谱增强的记忆检索

        策略：
        1. 先用向量检索找到初始记忆
        2. 通过图扩展上下文
        3. 重新排序结果
        """
        # Step 1: 向量检索初始结果
        initial_results = await self.memory_system.search_memories(query, k=k)

        if not initial_results:
            return []

        # Step 2: 提取查询中的实体
        query_entities = self.extract_entities(query)

        # Step 3: 图扩展
        expanded_memory_ids = set()

        for memory in initial_results:
            memory_id = memory.get('id')
            memory_node_id = f"memory_{memory_id}"

            # 如果记忆在图中
            if memory_node_id in self.kg.nodes:
                # 1-hop扩展
                context_nodes = self.kg.expand_context(memory_node_id, depth=1)

                # 提取记忆节点
                for node_id in context_nodes:
                    if node_id.startswith('memory_'):
                        expanded_memory_ids.add(node_id.replace('memory_', ''))

        # Step 4: 获取扩展的记忆
        expanded_results = []

        for memory_id in expanded_memory_ids:
            # 检查是否已在初始结果中
            if any(m.get('id') == memory_id for m in initial_results):
                continue

            # 获取记忆
            memories = await self.memory_system.search_memories(
                query="",
                filters={'id': memory_id}
            )

            if memories:
                memory = memories[0]
                memory['_source'] = 'graph_expansion'
                expanded_results.append(memory)

        # Step 5: 合并结果
        all_results = initial_results + expanded_results[:k]

        logger.info(f"图增强检索: 初始{len(initial_results)}条, "
                   f"扩展{len(expanded_results)}条")

        return all_results[:k * 2]  # 返回更多结果

    async def find_memory_associations(self, memory_id: str,
                                      max_depth: int = 2) -> Dict[str, Any]:
        """
        查找记忆的关联

        Args:
            memory_id: 记忆ID
            max_depth: 最大深度

        Returns:
            关联信息
        """
        memory_node_id = f"memory_{memory_id}"

        if memory_node_id not in self.kg.nodes:
            return {'found': False}

        # 扩展上下文
        context_nodes = self.kg.expand_context(memory_node_id, depth=max_depth)

        # 提取记忆节点
        related_memories = []
        related_entities = []

        for node_id in context_nodes:
            if node_id == memory_node_id:
                continue

            node = self.kg.get_node(node_id)
            if not node:
                continue

            if node.entity_type == EntityType.MEMORY:
                related_memories.append({
                    'memory_id': node_id.replace('memory_', ''),
                    'content': node.content,
                    'importance': node.importance
                })
            else:
                related_entities.append({
                    'entity': node.content,
                    'type': node.entity_type,
                    'importance': node.importance
                })

        # 查找路径
        paths = []
        for related_mem in related_memories[:5]:
            related_node_id = f"memory_{related_mem['memory_id']}"
            path = self.kg.find_shortest_path(memory_node_id, related_node_id)

            if path:
                paths.append({
                    'target': related_mem['memory_id'],
                    'path': path,
                    'length': len(path)
                })

        return {
            'found': True,
            'related_memories': related_memories,
            'related_entities': related_entities,
            'paths': paths,
            'total_context': len(context_nodes)
        }

    # ==================== 图分析 ====================

    async def analyze_memory_importance(self) -> List[Dict[str, Any]]:
        """分析记忆重要性(基于图中心性)"""
        pagerank_scores = self.kg.compute_pagerank()

        # 提取记忆节点的得分
        memory_scores = []

        for node_id, score in pagerank_scores.items():
            if node_id.startswith('memory_'):
                memory_id = node_id.replace('memory_', '')
                node = self.kg.get_node(node_id)

                memory_scores.append({
                    'memory_id': memory_id,
                    'pagerank': score,
                    'content': node.content if node else '',
                    'degree': self.kg.graph.degree(node_id)
                })

        # 按PageRank排序
        memory_scores.sort(key=lambda x: x['pagerank'], reverse=True)

        return memory_scores[:20]

    async def detect_memory_clusters(self) -> List[List[str]]:
        """检测记忆聚类"""
        communities = self.kg.detect_communities()

        # 提取每个社区中的记忆
        memory_clusters = []

        for community in communities:
            memory_ids = []

            for node_id in community:
                if node_id.startswith('memory_'):
                    memory_id = node_id.replace('memory_', '')
                    memory_ids.append(memory_id)

            if memory_ids:
                memory_clusters.append(memory_ids)

        logger.info(f"检测到 {len(memory_clusters)} 个记忆聚类")

        return memory_clusters

    # ==================== 维护和优化 ====================

    async def update_memory_associations_from_kg(self, memory_id: str):
        """从KG更新记忆系统的关联字段"""
        memory_node_id = f"memory_{memory_id}"

        if memory_node_id not in self.kg.nodes:
            return

        # 获取1-hop邻居记忆
        neighbors = self.kg.get_neighbors(memory_node_id)

        association_ids = []
        for neighbor_id in neighbors:
            if neighbor_id.startswith('memory_'):
                assoc_id = neighbor_id.replace('memory_', '')
                association_ids.append(assoc_id)

        # 更新记忆系统
        # (需要memory_system支持更新associations字段)
        logger.info(f"更新记忆 {memory_id} 的关联: {len(association_ids)}个")

    async def prune_weak_connections(self, threshold: float = 0.1):
        """修剪弱连接"""
        removed = 0

        edges_to_remove = []

        for edge_key, edge in self.kg.edges.items():
            if edge.strength < threshold:
                edges_to_remove.append((edge.source_id, edge.target_id, edge.relation_type))

        for source, target, rel_type in edges_to_remove:
            if self.kg.graph.has_edge(source, target, key=rel_type):
                self.kg.graph.remove_edge(source, target, key=rel_type)
                removed += 1

        logger.info(f"修剪了 {removed} 条弱连接")

        return removed


# 全局集成器实例
kg_integration = KGMemoryIntegration(knowledge_graph, memory_system)