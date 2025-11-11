"""
Multi-Round Retrieval System - 多轮检索调度
Phase 3A Enhancement: Team C

理论依据:
- Iterative Retrieval and Reasoning (IRR)
- Query Refinement and Re-ranking
- Gap Detection and补充检索

系统流程:
1. 初始检索 → 2. 缺口检测 → 3. 再检索 → 4. 结果合并
"""

import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class GapDetector:
    """
    缺口检测器 - 识别检索结果中的信息缺口

    检测维度:
    1. 时间信息缺失（问 When，但没有时间信息）
    2. 实体信息缺失（问 Who，但没有人名）
    3. 地点信息缺失（问 Where，但没有地点）
    4. 多跳推理缺失（需要中间步骤）
    """

    def __init__(self):
        self.temporal_keywords = [
            'when', 'what time', 'what date', 'which year', 'which month',
            'how long ago', 'how recently'
        ]

        self.entity_keywords = [
            'who', 'whose', 'which person', 'what is.*name'
        ]

        self.location_keywords = [
            'where', 'which place', 'which location', 'which city', 'which country'
        ]

        self.reason_keywords = [
            'why', 'how', 'what caused', 'what led to', 'what motivated'
        ]

    def detect_gaps(
        self,
        query: str,
        retrieved_memories: List[Dict[str, Any]],
        reasoning_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        检测信息缺口

        Args:
            query: 用户查询
            retrieved_memories: 检索到的记忆
            reasoning_result: 推理结果（可选）

        Returns:
            {
                'has_gaps': bool,
                'gap_types': List[str],  # ['temporal', 'entity', 'location', 'multi_hop']
                'missing_info': List[str],  # 缺失的具体信息
                'confidence': float,  # 0-1, 缺口检测的置信度
                'suggested_queries': List[str]  # 建议的补充查询
            }
        """
        query_lower = query.lower()
        gaps = {
            'has_gaps': False,
            'gap_types': [],
            'missing_info': [],
            'confidence': 1.0,
            'suggested_queries': []
        }

        # 1. 检测时间信息缺口
        is_temporal_query = any(kw in query_lower for kw in self.temporal_keywords)
        if is_temporal_query:
            has_temporal_info = self._check_temporal_info(retrieved_memories)
            if not has_temporal_info:
                gaps['has_gaps'] = True
                gaps['gap_types'].append('temporal')
                gaps['missing_info'].append('时间信息缺失')
                gaps['suggested_queries'].append(self._generate_temporal_query(query))

        # 2. 检测实体信息缺口
        is_entity_query = any(re.search(kw, query_lower) for kw in self.entity_keywords)
        if is_entity_query:
            has_entity_info = self._check_entity_info(retrieved_memories, query)
            if not has_entity_info:
                gaps['has_gaps'] = True
                gaps['gap_types'].append('entity')
                gaps['missing_info'].append('实体信息缺失')
                gaps['suggested_queries'].append(self._generate_entity_query(query))

        # 3. 检测地点信息缺口
        is_location_query = any(kw in query_lower for kw in self.location_keywords)
        if is_location_query:
            has_location_info = self._check_location_info(retrieved_memories)
            if not has_location_info:
                gaps['has_gaps'] = True
                gaps['gap_types'].append('location')
                gaps['missing_info'].append('地点信息缺失')
                gaps['suggested_queries'].append(self._generate_location_query(query))

        # 4. 检测多跳推理缺口
        if reasoning_result:
            needs_multi_hop = self._check_multi_hop_need(query, retrieved_memories, reasoning_result)
            if needs_multi_hop:
                gaps['has_gaps'] = True
                gaps['gap_types'].append('multi_hop')
                gaps['missing_info'].append('需要中间推理步骤')
                gaps['suggested_queries'].extend(self._generate_multi_hop_queries(query, reasoning_result))

        # 5. 检测结果置信度低
        if len(retrieved_memories) < 3:
            gaps['has_gaps'] = True
            gaps['gap_types'].append('low_confidence')
            gaps['missing_info'].append(f'检索结果过少 ({len(retrieved_memories)}条)')
            gaps['confidence'] = 0.5

        # 6. 检测结果相关性低
        if retrieved_memories:
            avg_score = sum(m.get('score', 0) for m in retrieved_memories) / len(retrieved_memories)
            if avg_score < 0.6:
                gaps['has_gaps'] = True
                gaps['gap_types'].append('low_relevance')
                gaps['missing_info'].append(f'检索结果相关性低 (平均: {avg_score:.2f})')
                gaps['confidence'] = avg_score

        # 计算总体置信度
        if gaps['has_gaps']:
            gaps['confidence'] = max(0.3, gaps['confidence'] - 0.1 * len(gaps['gap_types']))

        return gaps

    def _check_temporal_info(self, memories: List[Dict[str, Any]]) -> bool:
        """检查是否包含时间信息"""
        temporal_patterns = [
            r'\d{4}',  # 年份
            r'\d{1,2}\s*(january|february|march|april|may|june|july|august|september|october|november|december)',
            r'(yesterday|today|tomorrow|last week|next week|last month|next month|last year|next year)',
            r'\d{1,2}/\d{1,2}/\d{2,4}',  # 日期格式
        ]

        for memory in memories:
            content = memory.get('content', '').lower()
            metadata = memory.get('metadata', {})

            # 检查内容中的时间表达
            for pattern in temporal_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return True

            # 检查元数据中的时间字段
            if metadata.get('timestamp') or metadata.get('session_date') or metadata.get('year'):
                return True

        return False

    def _check_entity_info(self, memories: List[Dict[str, Any]], query: str) -> bool:
        """检查是否包含实体信息（人名、组织等）"""
        # 提取查询中提到的实体
        # 检查记忆中是否包含这些实体或相关实体

        for memory in memories:
            content = memory.get('content', '')

            # 简单检查：是否包含大写开头的词（可能是人名）
            has_capitalized = bool(re.search(r'\b[A-Z][a-z]+\b', content))
            if has_capitalized:
                return True

        return False

    def _check_location_info(self, memories: List[Dict[str, Any]]) -> bool:
        """检查是否包含地点信息"""
        location_indicators = [
            r'\b(in|at|to|from)\s+[A-Z][a-z]+',  # "in Sweden", "at Google"
            r'\b(city|country|place|location|office|building|park)\b',
        ]

        for memory in memories:
            content = memory.get('content', '').lower()

            for pattern in location_indicators:
                if re.search(pattern, content, re.IGNORECASE):
                    return True

        return False

    def _check_multi_hop_need(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        reasoning_result: Dict[str, Any]
    ) -> bool:
        """检查是否需要多跳推理"""

        # 检查推理结果中是否有不确定的答案
        answer = reasoning_result.get('answer', '')
        confidence = reasoning_result.get('confidence', 1.0)

        if confidence < 0.7:
            return True

        # 检查是否包含 "不确定"、"可能"、"也许" 等词
        uncertain_indicators = ['不确定', '不清楚', '可能', '也许', 'maybe', 'perhaps', 'uncertain']
        if any(ind in answer.lower() for ind in uncertain_indicators):
            return True

        # 检查查询复杂度（是否包含 "and"、"then"、"after" 等连接词）
        complex_indicators = [' and ', ' then ', ' after ', ' before ', ' because ']
        if any(ind in query.lower() for ind in complex_indicators):
            return True

        return False

    def _generate_temporal_query(self, original_query: str) -> str:
        """生成补充的时间查询"""
        # 提取查询主体
        # 例如: "When did Caroline go camping?" → "Caroline camping date"
        query_words = original_query.lower().split()

        # 移除时间词
        filtered_words = [w for w in query_words if w not in ['when', 'what', 'time', 'date', 'did', '?']]

        return ' '.join(filtered_words) + ' date time'

    def _generate_entity_query(self, original_query: str) -> str:
        """生成补充的实体查询"""
        query_words = original_query.lower().split()
        filtered_words = [w for w in query_words if w not in ['who', 'whose', 'which', 'person', '?']]
        return ' '.join(filtered_words) + ' person name'

    def _generate_location_query(self, original_query: str) -> str:
        """生成补充的地点查询"""
        query_words = original_query.lower().split()
        filtered_words = [w for w in query_words if w not in ['where', 'which', 'place', 'location', '?']]
        return ' '.join(filtered_words) + ' location place'

    def _generate_multi_hop_queries(
        self,
        original_query: str,
        reasoning_result: Dict[str, Any]
    ) -> List[str]:
        """生成多跳推理的补充查询"""
        # 基于推理结果生成中间步骤查询
        queries = []

        # 如果答案提到某个实体，查询该实体的更多信息
        answer = reasoning_result.get('answer', '')

        # 提取答案中的大写词（可能是实体）
        entities = re.findall(r'\b[A-Z][a-z]+\b', answer)

        for entity in entities[:2]:  # 最多2个
            queries.append(f"{entity} details")

        return queries


class MultiRoundRetrievalScheduler:
    """
    多轮检索调度器

    流程:
    1. 初始检索
    2. 缺口检测
    3. 如果有缺口 → 生成补充查询 → 再检索
    4. 合并结果
    5. 重新推理
    """

    def __init__(self, max_rounds: int = 3):
        """
        Args:
            max_rounds: 最大检索轮数
        """
        self.max_rounds = max_rounds
        self.gap_detector = GapDetector()

    async def retrieve_with_gap_detection(
        self,
        query: str,
        retrieval_func,  # async function(query) -> List[Dict]
        reasoning_func=None,  # async function(query, memories) -> Dict
        **retrieval_kwargs
    ) -> Dict[str, Any]:
        """
        多轮检索主流程

        Args:
            query: 用户查询
            retrieval_func: 检索函数
            reasoning_func: 推理函数（可选）
            retrieval_kwargs: 传递给检索函数的额外参数

        Returns:
            {
                'memories': List[Dict],  # 最终合并的记忆
                'rounds': int,  # 实际检索轮数
                'gaps_detected': List[Dict],  # 每轮检测到的缺口
                'final_gaps': Dict,  # 最终的缺口信息
                'reasoning_result': Dict,  # 推理结果（如果提供了推理函数）
            }
        """

        all_memories = []
        seen_memory_ids = set()
        gaps_history = []

        current_query = query
        round_num = 0

        while round_num < self.max_rounds:
            round_num += 1

            # 1. 执行检索
            memories = await retrieval_func(current_query, **retrieval_kwargs)


            # 2. 去重并合并
            new_memories = []
            for memory in memories:
                memory_id = memory.get('id') or memory.get('content')
                if memory_id not in seen_memory_ids:
                    seen_memory_ids.add(memory_id)
                    new_memories.append(memory)
                    all_memories.append(memory)


            # 3. 执行推理（如果提供了推理函数）
            reasoning_result = None
            if reasoning_func:
                reasoning_result = await reasoning_func(current_query, all_memories)

            # 4. 缺口检测
            gaps = self.gap_detector.detect_gaps(current_query, all_memories, reasoning_result)
            gaps_history.append({
                'round': round_num,
                'query': current_query,
                'gaps': gaps
            })

            if gaps['has_gaps']:
                logger.info(f"Round {round_num}: gaps detected, continuing retrieval")

            # 5. 判断是否需要继续检索
            if not gaps['has_gaps']:
                break

            if round_num >= self.max_rounds:
                break

            # 6. 生成下一轮查询
            if gaps['suggested_queries']:
                current_query = gaps['suggested_queries'][0]  # 使用第一个建议查询
            else:
                break

        # 7. 返回结果
        result = {
            'memories': all_memories,
            'rounds': round_num,
            'gaps_detected': gaps_history,
            'final_gaps': gaps,
            'reasoning_result': reasoning_result
        }


        return result


# 便捷函数
async def retrieve_with_multi_round(
    query: str,
    retrieval_func,
    reasoning_func=None,
    max_rounds: int = 3,
    **retrieval_kwargs
) -> Dict[str, Any]:
    """
    便捷的多轮检索接口

    Args:
        query: 查询
        retrieval_func: async function(query, **kwargs) -> List[Dict]
        reasoning_func: async function(query, memories) -> Dict (可选)
        max_rounds: 最大轮数
        **retrieval_kwargs: 传递给检索函数的参数

    Returns:
        多轮检索结果字典
    """
    scheduler = MultiRoundRetrievalScheduler(max_rounds=max_rounds)
    return await scheduler.retrieve_with_gap_detection(
        query,
        retrieval_func,
        reasoning_func,
        **retrieval_kwargs
    )
