"""
Token Estimation Utilities
Token 估算工具

Provides accurate token counting with CJK-aware fallback.
提供精确的 token 计数，带有 CJK 感知的后备方案。
"""

import re
from typing import Optional

_encoder = None


def _get_encoder():
    """Lazy-load tiktoken encoder"""
    global _encoder
    if _encoder is None:
        try:
            import tiktoken
            _encoder = tiktoken.get_encoding("cl100k_base")
        except (ImportError, Exception):
            _encoder = False  # Mark as unavailable
    return _encoder if _encoder is not False else None


def _is_cjk(char: str) -> bool:
    """Check if a character is CJK (Chinese/Japanese/Korean)"""
    cp = ord(char)
    return (
        (0x4E00 <= cp <= 0x9FFF) or      # CJK Unified Ideographs
        (0x3400 <= cp <= 0x4DBF) or      # CJK Unified Ideographs Extension A
        (0xF900 <= cp <= 0xFAFF) or      # CJK Compatibility Ideographs
        (0x20000 <= cp <= 0x2A6DF) or    # CJK Unified Ideographs Extension B
        (0x2A700 <= cp <= 0x2B73F) or    # CJK Unified Ideographs Extension C
        (0x2B740 <= cp <= 0x2B81F) or    # CJK Unified Ideographs Extension D
        (0x3000 <= cp <= 0x303F) or      # CJK Symbols and Punctuation
        (0xFF00 <= cp <= 0xFFEF) or      # Halfwidth and Fullwidth Forms
        (0x3040 <= cp <= 0x309F) or      # Hiragana
        (0x30A0 <= cp <= 0x30FF) or      # Katakana
        (0xAC00 <= cp <= 0xD7AF)         # Hangul Syllables
    )


def _heuristic_estimate(text: str) -> int:
    """
    CJK-aware heuristic token estimation.

    CJK characters typically tokenize to ~1.5 tokens each.
    ASCII text averages ~4 characters per token.
    """
    if not text:
        return 0

    cjk_count = 0
    ascii_count = 0

    for char in text:
        if _is_cjk(char):
            cjk_count += 1
        else:
            ascii_count += 1

    # CJK: ~1.5 tokens per character, ASCII: ~0.25 tokens per character
    estimated = int(cjk_count * 1.5 + ascii_count / 4)
    return max(1, estimated) if text.strip() else 0


def estimate_tokens(text: str) -> int:
    """
    Estimate the number of tokens in the given text.

    Uses tiktoken (cl100k_base) when available, falls back to
    a CJK-aware heuristic that properly handles Chinese/Japanese/Korean text.

    Args:
        text: The text to estimate tokens for

    Returns:
        Estimated token count (always >= 0)
    """
    if not text:
        return 0

    encoder = _get_encoder()
    if encoder is not None:
        try:
            return len(encoder.encode(text))
        except Exception:
            pass

    return _heuristic_estimate(text)
