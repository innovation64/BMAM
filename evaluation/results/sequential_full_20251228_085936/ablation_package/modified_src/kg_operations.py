"""
Knowledge Graph operations for Temporal Lobe Agent
知识图谱操作模块
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)


# 🔥 2025-12-30: 消融实验支持
def _is_kg_enabled() -> bool:
    """检查 Knowledge Graph 是否启用"""
    try:
        from ....config.ablation_config import is_component_enabled
        return is_component_enabled('kg')
    except ImportError:
        return True  # 默认启用


class KGOperationsMixin:
    """Knowledge Graph operations mixin for TemporalLobeAgent"""

    def query_knowledge_graph(
        self,
        entity: str,
        relation: str = None
    ) -> Dict[str, Any]:
        """
        查询知识图谱

        Args:
            entity: 实体名称
            relation: 关系类型 (None = 所有关系)

        Returns:
            {'triples': List[Tuple[str, str, str]], 'count': int}
        """

        # 🔥 2025-12-30: 消融实验检查
        if not _is_kg_enabled():
            logger.warning("⚠️ 消融实验: Knowledge Graph 已禁用")
            return {'triples': [], 'count': 0, 'entity': entity, 'relation': relation, 'ablation_disabled': True}

        triples = self.kg.query_relations(entity, relation)

        return {
            'triples': triples,
            'count': len(triples),
            'entity': entity,
            'relation': relation
        }

    def multi_hop_reasoning(
        self,
        start_entity: str,
        max_depth: int = 2
    ) -> Dict[str, Any]:
        """
        多跳推理

        Args:
            start_entity: 起始实体
            max_depth: 最大跳数

        Returns:
            {'paths': List[List[Tuple]], 'count': int}
        """

        # 🔥 2025-12-30: 消融实验检查
        if not _is_kg_enabled():
            logger.warning("⚠️ 消融实验: Knowledge Graph 已禁用 (multi_hop)")
            return {'paths': [], 'count': 0, 'start_entity': start_entity, 'max_depth': max_depth, 'ablation_disabled': True}

        paths = self.kg.multi_hop_query(start_entity, max_depth)

        return {
            'paths': paths,
            'count': len(paths),
            'start_entity': start_entity,
            'max_depth': max_depth
        }

    async def get_kg_entities(self) -> List[str]:
        """
        获取KG中的所有实体

        P0硬编码清除：协调层需要这个接口来提取查询中的实体

        Returns:
            实体列表
        """
        return list(self.kg.graph.nodes()) if self.kg else []

    async def query_kg_multi_hop(
        self,
        start_entity: str,
        max_depth: int = 1
    ) -> List[List[Tuple[str, str, str]]]:
        """
        KG多跳查询

        P0硬编码清除：协调层需要这个接口来扩展KG实体

        Args:
            start_entity: 起始实体
            max_depth: 最大跳数

        Returns:
            路径列表，每个路径是三元组列表
        """
        if not self.kg:
            return []

        return self.kg.multi_hop_query(start_entity, max_depth=max_depth)

    async def search_kg_memory_joint(
        self,
        query: str,
        start_entity: str = None,
        k: int = 10,
        kg_depth: int = 1,
        beta: float = 0.6
    ) -> Dict[str, Any]:
        """
        Phase 2核心功能: KG-Memory联合检索

        理论依据:
        - Miller (1995) - WordNet: 知识图谱增强语义理解
        - Sun et al. (2019) - 知识图谱+文本检索联合优于单独使用

        Phase 2增强:
        - 知识图谱扩展 (实体→多跳关系→相关实体)
        - 记忆检索 (扩展后的实体集合)
        - 算法化融合: 优先KG关系记忆, 补充语义记忆

        Args:
            query: 查询文本
            start_entity: 起始实体 (None则从query提取)
            k: 返回数量
            kg_depth: 知识图谱跳数 (1-2)
            beta: KG权重 (0-1), memory权重 = 1-beta

        Returns:
            {
                'memories': List[Dict],
                'kg_expanded_entities': List[str],
                'kg_paths': List[List[Tuple]],
                'count': int
            }
        """

        # Step 1: 提取起始实体
        if not start_entity:
            # 算法: 从query中匹配KG中的实体 (精确匹配)
            query_lower = query.lower()
            matched_entities = []

            for entity in self.kg.graph.nodes():
                if entity.lower() in query_lower:
                    matched_entities.append(entity)

            if matched_entities:
                # 选择最长的实体 (算法: 贪心匹配最具体实体)
                start_entity = max(matched_entities, key=len)
            else:
                # Fallback: 纯记忆检索
                return await self.search_memories(query=query, k=k)

        # Step 2: KG扩展 (多跳推理)
        kg_paths = self.kg.multi_hop_query(start_entity, max_depth=kg_depth)

        # 收集扩展实体
        expanded_entities = {start_entity}

        for path in kg_paths:
            for (source, relation, target) in path:
                expanded_entities.add(source)
                expanded_entities.add(target)

        # Step 3: 基于扩展实体检索记忆 (算法: 实体集合匹配)
        kg_related_memories = []

        for mem in self.memories:
            # 算法: 记忆实体与扩展实体集合的交集
            mem_entities = set(mem.entities)
            overlap = mem_entities & expanded_entities

            if overlap:
                # KG相关度 = overlap_size / total_kg_entities
                kg_relevance = len(overlap) / len(expanded_entities) if len(expanded_entities) > 0 else 0

                kg_related_memories.append({
                    'memory': mem,
                    'kg_relevance': kg_relevance,
                    'matched_entities': list(overlap)
                })

        # Step 4: 补充语义记忆 (非KG相关但语义相关)
        semantic_results = await self.search_memories(query=query, k=k * 2)
        semantic_memories = semantic_results['memories']

        # 过滤掉已在kg_related_memories中的记忆
        kg_mem_ids = {r['memory'].id for r in kg_related_memories}
        supplementary_memories = []

        for mem_dict in semantic_memories:
            if mem_dict['id'] not in kg_mem_ids:
                # 重建SemanticMemory对象
                if mem_dict['id'] in self.memory_dict:
                    mem = self.memory_dict[mem_dict['id']]
                    supplementary_memories.append({
                        'memory': mem,
                        'semantic_relevance': 0.5,  # 默认语义相关度
                        'matched_entities': []
                    })

        # Step 5: 融合排序 (算法: beta * kg_relevance + (1-beta) * semantic_relevance)
        all_results = []

        for r in kg_related_memories:
            final_score = beta * r['kg_relevance'] + (1 - beta) * 0.3  # KG记忆默认语义0.3
            all_results.append({
                'memory': r['memory'],
                'score': final_score,
                'kg_relevance': r['kg_relevance'],
                'matched_entities': r['matched_entities'],
                'source': 'kg'
            })

        for r in supplementary_memories[:k]:  # 限制补充数量
            final_score = beta * 0.0 + (1 - beta) * r['semantic_relevance']
            all_results.append({
                'memory': r['memory'],
                'score': final_score,
                'kg_relevance': 0.0,
                'matched_entities': r['matched_entities'],
                'source': 'semantic'
            })

        # 排序
        all_results.sort(key=lambda x: x['score'], reverse=True)

        # Step 6: TopK
        final_results = all_results[:k]

        # 更新访问统计
        for r in final_results:
            r['memory'].access_count += 1
            r['memory'].last_accessed = datetime.now()

        return {
            'memories': [self._memory_to_dict(r['memory']) for r in final_results],
            'kg_expanded_entities': list(expanded_entities),
            'kg_paths': kg_paths[:5],  # 返回前5条路径示例
            'count': len(final_results),
            'score_breakdown': [
                {
                    'id': r['memory'].id[:8],
                    'score': round(r['score'], 3),
                    'kg_rel': round(r['kg_relevance'], 3),
                    'source': r['source'],
                    'entities': r['matched_entities']
                } for r in final_results
            ]
        }
