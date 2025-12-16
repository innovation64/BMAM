"""
General Reasoning Mixin
通用推理模块 (包含research和factual推理)
"""

import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class GeneralReasoningMixin:
    """通用推理Mixin"""

    async def _research_reasoning(
        self,
        query: str,
        memories: List[Dict],
        hippocampus: Optional[Any] = None,
        memories_by_region: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Research提取: 提取研究对象
        """

        memories_text = self._format_memories(memories)

        reasoning_prompt = f"""Extract what was being researched from memories.

Question: {query}

Available Evidence:
{memories_text}

Task: Extract the specific OBJECT of research.

Step 1 - Find Research Keywords:
Look for: "research", "researching", "studied", "investigated", "looked into"

Step 2 - Extract Object:
The object is usually right after the verb:
- "researching [adoption agencies]" → object = "adoption agencies"
- "studied [computer science]" → object = "computer science"

Step 3 - Verify:
Is this a specific, concrete thing being researched? (not vague)

Output JSON only (use actual extracted values, NOT these placeholders):
{{
    "keywords_found": [],
    "research_object": "<EXTRACTED_SPECIFIC_OBJECT>",
    "answer": "<SAME_AS_RESEARCH_OBJECT>",
    "confidence": 0.0-1.0,
    "reasoning_chain": [],
    "refined_query": null
}}

CRITICAL: Return the ACTUAL object name from memories, NOT phrases like "the object being researched"!
"""

        try:
            full_prompt = f"You are an information extraction expert. Output valid JSON only.\n\n{reasoning_prompt}"
            content = await self.call_llm(
                prompt=full_prompt,
                temperature=0.2,
                max_tokens=300
            )
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result = json.loads(content)

            # 🔥 后处理: 验证answer不是generic phrase
            answer = result.get('answer', '')
            generic_phrases = ['the object being researched', 'what was researched', 'the research object',
                              'what they researched', 'the thing being researched']

            if any(phrase in answer.lower() for phrase in generic_phrases):
                # 尝试从research_object字段获取
                if result.get('research_object') and result['research_object'] not in generic_phrases:
                    result['answer'] = result['research_object']
                    logger.warning(f"⚠️ Fixed generic answer, using research_object: {result['answer']}")
                else:
                    # 降低置信度,让系统fallback
                    result['confidence'] = 0.3
                    logger.warning(f"⚠️ Generic answer detected, lowering confidence")

            # 双向反馈
            if result.get('confidence', 0) < 0.7 and result.get('refined_query') and hippocampus:
                # 修复: hippocampus.retrieve -> hippocampus.search_memories
                search_result = await hippocampus.search_memories(result['refined_query'], k=10)
                more_memories = search_result.get('memories', []) if isinstance(search_result, dict) else search_result
                if more_memories:
                    return await self._research_reasoning(query, memories + more_memories, None)

            logger.debug(f"✅ Research reasoning: {result.get('answer')} (confidence={result.get('confidence', 0):.2f})")
            return result

        except Exception as e:
            import traceback
            logger.error(f"Research reasoning error: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {'answer': None, 'confidence': 0.0, 'reasoning_chain': [f'Error: {str(e)}']}

    async def _general_reasoning(self, query: str, memories: List[Dict]) -> Dict[str, Any]:
        """
        通用推理 - 用于factual问题 (relationship status, location等)

        直接从记忆中提取事实信息
        """
        if not memories:
            return {
                'answer': None,
                'confidence': 0.0,
                'reasoning_chain': ['No memories available'],
                'evidence': []
            }

        memories_text = self._format_memories(memories)

        reasoning_prompt = f"""You are extracting factual information from memories.

Question: {query}

Available Memories:
{memories_text}

Task: Extract the DIRECT answer from memories. This is a simple fact retrieval task.

Examples:
- Question: "What is Person's relationship status?"
  Memory: "Person is single and has had their friends for 4 years."
  Answer: "single"

- Question: "Where did Person move from?"
  Memory: "Person moved from CountryX 4 years ago."
  Answer: "CountryX"

Instructions:
1. Find the memory that directly answers the question
2. Extract the specific fact (relationship status, location, etc.)
3. Return ONLY the factual answer (concise, 1-3 words preferred)

Output JSON only:
{{
    "answer": "concise factual answer",
    "confidence": 0.0-1.0,
    "reasoning_chain": ["Found in memory: ...", "Extracted fact: ..."],
    "evidence_memory": "the memory that contains the answer"
}}
"""

        try:
            full_prompt = f"You are a factual information extractor. Output valid JSON only.\n\n{reasoning_prompt}"
            content = await self.call_llm(
                prompt=full_prompt,
                temperature=0.1,
                max_tokens=300
            )

            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result = json.loads(content)
            logger.debug(f"✅ Factual reasoning: {result.get('answer')} (confidence={result.get('confidence', 0):.2f})")
            return result

        except Exception as e:
            logger.error(f"Factual reasoning error: {e}")
            return {
                'answer': None,
                'confidence': 0.0,
                'reasoning_chain': [f'Error: {str(e)}'],
                'evidence': memories[:3]
            }

    def _format_memories(self, memories: List[Dict]) -> str:
        """格式化记忆用于prompt"""
        formatted = []
        for i, mem in enumerate(memories[:15], 1):  # 最多15条
            content = mem.get('content', str(mem))
            timestamp = mem.get('timestamp', '')
            formatted.append(f"Memory {i}: {content}")
            if timestamp:
                formatted.append(f"  (Timestamp: {timestamp})")

        return "\n".join(formatted)
