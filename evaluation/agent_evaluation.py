#!/usr/bin/env python3
"""
Agent Performance Evaluation Module
Evaluate individual agent and coordination performance
"""

import asyncio
import time
import random
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import numpy as np
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class AgentEvaluator:
    """Evaluate agent performance and coordination"""

    def __init__(self):
        self.agent_metrics = {}
        self.coordination_metrics = {}
        self.test_scenarios = []

    def generate_test_scenarios(self) -> List[Dict]:
        """Generate test scenarios for agent evaluation"""
        scenarios = [
            {
                "id": "scenario_001",
                "type": "single_agent",
                "description": "Simple memory recall",
                "agent": "memory_retrieval",
                "input": "What did I do yesterday?",
                "expected_agents": ["memory_retrieval"],
                "timeout": 5.0
            },
            {
                "id": "scenario_002",
                "type": "multi_agent",
                "description": "Complex planning task",
                "input": "Help me plan a vacation to Japan",
                "expected_agents": ["executive_control", "long_term_memory", "action_execution"],
                "timeout": 10.0
            },
            {
                "id": "scenario_003",
                "type": "emotional",
                "description": "Emotional response",
                "input": "I'm feeling overwhelmed with work",
                "expected_agents": ["personality", "stress_response", "executive_control"],
                "timeout": 7.0
            },
            {
                "id": "scenario_004",
                "type": "learning",
                "description": "Learning and adaptation",
                "input": "Teach me about quantum physics",
                "expected_agents": ["perception_encoding", "consolidation", "long_term_memory"],
                "timeout": 8.0
            },
            {
                "id": "scenario_005",
                "type": "reflection",
                "description": "Self-reflection task",
                "input": "What have I learned this week?",
                "expected_agents": ["reflection", "memory_retrieval", "consolidation"],
                "timeout": 10.0
            },
            {
                "id": "scenario_006",
                "type": "problem_solving",
                "description": "Problem solving scenario",
                "input": "How can I improve my productivity?",
                "expected_agents": ["executive_control", "reflection", "action_execution"],
                "timeout": 8.0
            },
            {
                "id": "scenario_007",
                "type": "memory_distortion",
                "description": "Handle conflicting memories",
                "input": "Did I meet John on Monday or Tuesday?",
                "expected_agents": ["memory_retrieval", "memory_distortion", "executive_control"],
                "timeout": 6.0
            },
            {
                "id": "scenario_008",
                "type": "forgetting",
                "description": "Selective forgetting",
                "input": "Clear unimportant memories from last month",
                "expected_agents": ["forgetting", "memory_retrieval", "executive_control"],
                "timeout": 7.0
            }
        ]

        return scenarios

    async def evaluate_agent_response_time(self, agent_system, agent_name: str) -> Dict:
        """Evaluate individual agent response time"""
        results = {
            "agent": agent_name,
            "response_times": [],
            "average_response_time": 0,
            "min_response_time": float('inf'),
            "max_response_time": 0,
            "timeout_count": 0
        }

        test_inputs = [
            "Simple test input",
            "More complex input with multiple parts",
            "What about this question?",
            "Process this information please",
            "Another test message"
        ]

        for input_text in test_inputs:
            try:
                start = time.time()

                # Send input to specific agent
                agent = agent_system.agents.get(agent_name)
                if agent:
                    response = await asyncio.wait_for(
                        agent.process(input_text),
                        timeout=5.0
                    )
                    elapsed = time.time() - start
                    results["response_times"].append(elapsed)
                    results["min_response_time"] = min(results["min_response_time"], elapsed)
                    results["max_response_time"] = max(results["max_response_time"], elapsed)

            except asyncio.TimeoutError:
                results["timeout_count"] += 1
            except Exception as e:
                logger.error(f"Agent {agent_name} evaluation error: {e}")

        if results["response_times"]:
            results["average_response_time"] = np.mean(results["response_times"])
            results["response_time_std"] = np.std(results["response_times"])

        return results

    async def evaluate_agent_coordination(self, coordinator) -> Dict:
        """Evaluate multi-agent coordination"""
        results = {
            "total_scenarios": 0,
            "successful_coordinations": 0,
            "failed_coordinations": 0,
            "coordination_times": [],
            "agent_participation": {},
            "routing_accuracy": 0
        }

        scenarios = self.generate_test_scenarios()

        for scenario in scenarios:
            try:
                results["total_scenarios"] += 1
                start = time.time()

                # Track which agents participate
                participating_agents = set()

                # Custom callback to track agent activation
                original_route = coordinator.route_message

                async def tracking_route(message, sender=None):
                    result = await original_route(message, sender)
                    if hasattr(coordinator, 'last_active_agents'):
                        participating_agents.update(coordinator.last_active_agents)
                    return result

                coordinator.route_message = tracking_route

                # Process scenario
                response = await asyncio.wait_for(
                    coordinator.process_user_input(scenario["input"]),
                    timeout=scenario["timeout"]
                )

                elapsed = time.time() - start

                # Restore original routing
                coordinator.route_message = original_route

                if response and hasattr(response, 'response') and response.response:
                    results["successful_coordinations"] += 1
                    results["coordination_times"].append(elapsed)

                    # Check if expected agents participated
                    expected = set(scenario.get("expected_agents", []))
                    if expected.intersection(participating_agents):
                        results["routing_accuracy"] += 1

                    # Track agent participation
                    for agent in participating_agents:
                        if agent not in results["agent_participation"]:
                            results["agent_participation"][agent] = 0
                        results["agent_participation"][agent] += 1

            except Exception as e:
                logger.error(f"Coordination evaluation error: {e}")
                results["failed_coordinations"] += 1

        # Calculate metrics
        if results["coordination_times"]:
            results["average_coordination_time"] = np.mean(results["coordination_times"])
            results["coordination_time_std"] = np.std(results["coordination_times"])

        if results["total_scenarios"] > 0:
            results["success_rate"] = results["successful_coordinations"] / results["total_scenarios"]
            results["routing_accuracy"] = results["routing_accuracy"] / results["total_scenarios"]

        return results

    async def evaluate_agent_resource_usage(self, agent_system) -> Dict:
        """Evaluate resource usage by agents"""
        results = {
            "agents": {},
            "total_memory_usage": 0,
            "total_buffer_size": 0
        }

        for agent_name, agent in agent_system.agents.items():
            agent_metrics = {
                "buffer_size": 0,
                "memory_usage_estimate": 0,
                "active_connections": 0
            }

            try:
                # Check agent buffer
                if hasattr(agent, 'buffer'):
                    if hasattr(agent.buffer, '__len__'):
                        agent_metrics["buffer_size"] = len(agent.buffer)
                    elif hasattr(agent.buffer, 'size'):
                        agent_metrics["buffer_size"] = agent.buffer.size()

                # Estimate memory usage (simplified)
                agent_metrics["memory_usage_estimate"] = agent_metrics["buffer_size"] * 1024  # Rough estimate

                # Count active connections
                if hasattr(agent, 'connections'):
                    agent_metrics["active_connections"] = len(agent.connections)

            except Exception as e:
                logger.error(f"Resource evaluation error for {agent_name}: {e}")

            results["agents"][agent_name] = agent_metrics
            results["total_buffer_size"] += agent_metrics["buffer_size"]
            results["total_memory_usage"] += agent_metrics["memory_usage_estimate"]

        return results

    async def evaluate_error_recovery(self, coordinator) -> Dict:
        """Evaluate error recovery capabilities"""
        results = {
            "total_error_scenarios": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "recovery_times": [],
            "error_types": {}
        }

        error_scenarios = [
            {
                "type": "invalid_input",
                "input": None,
                "description": "Null input"
            },
            {
                "type": "malformed_input",
                "input": {"not": "a", "string": "input"},
                "description": "Wrong input type"
            },
            {
                "type": "overflow",
                "input": "x" * 10000,
                "description": "Very long input"
            },
            {
                "type": "special_chars",
                "input": "!@#$%^&*()_+{}[]|\\:;<>?,./",
                "description": "Special characters"
            },
            {
                "type": "empty_input",
                "input": "",
                "description": "Empty string"
            }
        ]

        for scenario in error_scenarios:
            results["total_error_scenarios"] += 1
            error_type = scenario["type"]

            if error_type not in results["error_types"]:
                results["error_types"][error_type] = {
                    "attempts": 0,
                    "recoveries": 0
                }

            results["error_types"][error_type]["attempts"] += 1

            try:
                start = time.time()

                # Attempt to process error scenario
                response = await asyncio.wait_for(
                    coordinator.process_user_input(scenario["input"]),
                    timeout=5.0
                )

                elapsed = time.time() - start

                # If we get here without exception, recovery was successful
                if response and hasattr(response, 'response') and response.response:
                    results["successful_recoveries"] += 1
                    results["recovery_times"].append(elapsed)
                    results["error_types"][error_type]["recoveries"] += 1

            except asyncio.TimeoutError:
                results["failed_recoveries"] += 1
                logger.warning(f"Timeout on error scenario: {scenario['description']}")
            except Exception as e:
                # Check if error was handled gracefully
                if hasattr(coordinator, 'error_handler'):
                    results["successful_recoveries"] += 1
                    results["error_types"][error_type]["recoveries"] += 1
                else:
                    results["failed_recoveries"] += 1
                logger.info(f"Error scenario handled: {scenario['description']} - {e}")

        # Calculate metrics
        if results["recovery_times"]:
            results["average_recovery_time"] = np.mean(results["recovery_times"])

        if results["total_error_scenarios"] > 0:
            results["recovery_rate"] = results["successful_recoveries"] / results["total_error_scenarios"]

        return results

    async def evaluate_load_handling(self, coordinator) -> Dict:
        """Evaluate system under load"""
        results = {
            "load_levels": [],
            "throughput": [],
            "latency": [],
            "error_rates": []
        }

        load_levels = [1, 5, 10, 20, 50]

        for load in load_levels:
            logger.info(f"Testing load level: {load} concurrent requests")

            successes = 0
            errors = 0
            latencies = []

            async def single_request(idx):
                try:
                    start = time.time()
                    response = await coordinator.process_user_input(f"Test request {idx}")
                    elapsed = time.time() - start

                    if response and hasattr(response, 'response') and response.response:
                        return ("success", elapsed)
                    else:
                        return ("error", elapsed)
                except Exception:
                    return ("error", 0)

            # Send concurrent requests
            start_time = time.time()
            tasks = [single_request(i) for i in range(load)]
            results_list = await asyncio.gather(*tasks)
            total_time = time.time() - start_time

            # Process results
            for result, latency in results_list:
                if result == "success":
                    successes += 1
                    if latency > 0:
                        latencies.append(latency)
                else:
                    errors += 1

            # Calculate metrics
            throughput = successes / total_time if total_time > 0 else 0
            avg_latency = np.mean(latencies) if latencies else 0
            error_rate = errors / load if load > 0 else 0

            results["load_levels"].append(load)
            results["throughput"].append(throughput)
            results["latency"].append(avg_latency)
            results["error_rates"].append(error_rate)

        return results

    async def run_comprehensive_evaluation(self, coordinator, agent_system=None) -> Dict:
        """Run all agent evaluation tests"""
        logger.info("Starting comprehensive agent evaluation...")

        results = {
            "timestamp": datetime.now().isoformat(),
            "coordination": await self.evaluate_agent_coordination(coordinator),
            "error_recovery": await self.evaluate_error_recovery(coordinator),
            "load_handling": await self.evaluate_load_handling(coordinator)
        }

        # Add individual agent evaluation if system is available
        if agent_system:
            results["resource_usage"] = await self.evaluate_agent_resource_usage(agent_system)

            # Evaluate key agents
            key_agents = ["executive_control", "memory_retrieval", "personality"]
            results["agent_performance"] = {}

            for agent_name in key_agents:
                if agent_name in agent_system.agents:
                    results["agent_performance"][agent_name] = await self.evaluate_agent_response_time(
                        agent_system, agent_name
                    )

        # Calculate overall score
        scores = []

        if "success_rate" in results["coordination"]:
            scores.append(results["coordination"]["success_rate"])

        if "recovery_rate" in results["error_recovery"]:
            scores.append(results["error_recovery"]["recovery_rate"])

        if results["load_handling"]["error_rates"]:
            avg_error_rate = np.mean(results["load_handling"]["error_rates"])
            scores.append(1 - avg_error_rate)

        results["overall_score"] = np.mean(scores) if scores else 0.0

        return results

    def generate_agent_report(self, results: Dict) -> str:
        """Generate agent evaluation report"""
        report = []
        report.append("=" * 60)
        report.append("AGENT SYSTEM EVALUATION REPORT")
        report.append("=" * 60)
        report.append(f"Timestamp: {results.get('timestamp', 'N/A')}")
        report.append(f"Overall Score: {results.get('overall_score', 0):.2%}")
        report.append("")

        # Coordination
        coord = results.get("coordination", {})
        report.append("AGENT COORDINATION")
        report.append("-" * 30)
        report.append(f"Total Scenarios: {coord.get('total_scenarios', 0)}")
        report.append(f"Successful: {coord.get('successful_coordinations', 0)}")
        report.append(f"Success Rate: {coord.get('success_rate', 0):.2%}")
        report.append(f"Routing Accuracy: {coord.get('routing_accuracy', 0):.2%}")
        report.append(f"Avg Coordination Time: {coord.get('average_coordination_time', 0):.3f}s")
        report.append("")

        # Agent Participation
        if coord.get("agent_participation"):
            report.append("Agent Participation:")
            for agent, count in coord["agent_participation"].items():
                report.append(f"  {agent}: {count} scenarios")
            report.append("")

        # Error Recovery
        recovery = results.get("error_recovery", {})
        report.append("ERROR RECOVERY")
        report.append("-" * 30)
        report.append(f"Total Errors: {recovery.get('total_error_scenarios', 0)}")
        report.append(f"Successful Recoveries: {recovery.get('successful_recoveries', 0)}")
        report.append(f"Recovery Rate: {recovery.get('recovery_rate', 0):.2%}")
        report.append("")

        # Load Handling
        load = results.get("load_handling", {})
        if load.get("load_levels"):
            report.append("LOAD HANDLING")
            report.append("-" * 30)
            report.append("Load | Throughput | Latency | Error Rate")
            for i, level in enumerate(load["load_levels"]):
                throughput = load["throughput"][i] if i < len(load["throughput"]) else 0
                latency = load["latency"][i] if i < len(load["latency"]) else 0
                error_rate = load["error_rates"][i] if i < len(load["error_rates"]) else 0
                report.append(f"{level:4d} | {throughput:10.2f} | {latency:7.3f}s | {error_rate:10.2%}")
            report.append("")

        # Resource Usage
        if "resource_usage" in results:
            resource = results["resource_usage"]
            report.append("RESOURCE USAGE")
            report.append("-" * 30)
            report.append(f"Total Buffer Size: {resource.get('total_buffer_size', 0)}")
            report.append(f"Total Memory Usage: {resource.get('total_memory_usage', 0) / 1024:.2f} KB")

        report.append("")
        report.append("=" * 60)

        return "\n".join(report)


async def main():
    """Run agent evaluation independently"""
    evaluator = AgentEvaluator()

    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.coordination.brain_coordinator import BrainInspiredCoordinator
        from src.agents.agent_system import AgentSystem

        # Initialize systems
        coordinator = BrainInspiredCoordinator()
        await coordinator.initialize()

        agent_system = AgentSystem()
        await agent_system.initialize()

        # Run evaluation
        results = await evaluator.run_comprehensive_evaluation(coordinator, agent_system)
        report = evaluator.generate_agent_report(results)
        print(report)

        # Save results
        output_dir = Path("results/evaluation")
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_dir / "agent_evaluation.json", 'w') as f:
            json.dump(results, f, indent=2, default=str)

        # Cleanup
        await coordinator.stop_system()

    except Exception as e:
        print(f"Agent evaluation failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())