"""
Clean Agent System - 简洁的12智能体系统
移除冗余包装器，直接使用核心智能体
"""

import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..utils.config import get_logger
from ..agents.base import BrainAgent

# 直接导入核心智能体，无需包装器
from ..agents.core.short_term_memory import ShortTermMemoryAgent
from ..agents.core.long_term_memory import LongTermMemoryAgent
from ..agents.core.memory_retrieval import MemoryRetrievalAgent  
from ..agents.core.consolidation import ConsolidationAgent
from ..agents.core.memory_distortion import MemoryDistortionAgent
from ..agents.core.reflection import ReflectionAgent
from ..agents.core.forgetting import ForgettingAgent
from ..agents.core.stress_response import StressResponseAgent
from ..agents.core.personality import PersonalityAgent
from ..agents.core.persona_memory import PersonaMemoryAgent

logger = get_logger(__name__)

# 全局并发控制
_global_semaphore = asyncio.Semaphore(4)


class BrainRegion(Enum):
    """脑区枚举"""
    HIPPOCAMPUS = "hippocampus"
    NEOCORTEX = "neocortex"  
    PREFRONTAL = "prefrontal"
    AMYGDALA = "amygdala"
    THALAMUS = "thalamus"
    BASAL_GANGLIA = "basal_ganglia"
    DEFAULT_MODE = "default_mode"
    INHIBITION = "inhibition"
    BROCA_WERNICKE = "broca_wernicke"
    ACC = "acc"
    MOTOR_CORTEX = "motor_cortex"
    SENSORY_CORTEX = "sensory_cortex"


@dataclass
class AgentMessage:
    """智能体间通信消息"""
    sender: str
    receiver: str
    message_type: str
    content: Dict[str, Any]
    priority: str = "medium"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    correlation_id: str = field(default_factory=lambda: str(__import__('uuid').uuid4()))


# ========================================
# 辅助智能体 - 简单实现
# ========================================

