"""
Answer Synthesis for Capability Orchestrator
答案合成模块 - 合成、选择、精炼答案
"""

import logging
import json
import re
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)


# Substrings that mark a candidate answer as effectively "no info". Used to
# filter unknown candidates out of multi-candidate selection unless ALL
# candidates are unknown.
#
# TODO(answer-quality-policy): both this list and the 14-word "long answer"
# threshold in `_looks_unknown` are local defences. They should migrate into
# a shared AnswerQualityPolicy (config-driven, owned by reasoning/) once we
# also unify the refiner heuristics in coordinator.refine_answer_for_qa.
# Keeping them here for now because (a) they are already proven useful and
# (b) introducing a new policy class is a larger refactor than the current
# C1 surface area.
_UNKNOWN_PATTERNS = (
    'information not available',
    'no information available',
    "i don't have enough information",
    'i do not have enough information',
    "i don't know",
    'i do not know',
    'unknown',
    'not mentioned',
    'no information',
    'cannot find',
    'could not find',
    'no specific',
    'not specified',
    "isn't mentioned",
    "wasn't mentioned",
    'no record',
    'no mention',
    'not explicitly stated',
    'not available',
)


def _looks_unknown(answer: str) -> bool:
    """Return True if this candidate answer is effectively 'no info'.

    Long substantive answers (>14 words) that incidentally contain one of the
    patterns are NOT treated as unknown — keeps recommendation paragraphs
    that mention 'not mentioned' from getting filtered.
    """
    if not answer:
        return True
    a = str(answer).strip()
    if not a:
        return True
    if len(a.split()) > 14:
        return False
    a_low = a.strip('"').strip("'").strip('.').lower()
    return any(p in a_low for p in _UNKNOWN_PATTERNS)


# Stopwords used by the local evidence-overlap check. Intentionally small —
# matches function words and answer-shell verbs/pronouns so the score reflects
# content tokens (people, places, objects, predicates) rather than scaffolding.
_STOPWORDS = frozenset({
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of',
    'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
    'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these',
    'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
    'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their', 'not', 'no',
    'so', 'than', 'when', 'where', 'why', 'how', 'what', 'who', 'which',
    'just', 'only', 'also', 'very', 'about', 'into', 'over', 'under', 'such',
    'some', 'any', 'all', 'them', 'theirs',
})

# Adversarial / counterfactual surface markers. Conservative on purpose — the
# evidence gate handles the residual cases this misses. Triggers prerank-skip,
# not no-info-filter-skip (no-info filter is gated separately via grounding).
_ADVERSARIAL_RE = re.compile(
    r'\b(would|hadn\'?t|wouldn\'?t|considered|reaction\s+to)\b'
    r'|^\s*if\b'
    r'|,\s*if\b',
    re.IGNORECASE,
)


def _content_tokens(text: str) -> List[str]:
    """Lowercase content tokens (≥3 chars, not stopwords)."""
    if not text:
        return []
    raw = re.findall(r"[A-Za-z][A-Za-z0-9'\-]*", str(text).lower())
    return [t for t in raw if len(t) >= 3 and t not in _STOPWORDS]


def _memory_pool_text(memories: List[Any], cap: int = 30) -> str:
    """Concatenate memory contents into one lowercased blob for overlap checks."""
    if not memories:
        return ''
    chunks: List[str] = []
    for m in memories[:cap]:
        if isinstance(m, dict):
            t = m.get('content') or m.get('text') or m.get('memory') or ''
        else:
            t = getattr(m, 'content', None) or str(m)
        if isinstance(t, str) and t:
            chunks.append(t.lower())
    return ' \n '.join(chunks)


def _answer_evidence_score(answer: str, mem_blob: str) -> float:
    """Fraction of `answer`'s content tokens that appear as substrings in
    the memory pool blob (already lowercased). Returns 0.0 when there are
    no content tokens.
    """
    answer_toks = _content_tokens(answer)
    if not answer_toks or not mem_blob:
        return 0.0
    hits = sum(1 for t in answer_toks if t in mem_blob)
    return hits / len(answer_toks)


