#!/usr/bin/env python3
"""
KG Comparison Experiment Runner
批量运行无KG、低KG、基准配置的对比实验
"""

import asyncio
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KGComparisonRunner:
    """Run comparison experiments across different KG configurations"""

    def __init__(self, output_dir: str = "results/kg_comparison"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.configs_dir = project_root / "configs/experiment_configs"
        self.eval_script = project_root / "scripts/evaluation/run_bmam_memos_eval.py"

        self.experiments = [
            {
                "name": "No KG",
                "config_file": "no_kg_config.json",
                "description": "完全禁用知识图谱"
            },
            {
                "name": "Low KG",
                "config_file": "low_kg_config.json",
                "description": "降低知识图谱权重"
            },
            {
                "name": "Baseline",
                "config_file": "baseline_config.json",
                "description": "当前生产配置"
            }
        ]

        self.results = {}

    def run_experiment(self, experiment: Dict[str, str]) -> Dict[str, Any]:
        """Run a single experiment"""
        name = experiment["name"]
        config_path = self.configs_dir / experiment["config_file"]

        if not config_path.exists():
            logger.error(f"Config file not found: {config_path}")
            return {"error": f"Config file not found: {config_path}"}

        logger.info(f"\n{'=' * 80}")
        logger.info(f"Running experiment: {name}")
        logger.info(f"Config: {config_path}")
        logger.info(f"Description: {experiment['description']}")
        logger.info(f"{'=' * 80}\n")

        # Prepare command
        cmd = [
            sys.executable,
            str(self.eval_script),
            "--config", str(config_path),
            "--output", str(self.output_dir / name.lower().replace(' ', '_'))
        ]

        try:
            # Run evaluation
            start_time = datetime.now()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()

            if result.returncode == 0:
                logger.info(f"✅ {name} completed successfully in {elapsed:.1f}s")

                # Parse results from output
                return {
                    "name": name,
                    "status": "success",
                    "duration": elapsed,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            else:
                logger.error(f"❌ {name} failed with return code {result.returncode}")
                return {
                    "name": name,
                    "status": "failed",
                    "return_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }

        except subprocess.TimeoutExpired:
            logger.error(f"❌ {name} timed out after 10 minutes")
            return {
                "name": name,
                "status": "timeout"
            }
        except Exception as e:
            logger.error(f"❌ {name} encountered error: {e}")
            return {
                "name": name,
                "status": "error",
                "error": str(e)
            }

    def collect_results(self) -> Dict[str, Any]:
        """Collect results from all experiments"""
        collected_results = {}

        for experiment in self.experiments:
            name = experiment["name"]
            exp_dir = self.output_dir / name.lower().replace(' ', '_')

            # Find latest summary file
            summary_files = list(exp_dir.glob("summary_*.json"))
            if not summary_files:
                logger.warning(f"No summary file found for {name}")
                continue

            latest_summary = max(summary_files, key=lambda p: p.stat().st_mtime)

            with open(latest_summary, 'r', encoding='utf-8') as f:
                summary = json.load(f)

            collected_results[name] = summary

        return collected_results

    def generate_comparison_report(self, results: Dict[str, Any]) -> str:
        """Generate comparison report"""
        lines = []
        lines.append("\n" + "=" * 80)
        lines.append("KG CONFIGURATION COMPARISON REPORT")
        lines.append("=" * 80)
        lines.append(f"Timestamp: {datetime.now().isoformat()}")
        lines.append(f"Experiments: {len(results)}")
        lines.append("")

        # Summary table
        lines.append("ACCURACY COMPARISON")
        lines.append("-" * 40)

        # Sort by accuracy
        sorted_results = sorted(
            results.items(),
            key=lambda x: x[1].get('accuracy', 0),
            reverse=True
        )

        for rank, (name, data) in enumerate(sorted_results, 1):
            accuracy = data.get('accuracy', 0)
            correct = data.get('correct', 0)
            total = data.get('total', 0)

            lines.append(f"{rank}. {name}")
            lines.append(f"   Accuracy: {accuracy:.2%}")
            lines.append(f"   Correct: {correct}/{total}")
            lines.append("")

        # Detailed comparison
        if len(results) >= 2:
            lines.append("DETAILED COMPARISON")
            lines.append("-" * 40)

            baseline_name = "Baseline"
            if baseline_name in results:
                baseline_acc = results[baseline_name].get('accuracy', 0)

                for name, data in results.items():
                    if name == baseline_name:
                        continue

                    acc = data.get('accuracy', 0)
                    diff = acc - baseline_acc
                    diff_pct = (diff / baseline_acc) * 100 if baseline_acc > 0 else 0

                    lines.append(f"{name} vs {baseline_name}:")
                    lines.append(f"  Absolute difference: {diff:+.2%}")
                    lines.append(f"  Relative difference: {diff_pct:+.1f}%")
                    lines.append("")

        # Recommendations
        lines.append("INSIGHTS")
        lines.append("-" * 40)

        if len(sorted_results) > 0:
            best_name, best_data = sorted_results[0]
            lines.append(f"• Best configuration: {best_name} ({best_data.get('accuracy', 0):.2%})")

        if "No KG" in results and "Baseline" in results:
            no_kg_acc = results["No KG"].get('accuracy', 0)
            baseline_acc = results["Baseline"].get('accuracy', 0)

            if baseline_acc > no_kg_acc:
                improvement = ((baseline_acc - no_kg_acc) / no_kg_acc) * 100
                lines.append(f"• KG provides {improvement:.1f}% improvement over no KG")
            else:
                lines.append("• KG does not provide clear benefit - investigate further")

        if "Low KG" in results and "Baseline" in results:
            low_kg_acc = results["Low KG"].get('accuracy', 0)
            baseline_acc = results["Baseline"].get('accuracy', 0)

            if abs(low_kg_acc - baseline_acc) < 0.02:
                lines.append("• Low KG configuration performs similarly to baseline")
            elif low_kg_acc > baseline_acc:
                lines.append("• Consider reducing KG weight for better performance")
            else:
                lines.append("• Current KG weighting appears optimal")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)

    def save_comparison_results(self, results: Dict[str, Any], report: str):
        """Save comparison results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save results JSON
        results_file = self.output_dir / f"comparison_results_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"📁 Comparison results saved to: {results_file}")

        # Save report
        report_file = self.output_dir / f"comparison_report_{timestamp}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"📄 Comparison report saved to: {report_file}")

    def run_all_experiments(self):
        """Run all comparison experiments"""
        print("\n" + "=" * 80)
        print("KG CONFIGURATION COMPARISON EXPERIMENTS")
        print("=" * 80)
        print(f"Running {len(self.experiments)} experiments")
        print("=" * 80 + "\n")

        start_time = datetime.now()

        # Run each experiment
        for i, experiment in enumerate(self.experiments, 1):
            print(f"\n[Experiment {i}/{len(self.experiments)}]")
            result = self.run_experiment(experiment)
            self.results[experiment['name']] = result

        # Collect results
        logger.info("\nCollecting results from all experiments...")
        collected = self.collect_results()

        # Generate report
        report = self.generate_comparison_report(collected)
        print(report)

        # Save results
        self.save_comparison_results(collected, report)

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        print(f"\n⏱️  Total time: {elapsed:.1f}s")
        print(f"📁 Results directory: {self.output_dir}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run KG configuration comparison experiments"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results/kg_comparison",
        help="Output directory for comparison results"
    )

    args = parser.parse_args()

    runner = KGComparisonRunner(output_dir=args.output)
    runner.run_all_experiments()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Comparison interrupted by user")
    except Exception as e:
        print(f"\n❌ Comparison failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
