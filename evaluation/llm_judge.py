#!/usr/bin/env python3
"""
LLM Judge Implementation for BMAM Evaluation
OpenAI GPT-based evaluation following MemOS methodology
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import nltk
    from nltk.translate.bleu_score import SmoothingFunction, sentence_bleu
    from nltk.translate.meteor_score import meteor_score
    from rouge_score import rouge_scorer
    from bert_score import score as bert_score
    from sentence_transformers import SentenceTransformer
    from scipy.spatial.distance import cosine
    import numpy as np
    EVALUATION_LIBS_AVAILABLE = True
except ImportError:
    EVALUATION_LIBS_AVAILABLE = False

logger = logging.getLogger(__name__)


class LLMJudge:
    """OpenAI GPT-based evaluation judge for memory system responses"""

    def __init__(self, api_key: str = None, model: str = "gpt-4"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model

        if OPENAI_AVAILABLE and self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("OpenAI client not available. Install openai and set OPENAI_API_KEY.")

        # Initialize evaluation models
        self.rouge_scorer = None
        self.sentence_model = None
        self._init_evaluation_models()

        # MemOS LLM Judge prompt template
        self.judge_prompt_template = """
Your task is to label an answer to a question as 'CORRECT' or 'WRONG'. You will be given the following data:
    (1) a question (posed by one user to another user),
    (2) a 'gold' (ground truth) answer,
    (3) a generated answer
which you will score as CORRECT/WRONG.

The point of the question is to ask about something one user should know about the other user based on their prior conversations.
The gold answer will usually be a concise and short answer that includes the referenced topic, for example:
Question: Where did I buy my new tennis racket from?
Gold answer: the sports store downtown
The generated answer might be much longer, but you should be generous with your grading - as long as it touches on the same topic as the gold answer, it should be counted as CORRECT.

For time related questions, the gold answer will be a specific date, month, year, etc. The generated answer might be much longer or use relative time references (like "last Tuesday" or "next month"), but you should be generous with your grading - as long as it refers to the same date or time period as the gold answer, it should be counted as CORRECT. Even if the format differs (e.g., "May 7th" vs "7 May"), consider it CORRECT if it's the same date.

Now it's time for the real question:
Question: {question}
Gold answer: {golden_answer}
Generated answer: {response}

First, provide a short (one sentence) explanation of your reasoning, then finish with CORRECT or WRONG.
Do NOT include both CORRECT and WRONG in your response, or it will break the evaluation script.

