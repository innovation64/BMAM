#!/usr/bin/env python3
"""
BMAM MeMOS Evaluation Runner with Experimental Configuration Support
运行 MeMOS 评估，支持不同的实验配置（无KG、低KG、基准）
"""

import asyncio
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.coordination.brain_coordinator import BrainInspiredCoordinator
from src.coordination.kg_merge_config import KGMergeConfig, set_kg_merge_config
from src.utils.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BMAMMemosEvaluator:
    """BMAM MeMOS Evaluator with experiment configuration support"""

    def __init__(
        self,
        experiment_config_path: Optional[str] = None,
        output_dir: str = "results/memos_eval"
    ):
        self.experiment_config_path = experiment_config_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.experiment_config = None
        self.coordinator = None
        self.results = {}

    def load_experiment_config(self) -> Dict[str, Any]:
        """Load experiment configuration"""
        if not self.experiment_config_path:
            logger.info("No experiment config specified, using baseline")
            return self._get_baseline_config()

        config_path = Path(self.experiment_config_path)
        if not config_path.exists():
            logger.error(f"Config file not found: {config_path}")
            sys.exit(1)

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        logger.info(f"Loaded experiment config: {config.get('experiment_name', 'Unknown')}")
        return config

    def _get_baseline_config(self) -> Dict[str, Any]:
        """Get baseline configuration"""
        baseline_path = project_root / "configs/experiment_configs/baseline_config.json"
        if baseline_path.exists():
            with open(baseline_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.warning("Baseline config not found, using hardcoded defaults")
            return {
                "experiment_name": "Baseline",
                "description": "Default baseline configuration",
                "memory_settings": {
                    "enable_kg": True,
                    "enable_hippocampal_graph": True,
                    "enable_temporal_concept_graph": True
                },
                "evaluation_settings": {
                    "dataset": "memos",
                    "output_suffix": "baseline"
                }
            }

    def apply_kg_merge_config(self):
        """Apply KG merge configuration from experiment config"""
        if not self.experiment_config:
            logger.warning("No experiment config loaded")
            return

        kg_config_data = self.experiment_config.get("kg_merge_config")
        if not kg_config_data:
            logger.info("No kg_merge_config in experiment config, using defaults")
            return

        # Create KGMergeConfig from data
        kg_config = KGMergeConfig.from_dict(kg_config_data)

        # Validate
        errors = kg_config.validate()
        if errors:
            logger.error(f"Invalid KG merge config: {errors}")
            sys.exit(1)

        # Apply globally
        set_kg_merge_config(kg_config)
        logger.info(f"✅ Applied KG merge config: plasticity_score={kg_config.kg_fact_plasticity_score}")

    async def initialize_bmam(self):
        """Initialize BMAM coordinator with experiment settings"""
        try:
            logger.info("Initializing BMAM system...")

            # Apply memory settings from experiment config
            memory_settings = self.experiment_config.get("memory_settings", {})

            # Create coordinator
            self.coordinator = BrainInspiredCoordinator()

            # Apply memory settings if needed
            if hasattr(self.coordinator, 'memory_manager'):
                for key, value in memory_settings.items():
                    if hasattr(self.coordinator.memory_manager, key):
                        setattr(self.coordinator.memory_manager, key, value)
                        logger.info(f"  Set memory_manager.{key} = {value}")

            await self.coordinator.initialize()
            logger.info("✅ BMAM system initialized")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize BMAM: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def load_memos_dataset(self, dataset_path: str = "data/memos_dataset.json"):
        """Load MeMOS dataset"""
        dataset_file = Path(dataset_path)
        if not dataset_file.exists():
            logger.error(f"MeMOS dataset not found: {dataset_path}")
            sys.exit(1)

        with open(dataset_file, 'r', encoding='utf-8') as f:
            dataset = json.load(f)

        logger.info(f"Loaded MeMOS dataset: {len(dataset.get('memories', []))} memories, "
                   f"{len(dataset.get('questions', []))} questions")
        return dataset

    async def ingest_memories(self, memories: list):
        """Ingest memories into BMAM"""
        logger.info(f"Ingesting {len(memories)} memories...")

        for i, memory in enumerate(memories, 1):
            try:
                text = memory.get('text', '')
                metadata = memory.get('metadata', {})

                # Store memory
                await self.coordinator.memory_manager.store_memory(
                    content=text,
                    metadata=metadata
                )

                if i % 5 == 0:
                    logger.info(f"  Ingested {i}/{len(memories)} memories")

            except Exception as e:
                logger.error(f"Failed to ingest memory {i}: {e}")

        logger.info("✅ Memory ingestion completed")

    async def evaluate_questions(self, questions: list) -> Dict[str, Any]:
        """Evaluate questions"""
        logger.info(f"Evaluating {len(questions)} questions...")

        results = {
            "total_questions": len(questions),
            "correct": 0,
            "incorrect": 0,
            "details": []
        }

        for i, question_data in enumerate(questions, 1):
            try:
                question = question_data.get('question', '')
                expected_answer = question_data.get('answer', '')
                question_type = question_data.get('type', 'unknown')

                logger.info(f"\n[Q{i}/{len(questions)}] {question}")

                # Retrieve relevant memories
                retrieved = await self.coordinator.memory_manager.retrieve_memories(
                    query=question,
                    k=10
                )

                # Simple answer extraction (can be enhanced)
                prediction = self._extract_answer(retrieved, question)

                # Evaluate
                is_correct = self._evaluate_answer(prediction, expected_answer)

                result_entry = {
                    "question_id": i,
                    "question": question,
                    "type": question_type,
                    "expected": expected_answer,
                    "predicted": prediction,
                    "correct": is_correct,
                    "retrieved_count": len(retrieved)
                }

                results["details"].append(result_entry)

                if is_correct:
                    results["correct"] += 1
                    logger.info(f"  ✅ Correct")
                else:
                    results["incorrect"] += 1
                    logger.info(f"  ❌ Incorrect - Expected: {expected_answer}, Got: {prediction}")

            except Exception as e:
                logger.error(f"Failed to evaluate question {i}: {e}")
                results["details"].append({
                    "question_id": i,
                    "error": str(e)
                })

        # Calculate accuracy
        results["accuracy"] = results["correct"] / max(results["total_questions"], 1)

        return results

    def _extract_answer(self, memories: list, question: str) -> str:
        """Extract answer from retrieved memories (simplified)"""
        if not memories:
            return "unknown"

        # Simple extraction: return content of top memory
        top_memory = memories[0]
        return top_memory.get('content', 'unknown')[:100]  # First 100 chars

    def _evaluate_answer(self, predicted: str, expected: str) -> bool:
        """Evaluate if prediction matches expected answer"""
        # Normalize
        pred_norm = predicted.lower().strip()
        exp_norm = expected.lower().strip()

        # Check if expected answer is in predicted
        return exp_norm in pred_norm

    async def run_evaluation(
        self,
        dataset_path: str = "data/memos_dataset.json",
        learning_log_path: str = "data/learning_log.jsonl"
    ) -> Dict[str, Any]:
        """Run complete evaluation"""
        start_time = datetime.now()

        print("\n" + "=" * 80)
        print("BMAM MEMOS EVALUATION")
        print("=" * 80)

        # Load experiment config
        self.experiment_config = self.load_experiment_config()
        print(f"Experiment: {self.experiment_config.get('experiment_name', 'Unknown')}")
        print(f"Description: {self.experiment_config.get('description', 'N/A')}")
        print("=" * 80 + "\n")

        # Apply KG merge config
        self.apply_kg_merge_config()

        # Initialize BMAM
        if not await self.initialize_bmam():
            logger.error("Failed to initialize BMAM, aborting")
            return {"error": "Initialization failed"}

        # Load dataset
        dataset = await self.load_memos_dataset(dataset_path)

        # Ingest memories
        await self.ingest_memories(dataset.get('memories', []))

        # Evaluate questions
        eval_results = await self.evaluate_questions(dataset.get('questions', []))

        # Cleanup
        if self.coordinator:
            await self.coordinator.stop_system()

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        # Compile final results
        final_results = {
            "experiment_name": self.experiment_config.get('experiment_name', 'Unknown'),
            "timestamp": start_time.isoformat(),
            "duration_seconds": elapsed,
            "dataset": dataset_path,
            "learning_log": learning_log_path,
            "evaluation_results": eval_results,
            "config": self.experiment_config
        }

        # Save results
        self._save_results(final_results)

        # Print summary
        self._print_summary(eval_results)

        return final_results

    def _save_results(self, results: Dict[str, Any]):
        """Save evaluation results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        experiment_name = results.get('experiment_name', 'unknown').lower().replace(' ', '_')

        # Save detailed results
        detailed_file = self.output_dir / f"memos_eval_{experiment_name}_{timestamp}.json"
        with open(detailed_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"📁 Results saved to: {detailed_file}")

        # Save summary
        summary = {
            "experiment_name": results.get('experiment_name'),
            "timestamp": results.get('timestamp'),
            "accuracy": results['evaluation_results']['accuracy'],
            "correct": results['evaluation_results']['correct'],
            "total": results['evaluation_results']['total_questions']
        }

        summary_file = self.output_dir / f"summary_{experiment_name}_{timestamp}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

    def _print_summary(self, eval_results: Dict[str, Any]):
        """Print evaluation summary"""
        print("\n" + "=" * 80)
        print("EVALUATION SUMMARY")
        print("=" * 80)
        print(f"Total Questions: {eval_results['total_questions']}")
        print(f"Correct: {eval_results['correct']}")
        print(f"Incorrect: {eval_results['incorrect']}")
        print(f"Accuracy: {eval_results['accuracy']:.2%}")
        print("=" * 80 + "\n")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="BMAM MeMOS Evaluation with Experiment Configs"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to experiment configuration JSON file"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="data/memos_dataset.json",
        help="Path to MeMOS dataset"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results/memos_eval",
        help="Output directory for results"
    )
    parser.add_argument(
        "--log",
        type=str,
        default="data/learning_log.jsonl",
        help="Path to learning log file"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run evaluation
    evaluator = BMAMMemosEvaluator(
        experiment_config_path=args.config,
        output_dir=args.output
    )

    await evaluator.run_evaluation(
        dataset_path=args.dataset,
        learning_log_path=args.log
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Evaluation interrupted by user")
    except Exception as e:
        print(f"\n❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
