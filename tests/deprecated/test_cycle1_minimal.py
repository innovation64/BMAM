"""
Minimal test for PDCA Cycle 1
Tests 2 questions to quickly validate optimizations
"""
import asyncio
import sys
import time
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.coordination.brain_coordinator import brain_coordinator

async def main():
    questions = [
        ('When did Caroline go to the LGBTQ support group?', '7 May 2023'),
        ('What did Caroline research?', 'Adoption agencies'),
    ]

    results = []

    print("="*80)
    print("PDCA Cycle 1 - Minimal Test (2 questions)")
    print("="*80)

    for i, (question, expected) in enumerate(questions, 1):
        print(f'\n--- Question {i}/2 ---')
        print(f'Q: {question}')
        print(f'Expected: {expected}')

        start = time.time()
        try:
            response = await brain_coordinator.process_message(question)
            elapsed = time.time() - start

            print(f'A: {response}')
            print(f'Time: {elapsed:.2f}s')

            results.append({
                'question': question,
                'expected': expected,
                'response': response,
                'time': elapsed
            })
        except Exception as e:
            print(f'ERROR: {e}')
            results.append({
                'question': question,
                'expected': expected,
                'error': str(e),
                'time': time.time() - start
            })

    # Save results
    output_file = project_root / 'results' / 'cycle1_minimal_test.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump({
            'total_questions': len(questions),
            'avg_time': sum(r.get('time', 0) for r in results) / len(results),
            'results': results
        }, f, indent=2)

    print(f"\n{'='*80}")
    print(f"Results saved to: {output_file}")
    print(f"Average time: {sum(r.get('time', 0) for r in results) / len(results):.2f}s")
    print(f"{'='*80}")

if __name__ == '__main__':
    asyncio.run(main())
