"""
LoCoMo LLM-as-Judge Evaluator

Implements the official LoCoMo evaluation methodology using LLM to judge answer correctness.
Reference: MemOS/evaluation/scripts/locomo/locomo_eval.py
"""

import json
import asyncio
from typing import Dict, Any
from openai import AsyncOpenAI


class LoCoMoLLMJudge:
    """LLM-as-Judge evaluator following LoCoMo benchmark standard"""

    def __init__(self, model="gpt-4o-mini"):
        self.model = model
        import os
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            try:
                from src.config import OPENAI_API_KEY
                api_key = OPENAI_API_KEY
            except ImportError:
                pass
        self.client = AsyncOpenAI(api_key=api_key)

    async def judge_answer(self, question: str, gold_answer: str, generated_answer: str) -> Dict[str, Any]:
        """
        Judge if generated answer is correct using LLM.

        Args:
            question: The question asked
            gold_answer: The ground truth answer
            generated_answer: The system's answer

        Returns:
            {
                'correct': bool,
                'reasoning': str,
                'label': 'CORRECT' | 'WRONG'
            }
        """
        system_prompt = """You are an expert grader that determines if answers to questions match a gold standard answer."""

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
Generated answer: {generated_answer}

First, provide a short (one sentence) explanation of your reasoning, then finish with CORRECT or WRONG.
Do NOT include both CORRECT and WRONG in your response, or it will break the evaluation script.

Just return the label CORRECT or WRONG in a json format with the key as "label" and reasoning with key "reasoning".
"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": accuracy_prompt},
            ],
            temperature=0,
        )

        message_content = response.choices[0].message.content
        try:
            result = json.loads(message_content)
            label = result.get("label", "WRONG").strip().upper()
            reasoning = result.get("reasoning", "")

            return {
                'correct': label == "CORRECT",
                'label': label,
                'reasoning': reasoning
            }
        except json.JSONDecodeError:
            # Fallback parsing
            content_upper = message_content.upper()
            if "CORRECT" in content_upper and "WRONG" not in content_upper:
                return {'correct': True, 'label': 'CORRECT', 'reasoning': message_content}
            else:
                return {'correct': False, 'label': 'WRONG', 'reasoning': message_content}


async def evaluate_with_llm_judge(results: list) -> Dict[str, Any]:
    """
    Re-evaluate test results using LLM-as-Judge.

    Args:
        results: List of test results with format:
            [
                {
                    'question': str,
                    'expected': str,
                    'answer': str,
                    'correct_string_match': bool  # Original simple matching result
                },
                ...
            ]

    Returns:
        {
            'llm_judge_accuracy': float,
            'string_match_accuracy': float,
            'difference': float,
            'details': list
        }
    """
    judge = LoCoMoLLMJudge()

    llm_correct = 0
    string_match_correct = 0
    details = []

    for result in results:
        # LLM judgment
        judgment = await judge.judge_answer(
            question=result['question'],
            gold_answer=result['expected'],
            generated_answer=result['answer']
        )

        llm_is_correct = judgment['correct']
        string_is_correct = result.get('correct_string_match', False)

        if llm_is_correct:
            llm_correct += 1
        if string_is_correct:
            string_match_correct += 1

        details.append({
            **result,
            'llm_judgment': judgment['label'],
            'llm_reasoning': judgment['reasoning'],
            'llm_correct': llm_is_correct,
            'disagreement': llm_is_correct != string_is_correct
        })

    total = len(results)
    llm_accuracy = llm_correct / total if total > 0 else 0.0
    string_accuracy = string_match_correct / total if total > 0 else 0.0

    return {
        'llm_judge_accuracy': llm_accuracy,
        'string_match_accuracy': string_accuracy,
        'accuracy_difference': llm_accuracy - string_accuracy,
        'llm_correct_count': llm_correct,
        'string_correct_count': string_match_correct,
        'total': total,
        'details': details
    }


if __name__ == "__main__":
    # Example usage
    test_results = [
        {
            'question': 'What fields would Caroline pursue?',
            'expected': 'psychology',
            'answer': 'Community Advocacy, LGBTQ Studies, Psychology, Social Work',
            'correct_string_match': False  # String matching says WRONG because it's a list
        },
        {
            'question': 'What is Caroline\'s identity?',
            'expected': 'transgender woman',
            'answer': 'transgender woman',
            'correct_string_match': True
        }
    ]

    async def run_example():
        result = await evaluate_with_llm_judge(test_results)
        print("\n=== LLM-as-Judge Evaluation Results ===")
        print(f"LLM-as-Judge Accuracy: {result['llm_judge_accuracy']:.1%}")
        print(f"String Match Accuracy: {result['string_match_accuracy']:.1%}")
        print(f"Difference: {result['accuracy_difference']:.1%}")

        print("\n=== Details ===")
        for detail in result['details']:
            symbol = "✅" if detail['llm_correct'] else "❌"
            print(f"\n{symbol} Q: {detail['question']}")
            print(f"   Expected: {detail['expected']}")
            print(f"   Got: {detail['answer']}")
            print(f"   LLM Judge: {detail['llm_judgment']}")
            if detail['disagreement']:
                print(f"   ⚠️  Disagrees with string matching!")

    asyncio.run(run_example())
