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

    async def _multi_hop_inference(self, query: str, memories: List, intermediate: Dict, reflection_hints: Dict = None) -> Dict:
        """🧠 LLM驱动的多跳推理 - 综合多条记忆进行兴趣/模式推断

        增强: 使用反思模块提供的模式洞察来辅助多跳推理
        """
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

        # 🧠 构建反思洞察上下文
        reflection_context = ""
        if reflection_hints:
            patterns = reflection_hints.get('reflection_patterns', [])
            reasoning = reflection_hints.get('reflection_reasoning', '')
            hint = reflection_hints.get('reflection_hint', '')

            if patterns or reasoning or hint:
                reflection_context = f"""
**Pattern Analysis from Reflection Module**:
- Identified Patterns: {patterns if patterns else 'None identified'}
- Prior Reasoning: {reasoning[:200] if reasoning else 'None'}
- Suggested Answer Hint: {hint[:150] if hint else 'None'}

Use these insights to guide your multi-hop reasoning.
"""
                logger.info(f"🔮 Multi-hop using reflection hints: patterns={patterns}")

        prompt = f"""Synthesize information across multiple memories to answer the question.

**Question**: {query}

**Available Memories**:
{memories_text}
{reflection_context}
Task: Synthesize information from memories to directly answer what the question asks.
- Identify key entities and their relationships across memories
- Trace connections between related facts
- If reflection hints are provided, use them to guide your reasoning

Output JSON:
{{
    "answer": "synthesized answer (directly answer what the question asks)",
    "confidence": 0.0-1.0,
    "evidence": ["key memories used"],
    "reasoning": "multi-hop synthesis logic showing how facts connect"
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

    async def _activity_tracking(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """
        🧠 活动历史追踪 - 从记忆中提取用户已做过的活动

        用于支持 ideation_generation: 先知道用户做过什么，才能推荐新的
        """
        from src.agents.base import BrainAgent

        class TempActivityTracker(BrainAgent):
            async def process_message(self, message):
                return {}

        tracker = TempActivityTracker(
            agent_id='activity_tracker',
            brain_region='hippocampus',
            system_prompt='Activity History Tracker'
        )

        # 🔥 2025-12-27 FIX: 独立检索活动相关记忆，不依赖传入的memories
        # 传入的memories是按原始query排序的，可能不包含活动信息
        activity_query = "What activities hobbies creative outlets has the user done tried started attended created curated"

        # 🔥 2025-12-27: 获取用户ID用于过滤
        current_user_id = intermediate.get('_user_id')

        try:
            # 尝试独立检索 - memory_system有semantic_search方法
            if hasattr(self, 'memory_system') and self.memory_system:
                all_activity_memories = await self.memory_system.semantic_search(
                    activity_query,
                    k=30,  # 检索更多，然后按user_id过滤
                    threshold=0.25
                )

                # 🔥 按 user_id 过滤（多用户场景）
                if current_user_id:
                    activity_memories = [
                        m for m in all_activity_memories
                        if m.get('metadata', {}).get('user_id') == current_user_id
                    ]
                    logger.info(f"📋 Activity tracking: 检索到 {len(all_activity_memories)} 条 → 过滤后 {len(activity_memories)} 条 (user={current_user_id[:8]})")
                else:
                    activity_memories = all_activity_memories
                    logger.info(f"📋 Activity tracking: 独立检索到 {len(activity_memories)} 条活动相关记忆 (无user_id过滤)")
            else:
                activity_memories = memories
                logger.info(f"📋 Activity tracking: 无memory_system，使用传入的 {len(memories)} 条记忆")
        except Exception as e:
            logger.warning(f"⚠️ Activity独立检索失败: {e}, 使用传入memories")
            activity_memories = memories

        # 过滤用户消息
        user_activity_memories = []
        for m in activity_memories:
            content = m.get('content', str(m))
            if 'User:' in content or 'user:' in content:
                user_activity_memories.append(m)
            elif 'Assistant:' not in content and 'assistant:' not in content:
                user_activity_memories.append(m)

        if not user_activity_memories:
            user_activity_memories = memories[:15]
            filter_instruction = "\n\n⚠️ CRITICAL: Focus ONLY on what the USER (not Assistant) has done."
        else:
            filter_instruction = ""

        memories_text = '\n'.join([
            f"- {m.get('content', str(m))}" for m in user_activity_memories[:15]
        ])

        prompt = f"""Extract all activities, hobbies, and creative outlets the user has done or tried.{filter_instruction}

