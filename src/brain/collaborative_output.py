"""
🧠 协同输出生成 - Collaborative Output Generation

核心原理:
1. 多脑区协作生成答案 (不是单一脑区输出)
2. 根据答案类型调用不同脑区组合
3. 交叉验证确保答案准确性

神经科学基础:
- 分布式表征 (Distributed Representation)
- 多区域协同 (Multi-region Collaboration)
- 前额叶整合 (Prefrontal Integration)

解决问题:
- Q1: 时间答案需要 temporal + language 协同格式化
- Q2: 复杂答案需要 reflection + consolidation 综合
- Q5: 身份答案需要 identity/relationship 协同判断

Author: BMAM Team
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple
import os
import ast
from dataclasses import dataclass
from enum import Enum

from ..utils.config import get_env

logger = logging.getLogger(__name__)


class AnswerType(Enum):
    """答案类型"""
    TEMPORAL = "temporal"           # 时间答案 (when, date)
    FACTUAL = "factual"            # 事实答案 (what, where)
    IDENTITY = "identity"          # 身份答案 (who is, identity)
    RELATIONSHIP = "relationship"  # 关系答案 (relationship status)
    INTEREST = "interest"          # 兴趣答案 (interests, fields)
    PATTERN = "pattern"            # 模式答案 (behavior patterns)
    COMPLEX = "complex"            # 复杂答案 (multi-hop)
    COUNTERFACTUAL = "counterfactual"  # 假设性问题 (Would X if Y?, hypothetical)


# Fallback keyword maps are configurable to avoid硬编码
DEFAULT_FALLBACK_KEYWORDS = {
    "temporal": ["when", "date", "time"],
    "identity": ["identity", "who is"],
    "relationship": ["relationship", "status"],
    "interest": ["field", "interest", "hobby"],
    "counterfactual": ["would", "could", "might", "if"],
}


def _load_fallback_keywords() -> Dict[str, List[str]]:
    """Load fallback keyword config from env (JSON dict) or use defaults."""
    raw = get_env("ANSWER_TYPE_FALLBACK_KEYWORDS")
    if not raw:
        return DEFAULT_FALLBACK_KEYWORDS

    try:
        parsed = ast.literal_eval(raw) if raw.startswith("{") else json.loads(raw)
        if isinstance(parsed, dict):
            normalized = {}
            for k, v in parsed.items():
                if isinstance(v, list):
                    normalized[k] = [str(item).lower() for item in v]
            if normalized:
                return normalized
    except Exception:
        logger.warning("Failed to parse ANSWER_TYPE_FALLBACK_KEYWORDS, using defaults")

    return DEFAULT_FALLBACK_KEYWORDS


FALLBACK_KEYWORDS = _load_fallback_keywords()
FALLBACK_CONFIDENCE = float(get_env("ANSWER_FALLBACK_CONFIDENCE", "0.4"))


@dataclass
class CollaborativeAnswer:
    """协同答案"""
    content: str
    answer_type: AnswerType
    contributing_regions: List[str]
    confidence: float
    reasoning: str
    metadata: Optional[Dict[str, Any]] = None


class CollaborativeOutput:
    """
    协同输出生成机制

    核心流程:
    1. 分析答案类型 (temporal/factual/identity...)
    2. 确定协同脑区 (不同类型需要不同组合)
    3. 多区域生成候选答案
    4. 交叉验证和整合
    5. 格式化输出
    """

    def __init__(self, brain_agents: Dict[str, Any] = None, llm_client=None):
        self.brain_agents = brain_agents or {}
        self.llm_client = llm_client

        # 答案类型 → 脑区协同配置
        self.collaboration_config = {
            AnswerType.TEMPORAL: {
                'primary': ['temporal_reasoning'],
                'secondary': ['language_production'],
                'validator': 'prefrontal_cortex'
            },
            AnswerType.FACTUAL: {
                'primary': ['fact_extraction'],
                'secondary': ['language_production'],
                'validator': 'reasoning_validator'
            },
            AnswerType.IDENTITY: {
                'primary': ['identity_inference'],
                'secondary': ['consolidation'],
                'validator': 'prefrontal_cortex'
            },
            AnswerType.RELATIONSHIP: {
                'primary': ['relationship_inference'],
                'secondary': ['identity_inference'],
                'validator': 'reasoning_validator'
            },
            AnswerType.INTEREST: {
                'primary': ['interest_inference', 'pattern_recognition'],
                'secondary': ['reflection'],
                'validator': 'prefrontal_cortex'
            },
            AnswerType.PATTERN: {
                'primary': ['pattern_recognition', 'reflection'],
                'secondary': ['consolidation'],
                'validator': 'prefrontal_cortex'
            },
            AnswerType.COMPLEX: {
                'primary': ['reflection', 'consolidation'],
                'secondary': ['reasoning_validator'],
                'validator': 'prefrontal_cortex'
            },
            AnswerType.COUNTERFACTUAL: {
                'primary': ['reflection', 'reasoning_validator'],
                'secondary': ['consolidation'],
                'validator': 'prefrontal_cortex'
            }
        }

    async def generate_answer(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        workspace: Dict[str, Any]
    ) -> CollaborativeAnswer:
        """
        生成协同答案

        Args:
            query: 用户问题
            memories: 检索到的记忆
            workspace: 脑区工作空间 (各脑区的中间结果)

        Returns:
            CollaborativeAnswer
        """
        # Step 1: 分析答案类型
        answer_type, answer_metadata = await self._classify_answer_type(query, memories)
        logger.debug(f"📊 Answer type: {answer_type.value}")

        # Step 2: 确定协同脑区
        config = self.collaboration_config.get(answer_type, self.collaboration_config[AnswerType.FACTUAL])
        logger.info(f"🤝 Collaboration: primary={config['primary']}, secondary={config['secondary']}")

        # Step 3: 多区域生成候选答案
        candidates = await self._generate_candidates(
            query=query,
            memories=memories,
            workspace=workspace,
            primary_regions=config['primary'],
            secondary_regions=config['secondary']
        )

        # Step 4: 交叉验证和整合
        validated_answer = await self._validate_and_integrate(
            query=query,
            candidates=candidates,
            validator_region=config['validator'],
            answer_type=answer_type
        )

        # Step 5: 格式化输出
        formatted_answer = await self._format_output(
            answer=validated_answer,
            answer_type=answer_type,
            query=query
        )

        # Step 6: 协同校准输出形态 (确保粒度/关键词准确)
        final_answer = await self._harmonize_answer(
            query=query,
            answer=formatted_answer,
            answer_type=answer_type,
            answer_metadata=answer_metadata,
            candidates=candidates,
            memories=memories
        )

        logger.debug(f"✅ Final answer: {final_answer[:100]}...")
        return CollaborativeAnswer(
            content=final_answer,
            answer_type=answer_type,
            contributing_regions=config['primary'] + config['secondary'],
            confidence=0.8,  # TODO: 实际计算confidence
            reasoning=f"Collaborative answer from {len(config['primary']) + len(config['secondary'])} regions",
            metadata=answer_metadata
        )

    async def _classify_answer_type(
        self,
        query: str,
        memories: List[Dict[str, Any]]
    ) -> Tuple[AnswerType, Dict[str, Any]]:
        """
        分类答案类型

        使用LLM分析问题和记忆,判断答案类型以及期望的输出形态。
        """
        prompt = f"""Classify what type of answer this question requires.

