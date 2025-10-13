#!/usr/bin/env python3
"""
Resume LoCoMo Test from Checkpoint

Resumes testing from where it crashed:
- Sample 1 (conv-26): Already learned (708 memories), test all 199 QA pairs
- Use batch BERTScore to avoid crashes

Run this to continue from the crash point without re-learning!
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
        logging.FileHandler('test_locomo_resume.log'),
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
            print(f"\n🔄 Calculating BERTScore for {len(references)} QA pairs (batch mode)...")
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
            print(f"✅ BERTScore complete in {elapsed:.1f}s ({elapsed/len(references):.2f}s per QA)")
            return F1.tolist()
        except Exception as e:
            logger.error(f"Batch BERTScore error: {e}")
            return [0.0] * len(references)


async def test_locomo_resume():
    """Resume testing from checkpoint"""

    print("=" * 80)
    print("🔄 Resume LoCoMo Test from Checkpoint")
    print("=" * 80)
    print()

    # Check memory state
    import faiss
    try:
        index = faiss.read_index('data/memory_vectors.index')
        print(f"✅ Found existing memory state: {index.ntotal} vectors")
        print(f"   Last updated: 2025-10-11 20:29")
        print()
    except:
        print("❌ No existing memory state found!")
        print("   Please run the full test from scratch.")
        return

    # Load dataset
    dataset_path = Path('data/benchmarks/locomo/locomo10.json')
    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    # Get Sample 1 (conv-26) - already learned
    sample = dataset[0]
    sample_id = sample.get('sample_id', 'conv-26')
    qa_pairs = sample.get('qa', [])

    print(f"📖 Resuming: Sample 1 - {sample_id}")
    print(f"   Total QA pairs to test: {len(qa_pairs)}")
    print(f"   Memory already loaded: {index.ntotal} vectors")
    print()

    # Initialize systems
    print("🔧 Initializing BMAM Brain Coordinator...")
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()
    print("✅ Coordinator initialized (using existing memory)")

    print("🔧 Initializing LLM Judge...")
    llm_judge = LoCoMoLLMJudge()
    print("✅ LLM Judge initialized")

    print("🔧 Initializing MemOS Metrics Calculator...")
    metrics_calculator = MemOSMetricsCalculator()
    print("✅ Metrics Calculator initialized")
    print()

    # Category mapping
    category_names = {1: 'single_hop', 2: 'temporal', 3: 'multi_hop', 4: 'open_domain'}

    # Phase 1: Generate answers (skip learning!)
    print(f"❓ Phase 1: Generating Answers ({len(qa_pairs)} questions)...")
    print()

    results = []
    correct_count = 0

    with tqdm(total=len(qa_pairs), desc="Answering", unit="question") as pbar:
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
                    'qa_index': qa_idx,
                    'category': category,
                    'question': question,
                    'gold_answer': str(gold_answer),
                    'generated_answer': generated_answer,
                    'llm_judge_correct': is_correct,
                    'response_time': elapsed_time,
                    'memories_retrieved': memories_count,
                    **metrics,
                    'bert_f1': None
                }

                results.append(qa_result)
                if is_correct:
                    correct_count += 1

            except Exception as e:
                logger.error(f"Error Q{qa_idx}: {e}")
                results.append({
                    'qa_index': qa_idx,
                    'category': category,
                    'question': question,
                    'gold_answer': str(gold_answer),
                    'generated_answer': f"ERROR: {e}",
                    'llm_judge_correct': False,
                    'error': str(e)
                })

            pbar.update(1)

    print(f"\n✅ Answers generated: {correct_count}/{len(qa_pairs)} correct ({correct_count/len(qa_pairs)*100:.1f}%)")
    print()

    # Phase 2: Batch BERTScore
    print(f"📊 Phase 2: Calculating BERTScore (batch mode)...")

    references = [r['gold_answer'] for r in results if 'error' not in r]
    generated = [r['generated_answer'] for r in results if 'error' not in r]

    bert_scores = metrics_calculator.batch_calculate_bert_f1(references, generated)

    # Fill in results
    bert_idx = 0
    for qa_result in results:
        if 'error' not in qa_result:
            qa_result['bert_f1'] = bert_scores[bert_idx]
            bert_idx += 1
        else:
            qa_result['bert_f1'] = 0.0

    print()

    # Summary
    print("=" * 80)
    print("📊 Results Summary")
    print("=" * 80)
    print()

    accuracy = (correct_count / len(qa_pairs) * 100)
    print(f"✅ Accuracy: {correct_count}/{len(qa_pairs)} ({accuracy:.2f}%)")
    print()

    # Metrics
    print("📈 MemOS Metrics:")
    print("-" * 80)
    for metric in ['f1', 'rouge_l', 'bleu_1', 'bleu_2', 'meteor', 'bert_f1', 'similarity']:
        values = [r[metric] for r in results if metric in r and r[metric] is not None]
        if values:
            mean = sum(values) / len(values)
            print(f"   {metric.upper():12s}: {mean*100:.2f}")
    print()

    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path('results/locomo_resume')
    results_dir.mkdir(parents=True, exist_ok=True)

    final_results = {
        'timestamp': datetime.now().isoformat(),
        'sample_id': sample_id,
        'total_qa': len(qa_pairs),
        'accuracy': accuracy,
        'correct': correct_count,
        'results': results
    }

    results_file = results_dir / f'locomo_resume_{timestamp}.json'
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(final_results, f, indent=2, ensure_ascii=False)

    print(f"💾 Results saved to: {results_file}")
    print()

    await coordinator.stop_system()
    return final_results


if __name__ == '__main__':
    asyncio.run(test_locomo_resume())
