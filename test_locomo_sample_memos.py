#!/usr/bin/env python3
"""
LoCoMo Dataset Sample Test with Full MemOS Evaluation Metrics

Tests a SAMPLE of LoCoMo benchmark (e.g., first 100 QA pairs from 3 samples)
to quickly get MemOS comparison metrics without running 35 hours.

Full metrics: LLMJudge, F1, ROUGE-L, BLEU-1/2, METEOR, BERT-F1, Similarity
"""

import asyncio
import json
import time
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict
import logging
from tqdm import tqdm

# Add BMAM to path
sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')
os.environ['USE_BRAIN_NETWORK'] = 'true'

from src.coordination.brain_coordinator import BrainInspiredCoordinator
from evaluation.llm_judge_locomo import LoCoMoLLMJudge

# Configure logging
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_locomo_sample.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MemOSMetricsCalculator:
    """Calculate all MemOS evaluation metrics"""

    def __init__(self):
        # Try to import NLP metrics libraries
        try:
            from rouge_score import rouge_scorer
            self.rouge_scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
            self.has_rouge = True
        except ImportError:
            logger.warning("rouge-score not installed")
            self.has_rouge = False

        try:
            from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
            from nltk.translate.meteor_score import meteor_score
            import nltk
            # Download required NLTK data
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt', quiet=True)
            try:
                nltk.data.find('corpora/wordnet')
            except LookupError:
                nltk.download('wordnet', quiet=True)
            self.has_nltk = True
            self.bleu_smoothing = SmoothingFunction().method1
        except ImportError:
            logger.warning("NLTK not installed")
            self.has_nltk = False

        try:
            from bert_score import score as bert_score
            self.bert_score = bert_score
            self.has_bert_score = True
        except ImportError:
            logger.warning("bert-score not installed")
            self.has_bert_score = False

        try:
            from sentence_transformers import SentenceTransformer, util
            self.similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.has_similarity = True
        except ImportError:
            logger.warning("sentence-transformers not installed")
            self.has_similarity = False

    def calculate_f1(self, reference: str, generated: str) -> float:
        """Calculate token-level F1 score"""
        ref_tokens = set(str(reference).lower().split())
        gen_tokens = set(str(generated).lower().split())

        if len(gen_tokens) == 0:
            return 0.0

        common = ref_tokens & gen_tokens
        if len(common) == 0:
            return 0.0

        precision = len(common) / len(gen_tokens)
        recall = len(common) / len(ref_tokens) if len(ref_tokens) > 0 else 0

        if precision + recall == 0:
            return 0.0

        f1 = 2 * (precision * recall) / (precision + recall)
        return f1

    def calculate_rouge_l(self, reference: str, generated: str) -> float:
        """Calculate ROUGE-L score"""
        if not self.has_rouge:
            return 0.0

        try:
            scores = self.rouge_scorer.score(str(reference), str(generated))
            return scores['rougeL'].fmeasure
        except Exception as e:
            logger.error(f"ROUGE-L calculation error: {e}")
            return 0.0

    def calculate_bleu(self, reference: str, generated: str, n: int = 1) -> float:
        """Calculate BLEU-n score"""
        if not self.has_nltk:
            return 0.0

        try:
            from nltk.translate.bleu_score import sentence_bleu
            ref_tokens = [str(reference).lower().split()]
            gen_tokens = str(generated).lower().split()

            if n == 1:
                weights = (1.0, 0, 0, 0)
            elif n == 2:
                weights = (0.5, 0.5, 0, 0)
            else:
                weights = (0.25, 0.25, 0.25, 0.25)

            return sentence_bleu(ref_tokens, gen_tokens, weights=weights, smoothing_function=self.bleu_smoothing)
        except Exception as e:
            logger.error(f"BLEU-{n} calculation error: {e}")
            return 0.0

    def calculate_meteor(self, reference: str, generated: str) -> float:
        """Calculate METEOR score"""
        if not self.has_nltk:
            return 0.0

        try:
            from nltk.translate.meteor_score import meteor_score
            import nltk
            ref_tokens = nltk.word_tokenize(str(reference).lower())
            gen_tokens = nltk.word_tokenize(str(generated).lower())
            return meteor_score([ref_tokens], gen_tokens)
        except Exception as e:
            logger.error(f"METEOR calculation error: {e}")
            return 0.0

    def calculate_bert_f1(self, reference: str, generated: str) -> float:
        """Calculate BERTScore F1"""
        if not self.has_bert_score:
            return 0.0

        try:
            P, R, F1 = self.bert_score([str(generated)], [str(reference)], lang='en', verbose=False)
            return F1.item()
        except Exception as e:
            logger.error(f"BERTScore calculation error: {e}")
            return 0.0

    def calculate_similarity(self, reference: str, generated: str) -> float:
        """Calculate semantic similarity using sentence transformers"""
        if not self.has_similarity:
            return 0.0

        try:
            from sentence_transformers import util
            ref_embedding = self.similarity_model.encode(str(reference), convert_to_tensor=True)
            gen_embedding = self.similarity_model.encode(str(generated), convert_to_tensor=True)
            similarity = util.cos_sim(ref_embedding, gen_embedding)
            return similarity.item()
        except Exception as e:
            logger.error(f"Similarity calculation error: {e}")
            return 0.0

    def calculate_all_metrics(self, reference: str, generated: str) -> Dict[str, float]:
        """Calculate all MemOS metrics for a single QA pair"""
        return {
            'f1': self.calculate_f1(reference, generated),
            'rouge_l': self.calculate_rouge_l(reference, generated),
            'bleu_1': self.calculate_bleu(reference, generated, n=1),
            'bleu_2': self.calculate_bleu(reference, generated, n=2),
            'meteor': self.calculate_meteor(reference, generated),
            'bert_f1': self.calculate_bert_f1(reference, generated),
            'similarity': self.calculate_similarity(reference, generated)
        }