Question: "{query}"

Answer Types:
- temporal: Questions about time, date, when, duration (e.g., "When did X happen?")
- factual: Simple factual questions (e.g., "What did X do?", "Where is X?")
- identity: Questions about personal identity (e.g., "What is X's identity?", "Who is X?")
- relationship: Questions about relationship status (e.g., "What is X's relationship status?", "Is X single?")
- interest: Questions about interests, fields, preferences (e.g., "What fields would X pursue?")
- pattern: Questions about behavioral patterns (e.g., "What does X regularly do?")
- complex: Multi-hop or complex reasoning questions
- counterfactual: Hypothetical "Would X...?" questions requiring reasoning about alternatives (e.g., "Would X pursue Y as a career?", "Would X still want to do Y if Z?")

Critical distinctions:
- "What is X's identity?" → identity (personal characteristics)
- "What is X's relationship status?" → relationship (marital/dating status)
- "What fields would X pursue?" → interest (academic/career interests)
- "What community did X engage with?" → factual (simple fact)
- "When did X do Y?" → temporal (time/date)

Analyse the EXACT question wording and decide:
- The answer type (one of the categories above)
- The expected output shape:
  * single → a single short phrase or value
  * list → multiple items should be listed (comma-separated)
  * duration → the answer must be a duration (e.g., "18 days")
  * range → the answer should express a range or interval
