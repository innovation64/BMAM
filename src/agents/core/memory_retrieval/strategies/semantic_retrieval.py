"""
Semantic Retrieval Strategy
语义检索策略 - 向量相似度 + BM25关键词检索
"""

from .base import RetrievalStrategy
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import re
from collections import Counter
import math

logger = logging.getLogger(__name__)


class SemanticRetrievalStrategy(RetrievalStrategy):
    """
    语义检索策略

    检索路径:
    1. 向量相似度检索 (主路径)
    2. BM25关键词检索 (后备路径)
    3. 时间范围过滤
    4. 按置信度和时效性排序

    特性:
    - 混合检索(vector + keyword)
    - 关键词变体扩展
    - 时间过滤和时效性加权
    - 自动后备策略
    """

    @property
    def strategy_name(self) -> str:
        return "semantic"

    async def retrieve(
        self,
        query: str,
        k: int = 10,
        time_range: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        语义检索主入口

        Args:
            query: 查询文本
            k: 返回结果数量
            time_range: 时间范围过滤 {'start': ISO时间, 'end': ISO时间}

        Returns:
            {
                'memories': List[Dict],
                'total_count': int,
                'strategy': str,
                'fallback_used': bool
            }
        """
        logger.info(f"Semantic retrieval: query='{query}', k={k}")

        # 1. 向量检索
        memories = await self._vector_search(query, k)
        fallback_used = False

        # 2. 如果向量检索无结果,尝试BM25关键词检索
        if not memories and self.db_manager:
            logger.info("Vector search empty, fallback to BM25 keyword search")
            memories = await self._bm25_search(query, k)
            fallback_used = True

        # 3. 时间范围过滤
        if time_range:
            memories = self._filter_by_time_range(memories, time_range)

        # 4. 按置信度和时效性排序
        memories = self._sort_by_confidence_and_recency(memories)

        # 5. 更新访问统计
        for mem in memories:
            if 'memory' in mem:
                self._update_memory_access(mem['memory'])

        return {
            'memories': memories,
            'total_count': len(memories),
            'strategy': self.strategy_name,
            'fallback_used': fallback_used,
            'query': query
        }

    async def _vector_search(self, query: str, k: int) -> List[Dict]:
        """
        向量相似度检索

        Args:
            query: 查询文本
            k: 返回数量

        Returns:
            记忆列表
        """
        if not self.embedding_service or not self.vector_db:
            logger.warning("Embedding service or vector DB not available")
            return []

        try:
            # 生成query embedding
            query_embedding = await self.embedding_service.encode_text(query)

            # 向量检索
            similar_memories = self.vector_db.search(
                query_embedding,
                k=k,
                threshold=0.3  # 过滤低相似度结果
            )

            logger.info(f"Vector search found {len(similar_memories)} memories")

            # 加载完整记忆对象
            memories = []
            for memory_id, similarity in similar_memories:
                memory = self.db_manager.load_memory(memory_id) if self.db_manager else None
                if memory:
                    memories.append({
                        'memory': memory.to_dict(),
                        'similarity': similarity,
                        'retrieval_confidence': similarity,  # 初始置信度=相似度
                        'retrieval_method': 'vector'
                    })

            return memories

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def _bm25_search(
        self,
        query: str,
        k: int,
        max_docs: int = 250
    ) -> List[Dict]:
        """
        BM25关键词检索 (后备策略)

        实现TF-IDF加权的BM25算法

        Args:
            query: 查询文本
            k: 返回数量
            max_docs: 最大搜索文档数

        Returns:
            记忆列表
        """
        if not self.db_manager:
            return []

        try:
            # 1. 分词和扩展
            query_tokens = self._tokenize(query)
            expanded_tokens = self._expand_keyword_variants(query_tokens)

            logger.info(
                f"BM25 search: {len(query_tokens)} tokens "
                f"→ {len(expanded_tokens)} expanded"
            )

            # 2. 获取候选文档
            all_memories = self.db_manager.search_memories(limit=max_docs)
            if not all_memories:
                return []

            # 3. 计算BM25分数
            # 参数: k1=1.5, b=0.75 (BM25标准参数)
            k1 = 1.5
            b = 0.75

            # 计算平均文档长度
            avg_doc_length = sum(
                len(self._tokenize(m.content)) for m in all_memories
            ) / len(all_memories)

            # 计算IDF (逆文档频率)
            doc_freq = Counter()
            for memory in all_memories:
                doc_tokens = set(self._tokenize(memory.content))
                for token in expanded_tokens:
                    if token in doc_tokens:
                        doc_freq[token] += 1

            idf = {}
            num_docs = len(all_memories)
            for token in expanded_tokens:
                df = doc_freq.get(token, 0)
                if df > 0:
                    idf[token] = math.log((num_docs - df + 0.5) / (df + 0.5) + 1.0)
                else:
                    idf[token] = 0.0

            # 4. 计算每个文档的BM25分数
            scored_memories = []
            for memory in all_memories:
                doc_tokens = self._tokenize(memory.content)
                doc_length = len(doc_tokens)
                token_freq = Counter(doc_tokens)

                bm25_score = 0.0
                for token in expanded_tokens:
                    if token in token_freq:
                        tf = token_freq[token]
                        # BM25公式
                        numerator = tf * (k1 + 1)
                        denominator = tf + k1 * (1 - b + b * doc_length / avg_doc_length)
                        bm25_score += idf.get(token, 0.0) * (numerator / denominator)

                if bm25_score > 0:
                    scored_memories.append({
                        'memory': memory.to_dict(),
                        'similarity': min(bm25_score / 10.0, 0.9),  # 归一化到[0,0.9]
                        'retrieval_confidence': min(bm25_score / 15.0, 0.8),
                        'retrieval_method': 'bm25',
                        'bm25_score': bm25_score
                    })

            # 5. 排序并返回top-k
            scored_memories.sort(key=lambda m: m['bm25_score'], reverse=True)
            return scored_memories[:k]

        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []

    def _tokenize(self, text: str) -> List[str]:
        """
        文本分词

        支持中英文混合分词

        Args:
            text: 输入文本

        Returns:
            词token列表
        """
        # 转小写
        text = text.lower()

        # 提取中文字符和英文单词
        # 中文: 单字分词
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)

        # 英文: 单词分词
        english_words = re.findall(r'[a-z]+', text)

        # 数字
        numbers = re.findall(r'\d+', text)

        return chinese_chars + english_words + numbers

    def _expand_keyword_variants(self, tokens: List[str]) -> List[str]:
        """
        关键词变体扩展

        扩展同义词、相关词

        Args:
            tokens: 原始tokens

        Returns:
            扩展后的tokens
        """
        expanded = set(tokens)

        # 定义扩展规则 (可以扩展为更复杂的同义词库)
        expansion_rules = {
            'ai': ['artificial', 'intelligence', '人工智能'],
            'ml': ['machine', 'learning', '机器学习'],
            'dl': ['deep', 'learning', '深度学习'],
            '茶': ['tea', '喝茶', '饮茶'],
            '绿茶': ['green', 'tea'],
            '咖啡': ['coffee'],
            '时间': ['time', '何时', 'when'],
        }

        for token in tokens:
            if token in expansion_rules:
                expanded.update(expansion_rules[token])

        return list(expanded)

    def _sort_by_confidence_and_recency(self, memories: List[Dict]) -> List[Dict]:
        """
        按置信度和时效性排序

        最近的记忆获得小额加分

        Args:
            memories: 记忆列表

        Returns:
            排序后的记忆列表
        """
        if not memories:
            return memories

        def get_sort_key(mem):
            confidence = mem.get('retrieval_confidence', 0.0)

            # 时效性加分
            recency_bonus = 0.0
            timestamp_str = self._extract_timestamp(mem)

            if timestamp_str:
                try:
                    mem_time = datetime.fromisoformat(
                        timestamp_str.replace('Z', '+00:00')
                    ).replace(tzinfo=None)

                    age_hours = (datetime.now() - mem_time).total_seconds() / 3600

                    # 7天内的记忆获得递减加分 (最高0.1)
                    recency_bonus = max(0, 0.1 * (1 - age_hours / (7 * 24)))

                except Exception:
                    pass

            return confidence + recency_bonus

        try:
            memories.sort(key=get_sort_key, reverse=True)
        except Exception as e:
            logger.warning(f"Failed to sort memories: {e}")

        return memories
