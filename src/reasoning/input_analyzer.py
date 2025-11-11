"""
🧠 Question Analyzer - 问题分析器

核心思想:
- 分析问题需要哪种**信息类型** (不是关键词!)
- 让LLM理解问题语义,不依赖keyword matching
- 用于指导memory retrieval - 只检索包含相关信息类型的记忆

设计原则:
1. 完全由LLM理解语义,不依赖关键词
2. Focus on INFORMATION TYPE needed, not question patterns
3. 可泛化 - "What fields", "What subjects", "What areas" → all map to "educational_interest"

Author: BMAM Team
"""

import logging
import json
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class QuestionAnalyzer:
    """
    问题分析器

    功能:
    1. 分析问题需要哪种information type
    2. 返回应该从哪些brain regions检索
    3. 指导semantic-aware retrieval
    """

    def __init__(self):
        self.analysis_cache = {}  # 缓存分析结果

    async def analyze_question(self, query: str, llm_caller) -> Dict[str, Any]:
        """
        分析问题需要的information type

        Args:
            query: 用户问题
            llm_caller: LLM调用函数 (async callable)

        Returns:
            {
                'required_information_types': ['personal_identity', 'community_affiliation'],
                'target_brain_regions': ['temporal_lobe', 'hippocampus'],
                'question_intent': 'identity_query|factual_query|temporal_query|inference_query',
                'confidence': 0.0-1.0
            }
        """

        # 检查缓存
        cache_key = query.lower().strip()
        if cache_key in self.analysis_cache:
            logger.debug(f"📦 Question analysis cache hit")
            return self.analysis_cache[cache_key]

        prompt = f"""Analyze what TYPE OF INFORMATION is needed to answer this question.

Question: {query}

Information Types (what information does this question ask for?):
- personal_identity: Who someone IS (their core identity, characteristics)
- community_affiliation: Which communities/groups someone belongs to or engages with
- educational_interest: Academic fields, subjects, or areas of study
- professional_interest: Career fields, job interests
- temporal_event: When something happened (dates, times)
- location_info: Where something is/was
- activity_info: What someone did (actions, activities)
- emotional_experience: How someone felt
- causal_relationship: Why something happened

Task: Identify what TYPE OF INFORMATION the question is asking for (not the answer itself).

Examples:
- "What is Caroline's identity?" → personal_identity
- "What community did Caroline engage with?" → community_affiliation
- "What fields would Caroline pursue?" → educational_interest
- "When did Caroline go?" → temporal_event
- "What did Caroline research?" → activity_info

Important: Focus on WHAT TYPE OF INFO is being asked, not specific keywords.

Output JSON:
{{
    "required_information_types": ["type1", "type2"],
    "question_intent": "identity_query|factual_query|temporal_query|inference_query",
    "reasoning": "why you identified these types",
    "confidence": 0.0-1.0
}}

Remember: Identify the INFORMATION TYPE needed, not the answer!"""

        try:
            response = await llm_caller(prompt, temperature=0.1, max_tokens=300)

            # Parse JSON
            if '```json' in response:
                response = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                response = response.split('```')[1].split('```')[0].strip()

            result = json.loads(response)

            # 推断target brain regions
            brain_regions = self._infer_target_brain_regions(result.get('required_information_types', []))
            result['target_brain_regions'] = brain_regions

            # 缓存结果
            if result.get('confidence', 0) >= 0.7:
                self.analysis_cache[cache_key] = result

            logger.debug(f"🧠 Question analysis: info_types={result.get('required_information_types')}, regions={brain_regions}")
            return result

        except Exception as e:
            logger.error(f"❌ Question analysis failed: {e}")
            # Fallback
            return {
                'required_information_types': ['temporal_event', 'activity_info'],
                'target_brain_regions': ['hippocampus'],
                'question_intent': 'factual_query',
                'confidence': 0.3
            }

    def _infer_target_brain_regions(self, information_types: List[str]) -> List[str]:
        """
        根据所需信息类型推断应该从哪些brain regions检索

        基于神经科学:
        - personal_identity, educational_interest → temporal_lobe (semantic memory)
        - temporal_event, activity_info → hippocampus (episodic memory)
        - community_affiliation → temporal_lobe + hippocampus
        - emotional_experience → amygdala
        """
        regions = set()

        type_to_regions = {
            'personal_identity': ['temporal_lobe', 'hippocampus'],
            'community_affiliation': ['temporal_lobe', 'hippocampus'],
            'educational_interest': ['temporal_lobe', 'prefrontal'],
            'professional_interest': ['temporal_lobe', 'prefrontal'],
            'temporal_event': ['hippocampus'],
            'location_info': ['hippocampus', 'parietal'],
            'activity_info': ['hippocampus'],
            'emotional_experience': ['amygdala', 'hippocampus'],
            'causal_relationship': ['prefrontal', 'hippocampus']
        }

        for info_type in information_types:
            if info_type in type_to_regions:
                regions.update(type_to_regions[info_type])

        # 如果没有匹配,默认hippocampus
        if not regions:
            regions.add('hippocampus')

        return list(regions)

    def should_use_semantic_filtering(self, question_analysis: Dict[str, Any]) -> bool:
        """
        判断是否应该使用semantic filtering

        如果question有明确的information type需求,应该filter
        """
        info_types = question_analysis.get('required_information_types', [])
        confidence = question_analysis.get('confidence', 0)

        # 只有当confidence高且有明确info type时才filter
        return confidence >= 0.7 and len(info_types) > 0
