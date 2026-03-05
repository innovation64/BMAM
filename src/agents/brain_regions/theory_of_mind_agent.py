"""
Theory of Mind Agent - 心智理论智能体
对应脑区: 内侧前额叶皮层 (mPFC) + 颞顶联合区 (TPJ)
主要功能: 意图推断 + 欺骗检测 + 心理状态建模

核心设计:
1. 推断用户查询的真实意图
2. 检测对抗性/欺骗性问题
3. 建模对话中实体的心理状态
4. 提供推理验证支持

神经科学基础:
- mPFC: 自我-他人区分，心理状态归因
- TPJ: 视角转换，信念推理
- 与前额叶协作进行执行控制

Author: BMAM Team
Date: 2025-12-17
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
import asyncio

from ..base import BrainAgent, AgentMessage, BrainRegion

logger = logging.getLogger(__name__)


@dataclass
class IntentAnalysis:
    """意图分析结果"""
    surface_intent: str       # 表面意图 (字面含义)
    deep_intent: str          # 深层意图 (真实目的)
    confidence: float         # 置信度 (0.0-1.0)
    is_adversarial: bool      # 是否为对抗性问题
    adversarial_type: Optional[str] = None  # 对抗类型
    reasoning: str = ""       # 推理过程


@dataclass
class DeceptionDetection:
    """欺骗检测结果"""
    is_deceptive: bool        # 是否存在欺骗性
    deception_type: str       # 欺骗类型: presupposition_violation, false_premise, etc.
    confidence: float         # 置信度
    violated_facts: List[str] # 被违反的事实
    suggested_response: str   # 建议的回应策略


@dataclass
class MentalState:
    """心理状态模型"""
    entity: str               # 实体名称
    beliefs: List[str]        # 信念列表
    desires: List[str]        # 欲望/目标列表
    intentions: List[str]     # 意图列表
    emotions: List[str]       # 情绪状态
    knowledge_gaps: List[str] # 知识缺口
    timestamp: datetime = field(default_factory=datetime.now)


# 🔥 2025-12-19: P1 心智理论深化 - Mental Model Table
@dataclass
class MentalModelEntry:
    """心智模型条目 - 记录他人的信念/目标/恐惧"""
    who: str                  # 谁 (实体名称)
    entry_type: str           # 类型: 'want', 'fear', 'believe', 'prefer', 'dislike'
    content: str              # 内容
    source_memory_id: str     # 来源记忆ID
    confidence: float         # 置信度
    created_at: str           # 创建时间
    last_confirmed: str       # 最后确认时间

    def to_dict(self) -> Dict[str, Any]:
        return {
            'who': self.who,
            'entry_type': self.entry_type,
            'content': self.content,
            'source_memory_id': self.source_memory_id,
            'confidence': self.confidence,
            'created_at': self.created_at,
            'last_confirmed': self.last_confirmed
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MentalModelEntry':
        return cls(
            who=data['who'],
            entry_type=data['entry_type'],
            content=data['content'],
            source_memory_id=data.get('source_memory_id', ''),
            confidence=data.get('confidence', 0.5),
            created_at=data.get('created_at', datetime.now().isoformat()),
            last_confirmed=data.get('last_confirmed', datetime.now().isoformat())
        )


class TheoryOfMindAgent(BrainAgent):
    """
    心智理论智能体 - 意图推断 + 欺骗检测 + 心理状态建模

    核心功能:
    1. infer_intent(): 推断查询的真实意图
    2. detect_deception(): 检测对抗性/欺骗性问题
    3. model_mental_state(): 建模实体心理状态
    4. validate_presupposition(): 验证问题预设
    """

    # 常见对抗性问题模式
    ADVERSARIAL_PATTERNS = {
        'false_premise': [
            'did .* with .* sister',
            'did .* attend .* with .* brother',
            'when did .* meet .* cousin',
            'how many times did .* call .* aunt',
        ],
        'presupposition_violation': [
            'when did .* stop',
            'why did .* leave',
            'how did .* feel when .* died',
        ],
        'negation_trap': [
            'isn\'t it true that',
            'didn\'t .* say that',
            'wasn\'t .* supposed to',
        ],
        'temporal_confusion': [
            'before .* was born',
            'after .* died',
            'during .* childhood .* adult event',
        ]
    }

    def __init__(self, client=None):
        super().__init__(
            agent_id="theory_of_mind",
            brain_region="medial_prefrontal",  # mPFC
            system_prompt="""You are the Theory of Mind agent, responsible for understanding intentions,
            detecting deception, and modeling mental states.

            Your capabilities:
            1. Infer the TRUE intent behind queries (not just surface meaning)
            2. Detect adversarial/deceptive questions that contain false premises
            3. Model the beliefs, desires, and intentions of entities in conversations
            4. Validate presuppositions in questions against known facts

            You help the system avoid being tricked by carefully analyzing queries.""",
            client=client
        )

        # 缓存
        self.intent_cache: Dict[str, IntentAnalysis] = {}
        self.mental_state_cache: Dict[str, MentalState] = {}

        # 已知实体关系 (从记忆中构建)
        self.known_relationships: Dict[str, Dict[str, List[str]]] = {}

        # 🔥 2025-12-19: P1 心智理论深化 - Mental Model Table
        self.mental_model_table: Dict[str, List[MentalModelEntry]] = {}  # who -> entries

        # 统计
        self.total_analyses = 0
        self.deceptions_detected = 0
        self.adversarial_detected = 0

        # 状态持久化
        from src.utils.paths import BMAMPaths
        self.state_file = BMAMPaths.DATA_DIR / 'tom_state.json'
        self._load_state()

        logger.info("✅ TheoryOfMindAgent initialized")

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """处理来自其他脑区的消息"""
        content = message.content
        action = content.get('action', '')

        if action == 'infer_intent':
            result = await self.infer_intent(
                query=content.get('query', ''),
                context=content.get('context', [])
            )
            return {'intent_analysis': result.__dict__}

        elif action == 'detect_deception':
            result = await self.detect_deception(
                query=content.get('query', ''),
                known_facts=content.get('facts', [])
            )
            return {'deception_detection': result.__dict__}

        elif action == 'model_mental_state':
            result = await self.model_mental_state(
                entity=content.get('entity', ''),
                events=content.get('events', [])
            )
            return {'mental_state': result.__dict__}

        return {'error': f'Unknown action: {action}'}

    async def infer_intent(self, query: str, context: List[str] = None) -> IntentAnalysis:
        """
        推断用户查询的真实意图

        Args:
            query: 用户查询
            context: 上下文信息

        Returns:
            IntentAnalysis: 意图分析结果
        """
        self.total_analyses += 1

        # 检查缓存
        cache_key = query.lower().strip()
        if cache_key in self.intent_cache:
            return self.intent_cache[cache_key]

        # 先做简单的模式匹配检测
        is_adversarial, adv_type = self._pattern_based_adversarial_check(query)

        # LLM 深度分析
        context_str = '\n'.join(context) if context else 'No additional context'

        prompt = f"""Analyze the TRUE INTENT behind this query.

