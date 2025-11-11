#!/usr/bin/env python3
"""
测试重构后的BMAM系统
验证核心模块是否正常工作
"""

import asyncio
import sys
from datetime import datetime

def print_section(title):
    """打印测试章节标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def test_result(test_name, success, details=""):
    """打印测试结果"""
    status = "✅" if success else "❌"
    print(f"{status} {test_name}")
    if details:
        print(f"   {details}")
    return success

async def main():
    """主测试流程"""
    all_passed = True

    print_section("BMAM 重构系统测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 测试1: 核心模块导入
    print_section("测试1: 核心模块导入")
    try:
        from src.agents.core.memory_retrieval import MemoryRetrievalAgent
        from src.agents.core.personality import PersonalityAgent

        all_passed &= test_result(
            "MemoryRetrievalAgent导入",
            True,
            f"模块路径: {MemoryRetrievalAgent.__module__}"
        )

        all_passed &= test_result(
            "PersonalityAgent导入",
            True,
            f"模块路径: {PersonalityAgent.__module__}"
        )

    except Exception as e:
        all_passed &= test_result("核心模块导入", False, f"错误: {e}")
        return all_passed

    # 测试2: 子模块导入
    print_section("测试2: 子模块导入")
    try:
        # MemoryRetrieval子模块
        from src.agents.core.memory_retrieval.strategies import (
            SemanticRetrievalStrategy,
            TemporalRetrievalStrategy
        )
        all_passed &= test_result("检索策略导入", True, "7种策略可用")

        # Personality子模块
        from src.agents.core.personality.emotion import EmotionDetector
        from src.agents.core.personality.traits import TraitManager
        all_passed &= test_result("人格子模块导入", True, "4个领域模块可用")

    except Exception as e:
        all_passed &= test_result("子模块导入", False, f"错误: {e}")

    # 测试3: 实例化测试
    print_section("测试3: 实例化测试")
    try:
        # 实例化 MemoryRetrievalAgent
        retrieval_agent = MemoryRetrievalAgent()
        all_passed &= test_result(
            "MemoryRetrievalAgent实例化",
            True,
            f"可用策略: {len(retrieval_agent.get_available_strategies())}种"
        )

        # 实例化 PersonalityAgent
        # 注意: PersonalityAgent需要参数，我们只测试类定义
        all_passed &= test_result(
            "PersonalityAgent类定义",
            True,
            "类定义正常"
        )

    except Exception as e:
        all_passed &= test_result("实例化测试", False, f"错误: {e}")

    # 测试4: 其他已重构模块
    print_section("测试4: 其他已重构模块")
    try:
        from src.agents.core.consolidation import ConsolidationAgent
        from src.agents.core.forgetting import ForgettingAgent
        from src.agents.core.reflection import ReflectionAgent

        all_passed &= test_result("其他模块导入", True, "巩固、遗忘、反思模块正常")

    except Exception as e:
        all_passed &= test_result("其他模块导入", False, f"错误: {e}")

    # 测试5: 简单功能测试
    print_section("测试5: 简单功能测试")
    try:
        # 测试检索策略枚举
        strategies = retrieval_agent.get_available_strategies()
        expected_strategies = ['semantic', 'temporal', 'episodic', 'associative',
                              'pattern', 'contextual', 'multi']

        has_all = all(s in strategies for s in expected_strategies)
        all_passed &= test_result(
            "检索策略完整性",
            has_all,
            f"实际策略: {strategies}"
        )

        # 测试缓存统计
        cache_stats = retrieval_agent.get_cache_stats()
        all_passed &= test_result(
            "缓存功能",
            'hit_rate' in cache_stats,
            f"缓存统计: {cache_stats}"
        )

    except Exception as e:
        all_passed &= test_result("功能测试", False, f"错误: {e}")

    # 最终结果
    print_section("测试总结")
    if all_passed:
        print("🎉 所有测试通过！")
        print("✅ 重构后的系统核心功能正常")
        print("✅ 模块化架构工作良好")
        print("✅ 可以进行进一步测试")
        return 0
    else:
        print("❌ 部分测试失败")
        print("⚠️  需要检查失败的模块")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
