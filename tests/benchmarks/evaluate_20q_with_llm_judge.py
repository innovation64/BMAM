"""
Re-evaluate the 20-question test results using LLM-as-Judge
"""

import asyncio
import sys
from pathlib import Path

# Use relative path instead of hardcoded absolute path
_BMAM_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(_BMAM_ROOT))

from evaluation.llm_judge_locomo import evaluate_with_llm_judge


# 20问测试结果（从test log中提取）
test_results = [
    {
        'question': 'When did Caroline go to the LGBTQ support group?',
        'expected': '7 May 2023',
        'answer': '7 May 2023',
        'correct_string_match': True
    },
    {
        'question': 'What did Caroline research?',
        'expected': 'adoption agencies',
        'answer': 'Community Advocacy, Family Studies, LGBTQ Studies, Psychology, Social Work',
        'correct_string_match': False
    },
    {
        'question': "What is Caroline's identity?",
        'expected': 'transgender woman',
        'answer': 'transgender woman',
        'correct_string_match': True
    },
    {
        'question': 'What fields would Caroline be likely to pursue in her education?',
        'expected': 'psychology',
        'answer': 'Community Advocacy, Family Studies, LGBTQ Studies, Psychology, Social Work',
        'correct_string_match': True
    },
    {
        'question': 'What community did Caroline engage with?',
        'expected': 'LGBTQ community',
        'answer': 'LGBTQ community',
        'correct_string_match': True
    },
    {
        'question': 'When did Caroline volunteer at the LGBTQ youth center?',
        'expected': '3 June 2023',
        'answer': '3 June 2023',
        'correct_string_match': True
    },
    {
        'question': 'How many days passed between Caroline going to the support group and researching adoption agencies?',
        'expected': '17',
        'answer': '17 days',
        'correct_string_match': True
    },
    {
        'question': 'What type of programs did Caroline apply to?',
        'expected': 'graduate programs',
        'answer': 'graduate programs in social work and psychology',
        'correct_string_match': True
    },
    {
        'question': 'What certification does Caroline want to get?',
        'expected': 'counselor',
        'answer': 'get certified as a counselor',
        'correct_string_match': True
    },
    {
        'question': "What is Caroline's relationship status?",
        'expected': 'single',
        'answer': 'single',
        'correct_string_match': True
    },
    {
        'question': 'What demographic does Caroline identify with?',
        'expected': 'LGBTQ',
        'answer': 'transgender woman',
        'correct_string_match': True
    },
    {
        'question': 'What specific area of counseling is Caroline interested in?',
        'expected': 'family counseling',
        'answer': 'Community Advocacy, LGBTQ Studies, Psychology, Social Work',
        'correct_string_match': True
    },
    {
        'question': 'What population does Caroline want to work with?',
        'expected': 'LGBTQ individuals',
        'answer': 'Caroline wants to work with the LGBTQ community, specifically focusing on family counseling for LGBTQ individuals',
        'correct_string_match': True
    },
    {
        'question': "What pattern can you identify in Caroline's activities across all sessions?",
        'expected': 'LGBTQ advocacy',
        'answer': "Caroline's activities consistently focus on community advocacy, LGBTQ studies, psychology, and social work",
        'correct_string_match': True
    },
    {
        'question': "What common theme appears in Caroline's career interests?",
        'expected': 'mental health',
        'answer': 'Community Advocacy, Family Studies, LGBTQ Studies, Psychology, Social Work',
        'correct_string_match': False
    },
    {
        'question': "Based on Caroline's experiences and interests, what career path is she most likely pursuing?",
        'expected': 'LGBTQ counselor',
        'answer': 'Community Advocacy, LGBTQ Studies, Psychology, Social Work',
        'correct_string_match': True
    },
    {
        'question': 'Why might Caroline be interested in family counseling specifically?',
        'expected': 'family acceptance issues',
        'answer': 'Community Advocacy, Family Studies, LGBTQ Studies, Psychology, Social Work',
        'correct_string_match': True
    },
    {
        'question': 'What was the first activity Caroline did related to LGBTQ community?',
        'expected': 'support group',
        'answer': '7 May 2023',
        'correct_string_match': False
    },
    {
        'question': 'Within what timeframe does Caroline want to become certified?',
        'expected': '2-3 years',
        'answer': '2-3 years',
        'correct_string_match': True
    },
    {
        'question': 'What motivated Caroline to pursue a career in counseling?',
        'expected': 'transgender stories inspired',
        'answer': 'Community Advocacy, Family Studies, LGBTQ Studies, Psychology, Social Work',
        'correct_string_match': False
    }
]


async def main():
    print("="*80)
    print("🔍 Re-evaluating 20-Question Test with LLM-as-Judge (LoCoMo Standard)")
    print("="*80)

    result = await evaluate_with_llm_judge(test_results)

    print(f"\n{'='*80}")
    print("📊 Overall Results")
    print(f"{'='*80}")
    print(f"String Match Accuracy:  {result['string_match_accuracy']:.1%} ({result['string_correct_count']}/{result['total']})")
    print(f"LLM-as-Judge Accuracy:  {result['llm_judge_accuracy']:.1%} ({result['llm_correct_count']}/{result['total']})")
    print(f"Accuracy Difference:    {result['accuracy_difference']:+.1%}")

    # Show disagreements
    disagreements = [d for d in result['details'] if d['disagreement']]
    if disagreements:
        print(f"\n{'='*80}")
        print(f"⚠️  {len(disagreements)} Disagreements between String Match and LLM Judge")
        print(f"{'='*80}")

        for detail in disagreements:
            string_result = "✅" if detail['correct_string_match'] else "❌"
            llm_result = "✅" if detail['llm_correct'] else "❌"

            print(f"\nQ: {detail['question']}")
            print(f"   Expected: {detail['expected']}")
            print(f"   Got: {detail['answer'][:80]}...")
            print(f"   String Match: {string_result}  |  LLM Judge: {llm_result} ({detail['llm_judgment']})")
            print(f"   Reasoning: {detail['llm_reasoning']}")

    # Show all results
    print(f"\n{'='*80}")
    print("📋 Detailed Results")
    print(f"{'='*80}")

    for i, detail in enumerate(result['details'], 1):
        symbol = "✅" if detail['llm_correct'] else "❌"
        print(f"\n{symbol} Q{i}: {detail['question']}")
        print(f"   Expected: {detail['expected']}")
        print(f"   Got: {detail['answer'][:100]}{'...' if len(detail['answer']) > 100 else ''}")
        print(f"   LLM Judge: {detail['llm_judgment']}")
        if not detail['llm_correct']:
            print(f"   Reasoning: {detail['llm_reasoning']}")


if __name__ == "__main__":
    asyncio.run(main())
