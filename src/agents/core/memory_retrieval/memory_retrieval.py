"""
Memory Retrieval Agent
记忆检索智能体 - 主编排器

这是一个基于策略模式的优雅记忆检索系统
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
import json
import time
from pathlib import Path
from datetime import datetime

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

    async def retrieve_multi_source(
        self,
        query: str,
        k: int = 10,
        strategy: str = "multi",
        brain_coordinator=None,
        enable_external_exploration: bool = False,
        use_cache: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        多源检索 + 外部探索兜底。

        优先尝试多策略检索；如果结果不足且允许，将触发EnvironmentAgent进行外部探索。
        """
        start_time = time.perf_counter()

        semantic_result = await self.retrieve(
            query=query,
            strategy="semantic",
            k=k,
            use_cache=use_cache,
            **kwargs
        )
        temporal_result = await self.retrieve(
            query=query,
            strategy="temporal",
            k=max(3, k // 2),
            use_cache=use_cache,
            **kwargs
        )

        if 'multi' in self.strategies:
            multi_result = await self.strategies['multi'].retrieve(
                query=query,
                k=k,
                strategy_names=[name for name in self.strategies.keys() if name != 'multi'],
                **kwargs
            )
        else:
            multi_result = {'memories': [], 'strategy': strategy, 'strategy_stats': {}}

        fused_memories = multi_result.get('memories', [])

        results: Dict[str, Any] = {
            'semantic': semantic_result.get('memories', []),
            'temporal': temporal_result.get('memories', []),
            'multi_fused': fused_memories,
            'strategy_stats': multi_result.get('strategy_stats', {}),
            'retrieval_strategy': multi_result.get('strategy', strategy),
        }

        # Use unique fused memories as the primary coverage signal; fall back to combined count.
        total_results = (
            self._count_unique_memories([fused_memories])
            if fused_memories
            else self._count_unique_memories([results['semantic'], results['temporal']])
        )

        exploration_triggered = False
        exploration_results: List[Dict[str, Any]] = []
        stored_count = 0

        if enable_external_exploration and self._detect_retrieval_insufficiency(total_results, k):
            exploration_triggered = True
            exploration_results, stored_count = await self._trigger_external_exploration(
                query=query,
                k=max(k, 5),
                brain_coordinator=brain_coordinator
            )

        results.update({
            'exploration': exploration_results,
            'exploration_triggered': exploration_triggered,
            'retrieval_time_ms': (time.perf_counter() - start_time) * 1000,
            'total_count': total_results + len(exploration_results),
            'storage_success': stored_count > 0
        })

        return results

    def _count_unique_memories(self, collections: List[List[Any]]) -> int:
        """Compute unique memory count across result collections."""
        seen = set()
        for collection in collections:
            for item in collection or []:
                mem = None
                if isinstance(item, dict):
                    mem = item.get('memory', item)
                else:
                    mem = getattr(item, 'memory', item)

                mem_id = None
                if isinstance(mem, dict):
                    mem_id = mem.get('id') or mem.get('memory_id') or mem.get('memoryId')
                else:
                    mem_id = getattr(mem, 'id', None) or getattr(mem, 'memory_id', None)

                seen.add(str(mem_id) if mem_id is not None else f"anon_{id(item)}")
        return len(seen)

    def _detect_retrieval_insufficiency(self, total_results: int, k: int) -> bool:
        """判断检索是否不足。"""
        # Trigger exploration unless we have strictly more than k solid candidates.
        return total_results <= max(1, k)

    async def _trigger_external_exploration(
        self,
        query: str,
        k: int,
        brain_coordinator=None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """触发外部探索，返回(探索结果列表, 成功写入数量)。"""
        start_time = time.perf_counter()
        exploration_results: List[Dict[str, Any]] = []
        stored = 0

        try:
            from src.agents.environment.environment_agent import EnvironmentAgent

            env_agent = getattr(brain_coordinator, 'environment_agent', None)
            if not env_agent:
                env_agent = EnvironmentAgent(brain_coordinator=brain_coordinator)

            exploration_response = await env_agent.explore_external(
                query=query,
                exploration_type="web_search",
                max_results=k
            )
            exploration_results = self._normalize_exploration_results(
                exploration_response,
                max_results=k
            )
        except Exception as e:
            logger.error(f"External exploration failed, using mock data: {e}")
            exploration_results = self._mock_exploration(query, k)

        if exploration_results:
            stored = await self._store_exploration_to_memory(
                query=query,
                exploration_results=exploration_results
            )

        duration_ms = (time.perf_counter() - start_time) * 1000
        self._log_exploration_event(
            query=query,
            exploration_results=exploration_results,
            stored_count=stored,
            duration_ms=duration_ms
        )

        return exploration_results, stored

    def _normalize_exploration_results(
        self,
        exploration_response: Any,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """将外部探索结果转换为统一的dict列表。"""
        if not exploration_response:
            return []

        raw_results = []
        source = 'external'

        if isinstance(exploration_response, dict):
            raw_results = exploration_response.get('results', [])
            source = exploration_response.get('source', 'external')
        elif isinstance(exploration_response, list):
            raw_results = exploration_response

        normalized: List[Dict[str, Any]] = []
        for item in raw_results[:max_results]:
            if hasattr(item, "to_dict"):
                item = item.to_dict()

            normalized.append({
                'title': item.get('title') or item.get('name') or item.get('content', '')[:50],
                'content': item.get('content') or item.get('snippet') or item.get('summary', ''),
                'source': item.get('source', source),
                'relevance': float(item.get('relevance', 0.6)),
                'url': item.get('url'),
                'metadata': item.get('metadata', {})
            })

        return normalized

    def _mock_exploration(self, query: str, k: int) -> List[Dict[str, Any]]:
        """在外部探索不可用时使用的兜底mock数据。"""
        return [
            {
                'title': f'External insight about {query}',
                'content': f'No indexed memories found. Mock insight for \"{query}\".',
                'source': 'mock_exploration',
                'relevance': 0.55,
                'metadata': {'mock': True}
            },
            {
                'title': 'Related background information',
                'content': f'General background related to \"{query}\".',
                'source': 'mock_exploration',
                'relevance': 0.5,
                'metadata': {'mock': True}
            }
        ][:max(1, min(k, 5))]

    async def _store_exploration_to_memory(
        self,
        query: str,
        exploration_results: List[Dict[str, Any]]
    ) -> int:
        """将外部探索结果写入记忆系统，返回成功写入数量。"""
        try:
            from src.memory.memory_system import memory_system
        except Exception as e:
            logger.error(f"Cannot store exploration results: {e}")
            return 0

        stored = 0
        for item in exploration_results:
            content = item.get('content') or item.get('title') or query
            metadata = dict(item.get('metadata', {}))
            metadata.update({
                'external_exploration': True,
                'source': item.get('source'),
                'original_query': query
            })

            try:
                memory_id = await memory_system.store_memory(
                    content=content,
                    memory_type='semantic',
                    importance=min(1.0, max(0.3, item.get('relevance', 0.5))),
                    metadata=metadata
                )
                if memory_id:
                    stored += 1
            except Exception as e:
                logger.warning(f"Failed to store exploration memory: {e}")

        return stored

    def _log_exploration_event(
        self,
        query: str,
        exploration_results: List[Dict[str, Any]],
        stored_count: int,
        duration_ms: float
    ) -> None:
        """将探索事件写入JSONL日志，便于集成测试验证。"""
        log_dir = Path("logs/exploration")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "external_exploration.jsonl"

        entry = {
            'event_type': 'external_exploration',
            'query': query,
            'result_count': len(exploration_results),
            'storage_success': stored_count > 0,
            'stored_count': stored_count,
            'duration_ms': duration_ms,
            'timestamp': datetime.now().isoformat(),
        }

        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log exploration event: {e}")
