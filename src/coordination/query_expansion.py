"""
Query Expansion Module - 查询扩展模块

实现真正的HRM迭代：每次迭代生成不同的检索线索

核心思想（模拟人脑联想）：
1. 第一次检索：原始query
2. 后续迭代：基于已检索内容提取新线索
3. 多维度检索：实体、时间、关系、上下文

Example:
  Query: "When did PersonA paint a sunrise?"
  Iter 1: "When did PersonA paint a sunrise?" (原始)
  Iter 2: "PersonA painting art" (从记忆中提取的实体)
  Iter 3: "lake sunrise last year" (从记忆中提取的关键词)
  Iter 4: "PersonA 2022 artwork" (时间线索)
"""

import logging
import re
from typing import List, Dict, Any, Set, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class QueryExpansionState:
    """跟踪查询扩展状态"""
    original_query: str
    iteration: int = 0
    extracted_entities: Set[str] = field(default_factory=set)
    extracted_keywords: Set[str] = field(default_factory=set)
    extracted_times: Set[str] = field(default_factory=set)
    used_queries: List[str] = field(default_factory=list)
    retrieved_memory_ids: Set[str] = field(default_factory=set)


class QueryExpander:
    """
    查询扩展器 - 让HRM迭代真正有意义

    策略：
    1. 实体扩展：从记忆中提取人名、地点、事物
    2. 关键词扩展：提取动词、名词短语
    3. 时间扩展：提取时间表达
    4. 关系扩展：基于KG三元组生成query
    """

    # 停用词（不作为扩展关键词）
    STOP_WORDS = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'can', 'to', 'of', 'in',
        'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through',
        'during', 'before', 'after', 'above', 'below', 'between',
        'and', 'or', 'but', 'if', 'because', 'when', 'where', 'what',
        'who', 'which', 'that', 'this', 'these', 'those', 'it', 'its',
        'i', 'you', 'he', 'she', 'we', 'they', 'my', 'your', 'his', 'her',
        'user', 'assistant', 'said', 'says', 'told', 'asked'
    }

    # 时间模式
    TIME_PATTERNS = [
        r'\b\d{4}\b',  # 年份 2022
        r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s*\d{0,4}\b',
        r'\b(?:last|next|this)\s+(?:year|month|week|day)\b',
        r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:january|february|march|april|may|june|july|august|september|october|november|december)\b',
    ]

    def __init__(self):
        self.state: Optional[QueryExpansionState] = None

    def start_new_query(self, query: str) -> QueryExpansionState:
        """开始新的查询扩展会话"""
        self.state = QueryExpansionState(original_query=query)
        self.state.used_queries.append(query)

        # 从原始query中提取初始实体和关键词
        self._extract_from_text(query)

        logger.info(f"🔍 QueryExpander: Started new session for '{query[:50]}...'")
        return self.state

    def get_query_for_iteration(
        self,
        iteration: int,
        memories: List[Dict[str, Any]] = None,
        kg_facts: List[Dict[str, Any]] = None
    ) -> str:
        """
        为当前迭代生成查询

        Args:
            iteration: 当前迭代次数 (1-based)
            memories: 上一次迭代检索到的记忆
            kg_facts: KG中的相关事实

        Returns:
            扩展后的查询字符串
        """
        if not self.state:
            raise ValueError("Must call start_new_query first")

        self.state.iteration = iteration

        # 第一次迭代：使用原始query
        if iteration == 1:
            return self.state.original_query

        # 从记忆中提取新线索
        if memories:
            self._extract_from_memories(memories)

        # 从KG中提取线索
        if kg_facts:
            self._extract_from_kg(kg_facts)

        # 生成扩展query
        expanded_query = self._generate_expanded_query(iteration)

        # 记录使用过的query
        if expanded_query not in self.state.used_queries:
            self.state.used_queries.append(expanded_query)

        logger.info(f"🔍 QueryExpander Iter {iteration}: '{expanded_query[:60]}...'")
        return expanded_query

    def _extract_from_text(self, text: str):
        """从文本中提取实体和关键词"""
        # 清理文本
        text_lower = text.lower()

        # 提取时间表达
        for pattern in self.TIME_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            self.state.extracted_times.update(matches)

        # 提取潜在实体（首字母大写的词）
        words = re.findall(r'\b[A-Z][a-z]+\b', text)
        for word in words:
            if word.lower() not in self.STOP_WORDS:
                self.state.extracted_entities.add(word)

        # 提取关键词（去除停用词）
        words = re.findall(r'\b\w+\b', text_lower)
        for word in words:
            if word not in self.STOP_WORDS and len(word) > 2:
                self.state.extracted_keywords.add(word)

    def _extract_from_memories(self, memories: List[Dict[str, Any]]):
        """从检索到的记忆中提取新线索"""
        for mem in memories:
            content = mem.get('content', '') or mem.get('text', '')
            if not content:
                continue

            # 记录已检索的memory ID
            mem_id = mem.get('id', mem.get('memory_id', ''))
            if mem_id:
                self.state.retrieved_memory_ids.add(mem_id)

            # 提取新线索
            self._extract_from_text(content)

    def _extract_from_kg(self, kg_facts: List[Dict[str, Any]]):
        """从KG事实中提取线索"""
        for fact in kg_facts:
            subject = fact.get('subject', '')
            predicate = fact.get('predicate', '')
            obj = fact.get('object', '')

            if subject:
                self.state.extracted_entities.add(subject)
            if obj and len(obj) > 2:
                # object可能是实体或值
                if obj[0].isupper():
                    self.state.extracted_entities.add(obj)
                else:
                    self.state.extracted_keywords.add(obj.lower())

    def _generate_expanded_query(self, iteration: int) -> str:
        """
        根据迭代次数生成不同策略的扩展query

        策略：
        - Iter 2: 实体聚焦 (人名 + 原始query关键词)
        - Iter 3: 时间聚焦 (时间表达 + 实体)
        - Iter 4: 关键词组合 (从记忆中提取的关键词)
        - Iter 5: 宽泛搜索 (移除限定词)
        """
        original = self.state.original_query
        entities = list(self.state.extracted_entities)[:5]
        keywords = list(self.state.extracted_keywords)[:10]
        times = list(self.state.extracted_times)[:3]

        if iteration == 2:
            # 实体聚焦：使用提取的实体
            if entities:
                # 保留原始query中的动词/动作词
                action_words = self._extract_action_words(original)
                query = ' '.join(entities[:3] + action_words[:2])
                return query if query.strip() else original
            return original

        elif iteration == 3:
            # 时间聚焦：如果有时间信息
            if times and entities:
                query = ' '.join([entities[0]] + times[:2])
                return query
            # 没有时间信息，尝试关键词组合
            if keywords and entities:
                return ' '.join(entities[:2] + keywords[:3])
            return original

        elif iteration == 4:
            # 关键词组合：使用从记忆中提取的关键词
            if keywords:
                # 选择与原始query不同的关键词
                original_words = set(original.lower().split())
                new_keywords = [k for k in keywords if k not in original_words][:5]
                if new_keywords and entities:
                    return ' '.join(entities[:2] + new_keywords[:3])
            return original

        elif iteration >= 5:
            # 宽泛搜索：简化query，去除限定词
            simplified = self._simplify_query(original)
            if simplified != original:
                return simplified
            # 如果无法简化，使用不同实体组合
            if len(entities) > 2:
                return ' '.join(entities[1:4])  # 使用不同的实体子集
            return original

        return original

    def _extract_action_words(self, text: str) -> List[str]:
        """提取动作词（动词）"""
        # 简单的动词模式
        action_patterns = [
            r'\b(paint|painted|painting)\b',
            r'\b(go|went|going)\b',
            r'\b(meet|met|meeting)\b',
            r'\b(run|ran|running)\b',
            r'\b(read|reading)\b',
            r'\b(write|wrote|writing)\b',
            r'\b(visit|visited|visiting)\b',
            r'\b(attend|attended|attending)\b',
        ]

        actions = []
        text_lower = text.lower()
        for pattern in action_patterns:
            matches = re.findall(pattern, text_lower)
            actions.extend(matches)

        return list(set(actions))

    def _simplify_query(self, query: str) -> str:
        """简化query，去除限定词"""
        # 移除疑问词
        simplified = re.sub(r'^(when|where|what|who|why|how|did|does|do|is|are|was|were)\s+', '', query, flags=re.IGNORECASE)
        # 移除冠词
        simplified = re.sub(r'\b(the|a|an)\b', '', simplified, flags=re.IGNORECASE)
        # 清理多余空格
        simplified = ' '.join(simplified.split())
        return simplified.strip() or query

    def get_retrieval_config_for_iteration(self, iteration: int) -> Dict[str, Any]:
        """
        为每次迭代返回不同的检索配置

        Args:
            iteration: 当前迭代次数

        Returns:
            检索配置 {k, threshold, strategy}
        """
        configs = {
            1: {'k': 30, 'threshold': 0.3, 'strategy': 'semantic'},
            2: {'k': 25, 'threshold': 0.25, 'strategy': 'entity_focused'},
            3: {'k': 20, 'threshold': 0.2, 'strategy': 'temporal'},
            4: {'k': 25, 'threshold': 0.2, 'strategy': 'keyword'},
            5: {'k': 30, 'threshold': 0.15, 'strategy': 'broad'},
        }
        return configs.get(iteration, configs[5])

    def should_continue_expansion(self) -> bool:
        """判断是否应该继续扩展"""
        if not self.state:
            return False

        # 如果提取到了足够多的线索，可以继续
        total_cues = (
            len(self.state.extracted_entities) +
            len(self.state.extracted_keywords) +
            len(self.state.extracted_times)
        )

        return total_cues > 3  # 至少有3个线索才继续扩展

    def get_expansion_summary(self) -> Dict[str, Any]:
        """获取扩展摘要"""
        if not self.state:
            return {}

        return {
            'original_query': self.state.original_query,
            'iterations': self.state.iteration,
            'entities_found': list(self.state.extracted_entities),
            'keywords_found': list(self.state.extracted_keywords)[:10],
            'times_found': list(self.state.extracted_times),
            'queries_used': self.state.used_queries,
            'memories_retrieved': len(self.state.retrieved_memory_ids)
        }


    def rerank_memories_by_original_query(
        self,
        memories: List[Dict[str, Any]],
        top_k: int = 30
    ) -> List[Dict[str, Any]]:
        """
        🔥 Re-rank accumulated memories by relevance to ORIGINAL query

        Problem: Query Expansion brings in many memories from expanded queries,
        but some are noise (e.g., asking about "sunrise painting" but expanded
        queries bring in all of Person's activities).

        Solution: Score each memory against the ORIGINAL query and keep top-k.

        Args:
            memories: All accumulated memories from HRM iterations
            top_k: Number of memories to return (default 30)

        Returns:
            Top-k most relevant memories to original query
        """
        if not self.state or not memories:
            return memories[:top_k]

        original_query = self.state.original_query.lower()
        query_words = set(original_query.split()) - self.STOP_WORDS

        # Score each memory
        scored_memories = []
        for i, mem in enumerate(memories):
            content = (mem.get('content', '') or mem.get('text', '')).lower()
            content_words = set(content.split())

            # Base score: keyword overlap
            overlap = len(query_words & content_words)
            keyword_score = overlap / max(len(query_words), 1)

            # Bonus: early retrieval (first iteration = more relevant)
            # Memories retrieved earlier in the list are from earlier iterations
            position_bonus = max(0, 1.0 - (i / max(len(memories), 1)) * 0.3)

            # Bonus: exact entity match (e.g., "PersonA" in query and memory)
            entity_bonus = 0
            for entity in self.state.extracted_entities:
                if entity.lower() in content:
                    entity_bonus += 0.2

            # Use existing score if available
            existing_score = mem.get('score', 0) or 0

            # Combined score
            total_score = (
                keyword_score * 0.4 +
                existing_score * 0.3 +
                position_bonus * 0.2 +
                entity_bonus * 0.1
            )

            scored_memories.append((total_score, mem))

        # Sort by score (descending) and return top-k
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        top_memories = [mem for _, mem in scored_memories[:top_k]]

        logger.info(f"🔄 Re-ranked {len(memories)} memories → kept top {len(top_memories)} by original query relevance")

        return top_memories


# 全局实例
query_expander = QueryExpander()
