"""
🧠 推理能力分析器 - Reasoning Capability Analyzer

核心思想: 问题不是"某一种类型",而是"需要哪些推理能力的组合"

设计原则:
1. 推理能力是可组合的 (composable)
2. LLM动态分析需求,不依赖硬编码规则
3. 系统根据能力需求,动态编排agent协作

示例:
- "X在哪住了多久?"
  → 需要: [memory_retrieval, location_extraction, duration_calculation]

- "如果X没搬家,现在会在哪?"
  → 需要: [memory_retrieval, counterfactual_reasoning, location_inference]

Author: BMAM Team
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ReasoningCapability:
    """推理能力定义"""
    name: str
    description: str
    required_agents: List[str]  # 需要的brain agents
    priority: int = 1  # 执行优先级 (1=highest)


# 🧠 推理能力库 - Reasoning Capability Library
CAPABILITY_LIBRARY = {
    # === 基础能力 (Foundational) ===
    'memory_retrieval': ReasoningCapability(
        name='memory_retrieval',
        description='Retrieve relevant episodic memories from past conversations',
        required_agents=['memory_retrieval', 'hippocampus'],
        priority=1
    ),
    'fact_extraction': ReasoningCapability(
        name='fact_extraction',
        description='Extract specific facts (name, location, status) from memories',
        required_agents=['reasoning_validator'],
        priority=2
    ),

    # === 时间推理 (Temporal) ===
    'temporal_calculation': ReasoningCapability(
        name='temporal_calculation',
        description='Calculate dates, durations, or temporal sequences',
        required_agents=['reasoning_validator'],
        priority=2
    ),
    'duration_inference': ReasoningCapability(
        name='duration_inference',
        description='Infer "how long" from start/end timestamps',
        required_agents=['reasoning_validator'],
        priority=2
    ),

    # === 身份推理 (Identity) ===
    'identity_inference': ReasoningCapability(
        name='identity_inference',
        description='Infer identity/characteristics from behavioral clues',
        required_agents=['consolidation', 'reasoning_validator'],
        priority=2
    ),

    # === 模式推理 (Pattern) ===
    'pattern_recognition': ReasoningCapability(
        name='pattern_recognition',
        description='Recognize behavioral patterns and abstract themes',
        required_agents=['reflection', 'reasoning_validator'],
        priority=2
    ),
    'interest_inference': ReasoningCapability(
        name='interest_inference',
        description='Infer interests/preferences and predict future pursuits (academic fields, career paths) from past activities and stated interests',
        required_agents=['reflection'],
        priority=2
    ),

    # === 因果推理 (Causal) ===
    'causal_reasoning': ReasoningCapability(
        name='causal_reasoning',
        description='Analyze cause-effect relationships (why X happened)',
        required_agents=['reasoning_validator', 'reflection'],
        priority=3
    ),

    # === 反事实推理 (Counterfactual) ===
    'counterfactual_reasoning': ReasoningCapability(
        name='counterfactual_reasoning',
        description='Reason about hypothetical scenarios (what if X)',
        required_agents=['reasoning_validator', 'reflection'],
        priority=3
    ),

    # === 比较推理 (Comparison) ===
    'comparison': ReasoningCapability(
        name='comparison',
        description='Compare two entities or concepts',
        required_agents=['reasoning_validator', 'consolidation'],
        priority=3
    ),

    # === 多跳推理 (Multi-hop) ===
    'multi_hop_inference': ReasoningCapability(
        name='multi_hop_inference',
        description='Combine multiple pieces of information across memories',
        required_agents=['reflection', 'consolidation', 'reasoning_validator'],
        priority=3
    )
}


class CapabilityAnalyzer:
    """
    推理能力分析器

    核心功能:
    1. 分析问题需要哪些推理能力
    2. 返回能力组合和执行计划
    3. 完全由LLM驱动,无硬编码规则
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.analysis_cache = {}  # 缓存分析结果

    async def analyze(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        分析问题需要的推理能力

        Args:
            query: 用户问题
            context: 上下文信息 (可选)

        Returns:
            {
                'capabilities': [
                    {'name': 'memory_retrieval', 'priority': 1, 'reason': '...'},
                    {'name': 'temporal_calculation', 'priority': 2, 'reason': '...'}
                ],
                'execution_plan': 'Step-by-step reasoning plan',
                'confidence': 0.0-1.0
            }
        """
        # 检查缓存
        cache_key = query.lower().strip()
        if cache_key in self.analysis_cache:
            logger.info(f"📦 Capability analysis cache hit")
            return self.analysis_cache[cache_key]

        # LLM分析
        result = await self._llm_analyze(query, context)

        # 缓存结果
        if result.get('confidence', 0) >= 0.7:
            self.analysis_cache[cache_key] = result

        return result

    async def _llm_analyze(self, query: str, context: Optional[Dict]) -> Dict[str, Any]:
        """使用LLM分析推理能力需求"""

        # 构建能力库描述
        capability_descriptions = "\n".join([
            f"- **{cap.name}**: {cap.description}"
            for cap in CAPABILITY_LIBRARY.values()
        ])

        prompt = f"""Analyze what cognitive capabilities are needed to answer this question.

Question: {query}

Available Capabilities:
{capability_descriptions}

Guidelines for capability selection:
- Questions asking "What is X's identity" or "Who is X" → prioritize identity_inference
- Questions asking "What community/group did X engage with" → use fact_extraction (simple fact, not identity)
- Questions about time/dates/duration → need temporal_calculation or duration_inference
- Questions needing synthesis across multiple memories → need multi_hop_inference
- Questions about patterns/themes → need pattern_recognition
- Questions about interests/preferences → need interest_inference

Focus on WHAT the question asks for, not what you might infer:
- "What community" asks for a simple fact (the community name) → fact_extraction
- "What is their identity" asks for identity inference (who they are) → identity_inference
- Questions about interests/pursuits/fields → consider interest_inference
- Questions requiring synthesis across memories → consider multi_hop_inference
- Questions about time ordering → consider temporal_calculation

Output JSON:
{{
    "capabilities": [
        {{"name": "capability_name", "priority": 1-3, "reason": "why needed"}}
    ],
    "execution_plan": "brief plan",
    "confidence": 0.0-1.0,
    "question_complexity": "simple|moderate|complex"
}}
"""

        try:
            from src.agents.base import BrainAgent
            # 创建临时agent用于LLM调用
            class TempAnalyzer(BrainAgent):
                async def process_message(self, message): return {}

            temp_agent = TempAnalyzer(agent_id='temp_analyzer', brain_region='prefrontal', system_prompt='Capability Analyzer')
            content = await temp_agent.call_llm(
                prompt=prompt,
                temperature=0.2,
                max_tokens=500
            )

            # 解析JSON
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result = json.loads(content)

            # 验证能力名称有效性
            valid_capabilities = []
            for cap in result.get('capabilities', []):
                if cap['name'] in CAPABILITY_LIBRARY:
                    valid_capabilities.append(cap)
                else:
                    logger.warning(f"⚠️ Unknown capability: {cap['name']}")

            result['capabilities'] = valid_capabilities

            logger.info(f"🧠 Capability analysis: {[c['name'] for c in valid_capabilities]}")
            return result

        except Exception as e:
            logger.error(f"Capability analysis failed: {e}")
            import traceback
            logger.error(traceback.format_exc())

            # Fallback: 最基础的能力组合
            return {
                'capabilities': [
                    {'name': 'memory_retrieval', 'priority': 1, 'reason': 'Fallback: retrieve relevant memories'},
                    {'name': 'fact_extraction', 'priority': 2, 'reason': 'Fallback: extract answer from memories'}
                ],
                'execution_plan': 'Fallback plan: retrieve memories and extract facts',
                'confidence': 0.3,
                'question_complexity': 'unknown'
            }

    def get_execution_order(self, capabilities: List[Dict[str, Any]]) -> List[str]:
        """
        根据priority排序,返回执行顺序

        Args:
            capabilities: analyze()返回的capabilities列表

        Returns:
            按执行顺序排列的能力名称列表
        """
        sorted_caps = sorted(capabilities, key=lambda c: c.get('priority', 99))
        return [c['name'] for c in sorted_caps]

    def get_required_agents(self, capability_names: List[str]) -> List[str]:
        """
        获取所需的agent列表

        Args:
            capability_names: 能力名称列表

        Returns:
            去重后的agent列表
        """
        agents = set()
        for cap_name in capability_names:
            if cap_name in CAPABILITY_LIBRARY:
                agents.update(CAPABILITY_LIBRARY[cap_name].required_agents)
        return list(agents)