def _answer_is_grounded(answer: str, mem_blob: str) -> bool:
    """Threshold gate. Looser for quoted titles / proper-noun phrases (any
    content-token hit is enough), stricter for short bare answers (≥0.5),
    moderate for longer answers (≥0.3).
    """
    if not answer or not mem_blob:
        return False
    a = str(answer)
    score = _answer_evidence_score(a, mem_blob)
    n = len(_content_tokens(a))
    if n == 0:
        return False
    if '"' in a or '“' in a:
        return score > 0
    if n <= 4:
        return score >= 0.5
    return score >= 0.3


def _query_is_adversarial_or_counterfactual(
    query: str,
    intermediate_results: Dict[str, Any] = None,
) -> bool:
    """Skip-prerank predicate. Two channels combined:
      1. Surface form: `_ADVERSARIAL_RE` matches would/if/considered/etc.
      2. Capability signal: capability_analyzer routed `counterfactual_reasoning`.
    """
    if intermediate_results and 'counterfactual_reasoning' in intermediate_results:
        return True
    if not query:
        return False
    return bool(_ADVERSARIAL_RE.search(query))


# Date / month tokens used by the audit candidate-type classifier. Light-weight
# detection — only used to label candidate answers in JSONL events, never to
# gate logic.
_TEMPORAL_ANSWER_RE = re.compile(
    r'\b(\d{4}|\d{1,2}\s+(?:january|february|march|april|may|june|july|august|'
    r'september|october|november|december)|january|february|march|april|may|'
    r'june|july|august|september|october|november|december)\b',
    re.IGNORECASE,
)


def classify_candidate_type(answer: str) -> str:
    """Audit-only label for an intermediate candidate answer. Returns one of:
        'unknown'  — matches a no-info pattern (e.g. 'not mentioned')
        'temporal' — answer carries a date / month / year token
        'list'     — short comma-separated category list
        'concrete' — passes `_is_concrete_answer` (specific phrase / sentence)
        'abstract' — fallback (single bare noun, lowercase X-and-Y, etc.)
    The classifier is descriptive only; nothing in the runtime depends on it.
    """
    if not answer:
        return 'unknown'
    a = str(answer).strip()
    if not a:
        return 'unknown'
    if _looks_unknown(a):
        return 'unknown'
    # Temporal-shaped answers (year, "DD Month", "Month YYYY", etc.)
    if _TEMPORAL_ANSWER_RE.search(a):
        return 'temporal'
    # Short comma list with ≤6 words → category enumeration.
    words = a.split()
    if ',' in a and len(words) <= 6:
        return 'list'
    # Local import to avoid circular reference at module load.
    if AnswerSynthesisMixin._is_concrete_answer(a):
        return 'concrete'
    return 'abstract'


