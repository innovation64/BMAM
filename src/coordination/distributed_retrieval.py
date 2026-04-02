"""
FIX-016: 五脑区分布式检索协调器
Distributed Retrieval Coordinator for Five Brain Regions

设计原则:
1. 每个脑区维护独立存储，符合人脑模块化设计
2. 检索时并行查询所有脑区，聚合结果
3. 每条记忆带有来源脑区标签，支持类型权重调整

架构:
┌─────────────────────────────────────────────────────────────────┐
│              DistributedRetrievalCoordinator                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Hippocampus │  │ Temporal    │  │ Amygdala    │              │
│  │ Retriever   │  │ Lobe        │  │ Retriever   │              │
│  │ (episodic)  │  │ Retriever   │  │ (emotional) │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐                               │
│  │ Prefrontal  │  │ Basal       │                               │
│  │ Retriever   │  │ Ganglia     │                               │
│  │ (working)   │  │ Retriever   │                               │
│  └─────────────┘  └─────────────┘                               │
├─────────────────────────────────────────────────────────────────┤
│  retrieve(query) → parallel query → merge → rank → return       │
└─────────────────────────────────────────────────────────────────┘
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Protocol
from enum import Enum

logger = logging.getLogger(__name__)


class BrainRegion(Enum):
    """五脑区枚举"""
    HIPPOCAMPUS = "hippocampus"      # 海马体 - 情景记忆
    TEMPORAL_LOBE = "temporal_lobe"  # 颞叶 - 语义记忆
    AMYGDALA = "amygdala"            # 杏仁核 - 情感记忆
    PREFRONTAL = "prefrontal"        # 前额叶 - 工作记忆
    BASAL_GANGLIA = "basal_ganglia"  # 基底节 - 程序记忆


@dataclass
class DistributedMemory:
    """分布式记忆项 - 带有来源脑区标签"""
    id: str
    content: str
    source_region: BrainRegion
    relevance: float = 0.0
    memory_type: str = ""  # episodic, semantic, emotional, working, procedural
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'content': self.content,
            'source_region': self.source_region.value,
            'relevance': self.relevance,
            'memory_type': self.memory_type,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'metadata': self.metadata
        }


class BrainRegionRetriever(ABC):
    """
    脑区检索器抽象基类
    每个脑区需要实现自己的检索逻辑
    """

    @property
    @abstractmethod
    def region(self) -> BrainRegion:
        """返回脑区类型"""
        pass

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        k: int = 5,
        context: Optional[Dict[str, Any]] = None
    ) -> List[DistributedMemory]:
        """
        从该脑区检索相关记忆

        Args:
            query: 查询文本
            k: 返回记忆数量
            context: 上下文信息

        Returns:
            DistributedMemory 列表
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查该脑区是否可用"""
        pass


# ============== 五脑区检索器实现 ==============

class HippocampusRetriever(BrainRegionRetriever):
    """海马体检索器 - 情景记忆"""

    def __init__(self, hippocampus_agent=None):
        self.hippocampus = hippocampus_agent

    @property
    def region(self) -> BrainRegion:
        return BrainRegion.HIPPOCAMPUS

    async def retrieve(
        self,
        query: str,
        k: int = 5,
        context: Optional[Dict[str, Any]] = None
    ) -> List[DistributedMemory]:
        if not self.hippocampus:
            return []

        try:
            memories = []
            user_id = (context or {}).get('user_id')

            # 方法1: 使用 memory_store.search_memories (KeyValueMemoryStore)
            if hasattr(self.hippocampus, 'memory_store') and self.hippocampus.memory_store:
                store = self.hippocampus.memory_store
                if hasattr(store, 'search_memories'):
                    memories = await store.search_memories(query, k=k)
                elif hasattr(store, 'get_all_memories'):
                    # 降级：关键词匹配
                    all_mems = store.get_all_memories() if callable(getattr(store, 'get_all_memories', None)) else []
                    query_lower = query.lower()
                    for mem in all_mems:
                        content = mem.get('content', '') if isinstance(mem, dict) else str(mem)
                        if any(word in content.lower() for word in query_lower.split() if len(word) > 3):
                            memories.append(mem if isinstance(mem, dict) else {'content': content})

            # 方法2: 使用 storage_adapter
            if not memories and hasattr(self.hippocampus, 'storage_adapter'):
                adapter = self.hippocampus.storage_adapter
                if hasattr(adapter, 'search'):
                    memories = await adapter.search(query, k=k) if asyncio.iscoroutinefunction(adapter.search) else adapter.search(query, k=k)

            results = []
            for mem in memories[:k]:
                if isinstance(mem, dict):
                    # 🔥 P0: user_id 隔离过滤
                    if user_id:
                        mem_meta = mem.get('metadata', {}) or {}
                        mem_uid = mem_meta.get('user_id', 'default')
                        if mem_uid != user_id and mem_uid != 'default':
                            continue
                    results.append(DistributedMemory(
                        id=mem.get('id', ''),
                        content=mem.get('content', ''),
                        source_region=BrainRegion.HIPPOCAMPUS,
                        relevance=mem.get('relevance', mem.get('score', 0.5)),
                        memory_type='episodic',
                        timestamp=mem.get('timestamp'),
                        metadata=mem.get('metadata', {})
                    ))
            return results
        except Exception as e:
            logger.warning(f"Hippocampus retrieval failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []

    def is_available(self) -> bool:
        return self.hippocampus is not None


class TemporalLobeRetriever(BrainRegionRetriever):
    """颞叶检索器 - 语义记忆 + 知识图谱"""

    def __init__(self, temporal_lobe_agent=None, knowledge_graph=None):
        self.temporal_lobe = temporal_lobe_agent
        self.kg = knowledge_graph

    @property
    def region(self) -> BrainRegion:
        return BrainRegion.TEMPORAL_LOBE

    async def retrieve(
        self,
        query: str,
        k: int = 5,
        context: Optional[Dict[str, Any]] = None
    ) -> List[DistributedMemory]:
        results = []

        # 1. 从颞叶语义记忆检索
        if self.temporal_lobe and hasattr(self.temporal_lobe, 'memories'):
            query_lower = query.lower()
            for mem in self.temporal_lobe.memories:
                content = getattr(mem, 'content', str(mem))
                if any(word in content.lower() for word in query_lower.split() if len(word) > 3):
                    results.append(DistributedMemory(
                        id=getattr(mem, 'id', str(id(mem))),
                        content=content,
                        source_region=BrainRegion.TEMPORAL_LOBE,
                        relevance=0.6,
                        memory_type='semantic',
                        metadata={'category': getattr(mem, 'category', 'general')}
                    ))

        # 2. 从知识图谱检索
        if self.kg and hasattr(self.kg, 'query'):
            try:
                kg_results = self.kg.query(query, k=k)
                for fact in kg_results:
                    results.append(DistributedMemory(
                        id=f"kg_{hash(str(fact))}",
                        content=str(fact) if isinstance(fact, str) else fact.get('content', str(fact)),
                        source_region=BrainRegion.TEMPORAL_LOBE,
                        relevance=fact.get('score', 0.7) if isinstance(fact, dict) else 0.7,
                        memory_type='semantic_kg',
                        metadata={'source': 'knowledge_graph'}
                    ))
            except Exception as e:
                logger.debug(f"KG retrieval failed: {e}")

        return results[:k]

    def is_available(self) -> bool:
        return self.temporal_lobe is not None or self.kg is not None


class AmygdalaRetriever(BrainRegionRetriever):
    """杏仁核检索器 - 情感记忆"""

    def __init__(self, amygdala_agent=None):
        self.amygdala = amygdala_agent

    @property
    def region(self) -> BrainRegion:
        return BrainRegion.AMYGDALA

    async def retrieve(
        self,
        query: str,
        k: int = 5,
        context: Optional[Dict[str, Any]] = None
    ) -> List[DistributedMemory]:
        if not self.amygdala:
            return []

        results = []
        try:
            # 检索情感相关的记忆
            if hasattr(self.amygdala, 'emotional_memories'):
                for mem in self.amygdala.emotional_memories[:k]:
                    results.append(DistributedMemory(
                        id=mem.get('id', ''),
                        content=mem.get('content', ''),
                        source_region=BrainRegion.AMYGDALA,
                        relevance=mem.get('emotional_intensity', 0.5),
                        memory_type='emotional',
                        metadata={'emotion': mem.get('emotion', 'neutral')}
                    ))

            # 检索显著性标记的记忆
            if hasattr(self.amygdala, 'salience_markers'):
                for marker in list(self.amygdala.salience_markers.values())[:k]:
                    if isinstance(marker, dict) and marker.get('content'):
                        results.append(DistributedMemory(
                            id=marker.get('id', ''),
                            content=marker.get('content', ''),
                            source_region=BrainRegion.AMYGDALA,
                            relevance=marker.get('salience', 0.6),
                            memory_type='emotional_salience',
                            metadata={'salience_type': marker.get('type', 'general')}
                        ))
        except Exception as e:
            logger.warning(f"Amygdala retrieval failed: {e}")

        return results[:k]

    def is_available(self) -> bool:
        return self.amygdala is not None


class PrefrontalRetriever(BrainRegionRetriever):
    """前额叶检索器 - 工作记忆"""

    def __init__(self, prefrontal_agent=None):
        self.prefrontal = prefrontal_agent

    @property
    def region(self) -> BrainRegion:
        return BrainRegion.PREFRONTAL

    async def retrieve(
        self,
        query: str,
        k: int = 5,
        context: Optional[Dict[str, Any]] = None
    ) -> List[DistributedMemory]:
        if not self.prefrontal:
            return []

        results = []
        try:
            # 从工作记忆中检索
            if hasattr(self.prefrontal, 'working_memory'):
                for mem in list(self.prefrontal.working_memory)[:k]:
                    content = mem.get('content', str(mem)) if isinstance(mem, dict) else str(mem)
                    results.append(DistributedMemory(
                        id=mem.get('id', str(id(mem))) if isinstance(mem, dict) else str(id(mem)),
                        content=content,
                        source_region=BrainRegion.PREFRONTAL,
                        relevance=0.8,  # 工作记忆高相关性
                        memory_type='working',
                        metadata={'recency': 'recent'}
                    ))

            # 从当前上下文中检索
            if hasattr(self.prefrontal, 'current_context'):
                ctx = self.prefrontal.current_context
                if ctx:
                    results.append(DistributedMemory(
                        id='current_context',
                        content=str(ctx),
                        source_region=BrainRegion.PREFRONTAL,
                        relevance=0.9,
                        memory_type='working_context',
                        metadata={'type': 'current_context'}
                    ))
        except Exception as e:
            logger.warning(f"Prefrontal retrieval failed: {e}")

        return results[:k]

    def is_available(self) -> bool:
        return self.prefrontal is not None


class BasalGangliaRetriever(BrainRegionRetriever):
    """基底节检索器 - 程序记忆"""

    def __init__(self, basal_ganglia_agent=None):
        self.basal_ganglia = basal_ganglia_agent

    @property
    def region(self) -> BrainRegion:
        return BrainRegion.BASAL_GANGLIA

    async def retrieve(
        self,
        query: str,
        k: int = 5,
        context: Optional[Dict[str, Any]] = None
    ) -> List[DistributedMemory]:
        if not self.basal_ganglia:
            return []

        results = []
        try:
            # 从技能库中检索
            if hasattr(self.basal_ganglia, 'skills'):
                query_lower = query.lower()
                for skill_name, skill in self.basal_ganglia.skills.items():
                    # 简单关键词匹配
                    if any(word in skill_name.lower() for word in query_lower.split() if len(word) > 2):
                        content = getattr(skill, 'description', str(skill))
                        results.append(DistributedMemory(
                            id=f"skill_{skill_name}",
                            content=f"Skill: {skill_name}. {content}",
                            source_region=BrainRegion.BASAL_GANGLIA,
                            relevance=getattr(skill, 'proficiency', 0.5),
                            memory_type='procedural',
                            metadata={'skill_name': skill_name}
                        ))
        except Exception as e:
            logger.warning(f"Basal Ganglia retrieval failed: {e}")

        return results[:k]

    def is_available(self) -> bool:
        return self.basal_ganglia is not None


# ============== 分布式检索协调器 ==============

@dataclass
class RegionWeights:
    """脑区权重配置"""
    hippocampus: float = 1.0      # 情景记忆权重
    temporal_lobe: float = 0.9    # 语义记忆权重
    amygdala: float = 0.7         # 情感记忆权重
    prefrontal: float = 1.1       # 工作记忆权重（最近的更重要）
    basal_ganglia: float = 0.5    # 程序记忆权重


class DistributedRetrievalCoordinator:
    """
    五脑区分布式检索协调器

    核心功能:
    1. 并行查询所有可用脑区
    2. 融合不同类型的记忆
    3. 按相关性和脑区权重排序
    4. 返回带有来源标签的统一结果
    """

    def __init__(
        self,
        hippocampus=None,
        temporal_lobe=None,
        amygdala=None,
        prefrontal=None,
        basal_ganglia=None,
        knowledge_graph=None,
        weights: Optional[RegionWeights] = None
    ):
        # 创建各脑区检索器
        self.retrievers: Dict[BrainRegion, BrainRegionRetriever] = {
            BrainRegion.HIPPOCAMPUS: HippocampusRetriever(hippocampus),
            BrainRegion.TEMPORAL_LOBE: TemporalLobeRetriever(temporal_lobe, knowledge_graph),
            BrainRegion.AMYGDALA: AmygdalaRetriever(amygdala),
            BrainRegion.PREFRONTAL: PrefrontalRetriever(prefrontal),
            BrainRegion.BASAL_GANGLIA: BasalGangliaRetriever(basal_ganglia),
        }

        self.weights = weights or RegionWeights()

        # 统计信息
        self.stats = {
            'total_queries': 0,
            'region_hits': {r.value: 0 for r in BrainRegion}
        }

        logger.info(f"DistributedRetrievalCoordinator initialized with {self._count_available()} available regions")

    def _count_available(self) -> int:
        return sum(1 for r in self.retrievers.values() if r.is_available())

    def _get_weight(self, region: BrainRegion) -> float:
        """获取脑区权重"""
        weight_map = {
            BrainRegion.HIPPOCAMPUS: self.weights.hippocampus,
            BrainRegion.TEMPORAL_LOBE: self.weights.temporal_lobe,
            BrainRegion.AMYGDALA: self.weights.amygdala,
            BrainRegion.PREFRONTAL: self.weights.prefrontal,
            BrainRegion.BASAL_GANGLIA: self.weights.basal_ganglia,
        }
        return weight_map.get(region, 1.0)

    async def retrieve(
        self,
        query: str,
        k: int = 10,
        context: Optional[Dict[str, Any]] = None,
        enabled_regions: Optional[List[BrainRegion]] = None
    ) -> List[DistributedMemory]:
        """
        从所有脑区检索并融合结果

        Args:
            query: 查询文本
            k: 返回记忆总数
            context: 上下文信息
            enabled_regions: 启用的脑区列表（默认全部）

        Returns:
            按相关性排序的 DistributedMemory 列表
        """
        self.stats['total_queries'] += 1

        # 确定要查询的脑区
        if enabled_regions is None:
            enabled_regions = list(BrainRegion)

        # 过滤可用的检索器
        active_retrievers = [
            (region, retriever)
            for region, retriever in self.retrievers.items()
            if region in enabled_regions and retriever.is_available()
        ]

        if not active_retrievers:
            logger.warning("No available retrievers for distributed retrieval")
            return []

        # 并行查询所有脑区
        per_region_k = max(3, k // len(active_retrievers) + 2)  # 每个脑区多取一些

        tasks = [
            retriever.retrieve(query, k=per_region_k, context=context)
            for _, retriever in active_retrievers
        ]

        region_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 融合结果
        all_memories: List[DistributedMemory] = []

        for (region, _), result in zip(active_retrievers, region_results):
            if isinstance(result, Exception):
                logger.warning(f"Region {region.value} failed: {result}")
                continue

            if result:
                self.stats['region_hits'][region.value] += 1

                # 应用脑区权重
                weight = self._get_weight(region)
                for mem in result:
                    mem.relevance *= weight
                    all_memories.append(mem)

        # 按相关性排序
        all_memories.sort(key=lambda m: m.relevance, reverse=True)

        # 去重（基于内容相似度）
        deduplicated = self._deduplicate(all_memories)

        logger.debug(f"Distributed retrieval: {len(all_memories)} raw → {len(deduplicated)} deduplicated")

        return deduplicated[:k]

    def _deduplicate(self, memories: List[DistributedMemory]) -> List[DistributedMemory]:
        """基于内容去重"""
        seen_contents = set()
        result = []

        for mem in memories:
            # 简化内容用于去重
            simplified = mem.content.lower().strip()[:100]
            if simplified not in seen_contents:
                seen_contents.add(simplified)
                result.append(mem)

        return result

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            'available_regions': [r.value for r, ret in self.retrievers.items() if ret.is_available()]
        }

    def update_retriever(self, region: BrainRegion, agent):
        """动态更新脑区检索器"""
        if region == BrainRegion.HIPPOCAMPUS:
            self.retrievers[region] = HippocampusRetriever(agent)
        elif region == BrainRegion.TEMPORAL_LOBE:
            # 保留现有的KG
            existing = self.retrievers.get(region)
            kg = existing.kg if existing else None
            self.retrievers[region] = TemporalLobeRetriever(agent, kg)
        elif region == BrainRegion.AMYGDALA:
            self.retrievers[region] = AmygdalaRetriever(agent)
        elif region == BrainRegion.PREFRONTAL:
            self.retrievers[region] = PrefrontalRetriever(agent)
        elif region == BrainRegion.BASAL_GANGLIA:
            self.retrievers[region] = BasalGangliaRetriever(agent)


# 全局实例
_distributed_coordinator: Optional[DistributedRetrievalCoordinator] = None


def get_distributed_coordinator() -> Optional[DistributedRetrievalCoordinator]:
    """获取全局分布式检索协调器"""
    return _distributed_coordinator


def init_distributed_coordinator(
    hippocampus=None,
    temporal_lobe=None,
    amygdala=None,
    prefrontal=None,
    basal_ganglia=None,
    knowledge_graph=None
) -> DistributedRetrievalCoordinator:
    """初始化全局分布式检索协调器"""
    global _distributed_coordinator
    _distributed_coordinator = DistributedRetrievalCoordinator(
        hippocampus=hippocampus,
        temporal_lobe=temporal_lobe,
        amygdala=amygdala,
        prefrontal=prefrontal,
        basal_ganglia=basal_ganglia,
        knowledge_graph=knowledge_graph
    )
    return _distributed_coordinator
