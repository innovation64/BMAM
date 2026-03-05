"""
优化后系统测试脚本 - 基于Locomo数据集小样本
测试上下文优化效果（Token使用、记忆摘要、动态压缩等）
"""

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.utils.context_budget_manager import get_budget_manager, Priority
from src.agents.core.context_compaction import ContextCompactionAgent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OptimizedContextTester:
    """优化后上下文系统测试器"""

    def __init__(self):
        self.coordinator = None
        self.budget_manager = get_budget_manager()
        self.compaction_agent = ContextCompactionAgent()
        self.conversation_history = []
        self.test_results = []

    async def initialize(self):
        """初始化系统"""
        logger.info("初始化优化后的系统...")
        self.coordinator = BrainInspiredCoordinator()
        await self.coordinator.initialize()
        logger.info("系统初始化完成")

    def load_locomo_sample(self, sample_size: int = 3) -> List[Dict]:
        """
        从Locomo数据集提取小样本

        Args:
            sample_size: 提取的会话数量（默认3个）

        Returns:
            提取的测试样本
        """
        locomo_path = Path("data/benchmarks/locomo/locomo10.json")

        if not locomo_path.exists():
            raise FileNotFoundError(f"Locomo数据集未找到: {locomo_path}")

        with open(locomo_path, 'r', encoding='utf-8') as f:
            all_data = json.load(f)

        # 提取前N个会话
        samples = all_data[:sample_size]

        logger.info(f"从Locomo数据集提取了 {len(samples)} 个会话样本")
        for i, sample in enumerate(samples, 1):
            qa_count = len(sample.get('qa', []))
            conv_turns = len(sample.get('conversation', []))
            logger.info(f"  样本{i}: {qa_count}个问答, {conv_turns}轮对话")

        return samples

    async def test_single_session(self, session: Dict, session_id: int) -> Dict[str, Any]:
        """
        测试单个会话

        Args:
            session: Locomo会话数据
            session_id: 会话编号

        Returns:
            测试结果
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"测试会话 #{session_id}")
        logger.info(f"{'='*60}")

        result = {
            'session_id': session_id,
            'qa_count': len(session.get('qa', [])),
            'conversation_turns': len(session.get('conversation', [])),
            'responses': [],
            'token_stats': {},
            'compaction_triggered': False,
            'errors': []
        }

        # 处理对话轮次 (从session_1提取)
        conversation = session.get('conversation', {})
        session_data = conversation.get('session_1', [])

        if not isinstance(session_data, list):
            logger.warning(f"会话数据格式异常: {type(session_data)}")
            session_data = []

        # 限制前10轮测试
        conv_list = session_data[:10]

        for i, turn in enumerate(conv_list, 1):
            user_input = turn.get('text', '')

            logger.info(f"\n--- 第 {i} 轮对话 ---")
            logger.info(f"用户: {user_input[:100]}...")

            try:
                # 分配Token预算
                allocated = self.budget_manager.allocate(
                    agent_id="test_coordinator",
                    task_type="user_query",
                    priority=Priority.HIGH
                )
                logger.info(f"分配Token预算: {allocated}")

                # 处理用户输入
                start_time = datetime.now()
                response_result = await self.coordinator.process_user_input(
                    user_input,
                    context={'session_id': session_id, 'turn': i}
                )
                end_time = datetime.now()

                response_time = (end_time - start_time).total_seconds()
                response_text = response_result.response

                logger.info(f"系统响应: {response_text[:100]}...")
                logger.info(f"响应时间: {response_time:.2f}s")

                # 记录到对话历史
                self.conversation_history.append({
                    'role': 'user',
                    'content': user_input
                })
                self.conversation_history.append({
                    'role': 'assistant',
                    'content': response_text
                })

                # 检查是否需要压缩
                should_compact_result = await self.compaction_agent.process_message(
                    type('Message', (), {
                        'content': {
                            'action': 'should_compact',
                            'turn_count': len(self.conversation_history) // 2
                        }
                    })()
                )

                if should_compact_result.get('should_compact'):
                    logger.info("🗜️ 触发上下文压缩...")
                    compact_result = await self.compaction_agent.process_message(
                        type('Message', (), {
                            'content': {
                                'action': 'compact_conversation',
                                'conversation_history': self.conversation_history
                            }
                        })()
                    )

                    if compact_result.get('compacted'):
                        result['compaction_triggered'] = True
                        tokens_saved = compact_result.get('tokens_saved', 0)
                        logger.info(f"✅ 压缩完成，节省 {tokens_saved} tokens")

                        # 重置对话历史为摘要
                        summary = compact_result.get('summary', '')
                        self.conversation_history = [
                            {'role': 'system', 'content': f"对话摘要：{summary}"}
                        ]

                        # 重置预算
                        self.budget_manager.reset()

                result['responses'].append({
                    'turn': i,
                    'user_input': user_input[:100],
                    'response': response_text[:100],
                    'response_time': response_time,
                    'agents_involved': response_result.agents_involved
                })

            except Exception as e:
                logger.error(f"处理第{i}轮时出错: {e}")
                result['errors'].append({
                    'turn': i,
                    'error': str(e)
                })

        # 获取Token统计
        budget_stats = self.budget_manager.get_stats()
        result['token_stats'] = budget_stats

        logger.info(f"\n📊 会话 #{session_id} Token统计:")
        logger.info(f"  - 最大预算: {budget_stats['max_budget']}")
        logger.info(f"  - 当前使用: {budget_stats['current_usage']}")
        logger.info(f"  - 使用率: {budget_stats['usage_ratio']}")
        logger.info(f"  - 分配效率: {budget_stats['allocation_efficiency']}")
        logger.info(f"  - 预算超支: {budget_stats['budget_overruns']}")

        # 测试问答（可选）
        qa_tests = session.get('qa', [])[:3]  # 只测试前3个问答
        for qa in qa_tests:
            question = qa.get('question', '')
            expected_answer = qa.get('answer', '')

            logger.info(f"\n❓ 问答测试: {question}")
            try:
                qa_result = await self.coordinator.process_user_input(question)
                logger.info(f"期望答案: {expected_answer}")
                logger.info(f"实际回答: {qa_result.response[:100]}...")
            except Exception as e:
                logger.error(f"问答测试失败: {e}")

        return result

    async def run_tests(self, sample_size: int = 3):
        """
        运行完整测试

        Args:
            sample_size: 测试的会话数量
        """
        logger.info("🚀 开始优化后系统测试...")

        # 加载样本
        samples = self.load_locomo_sample(sample_size)

        # 逐个测试会话
        for i, session in enumerate(samples, 1):
            result = await self.test_single_session(session, i)
            self.test_results.append(result)

            # 清空对话历史（新会话）
            self.conversation_history = []
            self.budget_manager.reset()

        # 生成测试报告
        self.generate_report()

    def generate_report(self):
        """生成测试报告"""
        logger.info(f"\n{'='*60}")
        logger.info("📋 测试报告汇总")
        logger.info(f"{'='*60}")

        total_sessions = len(self.test_results)
        total_responses = sum(len(r['responses']) for r in self.test_results)
        total_errors = sum(len(r['errors']) for r in self.test_results)
        compaction_count = sum(1 for r in self.test_results if r['compaction_triggered'])

        logger.info(f"\n总体统计:")
        logger.info(f"  - 测试会话: {total_sessions}")
        logger.info(f"  - 总响应数: {total_responses}")
        logger.info(f"  - 总错误数: {total_errors}")
        logger.info(f"  - 触发压缩: {compaction_count} 次")

        # 平均响应时间
        all_times = [
            resp['response_time']
            for r in self.test_results
            for resp in r['responses']
        ]
        avg_time = sum(all_times) / len(all_times) if all_times else 0
        logger.info(f"  - 平均响应时间: {avg_time:.2f}s")

        # Token效率
        logger.info(f"\nToken使用效率:")
        for i, result in enumerate(self.test_results, 1):
            stats = result.get('token_stats', {})
            logger.info(f"  会话#{i}:")
            logger.info(f"    - 使用率: {stats.get('usage_ratio', 'N/A')}")
            logger.info(f"    - 分配效率: {stats.get('allocation_efficiency', 'N/A')}")

        # 保存报告
        report_path = Path("results/optimization_test_report.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump({
                'test_time': datetime.now().isoformat(),
                'summary': {
                    'total_sessions': total_sessions,
                    'total_responses': total_responses,
                    'total_errors': total_errors,
                    'compaction_count': compaction_count,
                    'avg_response_time': avg_time
                },
                'detailed_results': self.test_results
            }, f, indent=2, ensure_ascii=False)

        logger.info(f"\n✅ 详细报告已保存到: {report_path}")

    async def cleanup(self):
        """清理资源"""
        if self.coordinator:
            await self.coordinator.stop_system()
        logger.info("系统已清理")


async def main():
    """主测试函数"""
    tester = OptimizedContextTester()

    try:
        await tester.initialize()
        await tester.run_tests(sample_size=3)  # 测试3个会话
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