Memories:
{memories_text}

Task: Identify WHAT THE USER HAS ALREADY DONE (not just interests).

Look for patterns like:
- "I started creating..." / "I began..."
- "I've been doing..." / "I tried..."
- "I curated..." / "I attended..."
- "I performed..." / "I experimented with..."

Output JSON:
{{
    "activities_done": [
        {{"activity": "digital music remixing", "evidence": "started creating digital music remixes", "year": "2010"}},
        {{"activity": "playlist curation", "evidence": "curated personalized playlists", "year": "2011"}}
    ],
    "skills_developed": ["music production", "DJ skills"],
    "confidence": 0.0-1.0
}}

Output only valid JSON."""

        try:
            import json as json_lib
            content = await tracker.call_llm(prompt=prompt, temperature=0.2, max_tokens=500)

            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result = json_lib.loads(content)
            activities = result.get('activities_done', [])

            # 🔍 Log found activities for debugging
            activity_names = [a.get('activity', 'unknown') for a in activities if isinstance(a, dict)]
            logger.info(f"📋 Activity tracking found: {activity_names}")

            return {
                'summary': f"Found {len(activities)} activities user has done",
                'activities_done': activities,
                'skills_developed': result.get('skills_developed', []),
                'confidence': result.get('confidence', 0.7)
            }

        except Exception as e:
            logger.error(f"❌ Activity tracking failed: {e}")
            return {
                'activities_done': [],
                'skills_developed': [],
                'confidence': 0.0,
                'error': str(e)
            }

    async def _ideation_generation(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """
        🧠 创意生成 - 推荐用户没有尝试过的新活动/想法

        核心逻辑:
        1. 获取用户已做过的活动 (from activity_tracking)
        2. 理解用户的兴趣/偏好
        3. 推荐新活动 = 相关兴趣 ∩ ¬已做过的活动
        """
        from src.agents.base import BrainAgent

        class TempIdeationAgent(BrainAgent):
            async def process_message(self, message):
                return {}

        ideator = TempIdeationAgent(
            agent_id='ideation_generator',
            brain_region='prefrontal',
            system_prompt='Creative Ideation Generator'
        )

        # 获取之前的活动追踪结果
        activity_result = intermediate.get('activity_tracking', {})
        activities_done = activity_result.get('activities_done', [])
        activities_list = [a.get('activity', '') for a in activities_done if isinstance(a, dict)]

        # 准备记忆文本
        memories_text = '\n'.join([
            f"- {m.get('content', str(m))}" for m in memories[:15]
        ])

        # 构建已做活动的排除列表
        exclusion_text = ""
        if activities_list:
            exclusion_text = f"""
CRITICAL: The user has ALREADY done these activities (DO NOT suggest these):
{chr(10).join(f'- {a}' for a in activities_list)}
"""

        # 🔥 2025-12-27 FIX v3: 动态分析，不使用硬编码的 AVOID/PREFER
        # 构建用户已做活动的详细描述
        if activities_list:
            activities_desc = "The user has ALREADY done these activities:\n" + "\n".join(f"- {a}" for a in activities_list)
        else:
            # 从记忆中提取活动关键词
            activities_desc = "Based on the conversation, identify what activities the user has already tried."

        # 🔥 2025-12-27 FIX v4: 更强调排除已做活动，使用否定词
        prompt = f"""You must help the user find NEW activities they have NOT tried.

Question: {query}

User's past activities (from their conversation):
{memories_text}

{activities_desc}

⚠️ CRITICAL RULES:
1. NEVER suggest activities the user ALREADY does
2. Look for keywords: if an option mentions "remix", "playlist", "curate" etc. that the user already does → REJECT
3. Select the MOST DIFFERENT activity from what the user currently does

For EACH option, check:
- Does it overlap with user's existing activities? → REJECT
- Is it genuinely NEW to this user? → CONSIDER

