"""Bilingual sentence splitter for streaming TTS.

Splits response text into sentence-sized chunks suitable for progressive
TTS synthesis, handling both Chinese and English punctuation.
"""

import re
from typing import Iterator

# Sentence-ending punctuation for Chinese and English
_SENTENCE_END = re.compile(
    r'(?<=[.!?\u3002\uff01\uff1f\u2026])'  # lookbehind: . ! ? 。！？…
    r'[\s]*'                                  # optional whitespace
    r'(?=\S)'                                 # lookahead: next non-space char
)

# Also split on semicolons, colons followed by newlines, and newlines
_CLAUSE_END = re.compile(
    r'(?<=[;;\uff1b::\uff1a])\s+'             # after ; ；: ：
    r'|(?<=\n)\s*'                             # after newline
)

# Minimum chunk length before we attempt to split
MIN_CHUNK_LEN = 10
# Maximum chunk length before we force-split
MAX_CHUNK_LEN = 200


def split_sentences(text: str) -> Iterator[str]:
    """Split text into sentence-level chunks for streaming TTS.

    Yields non-empty sentence strings. Handles Chinese and English mixed text.
    Tries to keep chunks between MIN_CHUNK_LEN and MAX_CHUNK_LEN characters.
    """
    text = text.strip()
    if not text:
        return

    # First pass: split on sentence-ending punctuation
    parts = _SENTENCE_END.split(text)

    buffer = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue

        buffer = f"{buffer} {part}".strip() if buffer else part

        if len(buffer) >= MIN_CHUNK_LEN:
            # If buffer is too long, try splitting on clause boundaries
            if len(buffer) > MAX_CHUNK_LEN:
                sub_parts = _CLAUSE_END.split(buffer)
                sub_buffer = ""
                for sp in sub_parts:
                    sp = sp.strip()
                    if not sp:
                        continue
                    sub_buffer = f"{sub_buffer} {sp}".strip() if sub_buffer else sp
                    if len(sub_buffer) >= MIN_CHUNK_LEN:
                        yield sub_buffer
                        sub_buffer = ""
                if sub_buffer:
                    yield sub_buffer
                buffer = ""
            else:
                yield buffer
                buffer = ""

    if buffer:
        yield buffer


def detect_language(text: str) -> str:
    """Simple heuristic to detect whether text is primarily Chinese or English.

    Returns "zh" or "en".
    """
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    total_chars = max(len(text.strip()), 1)
    return "zh" if chinese_chars / total_chars > 0.3 else "en"
