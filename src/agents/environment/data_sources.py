"""
External Data Source Abstraction for EnvironmentAgent
外部数据源抽象 - 支持可插拔的多种数据源

Design Pattern: Strategy Pattern + Factory Pattern
- 抽象基类定义数据源接口
- 具体实现类处理不同数据源（Web Search、Knowledge Base、Database等）
- 配置系统支持动态注册和选择数据源
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    """数据源类型"""
    WEB_SEARCH = "web_search"
    KNOWLEDGE_BASE = "knowledge_base"
    DATABASE = "database"
    API_SERVICE = "api_service"
    FILE_SYSTEM = "file_system"
    MOCK = "mock"


class DataSourcePriority(Enum):
    """数据源优先级"""
    HIGH = 3
    MEDIUM = 2
    LOW = 1


@dataclass
class ExplorationQuery:
    """探索查询参数"""
    query: str
    query_type: Optional[str] = None  # "factual", "procedural", "temporal", etc.
    language: str = "en"
    max_results: int = 5
    time_constraint: Optional[Dict[str, Any]] = None
    domain_filter: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExplorationResult:
    """探索结果"""
    result_id: str
    title: str
    content: str
    source: str
    source_type: DataSourceType
    relevance: float  # 0.0 - 1.0
    timestamp: datetime
    url: Optional[str] = None
    author: Optional[str] = None
    confidence: float = 0.7
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'result_id': self.result_id,
            'title': self.title,
            'content': self.content,
            'source': self.source,
            'source_type': self.source_type.value,
            'relevance': self.relevance,
            'timestamp': self.timestamp.isoformat(),
            'url': self.url,
            'author': self.author,
            'confidence': self.confidence,
            'metadata': self.metadata
        }


class DataSource(ABC):
    """
    数据源抽象基类

    所有外部数据源必须实现此接口
    """

    def __init__(
        self,
        source_name: str,
        source_type: DataSourceType,
        priority: DataSourcePriority = DataSourcePriority.MEDIUM,
        config: Optional[Dict[str, Any]] = None
    ):
        self.source_name = source_name
        self.source_type = source_type
        self.priority = priority
        self.config = config or {}
        self.is_available = True
        self.last_error: Optional[str] = None
        self.request_count = 0
        self.success_count = 0
        self.failure_count = 0

    @abstractmethod
    async def search(self, query: ExplorationQuery) -> List[ExplorationResult]:
        """
        执行搜索

        Args:
            query: 探索查询参数

        Returns:
            List[ExplorationResult]: 搜索结果列表
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        健康检查 - 验证数据源是否可用

        Returns:
            bool: True表示可用
        """
        pass

    def update_statistics(self, success: bool):
        """更新统计信息"""
        self.request_count += 1
        if success:
            self.success_count += 1
            self.last_error = None
        else:
            self.failure_count += 1

    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.request_count == 0:
            return 0.0
        return self.success_count / self.request_count

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'source_name': self.source_name,
            'source_type': self.source_type.value,
            'priority': self.priority.value,
            'is_available': self.is_available,
            'request_count': self.request_count,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'success_rate': self.get_success_rate(),
            'last_error': self.last_error
        }


class MockDataSource(DataSource):
    """
    Mock数据源 - 用于测试和演示
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            source_name="MockDataSource",
            source_type=DataSourceType.MOCK,
            priority=DataSourcePriority.LOW,
            config=config
        )

        # Mock数据库
        self.mock_database = {
            'weather': [
                {'title': 'Current Weather Report', 'content': 'Today is sunny with temperature 22°C. Light breeze from the northeast.', 'relevance': 0.95},
                {'title': 'Weather Forecast', 'content': 'Tomorrow will be cloudy with possible rain in the afternoon. Temperature around 18°C.', 'relevance': 0.85}
            ],
            'technology': [
                {'title': 'AI Advances in 2025', 'content': 'Recent breakthroughs in large language models show significant improvements in reasoning and factuality.', 'relevance': 0.92},
                {'title': 'Neural Network Evolution', 'content': 'Deep learning architectures continue to evolve with new attention mechanisms and efficient transformers.', 'relevance': 0.88}
            ],
            'history': [
                {'title': 'Historical Events Timeline', 'content': 'Important events from the past century including technological revolutions and social movements.', 'relevance': 0.90},
                {'title': 'Ancient Civilizations', 'content': 'Overview of major ancient civilizations and their contributions to modern society.', 'relevance': 0.82}
            ],
            'science': [
                {'title': 'Quantum Physics Discoveries', 'content': 'Recent findings in quantum physics reveal new insights into entanglement and superposition.', 'relevance': 0.93},
                {'title': 'Climate Research Update', 'content': 'Latest study on climate change effects shows accelerated ice melting in polar regions.', 'relevance': 0.87}
            ],
            'general': [
                {'title': 'General Knowledge', 'content': 'Comprehensive information covering various topics and domains.', 'relevance': 0.75},
                {'title': 'Encyclopedia Entry', 'content': 'Detailed encyclopedia entry with cross-references and citations.', 'relevance': 0.70}
            ]
        }

    async def search(self, query: ExplorationQuery) -> List[ExplorationResult]:
        """执行Mock搜索"""
        try:
            # 模拟网络延迟
            await asyncio.sleep(0.05)

            query_lower = query.query.lower()
            results = []

            # 关键词匹配
            matched = False
            for category, items in self.mock_database.items():
                if category in query_lower:
                    matched = True
                    for item in items[:query.max_results]:
                        results.append(ExplorationResult(
                            result_id=f"mock_{category}_{len(results)}",
                            title=item['title'],
                            content=item['content'],
                            source=self.source_name,
                            source_type=self.source_type,
                            relevance=item['relevance'],
                            timestamp=datetime.now(),
                            url=f"https://mock.example.com/{category}/{len(results)}",
                            confidence=0.8
                        ))

            # 如果没有匹配到特定类别，返回通用结果
            if not matched:
                for item in self.mock_database['general'][:query.max_results]:
                    results.append(ExplorationResult(
                        result_id=f"mock_general_{len(results)}",
                        title=f"{item['title']} for: {query.query}",
                        content=f"Mock external information related to '{query.query}'. {item['content']}",
                        source=self.source_name,
                        source_type=self.source_type,
                        relevance=item['relevance'],
                        timestamp=datetime.now(),
                        url=f"https://mock.example.com/general/{len(results)}",
                        confidence=0.7
                    ))

            self.update_statistics(success=True)
            return results

        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            self.last_error = str(e)
            self.update_statistics(success=False)
            logger.error(f"MockDataSource search failed: {e}")
            return []

    async def health_check(self) -> bool:
        """健康检查"""
        return True