Query: "{query}"
Context: {context_str}

Consider:
1. What is the SURFACE intent (literal question)?
2. What is the DEEP intent (what does the user REALLY want to know)?
3. Is this query potentially ADVERSARIAL (designed to trick the system)?
   - False premise: assumes something that isn't true
   - Presupposition violation: assumes an event happened that didn't
   - Negation trap: uses negative framing to confuse
   - Temporal confusion: asks about impossible time sequences

Output JSON:
{{
    "surface_intent": "what the question literally asks",
    "deep_intent": "what the user really wants to know",
    "confidence": 0.0-1.0,
    "is_adversarial": true/false,
    "adversarial_type": "false_premise|presupposition_violation|negation_trap|temporal_confusion|none",
    "reasoning": "why you concluded this"
}}"""

        try:
            response = await self.call_llm(prompt, temperature=0.1, max_tokens=400)

            # Parse JSON
            if '```json' in response:
                response = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                response = response.split('```')[1].split('```')[0].strip()

            result = json.loads(response)

            # 合并模式检测结果
            if is_adversarial and not result.get('is_adversarial'):
                result['is_adversarial'] = True
                result['adversarial_type'] = adv_type

            analysis = IntentAnalysis(
                surface_intent=result.get('surface_intent', query),
                deep_intent=result.get('deep_intent', query),
                confidence=result.get('confidence', 0.5),
                is_adversarial=result.get('is_adversarial', False),
                adversarial_type=result.get('adversarial_type'),
                reasoning=result.get('reasoning', '')
            )

            if analysis.is_adversarial:
                self.adversarial_detected += 1
                logger.info(f"🎭 Adversarial query detected: {query[:50]}... type={analysis.adversarial_type}")

            # 缓存
            if analysis.confidence >= 0.7:
                self.intent_cache[cache_key] = analysis

            return analysis

        except Exception as e:
            logger.error(f"Intent inference failed: {e}")
            return IntentAnalysis(
                surface_intent=query,
                deep_intent=query,
                confidence=0.3,
                is_adversarial=is_adversarial,
                adversarial_type=adv_type,
                reasoning=f"Error: {e}"
            )

    async def detect_deception(self, query: str, known_facts: List[str]) -> DeceptionDetection:
        """
        检测查询中的欺骗性内容

        Args:
            query: 用户查询
            known_facts: 已知事实列表

        Returns:
            DeceptionDetection: 欺骗检测结果
        """
        facts_str = '\n'.join(f"- {f}" for f in known_facts) if known_facts else 'No facts provided'

        prompt = f"""Analyze if this query contains deceptive elements or false premises.

