"""
🧠 海马-前额叶循环 - Hippocampal-Prefrontal Loop

核心原理:
1. 海马体 (Hippocampus) - 记忆检索
2. 前额叶 (Prefrontal Cortex) - 分析记忆缺失
3. 迭代循环 - 补充检索直到完整

神经科学基础:
- 海马-前额叶交互: 记忆检索与工作记忆的协同
- 前额叶gap analysis: 识别信息缺失
- 迭代检索: 多轮检索补充信息

解决问题:
- Q2: "What fields would Person pursue?" 只检索到部分记忆,
  缺少相关context → 需要迭代补充

Author: BMAM Team
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MemoryGapAnalysis:
    """记忆缺口分析结果"""
    is_sufficient: bool
    missing_aspects: List[str]
    retrieval_context: Dict[str, Any]
    confidence: float


class HippocampalPrefrontalLoop:
    """
    海马-前额叶循环机制

    核心流程:
    1. 海马体初始检索 → 获得记忆
    2. 前额叶分析缺口 → 识别缺失信息
    3. 海马体补充检索 → 根据缺口检索
    4. 迭代直到完整或达到上限
    """

    def __init__(self, memory_system=None, llm_client=None):
        self.memory_system = memory_system
        self.llm_client = llm_client
        self.max_iterations = 3  # 最大迭代次数

    async def iterative_retrieval(
        self,
        query: str,
        initial_memories: List[Dict[str, Any]],
        max_iterations: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        迭代式记忆检索

        Args:
            query: 用户问题
            initial_memories: 初始检索的记忆
            max_iterations: 最大迭代次数

        Returns:
            {
                'memories': 完整的记忆列表,
                'iterations': 迭代次数,
                'gap_analysis': 最终缺口分析
            }
        """
        max_iter = max_iterations or self.max_iterations
        current_memories = initial_memories
        all_memory_ids = set()

        # 记录已有的memory ID (去重)
        for mem in initial_memories:
            if isinstance(mem, dict) and 'id' in mem:
                all_memory_ids.add(mem['id'])

        logger.debug(f"🔄 Starting iterative retrieval (max {max_iter} iterations)")
        logger.info(f"📦 Initial memories: {len(initial_memories)}")

        for iteration in range(max_iter):
            logger.info(f"\n--- Iteration {iteration + 1}/{max_iter} ---")

            # 前额叶分析当前记忆
            gap_analysis = await self._analyze_memory_gaps(
                query=query,
                current_memories=current_memories
            )

            logger.debug(f"🧩 Gap analysis: sufficient={gap_analysis.is_sufficient}, "
                       f"confidence={gap_analysis.confidence:.2f}")

            # 如果已经足够,退出循环
            if gap_analysis.is_sufficient:
                logger.debug(f"✅ Memory complete after {iteration + 1} iterations")
                return {
                    'memories': current_memories,
                    'iterations': iteration + 1,
                    'gap_analysis': gap_analysis,
                    'complete': True
                }

            # 识别缺失信息
            missing_aspects = gap_analysis.missing_aspects
            logger.debug(f"🔍 Missing aspects: {missing_aspects}")

            if not missing_aspects:
                logger.info(f"⚠️ No specific missing aspects identified, stopping")
                break

            # 海马体补充检索
            additional_memories = await self._retrieve_by_aspects(
                query=query,
                missing_aspects=missing_aspects,
                context=gap_analysis.retrieval_context,
                exclude_ids=all_memory_ids
            )

            if not additional_memories:
                logger.info(f"⚠️ No additional memories found, stopping")
                break

            # 合并记忆
            new_count = 0
            for mem in additional_memories:
                mem_id = mem.get('id') if isinstance(mem, dict) else None
                if mem_id and mem_id not in all_memory_ids:
                    current_memories.append(mem)
                    all_memory_ids.add(mem_id)
                    new_count += 1

            logger.info(f"➕ Added {new_count} new memories (total: {len(current_memories)})")

            if new_count == 0:
                logger.info(f"⚠️ No new unique memories, stopping")
                break

        # 最终返回
        logger.info(f"🏁 Iterative retrieval complete: {len(current_memories)} memories")
        return {
            'memories': current_memories,
            'iterations': max_iter,
            'gap_analysis': gap_analysis,
            'complete': False  # 没有在循环内完成
        }

    async def _analyze_memory_gaps(
        self,
        query: str,
        current_memories: List[Dict[str, Any]]
    ) -> MemoryGapAnalysis:
        """
        前额叶分析记忆缺口

        分析当前记忆是否足够回答问题,缺少哪些信息
        """
        # 提取记忆内容
        memory_texts = []
        for mem in current_memories[:10]:  # 只看前10条
            if isinstance(mem, dict) and 'content' in mem:
                memory_texts.append(mem['content'])
            elif isinstance(mem, str):
                memory_texts.append(mem)

        memories_summary = "\n".join([f"- {text[:100]}..." for text in memory_texts])

        prompt = f"""Analyze if the current memories are sufficient to answer the question.

Question: "{query}"

Current Memories:
{memories_summary}

Task:
1. Can you answer the question with these memories? (Yes/No)
2. If No, what specific aspects are missing?

Examples of missing aspects:
- "education context" (if question about education but memories only show interest)
- "specific date/time" (if question about when but no temporal info)
- "relationship status" (if question about status but no explicit mention)
- "background context" (if question needs more context)

Output JSON:
{{
    "is_sufficient": true/false,
    "confidence": 0.0-1.0,
    "missing_aspects": ["aspect1", "aspect2"],
    "reasoning": "explain what's missing or why it's sufficient"
}}
"""

        try:
            # 使用临时agent调用LLM
            from src.agents.base import BrainAgent

            class TempAnalyzer(BrainAgent):
                async def process_message(self, message):
                    return {}

            temp_agent = TempAnalyzer(
                agent_id='gap_analyzer',
                brain_region='prefrontal',
                system_prompt='Memory Gap Analyzer'
            )

            content = await temp_agent.call_llm(
                prompt=prompt,
                temperature=0.2,
                max_tokens=300
            )

            # 解析JSON
            import json
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result = json.loads(content)

            logger.info(f"💡 Gap reasoning: {result.get('reasoning', 'N/A')}")

            return MemoryGapAnalysis(
                is_sufficient=result.get('is_sufficient', False),
                missing_aspects=result.get('missing_aspects', []),
                retrieval_context={'query': query, 'iteration_result': result},
                confidence=result.get('confidence', 0.5)
            )

        except Exception as e:
            logger.error(f"Gap analysis failed: {e}")
            import traceback
            logger.error(traceback.format_exc())

            # Fallback: 保守策略 - 认为不足够
            return MemoryGapAnalysis(
                is_sufficient=len(current_memories) >= 3,  # 至少3条记忆
                missing_aspects=['additional_context'],
                retrieval_context={'query': query},
                confidence=0.3
            )

    async def _retrieve_by_aspects(
        self,
        query: str,
        missing_aspects: List[str],
        context: Dict[str, Any],
        exclude_ids: set
    ) -> List[Dict[str, Any]]:
        """
        根据缺失方面检索记忆

        使用LLM生成检索query,针对性地补充信息
        """
        if not self.memory_system:
            logger.warning("⚠️ No memory system available for retrieval")
            return []

        # 构建补充检索query
        aspect_queries = []
        for aspect in missing_aspects[:3]:  # 最多3个方面
            if 'education' in aspect.lower():
                aspect_queries.append(f"education study learning field subject")
            elif 'relationship' in aspect.lower():
                aspect_queries.append(f"relationship status single married dating partner")
            elif 'date' in aspect.lower() or 'time' in aspect.lower():
                aspect_queries.append(f"date time when ago yesterday")
            elif 'context' in aspect.lower():
                aspect_queries.append(query)  # 使用原问题
            else:
                aspect_queries.append(aspect)

        # 执行检索
        all_additional = []
        for aspect_query in aspect_queries:
            logger.debug(f"🔎 Retrieving for aspect: {aspect_query[:50]}...")

            try:
                # 调用memory_system检索
                memories = await self.memory_system.search_memories(
                    query=aspect_query,
                    search_type='semantic',
                    limit=3,
                    min_similarity=0.6
                )

                # 过滤已有的记忆
                for mem in memories:
                    mem_id = mem.get('id') if isinstance(mem, dict) else None
                    if mem_id and mem_id not in exclude_ids:
                        all_additional.append(mem)

            except Exception as e:
                logger.error(f"Aspect retrieval failed for '{aspect_query}': {e}")

        logger.debug(f"📦 Retrieved {len(all_additional)} additional memories")
        return all_additional

    async def enhance_initial_retrieval(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        增强初始检索 - 使用多种检索策略

        策略:
        1. 语义检索 (semantic)
        2. 关键词检索 (keyword)
        3. 时间范围检索 (temporal)
        """
        if not self.memory_system:
            return []

        all_memories = []
        seen_ids = set()

        # 策略1: 语义检索
        try:
            semantic_mems = await self.memory_system.search_memories(
                query=query,
                search_type='semantic',
                limit=top_k,
                min_similarity=0.6
            )
            for mem in semantic_mems:
                mem_id = mem.get('id') if isinstance(mem, dict) else None
                if mem_id and mem_id not in seen_ids:
                    all_memories.append(mem)
                    seen_ids.add(mem_id)
        except Exception as e:
            logger.error(f"Semantic retrieval failed: {e}")

        # 策略2: 关键词检索 (提取query中的关键词)
        keywords = self._extract_keywords(query)
        if keywords:
            try:
                keyword_query = " ".join(keywords)
                keyword_mems = await self.memory_system.search_memories(
                    query=keyword_query,
                    search_type='semantic',
                    limit=3,
                    min_similarity=0.5
                )
                for mem in keyword_mems:
                    mem_id = mem.get('id') if isinstance(mem, dict) else None
                    if mem_id and mem_id not in seen_ids:
                        all_memories.append(mem)
                        seen_ids.add(mem_id)
            except Exception as e:
                logger.error(f"Keyword retrieval failed: {e}")

        logger.info(f"📦 Enhanced retrieval: {len(all_memories)} unique memories")
        return all_memories

    def _extract_keywords(self, query: str) -> List[str]:
        """提取query中的关键词"""
        # 简单的关键词提取 - 移除stopwords
        stopwords = {'what', 'when', 'where', 'who', 'how', 'is', 'are', 'the', 'a', 'an',
                    'did', 'do', 'does', 'was', 'were', 'would', 'could', 'should'}

        words = query.lower().split()
        keywords = [w.strip('?.,!') for w in words if w.lower() not in stopwords]
        return keywords[:5]  # 最多5个关键词
