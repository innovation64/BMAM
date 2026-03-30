"""
Search operations for Temporal Lobe Agent
搜索操作模块(BM25 + Embedding + Hybrid)
"""

import logging
import string
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional

from .data_models import MemoryType

logger = logging.getLogger(__name__)


class SearchMixin:
    """Search operations mixin for TemporalLobeAgent"""

    async def search_memories(
        self,
        query: str,
        memory_subtype: str = None,
        memory_type: Optional[MemoryType] = None,
        k: int = 10
    ) -> Dict[str, Any]:
        """
        搜索语义记忆 (BM25关键词 + Embedding语义相似度融合)

        Args:
            query: 查询文本
            memory_subtype: 'semantic' or 'common_sense' (None = 所有)
            memory_type: MemoryType枚举 (FACTUAL/RELATIONAL/TEMPORAL/PROCEDURAL/SUMMARY, None = 所有)
            k: 返回数量

        Returns:
            {'memories': List[Dict], 'count': int, 'search_time_ms': float}
        """

        start_time = datetime.now()
        results = []

        # 🔥 优先级2: 计算query的embedding（如果embedding_service可用）
        query_embedding = None
        if self.embedding_service:
            try:
                query_embedding = await self.embedding_service.encode_text(query)
                # 转换为list（避免numpy序列化问题）
                if hasattr(query_embedding, 'tolist'):
                    query_embedding = query_embedding.tolist()
            except (RuntimeError, ValueError) as e:
                logger.warning(f"Failed to compute query embedding: {e}")

        # 🔥 BM25-like关键词匹配 + 放宽匹配条件
        # 去除标点符号，统一小写
        query_clean = query.translate(str.maketrans('', '', string.punctuation))
        query_words = set(query_clean.lower().split())

        # 使用倒排索引加速检索
        candidate_ids = set()
        for word in query_words:
            candidate_ids.update(self.inverted_index.get(word, []))

        # 如果倒排索引没有结果,fallback到全文搜索（避免0召回）
        if not candidate_ids:
            candidates = self.memories
        else:
            candidates = [self.memory_dict[mid] for mid in candidate_ids if mid in self.memory_dict]
            # 如果候选太少,也加入全部记忆作为备选
            if len(candidates) < k:
                candidates = self.memories

        # 计算相关性并过滤（放宽overlap要求）
        for mem in candidates:
            # 类型过滤
            if memory_subtype and mem.memory_subtype != memory_subtype:
                continue

            # 🔥 阶段1: 按memory_type过滤（用于类型感知检索）
            if memory_type and mem.memory_type != memory_type:
                continue

            # 🔥 标记LLM生成的摘要（用于后续降权，而非直接排除）
            is_llm_summary = mem.metadata and 'source_episode_id' in mem.metadata

            # 对content也去除标点，统一小写
            content_clean = mem.content.translate(str.maketrans('', '', string.punctuation))
            content_words = set(content_clean.lower().split())
            overlap = len(query_words & content_words)

            # 🔥 2025-12-13 FIX: 同时搜索original_content（如果存在）
            # 这样即使LLM摘要丢失了某些关键词，仍然可以通过原文匹配
            original_content_overlap = 0
            if mem.metadata and 'original_content' in mem.metadata:
                original = mem.metadata['original_content']
                original_clean = original.translate(str.maketrans('', '', string.punctuation))
                original_words = set(original_clean.lower().split())
                original_content_overlap = len(query_words & original_words)
                # 使用原文和摘要中更高的overlap
                overlap = max(overlap, original_content_overlap)

            # 🔥 BM25 分数（含 IDF 加权）
            import math
            if overlap > 0:
                content_words_list = content_clean.lower().split()
                doc_len = len(content_words_list)
                avg_doc_len = sum(len((m.content or '').split()) for m in candidates) / max(len(candidates), 1)
                k1, b = 1.5, 0.75
                bm25_score = 0.0
                for word in query_words:
                    if word not in content_clean.lower():
                        continue
                    tf = content_words_list.count(word)
                    df = len(self.inverted_index.get(word, []))
                    idf = math.log(1 + max(0, (len(self.memories) - df + 0.5) / (df + 0.5)))
                    numerator = tf * (k1 + 1)
                    denominator = tf + k1 * (1 - b + b * (doc_len / max(avg_doc_len, 1)))
                    bm25_score += idf * (numerator / max(denominator, 0.001))
                bm25_score = min(bm25_score / 10.0, 1.0)
            else:
                # 保底分数：基于重要性
                bm25_score = 0.1 * mem.importance

            # 🔥 2025-12-13 FIX: 如果通过original_content匹配成功，提升分数而非降权
            if is_llm_summary:
                if original_content_overlap > 0:
                    # 原文匹配成功，加分
                    bm25_score *= 1.2
                else:
                    # 只匹配摘要，降权
                    bm25_score *= 0.5

            # 🔥 优先级2: Embedding相似度分数（如果可用）
            embedding_score = 0.0
            if query_embedding and mem.embedding:
                try:
                    # 计算余弦相似度
                    q_vec = np.array(query_embedding)
                    m_vec = np.array(mem.embedding)
                    cosine_sim = np.dot(q_vec, m_vec) / (np.linalg.norm(q_vec) * np.linalg.norm(m_vec))
                    # 余弦相似度范围[-1, 1]，归一化到[0, 1]
                    embedding_score = (cosine_sim + 1) / 2
                except (RuntimeError, ValueError) as e:
                    logger.warning(f"Failed to compute cosine similarity: {e}")

            # 🔧 2025-12-02: 恢复混合模式，使用保守的embedding权重
            # LLM摘要已在上方降权(bm25_score *= 0.5)，可以安全使用混合模式
            # 权重: 0.7 * BM25 + 0.3 * Embedding (BM25主导，embedding辅助)
            if embedding_score > 0:
                relevance = 0.7 * bm25_score + 0.3 * embedding_score
            else:
                relevance = bm25_score  # Fallback to pure BM25 if no embedding

            results.append({
                'memory': mem,
                'relevance': relevance,
                'bm25_score': bm25_score,
                'embedding_score': embedding_score
            })

        # 更新访问统计
        for item in results:
            mem = item['memory']
            mem.access_count += 1
            mem.last_accessed = datetime.now()
            metadata = mem.metadata or {}
            metadata['hit_count'] = mem.access_count
            metadata['last_accessed'] = mem.last_accessed.isoformat()
            metadata.setdefault('last_access_context', {})
            metadata['last_access_context']['query'] = query
            metadata['last_access_context']['memory_subtype'] = memory_subtype
            if memory_type:
                metadata['last_access_context']['memory_type'] = memory_type.name if hasattr(memory_type, 'name') else str(memory_type)
            mem.metadata = metadata

        # 排序: relevance > consolidation_level > importance > timestamp
        results.sort(
            key=lambda x: (
                x['relevance'],
                x['memory'].consolidation_level,
                x['memory'].importance,
                x['memory'].timestamp
            ),
            reverse=True
        )

        # 限制返回数量
        results = results[:k]

        search_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            'memories': [self._memory_to_dict(r['memory']) for r in results],
            'count': len(results),
            'search_time_ms': search_time
        }

    async def search_by_entities(
        self,
        entities: List[str],
        k: int = 20
    ) -> List[Dict[str, Any]]:
        """
        基于实体检索记忆

        P0硬编码清除：协调层需要这个接口来检索KG相关记忆

        Args:
            entities: 实体列表
            k: 返回数量

        Returns:
            记忆列表（带kg_relevance字段）
        """
        entity_set = set(entities)
        kg_related = []

        for mem in self.memories:
            # 计算实体交集
            mem_entities = set(mem.entities)
            overlap = mem_entities & entity_set

            if overlap:
                # KG相关度 = overlap_size / total_entities
                kg_relevance = len(overlap) / len(entity_set) if entity_set else 0

                mem_dict = self._memory_to_dict(mem)
                mem_dict['kg_relevance'] = kg_relevance
                mem_dict['matched_entities'] = list(overlap)

                kg_related.append(mem_dict)

        # 按KG相关度排序
        kg_related.sort(key=lambda x: x['kg_relevance'], reverse=True)

        # 返回TopK
        return kg_related[:k]

    async def search_memories_hybrid(
        self,
        query: str,
        memory_subtype: str = None,
        k: int = 10,
        alpha: float = 0.5,  # 默认均衡，由上层协调器动态调整
        use_client: bool = True
    ) -> Dict[str, Any]:
        """
        Phase 2核心功能: 混合检索 (BM25关键词 + Vector语义)

        理论依据:
        - Robertson & Zaragoza (2009) - BM25检索算法
        - Sentence-BERT (Reimers & Gurevych, 2019) - 语义向量检索
        - Hybrid Search (Luan et al., 2021) - 混合检索优于单一方法

        Phase 2增强:
        - BM25关键词检索 (已有inverted_index)
        - Vector语义检索 (通过client embedding)
        - 算法化融合: final_score = alpha * bm25_score + (1-alpha) * vector_score

        Args:
            query: 查询文本
            memory_subtype: 'semantic' or 'common_sense' (None = 所有)
            k: 返回数量
            alpha: BM25权重 (0-1), vector权重 = 1-alpha
                   alpha=1: 纯BM25
                   alpha=0: 纯语义
                   alpha=0.5: 均衡混合
            use_client: 是否使用client (False则fallback到纯BM25)

        Returns:
            {'memories': List[Dict], 'count': int, 'method': str, 'search_time_ms': float}
        """

        start_time = datetime.now()

        # Step 1: BM25关键词检索 (复用现有逻辑)
        bm25_results = await self.search_memories(
            query=query,
            memory_subtype=memory_subtype,
            k=k * 3  # 检索更多候选,后续融合时筛选
        )

        bm25_memories = bm25_results['memories']

        # 如果没有client或alpha=1,直接返回BM25结果
        if not use_client or self.client is None or alpha >= 1.0:
            return {
                'memories': bm25_memories[:k],
                'count': len(bm25_memories[:k]),
                'method': 'bm25_only',
                'search_time_ms': (datetime.now() - start_time).total_seconds() * 1000
            }

        # Step 2: Vector语义检索 (使用client embedding)
        try:
            from ....core.constants import DEFAULT_EMBEDDING_MODEL

            # 获取查询向量
            query_embedding_response = await self.client.embeddings.create(
                input=[query],
                model=DEFAULT_EMBEDDING_MODEL
            )
            query_vector = query_embedding_response.data[0].embedding

            # 计算所有候选记忆的向量相似度
            vector_scores = {}

            for mem_dict in bm25_memories:
                mem_id = mem_dict['id']
                mem_content = mem_dict['content']

                # 获取记忆向量
                mem_embedding_response = await self.client.embeddings.create(
                    input=[mem_content],
                    model=DEFAULT_EMBEDDING_MODEL
                )
                mem_vector = mem_embedding_response.data[0].embedding

                # 算法: 余弦相似度 = dot(A, B) / (||A|| * ||B||)
                dot_product = sum(a * b for a, b in zip(query_vector, mem_vector))
                query_norm = sum(x ** 2 for x in query_vector) ** 0.5
                mem_norm = sum(x ** 2 for x in mem_vector) ** 0.5

                cosine_sim = dot_product / (query_norm * mem_norm) if query_norm > 0 and mem_norm > 0 else 0
                vector_scores[mem_id] = cosine_sim

        except (RuntimeError, ValueError) as e:
            logger.warning(f"⚠️ Vector search failed: {e}, fallback to BM25")
            return {
                'memories': bm25_memories[:k],
                'count': len(bm25_memories[:k]),
                'method': 'bm25_fallback',
                'search_time_ms': (datetime.now() - start_time).total_seconds() * 1000
            }

        # Step 3: 混合融合 (算法: 加权平均)
        # BM25分数归一化 (假设BM25在search_memories中已排序,分数递减)
        bm25_scores = {}
        for idx, mem_dict in enumerate(bm25_memories):
            # 算法: 归一化BM25分数 (线性递减,最高1.0,最低0.0)
            normalized_score = 1.0 - (idx / len(bm25_memories)) if len(bm25_memories) > 0 else 0
            bm25_scores[mem_dict['id']] = normalized_score

        # 融合分数
        hybrid_results = []

        for mem_dict in bm25_memories:
            mem_id = mem_dict['id']

            # 算法: hybrid_score = alpha * bm25_score + (1-alpha) * vector_score
            bm25_score = bm25_scores.get(mem_id, 0)
            vector_score = vector_scores.get(mem_id, 0)

            hybrid_score = alpha * bm25_score + (1 - alpha) * vector_score

            hybrid_results.append({
                'memory': mem_dict,
                'hybrid_score': hybrid_score,
                'bm25_score': bm25_score,
                'vector_score': vector_score
            })

        # Step 4: 按混合分数排序
        hybrid_results.sort(key=lambda x: x['hybrid_score'], reverse=True)

        # Step 5: 返回TopK
        final_memories = [r['memory'] for r in hybrid_results[:k]]

        search_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            'memories': final_memories,
            'count': len(final_memories),
            'method': 'hybrid',
            'alpha': alpha,
            'search_time_ms': search_time,
            'score_breakdown': [
                {
                    'id': r['memory']['id'][:8],
                    'hybrid': round(r['hybrid_score'], 3),
                    'bm25': round(r['bm25_score'], 3),
                    'vector': round(r['vector_score'], 3)
                } for r in hybrid_results[:k]
            ]
        }