- The core entity or head noun that must appear (if any)

Output JSON:
{{
    "answer_type": "temporal|factual|identity|relationship|interest|pattern|complex",
    "expected_shape": "single|list|duration|range",
    "target_entity": "mandatory keyword or head noun (or empty string)",
    "confidence": 0.0-1.0,
    "reasoning": "explain why"
}}

"""

        try:
            from src.agents.base import BrainAgent

            class TempAnalyzer(BrainAgent):
                async def process_message(self, message):
                    return {}

            temp_agent = TempAnalyzer(
                agent_id='answer_type_analyzer',
                brain_region='prefrontal',
                system_prompt='Answer Type Classifier'
            )

            content = await temp_agent.call_llm(
                prompt=prompt,
                temperature=0.1,
                max_tokens=200
            )

            # 解析JSON
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result = json.loads(content)
            answer_type_str = result.get('answer_type', 'factual')

            logger.info(f"💡 Answer type reasoning: {result.get('reasoning', 'N/A')}")

            metadata = {
                'expected_shape': result.get('expected_shape', 'single'),
                'target_entity': result.get('target_entity', '').strip(),
                'confidence': result.get('confidence', 0.6),
                'reasoning': result.get('reasoning', '')
            }

            # 转换为AnswerType
            answer_type_map = {
                'temporal': AnswerType.TEMPORAL,
                'factual': AnswerType.FACTUAL,
                'identity': AnswerType.IDENTITY,
                'relationship': AnswerType.RELATIONSHIP,
                'interest': AnswerType.INTEREST,
                'pattern': AnswerType.PATTERN,
                'complex': AnswerType.COMPLEX,
                'counterfactual': AnswerType.COUNTERFACTUAL
            }

            answer_type = answer_type_map.get(answer_type_str, AnswerType.FACTUAL)
            return answer_type, metadata

        except Exception as e:
            logger.error(f"Answer type classification failed: {e}")
            import traceback
            logger.error(traceback.format_exc())

            # Fallback: 根据可配置的关键词简单判断
            query_lower = query.lower()
            fallback_map = {
                "temporal": (AnswerType.TEMPORAL, "single"),
                "identity": (AnswerType.IDENTITY, "single"),
                "relationship": (AnswerType.RELATIONSHIP, "single"),
                "interest": (AnswerType.INTEREST, "list"),
                "counterfactual": (AnswerType.COUNTERFACTUAL, "single"),
            }

            for key, keywords in FALLBACK_KEYWORDS.items():
                if any(kw in query_lower for kw in keywords):
                    ans_type, shape = fallback_map.get(key, (AnswerType.FACTUAL, "single"))
                    return ans_type, {
                        'expected_shape': shape,
                        'target_entity': '',
                        'confidence': FALLBACK_CONFIDENCE,
                        'reasoning': 'keyword fallback'
                    }

            return AnswerType.FACTUAL, {
                'expected_shape': 'single',
                'target_entity': '',
                'confidence': FALLBACK_CONFIDENCE,
                'reasoning': 'keyword fallback'
            }

    async def _generate_candidates(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        workspace: Dict[str, Any],
        primary_regions: List[str],
        secondary_regions: List[str]
    ) -> Dict[str, str]:
        """
        多区域生成候选答案

        从workspace中提取各脑区的答案候选
        """
        candidates = {}

        # 提取记忆文本
        memory_texts = []
        for mem in memories[:5]:
            if isinstance(mem, dict) and 'content' in mem:
                memory_texts.append(mem['content'])
            elif isinstance(mem, str):
                memory_texts.append(mem)

        memories_summary = "\n".join([f"- {text}" for text in memory_texts])

        # Primary regions生成答案
        for region in primary_regions:
            if region in workspace:
                candidates[region] = workspace[region]
            else:
                # 从记忆中生成
                answer = await self._generate_from_memories(
                    query=query,
                    memories=memories_summary,
                    region_type=region
                )
                candidates[region] = answer

        # Secondary regions补充答案
        for region in secondary_regions:
            if region in workspace:
                candidates[region] = workspace[region]

        logger.info(f"📦 Generated {len(candidates)} candidate answers from regions: {list(candidates.keys())}")
        return candidates

    async def _generate_from_memories(
        self,
        query: str,
        memories: str,
        region_type: str
    ) -> str:
        """从记忆中生成答案 (根据脑区类型)"""
        region_prompts = {
            'fact_extraction': "Extract the direct factual answer from memories.",
            'temporal_reasoning': "Extract the specific date/time from memories.",
            'identity_inference': "Infer the person's identity from memories.",
            'relationship_inference': "Infer the person's relationship status from memories.",
            'interest_inference': "Infer the person's interests/fields from memories.",
            'pattern_recognition': "Identify behavioral patterns from memories."
        }

        instruction = region_prompts.get(region_type, "Answer the question based on memories.")

        prompt = f"""{instruction}

