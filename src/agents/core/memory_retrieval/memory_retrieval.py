"""
Memory Retrieval Agent
记忆检索智能体 - 主编排器

这是一个基于策略模式的优雅记忆检索系统
"""

from typing import Dict, Any, List, Optional
import logging

from .data_models import RetrievalRequest, RetrievalResult, CacheKey
from .cache.lru_cache_manager import LRUCacheManager
from .confidence.confidence_calculator import ConfidenceCalculator
from .strategies.base import RetrievalStrategy
from .strategies.semantic_retrieval import SemanticRetrievalStrategy
from .strategies.temporal_retrieval import TemporalRetrievalStrategy
from .strategies.episodic_retrieval import EpisodicRetrievalStrategy
from .strategies.associative_retrieval import AssociativeRetrievalStrategy
from .strategies.pattern_completion import PatternCompletionStrategy
from .strategies.contextual_retrieval import ContextualRetrievalStrategy
from .strategies.multi_strategy import MultiStrategyRetrieval

logger = logging.getLogger(__name__)


class MemoryRetrievalAgent:
    """
    记忆检索智能体 - 主编排器

    职责:
    - 统一的检索接口
    - 策略选择和调度
    - 缓存管理
    - 置信度计算
    - 结果后处理

    设计模式:
    - Facade Pattern: 提供统一的检索接口
    - Strategy Pattern: 可插拔的检索策略
    - Dependency Injection: 低耦合设计
    """

    def __init__(
        self,
        db_manager=None,
        embedding_service=None,
        vector_db=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化记忆检索智能体

        Args:
            db_manager: 数据库管理器
            embedding_service: 嵌入服务
            vector_db: 向量数据库
            config: 配置参数
        """
        self.db_manager = db_manager
        self.embedding_service = embedding_service
        self.vector_db = vector_db
        self.config = config or {}

        # 初始化组件
        self.cache = LRUCacheManager(
            max_size=self.config.get('cache_size', 200)
        )
        self.confidence_calculator = ConfidenceCalculator(
            config=self.config.get('confidence', {})
        )

        # 初始化所有检索策略
        self.strategies = self._initialize_strategies()

        logger.info(
            f"MemoryRetrievalAgent initialized with "
            f"{len(self.strategies)} strategies"
        )

    def _initialize_strategies(self) -> Dict[str, RetrievalStrategy]:
        """
        初始化所有检索策略

        Returns:
            策略名称到策略实例的映射
        """
        # 共享的依赖
        deps = {
            'db_manager': self.db_manager,
            'embedding_service': self.embedding_service,
            'vector_db': self.vector_db
        }

        # 创建各个策略实例
        strategies = {
            'semantic': SemanticRetrievalStrategy(**deps),
            'temporal': TemporalRetrievalStrategy(**deps),
            'episodic': EpisodicRetrievalStrategy(**deps),
            'associative': AssociativeRetrievalStrategy(**deps),
            'pattern': PatternCompletionStrategy(**deps),
            'contextual': ContextualRetrievalStrategy(**deps),
        }

        # 多策略编排器需要访问其他策略
        strategies['multi'] = MultiStrategyRetrieval(
            strategies=strategies,
            **deps
        )

        return strategies

    async def retrieve(
        self,
        query: str,
        strategy: str = "semantic",
        k: int = 10,
        use_cache: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        统一的记忆检索接口

        Args:
            query: 查询文本
            strategy: 检索策略 ('semantic', 'temporal', 'episodic', etc.)
            k: 返回数量
            use_cache: 是否使用缓存
            **kwargs: 传递给策略的额外参数

        Returns:
            检索结果字典
            {
                'memories': [...],
                'total_count': 10,
                'strategy': 'semantic',
                'cache_hit': False,
                'execution_time': 0.05
            }
        """
        import time
        start_time = time.time()

        # 1. 尝试从缓存获取
        cache_key = None
        if use_cache:
            cache_key = CacheKey(
                strategy=strategy,
                query=query,
                params={'k': k, **kwargs}
            ).to_string()

            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for query: {query[:50]}...")
                cached_result['cache_hit'] = True
                cached_result['execution_time'] = time.time() - start_time
                return cached_result

        # 2. 选择并执行检索策略
        if strategy not in self.strategies:
            logger.warning(
                f"Unknown strategy '{strategy}', falling back to 'semantic'"
            )
            strategy = 'semantic'

        retrieval_strategy = self.strategies[strategy]

        try:
            # 执行检索
            result = await retrieval_strategy.retrieve(
                query=query,
                k=k,
                **kwargs
            )

            # 3. 后处理
            result = self._post_process(result, strategy, **kwargs)

            # 4. 缓存结果
            if use_cache and cache_key:
                self.cache.put(cache_key, result)

            # 5. 添加元信息
            result['cache_hit'] = False
            result['execution_time'] = time.time() - start_time

            logger.info(
                f"Retrieved {result.get('total_count', 0)} memories "
                f"in {result['execution_time']:.3f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Retrieval failed: {e}", exc_info=True)
            return {
                'memories': [],
                'total_count': 0,
                'strategy': strategy,
                'error': str(e),
                'cache_hit': False,
                'execution_time': time.time() - start_time
            }

    def _post_process(
        self,
        result: Dict[str, Any],
        strategy: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        后处理检索结果

        职责:
        - 统一置信度计算
        - 结果排序
        - 添加额外元信息
        """
        memories = result.get('memories', [])

        # 1. 批量计算/更新置信度
        # (各策略已经计算了retrieval_confidence, 这里可以选择性重新计算)
        if self.config.get('recalculate_confidence', False):
            memories = self.confidence_calculator.batch_calculate(
                memories,
                strategy,
                **kwargs
            )

        # 2. 最终排序
        memories.sort(
            key=lambda m: m.get('retrieval_confidence', 0.0),
            reverse=True
        )

        result['memories'] = memories
        return result

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            缓存统计字典
        """
        return self.cache.get_stats()

    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        logger.info("Cache cleared")

    def get_available_strategies(self) -> List[str]:
        """
        获取可用的检索策略列表

        Returns:
            策略名称列表
        """
        return list(self.strategies.keys())
