"""
学习模块 (Learning Module)

让系统"活"起来的核心组件:
- FeedbackLoop: 反馈循环，将检索结果转化为学习信号
- LiveLearningSystem: 活的学习系统，整合所有学习组件

使用方式:
    from src.learning import LiveLearningSystem, FeedbackLoop

    # 创建活的学习系统
    learning_system = LiveLearningSystem(
        hippocampus=hippocampus,
        key_optimizer=ContrastiveKeyOptimizer()
    )

    # 检索完成后自动学习
    await learning_system.on_retrieval_complete(query, query_vector, entities, memories)
"""

from .feedback_loop import (
    FeedbackLoop,
    LiveLearningSystem,
    RetrievalOutcome
)

__all__ = [
    'FeedbackLoop',
    'LiveLearningSystem',
    'RetrievalOutcome'
]
