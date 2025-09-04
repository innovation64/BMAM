#!/usr/bin/env python3
"""
Paper-Specific Evaluator for MA-CMM Framework
Implements exact evaluation metrics from the original papers:

1. "Personalized Large Language Model Assistant with Evolving Conditional Memory"
2. "MemoryOS: Towards General Computer Operating Systems for LLMs"

This evaluator ensures our results are directly comparable to the original papers.
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.api_client import APIClient
import nltk
from rouge_score import rouge_scorer
import random

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')


class PersonalizedLLMEvaluator:
    """
    Evaluator for "Personalized Large Language Model Assistant with Evolving Conditional Memory" paper
    
    Implements:
    - Rouge-1 and Rouge-2 scores
    - GPT-score (0-2 rating)
    - GSB testing (Good/Same/Bad comparison)
    - Multiple choice evaluation
    """
    
    def __init__(self):
        self.api_client = APIClient()
        self.rouge_scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
        self.logger = logging.getLogger(f"{__name__}.PersonalizedLLM")
    
    async def evaluate_response(self, 
                              generated_response: str, 
                              reference_response: str, 
                              query: str,
                              task_type: str = "continuing_dialogue") -> Dict[str, float]:
        """
        Evaluate response using paper-specific metrics
        
        Args:
            generated_response: Model's generated response
            reference_response: Ground truth reference
            query: Original query
            task_type: Type of task (continuing_dialogue, learning_knowledge, learning_feedback)
        """
        
        results = {}
        
        # 1. N-gram similarity metrics (Rouge-1, Rouge-2)
        rouge_scores = self._calculate_rouge_scores(generated_response, reference_response)
        results.update(rouge_scores)
        
        # 2. GPT-4 evaluation metrics
        if task_type == "learning_knowledge":
            # Use GPT-score for tasks with clear reference answers
            gpt_score = await self._calculate_gpt_score(generated_response, reference_response, query)
            results["gpt_score"] = gpt_score
        
        elif task_type in ["learning_feedback", "continuing_dialogue"]:
            # Use GSB testing for complex evaluation scenarios
            gsb_score = await self._calculate_gsb_score(generated_response, reference_response, query, task_type)
            results["gsb_score"] = gsb_score
        
        return results
    
    def _calculate_rouge_scores(self, generated: str, reference: str) -> Dict[str, float]:
        """Calculate Rouge-1 and Rouge-2 scores"""
        try:
            scores = self.rouge_scorer.score(reference, generated)
            
            return {
                "rouge1_f": scores['rouge1'].fmeasure,
                "rouge1_p": scores['rouge1'].precision,
                "rouge1_r": scores['rouge1'].recall,
                "rouge2_f": scores['rouge2'].fmeasure,
                "rouge2_p": scores['rouge2'].precision,
                "rouge2_r": scores['rouge2'].recall,
                "rougeL_f": scores['rougeL'].fmeasure,
            }
        except Exception as e:
            self.logger.error(f"Error calculating ROUGE scores: {e}")
            return {
                "rouge1_f": 0.0, "rouge1_p": 0.0, "rouge1_r": 0.0,
                "rouge2_f": 0.0, "rouge2_p": 0.0, "rouge2_r": 0.0,
                "rougeL_f": 0.0
            }
    
    async def _calculate_gpt_score(self, generated: str, reference: str, query: str) -> float:
        """
        Calculate GPT-score (0-2 rating) for tasks with clear reference answers
        
        0: Response is completely wrong
        1: Response contains partial information from reference
        2: Response contains all information from reference
        """
        
        evaluation_prompt = f"""
You are evaluating the quality of an AI assistant's response. Please rate the response on a scale of 0-2:

0: The response is completely wrong or contains no information from the reference answer
1: The response contains partial information from the reference answer
2: The response contains all the important information from the reference answer

Original Query: {query}

Reference Answer: {reference}

AI Response: {generated}

