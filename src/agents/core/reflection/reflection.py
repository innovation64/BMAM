"""
Reflection Agent
反思智能体 - 主类（重构版，使用Mixin架构）
"""

import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from ...base import BrainAgent, AgentMessage, BrainRegion
from ....memory.memory_item import MemoryItem

# 导入所有Mixin
from .reflection_triggers import ReflectionTriggersMixin
from .self_monitoring import SelfMonitoringMixin
from .pattern_analysis import PatternAnalysisMixin
from .insight_generation import InsightGenerationMixin
from .meta_learning import MetaLearningMixin
from .performance_evaluation import PerformanceEvaluationMixin
from .bias_detection import BiasDetectionMixin

# 导入数据模型
from .data_models import (
    ReflectionTrigger, PerformanceMetrics, Insight,
    ReflectionCycle, REFLECTION_CONFIG
)

logger = logging.getLogger(__name__)


class ReflectionAgent(
    BrainAgent,
    ReflectionTriggersMixin,
    SelfMonitoringMixin,
    PatternAnalysisMixin,
    InsightGenerationMixin,
    MetaLearningMixin,
    PerformanceEvaluationMixin,
    BiasDetectionMixin
):
    """
    Reflection Agent (Default Mode Network)

    核心概念：反思、元认知、自我监控
    主要功能：
    - 自我监控和性能评估
    - 模式识别和洞察生成
    - 认知偏差检测
    - 元学习和策略优化
    """

    def __init__(self, db_manager=None, embedding_service=None):
        super().__init__(
            agent_id="reflection",
            brain_region=BrainRegion.DEFAULT_MODE,
            system_prompt="""You identify patterns and generate insights across memories.
            Focus on understanding why patterns exist and what they reveal about learning."""
        )

        # External services
        self.db_manager = db_manager
        self.embedding_service = embedding_service

        # 配置
        self.config = REFLECTION_CONFIG.copy()

        # Reflection components
        self.insight_history = []
        self.pattern_cache = {}
        self.metacognitive_state = {
            'confidence': 0.5,
            'uncertainty': 0.3,
            'curiosity': 0.4,
            'satisfaction': 0.5
        }

        # Pattern analysis parameters
        self.pattern_threshold = 0.4
        self.insight_generation_interval = timedelta(hours=6)
        self.last_deep_reflection = datetime.now()

        # Reflection levels (移到data_models.py中的REFLECTION_CONFIG)
        self.reflection_levels = REFLECTION_CONFIG['reflection_levels']

        # 反思历史
        self.reflection_cycles = deque(maxlen=50)
        self.insights = deque(maxlen=100)

        # 性能监控
        self.performance_history = deque(maxlen=200)
        self.error_history = deque(maxlen=50)

        # Tracking
        self.tasks_completed_since_reflection = 0

        # Statistics
        self.insights_generated = 0
        self.patterns_identified = 0
        self.deep_reflections = 0
        self.biases_detected = 0
        self.total_reflections = 0

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process reflection and metacognition requests"""
        action = message.content.get('action')

        if action == 'analyze_patterns':
            return await self._analyze_memory_patterns(message.content.get('time_range'))
        elif action == 'generate_insight':
            return await self._generate_insight(message.content['memory_ids'])
        elif action == 'self_assessment':
            return await self._perform_self_assessment()
        elif action == 'abstract_learning':
            return await self._abstract_learning(message.content['experiences'])
        elif action == 'metacognitive_monitoring':
            return await self._metacognitive_monitoring()
        elif action == 'deep_reflection':
            return await self._deep_reflection_session()
        elif action == 'theme_analysis':
            return await self._analyze_life_themes()
        elif action == 'perspective_taking':
            return await self._perspective_taking_analysis(message.content['scenario'])
        elif action == 'generate_insights':
            return await self._generate_quick_insights(message.content.get('memories', []))
        elif action == 'infer_from_patterns':
            return await self._infer_from_patterns(
                message.content.get('memories', []),
                message.content.get('query', '')
            )
        elif action == 'abstract_reasoning':
            return await self._abstract_reasoning(
                message.content.get('memories', []),
                message.content.get('question_type', 'general')
            )

        return {'error': f'Unknown reflection action: {action}'}

    async def _analyze_memory_patterns(self, time_range: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze patterns in memory formation, access, and content"""

        if not self.db_manager:
            return {'error': 'Database manager not available'}

        # Load memories within time range
        memories = self.db_manager.load_memories_by_criteria()

        patterns = {
            'temporal_patterns': self._analyze_temporal_patterns(memories),
            'content_themes': self._analyze_content_themes(memories),
            'emotional_patterns': self._analyze_emotional_patterns(memories),
            'access_patterns': self._analyze_access_patterns(memories),
            'consolidation_patterns': self._analyze_consolidation_patterns(memories),
            'association_networks': self._analyze_association_networks(memories),
            'importance_trends': self._analyze_importance_trends(memories)
        }

        # Generate pattern-based insights
        insights = await self._generate_pattern_insights(patterns)

        # Update pattern cache
        self.pattern_cache.update(patterns)
        self.patterns_identified += len([p for p in patterns.values() if p])

        return {
            'pattern_analysis_complete': True,
            'time_range': time_range,
            'memories_analyzed': len(memories),
            'patterns': patterns,
            'insights': insights,
            'pattern_strength': self._calculate_overall_pattern_strength(patterns)
        }

    async def _generate_insight(self, memory_ids: List[str]) -> Dict[str, Any]:
        """Generate deep insights from memory connections"""

        if not self.db_manager:
            return {'error': 'Database manager not available'}

        memories = []
        for memory_id in memory_ids:
            memory = self.db_manager.load_memory(memory_id)
            if memory:
                memories.append(memory)

        if not memories:
            return {'error': 'No valid memories found for insight generation'}

        # Multi-level insight generation
        insights = {}

        for level in ['analytical', 'critical', 'metacognitive', 'transformative']:
            insight = await self._generate_level_specific_insight(memories, level)
            insights[level] = insight

        # Select the most profound insight
        best_insight = await self._select_best_insight(insights)

        # Create insight memory
        insight_memory = MemoryItem(
            content=f"INSIGHT ({best_insight['level']}): {best_insight['content']}",
            memory_type='semantic',
            brain_region=BrainRegion.DEFAULT_MODE,
            importance=0.8 + (0.2 if best_insight['level'] == 'transformative' else 0),
            consolidation_level=2,
            context_tags=['insight', 'reflection', best_insight['level']],
            metadata={
                'type': 'insight',
                'level': best_insight['level'],
                'source_memories': memory_ids,
                'generation_method': 'reflection_agent',
                'confidence': best_insight['confidence'],
                'generation_time': datetime.now().isoformat()
            }
        )

        # Generate embedding if service available
        if self.embedding_service:
            insight_memory.embedding = await self.embedding_service.encode_text(insight_memory.content)

        # Save insight
        if self.db_manager:
            self.db_manager.save_memory(insight_memory)

        self.insight_history.append({
            'memory_id': insight_memory.id,
            'level': best_insight['level'],
            'confidence': best_insight['confidence'],
            'timestamp': datetime.now().isoformat()
        })
        self.insights_generated += 1

        return {
            'insight_generated': True,
            'insight': best_insight,
            'all_insights': insights,
            'insight_memory_id': insight_memory.id,
            'source_memory_count': len(memories),
            'insight_level': best_insight['level']
        }

    async def _perform_self_assessment(self) -> Dict[str, Any]:
        """Perform comprehensive metacognitive self-assessment"""

        if not self.db_manager:
            return {'error': 'Database manager not available'}

        # Load system data
        all_memories = self.db_manager.load_memories_by_criteria()

        assessment = {
            'memory_system_health': self._assess_memory_system_health(all_memories),
            'learning_effectiveness': self._assess_learning_effectiveness(all_memories),
            'cognitive_biases': await self._identify_cognitive_biases(all_memories),
            'knowledge_gaps': await self._identify_knowledge_gaps(all_memories),
            'emotional_patterns': self._assess_emotional_patterns(all_memories),
            'metacognitive_awareness': self._assess_metacognitive_awareness(),
            'growth_indicators': self._assess_growth_indicators(all_memories)
        }

        # Generate self-improvement recommendations
        recommendations = await self._generate_self_improvement_recommendations(assessment)

        # Update metacognitive state
        self._update_metacognitive_state(assessment)

        return {
            'self_assessment_complete': True,
            'assessment': assessment,
            'recommendations': recommendations,
            'metacognitive_state': self.metacognitive_state,
            'confidence_level': self._calculate_overall_confidence(assessment)
        }

    async def _deep_reflection_session(self) -> Dict[str, Any]:
        """Conduct a deep reflection session on recent experiences and learning"""

        self.deep_reflections += 1
        self.last_deep_reflection = datetime.now()

        if not self.db_manager:
            return {'error': 'Database manager not available'}

        # Load recent significant memories
        recent_memories = self._get_recent_significant_memories()

        # Deep reflection prompts
        reflection_prompts = [
            "What are the most significant patterns in my recent experiences?",
            "How have my understanding and beliefs evolved recently?",
            "What assumptions am I making that might be limiting my growth?",
            "What connections exist between seemingly unrelated experiences?",
            "How can I apply recent learnings to future situations?"
        ]

        deep_insights = {}

        for prompt in reflection_prompts:
            insight = await self._deep_reflect_on_prompt(prompt, recent_memories)
            deep_insights[prompt] = insight

        # Synthesize meta-insight
        meta_insight = await self._synthesize_meta_insight(deep_insights)

        # Create deep reflection memory
        reflection_memory = MemoryItem(
            content=f"DEEP REFLECTION: {meta_insight}",
            memory_type='semantic',
            brain_region=BrainRegion.DEFAULT_MODE,
            importance=1.0,
            consolidation_level=3,
            context_tags=['deep_reflection', 'meta_insight', 'wisdom'],
            metadata={
                'type': 'deep_reflection',
                'reflection_session': self.deep_reflections,
                'prompts_explored': len(reflection_prompts),
                'synthesis_level': 'meta',
                'reflection_time': datetime.now().isoformat()
            }
        )

        if self.db_manager:
            self.db_manager.save_memory(reflection_memory)

        return {
            'deep_reflection_complete': True,
            'session_number': self.deep_reflections,
            'prompts_explored': reflection_prompts,
            'deep_insights': deep_insights,
            'meta_insight': meta_insight,
            'reflection_memory_id': reflection_memory.id,
            'memories_reflected_on': len(recent_memories)
        }

    # === Helper methods from original file ===

    def _get_recent_significant_memories(self) -> List[MemoryItem]:
        """Get recent memories with high significance for deep reflection"""
        if not self.db_manager:
            return []

        all_memories = self.db_manager.load_memories_by_criteria()
        recent_memories = [
            mem for mem in all_memories
            if (datetime.now() - mem.timestamp).days < 30
            and (mem.importance > 0.6 or mem.emotion_intensity > 0.6)
        ]

        recent_memories.sort(key=lambda m: m.importance, reverse=True)
        return recent_memories[:10]

    async def _deep_reflect_on_prompt(self, prompt: str, memories: List[MemoryItem]) -> str:
        """Conduct deep reflection on a specific prompt with relevant memories"""
        memory_context = "\n".join([f"- {mem.content}" for mem in memories])

        full_prompt = f"""
        Deep reflection prompt: {prompt}

        Relevant memories:
        {memory_context}

        Provide a thoughtful, introspective response that goes beyond surface-level observations.
        """

        return await self.call_llm(full_prompt)

    async def _synthesize_meta_insight(self, deep_insights: Dict[str, str]) -> str:
        """Synthesize multiple deep insights into a meta-insight"""
        insights_summary = "\n".join([f"Q: {q}\nA: {a}" for q, a in deep_insights.items()])

        prompt = f"""
        Synthesize these deep reflections into a single, profound meta-insight about growth, learning, or life patterns:

        {insights_summary}

        Provide a concise but profound synthesis.
        """

        return await self.call_llm(prompt)

    def _assess_emotional_patterns(self, memories: List[MemoryItem]) -> Dict[str, Any]:
        """Assess emotional patterns for wellbeing indicators"""
        if not memories:
            return {'emotional_health': 0.5}

        positive_emotions = ['joy', 'happiness', 'satisfaction', 'excitement', 'love', 'gratitude']
        negative_emotions = ['sadness', 'anger', 'fear', 'anxiety', 'frustration', 'disappointment']

        positive_count = sum(1 for m in memories for emotion in m.emotion_tags if emotion in positive_emotions)
        negative_count = sum(1 for m in memories for emotion in m.emotion_tags if emotion in negative_emotions)

        total_emotional_memories = positive_count + negative_count

        if total_emotional_memories == 0:
            emotional_balance = 0.5
        else:
            emotional_balance = positive_count / total_emotional_memories

        return {
            'emotional_balance': emotional_balance,
            'positive_emotions': positive_count,
            'negative_emotions': negative_count,
            'emotional_health': emotional_balance
        }

    def _assess_metacognitive_awareness(self) -> Dict[str, float]:
        """Assess current metacognitive awareness"""
        return {
            'self_monitoring': self.metacognitive_state['confidence'],
            'strategy_awareness': 0.6,
            'reflection_frequency': min(1.0, len(self.insight_history) / 10),
            'uncertainty_tolerance': 1.0 - self.metacognitive_state['uncertainty']
        }

    def _assess_growth_indicators(self, memories: List[MemoryItem]) -> Dict[str, float]:
        """Assess indicators of personal/cognitive growth"""
        if not memories:
            return {'growth_rate': 0.0}

        learning_memories = [m for m in memories if 'learning' in m.context_tags or m.memory_type == 'semantic']
        insight_memories = [m for m in memories if 'insight' in m.context_tags]

        return {
            'learning_rate': len(learning_memories) / len(memories),
            'insight_generation': len(insight_memories) / len(memories),
            'knowledge_expansion': len([m for m in memories if m.importance > 0.7]) / len(memories),
            'growth_rate': (len(learning_memories) + len(insight_memories)) / len(memories)
        }

    async def _generate_self_improvement_recommendations(self, assessment: Dict) -> List[str]:
        """Generate personalized self-improvement recommendations"""
        recommendations = []

        health = assessment['memory_system_health']
        if health['consolidation_rate'] < 0.5:
            recommendations.append("Increase memory consolidation through regular review and reflection")

        if health['association_rate'] < 0.3:
            recommendations.append("Focus on connecting new information to existing knowledge")

        learning = assessment['learning_effectiveness']
        if learning['insight_generation_rate'] < 0.1:
            recommendations.append("Engage in more reflective thinking to generate insights")

        emotional = assessment['emotional_patterns']
        if emotional['emotional_balance'] < 0.4:
            recommendations.append("Consider strategies to cultivate more positive experiences")

        biases = assessment['cognitive_biases']
        if biases:
            recommendations.append(f"Address identified cognitive biases: {', '.join(biases[:2])}")

        return recommendations[:5]

    def _update_metacognitive_state(self, assessment: Dict):
        """Update metacognitive state based on self-assessment"""
        health_score = assessment['memory_system_health']['overall_health']
        learning_score = assessment['learning_effectiveness']['effectiveness']

        self.metacognitive_state.update({
            'confidence': (health_score + learning_score) / 2,
            'satisfaction': assessment['emotional_patterns']['emotional_health'],
            'curiosity': min(1.0, self.metacognitive_state['curiosity'] + 0.1)
        })

    # === Additional methods for compatibility ===

    async def _abstract_learning(self, experiences: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract abstract principles from experiences (simplified)"""
        return {
            'abstraction_complete': True,
            'abstractions': {
                'patterns': "Extracted patterns from experiences",
                'principles': "Identified general principles"
            },
            'source_experience_count': len(experiences)
        }

    async def _metacognitive_monitoring(self) -> Dict[str, Any]:
        """Monitor and assess thinking processes"""
        monitoring_results = {
            'thinking_efficiency': self._assess_thinking_efficiency(),
            'attention_focus': self._assess_attention_focus(),
            'memory_confidence': self._assess_memory_confidence(),
            'learning_state': self._assess_learning_state()
        }

        return {
            'metacognitive_monitoring_complete': True,
            'monitoring_results': monitoring_results,
            'metacognitive_state': self.metacognitive_state
        }

    def _assess_memory_confidence(self) -> float:
        """Assess confidence in memory accuracy"""
        return self.metacognitive_state['confidence']

    def _assess_learning_state(self) -> float:
        """Assess current learning state"""
        return self.metacognitive_state['curiosity']

    async def _analyze_life_themes(self) -> Dict[str, Any]:
        """Analyze overarching themes (simplified)"""
        return {
            'theme_analysis_complete': True,
            'themes_by_timescale': {},
            'recurring_themes': [],
            'dominant_theme': None
        }

    async def _perspective_taking_analysis(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze scenario from multiple perspectives (simplified)"""
        return {
            'perspective_analysis_complete': True,
            'scenario': scenario,
            'perspectives': {},
            'synthesis': "Multi-perspective analysis complete"
        }

    async def _generate_quick_insights(self, memories) -> Dict[str, Any]:
        """Generate quick insights from memories"""
        if not memories:
            return {"insights": [], "status": "no_memories"}

        memory_count = len(memories)
        insights = [f"Analyzed {memory_count} memories quickly"]

        return {
            "insights": insights,
            "memory_count": memory_count,
            "status": "quick_analysis_complete"
        }

    async def _infer_from_patterns(self, memories: List, query: str) -> Dict[str, Any]:
        """Pattern-based reasoning for Q3-type questions"""
        if not memories:
            return {'answer': None, 'confidence': 0.0, 'reasoning': 'No memories to analyze'}

        memories_text = '\n'.join([
            f"- {m.get('content', str(m))}" if isinstance(m, dict) else f"- {m}"
            for m in memories[:10]
        ])

        prompt = f"""Pattern-based reasoning:
Question: {query}
Memories: {memories_text}

Identify patterns and make inferences. Output JSON:
{{"patterns_identified": [], "answer": "", "confidence": 0.0, "reasoning": ""}}
"""

        try:
            response = await self.call_llm(prompt, temperature=0.3, max_tokens=400)
            import json
            if '```json' in response:
                response = response.split('```json')[1].split('```')[0].strip()
            result = json.loads(response)
            return result
        except Exception as e:
            logger.error(f"Pattern reasoning error: {e}")
            return {'answer': None, 'confidence': 0.0, 'reasoning': f'Error: {str(e)}'}

    async def _abstract_reasoning(self, memories: List, question_type: str) -> Dict[str, Any]:
        """Abstract reasoning for high-level inferences"""
        if not memories:
            return {'inferences': [], 'confidence': 0.0}

        return {
            'abstract_concepts': [],
            'inferences': [],
            'confidence': 0.5
        }