async def test_locomo_sample():
    """Test a sample of LoCoMo dataset for quick MemOS comparison"""

    print("=" * 80)
    print("🧪 LoCoMo Sample Test with MemOS Metrics")
    print("=" * 80)
    print()

    # Configuration
    NUM_SAMPLES = 3  # Test first 3 conversation samples
    MAX_QA_PER_SAMPLE = 50  # Test first 50 QA pairs per sample

    # Load LoCoMo dataset
    dataset_path = Path('data/benchmarks/locomo/locomo10.json')
    if not dataset_path.exists():
        print(f"❌ Dataset not found: {dataset_path}")
        return

    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    print(f"📚 Loaded LoCoMo dataset: {len(dataset)} conversation samples")
    print(f"📊 Testing: First {NUM_SAMPLES} samples, up to {MAX_QA_PER_SAMPLE} QA pairs each")
    print()

    # Initialize systems
    print("🔧 Initializing BMAM Brain Coordinator...")
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()
    print("✅ Coordinator initialized")

    print("🔧 Initializing LLM Judge...")
    llm_judge = LoCoMoLLMJudge()
    print("✅ LLM Judge initialized")

    print("🔧 Initializing MemOS Metrics Calculator...")
    metrics_calculator = MemOSMetricsCalculator()
    print("✅ Metrics Calculator initialized")
    print()

    # Results storage
    all_results = []
    sample_summaries = []
    category_stats = defaultdict(lambda: {'correct': 0, 'total': 0, 'metrics': defaultdict(list)})

    # Category mapping
    category_names = {
        1: 'single_hop',
        2: 'temporal',
        3: 'multi_hop',
        4: 'open_domain'
    }

    # Test selected samples
    for sample_idx in range(min(NUM_SAMPLES, len(dataset))):
        sample = dataset[sample_idx]
        sample_id = sample.get('sample_id', f'sample_{sample_idx+1}')
        conversation = sample.get('conversation', {})
        qa_pairs = sample.get('qa', [])

        speaker_a = conversation.get('speaker_a', 'Speaker A')
        speaker_b = conversation.get('speaker_b', 'Speaker B')

        # Get all sessions
        session_keys = sorted([k for k in conversation.keys() if k.startswith('session_') and not k.endswith('_date_time')])

        print(f"📖 Sample {sample_idx+1}/{NUM_SAMPLES}: {sample_id}")
        print(f"   Speakers: {speaker_a} & {speaker_b}")
        print(f"   Sessions: {len(session_keys)}, QA Pairs: {len(qa_pairs)}")
        print()

        # Phase 1: Learn all sessions
        print(f"   📚 Phase 1: Learning Sessions...")

        total_dialogues = sum(len(conversation[session_key]) for session_key in session_keys)

        with tqdm(total=total_dialogues, desc="   Learning", unit="dialogue", leave=False) as pbar:
            for session_key in session_keys:
                session_dialogues = conversation[session_key]

                for dialogue in session_dialogues:
                    try:
                        speaker = dialogue.get('speaker', '')
                        text = dialogue.get('text', '')
                        dialogue_text = f"{speaker}: {text}"

                        # Process through coordinator
                        await coordinator.process_user_input(dialogue_text, {})
                        pbar.update(1)
                    except Exception as e:
                        logger.error(f"Error learning dialogue: {e}")
                        pbar.update(1)

        print(f"   ✅ Learning complete ({total_dialogues} dialogues)")
        print()

        # Phase 2: Test QA pairs (limited to MAX_QA_PER_SAMPLE)
        qa_to_test = qa_pairs[:MAX_QA_PER_SAMPLE]
        print(f"   ❓ Phase 2: Testing {len(qa_to_test)} Questions...")

        sample_results = []
        sample_correct = 0
        sample_metrics = defaultdict(list)

        with tqdm(total=len(qa_to_test), desc="   Testing", unit="question", leave=False) as pbar:
            for qa_idx, qa in enumerate(qa_to_test, 1):
                question = qa.get('question', '')
                gold_answer = qa.get('answer', '')
                category_id = qa.get('category', 1)
                category = category_names.get(category_id, 'unknown')

                try:
                    # Get system answer
                    start_time = time.time()
                    result = await coordinator.process_user_input(question, {})
                    elapsed_time = time.time() - start_time

                    generated_answer = result.response
                    memories_count = len(result.memories_retrieved) if result.memories_retrieved else 0

                    # LLM Judge evaluation
                    judgment = await llm_judge.judge_answer(question, str(gold_answer), generated_answer)
                    is_correct = judgment['correct']

                    # Calculate all MemOS metrics
                    nlp_metrics = metrics_calculator.calculate_all_metrics(str(gold_answer), generated_answer)

                    # Record result
                    qa_result = {
                        'sample_id': sample_id,
                        'qa_index': qa_idx,
                        'category': category,
                        'question': question,
                        'gold_answer': str(gold_answer),
                        'generated_answer': generated_answer,
                        'llm_judge_correct': is_correct,
                        'llm_judge_label': judgment['label'],
                        'llm_judge_reasoning': judgment['reasoning'],
                        'response_time': elapsed_time,
                        'memories_retrieved': memories_count,
                        **nlp_metrics
                    }

                    sample_results.append(qa_result)
                    all_results.append(qa_result)

                    # Update statistics
                    if is_correct:
                        sample_correct += 1

                    for metric_name, metric_value in nlp_metrics.items():
                        sample_metrics[metric_name].append(metric_value)

                    # Update category statistics
                    category_stats[category]['total'] += 1
                    if is_correct:
                        category_stats[category]['correct'] += 1
                    for metric_name, metric_value in nlp_metrics.items():
                        category_stats[category]['metrics'][metric_name].append(metric_value)

                except Exception as e:
                    logger.error(f"Error testing Q{qa_idx}: {e}")
                    qa_result = {
                        'sample_id': sample_id,
                        'qa_index': qa_idx,
                        'category': category,
                        'question': question,
                        'gold_answer': str(gold_answer),
                        'generated_answer': f"ERROR: {str(e)}",
                        'llm_judge_correct': False,
                        'error': str(e)
                    }
                    sample_results.append(qa_result)
                    all_results.append(qa_result)

                pbar.update(1)

        # Sample summary
        sample_accuracy = (sample_correct / len(qa_to_test) * 100) if len(qa_to_test) > 0 else 0

        sample_summary = {
            'sample_id': sample_id,
            'speakers': f"{speaker_a} & {speaker_b}",
            'total_sessions': len(session_keys),
            'total_dialogues': total_dialogues,
            'total_qa_tested': len(qa_to_test),
            'correct': sample_correct,
            'accuracy': sample_accuracy,
            'avg_metrics': {
                metric: (sum(values) / len(values) if values else 0.0)
                for metric, values in sample_metrics.items()
            }
        }
        sample_summaries.append(sample_summary)

        print(f"   ✅ Sample {sample_idx+1} complete: {sample_correct}/{len(qa_to_test)} ({sample_accuracy:.1f}%)")
        print()

    # Overall summary
    print("=" * 80)
    print("📊 Sample Test Results")
    print("=" * 80)
    print()

    total_qa = len(all_results)
    total_correct = sum(1 for r in all_results if r.get('llm_judge_correct', False))
    overall_accuracy = (total_correct / total_qa * 100) if total_qa > 0 else 0

    print(f"✅ Overall Accuracy (LLMJudge): {total_correct}/{total_qa} ({overall_accuracy:.2f}%)")
    print()

    # Calculate average metrics across all QA pairs
    print("📈 MemOS Metrics (All Tested QA Pairs):")
    print("-" * 80)

    all_metrics = defaultdict(list)
    for result in all_results:
        for metric in ['f1', 'rouge_l', 'bleu_1', 'bleu_2', 'meteor', 'bert_f1', 'similarity']:
            if metric in result:
                all_metrics[metric].append(result[metric])

    metrics_summary = {}
    for metric, values in all_metrics.items():
        if values:
            avg_value = sum(values) / len(values)
            std_value = (sum((x - avg_value) ** 2 for x in values) / len(values)) ** 0.5
            metrics_summary[metric] = {'mean': avg_value, 'std': std_value}
            print(f"   {metric.upper():12s}: {avg_value*100:.2f} ± {std_value*100:.2f}")
        else:
            metrics_summary[metric] = {'mean': 0.0, 'std': 0.0}
            print(f"   {metric.upper():12s}: N/A")
    print()

    # Category breakdown
    print("📊 Performance by Category:")
    print("-" * 80)
    for category, stats in sorted(category_stats.items()):
        cat_accuracy = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"   {category:20s}: {stats['correct']:3d}/{stats['total']:3d} ({cat_accuracy:5.1f}%)")
    print()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path('results/locomo_sample')
    results_dir.mkdir(parents=True, exist_ok=True)

    final_results = {
        'timestamp': datetime.now().isoformat(),
        'dataset': 'LoCoMo-Sample',
        'config': {
            'num_samples': NUM_SAMPLES,
            'max_qa_per_sample': MAX_QA_PER_SAMPLE
        },
        'total_samples_tested': NUM_SAMPLES,
        'total_qa_pairs': total_qa,
        'overall_accuracy': overall_accuracy,
        'overall_correct': total_correct,
        'metrics_summary': metrics_summary,
        'category_stats': dict(category_stats),
        'sample_summaries': sample_summaries,
        'detailed_results': all_results
    }

    results_file = results_dir / f'locomo_sample_results_{timestamp}.json'
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(final_results, f, indent=2, ensure_ascii=False)

    print(f"💾 Results saved to: {results_file}")
    print()

    # Comparison with MemOS baseline
    print("=" * 80)
    print("📊 Comparison with MemOS-0630 Baseline")
    print("=" * 80)
    print()

    memos_baseline = {
        'llm_judge': 73.31,
        'f1': 44.42,
        'rouge_l': 47.65,
        'bleu_1': 36.88,
        'bleu_2': 25.43,
        'meteor': 40.20,
        'bert_f1': 44.15,
        'similarity': 73.51
    }

    print(f"{'Metric':<12} {'MemOS-0630':>12} {'BMAM':>12} {'Gap':>12}")
    print("-" * 50)
    print(f"{'LLMJudge':<12} {memos_baseline['llm_judge']:>12.2f} {overall_accuracy:>12.2f} {overall_accuracy - memos_baseline['llm_judge']:>12.2f}")

    for metric, baseline_value in memos_baseline.items():
        if metric == 'llm_judge':
            continue
        bmam_value = metrics_summary.get(metric, {}).get('mean', 0.0) * 100
        gap = bmam_value - baseline_value
        symbol = "✅" if gap >= 0 else "⚠️"
        print(f"{metric.upper():<12} {baseline_value:>12.2f} {bmam_value:>12.2f} {gap:>11.2f} {symbol}")

    print()
    print("=" * 80)

    # Cleanup
    await coordinator.stop_system()

    return final_results


if __name__ == '__main__':
    asyncio.run(test_locomo_sample())
