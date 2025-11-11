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

        # 收集有答案的capabilities
        cap_results = []
        for cap_name, result in intermediate.items():
            if result.get('answer'):
                cap_results.append((cap_name, result))

        # Case 1: 没有答案
        if not cap_results:
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
7. Shorter, more direct answers are usually better than verbose explanations

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
- "Caroline would likely pursue education in social work, community advocacy, or LGBTQ studies"
  → "social work, community advocacy, LGBTQ studies"

- "She would be interested in psychology and counseling to help the transgender community"
  → "psychology, counseling"

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