Query: "{query}"

Known Facts:
{facts_str}

Deception Types:
1. False Premise: Query assumes something that contradicts known facts
   Example: "Did X visit Y with their sister?" when X has no sister
2. Presupposition Violation: Query assumes an event that never happened
   Example: "When did X stop smoking?" when X never smoked
3. Entity Confusion: Query confuses or conflates different entities
4. Temporal Impossibility: Query asks about impossible time sequences

Task: Check if the query contains any assumptions that CONTRADICT the known facts.

Output JSON:
{{
    "is_deceptive": true/false,
    "deception_type": "false_premise|presupposition_violation|entity_confusion|temporal_impossibility|none",
    "confidence": 0.0-1.0,
    "violated_facts": ["list of facts that the query violates"],
    "suggested_response": "how to respond if deceptive (e.g., 'The question assumes X has a sister, but there is no evidence of this.')"
}}"""

        try:
            response = await self.call_llm(prompt, temperature=0.1, max_tokens=500)

            # Parse JSON
            if '```json' in response:
                response = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                response = response.split('```')[1].split('```')[0].strip()

            result = json.loads(response)

            detection = DeceptionDetection(
                is_deceptive=result.get('is_deceptive', False),
                deception_type=result.get('deception_type', 'none'),
                confidence=result.get('confidence', 0.5),
                violated_facts=result.get('violated_facts', []),
                suggested_response=result.get('suggested_response', '')
            )

            if detection.is_deceptive:
                self.deceptions_detected += 1
                logger.info(f"🚨 Deception detected in query: {query[:50]}... type={detection.deception_type}")

            return detection

        except Exception as e:
            logger.error(f"Deception detection failed: {e}")
            return DeceptionDetection(
                is_deceptive=False,
                deception_type='none',
                confidence=0.3,
                violated_facts=[],
                suggested_response=''
            )

    async def model_mental_state(self, entity: str, events: List[str]) -> MentalState:
        """
        建模实体的心理状态

        Args:
            entity: 实体名称
            events: 与实体相关的事件列表

        Returns:
            MentalState: 心理状态模型
        """
        # 检查缓存
        cache_key = f"{entity}_{len(events)}"
        if cache_key in self.mental_state_cache:
            return self.mental_state_cache[cache_key]

        events_str = '\n'.join(f"- {e}" for e in events) if events else 'No events provided'

        prompt = f"""Model the mental state of {entity} based on these events.

Events involving {entity}:
{events_str}

Task: Infer {entity}'s mental state including:
1. Beliefs: What does {entity} believe/know?
2. Desires: What does {entity} want/aspire to?
3. Intentions: What is {entity} planning/trying to do?
4. Emotions: What emotions might {entity} be experiencing?
5. Knowledge Gaps: What might {entity} NOT know?

