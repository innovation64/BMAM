"""
Temporal Reasoning Mixin
时间推理模块

🔥 V2.0 增强: StoryArc 时间线集成
- 优先从 StoryArc 直接查询事件时间
- 解决 Temporal 准确率问题 (35% → 70%+)
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# 🔥 V2.0: StoryArc 集成
try:
    from ....memory.story_arc import get_story_arc_manager, StoryArcManager
    STORY_ARC_AVAILABLE = True
except ImportError:
    STORY_ARC_AVAILABLE = False
    logger.warning("StoryArc not available, temporal reasoning will use fallback methods")


class TemporalReasoningMixin:
    """时间推理Mixin"""

    async def _try_metadata_based_reasoning(
        self,
        query: str,
        memories: List[Dict],
        memories_by_region: Optional[Dict]
    ) -> Optional[Dict[str, Any]]:
        """
        🔥 2025-12-12 修复: 基于查询内容相关性选择最佳记忆

        存储时 extract_event_time_from_content 已经把 "yesterday+08 May→07 May" 算好了，
        存在 metadata.event_time。这里需要找到与查询最相关的记忆。

        Returns:
            Dict with answer/confidence if metadata has event_time, None otherwise
        """
        from datetime import datetime

        # 收集所有带 event_time 的记忆
        candidates = []

        # 优先使用 memories_by_region 中的 hippocampus 记忆
        source_memories = memories
        if memories_by_region:
            hippocampus_mems = memories_by_region.get('hippocampus', [])
            if hippocampus_mems:
                source_memories = hippocampus_mems

        # 🔥 2025-12-12: 提取查询中的关键词用于相关性匹配
        query_lower = query.lower()
        # 通用停用词（问题词+冠词+助动词）
        stop_words = {'when', 'did', 'what', 'where', 'how', 'who', 'is', 'are', 'was', 'were',
                      'the', 'a', 'an', 'to', 'go', 'went', 'does', 'do', 'have', 'has', 'had'}
        # 保留原始分词顺序用于短语匹配
        query_tokens = [w for w in query_lower.split() if w not in stop_words and len(w) > 2]
        query_words_set = set(query_tokens)

        for mem in source_memories:
            # 提取 metadata
            if isinstance(mem, dict):
                metadata = mem.get('metadata', {})
                content = mem.get('content', '')
            else:
                metadata = getattr(mem, 'metadata', {}) or {}
                content = getattr(mem, 'content', '')

            event_time = metadata.get('event_time')
            if not event_time:
                continue

            # 解析 event_time
            try:
                if isinstance(event_time, str):
                    # 尝试多种格式
                    for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d', '%d %B %Y']:
                        try:
                            dt = datetime.strptime(event_time.split('.')[0], fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        continue
                elif isinstance(event_time, datetime):
                    dt = event_time
                else:
                    continue

                # 🔥 2026-04-03: 用 embedding 相似度替代关键词匹配
                # 关键词匹配无法区分 "Caroline went to LGBTQ group" vs
                # "Caroline gave a speech" — 都包含 "Caroline" 但是不同事件。
                # embedding 能捕捉语义区别。
                content_lower = content.lower()
                relevance_score = 0.0

                # 首先尝试 embedding 相似度（最准确）
                mem_embedding = None
                if isinstance(mem, dict):
                    mem_embedding = mem.get('embedding')
                    if not mem_embedding:
                        mem_embedding = (mem.get('metadata') or {}).get('embedding')
                else:
                    mem_embedding = getattr(mem, 'embedding', None)

                if mem_embedding and hasattr(self, '_query_embedding_cache'):
                    try:
                        import numpy as np
                        q_vec = np.array(self._query_embedding_cache)
                        m_vec = np.array(mem_embedding)
                        cos_sim = float(np.dot(q_vec, m_vec) / (np.linalg.norm(q_vec) * np.linalg.norm(m_vec) + 1e-8))
                        relevance_score = cos_sim * 10.0  # 归一化到和关键词分类似的尺度
                    except Exception:
                        pass

                # embedding 不可用时回退到关键词匹配
                if relevance_score == 0.0:
                    keyword_matches = sum(1 for w in query_words_set if w in content_lower)
                    phrase_bonus = 0
                    for phrase_len in [4, 3, 2]:
                        if len(query_tokens) >= phrase_len:
                            for i in range(len(query_tokens) - phrase_len + 1):
                                phrase = ' '.join(query_tokens[i:i+phrase_len])
                                if phrase in content_lower:
                                    phrase_bonus += phrase_len * 0.5
                    relevance_score = keyword_matches + phrase_bonus

                # 🔥 2025-12-27 FIX: 细粒度置信度映射（替代二元判断）
                # 问题：之前是1.0或0.0的二元判断，无法区分不同提取方法的可靠性
                # 修复：根据提取方法给予不同的置信度权重
                extraction_method = metadata.get('event_time_extraction', 'unknown')

                # 置信度映射表 - 基于提取方法的可靠性
                EXTRACTION_CONFIDENCE_MAP = {
                    'relative': 0.95,      # "3 days before X" - 最可靠，有明确相对关系
                    'absolute': 0.90,      # "May 15, 2023" - 明确日期
                    'inherited': 0.85,     # 从对话上下文继承 - 较可靠
                    'metadata': 0.80,      # 从元数据提取 - 可靠
                    'context_approximate': 0.50,  # 上下文近似推断 - 中等
                    'context': 0.45,       # 纯上下文推断 - 较低
                    'fallback': 0.30,      # 回退方法 - 低可靠性
                    'unknown': 0.20        # 未知方法 - 最低
                }
                extraction_confidence = EXTRACTION_CONFIDENCE_MAP.get(extraction_method, 0.20)

                candidates.append({
                    'event_time': dt,
                    'content': content,
                    'metadata': metadata,
                    'relevance_score': relevance_score,
                    'extraction_method': extraction_method,
                    'extraction_confidence': extraction_confidence
                })
            except Exception:
                continue

        if not candidates:
            return None

        # 🔥 2025-12-16: 排序优先级: extraction_confidence > relevance_score
        candidates.sort(key=lambda x: (x['extraction_confidence'], x['relevance_score']), reverse=True)
        best = candidates[0]

        logger.debug(f"📅 Best candidate: method={best['extraction_method']}, "
                    f"relevance={best['relevance_score']:.1f}, content='{best['content'][:50]}...'")

        # 🔥 2025-12-13 FIX: 提高相关性阈值，避免返回错误的默认日期
        # 问题：阈值1.0太低，导致"27 June 2023"被错误返回给43个不相关问题
        # 🔥 2025-12-25 REFIX: 阈值3.0太高，导致大量查询fallback到LLM且失败
        # StoryArc bug修复后，metadata应该更可靠，降低阈值到1.5
        if best['relevance_score'] < 1.5:
            logger.info(f"📅 Metadata reasoning: relevance too low ({best['relevance_score']:.1f} < 1.5), fallback to LLM")
            return None

        # 🔥 额外检查：确保内容中包含查询的核心动词/动作
        # 例如 "When did X go to Y" 需要内容包含 "go" 或 "went" 相关词
        action_words = ['go', 'went', 'attend', 'attended', 'visit', 'visited',
                        'join', 'joined', 'meet', 'met', 'start', 'started',
                        'participate', 'participated', 'sign', 'signed', 'apply', 'applied']
        query_lower = query.lower()
        content_lower = best['content'].lower()

        has_matching_action = False
        for action in action_words:
            if action in query_lower and action in content_lower:
                has_matching_action = True
                break

        # 如果查询包含动作词但内容不匹配，降低信心
        query_has_action = any(a in query_lower for a in action_words)
        if query_has_action and not has_matching_action and best['relevance_score'] < 5.0:
            logger.info(f"📅 Metadata reasoning: action word mismatch, fallback to LLM")
            return None

        formatted_date = best['event_time'].strftime('%d %B %Y')

        logger.info(f"📅 Metadata-based temporal reasoning: event_time={formatted_date}, "
                   f"relevance={best['relevance_score']:.1f}, content='{best['content'][:80]}...'")

        return {
            'answer': formatted_date,
            'confidence': min(0.95, 0.70 + best['relevance_score'] * 0.05),  # 相关性影响置信度
            'event_time': best['event_time'].isoformat(),
            'reasoning_chain': [
                f"从记忆 metadata.event_time 获取预计算的事件时间",
                f"相关性得分: {best['relevance_score']:.1f}",
                f"匹配内容: {best['content'][:100]}...",
                f"event_time: {best['event_time'].isoformat()}",
                f"格式化结果: {formatted_date}"
            ],
            'source': 'metadata_event_time'
        }

    async def _try_story_arc_reasoning(
        self,
        query: str
    ) -> Optional[Dict[str, Any]]:
        """
        🔥 V2.0: 从 StoryArc 时间线直接查询事件时间

        StoryArc 维护显式的事件时间线索引，可以直接回答:
        - "When did X go to museum?" → 直接查找 X 的 museum_visit 事件
        - "How long have X and Y been friends?" → 查找 friendship 事件，计算时长

        Returns:
            Dict with answer/confidence if StoryArc has relevant event, None otherwise
        """
        if not STORY_ARC_AVAILABLE:
            return None

        try:
            story_arc = get_story_arc_manager()

            # 提取查询中的实体和事件类型
            entities, event_keywords = self._extract_query_elements(query)

            if not entities:
                logger.debug("StoryArc: No entities extracted from query")
                return None

            # 检测是否是 duration 问题
            is_duration_query = any(kw in query.lower() for kw in [
                'how long', 'how many years', 'how many months', 'how many days',
                'duration', '多久', '多长时间'
            ])

            # 尝试每个实体
            for entity in entities:
                if is_duration_query:
                    # Duration 查询
                    duration_result = await story_arc.calculate_duration(
                        entity=entity,
                        reference=query,  # 使用完整查询作为参考
                        reference_date=None  # 使用当前日期
                    )
                    if duration_result:
                        return {
                            'answer': duration_result['duration'],
                            'confidence': duration_result['confidence'],
                            'event_time': duration_result['start_date'].isoformat(),
                            'reasoning_chain': [
                                f"🔥 StoryArc 直接查询",
                                f"实体: {entity}",
                                f"起始日期: {duration_result['start_date']}",
                                f"持续时间: {duration_result['duration']}"
                            ],
                            'source': 'story_arc_duration'
                        }
                else:
                    # 时间点查询
                    time_result = await story_arc.query_event_time(
                        entity=entity,
                        event_keywords=event_keywords,
                        time_hint=None
                    )
                    if time_result:
                        return {
                            'answer': time_result['formatted_date'],
                            'confidence': time_result['confidence'],
                            'event_time': time_result['event_date'].isoformat(),
                            'reasoning_chain': [
                                f"🔥 StoryArc 直接查询",
                                f"实体: {entity}",
                                f"事件类型: {time_result['event'].event_type}",
                                f"事件日期: {time_result['formatted_date']}",
                                f"匹配分数: {time_result['match_score']}"
                            ],
                            'source': 'story_arc_event_time'
                        }

            return None

        except Exception as e:
            logger.warning(f"StoryArc reasoning failed: {e}")
            return None

    def _extract_query_elements(self, query: str) -> tuple[List[str], List[str]]:
        """
        从查询中提取实体和事件关键词（通用规则，无硬编码）

        实体：大写开头的非疑问词
        事件关键词：长度>3 的非停用词（名词/动词）
        """
        entities = []
        event_keywords = []

        # 停用词集合（通用，与领域无关）
        stop_words = {
            'when', 'where', 'what', 'how', 'who', 'which', 'why', 'did', 'does',
            'do', 'the', 'a', 'an', 'to', 'is', 'was', 'are', 'were', 'has', 'had',
            'have', 'will', 'would', 'could', 'should', 'may', 'might', 'can',
            'this', 'that', 'with', 'from', 'about', 'for', 'of', 'and', 'or',
            'but', 'not', 'in', 'on', 'at', 'by', 'it', 'up', 'out', 'off',
            'her', 'his', 'their', 'its', 'our', 'you', 'your', 'my', 'mine',
            'recently', 'lately', 'some', 'any', 'most', 'many', 'much',
            # 月份/星期（不应作为实体）
            'january', 'february', 'march', 'april', 'june',
            'july', 'august', 'september', 'october', 'november', 'december',
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
            'saturday', 'sunday',
        }

        # 1. 从大写单词提取实体（通用规则）
        words = query.split()
        for word in words:
            clean = re.sub(r'[^\w]', '', word)
            if (clean and len(clean) > 1 and clean[0].isupper()
                    and clean.lower() not in stop_words):
                if clean not in entities:
                    entities.append(clean)

        # 2. 提取事件关键词：所有非实体、非停用词、长度>3 的词
        entity_lower = {e.lower() for e in entities}
        for word in words:
            clean = re.sub(r'[^\w]', '', word).lower()
            if (len(clean) > 3
                    and clean not in stop_words
                    and clean not in entity_lower):
                if clean not in event_keywords:
                    event_keywords.append(clean)

        return entities, event_keywords

    async def _temporal_reasoning(
        self,
        query: str,
        memories: List[Dict],
        hippocampus: Optional[Any] = None,
        memories_by_region: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        时间推理: 计算相对时间到绝对时间

        人脑过程:
        1. 从海马体(hippocampus)提取对话日期和事件时间
        2. 识别相对时间表达("yesterday", "last week")
        3. 执行时间计算
        4. 验证结果合理性

        🔥 2025-12-11 优化: 优先使用 Hippocampus 的规则基础推理结果
        - 规则推理比 LLM 更可靠地计算 "yesterday = conversation_date - 1"
        - 只有在规则无法处理时才回退到 LLM
        """

        # 🔥 2025-12-27 FIX: 先检测是否是duration问题，影响后续路径选择
        query_lower = query.lower()
        is_duration_query = any(keyword in query_lower for keyword in [
            'how long', 'how many years', 'how many months', 'how many days',
            'how many weeks', 'how many hours', 'duration', 'passed between',
            'before', 'after', 'since', '多久', '多少天', 'how old'
        ])

        # 🔥 2025-12-27 FIX: 检测期望的答案格式
        expects_count = any(kw in query_lower for kw in [
            'how many days', 'how many months', 'how many years', 'how many weeks',
            'how old was'
        ])
        expects_duration = any(kw in query_lower for kw in [
            'how long'
        ])
        expects_time = 'what time' in query_lower

        # 🔥 2026-04-03: 缓存查询 embedding 供 metadata reasoning 使用
        self._query_embedding_cache = None
        if hippocampus and hasattr(hippocampus, 'embedding_service') and hippocampus.embedding_service:
            try:
                qe = await hippocampus.embedding_service.encode_text(query)
                self._query_embedding_cache = qe.tolist() if hasattr(qe, 'tolist') else qe
            except Exception:
                pass

        # 🔥 2025-12-11 重构: 优先使用 metadata.event_time（存储时已计算好）
        # 但对于 duration 问题，跳过直接的 metadata 日期返回
        if not (expects_count or expects_duration or expects_time):
            metadata_result = await self._try_metadata_based_reasoning(
                query=query,
                memories=memories,
                memories_by_region=memories_by_region
            )
            if metadata_result and metadata_result.get('answer'):
                logger.info(f"📅 Using metadata.event_time: {metadata_result.get('answer')}")
                return metadata_result

        # 🔥 V2.0: StoryArc 时间线直接查询 (比 LLM 更可靠)
        story_arc_result = await self._try_story_arc_reasoning(query)
        if story_arc_result and story_arc_result.get('answer'):
            logger.info(f"📅 Using StoryArc: {story_arc_result.get('answer')} "
                       f"(source={story_arc_result.get('source')})")
            return story_arc_result

        # 🔥 优先使用脑区组织的记忆
        if memories_by_region:
            hippocampus_memories = memories_by_region.get('hippocampus', [])
            temporal_memories = memories_by_region.get('temporal', [])

            memories_text = f"""
🧠 Hippocampus (Episodic Memory - Events & Time):
{chr(10).join(f"- {m}" for m in hippocampus_memories) if hippocampus_memories else "- (empty)"}

📚 Temporal Lobe (Semantic Memory - Facts):
{chr(10).join(f"- {m}" for m in temporal_memories) if temporal_memories else "- (empty)"}
"""
        else:
            memories_text = self._format_memories(memories)

        # 🔥 2025-12-27: is_duration_query 已在函数开头定义，此处不再重复

        reasoning_prompt = f"""You are simulating temporal reasoning in the prefrontal cortex.

Question: {query}

Available Evidence (organized by brain regions):
{memories_text}

Task: {"Calculate DURATION between two dates/events" if is_duration_query else "Calculate ABSOLUTE DATE from relative time references"} using CROSS-MEMORY reasoning.

{'🔥 DURATION CALCULATION MODE:' if is_duration_query else '🔥 DATE CALCULATION MODE - MUST RETURN ABSOLUTE DATE (e.g., 7 May 2023), NOT RELATIVE TIME!'}

{'Step 1 - Identify Time Points:' if is_duration_query else 'Step 1 - Find Conversation Date (查询海马体):'}
{'''Look for TWO time references:
- If "between EVENT_A and EVENT_B": Find dates for BOTH events
  Example: "between attending an event and completing a task"
  → Find: "Yesterday, Person attended..." (7 May) AND "On 25 May, Person completed..." (25 May)
- If "had X for Y time": Find reference date + duration
  Example: "had friends for 4 years" + conversation on "8 May 2023" → Started on 8 May 2019''' if is_duration_query else '''Look in HIPPOCAMPUS memories for:
- "[Context: This conversation is on DATE]"
- "Today's date is DATE"
- "On DATE, ..."'''}

{'Step 2 - Extract Event Dates:' if is_duration_query else 'Step 2 - Find Relative Time & SUBTRACT (查询海马体):'}
{'''Extract absolute dates for EACH event:
- If "Yesterday, Person attended..." + context "8 May 2023" → Event_A = 7 May 2023
- If "On 25 May, Person completed..." → Event_B = 25 May 2023
- If "had X for 4 years" → Duration is EXPLICITLY stated, use directly!''' if is_duration_query else '''Look in HIPPOCAMPUS memories for RELATIVE TIME words and SUBTRACT:
🔥 CRITICAL SUBTRACTION RULES:
- "yesterday" → conversation_date MINUS 1 day (8 May - 1 = 7 May)
- "today" → conversation_date PLUS 0 days
- "last week" → conversation_date MINUS 7 days
- "the day before" → conversation_date MINUS 1 day
- "two days ago" → conversation_date MINUS 2 days

🔥 EXAMPLE: If memory says "[Context: 8 May 2023] went yesterday"
   → Event happened on: 8 - 1 = 7 May 2023 (NOT 8 May!)'''}

Step 3 - {'Duration Calculation:' if is_duration_query else 'Cross-Memory Calculation (MUST SUBTRACT!):'}
{'''CRITICAL: Calculate "days PASSED BETWEEN" two dates (EXCLUSIVE of both endpoints):
- Example: Event_A = 7 May 2023, Event_B = 25 May 2023
- Question: "How many days passed BETWEEN 7 May and 25 May?"
- Calculation: Days in between = 25 - 7 - 1 = 17 days
  * Why -1? Because we count days BETWEEN (8,9,10...24), NOT including 7 and 25
  * Count: 8 May, 9 May, ..., 24 May = 17 days
- If question is "How many days FROM X TO Y?" (inclusive): Use 25 - 7 = 18
- VERIFY: Always count the actual days to double-check!
- Alternative: If duration EXPLICITLY stated like "had friends for 4 years" → use directly!''' if is_duration_query else '''🔥 MANDATORY CALCULATION STEPS:
1. Extract conversation_date from "[Context: This conversation is on DATE]"
2. Find relative_time word ("yesterday", "last week", etc.)
3. SUBTRACT to get event_date:
   - "yesterday" on 8 May → 8 - 1 = 7 May 2023 (ANSWER: 7 May)
   - "yesterday" on 10 May → 10 - 1 = 9 May 2023 (ANSWER: 9 May)
   - "last week" on 15 May → 15 - 7 = 8 May 2023 (ANSWER: 8 May)

⚠️ COMMON ERROR: Do NOT return the conversation_date as the answer!
   If conversation is on "8 May" and event was "yesterday", answer is "7 May" NOT "8 May"!'''}

Step 4 - Verify:
{"Does the duration make sense?" if is_duration_query else "Does the date make sense? (e.g., May 7 comes before May 8)"}

Step 5 - Decision:
- If clear {'duration' if is_duration_query else 'calculation'} from cross-memory: High confidence (0.9+)
- If ambiguous: Lower confidence, request clarification

🔥 CRITICAL for duration questions:
- If "between EVENT_A and EVENT_B": Extract BOTH dates first, then calculate difference
  Example: 7 May to 25 May → 25 - 7 = 18 days
- If memory explicitly states duration (e.g., "for 4 years"): Use that directly
- Answer format: "18 days", "4 years", "6 months", etc. (NOT dates!)

🚨 SELF-CHECK BEFORE ANSWERING:
- If you found "yesterday" in the memory and conversation_date is "8 May 2023"
- Your answer MUST be "7 May 2023" (8 minus 1 = 7)
- If your answer equals the conversation_date, YOU MADE AN ERROR! Redo the calculation.

🚫 ANTI-HALLUCINATION RULES (CRITICAL):
- If the memories do NOT contain information about the specific event asked → return "Unable to determine", confidence=0.2
- NEVER guess or invent dates not found in memories
- NEVER return a date from an unrelated event (e.g., don't return workshop date for museum question)
- Each question asks about a SPECIFIC event - find THAT event's date, not any random date
- If unsure which memory relates to the question → return "Unable to determine"

Output JSON only:
{{
    "conversation_date": "extracted date from [Context:...], e.g. '8 May 2023'",
    "relative_time": "extracted word like 'yesterday', 'last week', etc. (or null if explicit date given)",
    "calculation_steps": "SHOW YOUR MATH: '8 May 2023' - 'yesterday' (1 day) = '7 May 2023'",
    "calculated_date": "result of subtraction{' or null if duration query' if is_duration_query else ''} - THIS IS YOUR ANSWER",
    "duration": "{("extracted or calculated duration (e.g., '4 years')" if is_duration_query else 'null')}",
    "answer": "{("duration like '4 years' or '17 days'" if is_duration_query else 'THE CALCULATED DATE (must differ from conversation_date if relative time was used!)')}",
    "confidence": 0.0-1.0,
    "verification": "Is answer different from conversation_date when relative_time was used? YES/NO - if NO, recalculate!",
    "reasoning_chain": ["Step 1: conversation_date = X", "Step 2: relative_time = Y means -Z days", "Step 3: X - Z = ANSWER"],
    "refined_query": "query for more context if needed (else null)"
}}
"""

        try:
            full_prompt = f"You are a temporal reasoning expert. Output valid JSON only.\n\n{reasoning_prompt}"
            content = await self.call_llm(
                prompt=full_prompt,
                temperature=0.1,
                max_tokens=500
            )
            # 提取JSON内容
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            # 尝试解析JSON，处理格式错误
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parsing failed: {e}, attempting to fix...")
                # 尝试修复常见的JSON问题
                content = content.replace(',}', '}').replace(',]', ']')
                last_brace = content.rfind('}')
                if last_brace > 0:
                    content = content[:last_brace+1]
                try:
                    result = json.loads(content)
                    logger.debug("✅ JSON fixed and parsed successfully")
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Cannot parse JSON: {e}, using fallback")
                    result = {
                        'answer': 'Unable to determine',
                        'reasoning': 'JSON parsing error',
                        'confidence': 0.3,
                        'reasoning_chain': []
                    }

            if is_duration_query:
                result = await self._enforce_duration_answer(
                    query=query,
                    result=result,
                    memories_text=memories_text
                )

            # 🔥 2025-12-13 FIX: 验证答案与问题的相关性
            # 如果LLM返回的日期在记忆中没有出现，或者与问题不相关，降低置信度
            answer = result.get('answer', '')
            if answer and answer != 'Unable to determine':
                # 检查答案是否在memories_text中有对应内容
                answer_in_memories = str(answer).lower() in memories_text.lower()
                # 如果置信度高但答案不在记忆中，可能是幻觉
                if not answer_in_memories and result.get('confidence', 0) > 0.5:
                    logger.warning(f"⚠️ Temporal answer '{answer}' not found in memories, reducing confidence")
                    result['confidence'] = min(result.get('confidence', 0.5), 0.4)

            # 双向反馈
            if result.get('confidence', 0) < 0.7 and result.get('refined_query') and hippocampus:
                logger.debug(f"🔄 Temporal reasoning: Requesting more context from Hippocampus")
                # 修复: hippocampus.retrieve -> hippocampus.search_memories
                search_result = await hippocampus.search_memories(result['refined_query'], k=5)
                more_memories = search_result.get('memories', []) if isinstance(search_result, dict) else search_result
                if more_memories:
                    return await self._temporal_reasoning(query, memories + more_memories, None)

            logger.debug(f"✅ Temporal reasoning: {result.get('answer')} (confidence={result.get('confidence', 0):.2f})")
            return result

        except Exception as e:
            import traceback
            logger.error(f"Temporal reasoning error: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {'answer': None, 'confidence': 0.0, 'reasoning_chain': [f'Error: {str(e)}']}

    async def _enforce_duration_answer(
        self,
        query: str,
        result: Dict[str, Any],
        memories_text: str
    ) -> Dict[str, Any]:
        """
        确保时长类问题的答案最终输出为持续时间,而不是回到事件日期。
        """
        answer_text = (result.get('answer') or '').strip()
        duration_text = (result.get('duration') or '').strip()

        if duration_text and self._looks_like_duration(duration_text):
            if not self._looks_like_duration(answer_text):
                result['answer'] = duration_text
            return result

        if self._looks_like_duration(answer_text):
            return result

        correction_prompt = f"""You produced a temporal reasoning result, but the question requires a duration answer.

Question: "{query}"

Memories summary:
{memories_text}

Current reasoning JSON:
{json.dumps(result, indent=2, ensure_ascii=False)}

Task:
1. Derive the duration implied by the evidence (e.g., "18 days", "4 years").
2. Update the JSON so that:
   - "answer" contains ONLY the duration string.
   - "duration" mirrors the same duration string.
   - Adjust "confidence", "reasoning_chain", and "calculation_steps" if needed.
3. If the evidence truly lacks enough information, set "answer": "unknown duration", "duration": null, and confidence ≤ 0.3.

Return STRICT JSON matching the original schema.
"""

        try:
            content = await self.call_llm(
                prompt=correction_prompt,
                temperature=0.1,
                max_tokens=400
            )
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            refined = json.loads(content)
            # 仅在确实返回duration时刷新结果
            refined_duration = (refined.get('duration') or '').strip()
            refined_answer = (refined.get('answer') or '').strip()
            if self._looks_like_duration(refined_answer) or self._looks_like_duration(refined_duration):
                if refined_duration:
                    refined['duration'] = refined_duration
                result.update(refined)
        except Exception as exc:
            logger.warning(f"⚠️ Temporal duration enforcement failed: {exc}")

        return result

    def _looks_like_duration(self, text: str) -> bool:
        """粗略判断文本是否像是一个持续时间表达。"""
        if not text:
            return False
        lower = text.lower()
        duration_units = [
            'day', 'days', 'week', 'weeks', 'month', 'months', 'year', 'years',
            'hour', 'hours', 'minute', 'minutes', '天', '周', '月', '年', '小时', '分钟'
        ]
        has_number = any(char.isdigit() for char in lower)
        has_unit = any(unit in lower for unit in duration_units)
        return has_number and has_unit
