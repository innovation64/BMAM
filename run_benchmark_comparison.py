#!/usr/bin/env python3
"""
BMAM vs MemOS Benchmark Comparison Runner
Comprehensive comparison runner with standardized benchmarks
"""

import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from evaluation.benchmark_comparison import BenchmarkComparison
from evaluation.benchmark_datasets import BenchmarkDatasets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ComprehensiveBenchmarkRunner:
    """Run comprehensive benchmark comparison between BMAM and MemOS"""

    def __init__(self, memos_path: str = None, output_dir: str = None):
        self.datasets = BenchmarkDatasets()
        self.comparator = BenchmarkComparison(memos_path=memos_path)

        self.output_dir = Path(output_dir) if output_dir else Path("results/benchmark_comparison")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def setup_datasets(self, force_refresh: bool = False):
        """Download and prepare all benchmark datasets"""
        print("\n📊 Setting up benchmark datasets...")

        datasets_to_download = ["longmemeval", "locomo", "needle_in_haystack", "memorybank"]

        for dataset_name in datasets_to_download:
            print(f"  📥 Preparing {dataset_name}...")
            success = await self.datasets.download_dataset(dataset_name, force_refresh)

            if success:
                print(f"  ✅ {dataset_name} ready")
            else:
                print(f"  ❌ {dataset_name} failed to download")

        print("✅ Dataset setup completed")

    async def run_comprehensive_comparison(self, benchmarks: list = None, include_custom: bool = True):
        """Run comprehensive comparison across all benchmarks"""

        if benchmarks is None:
            benchmarks = ["longmemeval", "locomo"]
            if include_custom:
                benchmarks.extend(["needle_in_haystack", "memorybank"])

        print("\n" + "=" * 80)
        print("BMAM vs MemOS COMPREHENSIVE BENCHMARK COMPARISON")
        print("=" * 80)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Benchmarks: {', '.join(benchmarks)}")
        print("=" * 80)

        all_results = {
            "timestamp": datetime.now().isoformat(),
            "benchmarks": benchmarks,
            "comparisons": {},
            "overall_summary": {}
        }

        # Run each benchmark
        for benchmark in benchmarks:
            print(f"\n🔄 Running {benchmark} benchmark comparison...")

            try:
                # Run BMAM evaluation
                print(f"  🧠 Evaluating BMAM on {benchmark}...")
                bmam_results = await self.comparator.run_bmam_evaluation(benchmark)

                # Load MemOS baseline results
                print(f"  📊 Loading MemOS baseline for {benchmark}...")
                memos_results = self.comparator.load_memos_results(benchmark)

                # Generate comparison
                print(f"  📈 Generating comparison report...")
                comparison = await self.comparator.generate_comparison_report(
                    bmam_results, memos_results, benchmark
                )

                all_results["comparisons"][benchmark] = comparison

                # Print benchmark results
                report = self.comparator.generate_comparison_report_text(comparison)
                print(f"\n{report}")

                # Save individual benchmark results
                self.comparator.save_comparison_results(comparison, benchmark)

                print(f"✅ {benchmark} comparison completed")

            except Exception as e:
                logger.error(f"❌ {benchmark} comparison failed: {e}")
                all_results["comparisons"][benchmark] = {"error": str(e)}

        # Generate overall summary
        all_results["overall_summary"] = self._generate_overall_summary(all_results["comparisons"])

        # Save comprehensive results
        self._save_comprehensive_results(all_results)

        # Print overall summary
        self._print_overall_summary(all_results["overall_summary"])

        return all_results

    def _generate_overall_summary(self, comparisons: dict) -> dict:
        """Generate overall summary across all benchmarks"""
        summary = {
            "total_benchmarks": len(comparisons),
            "successful_comparisons": 0,
            "failed_comparisons": 0,
            "bmam_wins": 0,
            "memos_wins": 0,
            "total_metrics": 0,
            "avg_improvement": 0,
            "benchmark_scores": {},
            "key_findings": []
        }

        all_improvements = []

        for benchmark, comparison in comparisons.items():
            if "error" in comparison:
                summary["failed_comparisons"] += 1
                continue

            summary["successful_comparisons"] += 1

            # Extract summary from each benchmark
            bench_summary = comparison.get("summary", {})

            summary["bmam_wins"] += bench_summary.get("bmam_wins", 0)
            summary["memos_wins"] += bench_summary.get("memos_wins", 0)
            summary["total_metrics"] += bench_summary.get("total_metrics", 0)

            if "avg_improvement" in bench_summary:
                all_improvements.append(bench_summary["avg_improvement"])

            # Store benchmark-specific scores
            summary["benchmark_scores"][benchmark] = {
                "bmam_wins": bench_summary.get("bmam_wins", 0),
                "memos_wins": bench_summary.get("memos_wins", 0),
                "improvement": bench_summary.get("avg_improvement", 0)
            }

        # Calculate overall averages
        if all_improvements:
            summary["avg_improvement"] = sum(all_improvements) / len(all_improvements)

        # Generate key findings
        if summary["bmam_wins"] > summary["memos_wins"]:
            summary["key_findings"].append(
                f"BMAM outperforms MemOS overall ({summary['bmam_wins']} vs {summary['memos_wins']} metric wins)"
            )
        elif summary["memos_wins"] > summary["bmam_wins"]:
            summary["key_findings"].append(
                f"MemOS outperforms BMAM overall ({summary['memos_wins']} vs {summary['bmam_wins']} metric wins)"
            )
        else:
            summary["key_findings"].append("Performance is closely matched between BMAM and MemOS")

        if summary["avg_improvement"] > 15:
            summary["key_findings"].append("BMAM shows significant performance improvements")
        elif summary["avg_improvement"] > 5:
            summary["key_findings"].append("BMAM shows moderate performance improvements")
        elif summary["avg_improvement"] < -5:
            summary["key_findings"].append("MemOS shows better performance in several areas")

        # Best and worst performing benchmarks for BMAM
        if summary["benchmark_scores"]:
            best_benchmark = max(
                summary["benchmark_scores"].items(),
                key=lambda x: x[1]["improvement"]
            )
            worst_benchmark = min(
                summary["benchmark_scores"].items(),
                key=lambda x: x[1]["improvement"]
            )

            summary["key_findings"].append(
                f"BMAM performs best on {best_benchmark[0]} (+{best_benchmark[1]['improvement']:.1f}%)"
            )
            summary["key_findings"].append(
                f"BMAM needs improvement on {worst_benchmark[0]} ({worst_benchmark[1]['improvement']:.1f}%)"
            )

        return summary

    def _print_overall_summary(self, summary: dict):
        """Print overall summary report"""
        print("\n" + "=" * 80)
        print("OVERALL COMPARISON SUMMARY")
        print("=" * 80)

        print(f"Benchmarks Compared: {summary['successful_comparisons']}/{summary['total_benchmarks']}")
        print(f"Total Metrics: {summary['total_metrics']}")
        print(f"BMAM Wins: {summary['bmam_wins']}")
        print(f"MemOS Wins: {summary['memos_wins']}")
        print(f"Average Improvement: {summary['avg_improvement']:.1f}%")
        print("")

        print("BENCHMARK PERFORMANCE:")
        print("-" * 40)
        for benchmark, scores in summary["benchmark_scores"].items():
            winner = "BMAM" if scores["bmam_wins"] > scores["memos_wins"] else "MemOS"
            print(f"{benchmark:20} | {winner:6} | {scores['improvement']:+6.1f}%")
        print("")

        print("KEY FINDINGS:")
        print("-" * 40)
        for finding in summary["key_findings"]:
            print(f"• {finding}")

        print("=" * 80)

    def _save_comprehensive_results(self, results: dict):
        """Save comprehensive comparison results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON results
        json_file = self.output_dir / f"comprehensive_benchmark_comparison_{timestamp}.json"
        import json
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        # Save text summary
        summary_file = self.output_dir / f"benchmark_summary_{timestamp}.txt"
        with open(summary_file, 'w') as f:
            f.write("BMAM vs MemOS Comprehensive Benchmark Comparison\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"Generated: {results['timestamp']}\n")
            f.write(f"Benchmarks: {', '.join(results['benchmarks'])}\n\n")

            summary = results["overall_summary"]
            f.write("OVERALL SUMMARY:\n")
            f.write("-" * 30 + "\n")
            f.write(f"Successful Comparisons: {summary['successful_comparisons']}/{summary['total_benchmarks']}\n")
            f.write(f"BMAM Wins: {summary['bmam_wins']}\n")
            f.write(f"MemOS Wins: {summary['memos_wins']}\n")
            f.write(f"Average Improvement: {summary['avg_improvement']:.1f}%\n\n")

            f.write("KEY FINDINGS:\n")
            f.write("-" * 30 + "\n")
            for finding in summary["key_findings"]:
                f.write(f"• {finding}\n")

        # Update latest results
        latest_file = self.output_dir / "latest_comprehensive_comparison.json"
        with open(latest_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n📁 Results saved to {self.output_dir}")
        print(f"   📄 Detailed: {json_file.name}")
        print(f"   📄 Summary: {summary_file.name}")

    async def run_quick_comparison(self):
        """Run a quick comparison on core benchmarks"""
        print("\n⚡ Running quick benchmark comparison...")
        return await self.run_comprehensive_comparison(
            benchmarks=["longmemeval", "locomo"],
            include_custom=False
        )

    async def run_full_comparison(self):
        """Run full comparison including custom benchmarks"""
        print("\n🔬 Running full benchmark comparison...")
        return await self.run_comprehensive_comparison(
            benchmarks=None,
            include_custom=True
        )

    def list_available_benchmarks(self):
        """List all available benchmarks"""
        print("\n📋 Available Benchmarks:")
        print("-" * 40)

        info = self.datasets.get_dataset_info()
        for name, config in info.items():
            status = "✅ Ready" if config["cached"] else "📥 Not Downloaded"
            print(f"{name:20} | {status:12} | {config['description']}")

            if config["cached"] and "cache_info" in config:
                cache_info = config["cache_info"]
                print(f"{'':20} | {'':12} | Items: {cache_info.get('item_count', 'unknown')}")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="BMAM vs MemOS Benchmark Comparison")

    parser.add_argument(
        "--mode",
        choices=["quick", "full", "setup", "list"],
        default="quick",
        help="Comparison mode: quick (core benchmarks), full (all benchmarks), setup (download datasets), list (show benchmarks)"
    )

    parser.add_argument(
        "--benchmarks",
        nargs="+",
        choices=["longmemeval", "locomo", "needle_in_haystack", "memorybank"],
        help="Specific benchmarks to run"
    )

    parser.add_argument(
        "--memos-path",
        type=str,
        help="Path to MemOS installation"
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory for results"
    )

    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Force refresh of cached datasets"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize runner
    runner = ComprehensiveBenchmarkRunner(
        memos_path=args.memos_path,
        output_dir=args.output_dir
    )

    try:
        if args.mode == "setup":
            print("🔧 Setting up benchmark datasets...")
            await runner.setup_datasets(force_refresh=args.force_refresh)

        elif args.mode == "list":
            runner.list_available_benchmarks()

        elif args.mode == "quick":
            await runner.setup_datasets()
            await runner.run_quick_comparison()

        elif args.mode == "full":
            await runner.setup_datasets()
            await runner.run_full_comparison()

        elif args.benchmarks:
            await runner.setup_datasets()
            await runner.run_comprehensive_comparison(benchmarks=args.benchmarks)

    except KeyboardInterrupt:
        print("\n⚠️  Comparison interrupted by user")
    except Exception as e:
        print(f"\n❌ Comparison failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())