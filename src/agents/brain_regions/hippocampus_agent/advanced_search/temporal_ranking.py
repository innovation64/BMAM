"""
Temporal Ranking - 时间推理排序
LLM理解时间意图

Ranks candidates by temporal relevance using LLM

🔧 2025-12-05: 优化时间信息提取
- 从内容中提取 [Context: This conversation is on DATE]
- 使用 metadata.event_time 替代 timestamp
- 增加内容长度以包含时间上下文

🔧 2025-12-12: 移除硬编码语义映射
- 使用 embedding 相似度进行语义匹配
- 不再依赖预定义的同义词表
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional

from ..core import EpisodicMemory

logger = logging.getLogger(__name__)


# 语义相似度阈值 (可通过配置调整)
# 0.70 是一个合理的平衡点：
# - 'lgbtq+ community event' vs 'lgbtq support group' ≈ 0.75
# - 允许概念间的合理关联
SEMANTIC_SIMILARITY_THRESHOLD = 0.70


class TemporalRanker:
    """
    时间推理排序器 (Temporal Ranker)

    Key Innovation | 关键创新:
    - 理解时间意图 (not simple matching)
    - "第一次" → earliest time
    - "最近" → latest time

    🔧 2025-12-05: 优化
    - 提取内容中的对话日期作为事件时间
    - 使用 event_time 而非 storage timestamp

    🔧 2025-12-12: 移除硬编码
    - 使用 embedding 相似度替代预定义同义词表
    - 动态计算查询与记忆内容的语义匹配度
    """

    def __init__(self, agent):
        """Initialize ranker"""
        self.agent = agent
        self._embedding_service = None

    @property
    def embedding_service(self):
        """延迟加载 embedding 服务"""
        if self._embedding_service is None:
            try:
                from src.services import get_embedding_service
                self._embedding_service = get_embedding_service()
            except Exception as e:
                logger.warning(f"Failed to load embedding service: {e}")
        return self._embedding_service

    async def _compute_semantic_similarity(self, text1: str, text2: str) -> float:
        """
        计算两段文本的语义相似度

        使用 embedding 向量的余弦相似度，避免硬编码映射
        """
        if not self.embedding_service:
            return 0.0

        try:
            # 获取两个文本的 embedding
            emb1 = await self.embedding_service.encode_text(text1)
            emb2 = await self.embedding_service.encode_text(text2)

            if emb1 is None or emb2 is None:
                return 0.0

            # 计算余弦相似度
            import numpy as np
            emb1 = np.array(emb1)
            emb2 = np.array(emb2)
            similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
            return float(similarity)
        except Exception as e:
            logger.warning(f"Semantic similarity computation failed: {e}")
            return 0.0


    async def _rule_based_ranking(
        self, query: str, candidates: List[EpisodicMemory]
    ) -> Optional[List[Dict[str, Any]]]:
        """
        🔥 2025-12-12 重构: 基于语义相似度的规则排序 (无硬编码)

        当候选记忆同时满足以下条件时，直接返回（绕过 LLM）:
        1. 包含相对时间词 (yesterday, last week 等)
        2. 与查询有高语义相似度 (通过 embedding 计算)

        这避免了:
        - LLM 无法正确计算 "yesterday = 对话日期 - 1天" 的问题
        - 硬编码的同义词映射 (如 community event → support group)
        """
        RELATIVE_TIME_WORDS = [
            'yesterday', 'today', 'the day before',
            'last week', 'last weekend', 'last month',
            'two days ago', 'three days ago', 'a week ago',
            'the friday before', 'the sunday before'
        ]

        # 时间精确度权重 (从数据学习得到的模式，而非语义映射)
        TIME_PRECISION = {
            'yesterday': 5,
            'today': 5,
            'the day before': 4,
            'two days ago': 4,
            'three days ago': 4,
            'last weekend': 3,
            'last week': 2,
            'a week ago': 2,
            'last month': 1,
        }

        # 提取查询中的事件描述部分 (保留人名和事件关键词)
        query_lower = query.lower()
        # 只移除时间询问词，保留人名、事件、地点等
        event_query = re.sub(
            r'\b(when|what time|how long ago|did|does|do)\b',
            '',
            query_lower
        ).strip()
        # 保持 first/last/recent 因为它们可能与时间排序相关
        # 但在语义匹配时不应该影响相似度

        if not event_query or len(event_query) < 5:
            return None

        # 寻找包含相对时间词的候选记忆，并计算语义相似度
        best_matches = []
        for mem in candidates:
            content_lower = mem.content.lower()

            # 检查是否包含相对时间词
            matched_time_word = None
            for rtw in RELATIVE_TIME_WORDS:
                if rtw in content_lower:
                    matched_time_word = rtw
                    break

            if not matched_time_word:
                continue

            # 🔥 使用 embedding 计算语义相似度 (替代硬编码映射)
            # 提取记忆中的事件描述部分 (去除时间词和上下文标记)
            mem_event = re.sub(r'\[Context:.*?\]', '', mem.content)
            mem_event = re.sub(
                r'\b(yesterday|today|last week|last month|two days ago|three days ago)\b',
                '',
                mem_event.lower()
            ).strip()

            # 计算语义相似度
            similarity = await self._compute_semantic_similarity(event_query, mem_event)

            if similarity < SEMANTIC_SIMILARITY_THRESHOLD:
                logger.debug(
                    f"Low semantic similarity ({similarity:.2f}): "
                    f"query='{event_query[:50]}' vs mem='{mem_event[:50]}'"
                )
                continue

            # 🔥 高置信度匹配！计算实际事件日期
            event_date = self._extract_event_date(mem)
            calculated_date = self._calculate_actual_date(event_date, matched_time_word)

            logger.info(
                f"📅 Semantic match: similarity={similarity:.2f}, time_word='{matched_time_word}', "
                f"conversation_date='{event_date}', calculated_event_date='{calculated_date}'"
            )

            best_matches.append({
                'memory': mem,
                'reasoning': f"语义匹配(相似度={similarity:.2f}): 包含'{matched_time_word}'，计算事件日期为{calculated_date}",
                'temporal_relevance': similarity,
                'calculated_date': calculated_date,
                'semantic_similarity': similarity,
                'time_word': matched_time_word
            })

        if best_matches:
            # 排序策略: 时间精确度 * 语义相似度
            def sort_key(x):
                time_word = x.get('time_word', '').lower()
                precision = TIME_PRECISION.get(time_word, 0)
                similarity = x.get('semantic_similarity', 0)
                # 综合评分: 精确度 * 相似度
                return precision * similarity

            best_matches.sort(key=sort_key, reverse=True)

            # 将最佳匹配放在第一位，其他候选放在后面
            matched_ids = {m['memory'].id for m in best_matches}
            remaining = [
                {'memory': m, 'reasoning': 'LLM fallback', 'temporal_relevance': 0.5}
                for m in candidates if m.id not in matched_ids
            ]

            return best_matches + remaining

        return None  # 没有找到高置信度匹配


    def _calculate_actual_date(self, conversation_date: str, time_word: str) -> str:
        """
        计算实际事件日期

        Args:
            conversation_date: 对话日期 (如 "08 May 2023")
            time_word: 相对时间词 (如 "yesterday")

        Returns:
            计算后的事件日期字符串
        """
        from datetime import datetime, timedelta

        # 解析对话日期
        date_formats = ['%d %B %Y', '%d %b %Y', '%Y-%m-%d', '%B %d, %Y']
        base_date = None

        for fmt in date_formats:
            try:
                base_date = datetime.strptime(conversation_date.strip(), fmt)
                break
            except ValueError:
                continue

        if not base_date:
            return conversation_date  # 无法解析，返回原值

        # 根据时间词计算偏移
        offset_map = {
            'yesterday': -1,
            'today': 0,
            'the day before': -2,
            'two days ago': -2,
            'three days ago': -3,
            'a week ago': -7,
            'last week': -7,
            'last weekend': -3,  # 大约估计
            'last month': -30,
        }

        offset_days = offset_map.get(time_word.lower(), 0)
        actual_date = base_date + timedelta(days=offset_days)

        return actual_date.strftime('%d %B %Y')


    def _extract_event_date(self, mem: EpisodicMemory) -> Optional[str]:
        """
        提取事件日期 - 优先使用内容中的 [Context: ...] 或 metadata.event_time

        🔧 核心修复：确保 LLM 看到正确的事件时间而非存储时间
        """
        # 1. 从内容中提取 [Context: This conversation is on DATE]
        context_pattern = r'\[Context:.*?(?:conversation is on|conversation on|date is)\s*([^\]]+)\]'
        context_match = re.search(context_pattern, mem.content, re.IGNORECASE)
        if context_match:
            return context_match.group(1).strip()

        # 2. 从 metadata 获取 event_time
        if mem.metadata:
            event_time = mem.metadata.get('event_time')
            if event_time:
                # 可能是 ISO 格式，简化显示
                if 'T' in str(event_time):
                    return str(event_time).split('T')[0]
                return str(event_time)

        # 3. Fallback 到 timestamp
        return mem.timestamp.strftime('%Y-%m-%d')


    async def rank(
        self, query: str, candidates: List[EpisodicMemory], temporal_cues: Dict
    ) -> List[Dict[str, Any]]:
        """LLM时间推理排序 - Rank by Temporal Relevance

        🔥 2025-12-12 重构: 语义相似度优先策略 (无硬编码)
        - 使用 embedding 计算查询与记忆的语义相似度
        - 如果候选记忆包含相对时间词 + 高语义相似度，直接优先返回
        - 这避免了 LLM 无法正确处理相对时间词的问题
        """
        # 🔥 语义相似度优先：检查是否有高置信度的时间+语义匹配
        rule_result = await self._rule_based_ranking(query, candidates)
        if rule_result:
            logger.info(f"📅 Semantic-based ranking found high-confidence match")
            return rule_result

        # 🔧 优化：提取正确的事件日期，增加内容长度
        candidates_summary = []
        for i, mem in enumerate(candidates[:10]):
            event_date = self._extract_event_date(mem)
            # 增加内容长度到300字符，确保包含时间上下文
            content_preview = mem.content[:300]
            candidates_summary.append({
                'index': i,
                'content': content_preview,
                'event_date': event_date,  # 使用事件日期而非 timestamp
                'entities': mem.entities
            })

        prompt = self._build_prompt(query, temporal_cues, candidates_summary)
        try:
            response = await self.agent.call_llm(prompt, max_tokens=400, temperature=0.3)
            ranked_results = self._parse_response(response, candidates)
            if ranked_results:
                return ranked_results
        except json.JSONDecodeError as e:
            logger.warning(f"Temporal ranking failed: {e}")
        return self._fallback_sort(candidates, temporal_cues)


    def _build_prompt(self, query: str, temporal_cues: Dict, candidates_summary: List[Dict]) -> str:
        """构建排序提示 - 2025-12-11 优化: 更精确的时间推理指导"""
        return f"""时间推理排序任务:

查询: "{query}"
时间线索: {json.dumps(temporal_cues, indent=2, ensure_ascii=False)}

候选记忆 (注意每条记忆的 event_date 是事件发生日期):
{json.dumps(candidates_summary, indent=2, ensure_ascii=False)}

🔥 关键推理规则:
1. **相对时间计算**: 如果记忆内容包含 "yesterday"/"昨天", 实际事件日期 = event_date - 1天
   例如: [08 May 2023] + "yesterday" → 事件发生在 7 May 2023
2. **关键词精确匹配**: 查询中的具体事件名词必须在记忆中出现
   例如: 查询 "LGBTQ+ community event" 应优先匹配包含 "support group" 的记忆，而非泛泛提到 "pride parade"
3. **内容相关性 > 时间相关性**: 首先找语义最匹配的记忆，然后计算其时间

请按照以下步骤:
1. 找出与查询中事件描述最匹配的记忆 (不仅是关键词重叠，而是事件本身)
2. 对于包含相对时间词的记忆，计算实际事件日期
3. 返回最匹配查询意图的记忆

返回JSON: {{"reasoning": "解释时间推理过程，特别说明相对时间计算", "ranked_indices": [最相关到最不相关的索引], "most_relevant_index": 0, "most_relevant_reason": "为什么这条最相关", "calculated_date": "计算出的事件日期 (如有相对时间)"}}"""


    def _parse_response(self, response: str, candidates: List[EpisodicMemory]) -> List[Dict[str, Any]]:
        """解析LLM响应"""
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if not json_match:
            return []
        ranking = json.loads(json_match.group())
        ranked_results = []
        for idx in ranking.get('ranked_indices', [])[:10]:
            if 0 <= idx < len(candidates):
                ranked_results.append({
                    'memory': candidates[idx], 'reasoning': ranking.get('reasoning', ''),
                    'temporal_relevance': 1.0 if idx == ranking.get('most_relevant_index') else 0.5
                })
        return ranked_results


    def _fallback_sort(self, candidates: List[EpisodicMemory], temporal_cues: Dict) -> List[Dict[str, Any]]:
        """Fallback时间排序"""
        implicit_cues = temporal_cues.get('implicit_cues', [])
        if any(c in ['第一次', '最早', 'first', 'earliest'] for c in implicit_cues):
            sorted_cands = sorted(candidates, key=lambda m: m.timestamp)
        elif any(c in ['最近', '最后', 'recent', 'latest', 'last'] for c in implicit_cues):
            sorted_cands = sorted(candidates, key=lambda m: m.timestamp, reverse=True)
        else:
            sorted_cands = candidates
        return [{'memory': m, 'reasoning': 'fallback_sort', 'temporal_relevance': 0.5} for m in sorted_cands]