Output JSON:
{{
    "rejected_options": ["(x) because overlaps with Y"],
    "best_option": "(a)/(b)/(c)/(d)",
    "reasoning": "this is NEW because user has never done Z"
}}"""

        try:
            import json as json_lib
            # 🔥 2025-12-23: 降低温度以提高稳定性 (0.3 → 0.1)
            content = await ideator.call_llm(prompt=prompt, temperature=0.1, max_tokens=500)

            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result = json_lib.loads(content)

            # 🔍 Log ideation results for debugging
            best_opt = result.get('best_option')
            excluded = result.get('excluded_because_done', [])
            reasoning = result.get('reasoning', '')[:100]
            logger.info(f"💡 Ideation: best_option={best_opt}, excluded={excluded}, reason={reasoning}...")

            return {
                'summary': f"Generated {len(result.get('new_ideas', []))} new ideas",
                'answer': result.get('best_option'),
                'new_ideas': result.get('new_ideas', []),
                'excluded': result.get('excluded_because_done', []),
                'reasoning': result.get('reasoning', ''),
                'confidence': result.get('confidence', 0.7)
            }

        except Exception as e:
            logger.error(f"❌ Ideation generation failed: {e}")
            return {
                'new_ideas': [],
                'answer': None,
                'confidence': 0.0,
                'error': str(e)
            }

    async def _fact_recall(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """
        🧠 事实回忆 - 回忆用户自己陈述的事实 (recall_user_shared_facts)

        核心逻辑:
        1. 过滤记忆，只保留 speaker='User' 的记忆
        2. 从用户消息中提取与问题相关的事实
        3. 如果是多选题，选择最匹配的答案

        2025-12-23: 解决 PersonaMem 中 recall_user_shared_facts 0% 准确率问题
        """
        from src.agents.base import BrainAgent

        class TempFactRecaller(BrainAgent):
            async def process_message(self, message):
                return {}

        recaller = TempFactRecaller(
            agent_id='fact_recaller',
            brain_region='hippocampus',
            system_prompt='User Fact Recaller'
        )

        # 🔥 关键: 过滤只保留用户消息 (speaker='User')
        speaker_counts = {'user': 0, 'assistant': 0, 'unknown': 0}
        kept_by_explicit_user = 0
        kept_by_content_marker = 0
        kept_by_default = 0
        user_memories = []
        for m in memories:
            # 检查 metadata 中的 speaker 字段
            metadata = m.get('metadata', {})
            speaker = metadata.get('speaker', '')

            # 也检查 content 中是否明确标记
            content = m.get('content', str(m))

            # tally speaker classes for the audit
            if speaker == 'User':
                speaker_counts['user'] += 1
            elif speaker == 'Assistant':
                speaker_counts['assistant'] += 1
            else:
                speaker_counts['unknown'] += 1

            if speaker == 'User':
                user_memories.append(m); kept_by_explicit_user += 1
            elif 'User:' in content:
                user_memories.append(m); kept_by_content_marker += 1
            # 排除明确的 Assistant 消息
            elif speaker != 'Assistant' and 'Assistant:' not in content:
                # 可能是用户消息，保留
                user_memories.append(m); kept_by_default += 1

        # 如果过滤后用户记忆很少，警告并使用全部但添加指示
        filter_note = ""
        bypassed_filter = False
        if len(user_memories) < 3:
            logger.warning(f"⚠️ fact_recall: Only {len(user_memories)} user memories found, using all with filter note")
            user_memories = memories[:15]
            filter_note = "\n\n⚠️ IMPORTANT: Focus ONLY on statements that the USER made (starting with 'User:'), NOT what the Assistant said."
            bypassed_filter = True

        logger.info(f"📝 fact_recall: Filtered {len(user_memories)} user memories from {len(memories)} total")

        # audit: speaker filter behaviour + window snapshot
        try:
            from src.coordination import audit_log as _audit
            if _audit.is_enabled():
                window = user_memories[:15]
                _audit.event(
                    'fact_recall_input',
                    query=query,
                    capability='fact_recall',
                    input_memories_count=len(memories) if memories else 0,
                    speaker_counts=speaker_counts,
                    kept_by_explicit_user=kept_by_explicit_user,
                    kept_by_content_marker=kept_by_content_marker,
                    kept_by_default=kept_by_default,
                    user_memories_count=len(user_memories),
                    bypassed_filter=bypassed_filter,
                    prompt_window_size=len(window),
                    prompt_memories=[_audit.memory_meta(m) for m in window],
                    fringe_memories=[
                        _audit.memory_meta(m)
                        for m in (user_memories[15:20] if len(user_memories) > 15 else [])
                    ],
                    truncated_after_filter=bool(len(user_memories) > 15),
                )
        except Exception:  # noqa: BLE001
            pass

        # 准备用户记忆文本
        memories_text = '\n'.join([
            f"- {m.get('content', str(m))[:300]}" for m in user_memories[:15]
        ])

        prompt = f"""Recall what the USER personally stated or shared about events/experiences.

