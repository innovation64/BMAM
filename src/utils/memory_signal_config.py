import json
import logging
import os
from copy import deepcopy
from typing import Dict, Any

logger = logging.getLogger(__name__)

DEFAULT_MEMORY_SIGNAL_CONFIG: Dict[str, Any] = {
    # NOTE: These are generic defaults. For domain-specific tuning,
    # override via BMAM_MEMORY_SIGNAL_CONFIG env var or config/memory_signal_config.json
    "retrieval": {
        "factual_keywords": [
            # Generic learning/knowledge verbs
            "research",
            "researched",
            "study",
            "studied",
            "learn",
            "learned",
            # Generic activity verbs
            "work",
            "works",
            "working",
            "job",
            "career",
            "attend",
            "attended",
            "join",
            "joined",
            "specialize",
            "specializing",
            "field",
            "fields"
        ],
        "alpha_boost": 0.15,
        "alpha_cap": 0.7,
        "alpha_floor": 0.3
    },
    "answer_cleaning": {
        "noise_tokens": [
            "nature",
            "forests",
            "forest",
            "hiking",
            "hike",
            "mountains",
            "playing",
            "play",
            "game",
            "games",
            "fun",
            "happy",
            "weather",
            "day",
            "night",
            "morning",
            "evening"
        ],
        "filler_tokens": [
            "and",
            "the",
            "or",
            "with",
            "about",
            "from",
            "to",
            "in",
            "at",
            "on",
            "a",
            "an"
        ],
        "noise_ratio_threshold": 0.6
    },
    "memory_scoring": {
        "weights": {
            "confidence": 0.30,
            "hit_count": 0.08,
            "recency": 0.12,
            "decay": 0.05,
            "hybrid_score": 0.45,
            "coverage_bonus": 0.0,
            "conflict_penalty": 0.0
        },
        "kg_boost": 0.15,
        "recency_half_life_hours": 12,
        "hit_count_lambda": 0.2,
        "defaults": {
            "confidence": 0.6
        }
    },
    "fallback_filters": {
        "min_candidate_overlap": 1,
        "query_groups": [
            {
                "name": "education_fields",
                "query_keywords": [
                    "field",
                    "fields",
                    "education",
                    "career",
                    "job",
                    "path"
                ],
                "candidate_keywords": [
                    "field",
                    "fields",
                    "career",
                    "counsel",
                    "education",
                    "mental health"
                ]
            },
            {
                "name": "research_focus",
                "query_keywords": [
                    "research",
                    "studied",
                    "studies",
                    "investigate",
                    "look into",
                    "explore"
                ],
                "candidate_keywords": [
                    "adoption",
                    "research",
                    "study",
                    "investigation",
                    "project"
                ]
            }
        ]
    }
}

_CONFIG_CACHE: Dict[str, Any] = {}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _resolve_config_path(config_path: str = None) -> str:
    if config_path:
        return config_path

    env_path = os.getenv("BMAM_MEMORY_SIGNAL_CONFIG")
    if env_path:
        return env_path

    default_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "config",
        "memory_signal_config.json"
    )
    return os.path.abspath(default_path)


def load_memory_signal_config(config_path: str = None, force_reload: bool = False) -> Dict[str, Any]:
    """
    Load memory signal configuration (retrieval + answer cleaning heuristics).

    Returns merged result of defaults and optional JSON config file so that
    downstream code can rely on stable keys while allowing customization.
    """
    global _CONFIG_CACHE

    cache_key = config_path or "default"
    if not force_reload and cache_key in _CONFIG_CACHE:
        return _CONFIG_CACHE[cache_key]

    merged_config = deepcopy(DEFAULT_MEMORY_SIGNAL_CONFIG)
    path = _resolve_config_path(config_path)

    try:
        with open(path, "r", encoding="utf-8") as fp:
            file_config = json.load(fp)
        merged_config = _deep_merge(merged_config, file_config)
    except FileNotFoundError:
        logger.warning("Memory signal config file not found at %s. Using defaults.", path)
    except (json.JSONDecodeError) as exc:
        logger.error("Failed to parse memory signal config %s: %s. Using defaults.", path, exc)

    _CONFIG_CACHE[cache_key] = merged_config
    return merged_config


def reset_memory_signal_config_cache() -> None:
    """Testing helper to clear cached configuration."""
    _CONFIG_CACHE.clear()
