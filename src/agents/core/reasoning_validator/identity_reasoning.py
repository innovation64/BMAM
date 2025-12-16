"""
Identity Reasoning Mixin
身份推理模块
"""

import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class IdentityReasoningMixin:
    """身份推理Mixin"""

    async def _identity_reasoning(
        self,
        query: str,
        memories: List[Dict],
        hippocampus: Optional[Any] = None,
        memories_by_region: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        身份推理: 从线索推断身份

        人脑过程:
        1. 提取所有身份相关线索
        2. 模式匹配 (社群归属 + 共鸣 → 身份认同)
        3. 概率推理 P(identity | evidence)
        4. 如果证据不足,向海马体请求更多记忆

        🧠 NEW: 协作推理架构
        - Consolidation Agent: 整合事实细节,推断身份specifics (如性别)
        - Reasoning Validator: 验证和综合consolidation结果
        """

        # 🧠 Step 1: 调用Consolidation进行事实整合推理 (针对Q5)
        consolidation_result = None
        if self.consolidation_agent and memories:
            try:
                from ...base import AgentMessage
                logger.debug("🧠 Calling Consolidation Agent for identity detail inference...")

                consolidation_result = await self.consolidation_agent.process_message(
                    AgentMessage(
                        sender="reasoning_validator",
                        receiver="consolidation",
                        message_type="request",
                        content={
                            'action': 'infer_identity_details',
                            'memories': memories,
                            'query': query
                        }
                    )
                )

                if consolidation_result and consolidation_result.get('confidence', 0) >= 0.7:
                    logger.debug(f"✅ Consolidation Agent inferred: {consolidation_result.get('complete_identity')}")
                    # 如果consolidation高置信度,直接使用其结果
                    return {
                        'answer': consolidation_result.get('complete_identity'),
                        'confidence': consolidation_result.get('confidence'),
                        'reasoning_chain': [
                            'Consolidation Agent integrated facts from memories',
                            consolidation_result.get('reasoning', '')
                        ],
                        'evidence_quality': 'strong',
                        'clues_found': consolidation_result.get('contextual_clues', []),
                        'collaboration': 'consolidation_agent'
                    }
            except Exception as e:
                logger.warning(f"Consolidation collaboration failed: {e}")

        # 构建推理prompt
        memories_text = self._format_memories(memories)

        reasoning_prompt = f"""You are simulating human prefrontal cortex reasoning for identity inference.

Question: {query}

Available Evidence:
{memories_text}

Task: Analyze evidence and infer identity using probabilistic reasoning.

Step 1 - Extract Identity Clues:
Look for:
- Community affiliations (support groups, organizations)
- Emotional resonance with specific stories/topics
- Self-descriptive actions and statements
- Direct statements about identity

Step 2 - Pattern Matching:
Common patterns:
- Seeking [identity] community + resonance with [identity] stories → likely identifies as [identity]
- First time at [identity] group + finding it "powerful" → exploring that identity
- [Identity] topics "inspiring" + attending [identity] events → strong identification

Step 3 - Probabilistic Inference:
Calculate P(identity | evidence):
- 0.9-1.0: Almost certain (multiple strong clues)
- 0.7-0.9: Highly likely (clear pattern match)
- 0.5-0.7: Probable (moderate clues - PROVIDE INFERENCE)
- <0.5: Insufficient evidence

Step 4 - Decision:
- If confidence ≥ 0.5: Provide inferred identity with FULL DESCRIPTION
- If confidence < 0.5: Request more specific memories (return refined_query)

🔥 IMPORTANT - Answer Format Requirements:
- Be specific about the full identity when evidence supports it
- Include relevant descriptors (e.g., profession, background, characteristics)
- Base your answer ONLY on the evidence in the memories

Output JSON only:
{{
    "clues_found": ["clue1", "clue2", ...],
    "pattern_matched": "description of pattern",
    "answer": "inferred identity based on evidence (or null if insufficient)",
    "confidence": 0.0-1.0,
    "reasoning_chain": ["step1", "step2", "conclusion"],
    "evidence_quality": "strong/moderate/weak",
    "refined_query": "specific query for more memories (if needed, else null)"
}}
"""

        # 调用LLM推理 (使用继承的call_llm方法)
        try:
            full_prompt = f"You are a prefrontal cortex reasoning expert. Output valid JSON only.\n\n{reasoning_prompt}"
            content = await self.call_llm(
                prompt=full_prompt,
                temperature=0.3,
                max_tokens=500
            )

            # 提取JSON (可能被```json包裹)
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result = json.loads(content)

            # 🔥 双向反馈: 如果证据不足且有海马体,再检索
            if result.get('confidence', 0) < 0.7 and result.get('refined_query') and hippocampus:
                logger.debug(f"🔄 Reasoning Validator → Hippocampus: Requesting more memories")
                logger.info(f"   Refined query: {result['refined_query']}")

                # 修复: hippocampus.retrieve -> hippocampus.search_memories
                search_result = await hippocampus.search_memories(
                    query=result['refined_query'],
                    k=10
                )
                more_memories = search_result.get('memories', []) if isinstance(search_result, dict) else search_result

                if more_memories:
                    # 合并记忆,重新推理
                    all_memories = memories + more_memories
                    logger.debug(f"🔄 Hippocampus → Reasoning Validator: Got {len(more_memories)} more memories, re-reasoning")
                    return await self._identity_reasoning(query, all_memories, None)  # 防止无限循环,只反馈一次

            logger.debug(f"✅ Identity reasoning: {result.get('answer')} (confidence={result.get('confidence', 0):.2f})")
            return result

        except Exception as e:
            import traceback
            logger.error(f"Identity reasoning error: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {
                'answer': None,
                'confidence': 0.0,
                'reasoning_chain': [f'Error: {str(e)}'],
                'error': str(e)
            }