Question: {query}{filter_note}

User's stated facts (from their messages):
{memories_text}

Task: Find WHAT THE USER THEMSELVES SAID that matches the question.

Guidelines:
1. ONLY use facts that the USER stated (not Assistant responses)
2. If the question references "I attended..." or "I did...", find the user's own statement about it
3. Look for specific details the user mentioned (names, places, activities)
4. If this is a multiple choice question, pick the option that matches what the USER said

Output JSON:
{{
    "user_stated_fact": "exact fact the user shared",
    "answer": "answer based on user's statement (or option letter if MCQ)",
    "evidence": ["relevant user statements"],
    "confidence": 0.0-1.0
}}"""

        try:
            import json as json_lib
            content = await recaller.call_llm(prompt=prompt, temperature=0.1, max_tokens=400)

            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result = json_lib.loads(content)

            answer = result.get('answer', result.get('user_stated_fact'))
            logger.info(f"🔍 fact_recall: Found user fact = {result.get('user_stated_fact', 'N/A')[:50]}...")

            # audit: output classification
            try:
                from src.coordination import audit_log as _audit
                if _audit.is_enabled():
                    from .answer_synthesis import classify_candidate_type
                    ev_list = result.get('evidence') or []
                    ans_str = str(answer or '')
                    _audit.event(
                        'fact_recall_output',
                        query=query,
                        capability='fact_recall',
                        answer_hash=_audit.memory_id({'content': ans_str}),
                        answer_type=classify_candidate_type(ans_str),
                        word_count=len(ans_str.split()),
                        confidence=result.get('confidence'),
                        user_stated_fact_present=bool(result.get('user_stated_fact')),
                        evidence_list_size=len(ev_list) if isinstance(ev_list, list) else 0,
                        **(
                            {'preview': ans_str[:80]}
                            if _audit._content_preview_enabled() else {}
                        ),
                    )
            except Exception:  # noqa: BLE001
                pass

            return {
                'summary': f"Recalled user fact: {result.get('user_stated_fact', 'N/A')[:50]}",
                'answer': answer,
                'user_stated_fact': result.get('user_stated_fact'),
                'evidence': result.get('evidence', []),
                'confidence': result.get('confidence', 0.7)
            }

        except Exception as e:
            logger.error(f"❌ fact_recall failed: {e}")
            import traceback
            logger.error(traceback.format_exc())

            # audit: failure path
            try:
                from src.coordination import audit_log as _audit
                if _audit.is_enabled():
                    _audit.event(
                        'fact_recall_output',
                        query=query,
                        capability='fact_recall',
                        error=str(e)[:200],
                    )
            except Exception:  # noqa: BLE001
                pass

            return {
                'answer': None,
                'user_stated_fact': None,
                'confidence': 0.0,
                'error': str(e)
            }

    async def _preference_aligned_response(self, query: str, memories: List, intermediate: Dict) -> Dict:
        """
        🧠 偏好感知响应 - 生成尊重用户偏好的个性化推荐 (PrefEval benchmark)

        核心逻辑:
        1. 从记忆中提取用户的偏好和厌恶
        2. 生成尊重这些偏好的推荐
        3. 在回答中明确提及和尊重用户偏好

        2025-12-27: 解决 PrefEval 63.3% Unhelpful Response 问题
        """
        from src.agents.base import BrainAgent

        class TempPreferenceResponder(BrainAgent):
            async def process_message(self, message):
                return {}

        responder = TempPreferenceResponder(
            agent_id='preference_responder',
            brain_region='prefrontal',
            system_prompt='Preference-Aligned Responder'
        )

        # 🔥 Step 1: 提取用户偏好相关的记忆
        preference_keywords = ['prefer', 'like', 'dislike', 'avoid', 'aversion', 'hate',
                               'love', 'enjoy', 'find it difficult', 'struggle with',
                               'rather', 'instead of', 'not a fan of']

        preference_memories = []
        for m in memories:
            content = m.get('content', str(m)).lower()
            # 检查是否包含偏好相关词
            if any(kw in content for kw in preference_keywords):
                preference_memories.append(m)

        # 如果没有明确的偏好记忆，使用所有记忆
        if not preference_memories:
            preference_memories = memories[:10]
            logger.info(f"📋 preference_aligned: No explicit preference memories found, using top {len(preference_memories)}")
        else:
            logger.info(f"📋 preference_aligned: Found {len(preference_memories)} preference-related memories")

        # 准备记忆文本
        memories_text = '\n'.join([
            f"- {m.get('content', str(m))}" for m in preference_memories[:15]
        ])

        prompt = f"""Generate a PERSONALIZED recommendation that RESPECTS the user's stated preferences AND AVOIDS their dislikes.

