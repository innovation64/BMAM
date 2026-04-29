"""Structured audit telemetry sink — JSONL only, no behaviour changes.

Off by default. Enable by setting `BMAM_AUDIT_LOG_PATH=/path/to/file.jsonl`
in the environment, or programmatically via `audit_log.enable(path)`.

Probes are passive: they emit JSON lines describing thresholds, scores,
filter decisions, and expansion outputs. They never alter the data they
observe. Memory contents are NOT recorded — only ids, hashes, and scalar
features. See `tests/test_unstable_33.py` for the recommended runner that
binds question metadata around each `process_user_input` call.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Optional


def _safe_default(o: Any) -> str:
    try:
        return str(o)
    except Exception:  # noqa: BLE001
        return f"<unserializable: {type(o).__name__}>"


class AuditLog:
    """Append-only JSONL telemetry sink. Thread-safety is not a goal — the
    probes run on the asyncio event loop, one request at a time during
    benchmark replay. If concurrent use is ever needed, add a lock here.
    """

    def __init__(self) -> None:
        self._fp = None
        self._enabled = False
        self._path: Optional[Path] = None
        self._qid: Optional[str] = None
        self._question: Optional[str] = None

    # ----- lifecycle -----

    def enable(self, path: str | os.PathLike) -> "AuditLog":
        if self._enabled:
            return self
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._fp = self._path.open('a', buffering=1, encoding='utf-8')
        self._enabled = True
        # mark a session header so multiple runs are distinguishable
        self.event('session_start', pid=os.getpid())
        return self

    def disable(self) -> None:
        try:
            if self._fp:
                self._fp.flush()
                self._fp.close()
        finally:
            self._fp = None
            self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def path(self) -> Optional[Path]:
        return self._path

    # ----- per-question binding -----

    def set_question(
        self,
        qid: str,
        question: str,
        category: Any = None,
        gold: Any = None,
        **extra: Any,
    ) -> None:
        """Bind the probe context to a benchmark question. Subsequent
        `event()` calls auto-tag with this qid until set_question() is
        called again or `clear_question()` is invoked.
        """
        self._qid = str(qid) if qid is not None else None
        self._question = question
        self.event(
            'question_start',
            qid=self._qid,
            question=question,
            category=category,
            gold=gold,
            **extra,
        )

    def clear_question(self) -> None:
        if self._qid is not None:
            self.event('question_end', qid=self._qid)
        self._qid = None
        self._question = None

    # ----- emit -----

    def event(self, probe: str, **fields: Any) -> None:
        """Emit a probe event. No-op when disabled."""
        if not self._enabled or self._fp is None:
            return
        rec = {
            'ts': round(time.time(), 3),
            'probe': probe,
        }
        if self._qid is not None and 'qid' not in fields:
            rec['qid'] = self._qid
        rec.update(fields)
        try:
            line = json.dumps(rec, ensure_ascii=False, default=_safe_default)
            self._fp.write(line + '\n')
        except Exception:  # noqa: BLE001 - probe must never crash callers
            pass


# ----- module singleton ----------------------------------------------------

_AUDIT = AuditLog()


def enable(path: str | os.PathLike) -> AuditLog:
    return _AUDIT.enable(path)


def disable() -> None:
    _AUDIT.disable()


def is_enabled() -> bool:
    return _AUDIT.enabled


def set_question(qid: str, question: str, **extra: Any) -> None:
    _AUDIT.set_question(qid, question, **extra)


def clear_question() -> None:
    _AUDIT.clear_question()


def event(probe: str, **fields: Any) -> None:
    """Module-level shorthand for `_AUDIT.event(...)`. Safe to call from any
    code path; no-op when audit is disabled.
    """
    _AUDIT.event(probe, **fields)


def memory_id(memory: Any) -> str:
    """Stable, content-derived id for an audit memory reference. Never
    records the memory body itself — only an 8-char SHA256 prefix.
    """
    if memory is None:
        return ''
    if isinstance(memory, dict):
        for k in ('id', 'memory_id', '_id'):
            v = memory.get(k)
            if v:
                return str(v)
        body = memory.get('content') or memory.get('text') or memory.get('memory') or ''
    else:
        body = getattr(memory, 'content', None) or getattr(memory, 'id', None) or str(memory)
    s = str(body).encode('utf-8', 'ignore')
    return hashlib.sha256(s).hexdigest()[:12]


# ----- env auto-enable -----------------------------------------------------

_path_from_env = os.getenv('BMAM_AUDIT_LOG_PATH')
if _path_from_env:
    try:
        _AUDIT.enable(_path_from_env)
    except Exception:  # noqa: BLE001
        # silent — telemetry should never break a run
        pass
