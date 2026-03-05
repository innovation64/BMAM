#!/usr/bin/env python3
"""
BMAM Self-Evolution Harness
===========================

Systematic debugging and optimization loop inspired by:
- Anthropic's "Effective Harnesses for Long-Running Agents"
- AgentEvolver's self-questioning patterns

Evolution Cycle:
  1. Health Check  → Is the system healthy?
  2. Profile       → Run quick benchmark + profiling
  3. Diagnose      → Identify top bottleneck
  4. Propose       → Generate fix hypothesis
  5. Checkpoint    → git commit (pre-fix snapshot)
  6. Apply         → Make the fix
  7. Validate      → Re-run benchmark
  8. Decide        → If better: commit. If worse: revert
  9. Log           → Update evolution_progress.json
  10. Repeat       → Next cycle

Usage:
    # Dry run (no changes, just diagnose)
    python evaluation/scripts/self_evolution.py --dry-run --cycles 1

    # Single evolution cycle
    python evaluation/scripts/self_evolution.py --cycles 1 --samples 3

    # Full evolution loop (up to 5 cycles)
    python evaluation/scripts/self_evolution.py --cycles 5

    # Health check only
    python evaluation/scripts/self_evolution.py --health-only

    # Profile only
    python evaluation/scripts/self_evolution.py --profile-only --samples 5
"""

import asyncio
import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Suppress noisy logs during profiling
import warnings
warnings.filterwarnings('ignore')
import logging
logging.getLogger().setLevel(logging.WARNING)
for name in ['src', 'openai', 'httpx', 'httpcore', 'urllib3', 'faiss']:
    logging.getLogger(name).setLevel(logging.CRITICAL)
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

EVOLUTION_LOG_PATH = PROJECT_ROOT / 'evaluation' / 'evolution_progress.json'


class BottleneckType(str, Enum):
    RETRIEVAL_LATENCY = "retrieval_latency"
    LLM_CALL_OVERHEAD = "llm_call_overhead"
    LOW_CONFIDENCE = "low_confidence"
    MEMORY_POLLUTION = "memory_pollution"
    ROUTING_INEFFICIENCY = "routing_inefficiency"
    CONSOLIDATION_GAP = "consolidation_gap"
    UNKNOWN = "unknown"


@dataclass
class HealthReport:
    healthy: bool
    imports_ok: bool
    env_ok: bool
    memory_system_ok: bool
    smoke_test_ok: bool
    details: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ComponentTiming:
    name: str
    avg_ms: float
    count: int
    total_ms: float
    min_ms: float = 0.0
    max_ms: float = 0.0


@dataclass
class ProfileReport:
    total_queries: int
    total_time_s: float
    avg_response_time_s: float
    component_timings: List[ComponentTiming]
    accuracy: float
    correct: int
    total: int
    benchmark_name: str
    success_rate: float
    agent_activations: Dict[str, int] = field(default_factory=dict)
    memory_operations: int = 0
    kg_operations: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DiagnosticReport:
    bottleneck_type: BottleneckType
    description: str
    severity: str  # "high", "medium", "low"
    affected_component: str
    metric_value: float
    metric_unit: str
    recommendation: str
    all_bottlenecks: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class EvolutionResult:
    cycle_id: int
    bottleneck: str
    hypothesis: str
    action: str
    pre_score: float
    post_score: float
    improvement: float
    status: str  # "committed", "reverted", "dry_run", "skipped"
    git_commit: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class EvolutionLog:
    """Persistent JSON log of all evolution attempts."""

    def __init__(self, path: Path = EVOLUTION_LOG_PATH):
        self.path = path
        self._data = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            with open(self.path, 'r') as f:
                return json.load(f)
        return {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "baseline_scores": {},
            "current_scores": {},
            "evolution_cycles": [],
            "failed_attempts": [],
            "insights": [],
        }

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, 'w') as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def set_baseline(self, scores: Dict[str, float]):
        self._data["baseline_scores"] = scores
        self.save()

    def set_current(self, scores: Dict[str, float]):
        self._data["current_scores"] = scores
        self.save()

    def add_cycle(self, result: EvolutionResult):
        entry = asdict(result)
        if result.status == "committed":
            self._data["evolution_cycles"].append(entry)
        else:
            self._data["failed_attempts"].append(entry)
        self.save()

    def add_insight(self, insight: str):
        self._data["insights"].append({
            "timestamp": datetime.now().isoformat(),
            "insight": insight,
        })
        self.save()

    def get_recent_fix_types(self, n: int = 3) -> List[str]:
        """Return bottleneck types from the last n cycles (for cooldown)."""
        cycles = self._data["evolution_cycles"] + self._data["failed_attempts"]
        cycles.sort(key=lambda c: c.get("timestamp", ""), reverse=True)
        return [c.get("bottleneck", "") for c in cycles[:n]]

    @property
    def cycle_count(self) -> int:
        return len(self._data["evolution_cycles"]) + len(self._data["failed_attempts"])