Please provide only a single number (0, 1, or 2) as your rating.
"""
        
        try:
            rating_text = await self.api_client.get_completion(
                messages=[{"role": "user", "content": evaluation_prompt}],
                model="gpt-4",
                max_tokens=10,
                temperature=0.0
            )
            
            # Extract numeric rating
            rating_match = re.search(r'\b([0-2])\b', rating_text.strip())
            if rating_match:
                return float(rating_match.group(1))
            else:
                self.logger.warning(f"Could not parse GPT rating: {rating_text}")
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Error calculating GPT score: {e}")
            return 0.0
    
    async def _calculate_gsb_score(self, generated: str, reference: str, query: str, task_type: str) -> float:
        """
        Calculate GSB (Good/Same/Bad) score
        
        Returns:
            1.0 if generated is better than reference
            0.5 if generated is same as reference  
            0.0 if generated is worse than reference
        """
        
        # To avoid position bias, we do the comparison twice with swapped positions
        score1 = await self._single_gsb_comparison(generated, reference, query, task_type, first_position=True)
        score2 = await self._single_gsb_comparison(generated, reference, query, task_type, first_position=False)
        
        # Average the two comparisons
        return (score1 + score2) / 2.0
    
    async def _single_gsb_comparison(self, generated: str, reference: str, query: str, task_type: str, first_position: bool) -> float:
        """Perform a single GSB comparison"""
        
        if task_type == "learning_feedback":
            context_description = "learning from human feedback and applying user preferences"
        elif task_type == "continuing_dialogue":
            context_description = "continuing previous conversations with relevant context"
        else:
            context_description = "responding appropriately to the query"
        
        if first_position:
            candidate_a, candidate_b = generated, reference
            a_label, b_label = "Generated Response", "Reference Response"
        else:
            candidate_a, candidate_b = reference, generated
            a_label, b_label = "Reference Response", "Generated Response"
        
        comparison_prompt = f"""
You are evaluating two AI assistant responses for their quality in {context_description}.

Original Query: {query}

Response A ({a_label}): {candidate_a}

Response B ({b_label}): {candidate_b}

Which response is better? Consider:
- Relevance to the query
- Helpfulness and informativeness
- Appropriateness for the context
- Quality of personalization (if applicable)

Please respond with exactly one of: "A", "B", or "Same"
"""
        
        try:
            comparison_result = await self.api_client.get_completion(
                messages=[{"role": "user", "content": comparison_prompt}],
                model="gpt-4",
                max_tokens=10,
                temperature=0.0
            )
            
            result = comparison_result.strip().upper()
            
            if first_position:
                # generated is candidate A
                if result == "A":
                    return 1.0  # Generated is better
                elif result == "B":
                    return 0.0  # Reference is better
                else:  # "SAME"
                    return 0.5
            else:
                # generated is candidate B
                if result == "B":
                    return 1.0  # Generated is better
                elif result == "A":
                    return 0.0  # Reference is better
                else:  # "SAME"
                    return 0.5
                    
        except Exception as e:
            self.logger.error(f"Error in GSB comparison: {e}")
            return 0.5  # Default to "same" on error


class MemoryOSEvaluator:
    """
    Evaluator for "MemoryOS: Towards General Computer Operating Systems for LLMs" paper
    
    Implements:
    - Memory Retrieval Accuracy (binary 0/1)
    - Response Correctness (0, 0.5, 1)
    - Contextual Coherence (0, 0.5, 1)
    - F1 score and BLEU-1 for LoCoMo benchmark
    - Efficiency metrics (tokens consumed, LLM calls)
    """
    
    def __init__(self):
        self.api_client = APIClient()
        self.logger = logging.getLogger(f"{__name__}.MemoryOS")
    
    async def evaluate_response(self, 
                              generated_response: str, 
                              reference_response: str, 
                              query: str,
                              retrieved_memories: List[Dict] = None,
                              memory_operations: int = 0,
                              llm_calls: int = 1) -> Dict[str, float]:
        """
        Evaluate response using MemoryOS paper metrics
        
        Args:
            generated_response: Model's generated response
            reference_response: Ground truth reference
            query: Original query
            retrieved_memories: List of retrieved memory items
            memory_operations: Number of memory operations performed
            llm_calls: Number of LLM calls made
        """
        
        results = {}
        
        # 1. Memory Retrieval Accuracy (binary)
        memory_accuracy = await self._calculate_memory_retrieval_accuracy(
            query, retrieved_memories or [], reference_response
        )
        results["memory_retrieval_accuracy"] = memory_accuracy
        
        # 2. Response Correctness (0, 0.5, 1)
        response_correctness = await self._calculate_response_correctness(
            generated_response, reference_response, query
        )
        results["response_correctness"] = response_correctness
        
        # 3. Contextual Coherence (0, 0.5, 1)
        contextual_coherence = await self._calculate_contextual_coherence(
            generated_response, query, retrieved_memories or []
        )
        results["contextual_coherence"] = contextual_coherence
        
        # 4. F1 score for LoCoMo benchmark
        f1_score = self._calculate_f1_score(generated_response, reference_response)
        results["f1_score"] = f1_score
        
        # 5. BLEU-1 score for LoCoMo benchmark
        bleu1_score = self._calculate_bleu1_score(generated_response, reference_response)
        results["bleu1_score"] = bleu1_score
        
        # 6. Efficiency metrics
        results["memory_operations"] = memory_operations
        results["llm_calls"] = llm_calls
        
        return results
    
    async def _calculate_memory_retrieval_accuracy(self, query: str, retrieved_memories: List[Dict], reference: str) -> float:
        """
        Calculate Memory Retrieval Accuracy (binary 0/1)
        
        Evaluates whether the retrieved memories are relevant to answering the query
        """
        
        if not retrieved_memories:
            return 0.0
        
        # Format retrieved memories for evaluation
        memory_text = "\n".join([
            f"Memory {i+1}: {mem.get('content', str(mem))}" 
            for i, mem in enumerate(retrieved_memories)
        ])
        
        evaluation_prompt = f"""