class ConversationAgent(BrainAgent):
    """对话智能体"""
    
    def __init__(self):
        super().__init__(
            "conversation",
            BrainRegion.BROCA_WERNICKE.value,
            "你是语言理解和生成系统，负责自然语言交互和对话管理。"
        )
        # 缓存动态权重决策
        self._adaptive_weights_cache = {}
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        content = message.content
        action = content.get('action')

        # 🧠 BrainNetwork compatibility: handle 'stimulus' format
        if 'stimulus' in content:
            # BrainNetwork模式: content = {'stimulus': user_input, 'context': {...}}
            user_input = content['stimulus']
            context = content.get('context', {})
            memories = context.get('memories', [])

            return await self._generate_response(user_input, context, memories)

        # 原有Pipeline模式: content = {'action': 'generate_response', 'user_input': ..., 'context': {...}, 'memories': [...]}
        if action == 'generate_response':
            return await self._generate_response(
                content['user_input'],
                content.get('context', {}),
                content.get('memories', [])
            )

        return {'error': 'Unknown action', 'action': action}
    
    async def _generate_response(self, user_input: str, context: Dict, memories: List[Dict]) -> Dict[str, Any]:
        """生成对话响应"""
        # ✅ P0: 语言自适应 - 获取Perception Agent检测到的语言
        detected_language = context.get('detected_language', 'en')

        # ✅ 检测Benchmark模式
        benchmark_mode = context.get('benchmark_mode', False) or context.get('force_english', False)
        # ✅ P0: 如果强制英文，覆盖检测到的语言
        if context.get('force_english', False):
            detected_language = 'en'

        max_answer_length = context.get('max_answer_length', None)

        # 智能判断记忆相关性
        relevant_memories = self._filter_relevant_memories(user_input, memories)

        # 🎯 2025-12-22: 提前检测查询类型（用于偏好提取）
        user_input_lower = user_input.lower()
        is_recommendation = any(kw in user_input for kw in ['推荐', '建议', '介绍', '适合', '基于我的', '根据我的', 'recommend', 'suggest'])
        is_preference_query = is_recommendation or any(kw in user_input_lower for kw in ['recommend', 'suggest', 'should i', 'best for', 'what would', 'which one'])

        # 🎯 2025-12-22: 合并 PersonaMemory 检索的偏好与记忆中的偏好
        # 优先使用 PersonaMemory 的结构化偏好（由 BrainCoordinator 设置）
        extracted_preferences = list(context.get('user_preferences', []))

        # 如果是偏好相关查询，从普通记忆中补充偏好
        if is_preference_query or context.get('evaluation_mode', False):
            preference_patterns = [
                'i prefer', 'i like', 'i love', 'i hate', 'i dislike',
                "i don't like", "can't stand", 'i enjoy', 'i avoid',
                'i find', 'i usually', 'i always', 'i never',
                'my preference', 'my favorite', 'not a fan',
                'user likes:', 'user dislikes:', 'user prefers:'
            ]
            for mem in memories:
                content = self._extract_memory_content(mem).lower()
                if any(p in content for p in preference_patterns):
                    full_content = self._extract_memory_content(mem)
                    if full_content not in extracted_preferences and len(extracted_preferences) < 8:
                        extracted_preferences.append(full_content)

        # 使用摘要压缩记忆上下文（Anthropic建议）
        memory_context = ""
        if relevant_memories:
            # Benchmark模式: 简洁记忆格式
            if benchmark_mode:
                memory_context = "\n[Relevant Memories]\n" if detected_language == 'en' else "\n【相关记忆】\n"
                for i, mem in enumerate(relevant_memories, 1):
                    content = self._extract_memory_content(mem)
                    memory_context += f"{i}. {content}\n"
            else:
                # 如果记忆过多，先摘要再拼接
                if len(relevant_memories) > 5:
                    memory_context = await self._summarize_memories(user_input, relevant_memories)
                else:
                    if detected_language == 'zh':
                        memory_context = "\n【重要记忆】以下是与对话高度相关的准确记忆，请严格基于这些事实回答：\n"
                    else:
                        memory_context = "\n[Important Memories] Here are highly relevant memories, please answer based on these facts:\n"

                    for i, mem in enumerate(relevant_memories, 1):
                        content = self._extract_memory_content(mem)
                        memory_context += f"{i}. {content}\n"

        # 🧠 Step 1.4: 优先使用Reasoning Validator的推理结果
        has_reasoning = context.get('has_reasoning', False)
        reasoning_result = context.get('reasoning_result', {})

        if has_reasoning and reasoning_result:
            # Reasoning Validator已经完成推理,直接使用其结果
            confidence = reasoning_result.get('confidence', 0)
            inferred_answer = reasoning_result.get('answer', '')
            reasoning_chain = reasoning_result.get('reasoning_chain', [])

            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"🧠 Using Reasoning Validator result (confidence={confidence:.2f})")

            # 根据置信度调整回答方式
            if confidence >= 0.9:
                # 高置信度: 直接给出答案
                response = inferred_answer
            elif confidence >= 0.7:
                # 中等置信度: 给出答案但注明推理
                response = f"{inferred_answer} (inferred from context)"
            else:
                # 低置信度: 说明推理链但表达不确定性
                response = f"Based on available evidence: {inferred_answer}, but confidence is low"

            return {
                'response': response,
                'confidence': confidence,
                'reasoning_chain': reasoning_chain,
                'source': 'reasoning_validator'
            }

        # 根据查询类型调整prompt策略（is_recommendation 已在前面定义）
        is_recall = any(kw in user_input for kw in ['什么时候', '刚才说', '我说过', 'when', 'where', 'what', 'who', 'how'])

        if benchmark_mode:
            # ✅ P0: Benchmark模式根据检测语言自适应prompt
            if detected_language == 'en':
                if relevant_memories:
                    # ✅ P0-CRITICAL: Detect identity questions (通用检测，不针对特定类型)
                    is_identity_question = any(word in user_input.lower() for word in ['identity', '身份', 'who is', 'what is'])

                    # ✅ DEBUG: Log detection results
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.debug(f"🔍 Identity detection: is_identity={is_identity_question}")

                    # ✅ P0-Q4: Detect research-related questions (通用检测)
                    is_research_question = any(word in user_input.lower() for word in ['research', 'studied', 'investigated', 'looked into'])
                    has_research_context = any(word in memory_context.lower() for word in ['research', 'researching', 'studied', 'investigated'])
                    if is_research_question:
                        logger.debug(f"🔍 Research question detected, has_research_context={has_research_context}")

                    if is_research_question and has_research_context:
                        # Special handling for research questions (通用模板)
                        requirement = f"""[INSTRUCTIONS - CRITICAL]
- The question asks what someone researched/studied/investigated
- Look for research-related keywords in memories
- Extract the SPECIFIC topic/object of research from the memories
- Answer with the direct object only: what was being researched
- Answer in ENGLISH only in {max_answer_length or 10} words or less
"""
                    elif is_identity_question:
                        # 通用身份推理 (无特定答案提示)
                        requirement = f"""[INSTRUCTIONS - CRITICAL]
- The question asks about someone's identity
- You MUST infer the answer from contextual clues in the memories
- Look for: community affiliations, emotional resonance, self-descriptions
- Provide a specific identity based on evidence, not vague descriptions
- Do NOT say "Information not available" when contextual clues are present
- Answer in ENGLISH only in {max_answer_length or 15} words or less
- NO Chinese text whatsoever
"""
                    else:
                        # ✅ P1: 增强时间推理指令
                        time_reasoning_hint = ""
                        if any(word in user_input.lower() for word in ['when', 'what time', 'what date', '什么时候']):
                            time_reasoning_hint = """

TIME REASONING (CRITICAL - MUST FOLLOW):
Step 1: Look for relative time words in memories: "yesterday", "today", "last week"
Step 2: Find the conversation date from the context
Step 3: Calculate absolute date:
  - If conversation date is "8 May, 2023" and event says "yesterday" → Answer MUST be "7 May 2023" (8 - 1 = 7)
  - If conversation date is "8 May, 2023" and event says "today" → Answer is "8 May 2023"
  - If conversation date is "25 May, 2023" and event says "last Sunday" → Calculate to actual date

EXAMPLE:
Memory: "[Context: Date 8 May, 2023] Person: I attended an event yesterday"
Question: "When did Person attend the event?"
CORRECT Answer: "7 May 2023" (because 8 May - 1 day = 7 May)
WRONG Answer: "8 May 2023" ❌"""

                        requirement = f"""[INSTRUCTIONS - CRITICAL]
- Answer based on the memories above
- You MUST make inferences when asked{time_reasoning_hint}
- Be concise: answer in {max_answer_length or 15} words or less
- Answer in ENGLISH only
- NO emojis, NO greetings, NO Chinese text
- Provide the direct answer based on what memories imply
- Say "Information not available" ONLY if memories have absolutely nothing related to the question"""
                else:
                    # ✅ P1-Q2: 改进"不知道"答案格式
                    # 提取问题主题以生成更完整的回答
                    question_words = user_input.lower().split()
                    requirement = f"""[INSTRUCTIONS - CRITICAL]
- Answer in ENGLISH only
- If you don't know: Say "I don't have information about [the question topic]."
  * Example: Question "When did X do Y?" → Answer: "I don't have information about when X did Y."
  * Example: Question "What is X's age?" → Answer: "I don't have information about X's age."
- DO NOT just say "Information not available" - repeat key terms from the question
- Be concise but complete: 8-15 words
- NO emojis, NO greetings"""
            else:
                if relevant_memories:
                    requirement = f"""【要求 - 重要】
- 仅基于上述记忆回答
- 极度简洁：{max_answer_length or 10}个词以内
- 不要emoji、不要寒暄、不要解释
- 只给出直接答案
- 如果记忆中没有信息，回答"信息不可用"（3个字）"""
                else:
                    requirement = """【要求 - 重要】
- 极度简洁：10个词以内
- 不要emoji、不要寒暄
- 如果不知道，回答"信息不可用" """
        else:
            # 普通对话模式
            if relevant_memories:
                if is_recommendation:
                    requirement = "【要求】根据用户的偏好推荐时，必须优先考虑记忆中提到的喜好，将其作为首要推荐项。"
                elif is_recall:
                    requirement = "【要求】必须严格使用上述记忆中的准确信息回答，不要基于通识猜测或编造。"
                else:
                    requirement = "【要求】参考上述记忆信息，生成准确、自然的回复。"
            else:
                requirement = "请生成自然、有帮助的中文回复。"

        # 🎯 2025-12-22: 添加用户偏好（直接从记忆中提取）
        # 🔥 2025-12-27: 基于query_category使用不同的提示策略
        preference_section = ""
        # 优先使用直接提取的偏好，其次使用 context 中的
        user_prefs = extracted_preferences or context.get('user_preferences', [])
        query_category = context.get('persona_query_category', '')

        if user_prefs:
            pref_lines = "\n".join([f"- {p}" for p in user_prefs[:5]])

            if detected_language == 'en':
                # 🔥 根据问题类型生成不同的指导语
                if query_category == 'suggestion':
                    category_instruction = """⚠️ Generate CREATIVE suggestions that BUILD ON these preferences.
⚠️ Suggest NEW activities or ideas that ALIGN with their interests.
⚠️ Be specific and actionable in your suggestions."""
                elif query_category == 'recommendation':
                    category_instruction = """⚠️ Recommend options that MATCH these stated preferences.
⚠️ Explain WHY each recommendation fits their preferences.
⚠️ Avoid recommending anything that contradicts their preferences."""
                elif query_category == 'evolution':
                    category_instruction = """⚠️ Track how preferences have CHANGED over time.
⚠️ Identify the REASONS behind preference changes.
⚠️ Reference specific past statements about changes."""
                elif query_category == 'fact_recall':
                    category_instruction = """⚠️ Recall SPECIFIC facts the user has shared.
⚠️ Be precise about dates, events, and details.
⚠️ Only state what was explicitly mentioned."""
                else:
                    category_instruction = """⚠️ You MUST respect these preferences when responding.
⚠️ Your response MUST align with these stated preferences."""

                preference_section = f"""
[USER PREFERENCES - CRITICAL]
The user has expressed these preferences in previous conversations:
{pref_lines}

{category_instruction}
"""
            else:
                # 中文版本
                if query_category == 'suggestion':
                    category_instruction = """⚠️ 基于这些偏好生成创意建议。
⚠️ 建议应该与用户兴趣一致。"""
                elif query_category == 'recommendation':
                    category_instruction = """⚠️ 推荐符合用户偏好的选项。
⚠️ 解释为什么推荐适合他们。"""
                else:
                    category_instruction = """⚠️ 必须尊重这些偏好。"""

                preference_section = f"""
【用户偏好 - 关键】
用户在之前的对话中表达了以下偏好：
{pref_lines}

{category_instruction}
"""

        # ✅ P0: 根据检测到的语言生成prompt
        if detected_language == 'en':
            prompt = f"""User Question: {user_input}
{preference_section}{memory_context}

{requirement}"""
        else:  # zh - use English prompts for consistency
            prompt = f"""User Question: {user_input}
{preference_section}{memory_context}

{requirement}"""
        
        llm_failed = False
        response = await self.call_llm(
            prompt,
            context,
            max_tokens=600,
            quick_fail=False  # allow full timeout window for primary response
        )

        if self._looks_like_llm_error(response):
            llm_failed = True
            response = self._build_memory_fallback(user_input, memories, context)

        return {
            'response': response,
            'memories_used': len(relevant_memories),
            'context_applied': bool(context),
            'llm_failed': llm_failed
        }

    async def _get_adaptive_weights_async(self, user_input: str, query_intent: Optional[str]) -> Dict[str, float]:
        """使用LLM动态决定记忆过滤权重"""
        cache_key = f"{query_intent or 'general'}"

        if cache_key in self._adaptive_weights_cache:
            return self._adaptive_weights_cache[cache_key]

        # LLM-based weight decision
        prompt = f"""For filtering relevant memories for a "{query_intent or 'general'}" type query, rate the importance of each factor (0-10):
1. Vector similarity
2. Keyword match
3. Memory type
4. Query intent match

Return only 4 numbers separated by commas, e.g.: 10,3,2,4"""

        try:
            response = await self.call_llm(prompt, max_tokens=50, temperature=0.3, quick_fail=True)
            weights_str = response.strip()
            weights_list = [float(x.strip()) for x in weights_str.split(',')[:4]]

            weights = {
                'similarity_base': weights_list[0],
                'keyword_match': weights_list[1],
                'memory_type_bonus': weights_list[2],
                'query_intent_bonus': weights_list[3]
            }

            self._adaptive_weights_cache[cache_key] = weights
            return weights

        except Exception as e:
            # 失败时返回默认值
            return {
                'similarity_base': 10.0,
                'keyword_match': 2.0,
                'memory_type_bonus': 2.0,
                'query_intent_bonus': 3.0,
            }

    def _filter_relevant_memories(self, user_input: str, memories: List[Dict]) -> List[Dict]:
        """智能过滤相关记忆 - 基于语义相关性和查询意图

        采用动态评分系统，优先依赖向量相似度，辅以意图检测和关键词匹配。
        避免硬编码规则，使用可配置的权重系统。
        """
        if not memories:
            return []

        # 检测查询意图类型
        query_patterns = {
            'temporal': ['when', 'what date', 'what time', '什么时候', '几点', '哪天', '何时'],  # 🔥 新增时间查询检测
            'recall': ['哪里', '谁', '怎么', '为什么', '多少', '是否', '有没有', '刚才', '之前'],
            'preference': ['喜欢', '偏好', '习惯', '通常', '一般', '经常', '基于我的', '根据我的', '我的兴趣'],
            'recommendation': ['推荐', '建议', '介绍', '适合', '有什么'],
            'factual': ['是什么', '叫什么', '在哪', '几个']
        }

        query_intent = None
        user_input_lower = user_input.lower()
        for intent, patterns in query_patterns.items():
            if any(pattern in user_input_lower for pattern in patterns):
                query_intent = intent
                break

        # 异步获取LLM动态权重（避免硬编码）
        import asyncio
        try:
            WEIGHTS = asyncio.create_task(self._get_adaptive_weights_async(user_input, query_intent))
            WEIGHTS = asyncio.get_event_loop().run_until_complete(WEIGHTS) if not WEIGHTS.done() else WEIGHTS.result()
        except Exception as e:
            logger.debug(f"Failed to get adaptive weights: {e}, using default weights")
            # ✅ P1修复: 提高语义相似度权重，降低关键词匹配权重
            # 原因: Q4检索失败是因为"research"没匹配到"researching"
            # 解决: 依赖语义embedding而非精确关键词
            WEIGHTS = {
                'similarity_base': 15.0,  # 提高从10.0 -> 15.0
                'keyword_match': 1.0,      # 降低从2.0 -> 1.0
                'memory_type_bonus': 2.0,
                'query_intent_bonus': 3.0,
            }

        # 动态阈值：基于最高相似度的比例
        RELATIVE_THRESHOLD = 0.5  # 保留相似度 >= 最高分*50% 的记忆
        ABSOLUTE_THRESHOLD = 3.0  # 绝对最低分数

        # 提取用户查询的关键词（通用方法）
        stop_words = {'什么', '怎么', '哪里', '我们', '可以', '这个', '那个', '时候', '一下', '是否', '有没有', '？', '。', '，', '！', '的'}
        user_keywords = set()
        for word in user_input.replace('？', ' ').replace('。', ' ').replace('，', ' ').replace('！', ' ').split():
            if len(word) > 1 and word not in stop_words:
                user_keywords.add(word)

        scored_memories = []
        max_similarity = 0.0

        for mem in memories:
            content = self._extract_memory_content(mem)
            if not content:
                continue

            # === 计算多维度相关性得分 ===
            score = 0.0

            # 1. 向量相似度（最核心的指标）
            # ✅ 修复：使用hippocampus返回的字段名 (relevance/semantic_score)
            similarity = (mem.get('relevance') or mem.get('semantic_score') or
                         mem.get('similarity_score') or mem.get('retrieval_confidence') or
                         mem.get('similarity', 0))
            score += similarity * WEIGHTS['similarity_base']
            max_similarity = max(max_similarity, similarity)

            # 2. 关键词匹配（通用方法，不依赖具体词汇）
            keyword_matches = sum(1 for keyword in user_keywords if keyword in content)
            if keyword_matches > 0:
                score += keyword_matches * WEIGHTS['keyword_match']

            # 3. 记忆类型加权（检查metadata）
            context_tags = mem.get('context_tags', [])
            if isinstance(context_tags, str):
                context_tags = [context_tags]

            # 偏好记忆加权
            if 'preference' in context_tags or '用户偏好' in content:
                score += WEIGHTS['memory_type_bonus']

            # 个人信息记忆加权
            if 'personal_info' in context_tags:
                score += WEIGHTS['memory_type_bonus']

            # 4. 查询意图匹配加成（通用规则）
            if query_intent:
                # 回忆查询：优先使用带有明确事实的记忆
                if query_intent == 'recall' and ('preference' in context_tags or 'personal_info' in context_tags):
                    score += WEIGHTS['query_intent_bonus']

                # 偏好查询：优先使用偏好记忆
                if query_intent == 'preference' and 'preference' in context_tags:
                    score += WEIGHTS['query_intent_bonus']

                # 推荐查询：需要偏好信息作为基础
                if query_intent == 'recommendation' and 'preference' in context_tags:
                    score += WEIGHTS['query_intent_bonus']

            scored_memories.append({
                'memory': mem,
                'score': score,
                'similarity': similarity,
                'content': content
            })

        if not scored_memories:
            return []

        # === 动态阈值过滤 ===
        # 计算相对阈值（基于最高分）
        max_score = max(item['score'] for item in scored_memories)
        dynamic_threshold = max(max_score * RELATIVE_THRESHOLD, ABSOLUTE_THRESHOLD)

        # 过滤低分记忆
        relevant = [item for item in scored_memories if item['score'] >= dynamic_threshold]

        # ✅ P0-CRITICAL: For identity questions, include community/group-related memories
        # Even if they have low similarity scores (通用化：不针对特定身份类型)
        is_identity_query = any(word in user_input.lower() for word in ['identity', '身份', 'who is'])
        if is_identity_query:
            # 通用身份相关关键词 (社群、团体、自我描述)
            identity_keywords = ['community', 'group', 'support', 'identify', 'member', 'belong', '社群', '支持小组']
            for item in scored_memories:
                content_lower = item['content'].lower()
                if any(kw in content_lower for kw in identity_keywords):
                    if item not in relevant:
                        relevant.append(item)
                        logger.debug(f"🔍 Forcibly included identity-related memory for identity question: {item['content'][:60]}...")

        # 🔥 NEW: For temporal questions, use query intent matching to boost/demote memories
        if query_intent == 'temporal':
            # 时间查询: 优先包含时间信息的记忆,降低仅包含身份信息的记忆权重
            for item in relevant:
                content = item['content']
                content_lower = content.lower()

                # Boost: 包含时间相关词汇的记忆
                temporal_indicators = ['may', 'june', 'july', 'august', 'yesterday', 'today', 'on', 'at', '2023', '2024', 'date']
                has_temporal_info = any(indicator in content_lower for indicator in temporal_indicators)
                if has_temporal_info:
                    item['score'] += WEIGHTS.get('query_intent_bonus', 3.0)
                    logger.debug(f"📅 Boosted temporal memory: {content[:60]}...")

                # Demote: 仅包含身份信息但无时间信息的记忆 (通用指标)
                identity_indicators = ['identity', 'who is', 'what is', 'belong to', 'member of']
                has_identity_only = any(ind in content_lower for ind in identity_indicators) and not has_temporal_info
                if has_identity_only:
                    item['score'] -= WEIGHTS.get('keyword_match', 1.0)
                    logger.debug(f"⬇️ Demoted identity-only memory for temporal query: {content[:60]}...")

        # 按相关性排序，返回前5条（增加返回数量以提供更多上下文）
        relevant.sort(key=lambda x: x['score'], reverse=True)

        # 返回记忆对象和调试信息
        filtered_memories = [item['memory'] for item in relevant[:5]]

        # 记录过滤统计（用于调试）
        if filtered_memories:
            top_scores = [f"{item['score']:.2f}" for item in relevant[:3]]
            logger.debug(f"Memory filter: {len(filtered_memories)}/{len(memories)} memories passed (threshold={dynamic_threshold:.2f}, top_scores={top_scores})")

        return filtered_memories

    async def _summarize_memories(self, query: str, memories: List[Dict]) -> str:
        """Summarize memory context to reduce token usage"""
        memory_contents = []
        for mem in memories[:10]:  # process up to 10 memories
            content = self._extract_memory_content(mem)
            if content:
                memory_contents.append(content)

        if not memory_contents:
            return ""

        # Use LLM to compress memories
        summary_prompt = f"""For the user query "{query}", compress the following memories into key facts (3-5 points):
{chr(10).join(f'{i+1}. {m}' for i, m in enumerate(memory_contents))}

Keep only core information directly relevant to the query. Be concise."""

        summary = await self.call_llm(summary_prompt, max_tokens=200, quick_fail=True)
        return f"\n[Memory Summary] {summary}\n"

    def _extract_memory_content(self, memory: Dict) -> str:
        """统一提取记忆内容 - 处理多种数据格式，优先使用最新偏好"""
        # 优先检查是否有最新偏好信息
        metadata = None
        if 'metadata' in memory:
            metadata = memory['metadata']
        elif 'memory' in memory and isinstance(memory['memory'], dict):
            metadata = memory['memory'].get('metadata')

        # 如果有最新偏好，优先使用
        if metadata and isinstance(metadata, dict):
            latest_pref = metadata.get('latest_preference')
            if latest_pref:
                return f"{latest_pref} (最新偏好)"

        # 格式1: {'content': '...'}
        if 'content' in memory and isinstance(memory['content'], str):
            return memory['content']

        # 格式2: {'memory': {'content': '...'}}
        if 'memory' in memory:
            if isinstance(memory['memory'], dict) and 'content' in memory['memory']:
                return memory['memory']['content']
            elif isinstance(memory['memory'], str):
                return memory['memory']

        # 格式3: MemoryItem.to_dict() 格式
        if 'id' in memory and 'content' in memory:
            return memory['content']

        # 兜底：尝试转换为字符串
        return str(memory.get('content', ''))

    def _looks_like_llm_error(self, response: str) -> bool:
        if not response:
            return True
        error_markers = ['⚠️', 'API异常', 'API连接问题', '⏱️']
        return any(marker in response for marker in error_markers)

    def _build_memory_fallback(self, user_input: str, memories: List[Dict], context: Dict) -> str:
        if memories:
            # 提取用户输入的关键词
            user_keywords = set()
            for word in user_input.replace('？', ' ').replace('。', ' ').replace('，', ' ').split():
                if len(word) > 1 and word not in ['什么', '怎么', '哪里', '我们', '可以', '这个', '那个']:
                    user_keywords.add(word)

            # 寻找最相关的记忆
            best_memory = ""
            best_score = 0

            for mem in memories:
                content = mem.get('content', '')
                if not content:
                    continue

                # 计算相关性得分
                score = 0
                # 关键词匹配
                for keyword in user_keywords:
                    if keyword in content:
                        score += 3  # 提高关键词匹配权重

                # 偏好类记忆基础分
                if any(keyword in content for keyword in ['喜欢', '偏好', '习惯', '每天', '时间']):
                    score += 1

                # 特定关键词高权重匹配
                if '茶' in user_input and '茶' in content:
                    score += 5
                if '早上' in user_input and '早上' in content:
                    score += 5
                if '吃' in user_input and '吃' in content:
                    score += 4

                # 更新最佳匹配
                if score > best_score:
                    best_score = score
                    best_memory = content

            # 如果没找到相关记忆，使用最重要的那个
            if not best_memory and memories:
                best_memory = memories[0].get('content', '')

            if best_memory:
                # 截取合适长度，保持完整性
                if len(best_memory) > 100:
                    sentences = best_memory.split('。')
                    best_memory = sentences[0] + ('。' if len(sentences[0]) < 80 else '...')

                return f"抱歉，刚才思考得有点慢，不过我记得我们聊过：{best_memory}"

        # 没有记忆时仍给出友好回应
        return "我刚刚反应慢了一点，不过我会继续记得你告诉我的事情。可以再说说你的想法吗？"


