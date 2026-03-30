"""
Shared emotion detection utilities.

Single source of truth for emotion keywords. All brain regions and
coordination modules should use these functions instead of hardcoding
their own keyword lists.
"""

import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

_cached_keywords: Dict[str, List[str]] = {}


def get_emotion_keywords() -> Dict[str, List[str]]:
    """Load emotion keywords from SoulConfig → config file → minimal fallback."""
    global _cached_keywords
    if _cached_keywords:
        return _cached_keywords

    # Priority 1: SoulConfigLoader
    try:
        from ..coordination.soul_config_loader import SoulConfigLoader
        config = SoulConfigLoader()
        keywords = config.get_all_emotion_keywords('en')
        if keywords:
            _cached_keywords = keywords
            return _cached_keywords
    except Exception:
        pass

    # Priority 2: config/emotion_keywords.json
    import json
    from pathlib import Path
    config_path = Path(__file__).parent.parent.parent / 'config' / 'emotion_keywords.json'
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if data:
            _cached_keywords = data
            logger.debug(f"Loaded emotion keywords from {config_path}")
            return _cached_keywords
    except Exception:
        pass

    # Priority 3: Minimal fallback (should never reach here in production)
    logger.warning("No emotion keyword config found, using minimal defaults")
    _cached_keywords = {
        'joy': ['happy', 'excited'], 'sadness': ['sad', 'depressed'],
        'anger': ['angry', 'frustrated'], 'fear': ['afraid', 'scared'],
    }
    return _cached_keywords


def detect_emotions(text: str) -> Tuple[List[str], float]:
    """
    Detect emotions in text using shared keyword dictionary.

    Returns:
        (detected_emotions, intensity)
        intensity: 0.0-1.0 based on keyword match count
    """
    keywords = get_emotion_keywords()
    text_lower = text.lower()
    detected = []
    max_intensity = 0.0

    for emotion, kws in keywords.items():
        matches = [kw for kw in kws if kw in text_lower]
        if matches:
            detected.append(emotion)
            max_intensity = max(max_intensity, 0.3 + 0.05 * len(matches))

    return detected, min(max_intensity, 1.0)