Output JSON:
{{
    "beliefs": ["belief1", "belief2"],
    "desires": ["desire1", "desire2"],
    "intentions": ["intention1", "intention2"],
    "emotions": ["emotion1", "emotion2"],
    "knowledge_gaps": ["gap1", "gap2"]
}}"""

        try:
            response = await self.call_llm(prompt, temperature=0.3, max_tokens=500)

            # Parse JSON
            if '```json' in response:
                response = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                response = response.split('```')[1].split('```')[0].strip()

            result = json.loads(response)

            mental_state = MentalState(
                entity=entity,
                beliefs=result.get('beliefs', []),
                desires=result.get('desires', []),
                intentions=result.get('intentions', []),
                emotions=result.get('emotions', []),
                knowledge_gaps=result.get('knowledge_gaps', [])
            )

            # 缓存
            self.mental_state_cache[cache_key] = mental_state

            return mental_state

        except Exception as e:
            logger.error(f"Mental state modeling failed: {e}")
            return MentalState(
                entity=entity,
                beliefs=[],
                desires=[],
                intentions=[],
                emotions=[],
                knowledge_gaps=[]
            )

    async def validate_presupposition(self, query: str, memory_facts: List[str]) -> Tuple[bool, str]:
        """
        验证问题中的预设是否与记忆事实一致

        Args:
            query: 用户查询
            memory_facts: 从记忆中检索的事实

        Returns:
            (is_valid, explanation): 预设是否有效及解释
        """
        # 1. 使用 detect_deception 检测
        detection = await self.detect_deception(query, memory_facts)

        if detection.is_deceptive:
            return False, detection.suggested_response

        return True, "Presuppositions are consistent with known facts."

    async def get_adversarial_response_strategy(self, query: str, facts: List[str]) -> Dict[str, Any]:
        """
        获取对抗性问题的回应策略

        Args:
            query: 对抗性查询
            facts: 已知事实

        Returns:
            回应策略
        """
        intent = await self.infer_intent(query)

        if not intent.is_adversarial:
            return {
                'strategy': 'normal',
                'response_hint': None
            }

        detection = await self.detect_deception(query, facts)

        return {
            'strategy': 'adversarial_handling',
            'adversarial_type': intent.adversarial_type,
            'is_deceptive': detection.is_deceptive,
            'deception_type': detection.deception_type,
            'violated_facts': detection.violated_facts,
            'response_hint': detection.suggested_response or self._get_default_adversarial_response(intent.adversarial_type)
        }

    def _pattern_based_adversarial_check(self, query: str) -> Tuple[bool, Optional[str]]:
        """基于模式的快速对抗性检测"""
        import re
        query_lower = query.lower()

        for adv_type, patterns in self.ADVERSARIAL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return True, adv_type

        return False, None

    def _get_default_adversarial_response(self, adv_type: str) -> str:
        """获取默认的对抗性问题回应"""
        responses = {
            'false_premise': "The question contains an assumption that may not be supported by the available information.",
            'presupposition_violation': "The question assumes an event or situation that is not reflected in the known facts.",
            'negation_trap': "This question uses framing that could lead to a misleading answer. Let me clarify the actual facts.",
            'temporal_confusion': "The question refers to a time sequence that doesn't match the known timeline."
        }
        return responses.get(adv_type, "This question contains elements that require careful consideration of the known facts.")

    def build_relationship_index(self, memories: List[Dict[str, Any]]):
        """
        从记忆中构建实体关系索引

        Args:
            memories: 记忆列表
        """
        for memory in memories:
            content = memory.get('content', '')
            entities = memory.get('entities', [])

            # 简单提取关系 (可以用更复杂的NER+RE)
            for entity in entities:
                if entity not in self.known_relationships:
                    self.known_relationships[entity] = {
                        'family': [],
                        'friends': [],
                        'colleagues': [],
                        'activities': [],
                        'locations': []
                    }

                # 提取活动
                if 'activity' in memory.get('tags', []):
                    self.known_relationships[entity]['activities'].append(content[:100])

    # ============================================================================
    # 🔥 2025-12-19: P1 心智理论深化 - Mental Model & Perspective Taking
    # ============================================================================

    def record_mental_model_entry(
        self,
        who: str,
        entry_type: str,
        content: str,
        source_memory_id: str = "",
        confidence: float = 0.5
    ):
        """
        记录他人的信念/目标/恐惧到心智模型表

        Args:
            who: 实体名称 (e.g., "用户", "Alice", "Bob")
            entry_type: 类型 ('want', 'fear', 'believe', 'prefer', 'dislike')
            content: 内容 (e.g., "换一份更有挑战的工作")
            source_memory_id: 来源记忆ID
            confidence: 置信度

        Example:
            tom.record_mental_model_entry("用户", "want", "换一份更有挑战的工作", "mem_123")
            tom.record_mental_model_entry("Alice", "fear", "失去现在的朋友", "mem_456")
        """
        now = datetime.now().isoformat()

        entry = MentalModelEntry(
            who=who,
            entry_type=entry_type,
            content=content,
            source_memory_id=source_memory_id,
            confidence=confidence,
            created_at=now,
            last_confirmed=now
        )

        if who not in self.mental_model_table:
            self.mental_model_table[who] = []

        # 检查是否已存在相似条目
        for existing in self.mental_model_table[who]:
            if existing.entry_type == entry_type and existing.content.lower() == content.lower():
                # 更新置信度和确认时间
                existing.confidence = min(1.0, existing.confidence + 0.1)
                existing.last_confirmed = now
                logger.debug(f"🧠 Updated mental model: {who} {entry_type} '{content[:30]}...' (conf={existing.confidence:.2f})")
                self._save_state()
                return

        # 新增条目
        self.mental_model_table[who].append(entry)
        logger.info(f"🧠 Recorded mental model: {who} {entry_type} '{content[:30]}...'")
        self._save_state()

    async def extract_mental_model_from_text(
        self,
        text: str,
        entities: List[str] = None,
        memory_id: str = ""
    ) -> List[MentalModelEntry]:
        """
        从文本中提取心智模型条目

        Args:
            text: 文本内容
            entities: 相关实体列表
            memory_id: 来源记忆ID

        Returns:
            提取的心智模型条目列表
        """
        # 简单的关键词匹配
        patterns = {
            'want': ['想要', '希望', '想', 'want', 'hope', 'wish', '期待', '渴望'],
            'fear': ['害怕', '担心', '恐惧', 'fear', 'afraid', 'worry', '不安'],
            'believe': ['相信', '认为', '觉得', 'believe', 'think', '以为'],
            'prefer': ['喜欢', '偏好', 'prefer', 'like', 'love', '爱'],
            'dislike': ['不喜欢', '讨厌', 'dislike', 'hate', '厌恶']
        }

        extracted = []
        text_lower = text.lower()

        # 如果没有提供实体，尝试提取
        if not entities:
            entities = ['用户']  # 默认假设是用户

        for entity in entities:
            for entry_type, keywords in patterns.items():
                for kw in keywords:
                    if kw in text_lower:
                        # 提取关键词后面的内容作为 content
                        idx = text_lower.find(kw)
                        content_start = idx + len(kw)
                        # 取后面50个字符作为内容
                        content = text[content_start:content_start + 50].strip()
                        if content and len(content) > 3:
                            entry = MentalModelEntry(
                                who=entity,
                                entry_type=entry_type,
                                content=content,
                                source_memory_id=memory_id,
                                confidence=0.5,
                                created_at=datetime.now().isoformat(),
                                last_confirmed=datetime.now().isoformat()
                            )
                            extracted.append(entry)
                            self.record_mental_model_entry(
                                entity, entry_type, content, memory_id, 0.5
                            )
                            break  # 每种类型只取一个

        return extracted

    def get_mental_model(self, who: str) -> List[MentalModelEntry]:
        """获取某人的心智模型"""
        return self.mental_model_table.get(who, [])

    def get_mental_model_summary(self, who: str) -> Dict[str, List[str]]:
        """
        获取某人心智模型的摘要

        Returns:
            {
                'wants': ['...', '...'],
                'fears': ['...'],
                'beliefs': ['...'],
                'preferences': ['...']
            }
        """
        entries = self.get_mental_model(who)
        summary = {
            'wants': [],
            'fears': [],
            'beliefs': [],
            'preferences': [],
            'dislikes': []
        }

        for entry in entries:
            if entry.entry_type == 'want':
                summary['wants'].append(entry.content)
            elif entry.entry_type == 'fear':
                summary['fears'].append(entry.content)
            elif entry.entry_type == 'believe':
                summary['beliefs'].append(entry.content)
            elif entry.entry_type == 'prefer':
                summary['preferences'].append(entry.content)
            elif entry.entry_type == 'dislike':
                summary['dislikes'].append(entry.content)

        return summary

    async def generate_perspective_suggestion(
        self,
        who: str,
        topic: str,
        context: str = ""
    ) -> Dict[str, Any]:
        """
        生成"从对方角度..."的建议

        Args:
            who: 要模拟的人
            topic: 讨论的话题
            context: 上下文

        Returns:
            {
                'perspective': "从X的角度来看...",
                'might_feel': "X可能会觉得...",
                'suggestion': "建议...",
                'confidence': 0.5
            }
        """
        mental_model = self.get_mental_model_summary(who)

        # 构建已知信息
        known_info = []
        if mental_model['wants']:
            known_info.append(f"{who}想要: {', '.join(mental_model['wants'][:3])}")
        if mental_model['fears']:
            known_info.append(f"{who}担心: {', '.join(mental_model['fears'][:3])}")
        if mental_model['beliefs']:
            known_info.append(f"{who}相信: {', '.join(mental_model['beliefs'][:3])}")
        if mental_model['preferences']:
            known_info.append(f"{who}偏好: {', '.join(mental_model['preferences'][:3])}")

        known_str = '\n'.join(known_info) if known_info else f"没有关于{who}的已知信息"

        prompt = f"""基于以下关于 {who} 的心智模型，分析 {who} 对话题 "{topic}" 可能的看法。

