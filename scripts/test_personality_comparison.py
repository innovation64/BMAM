#!/usr/bin/env python3
"""
PersonalityAgent A/B对比测试脚本
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.coordination.personality_version_manager import get_version_manager
from src.coordination.brain_coordinator import BrainInspiredCoordinator


# 测试场景
TEST_SCENARIOS = [
    {
        "name": "记忆回忆",
        "setup": "请记住我喜欢喝绿茶，每天下午3点左右。",
        "questions": [
            "我刚才说我什么时候喝什么茶？",
            "基于我的偏好，推荐一些适合下午的饮品。"
        ]
    },
    {
        "name": "情感支持",
        "setup": None,
        "questions": [
            "今天工作压力很大，感觉很焦虑。"
        ]
    },
    {
        "name": "知识解释",
        "setup": None,
        "questions": [
            "介绍一下神经可塑性系统是如何工作的？"
        ]
    },
    {
        "name": "创意建议",
        "setup": None,
        "questions": [
            "帮我想一些周末放松的活动点子。"
        ]
    }
]


async def test_version(version_name: str):
    """测试指定版本"""
    print(f"\n{'='*60}")
    print(f"测试 {version_name.upper()} 版本")
    print(f"{'='*60}\n")

    # 设置版本
    manager = get_version_manager()
    manager.set_version(version_name)

    # 创建coordinator
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    results = []

    for scenario in TEST_SCENARIOS:
        print(f"\n--- 场景: {scenario['name']} ---\n")

        # 如果有setup，先执行
        if scenario['setup']:
            print(f"Setup: {scenario['setup']}")
            setup_result = await coordinator.process_user_input(scenario['setup'])
            print(f"Bot: {setup_result.response}\n")

        # 执行测试问题
        for question in scenario['questions']:
            print(f"Q: {question}")

            start_time = datetime.now()
            result = await coordinator.process_user_input(question)
            end_time = datetime.now()

            response_time = (end_time - start_time).total_seconds()

            print(f"A: {result.response}")
            print(f"⏱️  响应时间: {response_time:.2f}s")
            print(f"📊 使用记忆: {len(result.memories_retrieved)}")
            print()

            results.append({
                'scenario': scenario['name'],
                'question': question,
                'response': result.response,
                'response_time': response_time,
                'memories_used': len(result.memories_retrieved)
            })

    await coordinator.stop_system()

    return results


async def run_comparison():
    """运行完整对比测试"""
    print(f"\n{'#'*60}")
    print("PersonalityAgent A/B对比测试")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}\n")

    # 测试Original版本
    print("\n🔹 阶段1: 测试Original版本")
    original_results = await test_version('original')

    print("\n" + "="*60)
    print("⏸️  请等待5秒后开始下一个版本的测试...")
    print("="*60)
    await asyncio.sleep(5)

    # 测试MBTI版本
    print("\n🔹 阶段2: 测试MBTI版本")
    mbti_results = await test_version('mbti')

    # 生成对比报告
    print("\n" + "#"*60)
    print("对比报告")
    print("#"*60)

    # 计算平均响应时间
    original_avg_time = sum(r['response_time'] for r in original_results) / len(original_results)
    mbti_avg_time = sum(r['response_time'] for r in mbti_results) / len(mbti_results)

    print(f"\n📊 响应时间对比:")
    print(f"  Original: {original_avg_time:.3f}s")
    print(f"  MBTI:     {mbti_avg_time:.3f}s")
    print(f"  差异:     {abs(mbti_avg_time - original_avg_time):.3f}s")

    # 计算平均记忆使用
    original_avg_mem = sum(r['memories_used'] for r in original_results) / len(original_results)
    mbti_avg_mem = sum(r['memories_used'] for r in mbti_results) / len(mbti_results)

    print(f"\n🧠 记忆使用对比:")
    print(f"  Original: {original_avg_mem:.1f} 条/次")
    print(f"  MBTI:     {mbti_avg_mem:.1f} 条/次")

    print(f"\n📝 场景对比:")
    for i, scenario in enumerate(TEST_SCENARIOS):
        print(f"\n  {scenario['name']}:")
        print(f"    Original响应长度: {len(original_results[i]['response'])} 字符")
        print(f"    MBTI响应长度:     {len(mbti_results[i]['response'])} 字符")

    print("\n" + "#"*60)
    print(f"测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#"*60)

    print("\n💡 下一步:")
    print("  1. 阅读响应内容，评估哪个版本更符合预期")
    print("  2. 记录你的主观评分（1-5分）")
    print("  3. 在 docs/PERSONALITY_AB_TEST.md 中记录测试结果")
    print("  4. 决定使用哪个版本作为默认配置")


def main():
    """主函数"""
    try:
        asyncio.run(run_comparison())
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())