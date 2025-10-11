#!/usr/bin/env python3
"""
快速小样本LoCoMo测试
Quick LoCoMo Sample Test (10 questions)
"""

import asyncio
import json
import time
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.coordination.brain_coordinator import BrainInspiredCoordinator


async def main():
    print("=" * 80)
    print("🧪 BMAM LoCoMo Quick Sample Test (10 Questions)")
    print("=" * 80)
    print()

    # Load LoCoMo data
    locomo_file = Path("/Users/liyang/Desktop/testversion/MemOS/evaluation/data/locomo/locomo10.json")

    if not locomo_file.exists():
        print(f"❌ LoCoMo data not found: {locomo_file}")
        return

    with open(locomo_file) as f:
        conversations = json.load(f)

    print(f"✅ Loaded {len(conversations)} conversations")
    print()

    # Extract first 10 questions from first conversation only
    # (to avoid mixing contexts from different conversations)
    questions = []
    test_conversation = None

    if conversations and "qa" in conversations[0]:
        test_conversation = conversations[0]
        for qa in conversations[0]["qa"][:10]:  # First 10 questions
            questions.append({
                "question": qa["question"],
                "answer": str(qa.get("answer", "")),
                "category": qa.get("category", 4),
            })

    print(f"📝 Selected {len(questions)} questions for testing")
    print()

    # Category mapping
    category_names = {
        1: "multi_hop",
        2: "temporal_reasoning",
        3: "open_domain",
        4: "single_hop"
    }

    # Initialize BMAM
    print("🚀 Initializing BMAM...")
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()
    print("✅ BMAM initialized")
    print()

    # Step 1: Feed conversation context to build memory
    if test_conversation:
        print("📥 Feeding conversation context to BMAM...")
        conv_data = test_conversation["conversation"]
        speaker_a = conv_data.get("speaker_a", "Speaker A")
        speaker_b = conv_data.get("speaker_b", "Speaker B")

        # Process each session
        session_count = 0
        for key in sorted(conv_data.keys()):
            if key.startswith("session_") and not key.endswith("_date_time"):
                session_count += 1
                session_turns = conv_data[key]
                session_date = conv_data.get(f"{key}_date_time", "")

                # Feed session context as a batch (every 10 turns)
                for i in range(0, len(session_turns), 10):
                    batch = session_turns[i:i+10]
                    context_text = f"会话时间: {session_date}\n"
                    for turn in batch:
                        speaker = turn.get("speaker", "Unknown")
                        text = turn.get("text", "")
                        context_text += f"{speaker}: {text}\n"

                    # Feed to BMAM to store as memory
                    try:
                        await coordinator.process_user_input(
                            f"请记住这段对话内容：\n{context_text}"
                        )
                    except Exception as e:
                        print(f"⚠️ Warning feeding context: {e}")

        print(f"✅ Fed {session_count} sessions to memory")
        print()

    # Step 2: Run test questions
    results = []
    correct = 0

    for i, q in enumerate(questions, 1):
        category_name = category_names.get(q["category"], "unknown")
        print(f"[{i}/{len(questions)}] Category: {category_name}")
        print(f"Question: {q['question'][:80]}...")

        try:
            start = time.time()

            # Process with BMAM
            response_obj = await coordinator.process_user_input(q["question"])
            response = response_obj.response if hasattr(response_obj, 'response') else str(response_obj)

            elapsed = time.time() - start

            # Simple evaluation - check if answer keywords are in response
            expected_keywords = q["answer"].lower().split()
            response_lower = response.lower()

            keyword_matches = sum(1 for kw in expected_keywords if kw in response_lower)
            is_correct = keyword_matches >= len(expected_keywords) * 0.5  # 50% keyword match

            if is_correct:
                correct += 1
                status = "✅ PASS"
            else:
                status = "❌ FAIL"

            print(f"Expected: {q['answer'][:50]}...")
            print(f"Got: {response[:100]}...")
            print(f"Time: {elapsed:.2f}s | {status}")
            print()

            results.append({
                "question": q["question"],
                "expected": q["answer"],
                "response": response,
                "category": category_name,
                "correct": is_correct,
                "time": elapsed
            })

        except Exception as e:
            print(f"❌ Error: {e}")
            print()

    # Shutdown
    await coordinator.stop_system()

    # Summary
    print("=" * 80)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 80)
    print(f"Total Questions: {len(questions)}")
    print(f"Correct: {correct}")
    print(f"Accuracy: {correct/len(questions):.1%}")
    print()

    # Category breakdown
    from collections import Counter
    cat_total = Counter([r["category"] for r in results])
    cat_correct = Counter([r["category"] for r in results if r["correct"]])

    print("Category Performance:")
    for cat in set(cat_total.keys()):
        acc = cat_correct[cat] / cat_total[cat] if cat_total[cat] > 0 else 0
        print(f"  {cat:20s}: {cat_correct[cat]}/{cat_total[cat]} ({acc:.1%})")
    print()

    # Average time
    avg_time = sum(r["time"] for r in results) / len(results)
    print(f"Average Response Time: {avg_time:.2f}s")
    print()

    # Save results
    output_file = Path("results/quick_test_results.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_questions": len(questions),
            "correct": correct,
            "accuracy": correct / len(questions),
            "avg_time": avg_time,
            "results": results
        }, f, indent=2)

    print(f"✅ Results saved to: {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())