已知的{who}的心智模型:
{known_str}

上下文: {context if context else '无额外上下文'}

请输出JSON:
{{
    "perspective": "从{who}的角度来看...(简短分析)",
    "might_feel": "{who}可能会觉得...(情感反应)",
    "suggestion": "建议...(如何与{who}沟通这个话题)",
    "confidence": 0.0-1.0 (基于已知信息的置信度)
}}"""

        try:
            response = await self.call_llm(prompt, temperature=0.3, max_tokens=300)

            if '```json' in response:
                response = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                response = response.split('```')[1].split('```')[0].strip()

            result = json.loads(response)

            # 如果没有已知信息，降低置信度
            if not known_info:
                result['confidence'] = min(result.get('confidence', 0.5), 0.3)
                result['perspective'] = f"[推测] {result.get('perspective', '')}"

            return result

        except Exception as e:
            logger.error(f"Perspective generation failed: {e}")
            return {
                'perspective': f"无法生成{who}的视角分析",
                'might_feel': "未知",
                'suggestion': "建议直接沟通以了解对方想法",
                'confidence': 0.2
            }

    def format_perspective_block(
        self,
        who: str,
        perspective_result: Dict[str, Any]
    ) -> str:
        """
        格式化"对方可能会觉得..."响应块

        Args:
            who: 被模拟的人
            perspective_result: generate_perspective_suggestion的结果

        Returns:
            格式化的文本块
        """
        parts = []

        perspective = perspective_result.get('perspective', '')
        might_feel = perspective_result.get('might_feel', '')
        confidence = perspective_result.get('confidence', 0.5)

        if confidence < 0.4:
            parts.append(f"**{who}的可能视角** (仅供参考，信息有限):")
        else:
            parts.append(f"**{who}的可能视角**:")

        if perspective:
            parts.append(f"  {perspective}")

        if might_feel:
            parts.append(f"  💭 {might_feel}")

        return '\n'.join(parts)

    def _load_state(self):
        """加载状态"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                self.total_analyses = state.get('total_analyses', 0)
                self.deceptions_detected = state.get('deceptions_detected', 0)
                self.adversarial_detected = state.get('adversarial_detected', 0)
                self.known_relationships = state.get('known_relationships', {})

                # 🔥 2025-12-19: 加载心智模型表
                mental_model_data = state.get('mental_model_table', {})
                self.mental_model_table = {}
                for who, entries_data in mental_model_data.items():
                    self.mental_model_table[who] = [
                        MentalModelEntry.from_dict(e) for e in entries_data
                    ]

                logger.debug(f"Loaded ToM state: {self.total_analyses} analyses, "
                           f"{len(self.mental_model_table)} entities in mental model")
        except Exception as e:
            logger.warning(f"Failed to load ToM state: {e}")

    def _save_state(self):
        """保存状态"""
        try:
            # 🔥 2025-12-19: 序列化心智模型表
            mental_model_data = {}
            for who, entries in self.mental_model_table.items():
                mental_model_data[who] = [e.to_dict() for e in entries]

            state = {
                'total_analyses': self.total_analyses,
                'deceptions_detected': self.deceptions_detected,
                'adversarial_detected': self.adversarial_detected,
                'known_relationships': self.known_relationships,
                'mental_model_table': mental_model_data  # 🔥 2025-12-19
            }
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save ToM state: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        total_mental_entries = sum(len(entries) for entries in self.mental_model_table.values())
        return {
            'total_analyses': self.total_analyses,
            'deceptions_detected': self.deceptions_detected,
            'adversarial_detected': self.adversarial_detected,
            'cache_size': len(self.intent_cache),
            'known_entities': len(self.known_relationships),
            'mental_model_entities': len(self.mental_model_table),
            'mental_model_entries': total_mental_entries
        }


# 全局单例
_tom_agent: Optional[TheoryOfMindAgent] = None

def get_theory_of_mind_agent() -> TheoryOfMindAgent:
    """获取 Theory of Mind Agent 单例"""
    global _tom_agent
    if _tom_agent is None:
        _tom_agent = TheoryOfMindAgent()
    return _tom_agent