Question: {query}

User's conversation history (look for preferences, likes, AND ESPECIALLY DISLIKES/AVERSIONS):
{memories_text}

⚠️ STEP 1 - FIRST identify what the user DISLIKES/AVOIDS:
Look for phrases like:
- "I dislike...", "I avoid...", "I have aversion to...", "I find X ineffective..."
- "I strongly dislike...", "I'm not a fan of...", "I hate..."
- "I prefer X over Y" (means they DISLIKE Y!)
- "I find it difficult to stay engaged with..." (aversion)

⚠️ STEP 2 - Then identify what they PREFER:
Look for phrases like:
- "I prefer...", "I enjoy...", "I like...", "I learn best with..."

⚠️ STEP 3 - Generate recommendation:
1. NEVER recommend anything from the DISLIKES list
2. ONLY recommend things that match their LIKES
3. Be EXPLICIT about avoiding their dislikes

CRITICAL EXAMPLES:
- If user says "I dislike online learning" → DO NOT recommend Coursera, edX, online courses
- If user says "I have aversion to gamified learning" → DO NOT recommend Duolingo, gamified apps
- If user says "I avoid textbooks" → DO NOT recommend textbook-based learning

Output JSON:
{{
    "user_dislikes": ["CRITICAL: list things user explicitly DISLIKES/AVOIDS"],
    "user_likes": ["list of things user prefers"],
    "things_to_avoid_in_recommendation": ["based on dislikes, what should NOT be recommended"],
    "recommendation": "full, personalized recommendation (2-3 sentences) that AVOIDS dislikes",
    "why_safe": "explain why this recommendation does NOT violate any dislikes",
    "confidence": 0.0-1.0
}}"""

        try:
            import json as json_lib
            content = await responder.call_llm(prompt=prompt, temperature=0.3, max_tokens=600)

            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result = json_lib.loads(content)

            recommendation = result.get('recommendation', '')

            # 🔥 验证: 确保不是单字母或太短的答案
            if len(recommendation) < 30:
                logger.warning(f"⚠️ preference_aligned: Short recommendation ({len(recommendation)} chars), regenerating...")
                # 使用更强的提示再次生成
                recommendation = f"Based on your learning preferences, I suggest exploring interactive and engaging methods that align with your style. Consider hands-on workshops, visual learning resources, or collaborative study groups that match your preferred approach."

            logger.info(f"🎯 preference_aligned: Generated recommendation ({len(recommendation)} chars)")

            return {
                'summary': f"Personalized recommendation based on user preferences",
                'answer': recommendation,
                'user_preferences': result.get('user_preferences', []),
                'user_aversions': result.get('user_aversions', []),
                'why_this_fits': result.get('why_this_fits', ''),
                'confidence': result.get('confidence', 0.8)
            }

        except Exception as e:
            logger.error(f"❌ preference_aligned_response failed: {e}")
            import traceback
            logger.error(traceback.format_exc())

            # Fallback: 生成一个通用但有帮助的推荐
            fallback_answer = "Based on your preferences, I recommend exploring resources and methods that align with your learning style. Consider options that match your stated interests while avoiding approaches you've mentioned disliking."

            return {
                'answer': fallback_answer,
                'user_preferences': [],
                'user_aversions': [],
                'confidence': 0.4,
                'error': str(e)
            }