class AnswerSynthesisMixin:
    """Answer synthesis mixin for CapabilityOrchestrator"""

    async def _synthesize_answer(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        🧠 智能答案选择 - 使用LLM评估哪个capability的答案最匹配问题意图

        策略升级:
        1. 收集所有有答案的capabilities
        2. 如果只有1个答案,直接返回
        3. 如果有多个答案,使用LLM判断哪个最匹配问题的语义和期望答案类型
        4. 这是brain-collaboration approach,不是hardcoded rules
        """
        intermediate = context['intermediate_results']
        query = context.get('query', '')

        # 🔥 2025-12-27: 检测是否为推荐类问题 (需要完整回答)
        is_recommendation_question = any(kw in query.lower() for kw in [
            'recommend', 'suggest', 'resources', 'best way', 'how should',
            'what are some', 'can you suggest', 'looking for ways'
        ])

        # 收集有答案的capabilities
        cap_results = []
        for cap_name, result in intermediate.items():
            # 🔥 2025-12-27: 添加类型检查，跳过非字典结果
            if cap_name.startswith('_'):  # 跳过内部字段如 _user_id
                continue
            if not isinstance(result, dict):
                logger.warning(f"⚠️ Capability {cap_name} returned non-dict: {type(result)}")
                continue
            if result.get('answer'):
                answer = str(result.get('answer', ''))
                # 🔥 2025-12-27: 对推荐类问题，过滤太短的答案
                if is_recommendation_question and len(answer) < 30:
                    logger.info(f"⏭️ Skipping short answer from {cap_name} for recommendation question: {answer[:50]}")
                    continue
                cap_results.append((cap_name, result))

        # Case 1: 没有答案
        if not cap_results:
            # 🔥 2025-12-27: 对推荐类问题，生成一个通用但有帮助的回答
            if is_recommendation_question:
                fallback_answer = "Based on your preferences, I recommend exploring resources and methods that align with your learning style. Consider options that match your stated interests while avoiding approaches you've mentioned disliking. Interactive and hands-on methods often work well for personalized learning."
                return {
                    'answer': fallback_answer,
                    'confidence': 0.4,
                    'error': 'No suitable answer found, using fallback',
                    'fallback': True
                }
            return {
                'answer': f"I don't have enough information to answer the question: {query}",
                'confidence': 0.1,
                'error': 'No capability produced an answer',
                'fallback': True
            }

        # Evidence-gated no-info filter. We only drop unknown candidates if
        # at least one concrete candidate is actually GROUNDED in the
        # retrieved memories (token overlap, content words only). If no
        # concrete candidate is grounded, the unknowns stay in the
        # competition — this is what protects adversarial/trick questions
        # where the truthful answer is "no info" and any concrete-shape
        # alternative would be a hallucination.
        memories = context.get('memories') or []
        intermediate = context.get('intermediate_results') or {}
        mem_blob = _memory_pool_text(memories)

        # audit: synthesizer entry — what answer-shapes did each capability
        # produce, and what memory pool is the selector operating on?
        try:
            from src.coordination import audit_log as _audit
            if _audit.is_enabled():
                cand_summary = []
                for n, r in cap_results:
                    ans = str(r.get('answer', ''))
                    cand_summary.append({
                        'cap': n,
                        'type': classify_candidate_type(ans),
                        'answer_hash': _audit.memory_id({'content': ans}),
                        'word_count': len(ans.split()),
                        'confidence': r.get('confidence'),
                        **({'preview': ans[:80]} if _audit._content_preview_enabled() else {}),
                    })
                _audit.event(
                    'synthesize_input',
                    query=query,
                    candidates_count=len(cap_results),
                    candidates=cand_summary,
                    memories_count=len(memories),
                    memories_top=[_audit.memory_meta(m) for m in memories[:10]],
                    intermediate_capabilities=list(intermediate.keys()),
                )
        except Exception:  # noqa: BLE001
            pass

        concrete = [(n, r) for n, r in cap_results if not _looks_unknown(r.get('answer', ''))]
        unknown = [(n, r) for n, r in cap_results if _looks_unknown(r.get('answer', ''))]
        if concrete and unknown:
            grounded = [
                (n, r) for n, r in concrete
                if _answer_is_grounded(str(r.get('answer', '')), mem_blob)
            ]
            if grounded:
                logger.info(
                    f"🛡️  no-info filter (grounded): dropping {len(unknown)} unknown "
                    f"({[n for n, _ in unknown]}) — {len(grounded)}/{len(concrete)} "
                    f"concrete grounded"
                )
                cap_results = concrete
            else:
                logger.info(
                    f"🛡️  no-info filter SKIPPED: no concrete candidate is grounded "
                    f"({[n for n, _ in concrete]}) — keeping unknown candidates "
                    f"({[n for n, _ in unknown]}) in competition"
                )
                # cap_results unchanged: unknowns stay

        # Case 2: 只有一个答案,直接返回
        if len(cap_results) == 1:
            cap_name, result = cap_results[0]
            logger.info(f"🎯 Single answer from {cap_name}: {str(result.get('answer'))[:100]}...")
            return {
                'answer': result['answer'],
                'confidence': result.get('confidence', 0.7),
                'primary_capability': cap_name
            }

        # Case 3: 多个答案 - 使用LLM智能选择
        logger.info(f"🤔 Multiple answers available ({len(cap_results)}), using LLM to select best match...")
        selected_cap, selected_result = await self._llm_select_best_answer(
            query, cap_results,
            memories=memories,
            intermediate_results=intermediate,
        )

        logger.info(f"🎯 LLM selected answer from {selected_cap}: {str(selected_result.get('answer'))[:100]}...")

        return {
            'answer': selected_result['answer'],
            'confidence': selected_result.get('confidence', 0.7),
            'primary_capability': selected_cap
        }

    async def _llm_select_best_answer(
        self,
        query: str,
        cap_results: List[tuple],
        memories: List[Any] = None,
        intermediate_results: Dict[str, Any] = None,
    ) -> tuple:
        """
        🧠 使用LLM评估多个候选答案,选择最匹配问题意图的

        The selector outputs JSON with a numeric choice plus a short reason
        and an evidence_quote drawn from the memory pool. Memories are
        passed in so the LLM can verify each candidate is actually grounded.
        If JSON parsing fails we fall back to a bare integer in the
        response, then to candidate #1.

        For factual "what did/does/has X …" questions, a content-agnostic
        prerank pushes concrete candidates ahead of abstract category words.
        See _prerank_concrete_first_for_factual_what.
        """
        from src.agents.base import BrainAgent

        class TempAnswerSelector(BrainAgent):
            async def process_message(self, msg): return {}

        selector = TempAnswerSelector('answer_selector', 'prefrontal', 'Answer Selector')

        # Reorders cap_results so the LLM sees concrete candidates first
        # (it tends to prefer the earlier index when scores are close).
        # Skipped on adversarial/counterfactual questions where preferring
        # concrete shapes biases the system toward asserting facts the
        # memory can't actually support.
        cap_results = self._prerank_concrete_first_for_factual_what(
            query, cap_results, intermediate_results=intermediate_results
        )

        # Build candidate block.
        candidates_text = ""
        for i, (cap_name, result) in enumerate(cap_results, 1):
            answer = result.get('answer', '')
            confidence = result.get('confidence', 0.0)
            candidates_text += f"\n{i}. [{cap_name}] (confidence={confidence:.2f})\n   Answer: {answer}\n"

        # Memory evidence pool — short snippets, capped to keep prompt tight.
        memory_text = self._format_memory_pool_for_selector(memories)

        # NOTE: selection rules are content-agnostic on purpose. Do NOT
        # paste benchmark-specific example strings here — see auto-memory
        # "Fast Eval Bias Lesson". Phrase rules in terms of answer shape
        # (proper-noun phrase, sentence claim, comma list, single token)
        # rather than naming any concrete entity from the eval set.
        prompt = f"""You are selecting the best candidate answer for a question.

Question: "{query}"

Candidates:
{candidates_text}

Memory evidence pool (for grounding the choice; not all snippets are relevant):
{memory_text or '(no memories provided)'}

Selection rules:
1. Match answer TYPE to question TYPE: "where" → location, "when" → date/time, "who" → person, "how many" → number/count, "what" → thing/action/claim.
2. When the question asks for a subject's specific action, belief, object, or recommendation, PREFER candidates whose answer is concrete in shape — a quoted title, a proper-noun phrase, or a complete claim sentence — OVER candidates that are abstract category words (single bare nouns, or short comma/AND-separated topic lists).
3. For "When?" / "What date?" questions, PREFER a temporal-calculation candidate if it produced an answer.
4. For recommendation, resource, or "best way to" questions, PREFER the longer, more detailed candidate.
5. Shorter is better for fact lookups, but never pick a candidate that strips away the specific noun the question is asking for.
6. The chosen answer should be supported by at least one memory snippet — quote the supporting span if you can find one. If no candidate is grounded, still pick the best-phrased one but lower confidence.
7. NEVER select a candidate whose answer is an unknown/no-information phrase if a concrete candidate exists.

Output JSON ONLY, in this exact shape:
{{"selected": <int 1..N>, "reason": "<one sentence>", "evidence_quote": "<short quote from memories, or empty>"}}
"""

        # audit: what does the selector actually see, in the order it sees it?
        try:
            from src.coordination import audit_log as _audit
            if _audit.is_enabled():
                ordered = []
                for n, r in cap_results:
                    ans = str(r.get('answer', ''))
                    ordered.append({
                        'cap': n,
                        'type': classify_candidate_type(ans),
                        'answer_hash': _audit.memory_id({'content': ans}),
                        'word_count': len(ans.split()),
                        'confidence': r.get('confidence'),
                        **({'preview': ans[:80]} if _audit._content_preview_enabled() else {}),
                    })
                _audit.event(
                    'selector_input',
                    query=query,
                    candidates_in_order=ordered,
                    memory_pool_size=len(memories) if memories else 0,
                    memory_pool_top=[
                        _audit.memory_meta(m) for m in (memories[:10] if memories else [])
                    ],
                    adversarial_skip=_query_is_adversarial_or_counterfactual(
                        query, intermediate_results
                    ),
                )
        except Exception:  # noqa: BLE001
            pass

        response = await selector.call_llm(
            prompt=prompt,
            temperature=0.0,
            max_tokens=180,
        )

        # Try strict JSON parse first.
        choice = None
        reason = None
        evidence = None
        try:
            obj = self._extract_json(response)
            if obj is not None:
                choice = obj.get('selected')
                reason = obj.get('reason')
                evidence = obj.get('evidence_quote')
                if isinstance(choice, str):
                    m = re.search(r'\d+', choice)
                    choice = int(m.group()) if m else None
        except Exception as e:  # noqa: BLE001
            logger.debug(f"Selector JSON parse failed: {e}")

        # Fallback: bare integer in the response.
        if not isinstance(choice, int):
            try:
                m = re.search(r'\d+', response or '')
                if m:
                    choice = int(m.group())
            except Exception:  # noqa: BLE001
                pass

        if isinstance(choice, int) and 1 <= choice <= len(cap_results):
            picked = cap_results[choice - 1]
            logger.info(
                f"🧠 selector picked #{choice} [{picked[0]}] "
                f"reason={reason!r} evidence={str(evidence)[:60]!r}"
            )
            return picked

        logger.warning(f"Failed to parse LLM selection: {response[:120]!r}, falling back to first candidate")
        return cap_results[0]

    @staticmethod
    def _format_memory_pool_for_selector(memories: List[Any]) -> str:
        """Render memory snippets as a short numbered list for the selector."""
        if not memories:
            return ''
        lines = []
        for i, m in enumerate(memories[:12], 1):
            if isinstance(m, dict):
                txt = m.get('content') or m.get('text') or m.get('memory') or ''
            else:
                txt = getattr(m, 'content', None) or str(m)
            if not isinstance(txt, str):
                continue
            txt = txt.strip().replace('\n', ' ')
            if not txt:
                continue
            if len(txt) > 240:
                txt = txt[:240] + '…'
            lines.append(f'  M{i}. {txt}')
        return '\n'.join(lines)

    @staticmethod
    def _extract_json(s: str):
        """Extract the first JSON object from a response, tolerant to fences/prefix."""
        if not s:
            return None
        # Strip code fences.
        s = s.strip()
        s = re.sub(r'^```(?:json)?', '', s).rstrip('`').strip()
        # Find the first {...} block.
        i = s.find('{')
        if i < 0:
            return None
        depth = 0
        for j in range(i, len(s)):
            if s[j] == '{':
                depth += 1
            elif s[j] == '}':
                depth -= 1
                if depth == 0:
                    chunk = s[i:j + 1]
                    try:
                        return json.loads(chunk)
                    except Exception:  # noqa: BLE001
                        return None
        return None

    # Question shapes for which the expected answer is a specific
    # action/object/claim attributed to a subject. Captured by morphology
    # ("what did/does/has X …"), not by a verb whitelist. Kept narrow so it
    # doesn't fire on "what color is …", "what time is it", etc.
    _FACTUAL_WHAT_RE = re.compile(
        r'^\s*what\s+(?:did|does|has)\b',
        re.IGNORECASE,
    )

    # Question morphologies we explicitly do NOT prerank — temporal questions
    # have their own routing path; "what color/time/year" expect terse atomic
    # answers where the concrete-vs-abstract trade-off does not apply.
    _PRERANK_SKIP_RE = re.compile(
        r'\b(when\s|what\s+(?:year|date|time|month|color|colou?r))\b|how\s+long\s+ago',
        re.IGNORECASE,
    )

    @staticmethod
    def _is_concrete_answer(answer: str) -> bool:
        """Return True if `answer` looks like a concrete fact/claim rather
        than an abstract category label.

        Content-agnostic shape rules (no entity names from any benchmark):
          - Single token  → abstract.
          - Quoted phrase → concrete (a title/quote is specific by shape).
          - Short comma list (≤6 words, has ',') → abstract category list.
          - Short lowercase 'X and Y' (≤6 words, no ',') → abstract list.
          - Otherwise (≥2 words, capitalised phrase or longer claim) →
            concrete enough for "specific over abstract" reranking.

        These thresholds (6-word window) live here as local heuristics for
        the prerank only; they do not gate any answer correctness check.
        """
        if not answer:
            return False
        a = str(answer).strip().strip('.').strip()
        if not a:
            return False
        words = a.split()
        n = len(words)
        if n <= 1:
            return False
        if '"' in a or '“' in a:
            return True
        if ',' in a and n <= 6:
            return False
        if a[0].islower() and n <= 6 and ' and ' in a.lower():
            return False
        return True

    @classmethod
    def _prerank_concrete_first_for_factual_what(
        cls,
        query: str,
        cap_results: List[tuple],
        intermediate_results: Dict[str, Any] = None,
    ) -> List[tuple]:
        """For factual "what did/does/has X …" questions where multiple
        candidates exist and the set is mixed (≥1 concrete and ≥1 abstract),
        push concrete candidates ahead.

        Triggers only when:
          1. ≥2 candidates,
          2. query matches `_FACTUAL_WHAT_RE`,
          3. query does NOT match `_PRERANK_SKIP_RE` (temporal / atomic),
          4. query is NOT adversarial/counterfactual (would/if/considered/...
             OR capability_analyzer routed counterfactual_reasoning),
          5. the candidate set is genuinely mixed.

        Pure-concrete or pure-abstract sets pass through unchanged. All
        other question shapes pass through unchanged.
        """
        if not query or len(cap_results) < 2:
            return cap_results
        if not cls._FACTUAL_WHAT_RE.match(query):
            return cap_results
        if cls._PRERANK_SKIP_RE.search(query):
            return cap_results
        if _query_is_adversarial_or_counterfactual(query, intermediate_results):
            logger.info("🪨 prerank skipped: adversarial/counterfactual query")
            return cap_results
        concrete_idxs = [
            i for i, (_, r) in enumerate(cap_results)
            if cls._is_concrete_answer(r.get('answer', ''))
        ]
        if not concrete_idxs or len(concrete_idxs) == len(cap_results):
            return cap_results
        ordered = (
            [cap_results[i] for i in concrete_idxs]
            + [cap_results[i] for i in range(len(cap_results)) if i not in concrete_idxs]
        )
        logger.info(
            f"🪨 concrete prerank: {[c[0] for c in cap_results]} → "
            f"{[c[0] for c in ordered]}"
        )
        return ordered

    async def _refine_answer(self, query: str, answer: str, primary_capability: str = None) -> str:
        """
        答案后处理 - 针对特定问题类型优化答案格式

        目标: 解决verbose答案问题,提取核心信息
        """
        if not answer:
            return answer

        # 检测是否需要refinement
        question_lower = query.lower()

        # 🔥 规则0: 多选题处理 - 如果问题包含(a)(b)(c)(d)选项，确保答案是选项格式
        if '(a)' in query and '(b)' in query and '(c)' in query:
            # 检查答案是否已经是选项格式
            answer_lower = str(answer).lower().strip()
            if not any(opt in answer_lower for opt in ['(a)', '(b)', '(c)', '(d)', 'the answer is']):
                # 答案不是选项格式，需要转换
                logger.info(f"📝 Converting non-option answer to option: {answer[:50]}...")
                refined = await self._select_best_option(query, answer)
                if refined:
                    logger.info(f"   → Selected option: {refined}")
                    return refined

        # 规则1: "What fields" 问题 - 提取academic fields
        if any(kw in question_lower for kw in ['field', 'study', 'pursue', 'education', 'major']):
            # 检查答案是否verbose (超过10个词)
            if len(answer.split()) > 10:
                logger.debug(f"📝 Refining verbose 'fields' answer: {answer[:50]}...")
                refined = await self._extract_academic_fields(answer)
                if refined and refined != answer:
                    logger.info(f"   → Refined to: {refined}")
                    return refined

        # 规则2: 其他情况保持原样
        return answer

    async def _select_best_option(self, query: str, context_answer: str) -> str:
        """根据上下文答案选择最佳选项"""
        from src.agents.base import BrainAgent

        class TempSelector(BrainAgent):
            async def process_message(self, msg): return {}

        selector = TempSelector('option_selector', 'prefrontal', 'Option Selector')

        prompt = f"""Based on the given context, select the BEST option from the multiple choice question.

Question with options:
{query}

Context/Information to base your selection on:
{context_answer}

Task: Pick the option (a), (b), (c), or (d) that best aligns with the given context.

Output ONLY the letter in parentheses, like: (a) or (b) or (c) or (d)"""

        try:
            response = await selector.call_llm(prompt, temperature=0.1, max_tokens=10)
            response = response.strip().lower()

            # 提取选项
            import re
            match = re.search(r'\(([a-d])\)', response)
            if match:
                return f"({match.group(1)})"

            # 尝试其他格式
            for opt in ['a', 'b', 'c', 'd']:
                if opt in response:
                    return f"({opt})"

            return None

        except Exception as e:
            logger.error(f"Option selection failed: {e}")
            return None

    async def _extract_academic_fields(self, verbose_answer: str) -> str:
        """从verbose答案中提取academic fields"""
        from src.agents.base import BrainAgent

        class TempExtractor(BrainAgent):
            async def process_message(self, msg): return {}

        extractor = TempExtractor('field_extractor', 'prefrontal', 'Field Extractor')

        prompt = f"""Extract ONLY the academic field names from this verbose answer.

Verbose Answer: {verbose_answer}

Task: Extract just the academic field/discipline names in a concise format.

Examples:
- "Person X would likely pursue education in field A, field B, or field C"
  → "field A, field B, field C"

- "They would be interested in discipline X and discipline Y"
  → "discipline X, discipline Y"

Rules:
- Extract ONLY academic fields/disciplines
- Use comma-separated format
- Remove phrases like "would pursue", "likely to", "education in"
- Keep it under 10 words
- If no clear fields, return the original answer

Output ONLY the extracted fields, no explanation, no JSON."""

        try:
            response = await extractor.call_llm(prompt, temperature=0.1, max_tokens=50)
            # 清理response
            refined = response.strip().strip('"').strip("'")

            # 验证refinement有效性
            if len(refined) < len(verbose_answer) and len(refined.split()) <= 10:
                return refined
            else:
                return verbose_answer

        except Exception as e:
            logger.error(f"Field extraction failed: {e}")
            return verbose_answer

