"""
KG Merge Refactored - 重构的 KG 融合逻辑
使用配置化参数，取代硬编码常量

Team F – KG Merge Parametrization
这个文件提供了重构后的 _merge_kg_and_vector_results 实现
可以直接替换 brain_coordinator.py 中的原实现
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from .kg_merge_config import KGMergeConfig, get_kg_merge_config

logger = logging.getLogger(__name__)


class KGMerger:
    """
    知识图谱融合器

    使用配置化参数进行 KG facts 与 vector memories 的融合
    """

    def __init__(self, config: KGMergeConfig = None):
        """
        初始化融合器

        Args:
            config: KG 融合配置（None 则使用全局配置）
        """
        self.config = config or get_kg_merge_config()

    async def merge_kg_and_vector_results(
        self,
        vector_memories: List[Dict[str, Any]],
        kg_facts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        融合 KG facts 与 vector memories

        这是重构后的版本，所有参数都来自配置

        Strategy:
        1. Quality filter: 只使用高质量 KG facts（避免噪声）
        2. KG facts 优先（插入到前面）如果高质量
        3. Smart deduplication: 移除与 KG 重叠的 vector 结果
        4. 保留 vector memories（它们通常包含关键上下文）

        Args:
            vector_memories: Vector 检索的记忆列表
            kg_facts: KG 提取的事实列表

        Returns:
            融合后的记忆列表
        """
        if not kg_facts:
            return vector_memories

        # Step 1: 过滤高质量 KG facts
        high_quality_kg_facts = self._filter_high_quality_kg_facts(kg_facts)

        # 如果没有高质量 KG facts，直接返回 vector memories
        if not high_quality_kg_facts:
            if self.config.log_merge_details:
                logger.info("No high-quality KG facts found, returning vector memories only")
            return vector_memories

        # Step 2: KG facts 放在前面（如果配置允许）
        if self.config.kg_facts_at_front:
            merged = high_quality_kg_facts.copy()
        else:
            merged = []

        # Step 3: 提取 KG 内容短语（用于去重）
        kg_content_phrases = self._extract_kg_phrases(high_quality_kg_facts)

        # Step 4: 过滤 vector results（去除高重叠的）
        filtered_vector_memories = self._filter_overlapping_memories(
            vector_memories,
            kg_content_phrases
        )

        # Step 5: 合并结果
        if self.config.kg_facts_at_front:
            merged.extend(filtered_vector_memories)
        else:
            # 不强制 KG 在前，按 plasticity_score 排序
            merged = high_quality_kg_facts + filtered_vector_memories
            merged.sort(key=lambda x: x.get('plasticity_score', 0.0), reverse=True)

        # Step 6: 限制总数量
        max_results = min(
            len(vector_memories) + len(high_quality_kg_facts),
            self.config.max_merged_results
        )
        merged = merged[:max_results]

        # 日志
        if self.config.log_merge_details:
            logger.info(
                f"✅ Merged {len(high_quality_kg_facts)} high-quality KG facts + "
                f"{len(filtered_vector_memories)} vector memories → {len(merged)} total"
            )

        return merged

    def _filter_high_quality_kg_facts(
        self,
        kg_facts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        过滤高质量 KG facts

        质量标准:
        1. 谓词不在 low_quality_predicates 中
        2. 对象不能太短或太泛化（除非在 important_keywords 中）

        Args:
            kg_facts: KG facts 列表

        Returns:
            高质量 KG facts
        """
        high_quality_facts = []

        for kg_fact in kg_facts:
            triple = kg_fact.get('kg_triple', {})
            predicate = triple.get('predicate', '').lower()
            obj = triple.get('object', '')

            # 检查1: 谓词质量
            if predicate in self.config.low_quality_predicates:
                if self.config.log_quality_filtering:
                    logger.debug(f"❌ Filtered low-quality predicate: '{predicate}'")
                continue

            # 检查2: 对象长度/质量
            obj_lower = obj.lower()
            obj_word_count = len(obj.split())

            # 如果对象太短，检查是否在重要关键词中
            if obj_word_count < self.config.min_object_word_count:
                if obj_lower not in self.config.important_keywords:
                    if self.config.log_quality_filtering:
                        logger.debug(
                            f"❌ Filtered short object: '{obj}' "
                            f"(word_count={obj_word_count}, not in important_keywords)"
                        )
                    continue
                else:
                    if self.config.log_quality_filtering:
                        logger.debug(f"✅ Short object '{obj}' is in important_keywords, keeping")

            high_quality_facts.append(kg_fact)

        if self.config.log_quality_filtering:
            logger.info(
                f"Quality filtering: {len(kg_facts)} KG facts → {len(high_quality_facts)} high-quality"
            )

        return high_quality_facts

    def _extract_kg_phrases(
        self,
        kg_facts: List[Dict[str, Any]]
    ) -> set:
        """
        从 KG facts 提取关键短语

        Args:
            kg_facts: KG facts 列表

        Returns:
            关键短语集合
        """
        phrases = set()

        for kg_fact in kg_facts:
            triple = kg_fact.get('kg_triple', {})
            subject = triple.get('subject', '').lower()
            obj = triple.get('object', '').lower()

            # 只添加长度足够的短语
            if len(subject) >= self.config.min_phrase_length:
                phrases.add(subject)
            if len(obj) >= self.config.min_phrase_length:
                phrases.add(obj)

        return phrases

    def _filter_overlapping_memories(
        self,
        vector_memories: List[Dict[str, Any]],
        kg_phrases: set
    ) -> List[Dict[str, Any]]:
        """
        过滤与 KG 重叠的 vector memories

        Args:
            vector_memories: Vector 记忆列表
            kg_phrases: KG 短语集合

        Returns:
            过滤后的 vector memories
        """
        if self.config.preserve_vector_memories:
            # 保守策略：只过滤高重叠的
            threshold = self.config.overlap_threshold
        else:
            # 激进策略：过滤中等重叠的
            threshold = self.config.overlap_threshold - 0.1

        filtered_memories = []

        for mem in vector_memories:
            mem_content = mem.get('content', '').lower()

            # 跳过空内容
            if not mem_content:
                continue

            # 检查是否与 KG 短语高度重叠
            has_high_overlap = self._check_overlap(mem_content, kg_phrases, threshold)

            # 保留低重叠的记忆
            if not has_high_overlap:
                filtered_memories.append(mem)
            elif self.config.log_deduplication:
                logger.debug(f"Skipped high-overlap memory: {mem.get('id', 'unknown')}")

        if self.config.log_deduplication:
            logger.info(
                f"Deduplication: {len(vector_memories)} vector memories → "
                f"{len(filtered_memories)} after overlap filtering"
            )

        return filtered_memories

    def _check_overlap(
        self,
        content: str,
        kg_phrases: set,
        threshold: float
    ) -> bool:
        """
        检查内容是否与 KG 短语高度重叠

        Args:
            content: 记忆内容
            kg_phrases: KG 短语集合
            threshold: 重叠阈值

        Returns:
            True 如果高度重叠
        """
        content_words = set(content.split())

        for phrase in kg_phrases:
            if len(phrase) < self.config.min_phrase_length:
                continue

            # 检查短语是否完整包含在内容中
            if phrase in content:
                phrase_words = set(phrase.split())
                overlap_ratio = len(phrase_words & content_words) / max(len(content_words), 1)

                if overlap_ratio > threshold:
                    return True

        return False


# ============================================================================
# Standalone Function (保持与原接口一致)
# ============================================================================

async def merge_kg_and_vector_results(
    vector_memories: List[Dict[str, Any]],
    kg_facts: List[Dict[str, Any]],
    config: KGMergeConfig = None
) -> List[Dict[str, Any]]:
    """
    融合 KG facts 与 vector memories（独立函数版本）

    这个函数可以直接替换 brain_coordinator.py 中的原实现

    Args:
        vector_memories: Vector 检索的记忆列表
        kg_facts: KG 提取的事实列表
        config: KG 融合配置（None 则使用全局配置）

    Returns:
        融合后的记忆列表
    """
    merger = KGMerger(config)
    return await merger.merge_kg_and_vector_results(vector_memories, kg_facts)


# ============================================================================
# Plasticity Ranking (额外功能)
# ============================================================================

def apply_plasticity_ranking(
    memories: List[Dict[str, Any]],
    config: KGMergeConfig = None
) -> List[Dict[str, Any]]:
    """
    应用 plasticity ranking

    根据配置的 top_k 和 threshold 过滤/排序记忆

    Args:
        memories: 记忆列表
        config: KG 融合配置（None 则使用全局配置）

    Returns:
        排序/过滤后的记忆列表
    """
    if config is None:
        config = get_kg_merge_config()

    if not config.plasticity_top_k_enabled:
        return memories

    # Step 1: 按 plasticity_score 排序
    ranked = sorted(
        memories,
        key=lambda x: x.get('plasticity_score', 0.0),
        reverse=True
    )

    # Step 2: 应用 threshold 过滤
    if config.plasticity_score_threshold is not None:
        ranked = [
            mem for mem in ranked
            if mem.get('plasticity_score', 0.0) >= config.plasticity_score_threshold
        ]

    # Step 3: 应用 top-k 限制
    if config.plasticity_top_k is not None:
        ranked = ranked[:config.plasticity_top_k]

    return ranked


def create_kg_fact_memory(
    triple: Dict[str, Any],
    config: KGMergeConfig = None
) -> Dict[str, Any]:
    """
    从 KG triple 创建记忆对象

    使用配置化的 score 和 plasticity_score

    Args:
        triple: KG triple 字典 {'subject', 'predicate', 'object'}
        config: KG 融合配置（None 则使用全局配置）

    Returns:
        记忆对象
    """
    if config is None:
        config = get_kg_merge_config()

    subject = triple.get('subject', '')
    predicate = triple.get('predicate', '')
    obj = triple.get('object', '')

    # 格式化内容
    content = f"{subject} {predicate} {obj}".strip()

    # 生成 ID
    import hashlib
    triple_id = hashlib.md5(content.encode()).hexdigest()[:8]

    return {
        'id': f'kg_fact_{triple_id}',
        'content': content,
        'kg_triple': triple,
        'score': config.kg_fact_default_score,
        'plasticity_score': config.kg_fact_plasticity_score,
        'source': 'knowledge_graph',
        'timestamp': datetime.now().isoformat(),
        'kg_enhanced': True,
        'metadata': {
            'kg_source': 'knowledge_graph',
            'triple': triple,
            'created_at': datetime.now().isoformat()
        }
    }


# ============================================================================
# Integration Helper (集成辅助函数)
# ============================================================================

def get_merge_statistics(
    original_vector_count: int,
    original_kg_count: int,
    merged_count: int,
    high_quality_kg_count: int
) -> Dict[str, Any]:
    """
    获取融合统计信息

    Args:
        original_vector_count: 原始 vector memories 数量
        original_kg_count: 原始 KG facts 数量
        merged_count: 融合后总数量
        high_quality_kg_count: 高质量 KG facts 数量

    Returns:
        统计信息字典
    """
    return {
        'original_vector_count': original_vector_count,
        'original_kg_count': original_kg_count,
        'high_quality_kg_count': high_quality_kg_count,
        'merged_count': merged_count,
        'kg_quality_rate': high_quality_kg_count / original_kg_count if original_kg_count > 0 else 0,
        'deduplication_rate': (original_vector_count + high_quality_kg_count - merged_count) / (original_vector_count + high_quality_kg_count) if (original_vector_count + high_quality_kg_count) > 0 else 0,
        'kg_contribution': high_quality_kg_count / merged_count if merged_count > 0 else 0
    }


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    import asyncio

    async def test_merge():
        """测试融合功能"""

        # 模拟 vector memories
        vector_memories = [
            {
                'id': 'vec1',
                'content': 'Alice visited Sweden last summer for vacation',
                'score': 0.8,
                'plasticity_score': 0.8
            },
            {
                'id': 'vec2',
                'content': 'Bob likes camping in the mountains',
                'score': 0.7,
                'plasticity_score': 0.7
            },
            {
                'id': 'vec3',
                'content': 'Charlie is a person who works at university',
                'score': 0.6,
                'plasticity_score': 0.6
            }
        ]

        # 模拟 KG facts
        kg_facts = [
            create_kg_fact_memory({'subject': 'Alice', 'predicate': 'visited', 'object': 'Sweden'}),
            create_kg_fact_memory({'subject': 'Bob', 'predicate': 'likes', 'object': 'camping'}),
            create_kg_fact_memory({'subject': 'Charlie', 'predicate': 'is_a', 'object': 'person'})  # 低质量
        ]

        # 使用默认配置融合
        merged = await merge_kg_and_vector_results(vector_memories, kg_facts)

        for i, mem in enumerate(merged):
            pass

        # 使用保守配置融合
        from .kg_merge_config import get_conservative_config
        conservative_merged = await merge_kg_and_vector_results(
            vector_memories, kg_facts,
            config=get_conservative_config()
        )

        for i, mem in enumerate(conservative_merged):
            pass

        # 测试 plasticity ranking
        ranked = apply_plasticity_ranking(merged)
        for i, mem in enumerate(ranked):
            pass

    asyncio.run(test_merge())

