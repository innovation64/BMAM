#!/usr/bin/env python3
"""
Learning Log Analysis Script
Analyzes data/learning_log.jsonl to provide insights on memory retrieval strategies,
plasticity trends, KG triggering, and reflection behavior.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Any
import statistics

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class LearningLogAnalyzer:
    """Analyzer for learning_log.jsonl"""

    def __init__(self, log_path: str = "data/learning_log.jsonl"):
        self.log_path = Path(log_path)
        self.events = []
        self.analysis = {}

    def load_log(self):
        """Load learning log from JSONL file"""
        if not self.log_path.exists():
            print(f"Error: Log file not found at {self.log_path}")
            sys.exit(1)

        with open(self.log_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    self.events.append(event)
                except json.JSONDecodeError as e:
                    print(f"Warning: Invalid JSON at line {line_num}: {e}")

        print(f"Loaded {len(self.events)} events from {self.log_path}")

    def analyze_strategy_distribution(self) -> Dict[str, Any]:
        """Analyze distribution of retrieval strategies"""
        strategies = Counter()
        strategies_by_query_type = defaultdict(Counter)

        for event in self.events:
            if event.get("event") != "smart_retrieve":
                continue

            payload = event.get("payload", {})
            strategy = payload.get("strategy", "unknown")
            strategies[strategy] += 1

            # Categorize query type based on query text
            query = payload.get("query", "")
            if query.lower().startswith("when"):
                query_type = "temporal"
            elif query.lower().startswith("what"):
                query_type = "factual"
            elif query.lower().startswith("who"):
                query_type = "entity"
            else:
                query_type = "other"

            strategies_by_query_type[query_type][strategy] += 1

        return {
            "overall_distribution": dict(strategies),
            "by_query_type": {k: dict(v) for k, v in strategies_by_query_type.items()},
            "total_retrievals": sum(strategies.values())
        }

    def analyze_plasticity_trends(self) -> Dict[str, Any]:
        """Analyze plasticity value trends"""
        plasticity_values = []
        plasticity_by_source = defaultdict(list)
        plasticity_over_time = []

        for event in self.events:
            if event.get("event") != "smart_retrieve":
                continue

            payload = event.get("payload", {})
            top_memories = payload.get("top_memories", [])
            timestamp = event.get("timestamp", "")

            for mem in top_memories:
                plasticity = mem.get("plasticity")
                if plasticity is not None:
                    plasticity_values.append(plasticity)
                    source = mem.get("source", "unknown")
                    plasticity_by_source[source].append(plasticity)

                    if timestamp:
                        plasticity_over_time.append({
                            "timestamp": timestamp,
                            "plasticity": plasticity,
                            "source": source
                        })

        if not plasticity_values:
            return {"error": "No plasticity data found"}

        return {
            "overall_stats": {
                "mean": statistics.mean(plasticity_values),
                "median": statistics.median(plasticity_values),
                "min": min(plasticity_values),
                "max": max(plasticity_values),
                "std_dev": statistics.stdev(plasticity_values) if len(plasticity_values) > 1 else 0,
                "total_samples": len(plasticity_values)
            },
            "by_source": {
                source: {
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "count": len(values)
                }
                for source, values in plasticity_by_source.items()
            },
            "over_time": plasticity_over_time[:20]  # First 20 samples
        }

    def analyze_kg_triggering(self) -> Dict[str, Any]:
        """Analyze knowledge graph triggering patterns"""
        kg_trigger_stats = {
            "total_retrievals": 0,
            "kg_triggered": 0,
            "kg_not_triggered": 0
        }

        kg_triggers_by_query = defaultdict(int)
        queries_with_kg = []
        queries_without_kg = []

        for event in self.events:
            if event.get("event") != "smart_retrieve":
                continue

            payload = event.get("payload", {})
            kg_triggered = payload.get("kg_triggered", False)
            query = payload.get("query", "")

            kg_trigger_stats["total_retrievals"] += 1

            if kg_triggered:
                kg_trigger_stats["kg_triggered"] += 1
                queries_with_kg.append(query)
            else:
                kg_trigger_stats["kg_not_triggered"] += 1
                queries_without_kg.append(query)

        kg_trigger_rate = (kg_trigger_stats["kg_triggered"] /
                          max(kg_trigger_stats["total_retrievals"], 1))

        return {
            "trigger_stats": kg_trigger_stats,
            "trigger_rate": kg_trigger_rate,
            "sample_queries_with_kg": queries_with_kg[:5],
            "sample_queries_without_kg": queries_without_kg[:5]
        }

    def analyze_reflection_triggering(self) -> Dict[str, Any]:
        """Analyze reflection triggering patterns"""
        reflection_stats = {
            "total_retrievals": 0,
            "reflection_triggered": 0,
            "reflection_not_triggered": 0
        }

        queries_with_reflection = []
        queries_without_reflection = []

        for event in self.events:
            if event.get("event") != "smart_retrieve":
                continue

            payload = event.get("payload", {})
            reflection_triggered = payload.get("reflection_triggered", False)
            query = payload.get("query", "")

            reflection_stats["total_retrievals"] += 1

            if reflection_triggered:
                reflection_stats["reflection_triggered"] += 1
                queries_with_reflection.append(query)
            else:
                reflection_stats["reflection_not_triggered"] += 1
                queries_without_reflection.append(query)

        reflection_trigger_rate = (reflection_stats["reflection_triggered"] /
                                   max(reflection_stats["total_retrievals"], 1))

        return {
            "trigger_stats": reflection_stats,
            "trigger_rate": reflection_trigger_rate,
            "sample_queries_with_reflection": queries_with_reflection[:5],
            "sample_queries_without_reflection": queries_without_reflection[:5]
        }

    def analyze_coverage_ratio(self) -> Dict[str, Any]:
        """Analyze coverage ratio distribution"""
        coverage_values = []
        coverage_by_strategy = defaultdict(list)

        for event in self.events:
            if event.get("event") != "smart_retrieve":
                continue

            payload = event.get("payload", {})
            coverage = payload.get("coverage_ratio")
            strategy = payload.get("strategy", "unknown")

            if coverage is not None:
                coverage_values.append(coverage)
                coverage_by_strategy[strategy].append(coverage)

        if not coverage_values:
            return {"error": "No coverage data found"}

        return {
            "overall_stats": {
                "mean": statistics.mean(coverage_values),
                "median": statistics.median(coverage_values),
                "min": min(coverage_values),
                "max": max(coverage_values),
                "count": len(coverage_values)
            },
            "by_strategy": {
                strategy: {
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "count": len(values)
                }
                for strategy, values in coverage_by_strategy.items()
            }
        }

    def analyze_memory_counts(self) -> Dict[str, Any]:
        """Analyze memory count patterns"""
        total_memories = []
        top_memories_count = []

        for event in self.events:
            if event.get("event") != "smart_retrieve":
                continue

            payload = event.get("payload", {})
            total = payload.get("total_memories", 0)
            top = len(payload.get("top_memories", []))

            total_memories.append(total)
            top_memories_count.append(top)

        if not total_memories:
            return {"error": "No memory count data found"}

        return {
            "total_memories": {
                "mean": statistics.mean(total_memories),
                "median": statistics.median(total_memories),
                "min": min(total_memories),
                "max": max(total_memories)
            },
            "top_memories_returned": {
                "mean": statistics.mean(top_memories_count),
                "median": statistics.median(top_memories_count),
                "min": min(top_memories_count),
                "max": max(top_memories_count)
            }
        }

    def run_full_analysis(self) -> Dict[str, Any]:
        """Run complete analysis"""
        self.load_log()

        print("\n" + "=" * 80)
        print("LEARNING LOG ANALYSIS")
        print("=" * 80)

        # Strategy distribution
        print("\n[1/6] Analyzing retrieval strategy distribution...")
        self.analysis["strategy_distribution"] = self.analyze_strategy_distribution()

        # Plasticity trends
        print("[2/6] Analyzing plasticity trends...")
        self.analysis["plasticity_trends"] = self.analyze_plasticity_trends()

        # KG triggering
        print("[3/6] Analyzing KG triggering patterns...")
        self.analysis["kg_triggering"] = self.analyze_kg_triggering()

        # Reflection triggering
        print("[4/6] Analyzing reflection triggering patterns...")
        self.analysis["reflection_triggering"] = self.analyze_reflection_triggering()

        # Coverage ratio
        print("[5/6] Analyzing coverage ratio...")
        self.analysis["coverage_ratio"] = self.analyze_coverage_ratio()

        # Memory counts
        print("[6/6] Analyzing memory counts...")
        self.analysis["memory_counts"] = self.analyze_memory_counts()

        return self.analysis

    def generate_report(self) -> str:
        """Generate human-readable analysis report"""
        lines = []
        lines.append("\n" + "=" * 80)
        lines.append("LEARNING LOG ANALYSIS REPORT")
        lines.append("=" * 80)
        lines.append(f"Log file: {self.log_path}")
        lines.append(f"Total events: {len(self.events)}")
        lines.append("")

        # Strategy Distribution
        if "strategy_distribution" in self.analysis:
            sd = self.analysis["strategy_distribution"]
            lines.append("RETRIEVAL STRATEGY DISTRIBUTION")
            lines.append("-" * 40)
            lines.append(f"Total retrievals: {sd['total_retrievals']}")
            lines.append("\nOverall strategy distribution:")
            for strategy, count in sorted(sd["overall_distribution"].items(),
                                         key=lambda x: x[1], reverse=True):
                pct = (count / sd['total_retrievals']) * 100
                lines.append(f"  {strategy}: {count} ({pct:.1f}%)")
            lines.append("")

        # Plasticity Trends
        if "plasticity_trends" in self.analysis:
            pt = self.analysis["plasticity_trends"]
            if "error" not in pt:
                lines.append("PLASTICITY TRENDS")
                lines.append("-" * 40)
                stats = pt["overall_stats"]
                lines.append(f"Mean plasticity: {stats['mean']:.4f}")
                lines.append(f"Median plasticity: {stats['median']:.4f}")
                lines.append(f"Range: {stats['min']:.4f} - {stats['max']:.4f}")
                lines.append(f"Std deviation: {stats['std_dev']:.4f}")
                lines.append(f"Total samples: {stats['total_samples']}")
                lines.append("")

        # KG Triggering
        if "kg_triggering" in self.analysis:
            kg = self.analysis["kg_triggering"]
            lines.append("KNOWLEDGE GRAPH TRIGGERING")
            lines.append("-" * 40)
            lines.append(f"KG trigger rate: {kg['trigger_rate']:.2%}")
            lines.append(f"  Triggered: {kg['trigger_stats']['kg_triggered']}")
            lines.append(f"  Not triggered: {kg['trigger_stats']['kg_not_triggered']}")
            lines.append("")

        # Reflection Triggering
        if "reflection_triggering" in self.analysis:
            rf = self.analysis["reflection_triggering"]
            lines.append("REFLECTION TRIGGERING")
            lines.append("-" * 40)
            lines.append(f"Reflection trigger rate: {rf['trigger_rate']:.2%}")
            lines.append(f"  Triggered: {rf['trigger_stats']['reflection_triggered']}")
            lines.append(f"  Not triggered: {rf['trigger_stats']['reflection_not_triggered']}")
            lines.append("")

        # Coverage Ratio
        if "coverage_ratio" in self.analysis:
            cr = self.analysis["coverage_ratio"]
            if "error" not in cr:
                lines.append("COVERAGE RATIO")
                lines.append("-" * 40)
                stats = cr["overall_stats"]
                lines.append(f"Mean coverage: {stats['mean']:.2%}")
                lines.append(f"Median coverage: {stats['median']:.2%}")
                lines.append("")

        # Memory Counts
        if "memory_counts" in self.analysis:
            mc = self.analysis["memory_counts"]
            if "error" not in mc:
                lines.append("MEMORY COUNTS")
                lines.append("-" * 40)
                lines.append(f"Avg total memories: {mc['total_memories']['mean']:.1f}")
                lines.append(f"Avg top memories returned: {mc['top_memories_returned']['mean']:.1f}")
                lines.append("")

        lines.append("=" * 80)
        return "\n".join(lines)

    def save_analysis(self, output_path: str):
        """Save analysis results to JSON file"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.analysis, f, indent=2, ensure_ascii=False)

        print(f"\nAnalysis saved to: {output_file}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze learning log")
    parser.add_argument(
        "--log",
        type=str,
        default="data/learning_log.jsonl",
        help="Path to learning log file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results/learning_log_analysis.json",
        help="Output path for analysis JSON"
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Only print report, don't save JSON"
    )

    args = parser.parse_args()

    # Run analysis
    analyzer = LearningLogAnalyzer(args.log)
    analyzer.run_full_analysis()

    # Print report
    report = analyzer.generate_report()
    print(report)

    # Save results
    if not args.report_only:
        analyzer.save_analysis(args.output)


if __name__ == "__main__":
    main()
