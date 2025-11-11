"""
Inference Mixin
推理巩固模块 - 事实整合和身份推断
"""

import logging
from typing import Dict, Any, List
import json
import re

logger = logging.getLogger(__name__)


class InferenceMixin:
    """推理Mixin - 处理记忆巩固中的推理和整合"""

    async def _consolidate_for_inference(self, memories: List, query: str) -> Dict[str, Any]:
        """
        🧠 Fact integration reasoning (Consolidation Agent推理能力)

        整合多条记忆中的相关事实 - 用于补全缺失细节
        Example: "transgender" + "LGBTQ group" + "inspiring stories" → consolidate → "transgender woman"
        """

        if not memories:
            return {
                'consolidated_facts': [],
                'integrated_answer': 'No memories to consolidate',
                'confidence': 0.0
            }

        # Prepare memory contents for consolidation
        memory_texts = []
        for mem in memories:
            if isinstance(mem, dict):
                content = mem.get('content', '')
            else:
                content = str(mem)
            memory_texts.append(content)

        # Build consolidation prompt
        prompt = f"""You are a memory consolidation system that integrates related facts from multiple memory fragments.

Query: {query}

Available memory fragments:
{chr(10).join(f"{i+1}. {text}" for i, text in enumerate(memory_texts))}

Task: Consolidate these memory fragments to extract complete factual information.

Instructions:
1. Identify explicit facts stated in memories
2. Identify implicit facts that can be reliably inferred from context
3. Look for complementary information across memories that together form complete facts
4. For identity/characteristic questions: infer missing specifics from contextual clues

Example reasoning:
- Memory 1: "attended LGBTQ support group"
- Memory 2: "found transgender stories inspiring"
- Memory 3: "emotional connection to women's experiences"
→ Consolidation: These fragments suggest "transgender woman" (infers gender from feminine context)

Return ONLY a JSON object with this exact structure:
{{
    "consolidated_facts": ["fact1", "fact2", ...],
    "integrated_answer": "complete answer based on consolidated facts",
    "confidence": 0.0-1.0,
    "inference_chain": "brief explanation of consolidation logic"
}}"""

        try:
            response = await self.call_llm(
                prompt=prompt,
                max_tokens=600,
                temperature=0.2  # Low temperature for consistent fact integration
            )

            # Parse JSON response
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                # Fallback if JSON parsing fails
                return {
                    'consolidated_facts': [],
                    'integrated_answer': response.strip(),
                    'confidence': 0.5,
                    'inference_chain': 'Direct LLM response (JSON parsing failed)'
                }

        except Exception as e:
            logger.error(f"Fact consolidation failed: {e}")
            return {
                'consolidated_facts': [],
                'integrated_answer': 'Consolidation failed',
                'confidence': 0.0,
                'error': str(e)
            }

    async def _infer_identity_details(self, memories: List, query: str) -> Dict[str, Any]:
        """
        🧠 Identity detail inference (特别针对Q5类型问题)

        从上下文线索推断身份细节 (如性别、具体特征)
        Example: "transgender" (base) + contextual clues → "transgender woman"
        """

        if not memories:
            return {
                'identity_base': '',
                'inferred_details': [],
                'complete_identity': 'Information not available',
                'confidence': 0.0
            }

        # Prepare memory contents
        memory_texts = []
        for mem in memories:
            if isinstance(mem, dict):
                content = mem.get('content', '')
            else:
                content = str(mem)
            memory_texts.append(content)

        # Build identity inference prompt
        prompt = f"""You are a memory consolidation system specializing in identity inference from contextual clues.

Query: {query}

Available memories:
{chr(10).join(f"{i+1}. {text}" for i, text in enumerate(memory_texts))}

Task: Infer complete identity details by consolidating explicit statements with contextual clues.

Identity Inference Rules:
1. Extract explicit identity markers (e.g., "transgender", "LGBTQ", "gay", "lesbian")
2. Infer gender from contextual clues:
   - Feminine contexts: women's groups, feminine pronouns, women's stories → likely woman
   - Masculine contexts: men's groups, masculine pronouns, men's stories → likely man
3. Consolidate base identity + gender → complete identity
   - "transgender" + feminine context → "transgender woman"
   - "gay" + masculine context → "gay man"
4. Only infer details when evidence is strong (confidence > 0.7)

Example:
- Memory 1: "attended LGBTQ support group"
- Memory 2: "transgender stories were inspiring"
- Memory 3: "emotional about women's experiences"
→ Base identity: transgender
→ Gender inference: woman (from feminine emotional resonance)
→ Complete identity: transgender woman

Return ONLY a JSON object:
{{
    "identity_base": "base identity extracted",
    "contextual_clues": ["clue1", "clue2"],
    "inferred_details": ["detail1", "detail2"],
    "complete_identity": "full identity answer",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}"""

        try:
            response = await self.call_llm(
                prompt=prompt,
                max_tokens=600,
                temperature=0.1  # Very low temperature for consistent identity inference
            )

            # Parse JSON response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                return {
                    'identity_base': '',
                    'inferred_details': [],
                    'complete_identity': response.strip(),
                    'confidence': 0.5,
                    'reasoning': 'Direct response (JSON parsing failed)'
                }

        except Exception as e:
            logger.error(f"Identity inference failed: {e}")
            return {
                'identity_base': '',
                'inferred_details': [],
                'complete_identity': 'Information not available',
                'confidence': 0.0,
                'error': str(e)
            }
