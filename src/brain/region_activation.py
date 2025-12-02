"""
🧠 动态脑区激活机制 - Dynamic Region Activation Dynamics

核心原理:
1. 基于Query语义动态计算脑区激活强度 (不硬编码priority)
2. Winner-takes-all + Lateral Inhibition 机制
3. 解决Q5问题: identity_inference vs relationship_inference的竞争

神经科学基础:
- Spreading Activation Theory (激活扩散理论)
- Lateral Inhibition (侧抑制)
- Winner-takes-all networks (赢者通吃网络)

Author: BMAM Team
"""

import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ActivationScore:
    """脑区激活得分"""
    region_name: str
    score: float
    reason: str
    source: str  # 'query_semantic' | 'memory_relevance' | 'lateral_inhibition'


class RegionActivationDynamics:
    """
    动态脑区激活机制

    核心功能:
    1. 分析Query语义 → 初始激活强度
    2. 分析Memory内容 → 调制激活强度
    3. 侧抑制机制 → 最终激活强度
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

        # 脑区能力定义 (用于语义匹配,非硬编码priority)
        self.region_capabilities = {
            'identity_inference': {
                'keywords': ['identity', 'who is', 'what is someone', 'person\'s characteristics',
                           'personal identity', 'core identity', 'self-identification'],
                'description': 'Infer personal identity and characteristics'
            },
            'relationship_inference': {
                'keywords': ['relationship', 'marital status', 'single', 'married', 'dating',
                           'partner', 'spouse', 'relationship status'],
                'description': 'Infer relationship and marital status'
            },
            'interest_inference': {
                'keywords': ['interest', 'hobby', 'like', 'enjoy', 'passion', 'favorite'],
                'description': 'Infer interests and preferences'
            },
            'pattern_recognition': {
                'keywords': ['pattern', 'behavior', 'trend', 'habit', 'regularly', 'often'],
                'description': 'Recognize behavioral patterns'
            },
            'temporal_calculation': {
                'keywords': ['when', 'date', 'time', 'duration', 'how long', 'yesterday', 'ago'],
                'description': 'Calculate temporal information'
            },
            'fact_extraction': {
                'keywords': ['what', 'which', 'where', 'specific information'],
                'description': 'Extract factual information'
            }
        }

        # Lateral inhibition参数
        self.inhibition_strength = 0.3  # 抑制强度
        self.winner_threshold = 0.6     # 赢家阈值

    async def compute_activation_map(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        current_activation: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        计算脑区激活图谱

        Args:
            query: 用户问题
            memories: 检索到的记忆
            current_activation: 当前激活状态 (可选)

        Returns:
            {region_name: activation_score} - 激活强度在0-1之间
        """
        # Step 1: Query语义分析 → 初始激活
        semantic_activation = await self._analyze_query_semantics(query)
        logger.debug(f"🔍 Query semantic activation: {semantic_activation}")

        # Step 2: 记忆内容分析 → 调制激活
        memory_activation = await self._analyze_memory_relevance(query, memories)
        logger.debug(f"💾 Memory-based activation: {memory_activation}")

        # Step 3: 融合激活信号
        combined_activation = self._combine_activations(
            semantic_activation,
            memory_activation,
            weights={'semantic': 0.6, 'memory': 0.4}
        )

        # Step 4: Lateral inhibition - 赢家抑制其他区域
        final_activation = self._apply_lateral_inhibition(combined_activation)
        logger.debug(f"🧠 Final activation (after lateral inhibition): {final_activation}")

        return final_activation

    async def _analyze_query_semantics(self, query: str) -> Dict[str, float]:
        """
        分析Query语义,计算初始激活强度

        使用LLM进行语义理解,而非简单关键词匹配
        """
        prompt = f"""Analyze what cognitive capability is most relevant to answer this question.

Question: "{query}"

Available capabilities:
{json.dumps(self.region_capabilities, indent=2)}

Critical distinction:
- "What is X's identity?" → identity_inference (who they are as a person)
- "What is X's relationship status?" → relationship_inference (single/married/dating)
- "What community did X engage with?" → fact_extraction (simple fact)
- "What fields would X pursue?" → interest_inference (academic/career interests)

Analyze the EXACT question wording:
- Does it explicitly ask about "relationship", "marital status", "single/married"?
- Does it ask about "identity", "who is", "characteristics"?
- Does it ask about "community", "group" (factual)?
- Does it ask about "fields", "education", "subjects" (interests)?

Output JSON with activation scores (0.0-1.0):
{{
    "identity_inference": 0.0-1.0,
    "relationship_inference": 0.0-1.0,
    "interest_inference": 0.0-1.0,
    "pattern_recognition": 0.0-1.0,
    "temporal_calculation": 0.0-1.0,
    "fact_extraction": 0.0-1.0,
    "reasoning": "explain which capability fits best"
}}
"""

        try:
            # 使用临时agent调用LLM
            from src.agents.base import BrainAgent

            class TempAnalyzer(BrainAgent):
                async def process_message(self, message):
                    return {}

            temp_agent = TempAnalyzer(
                agent_id='semantic_analyzer',
                brain_region='prefrontal',
                system_prompt='Query Semantic Analyzer'
            )

            content = await temp_agent.call_llm(
                prompt=prompt,
                temperature=0.1,
                max_tokens=300
            )

            # 解析JSON
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result = json.loads(content)

            # 提取激活分数
            activation = {}
            for region in self.region_capabilities.keys():
                activation[region] = result.get(region, 0.0)

            logger.info(f"💡 LLM reasoning: {result.get('reasoning', 'N/A')}")
            return activation

        except Exception as e:
            logger.error(f"Semantic analysis failed: {e}")
            import traceback
            logger.error(traceback.format_exc())

            # Fallback: 简单关键词匹配
            return self._fallback_keyword_match(query)

    def _fallback_keyword_match(self, query: str) -> Dict[str, float]:
        """Fallback: 简单关键词匹配"""
        query_lower = query.lower()
        activation = {}

        for region, config in self.region_capabilities.items():
            score = 0.0
            for keyword in config['keywords']:
                if keyword.lower() in query_lower:
                    score = max(score, 0.7)  # 匹配到关键词
            activation[region] = score

        # 如果没有匹配,默认fact_extraction
        if max(activation.values()) == 0.0:
            activation['fact_extraction'] = 0.5

        return activation

    async def _analyze_memory_relevance(
        self,
        query: str,
        memories: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        分析记忆内容对各脑区的相关性

        例如: 如果记忆中包含\"single\"关键词,则提升relationship_inference激活。
        改进: 先尝试让LLM综合记忆簇的能力分布,失败时再回退到关键词统计。
        """
        if not memories:
            return {region: 0.0 for region in self.region_capabilities.keys()}

        try:
            llm_scores = await self._llm_memory_distribution(query, memories)
            if llm_scores:
                logger.debug(f"🧬 Memory distribution (LLM): {llm_scores}")
                return llm_scores
        except Exception as exc:
            logger.warning(f"⚠️ Memory distribution analysis failed, fallback to keyword profile: {exc}")

        fallback_scores = self._keyword_memory_profile(memories)
        logger.debug(f"📝 Memory distribution (keyword fallback): {fallback_scores}")
        return fallback_scores

    async def _llm_memory_distribution(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        max_entries: int = 8
    ) -> Optional[Dict[str, float]]:
        """
        通过LLM分析记忆簇在不同脑区的证据强度。
        返回 {region: score} 的字典,得分范围0-1。
        """
        memory_snippets = self._prepare_memory_snippets(memories, max_entries=max_entries)
        if not memory_snippets:
            return None

        prompt = f"""You are analysing retrieved episodic memories to determine which cognitive capabilities have the strongest evidence to answer a question.

Question: "{query}"

Brain regions and their capabilities:
{json.dumps(self.region_capabilities, indent=2, ensure_ascii=False)}

Retrieved memories (ordered by relevance):
{memory_snippets}

Task:
1. Treat the memories as a distribution and judge how strongly each brain region is supported.
2. Score every region between 0.0 and 1.0 (0 = no evidence, 1 = overwhelming evidence).
3. Note the key signals that justify high scores.

Return STRICT JSON:
{{
  "scores": {{
    "identity_inference": 0.0-1.0,
    "relationship_inference": 0.0-1.0,
    "interest_inference": 0.0-1.0,
    "pattern_recognition": 0.0-1.0,
    "temporal_calculation": 0.0-1.0,
    "fact_extraction": 0.0-1.0
  }},
  "signals": {{
    "identity_inference": ["concise evidence phrases"],
    "relationship_inference": ["..."],
    "interest_inference": ["..."],
    "pattern_recognition": ["..."],
    "temporal_calculation": ["..."],
    "fact_extraction": ["..."]
  }}
}}
"""

        from src.agents.base import BrainAgent

        class MemoryProfilerAgent(BrainAgent):
            async def process_message(self, message):
                return {}

        profiler = MemoryProfilerAgent(
            agent_id='memory_distribution_profiler',
            brain_region='prefrontal',
            system_prompt='Memory Distribution Profiler'
        )

        content = await profiler.call_llm(
            prompt=prompt,
            temperature=0.2,
            max_tokens=400
        )

        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()

        parsed = json.loads(content)
        scores = parsed.get('scores', {})

        activation = {}
        for region in self.region_capabilities.keys():
            activation[region] = float(scores.get(region, 0.0))

        return activation

    def _prepare_memory_snippets(
        self,
        memories: List[Dict[str, Any]],
        max_entries: int = 8,
        max_length: int = 220
    ) -> str:
        """将记忆裁剪成提示用的简短片段。"""
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

        return "\n".join(snippets)

    def _keyword_memory_profile(self, memories: List[Dict[str, Any]]) -> Dict[str, float]:
        """关键词统计的备用方案。"""
        combined_text = []
        for mem in memories[:10]:
            if isinstance(mem, dict) and 'content' in mem:
                combined_text.append(mem['content'])
            else:
                combined_text.append(str(mem))

        text = " ".join(combined_text).lower()

        activation = {}
        for region, config in self.region_capabilities.items():
            score = 0.0
            for keyword in config['keywords']:
                if keyword.lower() in text:
                    score += 0.2
            activation[region] = min(score, 1.0)

        return activation

    def _combine_activations(
        self,
        semantic_activation: Dict[str, float],
        memory_activation: Dict[str, float],
        weights: Dict[str, float] = {'semantic': 0.6, 'memory': 0.4}
    ) -> Dict[str, float]:
        """融合语义激活和记忆激活"""
        combined = {}
        all_regions = set(semantic_activation.keys()) | set(memory_activation.keys())

        for region in all_regions:
            sem_score = semantic_activation.get(region, 0.0)
            mem_score = memory_activation.get(region, 0.0)
            combined[region] = (
                weights['semantic'] * sem_score +
                weights['memory'] * mem_score
            )

        return combined

    def _apply_lateral_inhibition(
        self,
        activation: Dict[str, float]
    ) -> Dict[str, float]:
        """
        应用侧抑制机制: 最强的区域抑制其他区域

        神经科学原理:
        - Winner-takes-all: 最强信号赢
        - Lateral inhibition: 赢家抑制邻近区域
        """
        if not activation:
            return activation

        # 找出赢家
        winner = max(activation.items(), key=lambda x: x[1])
        winner_region, winner_score = winner

        # 如果赢家分数太低,不应用抑制
        if winner_score < self.winner_threshold:
            logger.info(f"⚠️ No clear winner (max={winner_score:.2f}), skip inhibition")
            return activation

        # 应用抑制
        inhibited = {}
        for region, score in activation.items():
            if region == winner_region:
                inhibited[region] = score  # 赢家保持不变
            else:
                # 被抑制: score * (1 - inhibition_strength * winner_score)
                inhibited[region] = score * (1 - self.inhibition_strength * winner_score)

        logger.info(f"🏆 Winner: {winner_region} ({winner_score:.2f}), inhibiting others")
        return inhibited

    def get_top_regions(
        self,
        activation_map: Dict[str, float],
        top_k: int = 3
    ) -> List[str]:
        """返回激活最强的top-k个脑区"""
        sorted_regions = sorted(
            activation_map.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [region for region, score in sorted_regions[:top_k] if score > 0.1]
