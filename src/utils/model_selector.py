"""
🔥 P1-5: 智能模型选择器
Smart Model Selector - dynamically select LLM based on query complexity
"""

import re
from typing import Dict, Any, Optional
from .config import get_settings, get_logger

logger = get_logger(__name__)


def select_model_for_query(
    query: str,
    task_type: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    根据查询复杂度和任务类型动态选择模型

    Simple queries use fast_llm_model (gpt-4o-mini)
    Complex queries use default_llm_model or heavy_llm_model (gpt-4o)

    Args:
        query: User query string
        task_type: Optional task type hint
            - 'consolidation': Memory consolidation (use heavy)
            - 'complex_reasoning': Complex reasoning task (use heavy)
            - 'extraction': Entity/event extraction (use fast)
            - 'compression': Text compression (use fast)
            - 'summary': Summarization (use fast)
        context: Optional context dict

    Returns:
        Model name string (e.g., 'gpt-4o-mini', 'gpt-4o')
    """
    settings = get_settings()

    # Task type override
    if task_type:
        if task_type in ['consolidation', 'complex_reasoning']:
            logger.debug(f"Model selection: task_type='{task_type}' → {settings.heavy_llm_model}")
            return settings.heavy_llm_model
        elif task_type in ['extraction', 'compression', 'summary', 'forgetting']:
            logger.debug(f"Model selection: task_type='{task_type}' → {settings.fast_llm_model}")
            return settings.fast_llm_model

    # Query complexity detection
    query_lower = query.lower()

    # Simple query patterns (use fast model)
    simple_patterns = [
        r'^what is\b',           # "What is X?"
        r'^who is\b',            # "Who is X?"
        r'^define\b',            # "Define X"
        r'^when (did|was|is)\b', # "When did/was X?"
        r'^where (is|was)\b',    # "Where is/was X?"
        r'\byes\b.*\bno\b',      # "Is this yes or no?"
        r'^list\b',              # "List X"
        r'^name\b',              # "Name X"
    ]

    is_simple_pattern = any(re.match(pattern, query_lower) for pattern in simple_patterns)

    # Query length check
    word_count = len(query.split())
    is_short = word_count < 15

    # Complex query indicators (use heavy model)
    complex_indicators = [
        r'\bcompare\b',          # Comparison tasks
        r'\banalyze\b',          # Analysis tasks
        r'\bexplain why\b',      # Causal reasoning
        r'\breason\b',           # Reasoning tasks
        r'\bsynthesize\b',       # Synthesis tasks
        r'\bevaluate\b',         # Evaluation tasks
        r'\bhow (does|do|did)\b.*\bwork\b',  # "How does X work?"
        r'\bwhat.*relationship\b',           # "What is the relationship?"
        r'\bwhy\b',              # "Why" questions (causal)
    ]

    has_complex_indicator = any(re.search(pattern, query_lower) for pattern in complex_indicators)

    # Decision logic
    if has_complex_indicator or word_count > 30:
        # Complex query: use default or heavy model
        logger.debug(f"Model selection: complex query (indicators={has_complex_indicator}, words={word_count}) → {settings.default_llm_model}")
        return settings.default_llm_model

    elif is_simple_pattern and is_short:
        # Simple query: use fast model
        logger.debug(f"Model selection: simple query (pattern match, words={word_count}) → {settings.fast_llm_model}")
        return settings.fast_llm_model

    else:
        # Default: balanced model
        logger.debug(f"Model selection: default case (words={word_count}) → {settings.default_llm_model}")
        return settings.default_llm_model


def select_model_for_task(task_type: str) -> str:
    """
    根据任务类型直接选择模型（不依赖查询内容）

    Args:
        task_type: Task type
            - 'consolidation': heavy
            - 'complex_reasoning': heavy
            - 'extraction': fast
            - 'compression': fast
            - 'summary': fast
            - 'forgetting': fast
            - 'kg_extraction': fast
            - 'default': default

    Returns:
        Model name string
    """
    settings = get_settings()

    task_model_map = {
        'consolidation': settings.heavy_llm_model,
        'complex_reasoning': settings.heavy_llm_model,
        'extraction': settings.fast_llm_model,
        'compression': settings.fast_llm_model,
        'summary': settings.fast_llm_model,
        'forgetting': settings.fast_llm_model,
        'kg_extraction': settings.fast_llm_model,
        'default': settings.default_llm_model
    }

    model = task_model_map.get(task_type, settings.default_llm_model)
    logger.debug(f"Task model selection: task='{task_type}' → {model}")
    return model
