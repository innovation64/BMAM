"""B-lite route-decision cache — diagnostic only, off by default.

Goal: make the answer_path decision stable across runs of the same query
so we can isolate "path drift" from "answer-generation drift" as noise
sources. NOT a final fix; if `BMAM_ROUTE_CACHE=1` is set, the same query
will keep using whichever path was chosen on the first miss — meaning a
bad first-pick will be persisted. Use only as a probe.

Cache key:
  sha256( normalized_query | user_id | session_id )
  — normalization lower-cases and collapses whitespace
  — user/session keep different speakers' contexts separate (always
    empty for skip_memory_store=True benchmark replays, which is fine)

Cache value (full RouteDecision):
  answer_path:               'orchestrator' | 'reasoning_chain' | 'temporal' | 'conversation'
  has_temporal_result:       bool
  has_reasoning_chain:       bool
  use_reasoning_chain:       bool   — gate for actually invoking the chain
  learnable_selected_agents: list[str]
  learnable_top_agent:       str | None
  learnable_top_score:       float | None
  capabilities:              list[str]   — orchestrator path only
  written_ts:                ISO timestamp (debug)

Persistence:
  metrics/cache/route_cache.json — JSON dict {key: decision}
  Loaded lazily on first lookup, written on every save (cheap; cache
  size is bounded by question count).

Switch:
  BMAM_ROUTE_CACHE=1 enables lookup + save
  BMAM_ROUTE_CACHE_PATH=<file> overrides the default location

Behaviour:
  enabled + key in cache → returns the cached RouteDecision
  enabled + key not in cache → returns None; caller runs normal route
    logic and calls save_route(...) to persist the decision
  disabled → lookup returns None and save is a no-op
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ..utils.paths import BMAMPaths


_DEFAULT_PATH = BMAMPaths.BMAM_ROOT / 'metrics' / 'cache' / 'route_cache.json'


class _RouteCache:
    """Thread-safe persistent cache. Single global instance via the module
    helpers below — never instantiate directly outside this file.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: Optional[Dict[str, Dict[str, Any]]] = None
        self._path: Optional[Path] = None

    # ---- enablement ----

    @staticmethod
    def enabled() -> bool:
        return os.getenv('BMAM_ROUTE_CACHE', '0') == '1'

    def _resolve_path(self) -> Path:
        if self._path is None:
            override = os.getenv('BMAM_ROUTE_CACHE_PATH')
            self._path = Path(override) if override else _DEFAULT_PATH
        return self._path

    # ---- load/save ----

    def _ensure_loaded(self) -> None:
        if self._data is not None:
            return
        path = self._resolve_path()
        if path.exists():
            try:
                self._data = json.loads(path.read_text())
                if not isinstance(self._data, dict):
                    self._data = {}
            except Exception:  # noqa: BLE001
                # Corrupt cache should not break the run.
                self._data = {}
        else:
            self._data = {}

    def _flush(self) -> None:
        if self._data is None:
            return
        path = self._resolve_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(json.dumps(self._data, indent=2, ensure_ascii=False))
        except Exception:  # noqa: BLE001 - probe must never break a run
            pass

    # ---- key ----

    @staticmethod
    def make_key(
        query: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        norm_query = ' '.join((query or '').lower().split())
        u = user_id or ''
        s = session_id or ''
        material = f'{norm_query}|{u}|{s}'.encode('utf-8', 'ignore')
        return hashlib.sha256(material).hexdigest()[:16]

    # ---- lookup / save ----

    def lookup(
        self,
        query: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.enabled():
            return None
        with self._lock:
            self._ensure_loaded()
            return self._data.get(self.make_key(query, user_id, session_id))

    def save(
        self,
        query: str,
        decision: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        if not self.enabled():
            return
        with self._lock:
            self._ensure_loaded()
            decision = dict(decision)  # copy
            decision.setdefault('written_ts', datetime.utcnow().isoformat() + 'Z')
            self._data[self.make_key(query, user_id, session_id)] = decision
            self._flush()


_CACHE = _RouteCache()


# ---------- module API ---------- #

def enabled() -> bool:
    return _RouteCache.enabled()


def make_key(query: str, user_id: Optional[str] = None,
             session_id: Optional[str] = None) -> str:
    return _RouteCache.make_key(query, user_id, session_id)


def lookup_route(
    query: str,
    context: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Return cached RouteDecision dict or None."""
    ctx = context or {}
    return _CACHE.lookup(
        query,
        user_id=ctx.get('user_id'),
        session_id=ctx.get('session_id'),
    )


def save_route(
    query: str,
    decision: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Persist a RouteDecision dict for `query`."""
    ctx = context or {}
    _CACHE.save(
        query,
        decision,
        user_id=ctx.get('user_id'),
        session_id=ctx.get('session_id'),
    )
