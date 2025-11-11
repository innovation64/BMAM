"""
Contextual Retrieval Strategy
上下文检索策略 - 基于上下文特征的记忆检索
"""

from .base import RetrievalStrategy
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class ContextualRetrievalStrategy(RetrievalStrategy):
    """
    上下文检索策略

    功能:
    - 基于上下文特征匹配记忆
    - 支持多维度上下文(标签、环境、任务、情绪等)
    - 计算上下文匹配度

    应用场景:
    - 情境记忆检索
    - 任务相关记忆
    - 环境触发的记忆
    """

    @property
    def strategy_name(self) -> str:
        return "contextual"

    async def retrieve(
        self,
        context: Dict[str, Any],
        k: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        上下文检索

        Args:
            context: 上下文特征字典
                {
                    'tags': ['工作', '项目'],
                    'environment': '办公室',
                    'task': '编程',
                    'mood': '专注',
                    'time_of_day': '下午'
                }
            k: 返回数量

        Returns:
            上下文匹配的记忆列表
        """
        if not self.db_manager or not context:
            return {'memories': [], 'total_count': 0, 'strategy': self.strategy_name}

        logger.info(f"Contextual retrieval: context_features={list(context.keys())}")

        # 1. 提取上下文特征
        context_features = {
            'tags': context.get('tags', []),
            'environment': context.get('environment'),
            'task': context.get('task'),
            'mood': context.get('mood'),
            'time_of_day': context.get('time_of_day'),
            'location': context.get('location'),
            'people': context.get('people', [])
        }

        # 2. 获取候选记忆
        all_memories = self.db_manager.search_memories(limit=200)

        # 3. 计算上下文匹配度
        matched_memories = []
        for memory in all_memories:
            context_score = self._calculate_context_match(memory, context_features)

            if context_score > 0.3:  # 阈值过滤
                matched_features = self._get_matched_context_features(
                    memory,
                    context_features
                )

                # 计算最终置信度
                retrieval_confidence = context_score
                if hasattr(memory, 'importance'):
                    retrieval_confidence *= (0.7 + 0.3 * memory.importance)

                matched_memories.append({
                    'memory': memory.to_dict(),
                    'context_score': context_score,
                    'retrieval_confidence': retrieval_confidence,
                    'retrieval_method': 'contextual',
                    'matched_features': matched_features
                })

        # 4. 排序并返回top-k
        matched_memories.sort(key=lambda m: m['context_score'], reverse=True)

        logger.info(
            f"Contextual retrieval: {len(all_memories)} → {len(matched_memories)} memories"
        )

        return {
            'memories': matched_memories[:k],
            'total_count': len(matched_memories),
            'strategy': self.strategy_name,
            'context_used': context_features
        }

    def _calculate_context_match(
        self,
        memory,
        context_features: Dict[str, Any]
    ) -> float:
        """
        计算上下文匹配度

        Args:
            memory: 记忆对象
            context_features: 上下文特征

        Returns:
            匹配度分数 [0.0, 1.0]
        """
        memory_dict = memory.to_dict() if hasattr(memory, 'to_dict') else {}
        metadata = memory_dict.get('metadata', {})

        total_score = 0.0
        matched_count = 0
        total_features = 0

        # 1. 标签匹配 (权重: 0.3)
        if context_features.get('tags'):
            total_features += 1
            memory_tags = set(metadata.get('tags', []))
            context_tags = set(context_features['tags'])

            if memory_tags & context_tags:
                overlap_ratio = len(memory_tags & context_tags) / len(context_tags)
                total_score += 0.3 * overlap_ratio
                matched_count += 1

        # 2. 环境匹配 (权重: 0.2)
        if context_features.get('environment'):
            total_features += 1
            memory_env = metadata.get('environment')
            if memory_env == context_features['environment']:
                total_score += 0.2
                matched_count += 1

        # 3. 任务匹配 (权重: 0.2)
        if context_features.get('task'):
            total_features += 1
            memory_task = metadata.get('task')
            if memory_task == context_features['task']:
                total_score += 0.2
                matched_count += 1

        # 4. 情绪匹配 (权重: 0.15)
        if context_features.get('mood'):
            total_features += 1
            memory_mood = metadata.get('mood')
            if memory_mood == context_features['mood']:
                total_score += 0.15
                matched_count += 1

        # 5. 时段匹配 (权重: 0.1)
        if context_features.get('time_of_day'):
            total_features += 1
            memory_time = metadata.get('time_of_day')
            if memory_time == context_features['time_of_day']:
                total_score += 0.1
                matched_count += 1

        # 6. 地点匹配 (权重: 0.05)
        if context_features.get('location'):
            total_features += 1
            memory_location = metadata.get('location')
            if memory_location == context_features['location']:
                total_score += 0.05
                matched_count += 1

        return total_score

    def _get_matched_context_features(
        self,
        memory,
        context_features: Dict[str, Any]
    ) -> List[str]:
        """
        获取匹配的上下文特征列表

        Args:
            memory: 记忆对象
            context_features: 上下文特征

        Returns:
            匹配的特征名称列表
        """
        memory_dict = memory.to_dict() if hasattr(memory, 'to_dict') else {}
        metadata = memory_dict.get('metadata', {})

        matched_features = []

        # 检查每个特征
        if context_features.get('tags'):
            memory_tags = set(metadata.get('tags', []))
            context_tags = set(context_features['tags'])
            if memory_tags & context_tags:
                matched_features.append(f"tags: {list(memory_tags & context_tags)}")

        for feature_name in ['environment', 'task', 'mood', 'time_of_day', 'location']:
            if context_features.get(feature_name):
                memory_value = metadata.get(feature_name)
                if memory_value == context_features[feature_name]:
                    matched_features.append(f"{feature_name}: {memory_value}")

        return matched_features
