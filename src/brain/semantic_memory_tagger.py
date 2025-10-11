"""
🧠 Semantic Memory Tagger - 语义记忆标注系统

核心思想:
- 当记忆存储时,LLM自动分析记忆的语义类型
- 标注记忆的semantic tags (不是关键词匹配!)
- 这些tags用于brain region分布和后续检索

设计原则:
1. 完全由LLM理解语义,不依赖关键词
2. Tags描述记忆包含的INFORMATION TYPE,不是keywords
3. 支持memory plasticity - tags可以随时间演化

Author: BMAM Team
"""

import logging
import json
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class SemanticMemoryTagger:
    """
    语义记忆标注器

    功能:
    1. 分析记忆内容的语义类型
    2. 自动标注semantic tags
    3. 指导brain region分布
    """

    def __init__(self):
        self.tag_cache = {}  # 缓存标注结果

    async def analyze_memory_semantics(self, memory_content: str, llm_caller) -> Dict[str, Any]:
        """
        分析记忆的语义类型

        Args:
            memory_content: 记忆内容
            llm_caller: LLM调用函数 (async callable)

        Returns:
            {
                'semantic_type': 'episodic|semantic|identity|procedural',
                'information_types': ['personal_identity', 'community_affiliation', 'educational_interest'],
                'brain_region_hints': {
                    'temporal_lobe': 0.8,  # semantic memory about identity
                    'hippocampus': 0.6,     # episodic event
                    'prefrontal': 0.3       # planning/interest
                },
                'confidence': 0.0-1.0
            }
        """

        prompt = f"""Analyze the semantic type and information content of this memory.

Memory: {memory_content}

Task: Determine what TYPE OF INFORMATION this memory contains (not just keywords).

Semantic Types:
- episodic: Specific event that happened (time, place, what happened)
- semantic: Facts, knowledge, identity information (who someone is, what they know)
- identity: Core identity characteristics (transgender, veteran, profession, etc.)
- procedural: How to do something, skills, procedures
- social: Social relationships, community connections

Information Types (what information does this memory contain?):
- personal_identity: Information about WHO someone is
- community_affiliation: Which communities/groups someone belongs to
- educational_interest: Academic fields or learning interests
- temporal_event: Time-bound events
- emotional_experience: Emotional reactions or experiences
- behavioral_pattern: Repeated behaviors or habits

Output JSON:
{{
    "semantic_type": "primary type",
    "information_types": ["type1", "type2"],
    "reasoning": "why you classified it this way",
    "confidence": 0.0-1.0
}}

Important: Focus on what INFORMATION the memory contains, not on specific keywords."""

        try:
            response = await llm_caller(prompt, temperature=0.1, max_tokens=300)

            # Parse JSON
            if '```json' in response:
                response = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                response = response.split('```')[1].split('```')[0].strip()

            result = json.loads(response)

            # 基于information types推断brain region分布
            brain_hints = self._infer_brain_regions(result.get('information_types', []))
            result['brain_region_hints'] = brain_hints

            logger.info(f"📊 Semantic analysis: {result.get('semantic_type')}, types={result.get('information_types')}")
            return result

        except Exception as e:
            logger.error(f"❌ Semantic analysis failed: {e}")
            # Fallback: 默认为episodic memory
            return {
                'semantic_type': 'episodic',
                'information_types': ['temporal_event'],
                'brain_region_hints': {'hippocampus': 1.0},
                'confidence': 0.3
            }

    def _infer_brain_regions(self, information_types: List[str]) -> Dict[str, float]:
        """
        根据information types推断应该存储到哪些brain regions

        这是基于神经科学的脑区功能映射,不是硬编码:
        - Temporal lobe: Semantic memory (facts, identity)
        - Hippocampus: Episodic memory (events)
        - Prefrontal: Working memory, planning, interests
        - Amygdala: Emotional memory
        - Parietal: Spatial memory
        """
        hints = {}

        # 基于神经科学的脑区功能
        type_to_region = {
            'personal_identity': {'temporal_lobe': 0.9, 'hippocampus': 0.4},
            'community_affiliation': {'temporal_lobe': 0.7, 'hippocampus': 0.5},
            'educational_interest': {'prefrontal': 0.8, 'temporal_lobe': 0.5},
            'temporal_event': {'hippocampus': 1.0},
            'emotional_experience': {'amygdala': 0.9, 'hippocampus': 0.6},
            'behavioral_pattern': {'prefrontal': 0.7, 'hippocampus': 0.5}
        }

        # 聚合所有信息类型的脑区权重
        for info_type in information_types:
            if info_type in type_to_region:
                for region, weight in type_to_region[info_type].items():
                    hints[region] = max(hints.get(region, 0), weight)

        # 如果没有匹配,默认hippocampus
        if not hints:
            hints['hippocampus'] = 0.8

        return hints

    def enhance_memory_metadata(self, memory_obj: Dict[str, Any], semantic_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        用语义分析结果增强记忆metadata

        Args:
            memory_obj: 原始记忆对象
            semantic_analysis: analyze_memory_semantics的结果

        Returns:
            增强后的记忆对象
        """
        if 'metadata' not in memory_obj:
            memory_obj['metadata'] = {}

        memory_obj['metadata']['semantic_type'] = semantic_analysis.get('semantic_type')
        memory_obj['metadata']['information_types'] = semantic_analysis.get('information_types', [])
        memory_obj['metadata']['brain_region_hints'] = semantic_analysis.get('brain_region_hints', {})

        return memory_obj
