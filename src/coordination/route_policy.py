"""B-full deterministic route policy — feature-flagged, content-agnostic.

Replaces the LLM-driven `_determine_answer_path` with a strict
priority-ordered classifier. Designed to address the diagnostic finding
that BMAM has the capacity to answer most questions correctly (oracle
97% on the unstable_33 churn set) but rolls dice on path selection,
with reasoning_chain consistently outperforming orchestrator (78% vs
67%) when used.

Strict priority:
  1. temporal explicit (when, what date/time/year, how long,
     earliest/latest/first/last/order) → temporal
  2. adversarial / counterfactual / premise-check
     (would, if, considered, hadn't, without, reaction-to, OR yes/no
     question shape) → orchestrator
  3. fact-like reasoning shape (what did/does/has X V, what motivated,
     what caused, why, what does X think/feel/realize/believe, what is
     the relationship between) → reasoning_chain
  4. fallback → orchestrator

Tier 2 BEFORE tier 3 on purpose: adversarial questions also match
"what did X V" or "is X's pet" shapes, and routing them to
reasoning_chain would make the system over-specify on premises that
don't hold.

Patterns describe answer SHAPE only — no benchmark entity names, no
verb whitelists derived from any specific eval set.

Switch:
  BMAM_ROUTE_POLICY_V2=1 enables override
  Off by default; coordinator falls back to its existing
  _determine_answer_path when disabled.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional, Tuple


# ----- enable -----

def enabled() -> bool:
    return os.getenv('BMAM_ROUTE_POLICY_V2', '0') == '1'


# ----- patterns: temporal explicit -----

_TEMPORAL_PATTERNS = (
    # "when did/was/is/will/has/does X …"
    re.compile(r'^\s*when\s+', re.IGNORECASE),
    # "what date/time/year/month/day"
    re.compile(r'\bwhat\s+(?:date|time|year|month|day)\b', re.IGNORECASE),
    # "how long ago / has / since / did"
    re.compile(r'\bhow\s+long\b', re.IGNORECASE),
    # ordering / sequence
    re.compile(r'\b(?:earliest|latest|first|last|previous|next|in\s+order)\b',
               re.IGNORECASE),
)


def _looks_temporal(query: str) -> bool:
    return any(p.search(query) for p in _TEMPORAL_PATTERNS)


# ----- patterns: adversarial / counterfactual / premise-check -----

_ADVERSARIAL_TIER2_RE = re.compile(
    r'\b(?:would|hadn\'?t|wouldn\'?t|couldn\'?t|considered|assume|assuming|'
    r'reaction\s+to|without)\b'
    r'|^\s*if\b'
    r'|,\s*if\b',
    re.IGNORECASE,
)

# Yes/no question shape — premise-check pattern. Starts with a finite
# verb that flags binary inquiry rather than open extraction.
# Excluded: wh-words at start (those are open questions).
_YES_NO_STARTERS = (
    'is ', 'are ', 'was ', 'were ', 'did ', 'does ', 'do ',
    'has ', 'have ', 'had ', 'will ', 'should ', 'can ', 'could ',
    'may ', 'might ',
)


def _looks_adversarial(
    query: str,
    intermediate_results: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str]:
    """Return (is_adversarial, channel). channel ∈
    {capability_flag, surface_marker, yes_no_shape, ''}.
    """
    if intermediate_results and 'counterfactual_reasoning' in intermediate_results:
        return True, 'capability_flag'
    if not query:
        return False, ''
    if _ADVERSARIAL_TIER2_RE.search(query):
        return True, 'surface_marker'
    q_low = query.strip().lower()
    if any(q_low.startswith(s) for s in _YES_NO_STARTERS):
        # Heuristic: yes/no questions are premise-checks more often than
        # genuine open extraction. Route to orchestrator where C1 already
        # handles the unknown-vs-concrete trade-off.
        return True, 'yes_no_shape'
    return False, ''


# ----- patterns: fact-like reasoning shape -----

# Tightened tier-3: only patterns that carry low false-premise risk.
# The bare predicate shapes `what did/does/has X V` and `how did X V` are
# DELIBERATELY ABSENT — they catch real factual questions but also
# false-premise adversarial ones, and a query-only classifier cannot
# distinguish the two. Those questions fall through to orchestrator
# where C1's evidence-gated selector handles the unknown trade-off.
_REASONING_PATTERNS = (
    # what motivated / caused / prompted / led / drove
    # Narrow: causal/motivational questions are intrinsically reasoning,
    # rarely false-premise as a syntactic class.
    (re.compile(r'^\s*what\s+(?:motivated|caused|prompted|led|drove|inspired)\b',
                re.IGNORECASE), 'cause_motivation'),
    # why-causal questions
    (re.compile(r'^\s*why\s+\S', re.IGNORECASE), 'why_causal'),
    # what does/did X (mental-state verb)
    # Attitude/belief questions ask about a subject's stance — even on
    # false-premise topic the answer "she had no opinion / was unaware"
    # is reasoning-shaped, not a hallucinated fact.
    # Verbs are intentionally restricted to mental-state ones; physical
    # observation verbs (see/notice/find/consider) are excluded because
    # they let factual "what did X see at Y" questions leak into RC and
    # become hallucinations on false-premise events.
    (re.compile(
        r'^\s*what\s+(?:does|did)\s+\S+\s+'
        r'(?:think|feel|realize|believe|wonder|learn|view|understand)\b',
        re.IGNORECASE), 'attitude_belief'),
    # what is/are the relationship between …
    (re.compile(r'^\s*what\s+(?:is|are)\s+the\s+relationship\b', re.IGNORECASE),
     'relationship'),
    # property/attribute questions: "what X (is|are) Y to Z" — generic
    # shape for asking which items hold an attribute toward a subject
    # (e.g. "what topics are interesting to her", "what symbols are
    # important to him"). Multi-hop by nature; the "to/of/for" connector
    # constrains it tightly enough to avoid factual false-premise leak.
    (re.compile(
        r'^\s*what\s+\S+\s+(?:are|is)\s+\S+\s+(?:to|of|for)\s+\S+',
        re.IGNORECASE), 'property_attribute'),
)


def _looks_reasoning(query: str) -> Tuple[bool, str]:
    """Return (matches_reasoning_shape, pattern_name)."""
    if not query:
        return False, ''
    for pat, name in _REASONING_PATTERNS:
        if pat.search(query):
            return True, name
    return False, ''


# ----- main classifier -----

def classify_route_v2(
    query: str,
    has_temporal_result: bool,
    has_reasoning_chain: bool,
    intermediate_results: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str, Dict[str, Any]]:
    """Deterministic answer-path classifier.

    Returns
    -------
    answer_path   : 'temporal' | 'orchestrator' | 'reasoning_chain'
    reason        : tier label, e.g. 'temporal_explicit',
                    'adversarial_capability_flag', 'reasoning_shape',
                    'reasoning_unavailable_fallback', 'fallback'
    flags         : per-tier hits captured for telemetry —
                    {temporal, adversarial, adversarial_channel,
                     reasoning_shape, reasoning_pattern}
    """
    flags: Dict[str, Any] = {}

    is_temporal = _looks_temporal(query) if query else False
    is_adv, adv_channel = _looks_adversarial(query, intermediate_results)
    is_reasoning, reasoning_pattern = _looks_reasoning(query)

    flags['temporal'] = is_temporal
    flags['adversarial'] = is_adv
    flags['adversarial_channel'] = adv_channel
    flags['reasoning_shape'] = is_reasoning
    flags['reasoning_pattern'] = reasoning_pattern

    # Tier 1: temporal explicit. Only honour if a temporal result actually
    # came back from the temporal_reasoning chain — otherwise the path
    # cannot be served.
    if is_temporal and has_temporal_result:
        return 'temporal', 'temporal_explicit', flags

    # Tier 2: adversarial / counterfactual / premise-check. Routes to
    # orchestrator where C1's evidence-gated selector handles the
    # unknown-vs-concrete trade-off correctly.
    if is_adv:
        return 'orchestrator', f'adversarial_{adv_channel}', flags

    # Tier 3: fact-like reasoning shape. Only honour if reasoning_chain
    # actually ran and produced a result; otherwise drop to fallback.
    if is_reasoning:
        if has_reasoning_chain:
            return 'reasoning_chain', f'reasoning_shape:{reasoning_pattern}', flags
        # If the shape says reasoning but the chain isn't available, we
        # still want to record that the policy WANTED reasoning_chain,
        # so callers can decide whether to force it on subsequent runs.
        return 'orchestrator', 'reasoning_unavailable_fallback', flags

    # Tier 4: fallback
    return 'orchestrator', 'fallback', flags
