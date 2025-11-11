#!/usr/bin/env python3
"""
Long-Term Retrieval Quality Evaluation Framework
长程检索质量评估框架

Objective: Quantify long-term storage retrieval effectiveness using precision/recall metrics
compared to short-term (Hippocampus-only) retrieval.

Methodology:
1. Create ground truth dataset with labeled relevance
2. Ingest memories and trigger consolidation
3. Test retrieval with both strategies:
   - Short-term only (Hippocampus)
   - Long-term enabled (TemporalLobe + MemorySystem)
4. Calculate metrics: Precision, Recall, F1-Score, MRR

Metrics Definitions:
- Precision: relevant_retrieved / total_retrieved
- Recall: relevant_retrieved / total_relevant
- F1-Score: 2 * (Precision * Recall) / (Precision + Recall)
- MRR (Mean Reciprocal Rank): Average of 1/rank for first relevant result
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Set

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator


# Ground truth dataset with labeled relevance
GROUND_TRUTH_DATASET = {
    'memories': [
        # Topic 1: Machine Learning Research
        {'id': 'ml_001', 'content': 'AlexNet won ImageNet 2012 competition with deep CNN.', 'topics': ['ml', 'vision'], 'importance': 0.9},
        {'id': 'ml_002', 'content': 'ResNet introduced skip connections for deeper networks.', 'topics': ['ml', 'vision'], 'importance': 0.9},
        {'id': 'ml_003', 'content': 'BERT revolutionized NLP with bidirectional transformers.', 'topics': ['ml', 'nlp'], 'importance': 0.9},
        {'id': 'ml_004', 'content': 'GPT-3 demonstrated few-shot learning capabilities.', 'topics': ['ml', 'nlp'], 'importance': 0.9},
        {'id': 'ml_005', 'content': 'AlphaGo defeated world champion Lee Sedol in 2016.', 'topics': ['ml', 'rl'], 'importance': 0.8},

        # Topic 2: Neuroscience
        {'id': 'neuro_001', 'content': 'Hippocampus is critical for episodic memory formation.', 'topics': ['neuro', 'memory'], 'importance': 0.9},
        {'id': 'neuro_002', 'content': 'Prefrontal cortex handles executive functions and planning.', 'topics': ['neuro', 'cognition'], 'importance': 0.8},
        {'id': 'neuro_003', 'content': 'Memory consolidation occurs during sleep stages.', 'topics': ['neuro', 'memory'], 'importance': 0.9},
        {'id': 'neuro_004', 'content': 'Long-term potentiation strengthens synaptic connections.', 'topics': ['neuro', 'memory'], 'importance': 0.8},
        {'id': 'neuro_005', 'content': 'Working memory capacity is limited to 7±2 items.', 'topics': ['neuro', 'cognition'], 'importance': 0.7},

        # Topic 3: Climate Science
        {'id': 'climate_001', 'content': 'CO2 levels reached 420 ppm in 2023, highest in 3 million years.', 'topics': ['climate', 'data'], 'importance': 0.9},
        {'id': 'climate_002', 'content': 'Arctic sea ice is declining at 13% per decade.', 'topics': ['climate', 'data'], 'importance': 0.8},
        {'id': 'climate_003', 'content': 'Renewable energy costs dropped 90% since 2010.', 'topics': ['climate', 'tech'], 'importance': 0.8},
        {'id': 'climate_004', 'content': 'Paris Agreement aims to limit warming to 1.5°C.', 'topics': ['climate', 'policy'], 'importance': 0.9},
        {'id': 'climate_005', 'content': 'Electric vehicle sales exceeded 10 million in 2022.', 'topics': ['climate', 'tech'], 'importance': 0.7},

        # Topic 4: Space Exploration
        {'id': 'space_001', 'content': 'James Webb Space Telescope launched in December 2021.', 'topics': ['space', 'tech'], 'importance': 0.9},
        {'id': 'space_002', 'content': 'Perseverance rover found organic molecules on Mars.', 'topics': ['space', 'discovery'], 'importance': 0.9},
        {'id': 'space_003', 'content': 'SpaceX achieved first civilian spacewalk in 2024.', 'topics': ['space', 'commercial'], 'importance': 0.8},
        {'id': 'space_004', 'content': 'Europa Clipper mission will search for life on Jupiter\'s moon.', 'topics': ['space', 'discovery'], 'importance': 0.8},
        {'id': 'space_005', 'content': 'Artemis program plans lunar base by 2030.', 'topics': ['space', 'exploration'], 'importance': 0.8},
    ],

    'test_queries': [
        {
            'query': 'What are major breakthroughs in computer vision?',
            'relevant_ids': ['ml_001', 'ml_002'],  # AlexNet, ResNet
            'topic': 'ml_vision'
        },
        {
            'query': 'Tell me about transformer models in NLP.',
            'relevant_ids': ['ml_003', 'ml_004'],  # BERT, GPT-3
            'topic': 'ml_nlp'
        },
        {
            'query': 'How does the hippocampus work in memory?',
            'relevant_ids': ['neuro_001', 'neuro_003', 'neuro_004'],  # Hippocampus, consolidation, LTP
            'topic': 'neuro_memory'
        },
        {
            'query': 'What are the cognitive functions of the brain?',
            'relevant_ids': ['neuro_002', 'neuro_005'],  # PFC, working memory
            'topic': 'neuro_cognition'
        },
        {
            'query': 'What are recent climate change statistics?',
            'relevant_ids': ['climate_001', 'climate_002'],  # CO2, Arctic ice
            'topic': 'climate_data'
        },
        {
            'query': 'How is technology addressing climate change?',
            'relevant_ids': ['climate_003', 'climate_005'],  # Renewables, EVs
            'topic': 'climate_tech'
        },
        {
            'query': 'What discoveries have been made on Mars?',
            'relevant_ids': ['space_002'],  # Perseverance organics
            'topic': 'space_mars'
        },
        {
            'query': 'What are upcoming space missions?',
            'relevant_ids': ['space_004', 'space_005'],  # Europa Clipper, Artemis
            'topic': 'space_future'
        },
        {
            'query': 'Tell me about reinforcement learning achievements.',
            'relevant_ids': ['ml_005'],  # AlphaGo
            'topic': 'ml_rl'
        },
        {
            'query': 'What space technology was launched recently?',
            'relevant_ids': ['space_001', 'space_003'],  # JWST, SpaceX
            'topic': 'space_recent_tech'
        },
    ]
}


def calculate_metrics(retrieved_ids: List[str], relevant_ids: Set[str]) -> Dict[str, float]:
    """
    Calculate Precision, Recall, F1-Score for a single query
    """
    retrieved_set = set(retrieved_ids)
    relevant_set = set(relevant_ids)

    true_positives = len(retrieved_set & relevant_set)
    false_positives = len(retrieved_set - relevant_set)
    false_negatives = len(relevant_set - retrieved_set)

    precision = true_positives / len(retrieved_set) if len(retrieved_set) > 0 else 0.0
    recall = true_positives / len(relevant_set) if len(relevant_set) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'true_positives': true_positives,
        'false_positives': false_positives,
        'false_negatives': false_negatives
    }


def calculate_mrr(retrieved_ids: List[str], relevant_ids: Set[str]) -> float:
    """
    Calculate Mean Reciprocal Rank (MRR)
    Returns 1/rank of first relevant result, or 0 if none found
    """
    for rank, mem_id in enumerate(retrieved_ids, 1):
        if mem_id in relevant_ids:
            return 1.0 / rank
    return 0.0


async def ingest_and_consolidate(coordinator, dataset):
    """
    Ingest ground truth memories and trigger consolidation
    """
    print("\n[1/2] Ingesting ground truth dataset...")

    # Create memory_id → content mapping for later matching
    memory_map = {}

    for mem_data in dataset['memories']:
        content = mem_data['content']
        mem_id = mem_data['id']

        await coordinator.process_input(content)

        # Store mapping (we'll need to match retrieved memories back to IDs)
        memory_map[content] = mem_id

        print(f"  [{mem_id}] {content[:60]}...")

    print(f"\n  ✓ Ingested {len(dataset['memories'])} memories")

    # Trigger consolidation
    print("\n[2/2] Triggering consolidation...")

    # Boost importance
    for mem in coordinator.hippocampus.memories:
        mem.importance = 0.9
        mem.access_count = 0

    result = await coordinator.hippocampus.consolidate_memories()
    print(f"  ✓ Consolidated {result.get('consolidated', 0)} patterns")

    # Verify long-term storage
    temporal_count = len(coordinator.temporal_lobe.memories) if hasattr(coordinator.temporal_lobe, 'memories') else 0
    memory_system_count = 0
    if hasattr(coordinator, 'memory_system') and hasattr(coordinator.memory_system, 'db_manager'):
        memory_system_count = len(coordinator.memory_system.db_manager.get_all_memories())

    print(f"  → TemporalLobe: {temporal_count} memories")
    print(f"  → MemorySystem: {memory_system_count} memories")

    return memory_map


def match_retrieved_to_ids(retrieved_memories: List[Dict], memory_map: Dict[str, str]) -> List[str]:
    """
    Match retrieved memories back to their ground truth IDs
    """
    retrieved_ids = []
    for mem in retrieved_memories:
        content = mem.get('content', '')
        # Try exact match first
        if content in memory_map:
            retrieved_ids.append(memory_map[content])
        else:
            # Try partial match (for consolidated memories)
            for original_content, mem_id in memory_map.items():
                if original_content in content or content in original_content:
                    retrieved_ids.append(mem_id)
                    break

    return retrieved_ids


async def evaluate_retrieval_strategy(coordinator, dataset, memory_map, strategy: str, k: int = 10):
    """
    Evaluate retrieval quality for a given strategy
    """
    print(f"\n{'=' * 80}")
    print(f"Evaluating Strategy: {strategy.upper()}")
    print(f"{'=' * 80}")

    results = []
    total_precision = 0
    total_recall = 0
    total_f1 = 0
    total_mrr = 0

    for i, test_case in enumerate(dataset['test_queries'], 1):
        query = test_case['query']
        relevant_ids = set(test_case['relevant_ids'])

        print(f"\nQuery {i}/{len(dataset['test_queries'])}: {query}")
        print(f"  Expected relevant: {list(relevant_ids)}")

        # Retrieve
        retrieved = await coordinator.smart_retrieve(query, k=k, strategy=strategy)

        # Match to IDs
        retrieved_ids = match_retrieved_to_ids(retrieved, memory_map)

        # Calculate metrics
        metrics = calculate_metrics(retrieved_ids, relevant_ids)
        mrr = calculate_mrr(retrieved_ids, relevant_ids)

        print(f"  Retrieved {len(retrieved)} memories")
        print(f"  Matched IDs: {retrieved_ids[:5]}...")
        print(f"  Metrics: P={metrics['precision']:.3f}, R={metrics['recall']:.3f}, F1={metrics['f1']:.3f}, MRR={mrr:.3f}")

        results.append({
            'query': query,
            'topic': test_case['topic'],
            'retrieved_count': len(retrieved),
            'retrieved_ids': retrieved_ids,
            'relevant_ids': list(relevant_ids),
            'metrics': metrics,
            'mrr': mrr
        })

        total_precision += metrics['precision']
        total_recall += metrics['recall']
        total_f1 += metrics['f1']
        total_mrr += mrr

    # Calculate averages
    num_queries = len(dataset['test_queries'])
    avg_metrics = {
        'strategy': strategy,
        'k': k,
        'num_queries': num_queries,
        'avg_precision': total_precision / num_queries,
        'avg_recall': total_recall / num_queries,
        'avg_f1': total_f1 / num_queries,
        'avg_mrr': total_mrr / num_queries,
        'detailed_results': results
    }

    print(f"\n{'=' * 80}")
    print(f"Strategy: {strategy.upper()} - Summary")
    print(f"{'=' * 80}")
    print(f"Average Precision: {avg_metrics['avg_precision']:.3f}")
    print(f"Average Recall:    {avg_metrics['avg_recall']:.3f}")
    print(f"Average F1-Score:  {avg_metrics['avg_f1']:.3f}")
    print(f"Average MRR:       {avg_metrics['avg_mrr']:.3f}")

    return avg_metrics


async def main():
    """
    Main evaluation orchestrator
    """
    print("=" * 80)
    print("Long-Term Retrieval Quality Evaluation")
    print("=" * 80)
    print("Objective: Quantify long-term vs short-term retrieval effectiveness")
    print("Metrics: Precision, Recall, F1-Score, MRR")
    print("=" * 80)

    # Initialize coordinator
    coordinator = BrainInspiredCoordinator()

    # Ingest and consolidate
    memory_map = await ingest_and_consolidate(coordinator, GROUND_TRUTH_DATASET)

    # Evaluate different strategies
    strategies_to_test = [
        ('episodic', 'Short-term only (Hippocampus)'),
        ('hybrid', 'Multi-source (Hippocampus + TemporalLobe)'),
        ('semantic', 'Long-term only (TemporalLobe)')
    ]

    evaluation_results = []

    for strategy, description in strategies_to_test:
        print(f"\n\n{'=' * 80}")
        print(f"TESTING: {description}")
        print(f"{'=' * 80}")

        result = await evaluate_retrieval_strategy(
            coordinator,
            GROUND_TRUTH_DATASET,
            memory_map,
            strategy=strategy,
            k=10
        )

        evaluation_results.append(result)

    # Comparative analysis
    print("\n\n" + "=" * 80)
    print("COMPARATIVE ANALYSIS")
    print("=" * 80)

    print(f"\n{'Strategy':<20} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'MRR':<12}")
    print("-" * 80)

    for result in evaluation_results:
        strategy_name = result['strategy'].upper()
        print(f"{strategy_name:<20} "
              f"{result['avg_precision']:<12.3f} "
              f"{result['avg_recall']:<12.3f} "
              f"{result['avg_f1']:<12.3f} "
              f"{result['avg_mrr']:<12.3f}")

    # Determine best strategy
    best_f1 = max(evaluation_results, key=lambda x: x['avg_f1'])
    print(f"\n✅ Best overall strategy (by F1-Score): {best_f1['strategy'].upper()}")
    print(f"   F1-Score: {best_f1['avg_f1']:.3f}")

    # Long-term vs Short-term comparison
    episodic_result = next(r for r in evaluation_results if r['strategy'] == 'episodic')
    hybrid_result = next(r for r in evaluation_results if r['strategy'] == 'hybrid')

    improvement_f1 = ((hybrid_result['avg_f1'] - episodic_result['avg_f1']) / episodic_result['avg_f1'] * 100) if episodic_result['avg_f1'] > 0 else 0
    improvement_recall = ((hybrid_result['avg_recall'] - episodic_result['avg_recall']) / episodic_result['avg_recall'] * 100) if episodic_result['avg_recall'] > 0 else 0

    print(f"\n📊 Long-term storage effectiveness:")
    print(f"   Hybrid vs Episodic F1 improvement: {improvement_f1:+.1f}%")
    print(f"   Hybrid vs Episodic Recall improvement: {improvement_recall:+.1f}%")

    if improvement_f1 > 10:
        print(f"\n✅ CONCLUSION: Long-term storage significantly improves retrieval quality (>{improvement_f1:.0f}% improvement)")
    elif improvement_f1 > 0:
        print(f"\n⚠️  CONCLUSION: Long-term storage provides moderate improvement ({improvement_f1:.1f}%)")
    else:
        print(f"\n❌ CONCLUSION: Long-term storage not outperforming short-term (needs optimization)")

    # Save results
    output_file = Path("metrics/cross_session/long_term_retrieval_quality.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'dataset_size': len(GROUND_TRUTH_DATASET['memories']),
            'test_queries': len(GROUND_TRUTH_DATASET['test_queries']),
            'evaluation_results': evaluation_results,
            'comparative_analysis': {
                'best_strategy': best_f1['strategy'],
                'best_f1_score': best_f1['avg_f1'],
                'improvement_vs_episodic': {
                    'f1_percentage': improvement_f1,
                    'recall_percentage': improvement_recall
                }
            }
        }, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Results saved to {output_file}")

    await coordinator.stop_system()

    return improvement_f1 > 0  # Success if long-term improves over short-term


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
