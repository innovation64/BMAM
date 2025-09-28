#!/usr/bin/env python3
"""
Memory System Evaluation Module
Specialized evaluation for BMAM memory components
"""

import asyncio
import time
import random
import numpy as np
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MemoryEvaluator:
    """Evaluate memory system performance and capabilities"""

    def __init__(self):
        self.test_memories = []
        self.results = {}

    def generate_test_memories(self, count: int = 100) -> List[Dict]:
        """Generate test memory entries"""
        categories = ["personal", "factual", "emotional", "procedural", "episodic"]
        contexts = ["work", "home", "social", "learning", "entertainment"]

        memories = []
        for i in range(count):
            memory = {
                "id": f"test_mem_{i:04d}",
                "content": self._generate_memory_content(i),
                "category": random.choice(categories),
                "context": random.choice(contexts),
                "timestamp": (datetime.now() - timedelta(days=random.randint(0, 365))).isoformat(),
                "importance": random.random(),
                "emotional_valence": random.uniform(-1, 1),
                "access_count": random.randint(0, 10),
                "associations": [f"test_mem_{random.randint(0, count-1):04d}" for _ in range(random.randint(0, 3))]
            }
            memories.append(memory)

        return memories

    def _generate_memory_content(self, index: int) -> str:
        """Generate realistic memory content"""
        templates = [
            "Meeting with {person} about {topic} at {location}",
            "Learned that {fact} is important for {reason}",
            "Felt {emotion} when {event} happened",
            "Remember to {action} before {deadline}",
            "{person} said '{quote}' during {context}"
        ]

        template = random.choice(templates)
        content = template.format(
            person=f"Person_{random.randint(1, 20)}",
            topic=random.choice(["project", "budget", "planning", "review"]),
            location=random.choice(["office", "conference room", "online", "cafe"]),
            fact=random.choice(["deadline", "requirement", "process", "policy"]),
            reason=random.choice(["efficiency", "compliance", "quality", "safety"]),
            emotion=random.choice(["happy", "concerned", "excited", "thoughtful"]),
            event=random.choice(["presentation", "discussion", "decision", "announcement"]),
            action=random.choice(["submit report", "review document", "send email", "prepare slides"]),
            deadline=random.choice(["tomorrow", "next week", "month end", "Friday"]),
            quote=random.choice(["This is important", "Let's discuss", "Great work", "Need improvement"]),
            context=random.choice(["meeting", "lunch", "review", "call"])
        )

        return f"[{index:04d}] {content}"

    async def evaluate_storage_performance(self, memory_manager) -> Dict:
        """Evaluate memory storage performance"""
        logger.info("Evaluating memory storage performance...")

        results = {
            "total_memories": 0,
            "successful_stores": 0,
            "failed_stores": 0,
            "average_store_time": 0,
            "storage_times": []
        }

        test_memories = self.generate_test_memories(50)

        for memory in test_memories:
            try:
                start = time.time()
                await memory_manager.store_memory(
                    memory["content"],
                    {
                        "category": memory["category"],
                        "context": memory["context"],
                        "importance": memory["importance"]
                    }
                )
                elapsed = time.time() - start

                results["successful_stores"] += 1
                results["storage_times"].append(elapsed)

            except Exception as e:
                logger.error(f"Storage failed: {e}")
                results["failed_stores"] += 1

            results["total_memories"] += 1

        if results["storage_times"]:
            results["average_store_time"] = np.mean(results["storage_times"])
            results["min_store_time"] = min(results["storage_times"])
            results["max_store_time"] = max(results["storage_times"])

        return results

    async def evaluate_retrieval_performance(self, memory_manager) -> Dict:
        """Evaluate memory retrieval performance"""
        logger.info("Evaluating memory retrieval performance...")

        results = {
            "total_queries": 0,
            "successful_retrievals": 0,
            "average_retrieval_time": 0,
            "average_relevance_score": 0,
            "retrieval_times": [],
            "relevance_scores": []
        }

        # Test queries
        queries = [
            "What meetings did I have?",
            "Important deadlines",
            "Recent decisions",
            "Things to remember",
            "Project updates",
            "Team discussions",
            "Action items",
            "Learning notes"
        ]

        for query in queries:
            try:
                start = time.time()
                memories = await memory_manager.retrieve_memories(query, k=5)
                elapsed = time.time() - start

                if memories:
                    results["successful_retrievals"] += 1
                    results["retrieval_times"].append(elapsed)

                    # Calculate relevance (simplified)
                    relevance = self._calculate_relevance(query, memories)
                    results["relevance_scores"].append(relevance)

            except Exception as e:
                logger.error(f"Retrieval failed: {e}")

            results["total_queries"] += 1

        if results["retrieval_times"]:
            results["average_retrieval_time"] = np.mean(results["retrieval_times"])
            results["min_retrieval_time"] = min(results["retrieval_times"])
            results["max_retrieval_time"] = max(results["retrieval_times"])

        if results["relevance_scores"]:
            results["average_relevance_score"] = np.mean(results["relevance_scores"])

        return results

    async def evaluate_consolidation(self, memory_manager) -> Dict:
        """Evaluate memory consolidation capabilities"""
        logger.info("Evaluating memory consolidation...")

        results = {
            "pre_consolidation_count": 0,
            "post_consolidation_count": 0,
            "consolidation_time": 0,
            "memory_reduction_ratio": 0
        }

        try:
            # Count memories before consolidation
            all_memories = await memory_manager.get_all_memories()
            results["pre_consolidation_count"] = len(all_memories)

            # Perform consolidation
            start = time.time()
            await memory_manager.consolidate_memories()
            results["consolidation_time"] = time.time() - start

            # Count memories after consolidation
            all_memories = await memory_manager.get_all_memories()
            results["post_consolidation_count"] = len(all_memories)

            # Calculate reduction ratio
            if results["pre_consolidation_count"] > 0:
                results["memory_reduction_ratio"] = 1 - (
                    results["post_consolidation_count"] / results["pre_consolidation_count"]
                )

        except Exception as e:
            logger.error(f"Consolidation evaluation failed: {e}")
            results["error"] = str(e)

        return results

    async def evaluate_forgetting_curve(self, memory_manager) -> Dict:
        """Evaluate forgetting curve implementation"""
        logger.info("Evaluating forgetting curve...")

        results = {
            "initial_memories": 0,
            "retained_after_1h": 0,
            "retained_after_24h": 0,
            "retained_after_7d": 0,
            "forgetting_rate": 0
        }

        try:
            # Store test memories with different timestamps
            test_memories = [
                {"content": f"Recent memory {i}", "age": "1h"}
                for i in range(10)
            ] + [
                {"content": f"Day old memory {i}", "age": "24h"}
                for i in range(10)
            ] + [
                {"content": f"Week old memory {i}", "age": "7d"}
                for i in range(10)
            ]

            for memory in test_memories:
                await memory_manager.store_memory(
                    memory["content"],
                    {"age": memory["age"]}
                )

            results["initial_memories"] = len(test_memories)

            # Simulate forgetting process
            await memory_manager.apply_forgetting()

            # Check retention
            all_memories = await memory_manager.get_all_memories()
            for memory in all_memories:
                content = memory.get("content", "")
                if "Recent memory" in content:
                    results["retained_after_1h"] += 1
                elif "Day old memory" in content:
                    results["retained_after_24h"] += 1
                elif "Week old memory" in content:
                    results["retained_after_7d"] += 1

            # Calculate forgetting rate
            total_retained = (
                results["retained_after_1h"] +
                results["retained_after_24h"] +
                results["retained_after_7d"]
            )
            results["forgetting_rate"] = 1 - (total_retained / results["initial_memories"])

        except Exception as e:
            logger.error(f"Forgetting curve evaluation failed: {e}")
            results["error"] = str(e)

        return results

    async def evaluate_association_strength(self, memory_manager) -> Dict:
        """Evaluate memory association mechanisms"""
        logger.info("Evaluating memory associations...")

        results = {
            "total_associations": 0,
            "strong_associations": 0,
            "weak_associations": 0,
            "average_association_strength": 0,
            "association_strengths": []
        }

        try:
            # Create memories with known associations
            base_memory = "Important project meeting with team"
            associated_memories = [
                "Project deadline is next Friday",
                "Team needs additional resources",
                "Budget approval pending",
                "Client feedback was positive"
            ]

            # Store base memory
            await memory_manager.store_memory(base_memory, {"type": "base"})

            # Store associated memories
            for memory in associated_memories:
                await memory_manager.store_memory(
                    memory,
                    {"type": "associated", "base": base_memory}
                )

            # Test association retrieval
            retrieved = await memory_manager.retrieve_memories(base_memory, k=10)

            for memory in retrieved:
                if memory.get("content") in associated_memories:
                    # Calculate association strength (simplified)
                    strength = memory.get("similarity_score", 0)
                    results["association_strengths"].append(strength)

                    if strength > 0.7:
                        results["strong_associations"] += 1
                    else:
                        results["weak_associations"] += 1

                    results["total_associations"] += 1

            if results["association_strengths"]:
                results["average_association_strength"] = np.mean(results["association_strengths"])

        except Exception as e:
            logger.error(f"Association evaluation failed: {e}")
            results["error"] = str(e)

        return results

    def _calculate_relevance(self, query: str, memories: List[Dict]) -> float:
        """Calculate relevance score for retrieved memories"""
        if not memories:
            return 0.0

        query_words = set(query.lower().split())
        relevance_scores = []

        for memory in memories:
            content = memory.get("content", "").lower()
            content_words = set(content.split())

            # Calculate word overlap
            overlap = len(query_words.intersection(content_words))
            score = overlap / max(len(query_words), 1)
            relevance_scores.append(score)

        return np.mean(relevance_scores) if relevance_scores else 0.0

    async def run_comprehensive_evaluation(self, memory_manager) -> Dict:
        """Run all memory evaluation tests"""
        logger.info("Starting comprehensive memory evaluation...")

        results = {
            "timestamp": datetime.now().isoformat(),
            "storage_performance": await self.evaluate_storage_performance(memory_manager),
            "retrieval_performance": await self.evaluate_retrieval_performance(memory_manager),
            "consolidation": await self.evaluate_consolidation(memory_manager),
            "forgetting_curve": await self.evaluate_forgetting_curve(memory_manager),
            "associations": await self.evaluate_association_strength(memory_manager)
        }

        # Calculate overall memory score
        scores = []
        if results["storage_performance"]["successful_stores"] > 0:
            scores.append(
                results["storage_performance"]["successful_stores"] /
                results["storage_performance"]["total_memories"]
            )

        if results["retrieval_performance"]["successful_retrievals"] > 0:
            scores.append(
                results["retrieval_performance"]["successful_retrievals"] /
                results["retrieval_performance"]["total_queries"]
            )

        if "average_relevance_score" in results["retrieval_performance"]:
            scores.append(results["retrieval_performance"]["average_relevance_score"])

        if "average_association_strength" in results["associations"]:
            scores.append(results["associations"]["average_association_strength"])

        results["overall_score"] = np.mean(scores) if scores else 0.0

        return results

    def generate_memory_report(self, results: Dict) -> str:
        """Generate memory evaluation report"""
        report = []
        report.append("=" * 60)
        report.append("MEMORY SYSTEM EVALUATION REPORT")
        report.append("=" * 60)
        report.append(f"Timestamp: {results.get('timestamp', 'N/A')}")
        report.append(f"Overall Score: {results.get('overall_score', 0):.2%}")
        report.append("")

        # Storage Performance
        storage = results.get("storage_performance", {})
        report.append("STORAGE PERFORMANCE")
        report.append("-" * 30)
        report.append(f"Total Memories: {storage.get('total_memories', 0)}")
        report.append(f"Successful: {storage.get('successful_stores', 0)}")
        report.append(f"Failed: {storage.get('failed_stores', 0)}")
        report.append(f"Average Time: {storage.get('average_store_time', 0):.3f}s")
        report.append("")

        # Retrieval Performance
        retrieval = results.get("retrieval_performance", {})
        report.append("RETRIEVAL PERFORMANCE")
        report.append("-" * 30)
        report.append(f"Total Queries: {retrieval.get('total_queries', 0)}")
        report.append(f"Successful: {retrieval.get('successful_retrievals', 0)}")
        report.append(f"Average Time: {retrieval.get('average_retrieval_time', 0):.3f}s")
        report.append(f"Relevance Score: {retrieval.get('average_relevance_score', 0):.2%}")
        report.append("")

        # Consolidation
        consolidation = results.get("consolidation", {})
        report.append("CONSOLIDATION")
        report.append("-" * 30)
        report.append(f"Pre-consolidation: {consolidation.get('pre_consolidation_count', 0)}")
        report.append(f"Post-consolidation: {consolidation.get('post_consolidation_count', 0)}")
        report.append(f"Reduction Ratio: {consolidation.get('memory_reduction_ratio', 0):.2%}")
        report.append(f"Time: {consolidation.get('consolidation_time', 0):.3f}s")
        report.append("")

        # Associations
        associations = results.get("associations", {})
        report.append("ASSOCIATIONS")
        report.append("-" * 30)
        report.append(f"Total: {associations.get('total_associations', 0)}")
        report.append(f"Strong: {associations.get('strong_associations', 0)}")
        report.append(f"Weak: {associations.get('weak_associations', 0)}")
        report.append(f"Average Strength: {associations.get('average_association_strength', 0):.2%}")

        report.append("")
        report.append("=" * 60)

        return "\n".join(report)


async def main():
    """Run memory evaluation independently"""
    evaluator = MemoryEvaluator()

    # Try to load memory manager
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.memory.memory_manager import MemoryManager

        memory_manager = MemoryManager()
        await memory_manager.initialize()

        results = await evaluator.run_comprehensive_evaluation(memory_manager)
        report = evaluator.generate_memory_report(results)
        print(report)

        # Save results
        output_dir = Path("results/evaluation")
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_dir / "memory_evaluation.json", 'w') as f:
            json.dump(results, f, indent=2, default=str)

    except Exception as e:
        print(f"Memory evaluation failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())