Question: "{query}"

Memories:
{memories}

Provide a concise, direct answer (1-2 sentences max).
"""

        try:
            from src.agents.base import BrainAgent

            class TempGenerator(BrainAgent):
                async def process_message(self, message):
                    return {}

            temp_agent = TempGenerator(
                agent_id=f'{region_type}_generator',
                brain_region='prefrontal',
                system_prompt=f'{region_type} Answer Generator'
            )

            answer = await temp_agent.call_llm(
                prompt=prompt,
                temperature=0.3,
                max_tokens=100
            )

            return answer.strip()

        except Exception as e:
            logger.error(f"Answer generation failed for {region_type}: {e}")
            return f"Unable to extract answer from {region_type}"

    async def _validate_and_integrate(
        self,
        query: str,
        candidates: Dict[str, str],
        validator_region: str,
        answer_type: AnswerType
    ) -> str:
        """
        交叉验证和整合候选答案

        选择最佳答案或整合多个答案
        """
        if not candidates:
            return "I don't have enough information to answer the question."

        # 如果只有一个候选
        if len(candidates) == 1:
            return list(candidates.values())[0]

        # 多个候选 → 使用validator选择最佳
        candidates_text = "\n".join([
            f"- {region}: {answer}"
            for region, answer in candidates.items()
        ])

        prompt = f"""You are a validator. Select or integrate the best answer from multiple candidate answers.

Question: "{query}"
Answer Type: {answer_type.value}

Candidate Answers:
{candidates_text}

Task:
1. If one answer is clearly correct and complete, select it
2. If multiple answers are complementary, integrate them into one coherent answer
3. If answers conflict, choose the most accurate one based on the question

Output the final answer directly (no explanation).
"""

        try:
            from src.agents.base import BrainAgent

            class TempValidator(BrainAgent):
                async def process_message(self, message):
                    return {}

            temp_agent = TempValidator(
                agent_id='answer_validator',
                brain_region='prefrontal',
                system_prompt='Answer Validator'
            )

            validated = await temp_agent.call_llm(
                prompt=prompt,
                temperature=0.2,
                max_tokens=150
            )

            return validated.strip()

        except Exception as e:
            logger.error(f"Answer validation failed: {e}")
            # Fallback: 返回第一个候选
            return list(candidates.values())[0]

    async def _harmonize_answer(
        self,
        query: str,
        answer: str,
        answer_type: AnswerType,
        answer_metadata: Optional[Dict[str, Any]],
        candidates: Dict[str, str],
        memories: List[Dict[str, Any]]
    ) -> str:
        """
        对校验过的答案做输出形态约束,确保核心关键词和粒度符合预期。
        """
        answer_metadata = answer_metadata or {}
        expected_shape = (answer_metadata.get('expected_shape') or 'single').lower()
        target_entity = (answer_metadata.get('target_entity') or '').strip()

        if self._answer_matches_shape(answer, expected_shape, target_entity):
            return answer.strip()

        consensus_tokens = self._compute_consensus_tokens(candidates)
        memory_summary = self._summarize_memories(memories)

        prompt = f"""You are the collaborative output integrator.

Question: "{query}"
Answer type: {answer_type.value}
Expected shape: {expected_shape}
Target entity / head noun: {target_entity or 'N/A'}
Consensus tokens from brain regions: {', '.join(consensus_tokens) if consensus_tokens else 'N/A'}

Validated answer (needs harmonisation):
\"\"\"{answer.strip()}\"\"\"

Candidate answers by region:
{json.dumps(candidates, indent=2, ensure_ascii=False)}

Relevant memory snippets:
{memory_summary}

Task:
1. Produce the final answer strictly matching the expected shape.
2. Explicitly mention the target entity if provided.
3. Stay concise (one sentence or a short comma-separated list).
4. Do not add speculation beyond the provided candidates and memories.

