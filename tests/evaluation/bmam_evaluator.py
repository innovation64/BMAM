"""
BMAM Evaluator - Metric alignment with MemOS Locomo benchmark

This module adapts MemOS evaluation code to calculate identical metrics for BMAM.
Ensures fair comparison on the Locomo dataset.

Metrics:
- LLMJudge Score (GPT-4 binary judgment: CORRECT/WRONG)
- Lexical: F1, ROUGE-1/2/L, BLEU-1/2/3/4, METEOR
- Semantic: BERT-F1, Cosine Similarity
- Performance: Response/Search/Total Duration
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Optional

import nltk
import numpy as np
import transformers
from bert_score import score as bert_score
from dotenv import load_dotenv
from nltk.translate.bleu_score import SmoothingFunction, sentence_bleu
from nltk.translate.meteor_score import meteor_score
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from rouge_score import rouge_scorer
from scipy.spatial.distance import cosine
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
transformers.logging.set_verbosity_error()

# Download NLTK resources
try:
    nltk.download("wordnet", quiet=True)
    nltk.download("punkt", quiet=True)
    nltk.download("punkt_tab", quiet=True)
    logger.info("NLTK resources downloaded")
except Exception as e:
    logger.warning(f"Failed to download NLTK resources: {e}")

# Load sentence transformer
try:
    sentence_model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")
    logger.info("Sentence transformer loaded")
except Exception as e:
    logger.warning(f"Failed to load sentence transformer: {e}")
    sentence_model = None


class LLMGrade(BaseModel):
    llm_judgment: str = Field(description="CORRECT or WRONG")
    llm_reasoning: str = Field(description="Explain why the answer is correct or incorrect.")


async def llm_judge_grader(llm_client, question: str, gold_answer: str, response: str) -> bool:
    """
    LLMJudge evaluator using GPT-4 as judge.

    Args:
        llm_client: AsyncOpenAI client
        question: The question asked
        gold_answer: Ground truth answer
        response: Generated answer to evaluate

    Returns:
        bool: True if CORRECT, False if WRONG
    """
    system_prompt = """
        You are an expert grader that determines if answers to questions match a gold standard answer
        """

    accuracy_prompt = f"""
    Your task is to label an answer to a question as 'CORRECT' or 'WRONG'. You will be given the following data:
        (1) a question (posed by one user to another user),
        (2) a 'gold' (ground truth) answer,
        (3) a generated answer
    which you will score as CORRECT/WRONG.

    The point of the question is to ask about something one user should know about the other user based on their prior conversations.
    The gold answer will usually be a concise and short answer that includes the referenced topic, for example:
    Question: Do you remember what I got the last time I went to Hawaii?
    Gold answer: A shell necklace
    The generated answer might be much longer, but you should be generous with your grading - as long as it touches on the same topic as the gold answer, it should be counted as CORRECT.

    For time related questions, the gold answer will be a specific date, month, year, etc. The generated answer might be much longer or use relative time references (like "last Tuesday" or "next month"), but you should be generous with your grading - as long as it refers to the same date or time period as the gold answer, it should be counted as CORRECT. Even if the format differs (e.g., "May 7th" vs "7 May"), consider it CORRECT if it's the same date.

    Now it's time for the real question:
    Question: {question}
    Gold answer: {gold_answer}
    Generated answer: {response}

    First, provide a short (one sentence) explanation of your reasoning, then finish with CORRECT or WRONG.
    Do NOT include both CORRECT and WRONG in your response, or it will break the evaluation script.

    Just return the label CORRECT or WRONG in a json format with the key as "label".
    """

    response_obj = await llm_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": accuracy_prompt},
        ],
        temperature=0,
    )
    message_content = response_obj.choices[0].message.content
    label = json.loads(message_content)["label"]
    parsed = LLMGrade(llm_judgment=label, llm_reasoning="")

    return parsed.llm_judgment.strip().lower() == "correct"


def calculate_rouge_scores(gold_answer, response):
    """Calculate ROUGE-1/2/L F-scores"""
    metrics = {"rouge1_f": 0.0, "rouge2_f": 0.0, "rougeL_f": 0.0}
    try:
        scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
        rouge_scores = scorer.score(gold_answer, response)
        metrics["rouge1_f"] = rouge_scores["rouge1"].fmeasure
        metrics["rouge2_f"] = rouge_scores["rouge2"].fmeasure
        metrics["rougeL_f"] = rouge_scores["rougeL"].fmeasure
    except Exception as e:
        logger.error(f"Failed to calculate ROUGE scores: {e}")
    return metrics


def calculate_bleu_scores(gold_tokens, response_tokens):
    """Calculate BLEU-1/2/3/4 scores"""
    metrics = {"bleu1": 0.0, "bleu2": 0.0, "bleu3": 0.0, "bleu4": 0.0}

    try:
        smoothing = SmoothingFunction().method1
        weights = [(1, 0, 0, 0), (0.5, 0.5, 0, 0), (0.33, 0.33, 0.33, 0), (0.25, 0.25, 0.25, 0.25)]

        for i, weight in enumerate(weights, 1):
            metrics[f"bleu{i}"] = sentence_bleu(
                [gold_tokens], response_tokens, weights=weight, smoothing_function=smoothing
            )
    except ZeroDivisionError:
        pass
    except Exception as e:
        logger.error(f"Failed to calculate BLEU scores: {e}")

    return metrics


def calculate_meteor_score(gold_tokens, response_tokens):
    """Calculate METEOR score"""
    try:
        return meteor_score([gold_tokens], response_tokens)
    except Exception as e:
        logger.error(f"Failed to calculate METEOR score: {e}")
        return 0.0


def calculate_semantic_similarity(gold_answer, response):
    """Calculate cosine similarity using sentence embeddings"""
    global sentence_model

    try:
        if sentence_model is None:
            sentence_model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")

        gold_embedding = sentence_model.encode([gold_answer], show_progress_bar=False)[0]
        response_embedding = sentence_model.encode([response], show_progress_bar=False)[0]
        return 1 - cosine(gold_embedding, response_embedding)
    except Exception as e:
        logger.error(f"Failed to calculate semantic similarity: {e}")
        return 0.0


def calculate_f1_score(gold_tokens, response_tokens):
    """Calculate token-level F1 score"""
    try:
        gold_set = set(gold_tokens)
        response_set = set(response_tokens)

        if len(gold_set) == 0 or len(response_set) == 0:
            return 0.0

        precision = len(gold_set.intersection(response_set)) / len(response_set)
        recall = len(gold_set.intersection(response_set)) / len(gold_set)

        if precision + recall > 0:
            return 2 * precision * recall / (precision + recall)
        return 0.0
    except Exception as e:
        logger.error(f"Failed to calculate F1 score: {e}")
        return 0.0


def calculate_nlp_metrics(gold_answer, response, context, options=None):
    """
    Calculate all NLP metrics matching MemOS evaluation.

    Args:
        gold_answer: Ground truth answer
        response: Generated answer
        context: Retrieved context/memories used
        options: List of metric categories ["lexical", "semantic"]

    Returns:
        Dict with lexical and semantic metrics
    """
    if options is None:
        options = ["lexical", "semantic"]

    gold_answer = str(gold_answer) if gold_answer is not None else ""
    response = str(response) if response is not None else ""

    metrics = {"context_tokens": len(nltk.word_tokenize(context)) if context else 0}

    if "lexical" in options:
        gold_tokens = nltk.word_tokenize(gold_answer.lower())
        response_tokens = nltk.word_tokenize(response.lower())

        metrics["lexical"] = {}
        metrics["lexical"]["f1"] = calculate_f1_score(gold_tokens, response_tokens)
        metrics["lexical"].update(calculate_rouge_scores(gold_answer, response))
        metrics["lexical"].update(calculate_bleu_scores(gold_tokens, response_tokens))
        metrics["lexical"]["meteor"] = calculate_meteor_score(gold_tokens, response_tokens)

    if "semantic" in options:
        metrics["semantic"] = {}
        metrics["semantic"]["similarity"] = calculate_semantic_similarity(gold_answer, response)
        _, _, f1 = bert_score(
            [gold_answer], [response], lang="en", rescale_with_baseline=True, verbose=False
        )
        metrics["semantic"]["bert_f1"] = f1.item() if f1 is not None else 0.0

    return metrics


async def evaluate_bmam_results(
    results_file: str,
    output_file: str,
    num_runs: int = 3,
    options: List[str] = None
):
    """
    Evaluate BMAM test results using MemOS-compatible metrics.

    Args:
        results_file: Path to BMAM test results JSON
        output_file: Path to save evaluated results
        num_runs: Number of LLMJudge runs per question (for variance)
        options: Metric categories to calculate

    Returns:
        Dict with overall metrics matching MemOS format
    """
    if options is None:
        options = ["lexical", "semantic"]

    logger.info(f"🔍 Evaluating BMAM results from {results_file}")
    logger.info(f"   LLMJudge runs per question: {num_runs}")
    logger.info(f"   Metric categories: {options}")

    # Load BMAM test results
    with open(results_file) as f:
        bmam_results = json.load(f)

    # Initialize OpenAI client for LLMJudge
    load_dotenv()
    oai_client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL")
    )

    # Process each question
    evaluated_results = []
    # ✅ 适配不同的结果格式
    if "detailed_results" in bmam_results:
        # 旧格式: detailed_results.bmam
        detailed = bmam_results["detailed_results"]
        if isinstance(detailed, dict):
            questions = detailed.get("bmam", [])
        else:
            questions = detailed
    else:
        # 新格式: 直接是问题列表
        questions = bmam_results

    logger.info(f"📊 Found {len(questions)} questions to evaluate")

    for q_data in tqdm(questions, desc="Evaluating questions"):
        question = q_data.get("question")
        expected = q_data.get("expected_answer")
        answer = q_data.get("bmam_answer")
        category = q_data.get("category")

        # Get context (memories used)
        context = ""  # TODO: Extract from memories_used

        # Run LLMJudge multiple times for variance
        grading_tasks = [
            llm_judge_grader(oai_client, question, expected, answer)
            for _ in range(num_runs)
        ]
        judgments = await asyncio.gather(*grading_tasks)
        judgments_dict = {f"judgment_{i + 1}": j for i, j in enumerate(judgments)}

        # Calculate NLP metrics
        nlp_metrics = calculate_nlp_metrics(expected, answer, context, options)

        # Match MemOS response format
        evaluated_result = {
            "question": question,
            "answer": answer,
            "golden_answer": expected,
            "category": category,
            "llm_judgments": judgments_dict,
            "nlp_metrics": nlp_metrics,
            "response_duration_ms": q_data.get("response_time_ms", 0.0),
            "search_duration_ms": 0.0,  # TODO: Extract from BMAM metrics
            "total_duration_ms": q_data.get("response_time_ms", 0.0),
        }
        evaluated_results.append(evaluated_result)

    # Calculate overall metrics
    overall_metrics = calculate_overall_metrics(evaluated_results, num_runs)

    # Save results
    output_data = {
        "evaluated_results": evaluated_results,
        "overall_metrics": overall_metrics,
        "config": {
            "num_runs": num_runs,
            "options": options,
            "source_file": results_file,
        }
    }

    # Convert numpy types before JSON serialization
    def convert_numpy(obj):
        if isinstance(obj, np.number):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert_numpy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy(i) for i in obj]
        return obj

    output_data = convert_numpy(output_data)

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    logger.info(f"✅ Evaluation complete, saved to {output_file}")
    logger.info(f"📈 LLMJudge Score: {overall_metrics['llm_judge_score']:.4f}±{overall_metrics['llm_judge_std']:.4f}")

    return overall_metrics


def calculate_overall_metrics(evaluated_results: List[Dict], num_runs: int) -> Dict:
    """
    Calculate overall metrics matching MemOS format.

    Returns metrics structure:
    {
        "llm_judge_score": float,
        "llm_judge_std": float,
        "lexical": {
            "f1": float,
            "rouge1_f": float,
            "rouge2_f": float,
            "rougeL_f": float,
            "bleu1": float,
            "bleu2": float,
            "bleu3": float,
            "bleu4": float,
            "meteor": float,
        },
        "semantic": {
            "bert_f1": float,
            "similarity": float,
        },
        "context_tokens": float,
        "duration": {
            "response_duration_ms": float,
            "search_duration_ms": float,
            "total_duration_ms": float,
        }
    }
    """
    # LLMJudge score calculation
    judgment_run_scores = {f"judgment_{i}": [] for i in range(1, num_runs + 1)}

    for result in evaluated_results:
        for judgment_key, judgment_value in result["llm_judgments"].items():
            score = 1 if judgment_value else 0
            judgment_run_scores[judgment_key].append(score)

    # Average each run, then average across runs
    judgment_avgs = []
    for scores in judgment_run_scores.values():
        if scores:
            judgment_avgs.append(np.mean(scores))

    llm_judge_score = np.mean(judgment_avgs) if judgment_avgs else 0.0
    llm_judge_std = np.std(judgment_avgs) if len(judgment_avgs) > 1 else 0.0

    # Initialize metric accumulators
    overall = {
        "llm_judge_score": llm_judge_score,
        "llm_judge_std": llm_judge_std,
        "lexical": {
            m: [] for m in [
                "f1", "rouge1_f", "rouge2_f", "rougeL_f",
                "bleu1", "bleu2", "bleu3", "bleu4", "meteor"
            ]
        },
        "semantic": {m: [] for m in ["bert_f1", "similarity"]},
        "context_tokens": [],
        "duration": {
            m: [] for m in ["response_duration_ms", "search_duration_ms", "total_duration_ms"]
        }
    }

    # Accumulate metrics
    for result in evaluated_results:
        metrics = result["nlp_metrics"]

        if "lexical" in metrics:
            for k, v in metrics["lexical"].items():
                overall["lexical"][k].append(v)

        if "semantic" in metrics:
            for k, v in metrics["semantic"].items():
                overall["semantic"][k].append(v)

        overall["context_tokens"].append(metrics.get("context_tokens", 0))
        overall["duration"]["response_duration_ms"].append(result["response_duration_ms"])
        overall["duration"]["search_duration_ms"].append(result["search_duration_ms"])
        overall["duration"]["total_duration_ms"].append(result["total_duration_ms"])

    # Calculate averages
    for category in ["lexical", "semantic"]:
        for metric_name in overall[category]:
            values = overall[category][metric_name]
            overall[category][metric_name] = np.mean(values) if values else 0.0

    overall["context_tokens"] = np.mean(overall["context_tokens"]) if overall["context_tokens"] else 0.0

    for duration_metric in overall["duration"]:
        values = overall["duration"][duration_metric]
        overall["duration"][duration_metric] = np.mean(values) if values else 0.0

    return overall


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate BMAM results with MemOS-aligned metrics")
    parser.add_argument("--results", type=str, required=True, help="Path to BMAM test results JSON")
    parser.add_argument("--output", type=str, required=True, help="Path to save evaluated results")
    parser.add_argument("--num_runs", type=int, default=3, help="Number of LLMJudge runs per question")
    parser.add_argument("--options", nargs="+", default=["lexical", "semantic"], help="Metric categories")

    args = parser.parse_args()

    asyncio.run(evaluate_bmam_results(
        args.results,
        args.output,
        args.num_runs,
        args.options
    ))
