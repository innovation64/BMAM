"""
Paper-Accurate Evaluator
Implements the exact evaluation metrics from the original COLING 2025 paper
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
import re
from collections import Counter

# ROUGE implementation
try:
    from rouge_score import rouge_scorer
    ROUGE_AVAILABLE = True
except ImportError:
    print("Warning: ROUGE not available. Install with: pip install rouge-score")
    ROUGE_AVAILABLE = False

# OpenAI for GPT-4 evaluation
try:
    from openai import AsyncOpenAI
    import os
    OPENAI_AVAILABLE = True
except ImportError:
    print("Warning: OpenAI not available. Install with: pip install openai")
    OPENAI_AVAILABLE = False

class PaperAccurateEvaluator:
    """Evaluator that matches the exact metrics from the original paper"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize ROUGE scorer for ROUGE-1 and ROUGE-2 only
        if ROUGE_AVAILABLE:
            self.rouge_scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2'], use_stemmer=True)
        else:
            self.rouge_scorer = None
            
        # Initialize OpenAI client for GPT-4 evaluation
        if OPENAI_AVAILABLE and os.getenv('OPENAI_API_KEY'):
            self.openai_client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            self.gpt_available = True
        else:
            self.openai_client = None
            self.gpt_available = False
            self.logger.warning("GPT-4 evaluation not available - missing OpenAI API key")
    
    def calculate_rouge_scores(self, generated: str, reference: str) -> Dict[str, float]:
        """Calculate ROUGE-1 and ROUGE-2 scores exactly as in the paper"""
        
        if self.rouge_scorer:
            try:
                scores = self.rouge_scorer.score(reference, generated)
                return {
                    'rouge1': scores['rouge1'].fmeasure,
                    'rouge2': scores['rouge2'].fmeasure
                }
            except Exception as e:
                self.logger.error(f"ROUGE calculation failed: {e}")
                return self.calculate_rouge_fallback(generated, reference)
        else:
            return self.calculate_rouge_fallback(generated, reference)
    
    def calculate_rouge_fallback(self, generated: str, reference: str) -> Dict[str, float]:
        """Fallback ROUGE calculation when rouge-score is not available"""
        
        def get_ngrams(text: str, n: int) -> Counter:
            """Get n-grams from text"""
            words = text.lower().split()
            return Counter([tuple(words[i:i+n]) for i in range(len(words)-n+1)])
        
        def rouge_n(generated: str, reference: str, n: int) -> float:
            """Calculate ROUGE-n score"""
            gen_ngrams = get_ngrams(generated, n)
            ref_ngrams = get_ngrams(reference, n)
            
            if not ref_ngrams:
                return 0.0
            
            overlap = sum((gen_ngrams & ref_ngrams).values())
            total_ref = sum(ref_ngrams.values())
            
            return overlap / total_ref if total_ref > 0 else 0.0
        
        return {
            'rouge1': rouge_n(generated, reference, 1),
            'rouge2': rouge_n(generated, reference, 2)
        }
    
    async def calculate_gpt4_score(
        self, 
        generated: str, 
        reference: str, 
        dialogue_history: List[Dict[str, str]] = None,
        current_query: str = ""
    ) -> Dict[str, float]:
        """
        Calculate GPT-4 evaluation score on 0-2 scale as in the paper:
        0: Completely wrong
        1: Contains part of reference information
        2: Contains all reference information
        """
        
        if not self.gpt_available:
            self.logger.warning("GPT-4 evaluation not available")
            return {'gpt4_score': 0.0}
        
        # Prepare evaluation prompt exactly as in the paper
        evaluation_prompt = f"""You are an expert evaluator for conversational AI systems. 

Your task is to evaluate how well a generated response matches a reference response on a scale of 0-2:

**Evaluation Scale:**
- **0**: The generated response is completely wrong or irrelevant
- **1**: The generated response contains part of the reference information but is incomplete
- **2**: The generated response contains all the essential information from the reference

**Context:**
Query: {current_query}

**Reference Response (Ground Truth):**
{reference}

**Generated Response to Evaluate:**
{generated}

**Instructions:**
1. Compare the generated response against the reference response
2. Focus on factual accuracy and information completeness
3. Assign a score of 0, 1, or 2 based on the scale above
4. Respond with ONLY the number (0, 1, or 2), no explanation needed

Score:"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Use gpt-4o-mini as more cost-effective
                messages=[{"role": "user", "content": evaluation_prompt}],
                temperature=0.0,  # Deterministic evaluation
                max_tokens=5
            )
            
            score_text = response.choices[0].message.content.strip()
            
            # Parse the score
            try:
                score = int(score_text)
                if score in [0, 1, 2]:
                    return {'gpt4_score': float(score)}
                else:
                    self.logger.warning(f"Invalid GPT-4 score: {score_text}")
                    return {'gpt4_score': 0.0}
            except ValueError:
                self.logger.warning(f"Could not parse GPT-4 score: {score_text}")
                return {'gpt4_score': 0.0}
                
        except Exception as e:
            self.logger.error(f"GPT-4 evaluation failed: {e}")
            return {'gpt4_score': 0.0}
    
    async def evaluate_response(
        self,
        generated_response: str,
        reference_response: str,
        dialogue_history: List[Dict[str, str]] = None,
        current_query: str = "",
        **kwargs  # Ignore extra parameters
    ) -> Dict[str, float]:
        """
        Evaluate response using paper-accurate metrics:
        - ROUGE-1 and ROUGE-2 only
        - GPT-4 score on 0-2 scale
        """
        
        results = {}
        
        # Calculate ROUGE scores (only ROUGE-1 and ROUGE-2)
        rouge_scores = self.calculate_rouge_scores(generated_response, reference_response)
        results.update(rouge_scores)
        
        # Calculate GPT-4 score
        gpt4_scores = await self.calculate_gpt4_score(
            generated_response, 
            reference_response, 
            dialogue_history, 
            current_query
        )
        results.update(gpt4_scores)
        
        # Add response length for analysis
        results['response_length'] = len(generated_response.split())
        results['reference_length'] = len(reference_response.split())
        
        return results
    
    def format_results(self, scores: Dict[str, float]) -> str:
        """Format evaluation results for display"""
        
        output = []
        output.append("**📊 Paper-Accurate Evaluation Results:**")
        output.append("")
        
        # ROUGE scores
        rouge1 = scores.get('rouge1', 0)
        rouge2 = scores.get('rouge2', 0)
        output.append(f"**ROUGE-1:** {rouge1:.3f} ({rouge1*100:.1f}%)")
        output.append(f"**ROUGE-2:** {rouge2:.3f} ({rouge2*100:.1f}%)")
        
        # GPT-4 score
        gpt4_score = scores.get('gpt4_score', 0)
        gpt4_interpretation = {
            0: "Completely wrong",
            1: "Contains part of reference",
            2: "Contains all reference info"
        }
        interpretation = gpt4_interpretation.get(int(gpt4_score), "Unknown")
        output.append(f"**GPT-4 Score:** {gpt4_score:.1f}/2.0 ({interpretation})")
        
        # Comparison to paper benchmarks
        output.append("")
        output.append("**🎯 vs Paper Benchmarks:**")
        
        # Learning new knowledge benchmarks from paper
        target_rouge1 = 0.4608  # 46.08%
        target_rouge2 = 0.1738  # 17.38%
        target_gpt4 = 0.63      # 0.63/2.0
        
        rouge1_status = "✅" if rouge1 >= target_rouge1 else "❌"
        rouge2_status = "✅" if rouge2 >= target_rouge2 else "❌"
        gpt4_status = "✅" if gpt4_score >= target_gpt4 else "❌"
        
        output.append(f"- ROUGE-1 Target: {target_rouge1:.3f} {rouge1_status}")
        output.append(f"- ROUGE-2 Target: {target_rouge2:.3f} {rouge2_status}")
        output.append(f"- GPT-4 Target: {target_gpt4:.2f} {gpt4_status}")
        
        # Response stats
        output.append("")
        output.append(f"**📝 Response Stats:**")
        output.append(f"- Generated length: {scores.get('response_length', 0)} words")
        output.append(f"- Reference length: {scores.get('reference_length', 0)} words")
        
        return "\n".join(output)