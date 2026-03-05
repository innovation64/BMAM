"""
Pipeline Tracer — Diagnostic logging for benchmark execution path tracing.

Records every decision point in the query processing pipeline so you can see
exactly which components ran, which were skipped, and why.

Usage:
    from src.diagnostics.pipeline_tracer import get_tracer

    tracer = get_tracer()
    tracer.start_query("What is X?")
    tracer.record("fast_path", decision="skipped", reason="no pattern match")
    tracer.record("hippocampal_loop", decision="early_stop", reason="confidence=0.87 >= 0.85",
                  iterations=1, memories_before=5, memories_after=5)
    tracer.end_query(answer="X is ...", answer_path="orchestrator")

    # After benchmark, generate report:
    tracer.print_report()
    tracer.save_report("data/diagnostics/trace_report.json")
"""

import asyncio
import json
import logging
import os
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class QueryTrace:
    """Trace record for a single query."""

    __slots__ = ('query', 'start_time', 'end_time', 'events', 'answer',
                 'answer_path', 'correct', 'expected_answer', 'query_type')

    def __init__(self, query: str):
        self.query = query
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.events: List[Dict[str, Any]] = []
        self.answer: Optional[str] = None
        self.answer_path: Optional[str] = None
        self.correct: Optional[bool] = None
        self.expected_answer: Optional[str] = None
        self.query_type: Optional[str] = None

    def record(self, component: str, **kwargs):
        """Record a decision point."""
        self.events.append({
            'component': component,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        })

    def to_dict(self) -> Dict[str, Any]:
        duration_ms = None
        if self.end_time and self.start_time:
            duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        return {
            'query': self.query,
            'query_type': self.query_type,
            'answer': self.answer,
            'answer_path': self.answer_path,
            'correct': self.correct,
            'expected_answer': self.expected_answer,
            'duration_ms': duration_ms,
            'events': self.events,
        }


