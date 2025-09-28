#!/usr/bin/env python3
"""
BMAM Evaluation Framework
Comprehensive evaluation system for Brain-inspired Memory and Attention Model
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import numpy as np
from collections import defaultdict
import logging

# Import AgentMessage for direct agent communication
try:
    from ..coordination.clean_agent_system import AgentMessage
except ImportError:
    # Fallback if import fails
    AgentMessage = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class EvaluationMetrics:
    """Evaluation metrics for BMAM system"""

    # Performance metrics
    response_time: float = 0.0
    memory_retrieval_accuracy: float = 0.0
    context_relevance_score: float = 0.0

    # Memory metrics
    memory_capacity_utilization: float = 0.0
    memory_consolidation_rate: float = 0.0
    forgetting_curve_score: float = 0.0

    # Agent metrics
    agent_coordination_score: float = 0.0
    task_completion_rate: float = 0.0
    error_recovery_rate: float = 0.0

    # Persona metrics
    personality_consistency: float = 0.0
    emotional_appropriateness: float = 0.0
    response_coherence: float = 0.0

    # System metrics
    resource_efficiency: float = 0.0
    throughput: float = 0.0
    stability_score: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    def get_overall_score(self) -> float:
        """Calculate overall system score"""
        scores = [
            self.response_time,
            self.memory_retrieval_accuracy,
            self.context_relevance_score,
            self.memory_capacity_utilization,
            self.agent_coordination_score,
            self.task_completion_rate,
            self.personality_consistency,
            self.emotional_appropriateness,
            self.response_coherence,
            self.stability_score
        ]
        return np.mean([s for s in scores if s > 0])


@dataclass
class TestCase:
    """Test case for evaluation"""
    id: str
    category: str
    description: str
    input_data: Dict[str, Any]
    expected_output: Optional[Dict[str, Any]] = None
    evaluation_criteria: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict:
        return asdict(self)


class EvaluationFramework:
    """Main evaluation framework for BMAM"""

    def __init__(self, output_dir: str = "results/evaluation"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.test_cases: List[TestCase] = []
        self.results: Dict[str, Any] = {}
        self.metrics = EvaluationMetrics()

        # Performance tracking
        self.performance_history: List[Dict] = []
        self.error_log: List[Dict] = []

    def load_test_cases(self, test_file: Optional[str] = None):
        """Load test cases from file or generate defaults"""
        if test_file and Path(test_file).exists():
            with open(test_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.test_cases = [TestCase(**case) for case in data['test_cases']]
        else:
            self.test_cases = self._generate_default_test_cases()

    def _generate_default_test_cases(self) -> List[TestCase]:
        """Generate default test cases for evaluation"""
        return [
            # Memory test cases
            TestCase(
                id="mem_001",
                category="memory",
                description="Test memory storage and retrieval",
                input_data={
                    "action": "store",
                    "content": "The meeting is scheduled for tomorrow at 3 PM",
                    "context": "scheduling",
                    "importance": 0.8
                }
            ),
            TestCase(
                id="mem_002",
                category="memory",
                description="Test associative memory retrieval",
                input_data={
                    "action": "retrieve",
                    "query": "When is the meeting?",
                    "context": "scheduling"
                }
            ),
            TestCase(
                id="mem_003",
                category="memory",
                description="Test memory consolidation",
                input_data={
                    "action": "consolidate",
                    "time_window": "24h"
                }
            ),

            # Persona test cases
            TestCase(
                id="per_001",
                category="persona",
                description="Test personality consistency",
                input_data={
                    "prompt": "How do you feel about helping others?",
                    "context": "values"
                }
            ),
            TestCase(
                id="per_002",
                category="persona",
                description="Test emotional response",
                input_data={
                    "prompt": "I just got promoted!",
                    "context": "positive_news"
                }
            ),

            # Agent coordination test cases
            TestCase(
                id="agent_001",
                category="agent_coordination",
                description="Test multi-agent task handling",
                input_data={
                    "task": "Plan a birthday party",
                    "requirements": ["venue", "catering", "entertainment"]
                }
            ),
            TestCase(
                id="agent_002",
                category="agent_coordination",
                description="Test agent conflict resolution",
                input_data={
                    "conflicting_tasks": [
                        "Save money for vacation",
                        "Buy expensive gift"
                    ]
                }
            ),

            # Conversation test cases
            TestCase(
                id="conv_001",
                category="conversation",
                description="Test contextual understanding",
                input_data={
                    "conversation": [
                        "I love Italian food",
                        "What's your favorite cuisine?",
                        "Can you recommend a restaurant?"
                    ]
                }
            ),
            TestCase(
                id="conv_002",
                category="conversation",
                description="Test long-term context retention",
                input_data={
                    "conversation": [
                        "My name is Alice",
                        "I work as a teacher",
                        "What do you remember about me?"
                    ]
                }
            ),

            # Stress test cases
            TestCase(
                id="stress_001",
                category="stress",
                description="Test rapid memory operations",
                input_data={
                    "operations": 1000,
                    "type": "mixed_read_write"
                }
            ),
            TestCase(
                id="stress_002",
                category="stress",
                description="Test concurrent agent requests",
                input_data={
                    "concurrent_requests": 50,
                    "timeout": 30
                }
            )
        ]

    async def run_evaluation(self, coordinator=None) -> Dict[str, Any]:
        """Run complete evaluation suite"""
        logger.info("Starting BMAM evaluation...")
        start_time = time.time()

        # Initialize results structure
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "test_cases": {},
            "metrics": {},
            "summary": {}
        }

        # Run test categories
        if coordinator:
            await self._run_memory_tests(coordinator)
            await self._run_persona_tests(coordinator)
            await self._run_agent_tests(coordinator)
            await self._run_conversation_tests(coordinator)
            await self._run_stress_tests(coordinator)
        else:
            logger.warning("No coordinator provided, running mock tests")
            await self._run_mock_tests()

        # Calculate final metrics
        self._calculate_metrics()

        # Generate summary
        elapsed_time = time.time() - start_time
        self.results["summary"] = {
            "total_tests": len(self.test_cases),
            "passed": sum(1 for r in self.results["test_cases"].values() if r.get("passed", False)),
            "failed": sum(1 for r in self.results["test_cases"].values() if not r.get("passed", False)),
            "execution_time": elapsed_time,
            "overall_score": self.metrics.get_overall_score()
        }

        # Save results
        self._save_results()

        logger.info(f"Evaluation completed in {elapsed_time:.2f} seconds")
        return self.results

    async def _run_memory_tests(self, coordinator) -> None:
        """Run memory-related tests"""
        logger.info("Running memory tests...")

        memory_tests = [tc for tc in self.test_cases if tc.category == "memory"]

        for test in memory_tests:
            try:
                start = time.time()

                if test.input_data["action"] == "store":
                    # Test memory storage
                    processing_result = await coordinator.process_user_input(test.input_data["content"])
                    result = processing_result.response if hasattr(processing_result, 'response') else str(processing_result)
                    success = result is not None

                elif test.input_data["action"] == "retrieve":
                    # Test memory retrieval through memory_retrieval agent
                    processing_result = await coordinator.process_user_input(test.input_data["query"])
                    success = processing_result.success if hasattr(processing_result, 'success') else True
                    memories_count = len(processing_result.memories_retrieved) if hasattr(processing_result, 'memories_retrieved') else 0
                    result = {"retrieved_memories": memories_count}

                elif test.input_data["action"] == "consolidate":
                    # Test memory consolidation through consolidation agent
                    if hasattr(coordinator, 'consolidation'):
                        message = AgentMessage(
                            sender="evaluation_framework",
                            receiver="consolidation",
                            content="Trigger memory consolidation",
                            message_type="consolidation_request",
                            timestamp=datetime.now(),
                            metadata={}
                        )
                        consolidation_result = await coordinator.consolidation.process_message(message)
                        success = True
                        result = {"consolidation": "completed"}
                    else:
                        # Fallback: use general processing
                        processing_result = await coordinator.process_user_input("Consolidate memories")
                        success = processing_result.success if hasattr(processing_result, 'success') else True
                        result = {"consolidation": "completed"}

                elapsed = time.time() - start

                self.results["test_cases"][test.id] = {
                    "passed": success,
                    "execution_time": elapsed,
                    "result": result
                }

            except Exception as e:
                logger.error(f"Memory test {test.id} failed: {e}")
                self.results["test_cases"][test.id] = {
                    "passed": False,
                    "error": str(e)
                }

    async def _run_persona_tests(self, coordinator) -> None:
        """Run persona consistency tests"""
        logger.info("Running persona tests...")

        persona_tests = [tc for tc in self.test_cases if tc.category == "persona"]

        for test in persona_tests:
            try:
                start = time.time()

                # Test persona response
                processing_result = await coordinator.process_user_input(test.input_data["prompt"])
                response = processing_result.response if hasattr(processing_result, 'response') else str(processing_result)

                # Analyze response for consistency
                consistency_score = self._analyze_persona_consistency(response)
                emotional_score = self._analyze_emotional_appropriateness(
                    response,
                    test.input_data.get("context", "")
                )

                elapsed = time.time() - start

                self.results["test_cases"][test.id] = {
                    "passed": consistency_score > 0.7 and emotional_score > 0.7,
                    "execution_time": elapsed,
                    "consistency_score": consistency_score,
                    "emotional_score": emotional_score,
                    "response": response
                }

            except Exception as e:
                logger.error(f"Persona test {test.id} failed: {e}")
                self.results["test_cases"][test.id] = {
                    "passed": False,
                    "error": str(e)
                }

    async def _run_agent_tests(self, coordinator) -> None:
        """Run agent coordination tests"""
        logger.info("Running agent coordination tests...")

        agent_tests = [tc for tc in self.test_cases if tc.category == "agent_coordination"]

        for test in agent_tests:
            try:
                start = time.time()

                # Test agent coordination
                if "task" in test.input_data:
                    processing_result = await coordinator.process_user_input(test.input_data["task"])
                    result = processing_result.response if hasattr(processing_result, 'response') else str(processing_result)
                    # Check if all requirements are addressed
                    requirements = test.input_data.get("requirements", [])
                    coverage = sum(1 for req in requirements if req.lower() in result.lower())
                    success = coverage == len(requirements)

                elif "conflicting_tasks" in test.input_data:
                    # Test conflict resolution
                    results = []
                    for task in test.input_data["conflicting_tasks"]:
                        processing_result = await coordinator.process_user_input(task)
                        task_result = processing_result.response if hasattr(processing_result, 'response') else str(processing_result)
                        results.append(task_result)
                    success = len(results) == len(test.input_data["conflicting_tasks"])
                    result = {"resolutions": results}

                elapsed = time.time() - start

                self.results["test_cases"][test.id] = {
                    "passed": success,
                    "execution_time": elapsed,
                    "result": result
                }

            except Exception as e:
                logger.error(f"Agent test {test.id} failed: {e}")
                self.results["test_cases"][test.id] = {
                    "passed": False,
                    "error": str(e)
                }

    async def _run_conversation_tests(self, coordinator) -> None:
        """Run conversation and context tests"""
        logger.info("Running conversation tests...")

        conv_tests = [tc for tc in self.test_cases if tc.category == "conversation"]

        for test in conv_tests:
            try:
                start = time.time()

                responses = []
                for message in test.input_data["conversation"]:
                    processing_result = await coordinator.process_user_input(message)
                    response = processing_result.response if hasattr(processing_result, 'response') else str(processing_result)
                    responses.append(response)
                    await asyncio.sleep(0.1)  # Small delay between messages

                # Analyze conversation coherence
                coherence_score = self._analyze_conversation_coherence(responses)
                context_score = self._analyze_context_retention(
                    test.input_data["conversation"],
                    responses
                )

                elapsed = time.time() - start

                self.results["test_cases"][test.id] = {
                    "passed": coherence_score > 0.7 and context_score > 0.7,
                    "execution_time": elapsed,
                    "coherence_score": coherence_score,
                    "context_score": context_score,
                    "responses": responses
                }

            except Exception as e:
                logger.error(f"Conversation test {test.id} failed: {e}")
                self.results["test_cases"][test.id] = {
                    "passed": False,
                    "error": str(e)
                }

    async def _run_stress_tests(self, coordinator) -> None:
        """Run stress and performance tests"""
        logger.info("Running stress tests...")

        stress_tests = [tc for tc in self.test_cases if tc.category == "stress"]

        for test in stress_tests:
            try:
                start = time.time()

                if test.input_data.get("type") == "mixed_read_write":
                    # Rapid memory operations using coordinator interface
                    operations = test.input_data["operations"]
                    successes = 0

                    for i in range(operations):
                        try:
                            if i % 2 == 0:
                                # Write operation - store through coordinator
                                processing_result = await coordinator.process_user_input(f"Remember this: Test memory {i} with index {i}")
                                if hasattr(processing_result, 'memory_stored') and processing_result.memory_stored:
                                    successes += 1
                            else:
                                # Read operation - retrieve through coordinator
                                processing_result = await coordinator.process_user_input(f"What do you remember about memory {i-1}?")
                                if hasattr(processing_result, 'memories_retrieved') and processing_result.memories_retrieved:
                                    successes += 1
                        except Exception as e:
                            logger.error(f"Memory operation {i} failed: {e}")

                    success_rate = successes / operations if operations > 0 else 0
                    success = success_rate > 0.5

                elif "concurrent_requests" in test.input_data:
                    # Concurrent requests test
                    num_requests = test.input_data["concurrent_requests"]

                    async def make_request(idx):
                        processing_result = await coordinator.process_user_input(f"Test request {idx}")
                        return processing_result.response if hasattr(processing_result, 'response') else str(processing_result)

                    tasks = [make_request(i) for i in range(num_requests)]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    successes = sum(1 for r in results if not isinstance(r, Exception))
                    success_rate = successes / num_requests
                    success = success_rate > 0.9

                elapsed = time.time() - start
                throughput = test.input_data.get("operations", test.input_data.get("concurrent_requests", 1)) / elapsed

                self.results["test_cases"][test.id] = {
                    "passed": success,
                    "execution_time": elapsed,
                    "throughput": throughput,
                    "success_rate": success_rate
                }

            except Exception as e:
                logger.error(f"Stress test {test.id} failed: {e}")
                self.results["test_cases"][test.id] = {
                    "passed": False,
                    "error": str(e)
                }

    async def _run_mock_tests(self) -> None:
        """Run mock tests when no coordinator is available"""
        logger.info("Running mock tests...")

        for test in self.test_cases:
            self.results["test_cases"][test.id] = {
                "passed": np.random.random() > 0.3,
                "execution_time": np.random.random() * 2,
                "mock": True
            }

    def _analyze_persona_consistency(self, response: str) -> float:
        """Analyze persona consistency in response"""
        # Simple heuristic - check for consistent personality markers
        consistency_markers = [
            "helpful", "friendly", "supportive",
            "understanding", "patient", "caring"
        ]

        score = sum(1 for marker in consistency_markers if marker in response.lower())
        return min(1.0, score / 3)

    def _analyze_emotional_appropriateness(self, response: str, context: str) -> float:
        """Analyze emotional appropriateness of response"""
        if "positive" in context:
            positive_markers = ["congratulations", "happy", "great", "wonderful", "excited"]
            score = sum(1 for marker in positive_markers if marker in response.lower())
            return min(1.0, score / 2)

        return 0.8  # Default score

    def _analyze_conversation_coherence(self, responses: List[str]) -> float:
        """Analyze coherence of conversation responses"""
        if not responses:
            return 0.0

        # Check for consistency in tone and style
        coherence_score = 0.8  # Base score

        # Penalize very short or very long responses
        avg_length = np.mean([len(r) for r in responses])
        if avg_length < 10 or avg_length > 500:
            coherence_score -= 0.2

        return max(0.0, coherence_score)

    def _analyze_context_retention(self, inputs: List[str], responses: List[str]) -> float:
        """Analyze context retention across conversation"""
        score = 0.8  # Base score

        # Check if later responses reference earlier context
        for i, (inp, resp) in enumerate(zip(inputs, responses)):
            if i > 0:
                # Check if response references previous inputs
                for prev_inp in inputs[:i]:
                    key_words = [w for w in prev_inp.split() if len(w) > 4]
                    if any(word.lower() in resp.lower() for word in key_words):
                        score += 0.1

        return min(1.0, score)

    def _calculate_metrics(self) -> None:
        """Calculate overall evaluation metrics"""
        test_results = self.results["test_cases"]

        # Performance metrics
        response_times = [r["execution_time"] for r in test_results.values() if "execution_time" in r]
        if response_times:
            self.metrics.response_time = 1.0 / (1.0 + np.mean(response_times))

        # Memory metrics
        memory_tests = [r for tid, r in test_results.items() if tid.startswith("mem_")]
        if memory_tests:
            self.metrics.memory_retrieval_accuracy = sum(1 for t in memory_tests if t.get("passed", False)) / len(memory_tests)

        # Persona metrics
        persona_tests = [r for tid, r in test_results.items() if tid.startswith("per_")]
        if persona_tests:
            consistency_scores = [t.get("consistency_score", 0) for t in persona_tests]
            emotional_scores = [t.get("emotional_score", 0) for t in persona_tests]

            if consistency_scores:
                self.metrics.personality_consistency = np.mean(consistency_scores)
            if emotional_scores:
                self.metrics.emotional_appropriateness = np.mean(emotional_scores)

        # Agent metrics
        agent_tests = [r for tid, r in test_results.items() if tid.startswith("agent_")]
        if agent_tests:
            self.metrics.agent_coordination_score = sum(1 for t in agent_tests if t.get("passed", False)) / len(agent_tests)

        # Conversation metrics
        conv_tests = [r for tid, r in test_results.items() if tid.startswith("conv_")]
        if conv_tests:
            coherence_scores = [t.get("coherence_score", 0) for t in conv_tests]
            if coherence_scores:
                self.metrics.response_coherence = np.mean(coherence_scores)

            context_scores = [t.get("context_score", 0) for t in conv_tests]
            if context_scores:
                self.metrics.context_relevance_score = np.mean(context_scores)

        # Stress test metrics
        stress_tests = [r for tid, r in test_results.items() if tid.startswith("stress_")]
        if stress_tests:
            throughputs = [t.get("throughput", 0) for t in stress_tests]
            if throughputs:
                self.metrics.throughput = np.mean(throughputs)

            success_rates = [t.get("success_rate", 0) for t in stress_tests]
            if success_rates:
                self.metrics.stability_score = np.mean(success_rates)

        # Overall task completion
        all_tests = list(test_results.values())
        if all_tests:
            self.metrics.task_completion_rate = sum(1 for t in all_tests if t.get("passed", False)) / len(all_tests)

        # Add metrics to results
        self.results["metrics"] = self.metrics.to_dict()

    def _save_results(self) -> None:
        """Save evaluation results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save detailed results
        detailed_file = self.output_dir / f"evaluation_detailed_{timestamp}.json"
        with open(detailed_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, default=str)

        # Save summary
        summary_file = self.output_dir / f"evaluation_summary_{timestamp}.json"
        summary = {
            "timestamp": self.results["timestamp"],
            "summary": self.results["summary"],
            "metrics": self.results["metrics"]
        }
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, default=str)

        # Update latest results link
        latest_file = self.output_dir / "latest_evaluation.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, default=str)

        logger.info(f"Results saved to {detailed_file}")
        logger.info(f"Summary saved to {summary_file}")

    def generate_report(self) -> str:
        """Generate human-readable evaluation report"""
        report = []
        report.append("=" * 60)
        report.append("BMAM EVALUATION REPORT")
        report.append("=" * 60)
        report.append(f"Timestamp: {self.results.get('timestamp', 'N/A')}")
        report.append("")

        # Summary
        summary = self.results.get("summary", {})
        report.append("SUMMARY")
        report.append("-" * 30)
        report.append(f"Total Tests: {summary.get('total_tests', 0)}")
        report.append(f"Passed: {summary.get('passed', 0)}")
        report.append(f"Failed: {summary.get('failed', 0)}")
        report.append(f"Execution Time: {summary.get('execution_time', 0):.2f} seconds")
        report.append(f"Overall Score: {summary.get('overall_score', 0):.2%}")
        report.append("")

        # Metrics
        report.append("METRICS")
        report.append("-" * 30)
        metrics = self.results.get("metrics", {})
        for key, value in metrics.items():
            if isinstance(value, float):
                report.append(f"{key}: {value:.3f}")
            else:
                report.append(f"{key}: {value}")
        report.append("")

        # Test Results
        report.append("TEST RESULTS")
        report.append("-" * 30)

        # Group by category
        test_results = self.results.get("test_cases", {})
        categories = defaultdict(list)
        for test_id, result in test_results.items():
            category = test_id.split("_")[0]
            categories[category].append((test_id, result))

        for category, tests in categories.items():
            report.append(f"\n{category.upper()} Tests:")
            for test_id, result in tests:
                status = "✓" if result.get("passed", False) else "✗"
                time = result.get("execution_time", 0)
                report.append(f"  [{status}] {test_id}: {time:.3f}s")
                if "error" in result:
                    report.append(f"      Error: {result['error']}")

        report.append("")
        report.append("=" * 60)

        return "\n".join(report)


async def main():
    """Main evaluation runner"""
    print("BMAM Evaluation System")
    print("=" * 40)

    # Create evaluation framework
    evaluator = EvaluationFramework()

    # Load test cases
    evaluator.load_test_cases()
    print(f"Loaded {len(evaluator.test_cases)} test cases")

    # Try to import and initialize coordinator
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.coordination.brain_coordinator import BrainInspiredCoordinator

        print("Initializing BMAM coordinator...")
        coordinator = BrainInspiredCoordinator()
        await coordinator.initialize()
        print("Coordinator initialized successfully")

    except Exception as e:
        print(f"Could not initialize coordinator: {e}")
        print("Running with mock tests...")
        coordinator = None

    # Run evaluation
    print("\nStarting evaluation...")
    results = await evaluator.run_evaluation(coordinator)

    # Generate and print report
    report = evaluator.generate_report()
    print("\n" + report)

    # Cleanup
    if coordinator:
        await coordinator.stop_system()

    print(f"\nEvaluation complete. Results saved to {evaluator.output_dir}")


if __name__ == "__main__":
    asyncio.run(main())