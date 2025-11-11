"""
Multi-hop Reasoning Mixin
多跳推理模块
"""

import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class MultiHopReasoningMixin:
    """多跳推理Mixin"""

    async def _multi_hop_reasoning(
        self,
        query: str,
        memories: List[Dict],
        hippocampus: Optional[Any] = None,
        memories_by_region: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Multi-hop推理: 需要连接多条证据

        🧠 NEW: 协作推理架构
        - Reflection Agent: 识别抽象pattern,跨记忆推理 (如Q3: "LGBTQ group" → "helping profession")
        - Reasoning Validator: 验证和综合reflection结果
        """

        # 🧠 Step 1: 调用Reflection进行pattern-based推理 (针对Q3)
        reflection_result = None
        if self.reflection_agent and memories:
            try:
                from ...base import AgentMessage
                logger.debug("🧠 Calling Reflection Agent for pattern-based reasoning...")

                reflection_result = await self.reflection_agent.process_message(
                    AgentMessage(
                        sender="reasoning_validator",
                        receiver="reflection",
                        message_type="request",
                        content={
                            'action': 'infer_from_patterns',
                            'memories': memories,
                            'query': query
                        }
                    )
                )

                if reflection_result and reflection_result.get('confidence', 0) >= 0.7:
                    logger.debug(f"✅ Reflection Agent inferred: {reflection_result.get('answer')}")
                    # 如果reflection高置信度,直接使用其结果
                    return {
                        'answer': reflection_result.get('answer'),
                        'confidence': reflection_result.get('confidence'),
                        'reasoning_chain': reflection_result.get('patterns_identified', []),
                        'evidence_quality': 'strong',
                        'pattern_matched': reflection_result.get('abstract_connection', ''),
                        'collaboration': 'reflection_agent'
                    }
            except Exception as e:
                logger.warning(f"Reflection collaboration failed: {e}")

        memories_text = self._format_memories(memories)

        reasoning_prompt = f"""Perform multi-hop reasoning to answer the question.

Question: {query}

Available Evidence:
{memories_text}

Task: Connect multiple pieces of information to infer the answer.

Step 1 - Identify Required Hops:
What pieces of information need to be connected?

Step 2 - Extract Each Hop:
Hop 1: [Extract info A]
Hop 2: [Extract info B]
Hop 3: [Connect A + B → C]

Step 3 - Validate Chain:
Does each hop logically follow? Are there gaps?

Output JSON only:
{{
    "hops": [
        {{"hop": 1, "info": "extracted", "source": "memory X"}},
        {{"hop": 2, "info": "extracted", "source": "memory Y"}},
        {{"hop": 3, "info": "inferred", "reasoning": "A + B → C"}}
    ],
    "answer": "final inferred answer",
    "confidence": 0.0-1.0,
    "reasoning_chain": ["hop1", "hop2", "conclusion"],
    "missing_info": ["what info is missing, if any"],
    "refined_query": "query for missing info (else null)"
}}
"""

        try:
            full_prompt = f"You are a multi-hop reasoning expert. Output valid JSON only.\n\n{reasoning_prompt}"
            content = await self.call_llm(
                prompt=full_prompt,
                temperature=0.4,
                max_tokens=600
            )
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result = json.loads(content)

            # 双向反馈: Multi-hop最需要反馈
            if result.get('missing_info') and hippocampus:
                logger.debug(f"🔄 Multi-hop: Missing {len(result['missing_info'])} pieces, requesting from Hippocampus")
                for missing in result['missing_info'][:2]:  # 最多补充2条
                    more_memories = await hippocampus.retrieve(missing, k=5)
                    if more_memories:
                        memories.extend(more_memories)

                # 重新推理(只一次)
                return await self._multi_hop_reasoning(query, memories, None)

            logger.debug(f"✅ Multi-hop reasoning: {result.get('answer')} (confidence={result.get('confidence', 0):.2f})")
            return result

        except Exception as e:
            import traceback
            logger.error(f"Multi-hop reasoning error: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {'answer': None, 'confidence': 0.0, 'reasoning_chain': [f'Error: {str(e)}']}