Just return the label CORRECT or WRONG in a json format with the key as "label".
        """

    def _init_evaluation_models(self):
        """Initialize evaluation models and scorers"""
        if not EVALUATION_LIBS_AVAILABLE:
            logger.warning("Evaluation libraries not available. Install rouge-score, bert-score, sentence-transformers, nltk")
            return

        try:
            # Initialize ROUGE scorer
            self.rouge_scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)

            # Initialize sentence transformer for semantic similarity
            self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')

            # Download required NLTK data
            nltk.download('wordnet', quiet=True)
            nltk.download('punkt', quiet=True)

            logger.info("Evaluation models initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize evaluation models: {e}")

    async def evaluate_response(self, question: str, ground_truth: str, generated_response: str) -> Dict[str, Any]:
        """
        Evaluate a generated response against ground truth using multiple metrics
        Following MemOS evaluation methodology
        """
        start_time = time.time()

        evaluation_result = {
            "question": question,
            "ground_truth": ground_truth,
            "generated_response": generated_response,
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "llm_judge": {},
                "lexical": {},
                "semantic": {},
                "performance": {}
            }
        }

        # LLM Judge evaluation (GPT-based)
        if self.client:
            llm_judge_result = await self._llm_judge_evaluation(question, ground_truth, generated_response)
            evaluation_result["metrics"]["llm_judge"] = llm_judge_result
        else:
            logger.warning("OpenAI client not available, skipping LLM judge evaluation")

        # Lexical metrics
        if EVALUATION_LIBS_AVAILABLE:
            lexical_metrics = self._calculate_lexical_metrics(ground_truth, generated_response)
            evaluation_result["metrics"]["lexical"] = lexical_metrics

            # Semantic metrics
            semantic_metrics = self._calculate_semantic_metrics(ground_truth, generated_response)
            evaluation_result["metrics"]["semantic"] = semantic_metrics

        # Performance metrics
        total_duration = (time.time() - start_time) * 1000  # Convert to milliseconds
        evaluation_result["metrics"]["performance"] = {
            "total_duration_ms": total_duration,
            "response_duration_ms": total_duration * 0.7,  # Estimated
            "search_duration_ms": total_duration * 0.3,    # Estimated
            "context_tokens": len(generated_response.split())
        }

        return evaluation_result

    async def _llm_judge_evaluation(self, question: str, ground_truth: str, generated_response: str) -> Dict[str, Any]:
        """
        Perform LLM judge evaluation using OpenAI GPT
        Returns score and reasoning
        """
        try:
            prompt = self.judge_prompt_template.format(
                question=question,
                golden_answer=ground_truth,
                response=generated_response
            )

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert evaluator for memory system responses."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=200
            )

            response_text = response.choices[0].message.content.strip()

            # Try to parse JSON response
            try:
                response_json = json.loads(response_text)
                label = response_json.get("label", "UNKNOWN")
            except json.JSONDecodeError:
                # Fallback: extract CORRECT/WRONG from text
                if "CORRECT" in response_text.upper():
                    label = "CORRECT"
                elif "WRONG" in response_text.upper():
                    label = "WRONG"
                else:
                    label = "UNKNOWN"

            # Convert to binary score
            score = 1.0 if label == "CORRECT" else 0.0

            return {
                "llm_judge_score": score,
                "llm_judge_label": label,
                "llm_judge_reasoning": response_text,
                "model_used": self.model
            }

        except Exception as e:
            logger.error(f"LLM judge evaluation failed: {e}")
            return {
                "llm_judge_score": 0.0,
                "llm_judge_label": "ERROR",
                "llm_judge_reasoning": f"Evaluation failed: {str(e)}",
                "model_used": self.model
            }

    def _calculate_lexical_metrics(self, ground_truth: str, generated_response: str) -> Dict[str, float]:
        """Calculate lexical similarity metrics (ROUGE, BLEU, METEOR)"""
        if not EVALUATION_LIBS_AVAILABLE:
            return {}

        metrics = {}

        try:
            # ROUGE scores
            if self.rouge_scorer:
                rouge_scores = self.rouge_scorer.score(ground_truth, generated_response)
                metrics.update({
                    "rouge1_f": rouge_scores['rouge1'].fmeasure,
                    "rouge2_f": rouge_scores['rouge2'].fmeasure,
                    "rougeL_f": rouge_scores['rougeL'].fmeasure
                })

            # BLEU scores
            reference_tokens = nltk.word_tokenize(ground_truth.lower())
            candidate_tokens = nltk.word_tokenize(generated_response.lower())

            smoothing = SmoothingFunction()

            metrics.update({
                "bleu1": sentence_bleu([reference_tokens], candidate_tokens, weights=(1.0, 0, 0, 0), smoothing_function=smoothing.method1),
                "bleu2": sentence_bleu([reference_tokens], candidate_tokens, weights=(0.5, 0.5, 0, 0), smoothing_function=smoothing.method1),
                "bleu3": sentence_bleu([reference_tokens], candidate_tokens, weights=(0.33, 0.33, 0.33, 0), smoothing_function=smoothing.method1),
                "bleu4": sentence_bleu([reference_tokens], candidate_tokens, weights=(0.25, 0.25, 0.25, 0.25), smoothing_function=smoothing.method1)
            })

            # METEOR score
            metrics["meteor"] = meteor_score([reference_tokens], candidate_tokens)

            # F1 score (token-level)
            metrics["f1"] = self._calculate_f1_score(reference_tokens, candidate_tokens)

        except Exception as e:
            logger.error(f"Lexical metrics calculation failed: {e}")

        return metrics

    def _calculate_semantic_metrics(self, ground_truth: str, generated_response: str) -> Dict[str, float]:
        """Calculate semantic similarity metrics"""
        if not EVALUATION_LIBS_AVAILABLE:
            return {}

        metrics = {}

        try:
            # BERTScore
            P, R, F1 = bert_score([generated_response], [ground_truth], lang="en", verbose=False)
            metrics["bert_f1"] = F1.item()

            # Sentence-level semantic similarity
            if self.sentence_model:
                embeddings = self.sentence_model.encode([ground_truth, generated_response])
                similarity = 1 - cosine(embeddings[0], embeddings[1])
                metrics["similarity"] = max(0, similarity)  # Ensure non-negative

        except Exception as e:
            logger.error(f"Semantic metrics calculation failed: {e}")

        return metrics

    def _calculate_f1_score(self, reference_tokens: List[str], candidate_tokens: List[str]) -> float:
        """Calculate token-level F1 score"""
        if not reference_tokens or not candidate_tokens:
            return 0.0

        ref_set = set(reference_tokens)
        cand_set = set(candidate_tokens)

        if not ref_set or not cand_set:
            return 0.0

        intersection = ref_set.intersection(cand_set)

        precision = len(intersection) / len(cand_set)
        recall = len(intersection) / len(ref_set)

        if precision + recall == 0:
            return 0.0

        return 2 * (precision * recall) / (precision + recall)

    async def batch_evaluate(self, evaluation_pairs: List[Dict[str, str]], max_concurrent: int = 5) -> List[Dict[str, Any]]:
        """
        Evaluate multiple question-answer pairs concurrently

        Args:
            evaluation_pairs: List of dicts with keys: question, ground_truth, generated_response
            max_concurrent: Maximum concurrent evaluations
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def evaluate_single(pair):
            async with semaphore:
                return await self.evaluate_response(
                    pair["question"],
                    pair["ground_truth"],
                    pair["generated_response"]
                )

        tasks = [evaluate_single(pair) for pair in evaluation_pairs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Evaluation {i} failed: {result}")
                # Create error result
                pair = evaluation_pairs[i]
                error_result = {
                    "question": pair["question"],
                    "ground_truth": pair["ground_truth"],
                    "generated_response": pair["generated_response"],
                    "error": str(result),
                    "metrics": {"llm_judge": {"llm_judge_score": 0.0}}
                }
                valid_results.append(error_result)
            else:
                valid_results.append(result)

        return valid_results

    def aggregate_results(self, evaluation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate evaluation results following MemOS methodology
        """
        if not evaluation_results:
            return {}

        aggregated = {
            "total_evaluations": len(evaluation_results),
            "metrics": {
                "llm_judge_score": 0.0,
                "llm_judge_std": 0.0,
                "lexical": {},
                "semantic": {},
                "duration": {},
                "context_tokens": 0.0
            },
            "category_scores": {},
            "evaluation_details": evaluation_results
        }

        # Collect all metric values
        llm_scores = []
        lexical_metrics = {}
        semantic_metrics = {}
        duration_metrics = {}
        context_tokens = []

        for result in evaluation_results:
            metrics = result.get("metrics", {})

            # LLM judge scores
            llm_judge = metrics.get("llm_judge", {})
            if "llm_judge_score" in llm_judge:
                llm_scores.append(llm_judge["llm_judge_score"])

            # Lexical metrics
            lexical = metrics.get("lexical", {})
            for metric, value in lexical.items():
                if metric not in lexical_metrics:
                    lexical_metrics[metric] = []
                lexical_metrics[metric].append(value)

            # Semantic metrics
            semantic = metrics.get("semantic", {})
            for metric, value in semantic.items():
                if metric not in semantic_metrics:
                    semantic_metrics[metric] = []
                semantic_metrics[metric].append(value)

            # Performance metrics
            performance = metrics.get("performance", {})
            for metric, value in performance.items():
                if metric == "context_tokens":
                    context_tokens.append(value)
                else:
                    if metric not in duration_metrics:
                        duration_metrics[metric] = []
                    duration_metrics[metric].append(value)

        # Calculate aggregated scores
        if llm_scores:
            aggregated["metrics"]["llm_judge_score"] = np.mean(llm_scores)
            aggregated["metrics"]["llm_judge_std"] = np.std(llm_scores)

        # Aggregate lexical metrics
        for metric, values in lexical_metrics.items():
            if values:
                aggregated["metrics"]["lexical"][metric] = np.mean(values)

        # Aggregate semantic metrics
        for metric, values in semantic_metrics.items():
            if values:
                aggregated["metrics"]["semantic"][metric] = np.mean(values)

        # Aggregate duration metrics
        for metric, values in duration_metrics.items():
            if values:
                aggregated["metrics"]["duration"][metric] = np.mean(values)

        # Context tokens
        if context_tokens:
            aggregated["metrics"]["context_tokens"] = np.mean(context_tokens)

        return aggregated


async def main():
    """Test LLM Judge functionality"""
    judge = LLMJudge()

    # Test evaluation pairs
    test_pairs = [
        {
            "question": "What did I have for lunch yesterday?",
            "ground_truth": "pizza and salad",
            "generated_response": "You had pizza with a side salad for lunch yesterday."
        },
        {
            "question": "When is my meeting with John?",
            "ground_truth": "tomorrow at 3 PM",
            "generated_response": "Your meeting with John is scheduled for tomorrow afternoon at 3:00 PM."
        },
        {
            "question": "Where did I park my car?",
            "ground_truth": "parking garage level 2",
            "generated_response": "I don't have information about where you parked your car."
        }
    ]

    print("Testing LLM Judge evaluation...")

    # Batch evaluation
    results = await judge.batch_evaluate(test_pairs)

    # Aggregate results
    aggregated = judge.aggregate_results(results)

    print(f"\nEvaluation Results:")
    print(f"Total evaluations: {aggregated['total_evaluations']}")
    print(f"LLM Judge Score: {aggregated['metrics']['llm_judge_score']:.3f}")
    print(f"LLM Judge Std: {aggregated['metrics']['llm_judge_std']:.3f}")

    if aggregated['metrics']['lexical']:
        print(f"Lexical metrics: {aggregated['metrics']['lexical']}")

    if aggregated['metrics']['semantic']:
        print(f"Semantic metrics: {aggregated['metrics']['semantic']}")


if __name__ == "__main__":
    asyncio.run(main())