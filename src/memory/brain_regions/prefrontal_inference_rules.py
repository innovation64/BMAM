"""
Prefrontal Inference Rules - 前额叶推理规则

⚠️ DEPRECATED - This module has been removed in Phase 2 ⚠️

This file is kept for backward compatibility only.
All functionality has been replaced by:
- PrefrontalAgent LLM-based reasoning (prefrontal_agent.py)
- ReasoningValidator dynamic reasoning (reasoning_validator.py)

Reason for deprecation:
1. Hardcoded if-then rules were dataset-specific (LoCoMo)
2. No learning capability, couldn't generalize to new scenarios
3. Violated system design principle ("no hardcoding, only algorithms")

See:
- BMAM分布式存储层问题分析_其他脑区.md (问题4, 优化6)
- BMAM层间协作优化方案_Phase2.md
"""

import warnings
from typing import Dict, List, Any, Callable, Tuple

# Emit deprecation warning on import
warnings.warn(
    "PrefrontalInferenceRules is deprecated and will be removed in a future version. "
    "Use PrefrontalAgent's LLM-based reasoning instead.",
    DeprecationWarning,
    stacklevel=2
)


class PrefrontalInferenceRules:
    """
    DEPRECATED: Prefrontal Inference Rules

    This class is kept for backward compatibility only.
    Use PrefrontalAgent's LLM-based reasoning instead.
    """

    def __init__(self):
        warnings.warn(
            "PrefrontalInferenceRules is deprecated. Use PrefrontalAgent instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.rules: List[Dict[str, Any]] = []

    def add_rule(self, name: str, condition: Callable, conclusion: str, confidence: float) -> None:
        """Deprecated: Add rule (no-op)"""
        pass

    def apply_rules(self, facts: Dict[str, Any]) -> List[Tuple[str, float, str]]:
        """Deprecated: Apply rules (returns empty list)"""
        return []

    def get_rules_by_confidence(self, min_confidence: float = 0.5) -> List[Dict]:
        """Deprecated: Get rules (returns empty list)"""
        return []

    def remove_rule(self, name: str) -> bool:
        """Deprecated: Remove rule (no-op)"""
        return False

    def get_statistics(self) -> Dict:
        """Deprecated: Get statistics"""
        return {'total_rules': 0, 'avg_confidence': 0.0, 'deprecated': True}


def init_default_rules() -> PrefrontalInferenceRules:
    """
    DEPRECATED: Initialize default rules

    Returns an empty PrefrontalInferenceRules instance.
    All reasoning is now handled by LLM-based agents.
    """
    warnings.warn(
        "init_default_rules is deprecated. Use PrefrontalAgent for reasoning.",
        DeprecationWarning,
        stacklevel=2
    )
    return PrefrontalInferenceRules()