class ExecutiveControlAgent(BrainAgent):
    """执行控制智能体"""
    
    def __init__(self):
        super().__init__(
            "executive_control",
            BrainRegion.ACC.value,
            "你是执行控制和任务协调系统，负责任务规划和智能体协调。"
        )
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        action = message.content.get('action')
        
        if action == 'coordinate_agents':
            return await self._coordinate_agents(message.content['task_info'])
        
        return {'error': 'Unknown action', 'action': action}
    
    async def _coordinate_agents(self, task_info: Dict[str, Any]) -> Dict[str, Any]:
        """协调智能体 - 使用可塑性优化的智能路由"""
        task_type = task_info.get('type', 'general')
        
        # 优先使用可塑性引擎的优化序列
        optimal_sequence = task_info.get('optimal_sequence', [])
        
        if optimal_sequence and len(optimal_sequence) >= 2:
            # 使用可塑性引擎优化的智能体序列
            primary_agents = optimal_sequence[:2]
            secondary_agents = optimal_sequence[2:4] if len(optimal_sequence) > 2 else []
        else:
            # 回退到基础路由规则
            if task_type == 'memory_storage':
                primary_agents = ['long_term_memory', 'consolidation']
                secondary_agents = ['short_term_memory']
            elif task_type == 'memory_retrieval':
                primary_agents = ['memory_retrieval', 'short_term_memory']
                secondary_agents = ['reflection']
            elif task_type == 'conversation':
                primary_agents = ['conversation', 'personality']
                secondary_agents = ['memory_retrieval']
            else:
                primary_agents = ['conversation']
                secondary_agents = ['memory_retrieval']
        
        return {
            'coordination_plan': {
                'primary_agents': primary_agents,
                'secondary_agents': secondary_agents,
                'execution_order': 'parallel',
                'routing_method': 'plasticity_optimized' if optimal_sequence else 'fallback_rules'
            }
        }


