"""
BMAM Evaluation Module

This module contains evaluation code adapted from MemOS to ensure metric alignment
for fair comparison on the Locomo benchmark.

Metrics calculated:
- LLMJudge Score (GPT-4 evaluator)
- Lexical: F1, ROUGE-1/2/L, BLEU-1/2/3/4, METEOR
- Semantic: BERT-F1, Cosine Similarity
"""
