"""
Multi-Strategy Retrieval
多策略编排器 - 组合多种检索策略的智能编排
"""

from .base import RetrievalStrategy
from typing import Dict, Any, List, Optional, Set
import logging

logger = logging.getLogger(__name__)


class MultiStrategyRetrieval(RetrievalStrategy):
    """
    多策略编排器

    功能:
    - 组合多种检索策略
    - 智能融合检索结果
    - 去重和排序
    - 根据场景自动选择策略组合

    应用场景:
    - 复杂查询需要多角度检索
    - 提高检索召回率
    - 综合多种相关性信号
    """

    def __init__(self, strategies: Dict[str, RetrievalStrategy], **kwargs):
        """
        初始化多策略编排器

        Args:
            strategies: 策略名称到策略实例的映射
                {
                    'semantic': semantic_strategy,
                    'temporal': temporal_strategy,
                    ...
                }
        """
        super().__init__(**kwargs)
        self.strategies = strategies

    @property
    def strategy_name(self) -> str:
        return "multi"

    async def retrieve(
        self,
        query: str,
        strategy_names: Optional[List[str]] = None,
        strategy_weights: Optional[Dict[str, float]] = None,
        k: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        多策略检索

        Args:
            query: 查询文本
            strategy_names: 要使用的策略名称列表 (None表示使用所有策略)
            strategy_weights: 策略权重字典 {'semantic': 0.6, 'temporal': 0.4}
            k: 返回数量
            **kwargs: 传递给各个策略的参数

        Returns:
            融合后的检索结果
        """
        if not self.strategies:
            return {'memories': [], 'total_count': 0, 'strategy': self.strategy_name}

        # 1. 确定要使用的策略
        if strategy_names is None:
            strategy_names = list(self.strategies.keys())

        # 2. 设置默认权重
        if strategy_weights is None:
            strategy_weights = self._get_default_weights(strategy_names)

        logger.info(
            f"Multi-strategy retrieval: strategies={strategy_names}, "
            f"weights={strategy_weights}"
        )

        # 3. 并行执行各个策略 (简化版: 顺序执行)
        all_results = {}
        for strategy_name in strategy_names:
            if strategy_name not in self.strategies:
                logger.warning(f"Strategy '{strategy_name}' not found, skipping")
                continue

            strategy = self.strategies[strategy_name]

            try:
                # 调用对应策略的retrieve方法
                result = await self._call_strategy(
                    strategy,
                    strategy_name,
                    query,
                    k * 2,  # 获取更多候选以便融合
                    **kwargs
                )

                all_results[strategy_name] = result

            except Exception as e:
                logger.error(f"Strategy '{strategy_name}' failed: {e}")
                continue

        # 4. 融合结果
        fused_memories = self._fuse_results(
            all_results,
            strategy_weights,
            k
        )

        # 5. 计算统计信息
        strategy_stats = {
            name: result.get('total_count', 0)
            for name, result in all_results.items()
        }

        return {
            'memories': fused_memories,
            'total_count': len(fused_memories),
            'strategy': self.strategy_name,
            'strategies_used': strategy_names,
            'strategy_weights': strategy_weights,
            'strategy_stats': strategy_stats
        }

    async def _call_strategy(
        self,
        strategy: RetrievalStrategy,
        strategy_name: str,
        query: str,
        k: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        调用单个策略

        根据策略类型选择合适的参数
        """
        # 根据策略类型传递不同参数
        if strategy_name == 'semantic':
            return await strategy.retrieve(query=query, k=k, **kwargs)

        elif strategy_name == 'temporal':
            # 时间检索可能需要time_range参数
            return await strategy.retrieve(query=query, k=k, **kwargs)

        elif strategy_name == 'episodic':
            # 情节检索需要cues参数
            cues = kwargs.get('cues', {})
            return await strategy.retrieve(cues=cues, k=k, **kwargs)

        elif strategy_name == 'associative':
            # 关联检索需要memory_id参数
            memory_id = kwargs.get('memory_id', '')
            if memory_id:
                return await strategy.retrieve(memory_id=memory_id, k=k, **kwargs)
            return {'memories': [], 'total_count': 0, 'strategy': strategy_name}

        elif strategy_name == 'pattern':
            # 模式补全需要partial_cue
            return await strategy.retrieve(partial_cue=query, k=k, **kwargs)

        elif strategy_name == 'contextual':
            # 上下文检索需要context参数
            context = kwargs.get('context', {})
            return await strategy.retrieve(context=context, k=k, **kwargs)

        else:
            # 默认传递query
            return await strategy.retrieve(query=query, k=k, **kwargs)

    def _get_default_weights(self, strategy_names: List[str]) -> Dict[str, float]:
        """
        获取默认策略权重

        根据策略组合智能设置权重
        """
        # 预定义的权重方案
        weight_schemes = {
            # 单策略
            ('semantic',): {'semantic': 1.0},
            ('temporal',): {'temporal': 1.0},

            # 双策略组合
            ('semantic', 'temporal'): {'semantic': 0.7, 'temporal': 0.3},
            ('semantic', 'episodic'): {'semantic': 0.7, 'episodic': 0.3},
            ('semantic', 'contextual'): {'semantic': 0.6, 'contextual': 0.4},

            # 三策略组合
            ('semantic', 'temporal', 'episodic'): {
                'semantic': 0.5,
                'temporal': 0.3,
                'episodic': 0.2
            },
        }

        # 尝试匹配预定义方案
        key = tuple(sorted(strategy_names))
        if key in weight_schemes:
            return weight_schemes[key]

        # 默认: 均匀分配
        weight = 1.0 / len(strategy_names)
        return {name: weight for name in strategy_names}

    def _fuse_results(
        self,
        all_results: Dict[str, Dict[str, Any]],
        strategy_weights: Dict[str, float],
        k: int
    ) -> List[Dict[str, Any]]:
        """
        融合多个策略的检索结果

        策略:
        1. 去重 (基于memory_id)
        2. 加权得分计算
        3. 排序并返回top-k

        Args:
            all_results: 各策略的检索结果
            strategy_weights: 策略权重
            k: 返回数量

        Returns:
            融合后的记忆列表
        """
        # 使用字典去重 {memory_id: memory_info}
        memory_map: Dict[str, Dict[str, Any]] = {}

        # 1. 遍历所有策略的结果
        for strategy_name, result in all_results.items():
            memories = result.get('memories', [])
            weight = strategy_weights.get(strategy_name, 0.0)

            for mem_item in memories:
                memory = mem_item.get('memory', {})
                memory_id = memory.get('id', memory.get('memory_id'))

                if not memory_id:
                    continue

                # 2. 计算加权分数
                # 从各个策略结果中提取置信度/分数
                confidence = mem_item.get('retrieval_confidence', 0.0)
                weighted_score = confidence * weight

                # 3. 合并记忆
                if memory_id in memory_map:
                    # 已存在: 累加分数
                    memory_map[memory_id]['fused_score'] += weighted_score
                    memory_map[memory_id]['strategies'].append(strategy_name)
                    memory_map[memory_id]['strategy_scores'][strategy_name] = confidence
                else:
                    # 新记忆: 创建条目
                    memory_map[memory_id] = {
                        'memory': memory,
                        'fused_score': weighted_score,
                        'strategies': [strategy_name],
                        'strategy_scores': {strategy_name: confidence},
                        'retrieval_method': 'multi',
                        'retrieval_confidence': weighted_score
                    }

        # 4. 转为列表并排序
        fused_memories = list(memory_map.values())
        fused_memories.sort(key=lambda m: m['fused_score'], reverse=True)

        # 5. 更新最终置信度为融合分数
        for mem in fused_memories:
            mem['retrieval_confidence'] = mem['fused_score']

        logger.info(
            f"Fused {len(memory_map)} unique memories from "
            f"{len(all_results)} strategies"
        )

        return fused_memories[:k]
