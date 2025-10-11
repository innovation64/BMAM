"""
快速5题测试 - 验证修复效果
测试Q1, Q2, Q3, Q4, Q5
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from datetime import datetime

from src.coordination.brain_coordinator import BrainInspiredCoordinator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 5个测试问题
TEST_QUESTIONS = [
    {
        'id': 'Q1',
        'question': 'When did Caroline go to the LGBTQ support group?',
        'expected': '7 May 2023',
        'category': 'temporal_reasoning',
        'fix': '时间推理修复'
    },
    {
        'id': 'Q2',
        'question': 'When did Melanie paint a sunrise?',
        'expected': '2022',
        'category': 'temporal_reasoning',
        'fix': '答案格式改进'
    },
    {
        'id': 'Q3',
        'question': 'What fields would Caroline be likely to pursue in her educaton?',
        'expected': 'Psychology, counseling certification',
        'category': 'open_domain',
        'fix': '推理增强'
    },
    {
        'id': 'Q4',
        'question': 'What did Caroline research?',
        'expected': 'Adoption agencies',
        'category': 'multi_hop',
        'fix': '关键词变形检索'
    },
    {
        'id': 'Q5',
        'question': "What is Caroline's identity?",
        'expected': 'Transgender woman',
        'category': 'multi_hop',
        'fix': '身份推理强化'
    }
]

# 学习数据
LEARNING_DATA = [
    # Session 1 context
    "Today's date is 8 May, 2023. This conversation is happening on this date.",

    # Session 1 key dialogues
    "[Context: This conversation is on 8 May, 2023] Caroline: I went to a LGBTQ support group yesterday and it was so powerful.",
    "Caroline: The transgender stories were so inspiring! I was so happy and thankful for all the support.",
    "Caroline: The support group has made me feel accepted and given me courage to embrace myself.",
    "Caroline: I'm keen on counseling or working in mental health - I'd love to support those with similar issues.",
    "Melanie: You'd be a great counselor! Your empathy and understanding will really help the people you work with.",
    "Melanie: Yeah, I painted that lake sunrise last year! It's special to me.",

    # Session 2 events
    "On 25 May, 2023, Caroline: Caroline is inspired by her supportive friends and mentors to start researching adoption agencies.",
]


async def main():
    logger.info("="*80)
    logger.info("🧪 Quick 5-Question Test - 验证修复效果")
    logger.info("="*80)

    # 初始化系统
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()
    logger.info("✅ 系统初始化完成\n")

    # 学习阶段
    logger.info("📚 学习阶段: 输入关键记忆")
    logger.info("-"*80)
    for i, data in enumerate(LEARNING_DATA, 1):
        logger.info(f"  [{i}/{len(LEARNING_DATA)}] 学习: {data[:80]}...")
        try:
            await coordinator.process_user_input(data)
        except Exception as e:
            logger.warning(f"  ⚠️ 学习警告: {e}")
    logger.info("✅ 学习完成\n")

    # 测试阶段
    logger.info("🧪 测试阶段: 5个问题")
    logger.info("="*80)

    results = []
    correct_count = 0

    for i, qa in enumerate(TEST_QUESTIONS, 1):
        logger.info(f"\n--- 问题 {i}/5: {qa['id']} ---")
        logger.info(f"❓ {qa['question']}")
        logger.info(f"✅ 期望: {qa['expected']}")
        logger.info(f"🔧 修复: {qa['fix']}")

        start_time = time.time()
        try:
            # Benchmark模式
            response = await coordinator.process_user_input(
                qa['question'],
                context={'benchmark_mode': True, 'force_english': True}
            )
            elapsed = time.time() - start_time

            logger.info(f"💬 回答: {response}")
            logger.info(f"⏱️  耗时: {elapsed:.2f}s")

            # 简单评估
            expected_lower = str(qa['expected']).lower()
            response_lower = str(response).lower()

            is_correct = (
                expected_lower in response_lower or
                any(word in response_lower for word in expected_lower.split()[:2])
            )

            if is_correct:
                correct_count += 1
                logger.info(f"✅ 通过")
            else:
                logger.info(f"❌ 未通过")

            results.append({
                'id': qa['id'],
                'question': qa['question'],
                'expected': qa['expected'],
                'response': response,
                'correct': is_correct,
                'time': elapsed,
                'category': qa['category'],
                'fix_applied': qa['fix']
            })

        except Exception as e:
            logger.error(f"❌ 错误: {e}")
            results.append({
                'id': qa['id'],
                'question': qa['question'],
                'expected': qa['expected'],
                'error': str(e),
                'correct': False,
                'time': time.time() - start_time
            })

    # 总结
    logger.info("\n" + "="*80)
    logger.info("📊 测试总结")
    logger.info("="*80)
    logger.info(f"总问题数: {len(TEST_QUESTIONS)}")
    logger.info(f"通过数: {correct_count}")
    logger.info(f"准确率: {correct_count/len(TEST_QUESTIONS)*100:.1f}%")
    logger.info(f"平均耗时: {sum(r['time'] for r in results)/len(results):.2f}s")
    logger.info("")

    for r in results:
        status = "✅" if r.get('correct') else "❌"
        logger.info(f"  {status} {r['id']}: {r.get('fix_applied', 'N/A')}")

    # 保存结果
    output_file = Path('results/quick_5q_test_fixed.json')
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total': len(TEST_QUESTIONS),
            'correct': correct_count,
            'accuracy': correct_count/len(TEST_QUESTIONS),
            'avg_time': sum(r['time'] for r in results)/len(results),
            'results': results
        }, f, indent=2)

    logger.info(f"\n💾 结果已保存: {output_file}")
    logger.info("="*80)


if __name__ == '__main__':
    asyncio.run(main())