class WebSearchDataSource(DataSource):
    """
    Web搜索数据源 - 真实的网络搜索API集成

    支持的搜索引擎:
    - Google Custom Search API
    - Bing Web Search API
    - DuckDuckGo API
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            source_name="WebSearchAPI",
            source_type=DataSourceType.WEB_SEARCH,
            priority=DataSourcePriority.HIGH,
            config=config
        )

        # API配置
        self.api_key = self.config.get('api_key')
        self.search_engine = self.config.get('search_engine', 'google')  # 'google', 'bing', 'duckduckgo'
        self.custom_search_engine_id = self.config.get('custom_search_engine_id')  # For Google

        # 验证配置
        if self.search_engine == 'google' and (not self.api_key or not self.custom_search_engine_id):
            logger.warning("Google Custom Search API key or Search Engine ID not configured")
            self.is_available = False

    async def search(self, query: ExplorationQuery) -> List[ExplorationResult]:
        """执行Web搜索"""
        if not self.is_available:
            logger.warning("WebSearchDataSource is not available")
            return []

        try:
            if self.search_engine == 'google':
                return await self._search_google(query)
            elif self.search_engine == 'bing':
                return await self._search_bing(query)
            elif self.search_engine == 'duckduckgo':
                return await self._search_duckduckgo(query)
            else:
                logger.error(f"Unsupported search engine: {self.search_engine}")
                return []

        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            self.last_error = str(e)
            self.update_statistics(success=False)
            logger.error(f"WebSearchDataSource search failed: {e}")
            return []

    async def _search_google(self, query: ExplorationQuery) -> List[ExplorationResult]:
        """Google Custom Search API"""
        try:
            import aiohttp

            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': self.api_key,
                'cx': self.custom_search_engine_id,
                'q': query.query,
                'num': min(query.max_results, 10)
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []

                        for item in data.get('items', []):
                            results.append(ExplorationResult(
                                result_id=item.get('cacheId', f"google_{len(results)}"),
                                title=item.get('title', 'No Title'),
                                content=item.get('snippet', 'No content'),
                                source='Google',
                                source_type=self.source_type,
                                relevance=0.85,
                                timestamp=datetime.now(),
                                url=item.get('link'),
                                confidence=0.9,
                                metadata={'formattedUrl': item.get('formattedUrl')}
                            ))

                        self.update_statistics(success=True)
                        return results
                    else:
                        logger.error(f"Google Search API error: {response.status}")
                        self.update_statistics(success=False)
                        return []

        except (asyncio.TimeoutError) as e:
            logger.error(f"Google Search failed: {e}")
            self.update_statistics(success=False)
            return []

    async def _search_bing(self, query: ExplorationQuery) -> List[ExplorationResult]:
        """Bing Web Search API"""
        try:
            import aiohttp

            url = "https://api.bing.microsoft.com/v7.0/search"
            headers = {'Ocp-Apim-Subscription-Key': self.api_key}
            params = {
                'q': query.query,
                'count': query.max_results
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []

                        for item in data.get('webPages', {}).get('value', []):
                            results.append(ExplorationResult(
                                result_id=item.get('id', f"bing_{len(results)}"),
                                title=item.get('name', 'No Title'),
                                content=item.get('snippet', 'No content'),
                                source='Bing',
                                source_type=self.source_type,
                                relevance=0.85,
                                timestamp=datetime.now(),
                                url=item.get('url'),
                                confidence=0.9,
                                metadata={'displayUrl': item.get('displayUrl')}
                            ))

                        self.update_statistics(success=True)
                        return results
                    else:
                        logger.error(f"Bing Search API error: {response.status}")
                        self.update_statistics(success=False)
                        return []

        except (asyncio.TimeoutError) as e:
            logger.error(f"Bing Search failed: {e}")
            self.update_statistics(success=False)
            return []

    async def _search_duckduckgo(self, query: ExplorationQuery) -> List[ExplorationResult]:
        """DuckDuckGo API (使用第三方库)"""
        try:
            # 注意: DuckDuckGo不提供官方API，这里使用duckduckgo_search库
            # pip install duckduckgo-search
            from duckduckgo_search import AsyncDDGS

            results = []
            async with AsyncDDGS() as ddgs:
                search_results = await ddgs.text(
                    query.query,
                    max_results=query.max_results
                )

                for i, item in enumerate(search_results):
                    results.append(ExplorationResult(
                        result_id=f"ddg_{i}",
                        title=item.get('title', 'No Title'),
                        content=item.get('body', 'No content'),
                        source='DuckDuckGo',
                        source_type=self.source_type,
                        relevance=0.80,
                        timestamp=datetime.now(),
                        url=item.get('href'),
                        confidence=0.85
                    ))

            self.update_statistics(success=True)
            return results

        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            logger.error(f"DuckDuckGo Search failed: {e}")
            self.update_statistics(success=False)
            return []

    async def health_check(self) -> bool:
        """健康检查"""
        if not self.api_key:
            return False

        try:
            # 简单的测试查询
            test_query = ExplorationQuery(query="test", max_results=1)
            results = await self.search(test_query)
            return len(results) > 0
        except Exception as e:
            logger.debug(f"Availability check failed: {e}")
            return False


class KnowledgeBaseDataSource(DataSource):
    """
    知识库数据源 - Wikipedia, Wikidata等
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            source_name="KnowledgeBase",
            source_type=DataSourceType.KNOWLEDGE_BASE,
            priority=DataSourcePriority.MEDIUM,
            config=config
        )

        self.kb_type = self.config.get('kb_type', 'wikipedia')  # 'wikipedia', 'wikidata'

    async def search(self, query: ExplorationQuery) -> List[ExplorationResult]:
        """执行知识库搜索"""
        try:
            if self.kb_type == 'wikipedia':
                return await self._search_wikipedia(query)
            elif self.kb_type == 'wikidata':
                return await self._search_wikidata(query)
            else:
                logger.error(f"Unsupported KB type: {self.kb_type}")
                return []

        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            self.last_error = str(e)
            self.update_statistics(success=False)
            logger.error(f"KnowledgeBaseDataSource search failed: {e}")
            return []

    async def _search_wikipedia(self, query: ExplorationQuery) -> List[ExplorationResult]:
        """Wikipedia搜索"""
        try:
            import aiohttp

            # Wikipedia Search API
            url = "https://en.wikipedia.org/w/api.php"
            params = {
                'action': 'query',
                'list': 'search',
                'srsearch': query.query,
                'srlimit': query.max_results,
                'format': 'json'
            }

            results = []
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()

                        for item in data.get('query', {}).get('search', []):
                            # 获取文章摘要
                            summary = item.get('snippet', 'No content').replace('<span class="searchmatch">', '').replace('</span>', '')

                            results.append(ExplorationResult(
                                result_id=f"wiki_{item.get('pageid')}",
                                title=item.get('title', 'No Title'),
                                content=summary,
                                source='Wikipedia',
                                source_type=self.source_type,
                                relevance=0.90,
                                timestamp=datetime.now(),
                                url=f"https://en.wikipedia.org/?curid={item.get('pageid')}",
                                confidence=0.95,
                                metadata={'pageid': item.get('pageid'), 'wordcount': item.get('wordcount')}
                            ))

                        self.update_statistics(success=True)
                        return results

        except (asyncio.TimeoutError) as e:
            logger.error(f"Wikipedia search failed: {e}")
            self.update_statistics(success=False)
            return []

    async def _search_wikidata(self, query: ExplorationQuery) -> List[ExplorationResult]:
        """Wikidata搜索 (TODO: 实现)"""
        return []

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            test_query = ExplorationQuery(query="test", max_results=1)
            results = await self.search(test_query)
            return len(results) > 0
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False