You are evaluating whether retrieved memories are relevant for answering a query.

Query: {query}

Retrieved Memories:
{memory_text}

Expected Answer Context: {reference}

Are the retrieved memories relevant and helpful for answering the query? 
Consider if the memories contain information that would help generate an appropriate response.

Respond with exactly "1" if the memories are relevant, or "0" if they are not relevant.
"""
        
        try:
            result = await self.api_client.get_completion(
                messages=[{"role": "user", "content": evaluation_prompt}],
                model="gpt-4",
                max_tokens=10,
                temperature=0.0
            )
            
            # Extract binary result
            if "1" in result.strip():
                return 1.0
            else:
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Error calculating memory retrieval accuracy: {e}")
            return 0.0
    
    async def _calculate_response_correctness(self, generated: str, reference: str, query: str) -> float:
        """
        Calculate Response Correctness using three-point scale (0, 0.5, 1)
        
        0: Completely incorrect
        0.5: Partially correct
        1: Completely correct
        """
        
        evaluation_prompt = f"""
You are evaluating the correctness of an AI response compared to a reference answer.

Query: {query}

Reference Answer: {reference}

AI Response: {generated}

Rate the correctness of the AI response on a three-point scale:
0: Completely incorrect - the response is wrong or completely unrelated
0.5: Partially correct - the response contains some correct information but is incomplete or has errors
1: Completely correct - the response is accurate and complete

Respond with exactly one number: 0, 0.5, or 1
"""
        
        try:
            result = await self.api_client.get_completion(
                messages=[{"role": "user", "content": evaluation_prompt}],
                model="gpt-4",
                max_tokens=10,
                temperature=0.0
            )
            
            # Extract numeric result
            result_text = result.strip()
            if "0.5" in result_text:
                return 0.5
            elif "1" in result_text:
                return 1.0
            else:
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Error calculating response correctness: {e}")
            return 0.0
    
    async def _calculate_contextual_coherence(self, generated: str, query: str, retrieved_memories: List[Dict]) -> float:
        """
        Calculate Contextual Coherence using three-point scale (0, 0.5, 1)
        
        Evaluates how well the response incorporates and is coherent with the retrieved context
        """
        
        memory_context = "\n".join([
            f"- {mem.get('content', str(mem))}" 
            for mem in retrieved_memories
        ]) if retrieved_memories else "No memories retrieved"
        
        evaluation_prompt = f"""
You are evaluating the contextual coherence of an AI response.

Query: {query}

Retrieved Context:
{memory_context}

AI Response: {generated}

Rate how well the response is coherent with the retrieved context:
0: Not coherent - the response ignores or contradicts the context
0.5: Partially coherent - the response somewhat uses the context but has inconsistencies
1: Fully coherent - the response effectively incorporates and is consistent with the context

