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
    Detect emotions in text using keyword dictionary (sync, fast).

    Returns:
        (detected_emotions, intensity)
    """
    keywords = get_emotion_keywords()
    text_lower = text.lower()
    detected = []
    max_intensity = 0.0

    for emotion, kws in keywords.items():
        matches = [kw for kw in kws if kw in text_lower]
        if matches:
            detected.append(emotion)
            max_intensity = max(max_intensity, 0.5 + 0.1 * (len(matches) - 1))

    return detected, min(max_intensity, 1.0)


async def detect_emotions_llm(text: str) -> Tuple[List[str], float]:
    """
    LLM-powered emotion detection — catches nuanced emotions
    that keyword matching misses (powerful, moving, therapy, proud, etc.).

    Falls back to keyword matching if LLM unavailable.
    """
    # First try keywords (fast)
    detected, intensity = detect_emotions(text)
    if detected:
        return detected, intensity

    # LLM tier — catches nuanced emotions
    try:
        from ..services.shared_openai_client import shared_client_manager
        response = await shared_client_manager.chat_completion(
            messages=[
                {"role": "system",
                 "content": "Detect the primary emotion in this text. Reply: EMOTION INTENSITY\nEMOTION = one of: joy, sadness, anger, fear, surprise, love, pride, gratitude, anxiety, neutral\nINTENSITY = 0.0 to 1.0\nExample: joy 0.7"},
                {"role": "user", "content": text[:200]}
            ],
            temperature=0,
            max_tokens=10
        )
        content = response.choices[0].message.content.strip().lower()
        parts = content.split()
        if len(parts) >= 2 and parts[0] != 'neutral':
            emotion = parts[0]
            try:
                emo_intensity = float(parts[1])
            except ValueError:
                emo_intensity = 0.6
            return [emotion], min(emo_intensity, 1.0)
    except Exception:
        pass

    return [], 0.0