# ========== Data Source Registry ==========

class DataSourceRegistry:
    """
    数据源注册中心

    管理所有可用的数据源，支持动态注册和选择
    """

    def __init__(self):
        self.data_sources: Dict[str, DataSource] = {}
        self.default_source: Optional[str] = None

    def register(self, source: DataSource, set_as_default: bool = False):
        """
        注册数据源

        Args:
            source: 数据源实例
            set_as_default: 是否设置为默认数据源
        """
        self.data_sources[source.source_name] = source

        if set_as_default or self.default_source is None:
            self.default_source = source.source_name

    def unregister(self, source_name: str):
        """注销数据源"""
        if source_name in self.data_sources:
            del self.data_sources[source_name]

            if self.default_source == source_name:
                self.default_source = list(self.data_sources.keys())[0] if self.data_sources else None

    def get_source(self, source_name: str) -> Optional[DataSource]:
        """获取指定数据源"""
        return self.data_sources.get(source_name)

    def get_default_source(self) -> Optional[DataSource]:
        """获取默认数据源"""
        if self.default_source:
            return self.data_sources.get(self.default_source)
        return None

    def get_all_sources(self) -> List[DataSource]:
        """获取所有数据源"""
        return list(self.data_sources.values())

    def get_available_sources(self) -> List[DataSource]:
        """获取所有可用的数据源"""
        return [source for source in self.data_sources.values() if source.is_available]

    def get_sources_by_priority(self, priority: DataSourcePriority) -> List[DataSource]:
        """根据优先级获取数据源"""
        return [source for source in self.data_sources.values() if source.priority == priority]

    async def health_check_all(self) -> Dict[str, bool]:
        """对所有数据源进行健康检查"""
        results = {}
        for name, source in self.data_sources.items():
            is_healthy = await source.health_check()
            source.is_available = is_healthy
            results[name] = is_healthy
        return results

    def get_statistics(self) -> Dict[str, Any]:
        """获取所有数据源的统计信息"""
        return {
            'total_sources': len(self.data_sources),
            'available_sources': len(self.get_available_sources()),
            'default_source': self.default_source,
            'sources': [source.get_statistics() for source in self.data_sources.values()]
        }


# ========== Global Registry Instance ==========

# 全局数据源注册中心实例
data_source_registry = DataSourceRegistry()


def initialize_default_sources(config: Optional[Dict[str, Any]] = None):
    """
    初始化默认数据源

    Args:
        config: 配置字典
    """
    config = config or {}

    # 1. 注册Mock数据源 (总是可用，用于测试)
    mock_source = MockDataSource(config=config.get('mock', {}))
    data_source_registry.register(mock_source, set_as_default=True)

    # 2. 注册Web搜索数据源 (如果配置了API Key)
    web_config = config.get('web_search', {})
    if web_config.get('api_key'):
        web_source = WebSearchDataSource(config=web_config)
        data_source_registry.register(web_source, set_as_default=True)

    # 3. 注册知识库数据源
    kb_config = config.get('knowledge_base', {})
    kb_source = KnowledgeBaseDataSource(config=kb_config)
    data_source_registry.register(kb_source)

