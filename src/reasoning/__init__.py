"""
🧠 Reasoning Module - 可组合推理能力系统

组件:
- CapabilityAnalyzer: 分析问题需要的推理能力
- CapabilityOrchestrator: 编排执行推理能力
- CAPABILITY_LIBRARY: 推理能力定义库

使用方式:
```python
from src.reasoning import CapabilityBasedReasoning

reasoning = CapabilityBasedReasoning(brain_agents)
result = await reasoning.reason(query, memories)
```
"""

from .capability_analyzer import CapabilityAnalyzer, CAPABILITY_LIBRARY
from .capability_orchestrator import CapabilityOrchestrator

__all__ = ['CapabilityAnalyzer', 'CapabilityOrchestrator', 'CAPABILITY_LIBRARY', 'CapabilityBasedReasoning']


class CapabilityBasedReasoning:
    """
    可组合推理系统 - 统一接口

    简化使用:
    coordinator只需调用reason()方法,无需关心内部细节
    """

    def __init__(self, brain_agents: dict):
        self.analyzer = CapabilityAnalyzer()
        self.orchestrator = CapabilityOrchestrator(brain_agents)

    async def reason(self, query: str, memories: list, context: dict = None) -> dict:
        """
        执行推理

        Args:
            query: 用户问题
            memories: 检索到的记忆
            context: 额外上下文

        Returns:
            {
                'answer': str,
                'confidence': float,
                'reasoning_chain': list,
                'capabilities_used': list
            }
        """
        # Step 1: 分析需要的能力
        analysis = await self.analyzer.analyze(query, context)

        # Step 2: 执行能力组合
        result = await self.orchestrator.execute(
            query=query,
            capabilities=analysis['capabilities'],
            memories=memories,
            execution_plan=analysis['execution_plan']
        )

        return result
