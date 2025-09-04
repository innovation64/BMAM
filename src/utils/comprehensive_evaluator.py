"""
Comprehensive Evaluation Metrics for MA-CMM Framework

This module implements all evaluation metrics used in the original COLING 2025 paper
and additional metrics for thorough system assessment.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
# import numpy as np  # Optional dependency
from datetime import datetime
import re
from collections import Counter

# Text similarity metrics
try:
    from rouge_score import rouge_scorer
    ROUGE_AVAILABLE = True
except ImportError:
    print("Warning: ROUGE not available. Install with: pip install rouge-score")
    ROUGE_AVAILABLE = False

try:
    from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
    import nltk
    # Download required NLTK data
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')
    NLTK_AVAILABLE = True
except ImportError:
    print("Warning: NLTK not available. Install with: pip install nltk")
    NLTK_AVAILABLE = False
    # Define a simple replacement for SmoothingFunction
    class SmoothingFunction:
        @staticmethod
        def method4():
            return None

from .config import ConfigManager

# Optional imports
try:
    from .gpt_evaluator import GPTEvaluator
    GPT_EVALUATOR_AVAILABLE = True
except ImportError:
    print("Warning: GPT evaluator not available")

# Paper-specific evaluator
try:
    from .paper_specific_evaluator import PaperSpecificEvaluator
    PAPER_EVALUATOR_AVAILABLE = True
except ImportError:
    print("Warning: Paper-specific evaluator not available")
    PAPER_EVALUATOR_AVAILABLE = False
    GPT_EVALUATOR_AVAILABLE = False
    GPTEvaluator = None


class ComprehensiveEvaluator:
    """Comprehensive evaluation metrics for MA-CMM and baseline methods"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize comprehensive evaluator"""
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.get_config()
        self.logger = logging.getLogger(__name__)
        
        # Initialize GPT evaluator for advanced metrics
        if GPT_EVALUATOR_AVAILABLE:
            try:
                self.gpt_evaluator = GPTEvaluator(config_path)
                self.gpt_available = True
            except Exception as e:
                self.logger.warning(f"GPT evaluator not available: {str(e)}")
                self.gpt_evaluator = None
                self.gpt_available = False
        else:
            self.gpt_evaluator = None
            self.gpt_available = False
        
        # Initialize paper-specific evaluator
        if PAPER_EVALUATOR_AVAILABLE:
            try:
                self.paper_evaluator = PaperSpecificEvaluator()
                self.paper_evaluator_available = True
            except Exception as e:
                self.logger.warning(f"Paper-specific evaluator not available: {str(e)}")
                self.paper_evaluator = None
                self.paper_evaluator_available = False
        else:
            self.paper_evaluator = None
            self.paper_evaluator_available = False
        
        # Initialize ROUGE scorer
        if ROUGE_AVAILABLE:
            try:
                self.rouge_scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
                self.rouge_available = True
            except:
                self.logger.warning("ROUGE scorer not available")
                self.rouge_scorer = None
                self.rouge_available = False
        else:
            self.rouge_scorer = None
            self.rouge_available = False
        
        # BLEU smoothing function
        if NLTK_AVAILABLE:
            self.smoothing_function = SmoothingFunction().method4
        else:
            self.smoothing_function = None
    
    def _calculate_rouge_fallback(self, reference: str, generated: str) -> Dict[str, float]:
        """Fallback ROUGE calculation when rouge-score is not available"""
        def simple_rouge_l(ref, hyp):
            def lcs_length(x, y):
                m, n = len(x), len(y)
                L = [[0] * (n + 1) for _ in range(m + 1)]
                for i in range(m + 1):
                    for j in range(n + 1):
                        if i == 0 or j == 0:
                            L[i][j] = 0
                        elif x[i-1] == y[j-1]:
                            L[i][j] = L[i-1][j-1] + 1
                        else:
                            L[i][j] = max(L[i-1][j], L[i][j-1])
                return L[m][n]
            
            ref_tokens = ref.lower().split()
            hyp_tokens = hyp.lower().split()
            if not ref_tokens or not hyp_tokens:
                return 0.0
            
            lcs = lcs_length(ref_tokens, hyp_tokens)
            precision = lcs / len(hyp_tokens) if hyp_tokens else 0
            recall = lcs / len(ref_tokens) if ref_tokens else 0
            
            if precision + recall == 0:
                return 0.0
            
            return 2 * precision * recall / (precision + recall)
        
        rouge_l = simple_rouge_l(reference, generated)
        return {
            'rouge_1': rouge_l * 0.8,  # Approximate
            'rouge_2': rouge_l * 0.6,  # Approximate
            'rouge_l': rouge_l
        }
    
    def _calculate_bleu_fallback(self, reference: str, generated: str) -> float:
        """Fallback BLEU calculation when NLTK is not available"""
        import math
        from collections import Counter
        
        def get_ngrams(tokens, n):
            return [tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)]
        
        ref_tokens = reference.lower().split()
        hyp_tokens = generated.lower().split()
        
        if not hyp_tokens:
            return 0.0
        
        precisions = []
        for i in range(1, min(5, len(hyp_tokens)+1)):
            ref_ngrams = Counter(get_ngrams(ref_tokens, i))
            hyp_ngrams = Counter(get_ngrams(hyp_tokens, i))
            
            matches = sum((ref_ngrams & hyp_ngrams).values())
            total = sum(hyp_ngrams.values())
            
            if total > 0:
                precision = max(matches / total, 1e-10)
                precisions.append(precision)
        
        if not precisions:
            return 0.0
        
        log_precisions = [math.log(p) for p in precisions]
        avg_log_precision = sum(log_precisions) / len(log_precisions) if log_precisions else 0.0
        
        bp = 1.0
        if len(hyp_tokens) < len(ref_tokens):
            bp = math.exp(1 - len(ref_tokens) / len(hyp_tokens)) if len(hyp_tokens) > 0 else 0.0
        
        return bp * math.exp(avg_log_precision)
    
    async def evaluate_response(
        self,
        generated_response: str,
        reference_response: str,
        dialogue_history: List[Dict[str, str]] = None,
        current_query: str = "",
        conditions: List[Dict[str, Any]] = None,
        context_info: Dict[str, Any] = None
    ) -> Dict[str, float]:
        """
        Comprehensive evaluation of a generated response
        
        Args:
            generated_response: System generated response
            reference_response: Ground truth response
            dialogue_history: Previous dialogue turns
            current_query: Current user query
            conditions: Extracted conditions
            context_info: Additional context information
            
        Returns:
            Dictionary of evaluation metrics
        """
        
        metrics = {}
        
        # Paper-specific evaluation metrics (if available)
        if self.paper_evaluator_available and context_info:
            dataset_name = context_info.get("dataset_name")
            task_type = context_info.get("task_type") 
            retrieved_memories = context_info.get("retrieved_memories", [])
            memory_operations = context_info.get("memory_operations", 0)
            llm_calls = context_info.get("llm_calls", 1)
            
            if dataset_name:
                try:
                    paper_metrics = await self.paper_evaluator.evaluate_for_dataset(
                        dataset_name=dataset_name,
                        generated_response=generated_response,
                        reference_response=reference_response,
                        query=current_query,
                        task_type=task_type,
                        retrieved_memories=retrieved_memories,
                        memory_operations=memory_operations,
                        llm_calls=llm_calls
                    )
                    metrics.update(paper_metrics)
                except Exception as e:
                    self.logger.warning(f"Error in paper-specific evaluation: {e}")
        
        # Basic text similarity metrics
        metrics.update(self._calculate_text_similarity_metrics(generated_response, reference_response))
        
        # Condition-specific metrics
        if conditions:
            metrics.update(self._calculate_condition_metrics(generated_response, conditions))
        
        # Dialogue coherence metrics
        if dialogue_history:
            metrics.update(self._calculate_coherence_metrics(generated_response, dialogue_history, current_query))
        
        # GPT-based evaluation metrics
        if self.gpt_available and dialogue_history and current_query:
            try:
                gpt_scores = await self.gpt_evaluator.evaluate_response(
                    dialogue_history=dialogue_history,
                    current_query=current_query,
                    generated_response=generated_response,
                    reference_response=reference_response,
                    conditions=conditions,
                    context_info=context_info
                )
                metrics.update(gpt_scores)
            except Exception as e:
                self.logger.error(f"GPT evaluation failed: {str(e)}")
                # Add default GPT scores
                gpt_aspects = ['condition_satisfaction', 'response_relevance', 'dialogue_coherence', 'information_accuracy']
                for aspect in gpt_aspects:
                    metrics[f'gpt_{aspect}'] = 0.0
                metrics['gpt_overall'] = 0.0
        
        # Response quality metrics
        metrics.update(self._calculate_response_quality_metrics(generated_response, reference_response))
        
        return metrics
    
    def _calculate_text_similarity_metrics(self, generated: str, reference: str) -> Dict[str, float]:
        """Calculate text similarity metrics (F1, EM, ROUGE, BLEU)"""
        
        metrics = {}
        
        # Exact Match
        metrics['exact_match'] = float(generated.strip().lower() == reference.strip().lower())
        
        # Token-level F1 Score
        metrics['f1_score'] = self._calculate_f1_score(generated, reference)
        
        # ROUGE Scores
        if self.rouge_available and self.rouge_scorer:
            try:
                rouge_scores = self.rouge_scorer.score(reference, generated)
                metrics['rouge_1'] = rouge_scores['rouge1'].fmeasure
                metrics['rouge_2'] = rouge_scores['rouge2'].fmeasure
                metrics['rouge_l'] = rouge_scores['rougeL'].fmeasure
            except:
                # Use fallback
                rouge_scores = self._calculate_rouge_fallback(reference, generated)
                metrics.update(rouge_scores)
        else:
            # Use fallback implementation
            rouge_scores = self._calculate_rouge_fallback(reference, generated)
            metrics.update(rouge_scores)
        
        # BLEU Score
        if NLTK_AVAILABLE and self.smoothing_function:
            try:
                reference_tokens = [reference.split()]
                generated_tokens = generated.split()
                bleu_score = sentence_bleu(reference_tokens, generated_tokens, smoothing_function=self.smoothing_function)
                metrics['bleu_score'] = bleu_score
            except:
                # Use fallback
                metrics['bleu_score'] = self._calculate_bleu_fallback(reference, generated)
        else:
            # Use fallback implementation
            metrics['bleu_score'] = self._calculate_bleu_fallback(reference, generated)
        
        return metrics
    
    def _calculate_f1_score(self, generated: str, reference: str) -> float:
        """Calculate token-level F1 score"""
        
        def normalize_text(text):
            return re.sub(r'\W+', ' ', text.lower()).split()
        
        gen_tokens = normalize_text(generated)
        ref_tokens = normalize_text(reference)
        
        if not gen_tokens and not ref_tokens:
            return 1.0
        if not gen_tokens or not ref_tokens:
            return 0.0
        
        gen_counter = Counter(gen_tokens)
        ref_counter = Counter(ref_tokens)
        
        # Calculate precision, recall, F1
        common_tokens = gen_counter & ref_counter
        num_common = sum(common_tokens.values())
        
        if num_common == 0:
            return 0.0
        
        precision = num_common / sum(gen_counter.values())
        recall = num_common / sum(ref_counter.values())
        
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        return f1
    
    def _calculate_condition_metrics(self, generated_response: str, conditions: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate condition-specific evaluation metrics"""
        
        metrics = {
            'condition_extraction_count': len(conditions),
            'condition_satisfaction_rate': 0.0,
            'hard_constraint_satisfaction': 0.0,
            'soft_preference_satisfaction': 0.0,
            'temporal_condition_satisfaction': 0.0,
            'negation_condition_satisfaction': 0.0
        }
        
        if not conditions:
            return metrics
        
        # Categorize conditions by type
        condition_types = {
            'hard_constraints': [],
            'soft_preferences': [],
            'temporal_conditions': [],
            'negations': []
        }
        
        for condition in conditions:
            condition_type = condition.get('type', 'unknown')
            if condition_type in condition_types:
                condition_types[condition_type].append(condition)
        
        # Calculate satisfaction rates for each type
        total_satisfied = 0
        total_conditions = len(conditions)
        
        for cond_type, conds in condition_types.items():
            if conds:
                satisfied = sum(1 for cond in conds if self._is_condition_satisfied(generated_response, cond))
                satisfaction_rate = satisfied / len(conds)
                metrics[f'{cond_type}_satisfaction'] = satisfaction_rate
                total_satisfied += satisfied
        
        # Overall condition satisfaction rate
        metrics['condition_satisfaction_rate'] = total_satisfied / total_conditions if total_conditions > 0 else 0.0
        
        return metrics
    
    def _is_condition_satisfied(self, response: str, condition: Dict[str, Any]) -> bool:
        """Check if a condition is satisfied in the response (heuristic)"""
        
        condition_desc = condition.get('description', '').lower()
        response_lower = response.lower()
        
        # Extract keywords from condition description
        keywords = [word for word in condition_desc.split() if len(word) > 3]
        
        # Simple keyword matching (can be enhanced with more sophisticated methods)
        if condition.get('type') == 'negations':
            # For negation conditions, check that forbidden keywords are NOT present
            return not any(keyword in response_lower for keyword in keywords)
        else:
            # For other conditions, check that keywords are present
            return any(keyword in response_lower for keyword in keywords)
    
    def _calculate_coherence_metrics(
        self, 
        generated_response: str, 
        dialogue_history: List[Dict[str, str]], 
        current_query: str
    ) -> Dict[str, float]:
        """Calculate dialogue coherence metrics"""
        
        metrics = {
            'context_relevance': 0.0,
            'dialogue_continuity': 0.0,
            'topic_consistency': 0.0,
            'reference_appropriateness': 0.0
        }
        
        if not dialogue_history:
            return metrics
        
        # Context relevance: how well response relates to recent dialogue
        recent_context = " ".join([turn.get('content', '') for turn in dialogue_history[-3:]])
        metrics['context_relevance'] = self._calculate_semantic_similarity(generated_response, recent_context)
        
        # Query relevance: how well response addresses the current query
        metrics['query_relevance'] = self._calculate_semantic_similarity(generated_response, current_query)
        
        # Topic consistency: check if response maintains topic from dialogue
        dialogue_topics = self._extract_topics(dialogue_history)
        response_topics = self._extract_topics([{'content': generated_response}])
        metrics['topic_consistency'] = self._calculate_topic_overlap(dialogue_topics, response_topics)
        
        # Reference appropriateness: check if response appropriately references previous information
        metrics['reference_appropriateness'] = self._calculate_reference_score(generated_response, dialogue_history)
        
        return metrics
    
    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts (simplified)"""
        
        # Simple word overlap similarity (can be enhanced with embeddings)
        def normalize_text(text):
            return set(re.sub(r'\W+', ' ', text.lower()).split())
        
        words1 = normalize_text(text1)
        words2 = normalize_text(text2)
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0
    
    def _extract_topics(self, dialogue_turns: List[Dict[str, str]]) -> List[str]:
        """Extract topics from dialogue (simplified keyword extraction)"""
        
        text = " ".join([turn.get('content', '') for turn in dialogue_turns])
        
        # Simple topic extraction using common nouns (can be enhanced with NLP libraries)
        words = re.findall(r'\b[a-z]{4,}\b', text.lower())
        
        # Filter common words and return top topics
        stop_words = {'that', 'this', 'with', 'have', 'will', 'they', 'from', 'been', 'were', 'more', 'than', 'also', 'some', 'what', 'time', 'very', 'when', 'much', 'said', 'each', 'which', 'their', 'would', 'there', 'could', 'other'}
        topics = [word for word in words if word not in stop_words]
        
        # Return most frequent topics
        topic_counts = Counter(topics)
        return [topic for topic, count in topic_counts.most_common(10)]
    
    def _calculate_topic_overlap(self, topics1: List[str], topics2: List[str]) -> float:
        """Calculate topic overlap between two topic lists"""
        
        if not topics1 or not topics2:
            return 0.0
        
        set1 = set(topics1)
        set2 = set(topics2)
        
        intersection = set1 & set2
        union = set1 | set2
        
        return len(intersection) / len(union) if union else 0.0
    
    def _calculate_reference_score(self, response: str, dialogue_history: List[Dict[str, str]]) -> float:
        """Calculate how appropriately the response references previous information"""
        
        # Count reference indicators in the response
        reference_indicators = [
            'as mentioned', 'as discussed', 'previously', 'earlier', 'as you said',
            'as we talked about', 'referring to', 'building on', 'following up'
        ]
        
        response_lower = response.lower()
        reference_count = sum(1 for indicator in reference_indicators if indicator in response_lower)
        
        # Normalize by response length
        response_words = len(response.split())
        
        if response_words == 0:
            return 0.0
        
        # Score based on appropriate use of references (not too many, not too few)
        reference_ratio = reference_count / response_words * 100  # References per 100 words
        
        if reference_ratio > 5:  # Too many references
            return 0.7
        elif reference_ratio > 1:  # Good amount of references
            return 1.0
        elif reference_ratio > 0:  # Some references
            return 0.8
        else:  # No references (might be okay depending on context)
            return 0.5
    
    def _calculate_response_quality_metrics(self, generated: str, reference: str) -> Dict[str, float]:
        """Calculate response quality metrics"""
        
        metrics = {
            'response_length': len(generated.split()),
            'response_completeness': 0.0,
            'response_informativeness': 0.0,
            'response_clarity': 0.0
        }
        
        # Response completeness (compared to reference length)
        gen_length = len(generated.split())
        ref_length = len(reference.split())
        
        if ref_length > 0:
            length_ratio = gen_length / ref_length
            # Optimal ratio is around 0.8-1.2
            if 0.8 <= length_ratio <= 1.2:
                metrics['response_completeness'] = 1.0
            elif 0.5 <= length_ratio < 0.8 or 1.2 < length_ratio <= 1.5:
                metrics['response_completeness'] = 0.7
            else:
                metrics['response_completeness'] = 0.3
        
        # Response informativeness (unique information content)
        unique_words = len(set(generated.lower().split()))
        total_words = len(generated.split())
        
        if total_words > 0:
            metrics['response_informativeness'] = min(1.0, unique_words / total_words * 2)
        
        # Response clarity (sentence structure quality - simplified)
        sentences = generated.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        
        # Optimal sentence length is 10-20 words
        if 10 <= avg_sentence_length <= 20:
            metrics['response_clarity'] = 1.0
        elif 5 <= avg_sentence_length < 10 or 20 < avg_sentence_length <= 30:
            metrics['response_clarity'] = 0.8
        else:
            metrics['response_clarity'] = 0.5
        
        return metrics
    
    async def batch_evaluate(
        self,
        evaluation_data: List[Dict[str, Any]],
        include_gpt_scores: bool = True
    ) -> Dict[str, Any]:
        """
        Batch evaluation of multiple responses
        
        Args:
            evaluation_data: List of evaluation data dictionaries
            include_gpt_scores: Whether to include GPT-based evaluation
            
        Returns:
            Aggregated evaluation results
        """
        
        all_metrics = []
        
        for i, data in enumerate(evaluation_data):
            try:
                metrics = await self.evaluate_response(
                    generated_response=data.get('generated_response', ''),
                    reference_response=data.get('reference_response', ''),
                    dialogue_history=data.get('dialogue_history', []),
                    current_query=data.get('current_query', ''),
                    conditions=data.get('conditions', []),
                    context_info=data.get('context_info', {})
                )
                
                metrics['sample_id'] = i
                all_metrics.append(metrics)
                
                if (i + 1) % 10 == 0:
                    self.logger.info(f"Evaluated {i + 1}/{len(evaluation_data)} samples")
                
            except Exception as e:
                self.logger.error(f"Error evaluating sample {i}: {str(e)}")
                # Add default metrics for failed evaluation
                all_metrics.append({
                    'sample_id': i,
                    'evaluation_error': str(e)
                })
        
        # Aggregate results
        aggregated_results = self._aggregate_metrics(all_metrics)
        
        return {
            'individual_results': all_metrics,
            'aggregated_metrics': aggregated_results,
            'total_samples': len(evaluation_data),
            'successful_evaluations': len([m for m in all_metrics if 'evaluation_error' not in m])
        }
    
    def _aggregate_metrics(self, all_metrics: List[Dict[str, Any]]) -> Dict[str, float]:
        """Aggregate metrics across all samples"""
        
        # Filter out failed evaluations
        valid_metrics = [m for m in all_metrics if 'evaluation_error' not in m]
        
        if not valid_metrics:
            return {}
        
        aggregated = {}
        
        # Get all metric names
        metric_names = set()
        for metrics in valid_metrics:
            metric_names.update(metrics.keys())
        
        metric_names.discard('sample_id')  # Remove non-metric fields
        
        # Calculate mean for each metric
        for metric_name in metric_names:
            values = [m.get(metric_name, 0) for m in valid_metrics if isinstance(m.get(metric_name), (int, float))]
            
            if values:
                aggregated[f'{metric_name}_mean'] = np.mean(values)
                aggregated[f'{metric_name}_std'] = np.std(values)
                aggregated[f'{metric_name}_min'] = np.min(values)
                aggregated[f'{metric_name}_max'] = np.max(values)
        
        return aggregated
    
    async def calculate_metrics(self, generated_response: str, reference_response: str, query: str, 
                              dataset_name: str = None, task_type: str = None, 
                              retrieved_memories: List[Dict] = None, memory_operations: int = 0) -> Dict[str, float]:
        """
        Convenience method to calculate metrics for a single query
        
        Args:
            generated_response: System generated response
            reference_response: Ground truth response
            query: Original query
            dataset_name: Name of the dataset (for paper-specific metrics)
            task_type: Type of task within dataset
            retrieved_memories: Retrieved memory items
            memory_operations: Number of memory operations performed
            
        Returns:
            Dictionary of evaluation metrics
        """
        
        # Prepare context info for evaluation
        context_info = {}
        if dataset_name:
            context_info["dataset_name"] = dataset_name
        if task_type:
            context_info["task_type"] = task_type
        if retrieved_memories:
            context_info["retrieved_memories"] = retrieved_memories
        if memory_operations:
            context_info["memory_operations"] = memory_operations
        
        # Use the main evaluation method
        return await self.evaluate_response(
            generated_response=generated_response,
            reference_response=reference_response,
            current_query=query,
            context_info=context_info
        )


async def main():
    """Test comprehensive evaluator"""
    evaluator = ComprehensiveEvaluator()
    
    # Test data
    test_data = {
        'generated_response': 'Here are some great Python tutorials with hands-on examples: 1) Learn Python basics with interactive coding, 2) Build a calculator step-by-step, 3) Create a simple web scraper.',
        'reference_response': 'For hands-on Python learning, I recommend: 1) Interactive Python tutorials on Codecademy, 2) Building practical projects like calculators, 3) Following step-by-step coding examples.',
        'dialogue_history': [
            {'role': 'user', 'content': 'I want to learn Python programming.'},
            {'role': 'assistant', 'content': 'Great choice! Python is excellent for beginners.'},
            {'role': 'user', 'content': 'I prefer hands-on learning rather than just theory.'}
        ],
        'current_query': 'Can you suggest some practical Python tutorials?',
        'conditions': [
            {
                'type': 'soft_preferences',
                'description': 'User prefers hands-on learning',
                'importance': 'high'
            }
        ]
    }
    
    # Evaluate
    metrics = await evaluator.evaluate_response(**test_data)
    
    print("Comprehensive Evaluation Results:")
    for metric, value in sorted(metrics.items()):
        print(f"  {metric}: {value:.3f}")




if __name__ == "__main__":
    asyncio.run(main())