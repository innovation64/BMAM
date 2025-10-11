"""
记忆优先推理引擎 - Memory-First Reasoning Engine

核心理念:
1. 推理不是核心,记忆才是核心
2. 优先尝试直接从记忆回答
3. 只有在记忆不足时才触发推理
4. 很多对话完全不需要推理

设计原则:
- Memory First: 先尝试记忆直接回答
- Reasoning as Fallback: 推理作为后备方案
- Minimal Intervention: 最小化推理介入
"""

import logging
from typing import List, Dict, Any, Optional
from .memory_content_analyzer import MemoryContentAnalyzer

logger = logging.getLogger(__name__)


class MemoryFirstReasoningEngine:
    """
    记忆优先推理引擎

    工作流程:
    1. 检索记忆
    2. 判断记忆是否足够直接回答
    3. 如果足够,直接提取答案
    4. 如果不够,才触发推理
    """

    def __init__(self, brain_agents: Dict = None):
        self.agents = brain_agents or {}
        self.content_analyzer = MemoryContentAnalyzer()

    async def process(self, query: str, memories: List[Dict], context: Dict = None) -> Dict[str, Any]:
        """
        处理查询

        Args:
            query: 用户问题
            memories: 检索到的记忆
            context: 上下文信息

        Returns:
            {
                'answer': str,
                'source': 'direct_memory' | 'reasoning',
                'confidence': float,
                'reasoning_used': bool
            }
        """
        if not memories:
            return {
                'answer': "I don't have any relevant memories to answer this question.",
                'source': 'no_memory',
                'confidence': 0.0,
                'reasoning_used': False
            }

        # 步骤1: 分析记忆内容
        memory_features = await self.content_analyzer.analyze(memories, query)

        # 步骤2: 尝试直接从记忆回答
        direct_answer = await self._try_direct_answer(query, memories, memory_features)

        if direct_answer and direct_answer['confidence'] >= 0.7:
            logger.info(f"✅ Direct answer from memory (conf={direct_answer['confidence']:.2f})")
            return {
                'answer': direct_answer['answer'],
                'source': 'direct_memory',
                'confidence': direct_answer['confidence'],
                'reasoning_used': False
            }

        # 步骤3: 记忆不足,触发推理
        logger.info(f"🧠 Memory insufficient, triggering reasoning...")
        reasoning_result = await self._reasoning_fallback(query, memories, memory_features)

        return {
            'answer': reasoning_result['answer'],
            'source': 'reasoning',
            'confidence': reasoning_result['confidence'],
            'reasoning_used': True,
            'reasoning_type': reasoning_result.get('type', 'unknown')
        }

    async def _try_direct_answer(self, query: str, memories: List[Dict],
                                 features: Dict) -> Optional[Dict]:
        """
        尝试直接从记忆回答

        核心逻辑:
        - 如果记忆中有明确的事实陈述,直接提取
        - 不做任何推理或计算
        """
        from src.agents.base import BrainAgent

        class DirectExtractor(BrainAgent):
            async def process_message(self, msg): return {}

        extractor = DirectExtractor(
            agent_id='direct_extractor',
            brain_region='hippocampus',
            system_prompt='Direct Memory Extractor'
        )

        # 格式化记忆
        memories_text = '\n'.join([
            f"- {m.get('content', '')}" for m in memories[:10]
        ])

        prompt = f"""Extract the DIRECT answer from memories if it exists.

Question: {query}

Memories:
{memories_text}

Rules:
1. If the answer is DIRECTLY stated in memories, extract it
2. Do NOT infer, calculate, or reason
3. Do NOT make assumptions
4. If no direct answer exists, return null

Examples:
Q: "What did X research?"
Memory: "X researched adoption agencies"
Answer: {{"answer": "adoption agencies", "confidence": 0.9}}

Q: "When did X go to Y?"
Memory: "I went to Y yesterday" (but no absolute date given)
Answer: {{"answer": null, "confidence": 0.0, "reason": "only relative time, no absolute date"}}

Output JSON:
{{
    "answer": "direct answer or null",
    "confidence": 0.0-1.0,
    "reason": "why this answer or why null"
}}
"""

        try:
            import json
            content = await extractor.call_llm(prompt=prompt, temperature=0.1, max_tokens=200)

            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result = json.loads(content)

            if result.get('answer'):
                return {
                    'answer': result['answer'],
                    'confidence': result.get('confidence', 0.5)
                }

            return None

        except Exception as e:
            logger.error(f"Direct extraction error: {e}")
            return None

    async def _reasoning_fallback(self, query: str, memories: List[Dict],
                                  features: Dict) -> Dict:
        """
        推理后备方案

        基于记忆内容特征,选择合适的推理策略
        """
        # 根据记忆特征选择推理类型
        if features['has_relative_time'] and features['conversation_date']:
            # 需要时序推理
            return await self._temporal_reasoning(query, memories, features)

        elif features['has_identity_clues']:
            # 需要身份推理
            return await self._identity_reasoning(query, memories, features)

        elif features['has_career_mentions']:
            # 需要职业/教育领域推理
            return await self._professional_reasoning(query, memories, features)

        else:
            # 通用推理
            return await self._general_reasoning(query, memories, features)

    async def _temporal_reasoning(self, query: str, memories: List[Dict],
                                  features: Dict) -> Dict:
        """时序推理 - 基于记忆内容动态推理"""
        from src.agents.base import BrainAgent

        class TemporalReasoner(BrainAgent):
            async def process_message(self, msg): return {}

        reasoner = TemporalReasoner(
            agent_id='temporal_reasoner',
            brain_region='prefrontal',
            system_prompt='Temporal Reasoner'
        )

        memories_text = '\n'.join([f"- {m.get('content', '')}" for m in memories[:10]])

        prompt = f"""Calculate the absolute date based on memory content.

Question: {query}

Memories:
{memories_text}

Detected Time Expressions: {features['time_expressions']}
Conversation Date: {features['conversation_date']}

Task:
1. Find the relative time expression (yesterday/last week/etc.)
2. Use the conversation date to calculate absolute date
3. Return the specific date

Output JSON: {{"answer": "absolute date", "confidence": 0.0-1.0}}
"""

        try:
            import json
            content = await reasoner.call_llm(prompt=prompt, temperature=0.2, max_tokens=200)

            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            result = json.loads(content)

            return {
                'answer': result['answer'],
                'confidence': result.get('confidence', 0.7),
                'type': 'temporal'
            }
        except Exception as e:
            logger.error(f"Temporal reasoning error: {e}")
            return {'answer': 'Unknown', 'confidence': 0.0, 'type': 'temporal'}

    async def _identity_reasoning(self, query: str, memories: List[Dict],
                                  features: Dict) -> Dict:
        """身份推理 - 从行为线索推理具体身份"""
        from src.agents.base import BrainAgent

        class IdentityReasoner(BrainAgent):
            async def process_message(self, msg): return {}

        reasoner = IdentityReasoner(
            agent_id='identity_reasoner',
            brain_region='prefrontal',
            system_prompt='Identity Reasoner'
        )

        memories_text = '\n'.join([f"- {m.get('content', '')}" for m in memories[:15]])

        prompt = f"""Infer the SPECIFIC identity from behavioral clues in memories.

Question: {query}

Memories:
{memories_text}

Identity Signals Detected: {features['identity_signals']}

Rules:
1. Infer the MOST SPECIFIC identity (e.g., "transgender woman", not "LGBTQ+ member")
2. Look for strong clues: "X stories inspiring" indicates X identity
3. If clues point to transgender, say "transgender woman/man", NOT vague terms

Output JSON: {{"answer": "specific identity", "confidence": 0.0-1.0}}
"""

        try:
            import json
            content = await reasoner.call_llm(prompt=prompt, temperature=0.2, max_tokens=200)

            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            result = json.loads(content)

            return {
                'answer': result['answer'],
                'confidence': result.get('confidence', 0.7),
                'type': 'identity'
            }
        except Exception as e:
            logger.error(f"Identity reasoning error: {e}")
            return {'answer': 'Unknown', 'confidence': 0.0, 'type': 'identity'}

    async def _professional_reasoning(self, query: str, memories: List[Dict],
                                      features: Dict) -> Dict:
        """职业/教育领域推理"""
        from src.agents.base import BrainAgent

        class ProfessionalReasoner(BrainAgent):
            async def process_message(self, msg): return {}

        reasoner = ProfessionalReasoner(
            agent_id='professional_reasoner',
            brain_region='prefrontal',
            system_prompt='Professional Reasoner'
        )

        memories_text = '\n'.join([f"- {m.get('content', '')}" for m in memories[:15]])

        prompt = f"""Infer academic/professional fields from memories.

Question: {query}

Memories:
{memories_text}

Career Keywords Detected: {features['career_keywords']}

Rules:
1. Extract PROFESSIONAL FIELDS (psychology, counseling, social work)
2. NOT topic keywords (adoption, identity, support)
3. Look for explicit statements: "interested in X", "want to work in Y"

Output JSON: {{"answer": "professional fields", "confidence": 0.0-1.0}}
"""

        try:
            import json
            content = await reasoner.call_llm(prompt=prompt, temperature=0.2, max_tokens=200)

            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            result = json.loads(content)

            return {
                'answer': result['answer'],
                'confidence': result.get('confidence', 0.7),
                'type': 'professional'
            }
        except Exception as e:
            logger.error(f"Professional reasoning error: {e}")
            return {'answer': 'Unknown', 'confidence': 0.0, 'type': 'professional'}

    async def _general_reasoning(self, query: str, memories: List[Dict],
                                features: Dict) -> Dict:
        """通用推理 - 综合记忆内容回答"""
        from src.agents.base import BrainAgent

        class GeneralReasoner(BrainAgent):
            async def process_message(self, msg): return {}

        reasoner = GeneralReasoner(
            agent_id='general_reasoner',
            brain_region='prefrontal',
            system_prompt='General Reasoner'
        )

        memories_text = '\n'.join([f"- {m.get('content', '')}" for m in memories[:15]])

        prompt = f"""Answer the question by synthesizing information from memories.

Question: {query}

Memories:
{memories_text}

Output JSON: {{"answer": "synthesized answer", "confidence": 0.0-1.0}}
"""

        try:
            import json
            content = await reasoner.call_llm(prompt=prompt, temperature=0.3, max_tokens=300)

            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            result = json.loads(content)

            return {
                'answer': result['answer'],
                'confidence': result.get('confidence', 0.6),
                'type': 'general'
            }
        except Exception as e:
            logger.error(f"General reasoning error: {e}")
            return {'answer': 'I cannot answer based on available memories.',
                   'confidence': 0.0, 'type': 'general'}
