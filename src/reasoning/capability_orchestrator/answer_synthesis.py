"""
Answer Synthesis for Capability Orchestrator
答案合成模块 - 合成、选择、精炼答案
"""

import logging
import json
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class AnswerSynthesisMixin:
    """Answer synthesis mixin for CapabilityOrchestrator"""

    async def _synthesize_answer(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        🧠 智能答案选择 - 使用LLM评估哪个capability的答案最匹配问题意图

        策略升级:
        1. 收集所有有答案的capabilities
        2. 如果只有1个答案,直接返回
        3. 如果有多个答案,使用LLM判断哪个最匹配问题的语义和期望答案类型
        4. 这是brain-collaboration approach,不是hardcoded rules
        """
        intermediate = context['intermediate_results']
        query = context.get('query', '')

        # 🔥 2025-12-27: 检测是否为推荐类问题 (需要完整回答)
        is_recommendation_question = any(kw in query.lower() for kw in [
            'recommend', 'suggest', 'resources', 'best way', 'how should',
            'what are some', 'can you suggest', 'looking for ways'
        ])

        # 收集有答案的capabilities
        cap_results = []
        for cap_name, result in intermediate.items():
            # 🔥 2025-12-27: 添加类型检查，跳过非字典结果
            if cap_name.startswith('_'):  # 跳过内部字段如 _user_id
                continue
            if not isinstance(result, dict):
                logger.warning(f"⚠️ Capability {cap_name} returned non-dict: {type(result)}")
                continue
            if result.get('answer'):
                answer = str(result.get('answer', ''))
                # 🔥 2025-12-27: 对推荐类问题，过滤太短的答案
                if is_recommendation_question and len(answer) < 30:
                    logger.info(f"⏭️ Skipping short answer from {cap_name} for recommendation question: {answer[:50]}")
                    continue
                cap_results.append((cap_name, result))

        # Case 1: 没有答案
        if not cap_results:
            # 🔥 2025-12-27: 对推荐类问题，生成一个通用但有帮助的回答
            if is_recommendation_question:
                fallback_answer = "Based on your preferences, I recommend exploring resources and methods that align with your learning style. Consider options that match your stated interests while avoiding approaches you've mentioned disliking. Interactive and hands-on methods often work well for personalized learning."
                return {
                    'answer': fallback_answer,
                    'confidence': 0.4,
                    'error': 'No suitable answer found, using fallback',
                    'fallback': True
                }
            return {
                'answer': f"I don't have enough information to answer the question: {query}",
                'confidence': 0.1,
                'error': 'No capability produced an answer',
                'fallback': True
            }

        # Case 2: 只有一个答案,直接返回
        if len(cap_results) == 1:
            cap_name, result = cap_results[0]
            logger.info(f"🎯 Single answer from {cap_name}: {str(result.get('answer'))[:100]}...")
            return {
                'answer': result['answer'],
                'confidence': result.get('confidence', 0.7),
                'primary_capability': cap_name
            }

        # Case 3: 多个答案 - 使用LLM智能选择
        logger.info(f"🤔 Multiple answers available ({len(cap_results)}), using LLM to select best match...")
        selected_cap, selected_result = await self._llm_select_best_answer(query, cap_results)

        logger.info(f"🎯 LLM selected answer from {selected_cap}: {str(selected_result.get('answer'))[:100]}...")

        return {
            'answer': selected_result['answer'],
            'confidence': selected_result.get('confidence', 0.7),
            'primary_capability': selected_cap
        }

    async def _llm_select_best_answer(
        self,
        query: str,
        cap_results: List[tuple]
    ) -> tuple:
        """
        🧠 使用LLM评估多个候选答案,选择最匹配问题意图的

        这是brain-collaboration的核心 - 让LLM判断语义匹配,而非硬编码规则
        """
        from src.agents.base import BrainAgent

        class TempAnswerSelector(BrainAgent):
            async def process_message(self, msg): return {}

        selector = TempAnswerSelector('answer_selector', 'prefrontal', 'Answer Selector')

        # 构建候选答案描述
        candidates_text = ""
        for i, (cap_name, result) in enumerate(cap_results, 1):
            answer = result.get('answer', '')
            confidence = result.get('confidence', 0.0)
            candidates_text += f"\n{i}. [{cap_name}] (confidence={confidence:.2f})\n   Answer: {answer}\n"

        prompt = f"""You are evaluating multiple candidate answers from different cognitive capabilities to select the best match for the question.

Question: "{query}"

Available Candidates:
{candidates_text}

Task: Select the candidate that BEST matches what the question is asking for.

Guidelines:
1. For "What did X do/research/study?" questions → prefer SPECIFIC, CONCRETE facts over general interests
2. For "What fields would X pursue?" questions → prefer GENERAL interest inferences
3. For "What specific area?" questions → prefer SPECIFIC single answers over broad lists
4. For "Why?" questions → prefer CAUSAL reasoning over descriptions
5. For "When?" or "What date?" questions → **ALWAYS prefer temporal_calculation over other capabilities** (even if it shows duration/calculation, it's more relevant than facts)
6. Temporal answers (dates, times, durations) should be prioritized for time-related questions
7. For "Where?" questions → **ALWAYS prefer LOCATION answers** (place names, addresses), NEVER return dates for where questions
8. Match answer TYPE to question TYPE: "where"→location, "when"→date, "what"→thing/activity, "who"→person
9. Shorter, more direct answers are usually better than verbose explanations (EXCEPT for recommendation questions - see #10)
10. For recommendation/resource/learning questions → **PREFER preference_aligned_response** (personalized, full recommendations)
11. For "NEW ideas/activities user hasn't tried" questions → **PREFER ideation_generation** (considers what user has NOT tried)
12. If an answer contains "(a)", "(b)", "(c)", "(d)" format from ideation_generation, it's a direct answer to a multiple-choice question
13. 🔥 For "recommend", "suggest", "best way to", "resources for" questions → ALWAYS prefer LONGER, MORE DETAILED answers over short lists/keywords

Respond with ONLY the number (1, 2, 3, etc.) of the best candidate.
"""

        response = await selector.call_llm(
            prompt=prompt,
            temperature=0.0,
            max_tokens=10
        )

        # 解析选择
        try:
            selection = int(response.strip())
            if 1 <= selection <= len(cap_results):
                return cap_results[selection - 1]
        except (ValueError, IndexError) as e:
            logger.debug(f"Failed to parse selection: {e}")

        # Fallback: 返回第一个
        logger.warning(f"Failed to parse LLM selection: {response}, falling back to first candidate")
        return cap_results[0]

    async def _refine_answer(self, query: str, answer: str, primary_capability: str = None) -> str:
        """
        答案后处理 - 针对特定问题类型优化答案格式

        目标: 解决verbose答案问题,提取核心信息
        """
        if not answer:
            return answer

        # 检测是否需要refinement
        question_lower = query.lower()

        # 🔥 规则0: 多选题处理 - 如果问题包含(a)(b)(c)(d)选项，确保答案是选项格式
        if '(a)' in query and '(b)' in query and '(c)' in query:
            # 检查答案是否已经是选项格式
            answer_lower = str(answer).lower().strip()
            if not any(opt in answer_lower for opt in ['(a)', '(b)', '(c)', '(d)', 'the answer is']):
                # 答案不是选项格式，需要转换
                logger.info(f"📝 Converting non-option answer to option: {answer[:50]}...")
                refined = await self._select_best_option(query, answer)
                if refined:
                    logger.info(f"   → Selected option: {refined}")
                    return refined

        # 规则1: "What fields" 问题 - 提取academic fields
        if any(kw in question_lower for kw in ['field', 'study', 'pursue', 'education', 'major']):
            # 检查答案是否verbose (超过10个词)
            if len(answer.split()) > 10:
                logger.debug(f"📝 Refining verbose 'fields' answer: {answer[:50]}...")
                refined = await self._extract_academic_fields(answer)
                if refined and refined != answer:
                    logger.info(f"   → Refined to: {refined}")
                    return refined

        # 规则2: 其他情况保持原样
        return answer

    async def _select_best_option(self, query: str, context_answer: str) -> str:
        """根据上下文答案选择最佳选项"""
        from src.agents.base import BrainAgent

        class TempSelector(BrainAgent):
            async def process_message(self, msg): return {}

        selector = TempSelector('option_selector', 'prefrontal', 'Option Selector')

        prompt = f"""Based on the given context, select the BEST option from the multiple choice question.

Question with options:
{query}

Context/Information to base your selection on:
{context_answer}

Task: Pick the option (a), (b), (c), or (d) that best aligns with the given context.

Output ONLY the letter in parentheses, like: (a) or (b) or (c) or (d)"""

        try:
            response = await selector.call_llm(prompt, temperature=0.1, max_tokens=10)
            response = response.strip().lower()

            # 提取选项
            import re
            match = re.search(r'\(([a-d])\)', response)
            if match:
                return f"({match.group(1)})"

            # 尝试其他格式
            for opt in ['a', 'b', 'c', 'd']:
                if opt in response:
                    return f"({opt})"

            return None

        except Exception as e:
            logger.error(f"Option selection failed: {e}")
            return None

    async def _extract_academic_fields(self, verbose_answer: str) -> str:
        """从verbose答案中提取academic fields"""
        from src.agents.base import BrainAgent

        class TempExtractor(BrainAgent):
            async def process_message(self, msg): return {}

        extractor = TempExtractor('field_extractor', 'prefrontal', 'Field Extractor')

        prompt = f"""Extract ONLY the academic field names from this verbose answer.

Verbose Answer: {verbose_answer}

Task: Extract just the academic field/discipline names in a concise format.

Examples:
- "Person X would likely pursue education in field A, field B, or field C"
  → "field A, field B, field C"

- "They would be interested in discipline X and discipline Y"
  → "discipline X, discipline Y"

Rules:
- Extract ONLY academic fields/disciplines
- Use comma-separated format
- Remove phrases like "would pursue", "likely to", "education in"
- Keep it under 10 words
- If no clear fields, return the original answer

Output ONLY the extracted fields, no explanation, no JSON."""

        try:
            response = await extractor.call_llm(prompt, temperature=0.1, max_tokens=50)
            # 清理response
            refined = response.strip().strip('"').strip("'")

            # 验证refinement有效性
            if len(refined) < len(verbose_answer) and len(refined.split()) <= 10:
                return refined
            else:
                return verbose_answer

        except Exception as e:
            logger.error(f"Field extraction failed: {e}")
            return verbose_answer