Output STRICT JSON:
{{
  "final_answer": "concise answer following the rules"
}}
"""

        try:
            from src.agents.base import BrainAgent

            class OutputHarmonizer(BrainAgent):
                async def process_message(self, message):
                    return {}

            harmonizer = OutputHarmonizer(
                agent_id='collaborative_output_harmonizer',
                brain_region='prefrontal',
                system_prompt='Collaborative Output Harmonizer'
            )

            content = await harmonizer.call_llm(
                prompt=prompt,
                temperature=0.2,
                max_tokens=200
            )

            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            parsed = json.loads(content)
            final_answer = parsed.get('final_answer') or answer
            return final_answer.strip()
        except Exception as exc:
            logger.warning(f"⚠️ Answer harmonisation failed, returning original answer: {exc}")
            return answer.strip()

    def _answer_matches_shape(
        self,
        answer: str,
        expected_shape: str,
        target_entity: str
    ) -> bool:
        """快速判定答案是否已经满足期望形态。"""
        if not answer:
            return False

        normalized = answer.strip()
        lower = normalized.lower()

        if target_entity and target_entity.lower() not in lower:
            return False

        if expected_shape == 'list':
            # 允许用逗号、顿号或"and"连接
            return any(sep in normalized for sep in [',', '，', ';', ' and '])
        if expected_shape == 'duration':
            duration_units = ['day', 'days', 'week', 'weeks', 'month', 'months', 'year', 'years', '小时', '天', '周', '月', '年']
            return any(unit in lower for unit in duration_units)
        if expected_shape == 'range':
            return any(token in lower for token in [' to ', ' - ', 'between', '从', '至'])

        # single or unknown → 只要非空即可
        return True

    def _compute_consensus_tokens(
        self,
        candidates: Dict[str, str],
        min_occurrence: int = 2
    ) -> List[str]:
        """统计多个脑区答案中共同出现的关键token。"""
        frequency: Dict[str, int] = {}

        for answer in candidates.values():
            tokens = {
                token.strip(".,!?\"'").lower()
                for token in answer.split()
                if len(token.strip(".,!?\"'")) >= 4
            }
            for token in tokens:
                frequency[token] = frequency.get(token, 0) + 1

        consensus = [
            token for token, count in frequency.items()
            if count >= min_occurrence
        ]
        consensus.sort()
        return consensus[:8]

    def _summarize_memories(
        self,
        memories: List[Dict[str, Any]],
        max_entries: int = 5,
        max_length: int = 160
    ) -> str:
        """提取用于提示的记忆摘要。"""
        snippets = []
        for idx, mem in enumerate(memories[:max_entries], start=1):
            if isinstance(mem, dict):
                text = mem.get('content') or mem.get('text') or str(mem)
            else:
                text = str(mem)

            text = text.replace('\n', ' ').strip()
            if len(text) > max_length:
                text = text[:max_length - 3].rstrip() + '...'

            if text:
                snippets.append(f"{idx}. {text}")

        return "\n".join(snippets) if snippets else "N/A"

    async def _format_output(
        self,
        answer: str,
        answer_type: AnswerType,
        query: str
    ) -> str:
        """
        格式化输出

        根据答案类型调整格式 (例如时间答案需要特定格式)
        """
        # 时间答案格式化
        if answer_type == AnswerType.TEMPORAL:
            # 尝试格式化为 "7 May 2023" 格式
            formatted = await self._format_temporal_answer(answer, query)
            return formatted

        # 其他类型直接返回
        return answer

    async def _format_temporal_answer(self, answer: str, query: str) -> str:
        """格式化时间答案"""
        prompt = f"""Format this temporal answer in the appropriate format.

Question: "{query}"
Raw Answer: "{answer}"

If the answer contains a date, format it as "Day Month Year" (e.g., "7 May 2023").
If it's just a year, return just the year.
If it's a duration, keep the original format.

Output ONLY the formatted answer, nothing else.
"""

        try:
            from src.agents.base import BrainAgent

            class TempFormatter(BrainAgent):
                async def process_message(self, message):
                    return {}

            temp_agent = TempFormatter(
                agent_id='temporal_formatter',
                brain_region='language_production',
                system_prompt='Temporal Answer Formatter'
            )

            formatted = await temp_agent.call_llm(
                prompt=prompt,
                temperature=0.1,
                max_tokens=50
            )

            return formatted.strip()

        except Exception as e:
            logger.error(f"Temporal formatting failed: {e}")
            return answer  # Fallback: 返回原答案