Respond with exactly one number: 0, 0.5, or 1
"""
        
        try:
            result = await self.api_client.get_completion(
                messages=[{"role": "user", "content": evaluation_prompt}],
                model="gpt-4",
                max_tokens=10,
                temperature=0.0
            )
            
            # Extract numeric result
            result_text = result.strip()
            if "0.5" in result_text:
                return 0.5
            elif "1" in result_text:
                return 1.0
            else:
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Error calculating contextual coherence: {e}")
            return 0.0
    
    def _calculate_f1_score(self, generated: str, reference: str) -> float:
        """Calculate F1 score for LoCoMo benchmark"""
        try:
            # Tokenize and convert to sets
            generated_tokens = set(nltk.word_tokenize(generated.lower()))
            reference_tokens = set(nltk.word_tokenize(reference.lower()))
            
            # Calculate precision, recall, and F1
            if not generated_tokens:
                return 0.0
            
            intersection = generated_tokens & reference_tokens
            precision = len(intersection) / len(generated_tokens)
            recall = len(intersection) / len(reference_tokens) if reference_tokens else 0.0
            
            if precision + recall == 0:
                return 0.0
            
            f1 = 2 * (precision * recall) / (precision + recall)
            return f1
            
        except Exception as e:
            self.logger.error(f"Error calculating F1 score: {e}")
            return 0.0
    
    def _calculate_bleu1_score(self, generated: str, reference: str) -> float:
        """Calculate BLEU-1 score for LoCoMo benchmark"""
        try:
            # Simple BLEU-1 implementation
            generated_tokens = nltk.word_tokenize(generated.lower())
            reference_tokens = nltk.word_tokenize(reference.lower())
            
            if not generated_tokens:
                return 0.0
            
            # Count 1-gram matches
            generated_1grams = generated_tokens
            reference_1grams = reference_tokens
            
            matches = 0
            for gram in generated_1grams:
                if gram in reference_1grams:
                    matches += 1
                    reference_1grams.remove(gram)  # Remove to avoid double counting
            
            # BLEU-1 precision
            precision = matches / len(generated_1grams)
            
            # Brevity penalty
            bp = min(1, len(generated_tokens) / max(len(reference_tokens), 1))
            
            bleu1 = bp * precision
            return bleu1
            
        except Exception as e:
            self.logger.error(f"Error calculating BLEU-1 score: {e}")
            return 0.0


class PaperSpecificEvaluator:
    """
    Unified evaluator that combines both paper-specific evaluation approaches
    """
    
    def __init__(self):
        self.personalized_llm_evaluator = PersonalizedLLMEvaluator()
        self.memoryos_evaluator = MemoryOSEvaluator()
        self.logger = logging.getLogger(__name__)
    
    async def evaluate_for_dataset(self, 
                                 dataset_name: str,
                                 generated_response: str, 
                                 reference_response: str, 
                                 query: str,
                                 task_type: str = None,
                                 retrieved_memories: List[Dict] = None,
                                 memory_operations: int = 0,
                                 llm_calls: int = 1) -> Dict[str, float]:
        """
        Evaluate using appropriate metrics based on dataset
        
        Args:
            dataset_name: Name of the dataset being evaluated
            generated_response: Model's generated response
            reference_response: Ground truth reference
            query: Original query
            task_type: Specific task type within dataset
            retrieved_memories: Retrieved memory items
            memory_operations: Number of memory operations
            llm_calls: Number of LLM calls
        """
        
        results = {}
        
        if dataset_name == "evolving_conditional_memory":
            # Use Personalized LLM evaluation metrics
            if not task_type:
                # Infer task type from context or use default
                task_type = "continuing_dialogue"
            
            personalized_results = await self.personalized_llm_evaluator.evaluate_response(
                generated_response, reference_response, query, task_type
            )
            results.update(personalized_results)
            
        elif dataset_name in ["locomo", "memorybank_siliconfriend"]:
            # Use MemoryOS evaluation metrics
            memoryos_results = await self.memoryos_evaluator.evaluate_response(
                generated_response, reference_response, query, 
                retrieved_memories, memory_operations, llm_calls
            )
            results.update(memoryos_results)
        
        else:
            # Fall back to both evaluation approaches
            self.logger.warning(f"Unknown dataset {dataset_name}, using both evaluation approaches")
            
            personalized_results = await self.personalized_llm_evaluator.evaluate_response(
                generated_response, reference_response, query, "continuing_dialogue"
            )
            memoryos_results = await self.memoryos_evaluator.evaluate_response(
                generated_response, reference_response, query, 
                retrieved_memories, memory_operations, llm_calls
            )
            
            results.update(personalized_results)
            results.update(memoryos_results)
        
        return results
    
    def get_primary_metrics_for_dataset(self, dataset_name: str) -> List[str]:
        """Get the primary metrics that should be reported for each dataset"""
        
        if dataset_name == "evolving_conditional_memory":
            return ["rouge1_f", "rouge2_f", "gpt_score", "gsb_score"]
        
        elif dataset_name == "locomo":
            return ["f1_score", "bleu1_score", "memory_retrieval_accuracy", "response_correctness"]
        
        elif dataset_name == "memorybank_siliconfriend":
            return ["memory_retrieval_accuracy", "response_correctness", "contextual_coherence"]
        
        else:
            return ["rouge1_f", "f1_score", "response_correctness"]
    
    def format_results_for_paper(self, results: Dict[str, float], dataset_name: str) -> Dict[str, Any]:
        """Format results in the style reported in the original papers"""
        
        formatted = {}
        
        if dataset_name == "evolving_conditional_memory":
            # Format like Personalized LLM paper
            formatted["N-gram Similarity"] = {
                "ROUGE-1 F1": results.get("rouge1_f", 0.0),
                "ROUGE-2 F1": results.get("rouge2_f", 0.0),
                "ROUGE-L F1": results.get("rougeL_f", 0.0)
            }
            
            if "gpt_score" in results:
                formatted["GPT-4 Evaluation"] = {
                    "GPT-Score (0-2)": results["gpt_score"]
                }
            
            if "gsb_score" in results:
                formatted["GSB Testing"] = {
                    "Win Rate": results["gsb_score"]
                }
        
        elif dataset_name in ["locomo", "memorybank_siliconfriend"]:
            # Format like MemoryOS paper
            formatted["Memory Performance"] = {
                "Memory Retrieval Acc.": results.get("memory_retrieval_accuracy", 0.0),
                "Response Correctness": results.get("response_correctness", 0.0),
                "Contextual Coherence": results.get("contextual_coherence", 0.0)
            }
            
            if dataset_name == "locomo":
                formatted["LoCoMo Benchmark"] = {
                    "F1 Score": results.get("f1_score", 0.0),
                    "BLEU-1": results.get("bleu1_score", 0.0)
                }
            
            formatted["Efficiency"] = {
                "Memory Operations": results.get("memory_operations", 0),
                "LLM Calls": results.get("llm_calls", 1)
            }
        
        return formatted


# Example usage and testing
async def test_evaluators():
    """Test both evaluators with sample data"""
    
    evaluator = PaperSpecificEvaluator()
    
    # Test data
    test_cases = [
        {
            "dataset": "evolving_conditional_memory",
            "task_type": "learning_knowledge",
            "query": "What is my favorite color?",
            "generated": "Your favorite color is blue.",
            "reference": "Based on our previous conversations, your favorite color is blue."
        },
        {
            "dataset": "locomo", 
            "query": "Tell me about my hobbies",
            "generated": "You enjoy reading and playing guitar.",
            "reference": "You mentioned that you like reading books and playing guitar in your free time.",
            "memories": [{"content": "User likes reading"}, {"content": "User plays guitar"}]
        }
    ]
    
    for test_case in test_cases:
        print(f"\n=== Testing {test_case['dataset']} ===")
        
        results = await evaluator.evaluate_for_dataset(
            dataset_name=test_case["dataset"],
            generated_response=test_case["generated"],
            reference_response=test_case["reference"],
            query=test_case["query"],
            task_type=test_case.get("task_type"),
            retrieved_memories=test_case.get("memories", [])
        )
        
        formatted_results = evaluator.format_results_for_paper(results, test_case["dataset"])
        
        print("Raw Results:", json.dumps(results, indent=2))
        print("Formatted Results:", json.dumps(formatted_results, indent=2))


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_evaluators())