"""
Retrieval Guidance Mixin - 检索指导混入类

功能:
1. 分析查询意图，提供检索策略建议
2. 动态调整脑区激活计划
3. 提供关键实体和时间线索提取

🔧 2025-12-12: 新增，让前额叶参与检索决策
"""

import logging
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class RetrievalGuidanceMixin:
    """
    检索指导混入类

    前额叶分析查询意图，为海马体提供检索指导:
    - 应该激活哪些脑区
    - 应该关注哪些实体
    - 时间范围建议
    """

    async def provide_retrieval_guidance(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        分析查询并提供检索指导

        Args:
            query: 用户查询
            context: 上下文信息 (如历史对话)

        Returns:
            {
                'activation_plan': {'hippocampus': True, ...},
                'key_entities': ['Person1', 'Person2'],
                'temporal_hints': {'type': 'first', 'range': None},
                'search_strategy': 'temporal' | 'semantic' | 'entity' | 'hybrid',
                'priority_regions': ['hippocampus', 'temporal_lobe']
            }
        """
        query_lower = query.lower()

        # 1. 分析查询类型
        query_type = self._analyze_query_type(query_lower)

        # 2. 提取关键实体 (使用 LLM 或简单规则)
        key_entities = await self._extract_key_entities(query)

        # 3. 提取时间线索
        temporal_hints = self._extract_temporal_hints(query_lower)

        # 4. 确定检索策略和脑区激活计划
        activation_plan, strategy, priority_regions = self._determine_strategy(
            query_type, temporal_hints, key_entities
        )

        guidance = {
            'activation_plan': activation_plan,
            'key_entities': key_entities,
            'temporal_hints': temporal_hints,
            'search_strategy': strategy,
            'priority_regions': priority_regions,
            'query_type': query_type
        }

        logger.info(
            f"🧠 Prefrontal guidance: strategy={strategy}, "
            f"priority_regions={priority_regions}, entities={key_entities[:3]}"
        )

        return guidance

    def _analyze_query_type(self, query_lower: str) -> str:
        """分析查询类型"""
        # 时间查询
        if any(word in query_lower for word in ['when', 'what time', 'how long ago', 'first', 'last', 'recent']):
            return 'temporal'

        # 身份查询
        if any(word in query_lower for word in ['who is', 'what is', 'identity', 'what kind of']):
            return 'identity'

        # 关系查询
        if any(word in query_lower for word in ['relationship', 'how does', 'between', 'connection']):
            return 'relational'

        # 事实查询
        if any(word in query_lower for word in ['did', 'does', 'is', 'was', 'has', 'have']):
            return 'factual'

        # 多跳推理
        if query_lower.count('and') > 1 or 'because' in query_lower or 'why' in query_lower:
            return 'multi_hop'

        return 'general'

    async def _extract_key_entities(self, query: str) -> List[str]:
        """
        提取查询中的关键实体

        使用简单规则 + LLM 回退
        """
        entities = []

        # 1. 提取大写开头的词 (人名、地名)
        capitalized = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', query)
        entities.extend(capitalized)

        # 2. 提取引号内的内容
        quoted = re.findall(r'"([^"]+)"', query)
        entities.extend(quoted)

        # 3. 如果实体太少，使用 LLM
        if len(entities) < 2 and hasattr(self, 'call_llm'):
            try:
                prompt = f"""Extract key entities (people, places, events, organizations) from this query:
"{query}"

Return only a comma-separated list of entities, no explanation."""
                response = await self.call_llm(prompt, max_tokens=100, temperature=0)
                if response:
                    llm_entities = [e.strip() for e in response.split(',') if e.strip()]
                    entities.extend(llm_entities)
            except Exception as e:
                logger.debug(f"LLM entity extraction failed: {e}")

        # 去重
        return list(dict.fromkeys(entities))

    def _extract_temporal_hints(self, query_lower: str) -> Dict[str, Any]:
        """提取时间线索"""
        hints = {
            'type': None,  # 'first', 'last', 'range', 'relative'
            'range': None,
            'relative_words': []
        }

        # 顺序指示
        if 'first' in query_lower or 'earliest' in query_lower:
            hints['type'] = 'first'
        elif 'last' in query_lower or 'recent' in query_lower or 'latest' in query_lower:
            hints['type'] = 'last'

        # 相对时间词
        relative_words = ['yesterday', 'last week', 'last month', 'today', 'tomorrow']
        found_relative = [w for w in relative_words if w in query_lower]
        if found_relative:
            hints['type'] = 'relative'
            hints['relative_words'] = found_relative

        # 日期范围 (简单匹配)
        date_pattern = r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\w+\s+\d{4}|\d{4})\b'
        dates = re.findall(date_pattern, query_lower)
        if dates:
            hints['range'] = dates

        return hints

    def _determine_strategy(
        self,
        query_type: str,
        temporal_hints: Dict,
        key_entities: List[str]
    ) -> tuple:
        """
        确定检索策略和脑区激活计划

        Returns:
            (activation_plan, strategy, priority_regions)
        """
        # 默认激活所有脑区
        activation_plan = {
            'hippocampus': True,
            'temporal_lobe': True,
            'prefrontal': True,
            'amygdala': True,
            'basal_ganglia': True
        }

        # 根据查询类型调整策略
        if query_type == 'temporal':
            strategy = 'temporal'
            priority_regions = ['hippocampus']
            # 时间查询需要更多的海马体激活
            activation_plan['hippocampus'] = True
            activation_plan['temporal_lobe'] = True  # 语义补充

        elif query_type == 'identity':
            strategy = 'semantic'
            priority_regions = ['temporal_lobe', 'hippocampus']
            # 身份查询需要语义知识
            activation_plan['temporal_lobe'] = True

        elif query_type == 'relational':
            strategy = 'hybrid'
            priority_regions = ['temporal_lobe', 'prefrontal']
            # 关系查询需要知识图谱
            activation_plan['temporal_lobe'] = True
            activation_plan['prefrontal'] = True

        elif query_type == 'multi_hop':
            strategy = 'hybrid'
            priority_regions = ['hippocampus', 'temporal_lobe', 'prefrontal']
            # 多跳推理需要所有脑区

        else:
            strategy = 'hybrid'
            priority_regions = ['hippocampus', 'temporal_lobe']

        # 如果有明确的实体，增加实体检索权重
        if len(key_entities) > 0:
            strategy = 'entity' if strategy == 'general' else f'{strategy}+entity'

        return activation_plan, strategy, priority_regions
