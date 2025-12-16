"""
Basic Capabilities for Capability Orchestrator
基础能力模块 - 记忆检索、事实提取
"""

import logging
import json
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class BasicCapabilitiesMixin:
    """Basic capabilities mixin for CapabilityOrchestrator"""

    async def _memory_retrieval(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """记忆检索 - 基础能力"""
        # 记忆已经在brain_coordinator中检索过了,直接返回
        return {
            'summary': f'Retrieved {len(memories)} memories',
            'memories_count': len(memories)
        }

    async def _fact_extraction(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """🔥 增强版事实提取 - 添加答案相关性验证"""
        from src.agents.base import BrainAgent

        class TempFactExtractor(BrainAgent):
            async def process_message(self, message):
                return {}

        analyzer = TempFactExtractor(
            agent_id='fact_extractor',
            brain_region='prefrontal',
            system_prompt='Fact Extractor with Relevance Validation'
        )

        # 准备记忆文本
        memories_text = '\n'.join([
            f"Memory {i+1}: {m.get('content', str(m))}"
            for i, m in enumerate(memories[:10])
        ])

        # 🔥 2025-12-14: 检测问题语言
        chinese_chars = sum(1 for c in query if '\u4e00' <= c <= '\u9fff')
        is_chinese = chinese_chars / max(len(query), 1) > 0.3
        answer_language = "Chinese (中文)" if is_chinese else "English"

        prompt = f"""Extract the factual answer from the memories, ensuring relevance to the question.

**Question**: {query}

**Available Memories**:
{memories_text}

**Task**:
1. Identify what type of information the question is asking for
2. Search memories for that type of information
3. Extract the answer at the appropriate abstraction level

**Critical Rules**:
- If asking "Which country" → answer must be COUNTRY NAME
- If asking "What activity" → answer must be ACTIVITY
- If asking "Who" → answer must be PERSON or IDENTITY
- If asking "When" → answer must be TIME/DATE (NEVER make up dates!)
- If asking "Where" → answer must be LOCATION/PLACE (NEVER return dates for location questions!)
- If asking "What community" → answer must be COMMUNITY (generalize from specific groups)
- If asking "What did X research" → extract the MAIN TOPIC (concise)

**🚨 STRICT Anti-Hallucination Rules (MUST FOLLOW)**:
1. If the answer is NOT EXPLICITLY FOUND in memories → respond ONLY: "No information available" with confidence=0.1
2. NEVER invent, guess, or infer beyond what's EXPLICITLY stated in memories
3. NEVER fill in gaps with common knowledge - only use information from provided memories
4. If uncertain → set confidence < 0.5 and prefix answer with "Uncertain: "
5. Match answer TYPE to question TYPE: where→location, when→date, what→thing

**🌐 Language Rule (CRITICAL)**:
- Answer MUST be in {answer_language} to match the question language
- DO NOT mix languages in your answer

**Abstraction Level**:
- For "community" questions: generalize specific groups to broader communities
- For "research" questions: extract core topic, not all details
- Be concise: extract the key topic only

**Output JSON**:
{{
    "question_type": "country|activity|community|research|date|...",
    "answer": "the extracted fact (concise, in {answer_language})",
    "confidence": 0.0-1.0,
    "evidence": "which memory contains this fact"
}}

Output only valid JSON, no explanation."""

        try:
            content = await analyzer.call_llm(
                prompt=prompt,
                temperature=0.1,  # 低温度保证精确性
                max_tokens=300
            )

            result = json.loads(content)

            return {
                'summary': f"Extracted: {str(result.get('answer', ''))}",
                'answer': result.get('answer'),
                'confidence': result.get('confidence', 0.7),
                'question_type': result.get('question_type', '')
            }
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Fact extraction failed: {e}")
            # Fallback to original method
            reasoning_agent = self.agents.get('reasoning_validator')
            if reasoning_agent:
                result = await reasoning_agent._general_reasoning(query, memories)
                return {
                    'summary': f"Extracted: {str(result.get('answer', 'N/A'))}",
                    'answer': result.get('answer'),
                    'confidence': result.get('confidence', 0.0)
                }
            return {'error': str(e)}
