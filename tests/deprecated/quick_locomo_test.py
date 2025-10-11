"""
快速LoCoMo样本测试: BrainNetwork模式
"""
import asyncio
import os
import sys
import json

sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')

from src.coordination.brain_coordinator import BrainInspiredCoordinator

# 启用BrainNetwork
os.environ['USE_BRAIN_NETWORK'] = 'true'

async def main():
    print("🧠 BrainNetwork快速LoCoMo测试 (3个问题)\n")

    coordinator = BrainInspiredCoordinator()

    # 学习记忆
    print("📚 学习Session 1...")
    await coordinator.process_user_input("Today's date is 8 May, 2023. This conversation is happening on this date.")
    await coordinator.process_user_input("On 8 May, 2023, Caroline: Caroline attends an LGBTQ support group for the first time.")

    print("📚 学习Session 2...")
    await coordinator.process_user_input("On 25 May, 2023, Caroline: Caroline is inspired by her supportive friends and mentors to start researching adoption agencies.")

    print("\n📖 学习对话...")
    await coordinator.process_user_input("Caroline: Hey Mel! Good to see you! How have you been?")
    await coordinator.process_user_input("Melanie: Hey Caroline! Good to see you! I'm swamped with the kids & work. What's up with you? Anything new?")
    await coordinator.process_user_input("[Context: This conversation is on 8 May, 2023] Caroline: I went to a LGBTQ support group yesterday and it was so powerful.")

    # 测试3个关键问题
    questions = [
        ("When did Caroline go to the LGBTQ support group?", "7 May 2023"),
        ("What did Caroline research?", "Adoption agencies"),
        ("What is Caroline's identity?", "Transgender woman")
    ]

    results = []
    print("\n" + "="*80)
    print("📝 测试问题")
    print("="*80)

    for i, (q, expected) in enumerate(questions, 1):
        print(f"\n❓ Q{i}: {q}")
        print(f"✅ Expected: {expected}")

        result = await coordinator.process_user_input(q, {'benchmark_mode': True, 'force_english': True})
        answer = result.response

        print(f"🤖 BMAM: {answer}")
        print(f"⏱️  Time: {result.processing_time:.2f}s")
        print(f"🧠 Agents: {len(result.agents_involved)}")

        results.append({
            'question': q,
            'expected': expected,
            'answer': answer,
            'time': result.processing_time
        })

    print("\n" + "="*80)
    print("📊 总结")
    print("="*80)
    avg_time = sum(r['time'] for r in results) / len(results)
    print(f"平均响应时间: {avg_time:.2f}s")
    print(f"使用模式: BrainNetwork (并行激活)")

if __name__ == "__main__":
    asyncio.run(main())