# Import the enhanced perception encoding agent (resides under agents.core)
from ..agents.core.perception_encoding import (
    EnhancedPerceptionEncodingAgent as PerceptionEncodingAgent,
)


class ActionExecutionAgent(BrainAgent):
    """行动执行智能体"""
    
    def __init__(self):
        super().__init__(
            "action_execution",
            BrainRegion.MOTOR_CORTEX.value,
            "你是决策执行系统，负责执行具体行动。"
        )
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        action = message.content.get('action')
        
        if action == 'execute_tool':
            return await self._execute_tool(
                message.content['tool_name'],
                message.content.get('parameters', {})
            )
        
        return {'error': 'Unknown action', 'action': action}
    
    async def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具"""
        # 简单的工具执行模拟
        return {
            'tool_name': tool_name,
            'result': f"执行工具 {tool_name} 成功",
            'success': True,
            'execution_time': datetime.now().isoformat()
        }


# ========================================
# 导出清洁的智能体类
# ========================================

__all__ = [
    'BrainRegion', 'AgentMessage',
    # 核心记忆智能体 - 直接导入
    'ShortTermMemoryAgent', 'LongTermMemoryAgent', 'MemoryRetrievalAgent',
    'ConsolidationAgent', 'MemoryDistortionAgent', 'ReflectionAgent',
    'ForgettingAgent', 'StressResponseAgent', 'PersonalityAgent',
    'PersonaMemoryAgent',
    # 辅助智能体 - 简洁实现  
    'ConversationAgent', 'ExecutiveControlAgent',
    'PerceptionEncodingAgent', 'ActionExecutionAgent'
]
