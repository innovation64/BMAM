#!/usr/bin/env python3
"""
Persona Consistency Evaluation Module
Evaluate personality consistency and character coherence
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


class PersonaEvaluator:
    """Evaluate persona consistency and personality traits"""

    def __init__(self):
        self.personality_traits = {}
        self.consistency_scores = []
        self.interaction_history = []

    def generate_personality_test_questions(self) -> List[Dict]:
        """Generate questions to test personality consistency"""
        questions = [
            # Values and beliefs
            {
                "id": "values_001",
                "category": "values",
                "question": "What's most important to you in life?",
                "traits": ["openness", "conscientiousness"],
                "expected_themes": ["growth", "learning", "helping", "connection"]
            },
            {
                "id": "values_002",
                "category": "values",
                "question": "How do you feel about helping others?",
                "traits": ["agreeableness", "empathy"],
                "expected_themes": ["supportive", "caring", "helpful", "understanding"]
            },

            # Emotional responses
            {
                "id": "emotion_001",
                "category": "emotional",
                "question": "How do you handle stress?",
                "traits": ["neuroticism", "stability"],
                "expected_themes": ["calm", "thoughtful", "systematic", "patient"]
            },
            {
                "id": "emotion_002",
                "category": "emotional",
                "question": "What makes you happy?",
                "traits": ["extraversion", "positivity"],
                "expected_themes": ["learning", "helping", "connecting", "achieving"]
            },

            # Social interactions
            {
                "id": "social_001",
                "category": "social",
                "question": "How do you prefer to spend your free time?",
                "traits": ["extraversion", "openness"],
                "expected_themes": ["learning", "creating", "exploring", "reflecting"]
            },
            {
                "id": "social_002",
                "category": "social",
                "question": "How do you feel about meeting new people?",
                "traits": ["extraversion", "agreeableness"],
                "expected_themes": ["interested", "curious", "welcoming", "friendly"]
            },

            # Decision making
            {
                "id": "decision_001",
                "category": "decision",
                "question": "How do you make important decisions?",
                "traits": ["conscientiousness", "thinking"],
                "expected_themes": ["careful", "analytical", "thoughtful", "systematic"]
            },
            {
                "id": "decision_002",
                "category": "decision",
                "question": "Do you prefer planning or spontaneity?",
                "traits": ["conscientiousness", "openness"],
                "expected_themes": ["balance", "flexible", "organized", "adaptive"]
            },

            # Self-perception
            {
                "id": "self_001",
                "category": "self",
                "question": "How would you describe yourself?",
                "traits": ["all"],
                "expected_themes": ["helpful", "curious", "thoughtful", "supportive"]
            },
            {
                "id": "self_002",
                "category": "self",
                "question": "What are your strengths?",
                "traits": ["all"],
                "expected_themes": ["learning", "empathy", "analysis", "support"]
            }
        ]

        return questions

    def generate_interaction_scenarios(self) -> List[Dict]:
        """Generate interaction scenarios for testing"""
        scenarios = [
            {
                "id": "scenario_happy",
                "context": "User shares good news",
                "input": "I just got promoted at work!",
                "expected_emotion": "joy",
                "expected_response_traits": ["congratulatory", "supportive", "enthusiastic"]
            },
            {
                "id": "scenario_sad",
                "context": "User expresses sadness",
                "input": "I'm feeling really down today",
                "expected_emotion": "concern",
                "expected_response_traits": ["empathetic", "supportive", "understanding"]
            },
            {
                "id": "scenario_confused",
                "context": "User asks for clarification",
                "input": "I don't understand this concept",
                "expected_emotion": "helpful",
                "expected_response_traits": ["patient", "clear", "educational"]
            },
            {
                "id": "scenario_angry",
                "context": "User expresses frustration",
                "input": "This is so frustrating!",
                "expected_emotion": "calm",
                "expected_response_traits": ["understanding", "calming", "solution-oriented"]
            },
            {
                "id": "scenario_curious",
                "context": "User asks philosophical question",
                "input": "What do you think is the meaning of life?",
                "expected_emotion": "thoughtful",
                "expected_response_traits": ["reflective", "open", "philosophical"]
            }
        ]

        return scenarios

    async def evaluate_personality_consistency(self, coordinator) -> Dict:
        """Evaluate consistency in personality traits"""
        logger.info("Evaluating personality consistency...")

        results = {
            "questions_asked": 0,
            "trait_consistency": {},
            "theme_frequency": {},
            "consistency_scores": []
        }

        questions = self.generate_personality_test_questions()

        # Ask questions multiple times to check consistency
        for question in questions:
            responses = []

            # Ask the same question 3 times with slight variations
            variations = [
                question["question"],
                question["question"] + " Please tell me more.",
                "I'm curious - " + question["question"]
            ]

            for variation in variations:
                try:
                    processing_result = await coordinator.process_user_input(variation)
                    response = processing_result.response if hasattr(processing_result, 'response') else str(processing_result)
                    responses.append(response)
                    results["questions_asked"] += 1

                    # Analyze themes in response
                    for theme in question["expected_themes"]:
                        if theme.lower() in response.lower():
                            if theme not in results["theme_frequency"]:
                                results["theme_frequency"][theme] = 0
                            results["theme_frequency"][theme] += 1

                    await asyncio.sleep(0.5)  # Small delay between questions

                except Exception as e:
                    logger.error(f"Personality test error: {e}")

            # Calculate consistency score for this question
            if len(responses) >= 2:
                consistency_score = self._calculate_response_consistency(responses)
                results["consistency_scores"].append(consistency_score)

                # Track trait consistency
                for trait in question["traits"]:
                    if trait not in results["trait_consistency"]:
                        results["trait_consistency"][trait] = []
                    results["trait_consistency"][trait].append(consistency_score)

        # Calculate overall metrics
        if results["consistency_scores"]:
            results["average_consistency"] = np.mean(results["consistency_scores"])
            results["consistency_std"] = np.std(results["consistency_scores"])

        # Calculate trait averages
        for trait, scores in results["trait_consistency"].items():
            if scores:
                results["trait_consistency"][trait] = {
                    "average": np.mean(scores),
                    "std": np.std(scores),
                    "samples": len(scores)
                }

        return results

    async def evaluate_emotional_appropriateness(self, coordinator) -> Dict:
        """Evaluate appropriateness of emotional responses"""
        logger.info("Evaluating emotional appropriateness...")

        results = {
            "scenarios_tested": 0,
            "appropriate_responses": 0,
            "emotion_accuracy": {},
            "response_traits": {}
        }

        scenarios = self.generate_interaction_scenarios()

        for scenario in scenarios:
            try:
                # Send scenario input
                processing_result = await coordinator.process_user_input(scenario["input"])
                response = processing_result.response if hasattr(processing_result, 'response') else str(processing_result)
                results["scenarios_tested"] += 1

                # Analyze emotional appropriateness
                is_appropriate = False
                detected_traits = []

                # Check for expected response traits
                for trait in scenario["expected_response_traits"]:
                    if self._detect_trait_in_response(trait, response):
                        detected_traits.append(trait)
                        is_appropriate = True

                if is_appropriate:
                    results["appropriate_responses"] += 1

                # Track emotion accuracy
                emotion = scenario["expected_emotion"]
                if emotion not in results["emotion_accuracy"]:
                    results["emotion_accuracy"][emotion] = {
                        "total": 0,
                        "correct": 0
                    }

                results["emotion_accuracy"][emotion]["total"] += 1
                if is_appropriate:
                    results["emotion_accuracy"][emotion]["correct"] += 1

                # Track detected traits
                for trait in detected_traits:
                    if trait not in results["response_traits"]:
                        results["response_traits"][trait] = 0
                    results["response_traits"][trait] += 1

                # Store in interaction history
                self.interaction_history.append({
                    "scenario": scenario["id"],
                    "input": scenario["input"],
                    "response": response,
                    "appropriate": is_appropriate,
                    "detected_traits": detected_traits
                })

            except Exception as e:
                logger.error(f"Emotional evaluation error: {e}")

        # Calculate overall appropriateness
        if results["scenarios_tested"] > 0:
            results["appropriateness_rate"] = results["appropriate_responses"] / results["scenarios_tested"]

        # Calculate emotion-specific accuracy
        for emotion, data in results["emotion_accuracy"].items():
            if data["total"] > 0:
                data["accuracy"] = data["correct"] / data["total"]

        return results

    async def evaluate_character_coherence(self, coordinator) -> Dict:
        """Evaluate character/persona coherence over time"""
        logger.info("Evaluating character coherence...")

        results = {
            "coherence_tests": 0,
            "consistent_traits": [],
            "trait_stability": {},
            "character_drift": 0
        }

        # Define core character traits to track
        core_traits = {
            "helpful": ["help", "assist", "support", "aid"],
            "curious": ["curious", "wonder", "interested", "learn"],
            "empathetic": ["understand", "feel", "empathy", "care"],
            "thoughtful": ["think", "consider", "reflect", "ponder"],
            "friendly": ["friend", "warm", "kind", "welcoming"]
        }

        # Test trait persistence over multiple interactions
        test_prompts = [
            "Tell me about yourself",
            "What are you like?",
            "Describe your personality",
            "Who are you?",
            "What defines you?"
        ]

        trait_occurrences = {trait: [] for trait in core_traits}

        for i, prompt in enumerate(test_prompts):
            try:
                processing_result = await coordinator.process_user_input(prompt)
                response = processing_result.response if hasattr(processing_result, 'response') else str(processing_result)
                results["coherence_tests"] += 1

                # Check for each trait
                for trait, keywords in core_traits.items():
                    trait_present = any(keyword in response.lower() for keyword in keywords)
                    trait_occurrences[trait].append(trait_present)

                await asyncio.sleep(1)  # Delay between tests

            except Exception as e:
                logger.error(f"Coherence test error: {e}")

        # Analyze trait stability
        for trait, occurrences in trait_occurrences.items():
            if occurrences:
                stability = sum(occurrences) / len(occurrences)
                results["trait_stability"][trait] = stability

                # Consider trait consistent if present >60% of the time
                if stability > 0.6:
                    results["consistent_traits"].append(trait)

        # Calculate character drift (change over time)
        if len(test_prompts) > 1:
            early_traits = set()
            late_traits = set()

            for trait, occurrences in trait_occurrences.items():
                if occurrences[:2].count(True) > 0:
                    early_traits.add(trait)
                if occurrences[-2:].count(True) > 0:
                    late_traits.add(trait)

            # Drift is the symmetric difference between early and late traits
            drift_traits = early_traits.symmetric_difference(late_traits)
            results["character_drift"] = len(drift_traits) / len(core_traits)

        return results

    async def evaluate_context_awareness(self, coordinator) -> Dict:
        """Evaluate persona's context awareness"""
        logger.info("Evaluating context awareness...")

        results = {
            "context_tests": 0,
            "context_maintained": 0,
            "context_lost": 0,
            "response_adaptation": []
        }

        # Context scenarios
        context_scenarios = [
            {
                "setup": "I'm a teacher",
                "followup": "What advice do you have for my profession?",
                "expected_context": ["teach", "student", "education", "classroom"]
            },
            {
                "setup": "I'm feeling stressed about exams",
                "followup": "How should I prepare?",
                "expected_context": ["study", "exam", "stress", "preparation"]
            },
            {
                "setup": "I love cooking Italian food",
                "followup": "What should I make for dinner?",
                "expected_context": ["italian", "pasta", "cooking", "recipe"]
            }
        ]

        for scenario in context_scenarios:
            try:
                # Set context
                await coordinator.process_user_input(scenario["setup"])
                await asyncio.sleep(0.5)

                # Test context retention
                processing_result = await coordinator.process_user_input(scenario["followup"])
                response = processing_result.response if hasattr(processing_result, 'response') else str(processing_result)
                results["context_tests"] += 1

                # Check if context is maintained
                context_present = any(
                    keyword in response.lower()
                    for keyword in scenario["expected_context"]
                )

                if context_present:
                    results["context_maintained"] += 1
                else:
                    results["context_lost"] += 1

                results["response_adaptation"].append({
                    "setup": scenario["setup"],
                    "followup": scenario["followup"],
                    "response": response,
                    "context_maintained": context_present
                })

            except Exception as e:
                logger.error(f"Context awareness test error: {e}")

        # Calculate context retention rate
        if results["context_tests"] > 0:
            results["context_retention_rate"] = results["context_maintained"] / results["context_tests"]

        return results

    def _calculate_response_consistency(self, responses: List[str]) -> float:
        """Calculate consistency between multiple responses"""
        if len(responses) < 2:
            return 0.0

        # Extract key words from each response
        word_sets = []
        for response in responses:
            words = set(word.lower() for word in response.split() if len(word) > 4)
            word_sets.append(words)

        # Calculate Jaccard similarity between response pairs
        similarities = []
        for i in range(len(word_sets)):
            for j in range(i + 1, len(word_sets)):
                intersection = word_sets[i].intersection(word_sets[j])
                union = word_sets[i].union(word_sets[j])
                if union:
                    similarity = len(intersection) / len(union)
                    similarities.append(similarity)

        return np.mean(similarities) if similarities else 0.0

    def _detect_trait_in_response(self, trait: str, response: str) -> bool:
        """Detect if a trait is present in the response"""
        trait_indicators = {
            "congratulatory": ["congratulations", "congrats", "wonderful", "fantastic", "great"],
            "supportive": ["support", "help", "here for you", "assist", "aid"],
            "enthusiastic": ["excited", "amazing", "wonderful", "fantastic", "great"],
            "empathetic": ["understand", "feel", "sorry", "must be", "I can imagine"],
            "understanding": ["understand", "see", "makes sense", "I get it", "clear"],
            "patient": ["take your time", "no rush", "step by step", "gradually"],
            "clear": ["let me explain", "here's how", "basically", "simply put"],
            "educational": ["learn", "explain", "understand", "concept", "idea"],
            "calming": ["it's okay", "take a breath", "calm", "relax", "don't worry"],
            "solution-oriented": ["try", "could", "perhaps", "solution", "approach"],
            "reflective": ["think", "believe", "consider", "wonder", "perhaps"],
            "open": ["many ways", "depends", "various", "different perspectives"],
            "philosophical": ["meaning", "purpose", "exist", "life", "philosophical"]
        }

        indicators = trait_indicators.get(trait, [trait])
        return any(indicator in response.lower() for indicator in indicators)

    async def run_comprehensive_evaluation(self, coordinator) -> Dict:
        """Run all persona evaluation tests"""
        logger.info("Starting comprehensive persona evaluation...")

        results = {
            "timestamp": datetime.now().isoformat(),
            "personality_consistency": await self.evaluate_personality_consistency(coordinator),
            "emotional_appropriateness": await self.evaluate_emotional_appropriateness(coordinator),
            "character_coherence": await self.evaluate_character_coherence(coordinator),
            "context_awareness": await self.evaluate_context_awareness(coordinator)
        }

        # Calculate overall persona score
        scores = []

        if "average_consistency" in results["personality_consistency"]:
            scores.append(results["personality_consistency"]["average_consistency"])

        if "appropriateness_rate" in results["emotional_appropriateness"]:
            scores.append(results["emotional_appropriateness"]["appropriateness_rate"])

        if results["character_coherence"]["trait_stability"]:
            avg_stability = np.mean(list(results["character_coherence"]["trait_stability"].values()))
            scores.append(avg_stability)

        if "context_retention_rate" in results["context_awareness"]:
            scores.append(results["context_awareness"]["context_retention_rate"])

        results["overall_score"] = np.mean(scores) if scores else 0.0

        # Add interaction history
        results["interaction_history"] = self.interaction_history

        return results

    def generate_persona_report(self, results: Dict) -> str:
        """Generate persona evaluation report"""
        report = []
        report.append("=" * 60)
        report.append("PERSONA CONSISTENCY EVALUATION REPORT")
        report.append("=" * 60)
        report.append(f"Timestamp: {results.get('timestamp', 'N/A')}")
        report.append(f"Overall Score: {results.get('overall_score', 0):.2%}")
        report.append("")

        # Personality Consistency
        personality = results.get("personality_consistency", {})
        report.append("PERSONALITY CONSISTENCY")
        report.append("-" * 30)
        report.append(f"Questions Asked: {personality.get('questions_asked', 0)}")
        report.append(f"Average Consistency: {personality.get('average_consistency', 0):.2%}")

        if personality.get("trait_consistency"):
            report.append("\nTrait Consistency:")
            for trait, data in personality["trait_consistency"].items():
                if isinstance(data, dict):
                    report.append(f"  {trait}: {data['average']:.2%} (±{data['std']:.2%})")

        if personality.get("theme_frequency"):
            top_themes = sorted(personality["theme_frequency"].items(), key=lambda x: x[1], reverse=True)[:5]
            report.append("\nTop Themes:")
            for theme, count in top_themes:
                report.append(f"  {theme}: {count} occurrences")
        report.append("")

        # Emotional Appropriateness
        emotional = results.get("emotional_appropriateness", {})
        report.append("EMOTIONAL APPROPRIATENESS")
        report.append("-" * 30)
        report.append(f"Scenarios Tested: {emotional.get('scenarios_tested', 0)}")
        report.append(f"Appropriate Responses: {emotional.get('appropriate_responses', 0)}")
        report.append(f"Appropriateness Rate: {emotional.get('appropriateness_rate', 0):.2%}")

        if emotional.get("emotion_accuracy"):
            report.append("\nEmotion-Specific Accuracy:")
            for emotion, data in emotional["emotion_accuracy"].items():
                if "accuracy" in data:
                    report.append(f"  {emotion}: {data['accuracy']:.2%}")
        report.append("")

        # Character Coherence
        coherence = results.get("character_coherence", {})
        report.append("CHARACTER COHERENCE")
        report.append("-" * 30)
        report.append(f"Coherence Tests: {coherence.get('coherence_tests', 0)}")
        report.append(f"Character Drift: {coherence.get('character_drift', 0):.2%}")

        if coherence.get("consistent_traits"):
            report.append(f"Consistent Traits: {', '.join(coherence['consistent_traits'])}")

        if coherence.get("trait_stability"):
            report.append("\nTrait Stability:")
            for trait, stability in coherence["trait_stability"].items():
                report.append(f"  {trait}: {stability:.2%}")
        report.append("")

        # Context Awareness
        context = results.get("context_awareness", {})
        report.append("CONTEXT AWARENESS")
        report.append("-" * 30)
        report.append(f"Context Tests: {context.get('context_tests', 0)}")
        report.append(f"Context Maintained: {context.get('context_maintained', 0)}")
        report.append(f"Retention Rate: {context.get('context_retention_rate', 0):.2%}")

        report.append("")
        report.append("=" * 60)

        return "\n".join(report)


async def main():
    """Run persona evaluation independently"""
    evaluator = PersonaEvaluator()

    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.coordination.brain_coordinator import BrainInspiredCoordinator

        # Initialize coordinator
        coordinator = BrainInspiredCoordinator()
        await coordinator.initialize()

        # Run evaluation
        results = await evaluator.run_comprehensive_evaluation(coordinator)
        report = evaluator.generate_persona_report(results)
        print(report)

        # Save results
        output_dir = Path("results/evaluation")
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_dir / "persona_evaluation.json", 'w') as f:
            json.dump(results, f, indent=2, default=str)

        # Cleanup
        await coordinator.stop_system()

    except Exception as e:
        print(f"Persona evaluation failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())