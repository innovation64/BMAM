"""
Reasoning Capabilities for Capability Orchestrator
推理能力模块 - 时间、推理、模式识别等9个推理能力
"""

import logging
import json
import asyncio
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class ReasoningCapabilitiesMixin:
    """Reasoning capabilities mixin for CapabilityOrchestrator"""

    async def _temporal_calculation(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """时间计算"""
        reasoning_agent = self.agents.get('reasoning_validator')
        if not reasoning_agent:
            return {'error': 'reasoning_validator not found'}

        result = await reasoning_agent._temporal_reasoning(query, memories)
        return {
            'summary': f"Calculated: {str(result.get('answer', 'N/A'))}",
            'answer': result.get('answer'),
            'confidence': result.get('confidence', 0.0)
        }

    async def _duration_inference(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """时长推断 - 复用temporal_calculation"""
        return await self._temporal_calculation(query, memories, intermediate)

    async def _identity_inference(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """🧠 LLM驱动的身份推理 - 从隐式证据推断身份特征"""
        from src.agents.base import BrainAgent

        class TempIdentityAnalyzer(BrainAgent):
            async def process_message(self, message):
                return {}

        analyzer = TempIdentityAnalyzer(
            agent_id='identity_analyzer',
            brain_region='prefrontal',
            system_prompt='Identity Analyzer'
        )

        # 准备记忆文本
        memories_text = '\n'.join([
            f"- {m.get('content', str(m))}" for m in memories[:15]
        ])

        prompt = f"""Infer the person's core identity from their memories and emotional responses.

Question: {query}

Memories:
{memories_text}

Task: Analyze the memories to infer WHO the person IS at their core.

Key Inference Patterns (general rules, apply to any identity type):
1. Emotional resonance: When someone feels deeply inspired/empowered by stories about a specific group, they likely belong to that group
2. Personal connection: Research/interest in support services suggests personal relevance to that topic
3. Community affiliation: Attending support groups suggests membership in that community

Focus on the person's CORE IDENTITY (who they ARE), not roles/activities:
- ✓ Identity: specific identity characteristics (ethnicity, gender identity, profession, etc.)
- ✗ NOT roles: "advocate", "ally", "supporter", "volunteer", "researcher"

Output JSON (extract ONLY the identity, be concise):
{{
    "identity": "inferred core identity - be specific based on evidence",
    "confidence": 0.0-1.0,
    "evidence": ["key memories that reveal identity"],
    "reasoning": "why you inferred this identity"
}}
"""

        try:
            import json as json_lib
            content = await analyzer.call_llm(prompt=prompt, temperature=0.2, max_tokens=400)

            # Parse JSON
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result = json_lib.loads(content)

            return {
                'summary': f"Inferred identity: {str(result.get('identity', 'unknown'))}",
                'answer': result.get('identity'),
                'confidence': result.get('confidence', 0.7),
                'evidence': result.get('evidence', []),
                'reasoning': result.get('reasoning', '')
            }

        except Exception as e:
            logger.error(f"❌ Identity inference failed: {e}")
            import traceback
            logger.error(traceback.format_exc())

            # Fallback: 使用ReasoningValidator
            reasoning_agent = self.agents.get('reasoning_validator')
            if reasoning_agent:
                result = await reasoning_agent._identity_reasoning(query, memories)
                return {
                    'summary': f"Inferred (fallback): {str(result.get('answer'))}",
                    'answer': result.get('answer'),
                    'confidence': result.get('confidence', 0.5)
                }

            return {
                'answer': None,
                'confidence': 0.0,
                'error': str(e)
            }

    async def _pattern_recognition(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """模式识别 - 识别记忆中的模式和主题"""
        # 使用LLM进行模式识别 (不依赖老的AgentMessage架构)
        from src.agents.base import BrainAgent
        class TempAgent(BrainAgent):
            async def process_message(self, message): return {}
        temp_agent = TempAgent(agent_id='pattern_analyzer', brain_region='prefrontal', system_prompt='Temp Agent')

        memories_text = '\n'.join([f"- {m.get('content', str(m))}" for m in memories[:10]])

        prompt = f"""Analyze the patterns and themes in the memories to answer this question.

Question: {query}

Available Memories:
{memories_text}

Identify recurring patterns, common themes, or trends in the memories.
If there are no memories or patterns, state that clearly.

Output JSON:
{{
    "patterns_identified": ["pattern1", "pattern2"],
    "answer": "brief answer based on identified patterns",
    "confidence": 0.0-1.0
}}"""

        try:
            import json as json_lib
            response = await temp_agent.call_llm(prompt, temperature=0.0, max_tokens=400)

            # Parse JSON
            content = response
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result_json = json_lib.loads(content)

            return {
                'summary': f"Recognized patterns: {str(result_json.get('patterns_identified', []))}",
                'patterns': result_json.get('patterns_identified', []),
                'answer': result_json.get('answer'),
                'confidence': result_json.get('confidence', 0.0)
            }
        except Exception as e:
            logger.error(f"Pattern recognition failed: {e}")
            return {
                'summary': 'Pattern recognition failed',
                'patterns': [],
                'answer': None,
                'confidence': 0.0,
                'error': str(e)
            }

    async def _interest_inference(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """
        🧠 兴趣推断 - 通过reflection agent (DMN) + 语义映射

        分配给reflection agent的原因:
        1. Reflection使用Default Mode Network (DMN)
        2. DMN负责价值判断和目标规划
        3. "What fields would Person pursue?" 需要深度思考和意义提取

        重要: 该能力仅在问题真正询问兴趣/倾向时使用,由LLM判断适用性
        """
        from src.agents.base import BrainAgent

        class TempInterestAnalyzer(BrainAgent):
            async def process_message(self, message):
                return {}

        analyzer = TempInterestAnalyzer(
            agent_id='interest_analyzer',
            brain_region='default_mode',  # DMN
            system_prompt='Interest Inference Analyzer'
        )

        # 准备记忆文本
        memories_text = '\n'.join([
            f"- {m.get('content', str(m))}" for m in memories[:15]
        ])

        prompt = f"""Analyze the person's interests and infer academic fields they would pursue.

Question: {query}

Memories:
{memories_text}

Task:
1. Extract EXPLICIT interests (direct statements like "I'm keen on...")
2. Infer IMPLICIT interests (from actions like "researched...", "attended...")
3. Map interests to ACADEMIC FIELDS (be specific about disciplines)

Key Semantic Mappings (Interest → Academic Field):
- "counseling" / "mental health" / "therapy" → **Psychology**
- "social work" / "community services" → **Social Work**
- "teaching" / "education" → **Education**
- "law" / "legal" → **Law**
- "medicine" / "healthcare" → **Medicine**
- "business" / "management" → **Business Administration**

Infer the most relevant academic field based on the stated interests.

Output JSON:
{{
    "explicit_interests": ["list of directly stated interests"],
    "implicit_interests": ["list of inferred interests from actions"],
    "academic_fields": ["Psychology", "Social Work", etc.],
    "reasoning": "how you mapped interests to academic fields",
    "confidence": 0.0-1.0
}}

Output only valid JSON, no explanation."""

        try:
            import json as json_lib
            content = await analyzer.call_llm(prompt=prompt, temperature=0.2, max_tokens=400)

            # Parse JSON
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result = json_lib.loads(content)

            # 🔥 后处理: 语义映射增强 (确保counseling→Psychology映射)
            fields = set(result.get('academic_fields', []))
            all_interests = result.get('explicit_interests', []) + result.get('implicit_interests', [])

            # 应用语义映射表 (通用学科映射，不针对特定数据集)
            semantic_mapping = {
                'counseling': 'Psychology',
                'mental health': 'Psychology',
                'therapy': 'Psychology',
                'psychological': 'Psychology',
                'social work': 'Social Work',
                'community services': 'Social Work',
                'teaching': 'Education',
                'education': 'Education',
                'law': 'Law',
                'legal': 'Law',
                'medicine': 'Medicine',
                'healthcare': 'Medicine',
                'business': 'Business Administration',
                'management': 'Business Administration'
            }

            for interest in all_interests:
                interest_lower = interest.lower()
                for keyword, field in semantic_mapping.items():
                    if keyword in interest_lower:
                        fields.add(field)
                        logger.debug(f"🔗 Semantic mapping: '{interest}' → {field}")

            # 格式化最终答案
            if fields:
                answer = ', '.join(sorted(fields))
            else:
                answer = result.get('answer', 'Unable to determine academic fields')

            return {
                'summary': f"Interest inference: {answer}",
                'answer': answer,
                'confidence': result.get('confidence', 0.8),
                'explicit_interests': result.get('explicit_interests', []),
                'implicit_interests': result.get('implicit_interests', []),
                'reasoning': result.get('reasoning', '')
            }

        except Exception as e:
            logger.error(f"❌ Interest inference failed: {e}")
            import traceback
            logger.error(traceback.format_exc())

            # Fallback: 使用multi_hop_inference
            logger.info("⚠️ Falling back to multi_hop_inference")
            return await self._multi_hop_inference(query, memories, intermediate)

    async def _causal_reasoning(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """因果推理 - 分析为什么"""
        reasoning_agent = self.agents.get('reasoning_validator')
        if not reasoning_agent:
            return {'error': 'reasoning_validator not found'}

        # 使用LLM进行因果分析
        from src.agents.base import BrainAgent
        class TempAgent(BrainAgent):
            async def process_message(self, message): return {}
        temp_agent = TempAgent(agent_id='temp_causal', brain_region='prefrontal', system_prompt='Temp Agent')

        memories_text = '\n'.join([f"- {m.get('content', str(m))}" for m in memories[:10]])

        prompt = f"""Analyze the causal relationships to answer this question.

Question: {query}

Available Memories:
{memories_text}

Task: Identify cause-effect relationships and provide a causal explanation.

Output JSON:
{{
    "cause": "what caused it",
    "effect": "what happened",
    "answer": "causal explanation",
    "confidence": 0.0-1.0
}}
"""

        content = await temp_agent.call_llm(prompt=prompt, temperature=0.3, max_tokens=300)

        try:
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            result = json.loads(content)

            return {
                'summary': f"Cause: {str(result.get('cause'))}, Effect: {str(result.get('effect'))}",
                'answer': result.get('answer'),
                'confidence': result.get('confidence', 0.0)
            }
        except Exception as e:
            logger.error(f"Causal reasoning parse error: {e}")
            return {'error': str(e)}

    async def _counterfactual_reasoning(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """反事实推理 - what if"""
        reasoning_agent = self.agents.get('reasoning_validator')
        if not reasoning_agent:
            return {'error': 'reasoning_validator not found'}

        from src.agents.base import BrainAgent
        class TempAgent(BrainAgent):
            async def process_message(self, message): return {}
        temp_agent = TempAgent(agent_id='temp_counterfactual', brain_region='prefrontal', system_prompt='Temp Agent')

        memories_text = '\n'.join([f"- {m.get('content', str(m))}" for m in memories[:10]])

        prompt = f"""Perform counterfactual reasoning for a hypothetical scenario.

Question: {query}

Actual Events (from memories):
{memories_text}

Task: Reason about the alternative scenario.

Output JSON:
{{
    "actual_scenario": "what actually happened",
    "hypothetical_scenario": "the 'what if' scenario",
    "answer": "reasoning about the hypothetical outcome",
    "confidence": 0.0-1.0
}}
"""

        content = await temp_agent.call_llm(prompt=prompt, temperature=0.4, max_tokens=400)

        try:
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            result = json.loads(content)

            return {
                'summary': f"Hypothetical: {str(result.get('hypothetical_scenario'))}",
                'answer': result.get('answer'),
                'confidence': result.get('confidence', 0.0)
            }
        except Exception as e:
            logger.error(f"Counterfactual reasoning parse error: {e}")
            return {'error': str(e)}

    async def _comparison(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """比较推理"""
        reasoning_agent = self.agents.get('reasoning_validator')
        if not reasoning_agent:
            return {'error': 'reasoning_validator not found'}

        # 使用consolidation agent的能力
        result = await reasoning_agent._general_reasoning(query, memories)

        return {
            'summary': f"Comparison result: {str(result.get('answer', 'N/A'))}",
            'answer': result.get('answer'),
            'confidence': result.get('confidence', 0.0)
        }

    async def _multi_hop_inference(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """🧠 LLM驱动的多跳推理 - 综合多条记忆进行兴趣/模式推断"""
        from src.agents.base import BrainAgent

        class TempMultiHopAnalyzer(BrainAgent):
            async def process_message(self, message):
                return {}

        analyzer = TempMultiHopAnalyzer(
            agent_id='multihop_analyzer',
            brain_region='prefrontal',
            system_prompt='Multi-hop Analyzer'
        )

        # 准备记忆文本
        memories_text = '\n'.join([
            f"{i+1}. {m.get('content', str(m))}" for i, m in enumerate(memories[:20])
        ])

        prompt = f"""Synthesize information across multiple memories to answer the question.

**Question**: {query}

**Available Memories**:
{memories_text}

Task: Synthesize information from memories to directly answer what the question asks.

Output JSON:
{{
    "answer": "synthesized answer (directly answer what the question asks)",
    "confidence": 0.0-1.0,
    "evidence": ["key memories used"],
    "reasoning": "synthesis logic"
}}
"""

        try:
            import json as json_lib
            content = await analyzer.call_llm(prompt=prompt, temperature=0.2, max_tokens=400)

            # Parse JSON
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result = json_lib.loads(content)

            return {
                'summary': f"Multi-hop inference: {str(result.get('answer', 'N/A'))}",
                'answer': result.get('answer'),
                'confidence': result.get('confidence', 0.7),
                'supporting_memories': result.get('supporting_memories', []),
                'reasoning': result.get('reasoning', '')
            }

        except Exception as e:
            logger.error(f"❌ Multi-hop inference failed: {e}")
            import traceback
            logger.error(traceback.format_exc())

            # Fallback
            reasoning_agent = self.agents.get('reasoning_validator')
            if reasoning_agent:
                result = await reasoning_agent._multi_hop_reasoning(query, memories)
                return {
                    'summary': f"Multi-hop (fallback): {str(result.get('answer'))}",
                    'answer': result.get('answer'),
                    'confidence': result.get('confidence', 0.5)
                }

            return {
                'answer': None,
                'confidence': 0.0,
                'error': str(e)
            }

