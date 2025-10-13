#!/usr/bin/env python3
"""
Resume LoCoMo Test - Complete All Samples

Checkpoint-aware test that:
- Sample 1 (conv-26): Use existing memory (708 vectors), test 199 QA
- Sample 2-10: Learn + Test each sample
- Batch BERTScore per sample to avoid crashes

Total: 1986 QA pairs across 10 samples
"""

import asyncio
import json
import time
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
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
        logging.FileHandler('test_locomo_resume_all.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MemOSMetricsCalculator:
    """Calculate all MemOS evaluation metrics with batch support"""

    def __init__(self):
        try:
            from rouge_score import rouge_scorer
            self.rouge_scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
            self.has_rouge = True
        except ImportError:
            self.has_rouge = False

        try:
            from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
            from nltk.translate.meteor_score import meteor_score
            import nltk
            try:
                nltk.data.find('tokenizers/punkt')
            except:
                nltk.download('punkt', quiet=True)
            try:
                nltk.data.find('corpora/wordnet')
            except:
                nltk.download('wordnet', quiet=True)
            self.has_nltk = True
            self.bleu_smoothing = SmoothingFunction().method1
        except ImportError:
            self.has_nltk = False

        try:
            from bert_score import score as bert_score
            self.bert_score = bert_score
            self.has_bert_score = True
            print("✅ BERTScore available (batch mode)")
        except ImportError:
            self.has_bert_score = False
            print("⚠️  BERTScore not available")

        try:
            from sentence_transformers import SentenceTransformer, util
            self.similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.has_similarity = True
        except ImportError:
            self.has_similarity = False

    def calculate_f1(self, reference: str, generated: str) -> float:
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
        return 2 * (precision * recall) / (precision + recall)

    def calculate_rouge_l(self, reference: str, generated: str) -> float:
        if not self.has_rouge:
            return 0.0
        try:
            scores = self.rouge_scorer.score(str(reference), str(generated))
            return scores['rougeL'].fmeasure
        except:
            return 0.0

    def calculate_bleu(self, reference: str, generated: str, n: int = 1) -> float:
        if not self.has_nltk:
            return 0.0
        try:
            from nltk.translate.bleu_score import sentence_bleu
            ref_tokens = [str(reference).lower().split()]
            gen_tokens = str(generated).lower().split()
            weights = (1.0, 0, 0, 0) if n == 1 else (0.5, 0.5, 0, 0)
            return sentence_bleu(ref_tokens, gen_tokens, weights=weights, smoothing_function=self.bleu_smoothing)
        except:
            return 0.0

    def calculate_meteor(self, reference: str, generated: str) -> float:
        if not self.has_nltk:
            return 0.0
        try:
            from nltk.translate.meteor_score import meteor_score
            import nltk
            ref_tokens = nltk.word_tokenize(str(reference).lower())
            gen_tokens = nltk.word_tokenize(str(generated).lower())
            return meteor_score([ref_tokens], gen_tokens)
        except:
            return 0.0

    def calculate_similarity(self, reference: str, generated: str) -> float:
        if not self.has_similarity:
            return 0.0
        try:
            from sentence_transformers import util
            ref_embedding = self.similarity_model.encode(str(reference), convert_to_tensor=True)
            gen_embedding = self.similarity_model.encode(str(generated), convert_to_tensor=True)
            similarity = util.cos_sim(ref_embedding, gen_embedding)
            return similarity.item()
        except:
            return 0.0

    def calculate_lightweight_metrics(self, reference: str, generated: str) -> Dict[str, float]:
        return {
            'f1': self.calculate_f1(reference, generated),
            'rouge_l': self.calculate_rouge_l(reference, generated),
            'bleu_1': self.calculate_bleu(reference, generated, n=1),
            'bleu_2': self.calculate_bleu(reference, generated, n=2),
            'meteor': self.calculate_meteor(reference, generated),
            'similarity': self.calculate_similarity(reference, generated)
        }

    def batch_calculate_bert_f1(self, references: List[str], generated_list: List[str]) -> List[float]:
        if not self.has_bert_score or len(references) == 0:
            return [0.0] * len(references)

        try:
            print(f"   🔄 Calculating BERTScore for {len(references)} QA pairs...")
            start_time = time.time()

            _, _, F1 = self.bert_score(
                [str(g) for g in generated_list],
                [str(r) for r in references],
                lang='en',
                rescale_with_baseline=True,
                verbose=False,
                batch_size=32
            )

            elapsed = time.time() - start_time
            print(f"   ✅ BERTScore done in {elapsed:.1f}s ({elapsed/len(references):.2f}s/QA)")
            return F1.tolist()
        except Exception as e:
            logger.error(f"Batch BERTScore error: {e}")
            return [0.0] * len(references)


async def test_locomo_complete():
    """Test all 10 samples with checkpoint awareness"""

    print("=" * 80)
    print("🧪 Complete LoCoMo Test (Checkpoint-Aware)")
    print("=" * 80)
    print()

    # Check if Sample 1 memory exists
    import faiss
    has_sample1_memory = False
    try:
        index = faiss.read_index('data/memory_vectors.index')
        if index.ntotal >= 700:  # Sample 1 has ~700 memories
            has_sample1_memory = True
            print(f"✅ Found Sample 1 checkpoint: {index.ntotal} memories loaded")
            print(f"   Will skip learning for Sample 1, directly test")
        else:
            print(f"⚠️  Memory found but incomplete ({index.ntotal} vectors)")
            print(f"   Will learn all samples from scratch")
    except:
        print("⚠️  No checkpoint found, starting from scratch")
    print()

    # Load dataset
    dataset_path = Path('data/benchmarks/locomo/locomo10.json')
    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    total_qa = sum(len(sample.get('qa', [])) for sample in dataset)
    print(f"📚 Dataset: {len(dataset)} samples, {total_qa} QA pairs")
    print()

    # Initialize systems
    print("🔧 Initializing BMAM...")
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

    # Category mapping
    category_names = {1: 'single_hop', 2: 'temporal', 3: 'multi_hop', 4: 'open_domain'}

    # Results storage
    all_results = []
    sample_summaries = []
    category_stats = defaultdict(lambda: {'correct': 0, 'total': 0, 'metrics': defaultdict(list)})

    # Process each sample
    for sample_idx, sample in enumerate(dataset, 1):
        sample_id = sample.get('sample_id', f'sample_{sample_idx}')
        conversation = sample.get('conversation', {})
        qa_pairs = sample.get('qa', [])

        speaker_a = conversation.get('speaker_a', 'Speaker A')
        speaker_b = conversation.get('speaker_b', 'Speaker B')
        session_keys = sorted([k for k in conversation.keys() if k.startswith('session_') and not k.endswith('_date_time')])

        print(f"📖 Sample {sample_idx}/{len(dataset)}: {sample_id}")
        print(f"   Speakers: {speaker_a} & {speaker_b}")
        print(f"   Sessions: {len(session_keys)}, QA: {len(qa_pairs)}")
        print()

        # Phase 1: Learning (skip for Sample 1 if checkpoint exists)
        if sample_idx == 1 and has_sample1_memory:
            print(f"   ⏩ Skipping learning (using checkpoint with {index.ntotal} memories)")
            print()
        else:
            print(f"   📚 Phase 1: Learning Sessions...")
            total_dialogues = sum(len(conversation[sk]) for sk in session_keys)

            with tqdm(total=total_dialogues, desc="   Learning", unit="dialogue", leave=False) as pbar:
                for session_key in session_keys:
                    for dialogue in conversation[session_key]:
                        try:
                            speaker = dialogue.get('speaker', '')
                            text = dialogue.get('text', '')
                            dialogue_text = f"{speaker}: {text}"
                            await coordinator.process_user_input(dialogue_text, {})
                            pbar.update(1)
                        except Exception as e:
                            logger.error(f"Learning error: {e}")
                            pbar.update(1)

            print(f"   ✅ Learning complete ({total_dialogues} dialogues)")
            print()

        # Phase 2: Generate answers
        print(f"   ❓ Phase 2: Answering Questions ({len(qa_pairs)} QA)...")

        sample_results = []
        sample_correct = 0

        with tqdm(total=len(qa_pairs), desc="   Answering", unit="Q", leave=False) as pbar:
            for qa_idx, qa in enumerate(qa_pairs, 1):
                question = qa.get('question', '')
                gold_answer = qa.get('answer', '')
                category_id = qa.get('category', 1)
                category = category_names.get(category_id, 'unknown')

                try:
                    # Get answer
                    start_time = time.time()
                    result = await coordinator.process_user_input(question, {})
                    elapsed_time = time.time() - start_time

                    generated_answer = result.response
                    memories_count = len(result.memories_retrieved) if result.memories_retrieved else 0

                    # LLM Judge
                    judgment = await llm_judge.judge_answer(question, str(gold_answer), generated_answer)
                    is_correct = judgment['correct']

                    # Lightweight metrics
                    metrics = metrics_calculator.calculate_lightweight_metrics(str(gold_answer), generated_answer)

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
                        **metrics,
                        'bert_f1': None
                    }

                    sample_results.append(qa_result)
                    if is_correct:
                        sample_correct += 1

                except Exception as e:
                    logger.error(f"Q{qa_idx} error: {e}")
                    sample_results.append({
                        'sample_id': sample_id,
                        'qa_index': qa_idx,
                        'category': category,
                        'question': question,
                        'gold_answer': str(gold_answer),
                        'generated_answer': f"ERROR: {e}",
                        'llm_judge_correct': False,
                        'error': str(e)
                    })

                pbar.update(1)

        sample_accuracy = (sample_correct / len(qa_pairs) * 100) if len(qa_pairs) > 0 else 0
        print(f"   ✅ Answered: {sample_correct}/{len(qa_pairs)} ({sample_accuracy:.1f}%)")
        print()

        # Phase 3: Batch BERTScore
        print(f"   📊 Phase 3: BERTScore (batch)...")
        references = [r['gold_answer'] for r in sample_results if 'error' not in r]
        generated = [r['generated_answer'] for r in sample_results if 'error' not in r]
        bert_scores = metrics_calculator.batch_calculate_bert_f1(references, generated)

        bert_idx = 0
        for qa_result in sample_results:
            if 'error' not in qa_result:
                qa_result['bert_f1'] = bert_scores[bert_idx]
                bert_idx += 1
            else:
                qa_result['bert_f1'] = 0.0

        print()

        # Update stats
        for qa_result in sample_results:
            all_results.append(qa_result)
            category = qa_result['category']
            category_stats[category]['total'] += 1
            if qa_result.get('llm_judge_correct', False):
                category_stats[category]['correct'] += 1
            for metric in ['f1', 'rouge_l', 'bleu_1', 'bleu_2', 'meteor', 'bert_f1', 'similarity']:
                if metric in qa_result and qa_result[metric] is not None:
                    category_stats[category]['metrics'][metric].append(qa_result[metric])

        sample_summaries.append({
            'sample_id': sample_id,
            'speakers': f"{speaker_a} & {speaker_b}",
            'total_qa': len(qa_pairs),
            'correct': sample_correct,
            'accuracy': sample_accuracy
        })

        print(f"✅ Sample {sample_idx} complete: {sample_correct}/{len(qa_pairs)} ({sample_accuracy:.1f}%)")
        print()
        print("-" * 80)
        print()

    # Overall summary
    print("=" * 80)
    print("📊 Complete Dataset Results")
    print("=" * 80)
    print()

    total_qa_tested = len(all_results)
    total_correct = sum(1 for r in all_results if r.get('llm_judge_correct', False))
    overall_accuracy = (total_correct / total_qa_tested * 100) if total_qa_tested > 0 else 0

    print(f"✅ Overall Accuracy: {total_correct}/{total_qa_tested} ({overall_accuracy:.2f}%)")
    print()

    # Metrics summary
    print("📈 MemOS Metrics (All QA Pairs):")
    print("-" * 80)

    all_metrics = defaultdict(list)
    for result in all_results:
        for metric in ['f1', 'rouge_l', 'bleu_1', 'bleu_2', 'meteor', 'bert_f1', 'similarity']:
            if metric in result and result[metric] is not None:
                all_metrics[metric].append(result[metric])

    metrics_summary = {}
    for metric, values in all_metrics.items():
        if values:
            mean = sum(values) / len(values)
            std = (sum((x - mean) ** 2 for x in values) / len(values)) ** 0.5
            metrics_summary[metric] = {'mean': mean, 'std': std}
            print(f"   {metric.upper():12s}: {mean*100:.2f} ± {std*100:.2f}")
    print()

    # Category breakdown
    print("📊 Performance by Category:")
    print("-" * 80)
    for category, stats in sorted(category_stats.items()):
        cat_accuracy = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"   {category:20s}: {stats['correct']:3d}/{stats['total']:3d} ({cat_accuracy:5.1f}%)")
    print()

    # Sample breakdown
    print("📊 Performance by Sample:")
    print("-" * 80)
    for summary in sample_summaries:
        print(f"   {summary['sample_id']:15s}: {summary['correct']:3d}/{summary['total_qa']:3d} ({summary['accuracy']:5.1f}%)")
    print()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path('results/locomo_complete')
    results_dir.mkdir(parents=True, exist_ok=True)

    final_results = {
        'timestamp': datetime.now().isoformat(),
        'dataset': 'LoCoMo-10-Complete',
        'checkpoint_used': has_sample1_memory,
        'total_samples': len(dataset),
        'total_qa_pairs': total_qa_tested,
        'overall_accuracy': overall_accuracy,
        'overall_correct': total_correct,
        'metrics_summary': metrics_summary,
        'category_stats': dict(category_stats),
        'sample_summaries': sample_summaries,
        'detailed_results': all_results
    }

    results_file = results_dir / f'locomo_complete_{timestamp}.json'
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(final_results, f, indent=2, ensure_ascii=False)

    print(f"💾 Results saved to: {results_file}")
    print()

    # Comparison with MemOS
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

    await coordinator.stop_system()
    return final_results


if __name__ == '__main__':
    asyncio.run(test_locomo_complete())
