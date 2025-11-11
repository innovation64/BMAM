"""
Memory Compression for Prefrontal Agent
内存压缩模块
"""

import logging
import json
from typing import Dict, List, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


class MemoryCompressionMixin:
    """Memory compression mixin for PrefrontalAgent"""

    async def compress_working_memory(
        self,
        information: List[Dict],
        target_slots: int = 7,
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        工作记忆压缩 - 将大量信息压缩到7±2个槽位

        理论依据:
        - Miller (1956) - The Magical Number Seven, Plus or Minus Two
        - Cowan (2001) - The magical number 4 in short-term memory
        - Baddeley (2000) - Working memory capacity chunking

        策略:
        1. 聚类相似信息 (基于embedding或内容相似度)
        2. 提取每个cluster的摘要
        3. 保留最重要的target_slots个摘要

        Args:
            information: 大量信息 (如100个facts)
            target_slots: 目标槽位数 (默认7, 符合Miller's 7±2)
            use_llm: 是否使用LLM生成摘要 (否则使用规则)

        Returns:
            {
                'compressed_info': List[Dict],  # target_slots个压缩槽位
                'compression_ratio': float,     # 压缩比
                'cluster_count': int,            # 聚类数量
                'method': str                    # 压缩方法
            }
        """
        start_time = datetime.now()

        if not information:
            return {
                'compressed_info': [],
                'compression_ratio': 0.0,
                'cluster_count': 0,
                'method': 'empty'
            }

        # Step 1: 聚类相似信息
        clusters = await self._cluster_information(information, target_slots)

        # Step 2: 为每个cluster生成摘要
        compressed_slots = []
        for cluster_id, cluster_items in enumerate(clusters):
            if use_llm:
                summary = await self._summarize_cluster_with_llm(cluster_items, cluster_id)
            else:
                summary = self._summarize_cluster_with_rules(cluster_items, cluster_id)

            compressed_slots.append(summary)

        # Step 3: 按重要性排序 (保留最重要的target_slots个)
        compressed_slots = sorted(
            compressed_slots,
            key=lambda x: x.get('importance', 0.5),
            reverse=True
        )[:target_slots]

        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(
            f"✅ Compressed {len(information)} items → {len(compressed_slots)} slots "
            f"(ratio: {len(information)/len(compressed_slots):.1f}x) in {elapsed_ms:.0f}ms"
        )

        return {
            'compressed_info': compressed_slots,
            'compression_ratio': len(information) / len(compressed_slots) if compressed_slots else 0,
            'cluster_count': len(clusters),
            'method': 'llm' if use_llm else 'rule-based',
            'elapsed_ms': elapsed_ms
        }

    async def _cluster_information(
        self,
        information: List[Dict],
        target_clusters: int
    ) -> List[List[Dict]]:
        """
        聚类相似信息 (基于内容相似度)

        使用简单的贪心聚类:
        1. 初始化target_clusters个空聚类
        2. 对每个信息项,找到最相似的聚类加入
        3. 如果所有聚类都不相似,创建新聚类
        """
        if len(information) <= target_clusters:
            # 信息量少于目标槽位数,直接每个一个cluster
            return [[item] for item in information]

        # 初始化聚类 (以前target_clusters个item为中心)
        clusters: List[List[Dict]] = []
        for i in range(min(target_clusters, len(information))):
            clusters.append([information[i]])

        # 将剩余item分配到最相似的cluster
        for item in information[target_clusters:]:
            best_cluster_idx = 0
            best_similarity = 0.0

            for cluster_idx, cluster in enumerate(clusters):
                # 计算与cluster中所有item的平均相似度
                similarities = []
                for cluster_item in cluster:
                    sim = self._content_similarity(
                        str(item.get('content', '')),
                        str(cluster_item.get('content', ''))
                    )
                    similarities.append(sim)

                avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0

                if avg_similarity > best_similarity:
                    best_similarity = avg_similarity
                    best_cluster_idx = cluster_idx

            # 如果相似度太低(<0.1),考虑创建新cluster (但不超过target_clusters*1.5)
            if best_similarity < 0.1 and len(clusters) < int(target_clusters * 1.5):
                clusters.append([item])
            else:
                clusters[best_cluster_idx].append(item)

        return clusters

    async def _summarize_cluster_with_llm(
        self,
        cluster_items: List[Dict],
        cluster_id: int
    ) -> Dict[str, Any]:
        """使用LLM生成cluster摘要"""
        # 构建prompt
        contents = []
        for item in cluster_items[:10]:  # 最多10个item避免超长
            contents.append(str(item.get('content', '')))

        prompt = f"""Summarize the following {len(cluster_items)} related pieces of information into a single concise summary (2-3 sentences max):

{chr(10).join(f"{i+1}. {c}" for i, c in enumerate(contents))}

Provide:
1. A brief summary
2. Key entities/concepts mentioned
3. Importance score (0-1)"""

        try:
            # 使用client调用LLM
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a summarization expert."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )

            summary_text = response.choices[0].message.content

            # 简单解析(实际可以用JSON)
            return {
                'cluster_id': cluster_id,
                'summary': summary_text,
                'item_count': len(cluster_items),
                'importance': 0.7,  # 默认重要性
                'source_items': cluster_items
            }

        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            logger.warning(f"LLM summarization failed: {e}, fallback to rule-based")
            return self._summarize_cluster_with_rules(cluster_items, cluster_id)

    def _summarize_cluster_with_rules(
        self,
        cluster_items: List[Dict],
        cluster_id: int
    ) -> Dict[str, Any]:
        """基于规则生成cluster摘要"""
        # 提取最常见的词汇作为主题
        all_words = []
        for item in cluster_items:
            content = str(item.get('content', ''))
            words = [w.lower() for w in content.split() if len(w) > 3]
            all_words.extend(words)

        # 词频统计
        from collections import Counter
        word_freq = Counter(all_words)
        top_words = [word for word, _ in word_freq.most_common(5)]

        # 构建摘要
        summary = f"Cluster {cluster_id}: {len(cluster_items)} items about {', '.join(top_words[:3])}"

        # 计算重要性 (cluster越大越重要)
        importance = min(1.0, len(cluster_items) / 10.0)

        return {
            'cluster_id': cluster_id,
            'summary': summary,
            'item_count': len(cluster_items),
            'importance': importance,
            'key_concepts': top_words,
            'source_items': cluster_items
        }
