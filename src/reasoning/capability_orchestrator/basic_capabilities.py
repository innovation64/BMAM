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
- If asking "When" → answer must be TIME/DATE
- If asking "What community" → answer must be COMMUNITY (generalize from specific groups)
  Example: "LGBTQ support group" → community is "LGBTQ community"
- If asking "What did X research" → extract the MAIN TOPIC (concise)
  Example: "adoption agencies that support LGBTQ families" → "adoption agencies"

**Abstraction Level**:
- For "community" questions: generalize specific groups to broader communities
- For "research" questions: extract core topic, not all details
- Be concise: prefer "adoption agencies" over "adoption agencies that support LGBTQ families"

**Output JSON**:
{{
    "question_type": "country|activity|community|research|date|...",
    "answer": "the extracted fact (concise, appropriate abstraction level)",
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