class PipelineTracer:
    """
    Traces the execution path of every query through the BMAM pipeline.

    Thread-safe. Accumulates traces across a full benchmark run,
    then produces a summary report showing which components fired,
    which were skipped, and common failure patterns.
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._lock = threading.Lock()
        self._async_lock = None  # Lazy init for async lock
        self._traces: List[QueryTrace] = []
        self._current: Optional[QueryTrace] = None

    def _get_async_lock(self) -> asyncio.Lock:
        """Lazy initialization of async lock (must be called in async context)"""
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        return self._async_lock

    # ------------------------------------------------------------------
    # Recording API (sync)
    # ------------------------------------------------------------------

    def start_query(self, query: str, query_type: str = None):
        """Begin tracing a new query (sync)."""
        if not self.enabled:
            return
        trace = QueryTrace(query)
        trace.query_type = query_type
        with self._lock:
            self._current = trace

    def record(self, component: str, **kwargs):
        """Record a decision at a pipeline component (sync)."""
        if not self.enabled:
            return
        with self._lock:
            if self._current:
                self._current.record(component, **kwargs)

    def end_query(self, answer: str = None, answer_path: str = None,
                  correct: bool = None, expected_answer: str = None):
        """Finish tracing the current query (sync)."""
        if not self.enabled:
            return
        with self._lock:
            if self._current:
                self._current.end_time = datetime.now()
                self._current.answer = answer
                self._current.answer_path = answer_path
                self._current.correct = correct
                self._current.expected_answer = expected_answer
                self._traces.append(self._current)
                self._current = None

    # ------------------------------------------------------------------
    # Recording API (async)
    # ------------------------------------------------------------------

    async def async_start_query(self, query: str, query_type: str = None):
        """Begin tracing a new query (async, for use in async contexts)."""
        if not self.enabled:
            return
        trace = QueryTrace(query)
        trace.query_type = query_type
        async with self._get_async_lock():
            self._current = trace

    async def async_record(self, component: str, **kwargs):
        """Record a decision at a pipeline component (async)."""
        if not self.enabled:
            return
        async with self._get_async_lock():
            if self._current:
                self._current.record(component, **kwargs)

    async def async_end_query(
        self, answer: str = None, answer_path: str = None,
        correct: bool = None, expected_answer: str = None
    ):
        """Finish tracing the current query (async)."""
        if not self.enabled:
            return
        async with self._get_async_lock():
            if self._current:
                self._current.end_time = datetime.now()
                self._current.answer = answer
                self._current.answer_path = answer_path
                self._current.correct = correct
                self._current.expected_answer = expected_answer
                self._traces.append(self._current)
                self._current = None

    # ------------------------------------------------------------------
    # Reporting API
    # ------------------------------------------------------------------

    def print_report(self):
        """Print a concise summary to stdout."""
        report = self._build_report()
        total = report['total_queries']
        if total == 0:
            print("[PipelineTracer] No queries traced.")
            return

        print(f"\n{'=' * 72}")
        print(f"  PIPELINE TRACE REPORT  ({total} queries)")
        print(f"{'=' * 72}")

        # Component activation rates
        print(f"\n--- Component Activation Rates ---")
        for comp, stats in sorted(report['component_stats'].items()):
            fired = stats.get('fired', 0)
            skipped = stats.get('skipped', 0)
            total_comp = fired + skipped
            rate = (fired / total_comp * 100) if total_comp > 0 else 0
            print(f"  {comp:35s}  {fired:3d}/{total_comp:3d}  ({rate:5.1f}%)")

        # Answer path distribution
        print(f"\n--- Answer Path Distribution ---")
        for path, count in sorted(report['answer_path_distribution'].items(),
                                   key=lambda x: -x[1]):
            pct = count / total * 100
            print(f"  {path:25s}  {count:3d}  ({pct:5.1f}%)")

        # Accuracy by path
        if report.get('accuracy_by_path'):
            print(f"\n--- Accuracy by Answer Path ---")
            for path, stats in sorted(report['accuracy_by_path'].items()):
                correct = stats['correct']
                total_p = stats['total']
                acc = (correct / total_p * 100) if total_p > 0 else 0
                print(f"  {path:25s}  {correct:3d}/{total_p:3d}  ({acc:5.1f}%)")

        # Accuracy by query type
        if report.get('accuracy_by_query_type'):
            print(f"\n--- Accuracy by Query Type ---")
            for qtype, stats in sorted(report['accuracy_by_query_type'].items()):
                correct = stats['correct']
                total_q = stats['total']
                acc = (correct / total_q * 100) if total_q > 0 else 0
                print(f"  {qtype:25s}  {correct:3d}/{total_q:3d}  ({acc:5.1f}%)")

        # Common skip reasons
        print(f"\n--- Common Skip/Early-Stop Reasons ---")
        for reason, count in sorted(report['skip_reasons'].items(),
                                     key=lambda x: -x[1])[:15]:
            print(f"  {reason:50s}  {count:3d}")

        # Worst-performing queries
        wrong = [t for t in self._traces if t.correct is False]
        if wrong:
            print(f"\n--- Sample Wrong Answers ({min(10, len(wrong))}/{len(wrong)}) ---")
            for t in wrong[:10]:
                events_summary = ', '.join(
                    f"{e['component']}={e.get('decision', '?')}" for e in t.events
                )
                print(f"  Q: {t.query[:70]}")
                print(f"    Path: {t.answer_path}  |  Events: {events_summary}")
                print(f"    Got: {str(t.answer or '')[:60]}")
                print(f"    Expected: {str(t.expected_answer or '')[:60]}")
                print()

        print(f"{'=' * 72}\n")

    def save_report(self, path: str):
        """Save full trace data to JSON."""
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        report = self._build_report()
        report['traces'] = [t.to_dict() for t in self._traces]
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Pipeline trace report saved to {path}")

    def _build_report(self) -> Dict[str, Any]:
        """Aggregate stats from all traces."""
        total = len(self._traces)
        component_stats: Dict[str, Dict[str, int]] = {}
        answer_path_dist: Dict[str, int] = {}
        accuracy_by_path: Dict[str, Dict[str, int]] = {}
        accuracy_by_qtype: Dict[str, Dict[str, int]] = {}
        skip_reasons: Dict[str, int] = {}

        for trace in self._traces:
            # Answer path distribution
            path = trace.answer_path or 'unknown'
            answer_path_dist[path] = answer_path_dist.get(path, 0) + 1

            # Accuracy by path
            if trace.correct is not None:
                if path not in accuracy_by_path:
                    accuracy_by_path[path] = {'correct': 0, 'total': 0}
                accuracy_by_path[path]['total'] += 1
                if trace.correct:
                    accuracy_by_path[path]['correct'] += 1

            # Accuracy by query type
            qtype = trace.query_type or 'unknown'
            if trace.correct is not None:
                if qtype not in accuracy_by_qtype:
                    accuracy_by_qtype[qtype] = {'correct': 0, 'total': 0}
                accuracy_by_qtype[qtype]['total'] += 1
                if trace.correct:
                    accuracy_by_qtype[qtype]['correct'] += 1

            # Component stats
            for event in trace.events:
                comp = event['component']
                decision = event.get('decision', 'unknown')
                if comp not in component_stats:
                    component_stats[comp] = {'fired': 0, 'skipped': 0}

                if decision in ('fired', 'used', 'triggered', 'active',
                                'enhanced', 'applied'):
                    component_stats[comp]['fired'] += 1
                elif decision in ('skipped', 'disabled', 'early_stop',
                                  'not_triggered', 'unavailable'):
                    component_stats[comp]['skipped'] += 1
                else:
                    # Treat as fired if not explicitly skipped
                    component_stats[comp]['fired'] += 1

                # Skip reasons
                reason = event.get('reason')
                if reason and decision in ('skipped', 'early_stop',
                                           'not_triggered', 'disabled'):
                    key = f"{comp}: {reason}"
                    skip_reasons[key] = skip_reasons.get(key, 0) + 1

        return {
            'total_queries': total,
            'component_stats': component_stats,
            'answer_path_distribution': answer_path_dist,
            'accuracy_by_path': accuracy_by_path,
            'accuracy_by_query_type': accuracy_by_qtype,
            'skip_reasons': skip_reasons,
        }

    def reset(self):
        """Clear all traces (e.g. between benchmark runs). (sync)"""
        with self._lock:
            self._traces.clear()
            self._current = None

    async def async_reset(self):
        """Clear all traces (async)."""
        async with self._get_async_lock():
            self._traces.clear()
            self._current = None


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_tracer_instance: Optional[PipelineTracer] = None
_tracer_lock = threading.Lock()


def get_tracer(enabled: bool = True) -> PipelineTracer:
    """Get or create the global PipelineTracer singleton."""
    global _tracer_instance
    if _tracer_instance is None:
        with _tracer_lock:
            if _tracer_instance is None:
                _tracer_instance = PipelineTracer(enabled=enabled)
    return _tracer_instance


def reset_tracer():
    """Reset the global tracer (useful between benchmark runs)."""
    global _tracer_instance
    with _tracer_lock:
        if _tracer_instance:
            _tracer_instance.reset()
        _tracer_instance = None
