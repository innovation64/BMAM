#!/usr/bin/env python3
"""
BMAM Comprehensive Evaluation Runner
Run all evaluation modules and generate comprehensive report
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime
import json
import argparse
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from evaluation.evaluation_framework import EvaluationFramework
from evaluation.memory_evaluation import MemoryEvaluator
from evaluation.agent_evaluation import AgentEvaluator
from evaluation.persona_evaluation import PersonaEvaluator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ComprehensiveEvaluator:
    """Run comprehensive BMAM system evaluation"""

    def __init__(self, output_dir: str = "results/evaluation"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.framework = EvaluationFramework(output_dir)
        self.memory_eval = MemoryEvaluator()
        self.agent_eval = AgentEvaluator()
        self.persona_eval = PersonaEvaluator()

        self.results = {}
        self.coordinator = None

    async def initialize_system(self):
        """Initialize BMAM system for evaluation"""
        try:
            from src.coordination.brain_coordinator import BrainInspiredCoordinator

            logger.info("Initializing BMAM system...")
            self.coordinator = BrainInspiredCoordinator()
            await self.coordinator.initialize()
            logger.info("✅ BMAM system initialized successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize BMAM system: {e}")
            return False

    async def run_all_evaluations(self, modules: list = None):
        """Run all evaluation modules"""
        start_time = time.time()

        # Default to all modules if none specified
        if modules is None:
            modules = ["framework", "memory", "agent", "persona"]

        print("\n" + "=" * 60)
        print("BMAM COMPREHENSIVE EVALUATION")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Modules: {', '.join(modules)}")
        print("=" * 60 + "\n")

        self.results = {
            "timestamp": datetime.now().isoformat(),
            "modules_evaluated": modules,
            "system_initialized": False,
            "module_results": {},
            "overall_metrics": {}
        }

        # Initialize system
        if await self.initialize_system():
            self.results["system_initialized"] = True
        else:
            print("⚠️  Running in mock mode (no coordinator)")

        # Run framework evaluation
        if "framework" in modules:
            print("\n🔍 Running Framework Evaluation...")
            try:
                self.framework.load_test_cases()
                framework_results = await self.framework.run_evaluation(self.coordinator)
                self.results["module_results"]["framework"] = framework_results
                print("✅ Framework evaluation completed")
            except Exception as e:
                logger.error(f"Framework evaluation failed: {e}")
                self.results["module_results"]["framework"] = {"error": str(e)}

        # Run memory evaluation
        if "memory" in modules and self.coordinator:
            print("\n🧠 Running Memory Evaluation...")
            try:
                memory_results = await self.memory_eval.run_comprehensive_evaluation(
                    self.coordinator.memory_manager
                )
                self.results["module_results"]["memory"] = memory_results
                print("✅ Memory evaluation completed")
            except Exception as e:
                logger.error(f"Memory evaluation failed: {e}")
                self.results["module_results"]["memory"] = {"error": str(e)}

        # Run agent evaluation
        if "agent" in modules and self.coordinator:
            print("\n🤖 Running Agent Evaluation...")
            try:
                agent_results = await self.agent_eval.run_comprehensive_evaluation(
                    self.coordinator,
                    self.coordinator.agent_system if hasattr(self.coordinator, 'agent_system') else None
                )
                self.results["module_results"]["agent"] = agent_results
                print("✅ Agent evaluation completed")
            except Exception as e:
                logger.error(f"Agent evaluation failed: {e}")
                self.results["module_results"]["agent"] = {"error": str(e)}

        # Run persona evaluation
        if "persona" in modules and self.coordinator:
            print("\n👤 Running Persona Evaluation...")
            try:
                persona_results = await self.persona_eval.run_comprehensive_evaluation(
                    self.coordinator
                )
                self.results["module_results"]["persona"] = persona_results
                print("✅ Persona evaluation completed")
            except Exception as e:
                logger.error(f"Persona evaluation failed: {e}")
                self.results["module_results"]["persona"] = {"error": str(e)}

        # Calculate overall metrics
        self._calculate_overall_metrics()

        # Save results
        self._save_results()

        # Generate and print report
        report = self._generate_comprehensive_report()
        print("\n" + report)

        # Cleanup
        if self.coordinator:
            await self.coordinator.stop_system()

        elapsed = time.time() - start_time
        print(f"\n⏱️  Total evaluation time: {elapsed:.2f} seconds")
        print(f"📁 Results saved to: {self.output_dir}")

        return self.results

    def _calculate_overall_metrics(self):
        """Calculate overall system metrics"""
        metrics = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "module_scores": {},
            "overall_score": 0
        }

        scores = []

        # Framework metrics
        if "framework" in self.results["module_results"]:
            framework = self.results["module_results"]["framework"]
            if "summary" in framework:
                metrics["total_tests"] += framework["summary"].get("total_tests", 0)
                metrics["passed_tests"] += framework["summary"].get("passed", 0)
                metrics["failed_tests"] += framework["summary"].get("failed", 0)
                score = framework["summary"].get("overall_score", 0)
                metrics["module_scores"]["framework"] = score
                scores.append(score)

        # Memory metrics
        if "memory" in self.results["module_results"]:
            memory = self.results["module_results"]["memory"]
            if "overall_score" in memory:
                score = memory["overall_score"]
                metrics["module_scores"]["memory"] = score
                scores.append(score)

        # Agent metrics
        if "agent" in self.results["module_results"]:
            agent = self.results["module_results"]["agent"]
            if "overall_score" in agent:
                score = agent["overall_score"]
                metrics["module_scores"]["agent"] = score
                scores.append(score)

        # Persona metrics
        if "persona" in self.results["module_results"]:
            persona = self.results["module_results"]["persona"]
            if "overall_score" in persona:
                score = persona["overall_score"]
                metrics["module_scores"]["persona"] = score
                scores.append(score)

        # Calculate overall score
        if scores:
            metrics["overall_score"] = sum(scores) / len(scores)

        self.results["overall_metrics"] = metrics

    def _generate_comprehensive_report(self) -> str:
        """Generate comprehensive evaluation report"""
        report = []
        report.append("=" * 80)
        report.append("BMAM COMPREHENSIVE EVALUATION REPORT")
        report.append("=" * 80)
        report.append(f"Timestamp: {self.results['timestamp']}")
        report.append(f"System Initialized: {'Yes' if self.results['system_initialized'] else 'No (Mock Mode)'}")
        report.append("")

        # Overall metrics
        metrics = self.results.get("overall_metrics", {})
        report.append("OVERALL METRICS")
        report.append("-" * 40)
        report.append(f"Overall System Score: {metrics.get('overall_score', 0):.2%}")
        report.append(f"Total Tests: {metrics.get('total_tests', 0)}")
        report.append(f"Passed: {metrics.get('passed_tests', 0)}")
        report.append(f"Failed: {metrics.get('failed_tests', 0)}")
        report.append("")

        # Module scores
        if metrics.get("module_scores"):
            report.append("MODULE SCORES")
            report.append("-" * 40)
            for module, score in metrics["module_scores"].items():
                report.append(f"{module.capitalize()}: {score:.2%}")
            report.append("")

        # Individual module summaries
        for module_name in ["framework", "memory", "agent", "persona"]:
            if module_name in self.results["module_results"]:
                module_data = self.results["module_results"][module_name]

                if "error" in module_data:
                    report.append(f"{module_name.upper()} MODULE")
                    report.append("-" * 40)
                    report.append(f"❌ Error: {module_data['error']}")
                    report.append("")
                    continue

                report.append(f"{module_name.upper()} MODULE")
                report.append("-" * 40)

                if module_name == "framework":
                    summary = module_data.get("summary", {})
                    report.append(f"Tests Run: {summary.get('total_tests', 0)}")
                    report.append(f"Success Rate: {summary.get('passed', 0) / max(summary.get('total_tests', 1), 1):.2%}")

                elif module_name == "memory":
                    storage = module_data.get("storage_performance", {})
                    retrieval = module_data.get("retrieval_performance", {})
                    report.append(f"Storage Success Rate: {storage.get('successful_stores', 0) / max(storage.get('total_memories', 1), 1):.2%}")
                    report.append(f"Retrieval Success Rate: {retrieval.get('successful_retrievals', 0) / max(retrieval.get('total_queries', 1), 1):.2%}")

                elif module_name == "agent":
                    coord = module_data.get("coordination", {})
                    recovery = module_data.get("error_recovery", {})
                    report.append(f"Coordination Success: {coord.get('success_rate', 0):.2%}")
                    report.append(f"Error Recovery Rate: {recovery.get('recovery_rate', 0):.2%}")

                elif module_name == "persona":
                    personality = module_data.get("personality_consistency", {})
                    emotional = module_data.get("emotional_appropriateness", {})
                    report.append(f"Personality Consistency: {personality.get('average_consistency', 0):.2%}")
                    report.append(f"Emotional Appropriateness: {emotional.get('appropriateness_rate', 0):.2%}")

                report.append("")

        # Recommendations
        report.append("RECOMMENDATIONS")
        report.append("-" * 40)
        recommendations = self._generate_recommendations()
        for rec in recommendations:
            report.append(f"• {rec}")

        report.append("")
        report.append("=" * 80)

        return "\n".join(report)

    def _generate_recommendations(self) -> list:
        """Generate recommendations based on evaluation results"""
        recommendations = []
        metrics = self.results.get("overall_metrics", {})

        overall_score = metrics.get("overall_score", 0)

        if overall_score < 0.5:
            recommendations.append("System needs significant improvements across all modules")
        elif overall_score < 0.7:
            recommendations.append("System shows moderate performance, focus on weak areas")
        elif overall_score < 0.9:
            recommendations.append("System performing well, minor optimizations recommended")
        else:
            recommendations.append("System performing excellently")

        # Module-specific recommendations
        module_scores = metrics.get("module_scores", {})

        if module_scores.get("memory", 1) < 0.7:
            recommendations.append("Improve memory retrieval accuracy and consolidation")

        if module_scores.get("agent", 1) < 0.7:
            recommendations.append("Enhance agent coordination and error recovery")

        if module_scores.get("persona", 1) < 0.7:
            recommendations.append("Work on personality consistency and emotional responses")

        if module_scores.get("framework", 1) < 0.7:
            recommendations.append("Address failing test cases in the framework")

        return recommendations

    def _save_results(self):
        """Save evaluation results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save comprehensive results
        comprehensive_file = self.output_dir / f"comprehensive_evaluation_{timestamp}.json"
        with open(comprehensive_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, default=str)

        # Save summary
        summary = {
            "timestamp": self.results["timestamp"],
            "overall_metrics": self.results["overall_metrics"],
            "modules_evaluated": self.results["modules_evaluated"]
        }
        summary_file = self.output_dir / f"evaluation_summary_{timestamp}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, default=str)

        # Update latest link
        latest_file = self.output_dir / "latest_comprehensive_evaluation.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, default=str)

        logger.info(f"Results saved to {comprehensive_file}")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="BMAM Comprehensive Evaluation")
    parser.add_argument(
        "--modules",
        nargs="+",
        choices=["framework", "memory", "agent", "persona"],
        default=None,
        help="Specific modules to evaluate (default: all)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results/evaluation",
        help="Output directory for results"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create evaluator and run
    evaluator = ComprehensiveEvaluator(args.output)
    await evaluator.run_all_evaluations(args.modules)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Evaluation interrupted by user")
    except Exception as e:
        print(f"\n❌ Evaluation failed: {e}")
        sys.exit(1)