class ComponentProfiler:
    """Wraps PerformanceProfiler for component-level analysis."""

    def __init__(self):
        from src.utils.performance_profiler import get_profiler, enable_profiling, reset_profiler
        reset_profiler()
        enable_profiling()
        self._profiler = get_profiler()

    def get_component_timings(self) -> List[ComponentTiming]:
        stats = self._profiler.get_stats()
        timings = []
        for op_name, op_stats in stats.items():
            timings.append(ComponentTiming(
                name=op_stats.operation,
                avg_ms=round(op_stats.avg_duration_ms, 2),
                count=op_stats.count,
                total_ms=round(op_stats.total_duration_ms, 2),
                min_ms=round(op_stats.min_duration_ms, 2),
                max_ms=round(op_stats.max_duration_ms, 2),
            ))
        timings.sort(key=lambda t: t.total_ms, reverse=True)
        return timings

    def get_report(self) -> Dict[str, Any]:
        return self._profiler.get_report()

    def reset(self):
        self._profiler.reset()


def _git_run(*args: str) -> str:
    """Run a git command in the BMAM project root, return stdout."""
    result = subprocess.run(
        ["git"] + list(args),
        cwd=str(PROJECT_ROOT.parent),
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _git_commit(message: str) -> Optional[str]:
    """Stage all changes in BMAM/ and commit. Returns commit hash or None."""
    subprocess.run(
        ["git", "add", "BMAM/"],
        cwd=str(PROJECT_ROOT.parent),
        capture_output=True,
    )
    result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=str(PROJECT_ROOT.parent),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    sha = _git_run("rev-parse", "--short", "HEAD")
    return sha


def _git_revert_to(commit_sha: str):
    """Revert BMAM/ to a specific commit."""
    subprocess.run(
        ["git", "checkout", commit_sha, "--", "BMAM/"],
        cwd=str(PROJECT_ROOT.parent),
        capture_output=True,
    )


class EvolutionHarness:
    """
    Anthropic-style harness for incremental BMAM optimization.

    Principles:
    1. Progress tracking (evolution_progress.json)
    2. Git-based checkpoints (every fix = one commit)
    3. Health checks first (never optimize a broken system)
    4. Incremental scope (one fix at a time)
    5. Self-correction (auto-revert on regression)
    """

    def __init__(self, dry_run: bool = False, samples: int = 5, verbose: bool = False):
        self.dry_run = dry_run
        self.samples = samples
        self.verbose = verbose
        self.log = EvolutionLog()
        self.profiler = ComponentProfiler()

    # ─── Phase 1: Health Check ──────────────────────────────────────

    async def health_check(self) -> HealthReport:
        """Validate that the system is in a workable state."""
        errors = []
        imports_ok = self._check_imports(errors)
        env_ok = self._check_env(errors)
        memory_ok = self._check_memory_system(errors)

        smoke_ok = False
        if imports_ok and env_ok:
            smoke_ok = await self._smoke_test(errors)

        healthy = imports_ok and env_ok and memory_ok and smoke_ok
        return HealthReport(
            healthy=healthy,
            imports_ok=imports_ok,
            env_ok=env_ok,
            memory_system_ok=memory_ok,
            smoke_test_ok=smoke_ok,
            errors=errors,
        )

    def _check_imports(self, errors: List[str]) -> bool:
        """Verify all core modules can be imported."""
        modules = [
            "src.coordination.brain_coordinator_refactored",
            "src.coordination.hrm_coordinator_wrapper",
            "src.coordination.metrics_collector",
            "src.utils.performance_profiler",
            "src.memory.memory_system",
            "src.agents.brain_regions.hippocampus_agent.core",
            "src.agents.brain_regions.temporal_lobe_agent.core",
            "src.agents.brain_regions.prefrontal_agent.core",
            "src.agents.brain_regions.amygdala_agent",
            "src.agents.brain_regions.basal_ganglia_agent",
        ]
        all_ok = True
        for mod in modules:
            try:
                __import__(mod)
            except Exception as e:
                errors.append(f"Import failed: {mod} — {e}")
                all_ok = False
        return all_ok

    def _check_env(self, errors: List[str]) -> bool:
        """Verify environment variables are set."""
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / '.env')
        key = os.getenv("OPENAI_API_KEY", "")
        if not key or key == "sk-xxx":
            errors.append("OPENAI_API_KEY not set or placeholder in BMAM/.env")
            return False
        return True

    def _check_memory_system(self, errors: List[str]) -> bool:
        """Verify data directories exist."""
        data_dir = PROJECT_ROOT / 'data'
        if not data_dir.exists():
            data_dir.mkdir(parents=True, exist_ok=True)
        for subdir in ['memory', 'cache', 'state']:
            (data_dir / subdir).mkdir(parents=True, exist_ok=True)
        return True

    async def _smoke_test(self, errors: List[str]) -> bool:
        """Quick 1-query smoke test to verify the system responds."""
        try:
            from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
            coord = BrainInspiredCoordinator()
            await coord.start_system()
            result = await coord.process_user_input("Hello, how are you?")
            await coord.shutdown()
            if not result or not result.success:
                errors.append(f"Smoke test failed: {getattr(result, 'error', 'no response')}")
                return False
            return True
        except Exception as e:
            errors.append(f"Smoke test exception: {e}")
            return False

    # ─── Phase 2: Profile ───────────────────────────────────────────

    async def profile_system(self, benchmark: str = "locomo") -> ProfileReport:
        """Run a quick benchmark with profiling instrumentation."""
        self.profiler.reset()
        start_time = time.time()

        # Run quick_validate-style benchmark
        result = await self._run_benchmark(benchmark)
        elapsed = time.time() - start_time

        # Collect profiler data
        timings = self.profiler.get_component_timings()

        correct = result.get('correct', 0)
        total = result.get('total', 1)
        accuracy = correct / total * 100 if total > 0 else 0.0

        return ProfileReport(
            total_queries=total,
            total_time_s=round(elapsed, 2),
            avg_response_time_s=round(elapsed / max(total, 1), 2),
            component_timings=timings,
            accuracy=accuracy,
            correct=correct,
            total=total,
            benchmark_name=benchmark,
            success_rate=correct / max(total, 1) * 100,
        )

    async def _run_benchmark(self, benchmark: str) -> Dict[str, Any]:
        """Run a quick benchmark, reusing quick_validate patterns."""
        from evaluation.scripts.quick_validate import (
            test_locomo, test_longmemeval, test_prefeval, test_personamem,
        )
        runners = {
            "locomo": lambda: test_locomo(self.samples),
            "longmemeval": lambda: test_longmemeval(self.samples),
            "prefeval": lambda: test_prefeval(self.samples),
            "personamem": lambda: test_personamem(self.samples, users=1),
        }
        runner = runners.get(benchmark)
        if not runner:
            return {"error": f"Unknown benchmark: {benchmark}", "correct": 0, "total": 0}
        return await runner()

    # ─── Phase 3: Diagnose ──────────────────────────────────────────

    def diagnose(self, profile: ProfileReport) -> DiagnosticReport:
        """Identify the top bottleneck from profiling data."""
        bottlenecks = []

        # 1. Check retrieval latency
        retrieval_ops = [t for t in profile.component_timings
                         if any(k in t.name.lower() for k in
                                ['retriev', 'search', 'faiss', 'bm25', 'hybrid'])]
        if retrieval_ops:
            worst = max(retrieval_ops, key=lambda t: t.avg_ms)
            if worst.avg_ms > 500:
                bottlenecks.append({
                    "type": BottleneckType.RETRIEVAL_LATENCY,
                    "severity": "high" if worst.avg_ms > 2000 else "medium",
                    "component": worst.name,
                    "value": worst.avg_ms,
                    "unit": "ms",
                    "description": f"{worst.name} averaging {worst.avg_ms:.0f}ms per call",
                    "recommendation": (
                        "Consider pre-filtering search space, reducing k, "
                        "or caching frequent queries"
                    ),
                })

        # 2. Check LLM call overhead
        llm_ops = [t for t in profile.component_timings
                    if any(k in t.name.lower() for k in ['llm', 'openai', 'gpt', 'chat'])]
        if llm_ops:
            total_llm_ms = sum(t.total_ms for t in llm_ops)
            total_all_ms = profile.total_time_s * 1000
            if total_all_ms > 0 and total_llm_ms / total_all_ms > 0.7:
                bottlenecks.append({
                    "type": BottleneckType.LLM_CALL_OVERHEAD,
                    "severity": "high",
                    "component": "LLM calls",
                    "value": round(total_llm_ms / total_all_ms * 100, 1),
                    "unit": "% of total time",
                    "description": (
                        f"LLM calls consume {total_llm_ms / total_all_ms * 100:.0f}% "
                        f"of total processing time"
                    ),
                    "recommendation": (
                        "Reduce LLM call count per query, use caching, "
                        "or batch prompts"
                    ),
                })

        # 3. Check accuracy (low confidence)
        if profile.accuracy < 60:
            bottlenecks.append({
                "type": BottleneckType.LOW_CONFIDENCE,
                "severity": "high" if profile.accuracy < 40 else "medium",
                "component": "overall_accuracy",
                "value": profile.accuracy,
                "unit": "%",
                "description": f"Benchmark accuracy is {profile.accuracy:.1f}%",
                "recommendation": (
                    "Check retrieval relevance, memory consolidation, "
                    "and KG coverage"
                ),
            })

        # 4. Check for routing inefficiency (if many agents activated but low accuracy)
        if profile.agent_activations:
            avg_agents = sum(profile.agent_activations.values()) / max(profile.total_queries, 1)
            if avg_agents > 3 and profile.accuracy < 70:
                bottlenecks.append({
                    "type": BottleneckType.ROUTING_INEFFICIENCY,
                    "severity": "medium",
                    "component": "routing",
                    "value": avg_agents,
                    "unit": "agents/query",
                    "description": (
                        f"Average {avg_agents:.1f} agents activated per query "
                        f"with only {profile.accuracy:.1f}% accuracy"
                    ),
                    "recommendation": "Improve routing precision to activate fewer, more relevant agents",
                })

        # 5. Check response time
        if profile.avg_response_time_s > 10:
            bottlenecks.append({
                "type": BottleneckType.RETRIEVAL_LATENCY,
                "severity": "high" if profile.avg_response_time_s > 30 else "medium",
                "component": "end_to_end",
                "value": profile.avg_response_time_s,
                "unit": "seconds",
                "description": f"Average response time is {profile.avg_response_time_s:.1f}s",
                "recommendation": "Profile individual components to find the slowest stage",
            })

        # Sort by severity then value
        severity_order = {"high": 0, "medium": 1, "low": 2}
        bottlenecks.sort(key=lambda b: (severity_order.get(b["severity"], 9), -b["value"]))

        if not bottlenecks:
            return DiagnosticReport(
                bottleneck_type=BottleneckType.UNKNOWN,
                description="No obvious bottlenecks detected",
                severity="low",
                affected_component="none",
                metric_value=profile.accuracy,
                metric_unit="%",
                recommendation="System looks healthy. Consider deeper analysis.",
            )

        top = bottlenecks[0]
        return DiagnosticReport(
            bottleneck_type=top["type"],
            description=top["description"],
            severity=top["severity"],
            affected_component=top["component"],
            metric_value=top["value"],
            metric_unit=top["unit"],
            recommendation=top["recommendation"],
            all_bottlenecks=bottlenecks,
        )

    # ─── Phase 4: Evolution Cycle ───────────────────────────────────

    async def evolve_one_step(
        self,
        diagnostic: DiagnosticReport,
        pre_profile: ProfileReport,
        cycle_id: int,
    ) -> EvolutionResult:
        """Execute one evolution cycle: checkpoint → fix → validate → decide."""
        hypothesis = self._generate_hypothesis(diagnostic)

        if self.dry_run:
            return EvolutionResult(
                cycle_id=cycle_id,
                bottleneck=diagnostic.description,
                hypothesis=hypothesis,
                action="(dry run — no changes applied)",
                pre_score=pre_profile.accuracy,
                post_score=pre_profile.accuracy,
                improvement=0.0,
                status="dry_run",
            )

        # Checkpoint before fix
        pre_sha = _git_commit(
            f"evolution: pre-cycle-{cycle_id} checkpoint\n\n"
            f"Bottleneck: {diagnostic.description}\n"
            f"Score: {pre_profile.accuracy:.1f}%"
        )

        # The actual fix is NOT automated — this harness identifies
        # what to fix and tracks the result. The fix itself should be
        # applied by the developer or Claude Code via /evolve skill.
        action = (
            f"[Manual action required]\n"
            f"  Bottleneck: {diagnostic.bottleneck_type.value}\n"
            f"  Component: {diagnostic.affected_component}\n"
            f"  Hypothesis: {hypothesis}\n"
            f"  Recommendation: {diagnostic.recommendation}"
        )

        return EvolutionResult(
            cycle_id=cycle_id,
            bottleneck=diagnostic.description,
            hypothesis=hypothesis,
            action=action,
            pre_score=pre_profile.accuracy,
            post_score=pre_profile.accuracy,
            improvement=0.0,
            status="diagnosed",
            git_commit=pre_sha,
        )

    def _generate_hypothesis(self, diagnostic: DiagnosticReport) -> str:
        """Generate a fix hypothesis based on bottleneck type."""
        hypotheses = {
            BottleneckType.RETRIEVAL_LATENCY: (
                f"Reduce {diagnostic.affected_component} latency by "
                f"pre-filtering search space or adjusting k parameter"
            ),
            BottleneckType.LLM_CALL_OVERHEAD: (
                "Reduce LLM call count by caching intermediate results "
                "or batching multiple queries into single prompts"
            ),
            BottleneckType.LOW_CONFIDENCE: (
                "Improve retrieval relevance by tuning fusion weights, "
                "expanding KG coverage, or adjusting confidence thresholds"
            ),
            BottleneckType.MEMORY_POLLUTION: (
                "Clean stale memories by running forgetting cycle "
                "or improving deduplication in consolidation"
            ),
            BottleneckType.ROUTING_INEFFICIENCY: (
                "Improve query routing by fine-tuning the learnable router "
                "or adjusting brain-region activation thresholds"
            ),
            BottleneckType.CONSOLIDATION_GAP: (
                "Run consolidation cycle to transfer important episodic "
                "memories into semantic memory and knowledge graph"
            ),
        }
        return hypotheses.get(
            diagnostic.bottleneck_type,
            f"Investigate {diagnostic.affected_component} for optimization opportunities",
        )

    # ─── Phase 5: Full Evolution Loop ───────────────────────────────

    async def run_evolution(
        self,
        max_cycles: int = 5,
        benchmark: str = "locomo",
    ):
        """Run the full evolution loop."""
        print("=" * 60)
        print("BMAM Self-Evolution Harness")
        print(f"  Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"  Max cycles: {max_cycles}")
        print(f"  Samples per benchmark: {self.samples}")
        print(f"  Benchmark: {benchmark}")
        print("=" * 60)

        # Step 1: Health check
        print("\n[Phase 1] Health Check...")
        health = await self.health_check()
        self._print_health(health)
        if not health.healthy:
            print("\nSystem is NOT healthy. Fix errors before evolving.")
            return

        no_improvement_count = 0

        for cycle in range(1, max_cycles + 1):
            cycle_id = self.log.cycle_count + 1
            print(f"\n{'='*60}")
            print(f"  Evolution Cycle {cycle}/{max_cycles} (global #{cycle_id})")
            print(f"{'='*60}")

            # Step 2: Profile
            print("\n[Phase 2] Profiling system...")
            profile = await self.profile_system(benchmark)
            self._print_profile(profile)

            # Record baseline on first cycle
            if cycle == 1:
                self.log.set_baseline({benchmark: profile.accuracy})

            # Step 3: Diagnose
            print("\n[Phase 3] Diagnosing bottlenecks...")
            diagnostic = self.diagnose(profile)
            self._print_diagnostic(diagnostic)

            # Cooldown: skip if same fix type attempted recently
            recent = self.log.get_recent_fix_types(3)
            if diagnostic.bottleneck_type.value in recent:
                print(f"\n  Cooldown: {diagnostic.bottleneck_type.value} "
                      f"was attempted in last 3 cycles. Skipping.")
                self.log.add_insight(
                    f"Cycle {cycle_id}: skipped {diagnostic.bottleneck_type.value} (cooldown)"
                )
                no_improvement_count += 1
                if no_improvement_count >= 2:
                    print("\n  No new improvements for 2 cycles. Stopping.")
                    break
                continue

            # Step 4: Evolve
            print("\n[Phase 4] Evolution step...")
            result = await self.evolve_one_step(diagnostic, profile, cycle_id)
            self._print_result(result)

            # Log
            self.log.add_cycle(result)
            self.log.set_current({benchmark: result.post_score})

            if result.improvement <= 0:
                no_improvement_count += 1
            else:
                no_improvement_count = 0

            if no_improvement_count >= 2:
                print("\n  No improvement for 2 consecutive cycles. Stopping.")
                break

        print("\n" + "=" * 60)
        print("Evolution complete.")
        print(f"  Log saved to: {EVOLUTION_LOG_PATH}")
        print("=" * 60)

    # ─── Standalone modes ───────────────────────────────────────────

    async def run_health_only(self):
        """Run health check and print report."""
        print("BMAM Health Check")
        print("=" * 40)
        health = await self.health_check()
        self._print_health(health)
        return health

    async def run_profile_only(self, benchmark: str = "locomo"):
        """Run profiling and print report."""
        print("BMAM System Profile")
        print("=" * 40)
        profile = await self.profile_system(benchmark)
        self._print_profile(profile)
        diagnostic = self.diagnose(profile)
        self._print_diagnostic(diagnostic)
        return profile, diagnostic

    # ─── Display helpers ────────────────────────────────────────────

    def _print_health(self, health: HealthReport):
        status = "HEALTHY" if health.healthy else "UNHEALTHY"
        print(f"\n  Status: {status}")
        print(f"  Imports:       {'OK' if health.imports_ok else 'FAIL'}")
        print(f"  Environment:   {'OK' if health.env_ok else 'FAIL'}")
        print(f"  Memory System: {'OK' if health.memory_system_ok else 'FAIL'}")
        print(f"  Smoke Test:    {'OK' if health.smoke_test_ok else 'FAIL'}")
        for err in health.errors:
            print(f"    ERROR: {err}")

    def _print_profile(self, profile: ProfileReport):
        print(f"\n  Benchmark: {profile.benchmark_name}")
        print(f"  Accuracy:  {profile.accuracy:.1f}% ({profile.correct}/{profile.total})")
        print(f"  Total time: {profile.total_time_s:.1f}s")
        print(f"  Avg response: {profile.avg_response_time_s:.1f}s")
        if profile.component_timings:
            print(f"\n  Top components by time:")
            for t in profile.component_timings[:10]:
                print(f"    {t.name:40s}  avg={t.avg_ms:8.1f}ms  "
                      f"total={t.total_ms:10.1f}ms  n={t.count}")

    def _print_diagnostic(self, diagnostic: DiagnosticReport):
        print(f"\n  Top bottleneck: [{diagnostic.severity.upper()}] "
              f"{diagnostic.bottleneck_type.value}")
        print(f"  Description: {diagnostic.description}")
        print(f"  Component:   {diagnostic.affected_component}")
        print(f"  Metric:      {diagnostic.metric_value} {diagnostic.metric_unit}")
        print(f"  Recommendation: {diagnostic.recommendation}")
        if len(diagnostic.all_bottlenecks) > 1:
            print(f"\n  Other bottlenecks ({len(diagnostic.all_bottlenecks) - 1}):")
            for b in diagnostic.all_bottlenecks[1:]:
                print(f"    [{b['severity']}] {b['type'].value}: {b['description']}")

    def _print_result(self, result: EvolutionResult):
        print(f"\n  Cycle #{result.cycle_id}: {result.status}")
        print(f"  Bottleneck: {result.bottleneck}")
        print(f"  Hypothesis: {result.hypothesis}")
        print(f"  Score: {result.pre_score:.1f}% -> {result.post_score:.1f}% "
              f"({result.improvement:+.1f}%)")
        if result.git_commit:
            print(f"  Git commit: {result.git_commit}")
        print(f"  Action:\n{result.action}")


async def main():
    parser = argparse.ArgumentParser(
        description='BMAM Self-Evolution Harness',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry-run diagnosis (no changes)
  python evaluation/scripts/self_evolution.py --dry-run --cycles 1

  # Health check only
  python evaluation/scripts/self_evolution.py --health-only

  # Profile with 5 samples
  python evaluation/scripts/self_evolution.py --profile-only --samples 5

  # Full evolution loop
  python evaluation/scripts/self_evolution.py --cycles 5 --samples 3
        """,
    )
    parser.add_argument('--cycles', type=int, default=3,
                        help='Max evolution cycles (default: 3)')
    parser.add_argument('--samples', type=int, default=5,
                        help='Samples per benchmark run (default: 5)')
    parser.add_argument('--benchmark', type=str, default='locomo',
                        choices=['locomo', 'longmemeval', 'prefeval', 'personamem'],
                        help='Benchmark to use (default: locomo)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Diagnose only, no changes or commits')
    parser.add_argument('--health-only', action='store_true',
                        help='Run health check and exit')
    parser.add_argument('--profile-only', action='store_true',
                        help='Run profiling and exit')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')

    args = parser.parse_args()
    harness = EvolutionHarness(
        dry_run=args.dry_run,
        samples=args.samples,
        verbose=args.verbose,
    )

    if args.health_only:
        await harness.run_health_only()
    elif args.profile_only:
        await harness.run_profile_only(args.benchmark)
    else:
        await harness.run_evolution(
            max_cycles=args.cycles,
            benchmark=args.benchmark,
        )


if __name__ == '__main__':
    asyncio.run(main())
