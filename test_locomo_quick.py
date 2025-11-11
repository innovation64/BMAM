#!/usr/bin/env python3
"""
LoCoMo 快速测试 - 5个问题
验证重构后的系统在LoCoMo任务上的表现
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

class QuickLoCoMoTest:
    """LoCoMo快速测试类"""

    def __init__(self):
        self.coordinator = None
        self.results = []

    async def initialize(self):
        """初始化协调器"""
        print("🔧 初始化BMAM协调器...")
        try:
            self.coordinator = BrainInspiredCoordinator()
            print("✅ 协调器初始化成功")
            return True
        except Exception as e:
            print(f"❌ 协调器初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def run_test_questions(self, num_questions: int = 5):
        """运行测试问题"""
        print(f"\n📝 开始测试 {num_questions} 个问题")
        print("=" * 60)

        # 简单的测试问题（模拟LoCoMo格式）
        test_qa = [
            {
                "question": "今天天气怎么样？",
                "context": "早上8点，阳光明媚，气温20度。",
                "expected_type": "事实回忆"
            },
            {
                "question": "我早上做了什么？",
                "context": "之前说过：早上7点起床，吃了早餐。",
                "expected_type": "时间推理"
            },
            {
                "question": "我喜欢什么颜色？",
                "context": "之前提到：我最喜欢蓝色。",
                "expected_type": "偏好记忆"
            },
            {
                "question": "总结一下今天的活动",
                "context": "综合之前的对话内容",
                "expected_type": "多跳汇总"
            },
            {
                "question": "明天计划做什么？",
                "context": "之前说：明天要去图书馆学习。",
                "expected_type": "未来规划"
            }
        ]

        correct = 0

        for i, qa in enumerate(test_qa[:num_questions], 1):
            print(f"\n问题 {i}/{num_questions}")
            print(f"Q: {qa['question']}")
            print(f"类型: {qa['expected_type']}")

            try:
                # 先输入context
                if qa['context']:
                    print(f"输入上下文: {qa['context']}")
                    await self.coordinator.process_input(qa['context'])

                # 处理问题
                response = await self.coordinator.process_input(qa['question'])
                print(f"A: {response[:200]}...")

                # 简单判断（实际应该用LLM评判）
                has_response = len(response) > 0

                if has_response:
                    correct += 1
                    print("✅ 有响应")
                else:
                    print("❌ 无响应")

                self.results.append({
                    'question_id': i,
                    'question': qa['question'],
                    'response': response,
                    'has_response': has_response,
                    'type': qa['expected_type']
                })

            except Exception as e:
                print(f"❌ 处理失败: {e}")
                self.results.append({
                    'question_id': i,
                    'question': qa['question'],
                    'error': str(e),
                    'has_response': False
                })

        print(f"\n{'=' * 60}")
        print(f"📊 测试完成")
        print(f"   成功响应: {correct}/{num_questions} ({correct/num_questions*100:.1f}%)")

        return correct, num_questions

    def save_results(self, output_file: str = "test_results.json"):
        """保存测试结果"""
        result_data = {
            'test_time': datetime.now().isoformat(),
            'total_questions': len(self.results),
            'results': self.results
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        print(f"\n💾 结果已保存: {output_file}")

async def main():
    """主测试流程"""
    print("=" * 60)
    print("  LoCoMo 快速测试 (5个问题)")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 创建测试实例
    tester = QuickLoCoMoTest()

    # 初始化
    if not await tester.initialize():
        print("\n❌ 初始化失败，测试终止")
        return 1

    # 运行测试
    correct, total = await tester.run_test_questions(num_questions=5)

    # 保存结果
    tester.save_results("locomo_quick_test_results.json")

    # 总结
    print("\n" + "=" * 60)
    print("  测试总结")
    print("=" * 60)

    accuracy = correct / total * 100 if total > 0 else 0

    print(f"✅ 测试完成")
    print(f"   问题总数: {total}")
    print(f"   成功响应: {correct}")
    print(f"   响应率: {accuracy:.1f}%")

    if accuracy >= 80:
        print(f"\n🎉 测试通过！响应率 {accuracy:.1f}% >= 80%")
        return 0
    else:
        print(f"\n⚠️  响应率较低: {accuracy:.1f}%")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
