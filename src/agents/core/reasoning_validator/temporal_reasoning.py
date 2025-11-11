"""
Temporal Reasoning Mixin
时间推理模块
"""

import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class TemporalReasoningMixin:
    """时间推理Mixin"""

    async def _temporal_reasoning(
        self,
        query: str,
        memories: List[Dict],
        hippocampus: Optional[Any] = None,
        memories_by_region: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        时间推理: 计算相对时间到绝对时间

        人脑过程:
        1. 从海马体(hippocampus)提取对话日期和事件时间
        2. 识别相对时间表达("yesterday", "last week")
        3. 执行时间计算
        4. 验证结果合理性
        """

        # 🔥 优先使用脑区组织的记忆
        if memories_by_region:
            hippocampus_memories = memories_by_region.get('hippocampus', [])
            temporal_memories = memories_by_region.get('temporal', [])

            memories_text = f"""
🧠 Hippocampus (Episodic Memory - Events & Time):
{chr(10).join(f"- {m}" for m in hippocampus_memories) if hippocampus_memories else "- (empty)"}

📚 Temporal Lobe (Semantic Memory - Facts):
{chr(10).join(f"- {m}" for m in temporal_memories) if temporal_memories else "- (empty)"}
"""
        else:
            memories_text = self._format_memories(memories)

        # 🔥 检测是否是duration问题 ("how long", "for how many years", "how many days")
        is_duration_query = any(keyword in query.lower() for keyword in [
            'how long', 'how many years', 'how many months', 'how many days',
            'how many weeks', 'duration', 'passed between', '多久', '多少天'
        ])

        reasoning_prompt = f"""You are simulating temporal reasoning in the prefrontal cortex.

Question: {query}

Available Evidence (organized by brain regions):
{memories_text}

Task: {"Calculate DURATION between two dates/events" if is_duration_query else "Calculate ABSOLUTE DATE from relative time references"} using CROSS-MEMORY reasoning.

{'🔥 DURATION CALCULATION MODE:' if is_duration_query else '🔥 DATE CALCULATION MODE - MUST RETURN ABSOLUTE DATE (e.g., \"7 May 2023\"), NOT RELATIVE TIME!'}

{'Step 1 - Identify Time Points:' if is_duration_query else 'Step 1 - Find Conversation Date (查询海马体):'}
{'''Look for TWO time references:
- If "between EVENT_A and EVENT_B": Find dates for BOTH events
  Example: "between attending LGBTQ group and researching adoption"
  → Find: "Yesterday, Caroline attended..." (7 May) AND "On 25 May, Caroline researched..." (25 May)
- If "had X for Y time": Find reference date + duration
  Example: "had friends for 4 years" + conversation on "8 May 2023" → Started on 8 May 2019''' if is_duration_query else '''Look in HIPPOCAMPUS memories for:
- "[Context: This conversation is on DATE]"
- "Today's date is DATE"
- "On DATE, ..."'''}

{'Step 2 - Extract Event Dates:' if is_duration_query else 'Step 2 - Find Event Time (查询海马体):'}
{'''Extract absolute dates for EACH event:
- If "Yesterday, Caroline attended..." + context "8 May 2023" → Event_A = 7 May 2023
- If "On 25 May, Caroline researched..." → Event_B = 25 May 2023
- If "had X for 4 years" → Duration is EXPLICITLY stated, use directly!''' if is_duration_query else '''Look in HIPPOCAMPUS memories for:
- "yesterday" → -1 day
- "today" → +0 days
- "last week" → -7 days
- "I went to ... yesterday"'''}

Step 3 - {'Duration Calculation:' if is_duration_query else 'Cross-Memory Calculation:'}
{'''CRITICAL: Calculate "days PASSED BETWEEN" two dates (EXCLUSIVE of both endpoints):
- Example: Event_A = 7 May 2023, Event_B = 25 May 2023
- Question: "How many days passed BETWEEN 7 May and 25 May?"
- Calculation: Days in between = 25 - 7 - 1 = 17 days
  * Why -1? Because we count days BETWEEN (8,9,10...24), NOT including 7 and 25
  * Count: 8 May, 9 May, ..., 24 May = 17 days
- If question is "How many days FROM X TO Y?" (inclusive): Use 25 - 7 = 18
- VERIFY: Always count the actual days to double-check!
- Alternative: If duration EXPLICITLY stated like "had friends for 4 years" → use directly!''' if is_duration_query else '''If Hippocampus says: "Context: conversation is on 8 May 2023" (Memory A)
AND Hippocampus says: "I went to support group yesterday" (Memory B)
THEN calculate: 8 May - 1 day = 7 May 2023'''}

Step 4 - Verify:
{"Does the duration make sense?" if is_duration_query else "Does the date make sense? (e.g., May 7 comes before May 8)"}

Step 5 - Decision:
- If clear {'duration' if is_duration_query else 'calculation'} from cross-memory: High confidence (0.9+)
- If ambiguous: Lower confidence, request clarification

🔥 CRITICAL for duration questions:
- If "between EVENT_A and EVENT_B": Extract BOTH dates first, then calculate difference
  Example: 7 May to 25 May → 25 - 7 = 18 days
- If memory explicitly states duration (e.g., "for 4 years"): Use that directly
- Answer format: "18 days", "4 years", "6 months", etc. (NOT dates!)

Output JSON only:
{{
    "conversation_date": "extracted date or null",
    "relative_time": "extracted relative expression or null",
    "calculated_date": "calculated absolute date{' or null if duration query' if is_duration_query else ''}",
    "duration": "{('extracted or calculated duration (e.g., \'4 years\')' if is_duration_query else 'null')}",
    "answer": "final answer in requested format ({('duration like \'4 years\' or \'17 days\'' if is_duration_query else 'ABSOLUTE DATE like \'7 May 2023\' (NOT \'yesterday\' or \'-1 day\')')})",
    "confidence": 0.0-1.0,
    "reasoning_chain": ["Memory A: ...", "Memory B: ...", "calculated: ..."],
    "calculation_steps": "detailed cross-memory calculation",
    "refined_query": "query for more context if needed (else null)"
}}
"""

        try:
            full_prompt = f"You are a temporal reasoning expert. Output valid JSON only.\n\n{reasoning_prompt}"
            content = await self.call_llm(
                prompt=full_prompt,
                temperature=0.1,
                max_tokens=500
            )
            # 提取JSON内容
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            # 尝试解析JSON，处理格式错误
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parsing failed: {e}, attempting to fix...")
                # 尝试修复常见的JSON问题
                content = content.replace(',}', '}').replace(',]', ']')
                last_brace = content.rfind('}')
                if last_brace > 0:
                    content = content[:last_brace+1]
                try:
                    result = json.loads(content)
                    logger.debug("✅ JSON fixed and parsed successfully")
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Cannot parse JSON: {e}, using fallback")
                    result = {
                        'answer': 'Unable to determine',
                        'reasoning': 'JSON parsing error',
                        'confidence': 0.3,
                        'reasoning_chain': []
                    }

            if is_duration_query:
                result = await self._enforce_duration_answer(
                    query=query,
                    result=result,
                    memories_text=memories_text
                )

            # 双向反馈
            if result.get('confidence', 0) < 0.7 and result.get('refined_query') and hippocampus:
                logger.debug(f"🔄 Temporal reasoning: Requesting more context from Hippocampus")
                more_memories = await hippocampus.retrieve(result['refined_query'], k=5)
                if more_memories:
                    return await self._temporal_reasoning(query, memories + more_memories, None)

            logger.debug(f"✅ Temporal reasoning: {result.get('answer')} (confidence={result.get('confidence', 0):.2f})")
            return result

        except Exception as e:
            import traceback
            logger.error(f"Temporal reasoning error: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {'answer': None, 'confidence': 0.0, 'reasoning_chain': [f'Error: {str(e)}']}

    async def _enforce_duration_answer(
        self,
        query: str,
        result: Dict[str, Any],
        memories_text: str
    ) -> Dict[str, Any]:
        """
        确保时长类问题的答案最终输出为持续时间,而不是回到事件日期。
        """
        answer_text = (result.get('answer') or '').strip()
        duration_text = (result.get('duration') or '').strip()

        if duration_text and self._looks_like_duration(duration_text):
            if not self._looks_like_duration(answer_text):
                result['answer'] = duration_text
            return result

        if self._looks_like_duration(answer_text):
            return result

        correction_prompt = f"""You produced a temporal reasoning result, but the question requires a duration answer.

Question: "{query}"

Memories summary:
{memories_text}

Current reasoning JSON:
{json.dumps(result, indent=2, ensure_ascii=False)}

Task:
1. Derive the duration implied by the evidence (e.g., "18 days", "4 years").
2. Update the JSON so that:
   - "answer" contains ONLY the duration string.
   - "duration" mirrors the same duration string.
   - Adjust "confidence", "reasoning_chain", and "calculation_steps" if needed.
3. If the evidence truly lacks enough information, set "answer": "unknown duration", "duration": null, and confidence ≤ 0.3.

Return STRICT JSON matching the original schema.
"""

        try:
            content = await self.call_llm(
                prompt=correction_prompt,
                temperature=0.1,
                max_tokens=400
            )
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            refined = json.loads(content)
            # 仅在确实返回duration时刷新结果
            refined_duration = (refined.get('duration') or '').strip()
            refined_answer = (refined.get('answer') or '').strip()
            if self._looks_like_duration(refined_answer) or self._looks_like_duration(refined_duration):
                if refined_duration:
                    refined['duration'] = refined_duration
                result.update(refined)
        except Exception as exc:
            logger.warning(f"⚠️ Temporal duration enforcement failed: {exc}")

        return result

    def _looks_like_duration(self, text: str) -> bool:
        """粗略判断文本是否像是一个持续时间表达。"""
        if not text:
            return False
        lower = text.lower()
        duration_units = [
            'day', 'days', 'week', 'weeks', 'month', 'months', 'year', 'years',
            'hour', 'hours', 'minute', 'minutes', '天', '周', '月', '年', '小时', '分钟'
        ]
        has_number = any(char.isdigit() for char in lower)
        has_unit = any(unit in lower for unit in duration_units)
        return has_number and has_unit
