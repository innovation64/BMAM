"""
Distributed Memory System - 分布式记忆系统
模拟人脑中不同脑区存储不同类型记忆的架构

设计原则:
1. 海马体 (Hippocampus): 存储情景记忆 (episodic) - "我昨天做了什么"
2. 颞叶皮层 (Temporal): 存储语义记忆 (semantic) - "概念和事实"
3. 前额叶 (Prefrontal): 存储工作记忆 (working) - "当前任务的临时信息"
4. 杏仁核 (Amygdala): 存储情绪记忆 (emotional) - "带有强烈情绪的事件"
5. 小脑 (Cerebellum): 存储程序性记忆 (procedural) - "技能和习惯"
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class RegionalMemoryStore:
    """单个脑区的记忆存储"""

    def __init__(self, region_name: str, memory_type: str, max_capacity: int = 1000):
        self.region_name = region_name
        self.memory_type = memory_type
        self.max_capacity = max_capacity
        self.memories: List[Dict[str, Any]] = []
        self.access_count = 0

    def store(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """存储记忆到该脑区"""
        from uuid import uuid4

        memory_id = f"{self.region_name}_{uuid4().hex[:8]}"
        memory = {
            'id': memory_id,
            'content': content,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat(),
            'access_frequency': 0,
            'region': self.region_name,
            'type': self.memory_type
        }

        self.memories.append(memory)

        # 容量控制: LRU淘汰
        if len(self.memories) > self.max_capacity:
            # 按访问频率和时间排序,淘汰最旧且最少使用的
            self.memories.sort(key=lambda m: (m['access_frequency'], m['timestamp']))
            self.memories = self.memories[-self.max_capacity:]
            logger.debug(f"{self.region_name} memory pruned: {len(self.memories)}/{self.max_capacity}")

        logger.info(f"✅ {self.region_name} stored {self.memory_type} memory: {memory_id}")
        return memory_id

    def retrieve(self, query: str = None, k: int = 5, filters: Dict[str, Any] = None,
                 time_range: Dict[str, Any] = None, extract_dates: bool = True) -> List[Dict[str, Any]]:
        """
        从该脑区检索记忆

        Args:
            query: 查询关键词
            k: 返回数量
            filters: 元数据过滤器
            time_range: 时间范围过滤 {'start': '2023-05-01', 'end': '2023-05-31'}
            extract_dates: 是否提取内容中的日期进行匹配
        """
        self.access_count += 1

        # 简单检索: 关键词匹配 (支持多关键词)
        if query:
            # 拆分查询为多个关键词
            keywords = query.lower().split()
            results = []
            for m in self.memories:
                content_lower = m['content'].lower()
                # 只要匹配任意一个关键词即可
                if any(kw in content_lower for kw in keywords):
                    results.append(m)
                # 🔥 新增: 时序推理 - 提取内容中的日期进行匹配
                elif extract_dates and self._contains_date_mention(query, m['content']):
                    results.append(m)
        else:
            results = self.memories

        # 🔥 新增: 时间范围过滤 (支持时序推理)
        if time_range:
            from datetime import datetime
            start_time = None
            end_time = None

            if 'start' in time_range:
                try:
                    start_time = datetime.fromisoformat(time_range['start'])
                except:
                    pass
            if 'end' in time_range:
                try:
                    end_time = datetime.fromisoformat(time_range['end'])
                except:
                    pass

            # 按时间范围过滤
            filtered_by_time = []
            for m in results:
                timestamp_str = m.get('timestamp') or m.get('metadata', {}).get('timestamp')
                if not timestamp_str:
                    continue

                try:
                    mem_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    if hasattr(mem_time, 'tzinfo') and mem_time.tzinfo:
                        mem_time = mem_time.replace(tzinfo=None)

                    in_range = True
                    if start_time and mem_time < start_time:
                        in_range = False
                    if end_time and mem_time > end_time:
                        in_range = False

                    if in_range:
                        filtered_by_time.append(m)
                except:
                    continue

            results = filtered_by_time
            logger.debug(f"{self.region_name} time filtering: {len(results)} memories in range")

        # 应用元数据过滤器
        if filters:
            for key, value in filters.items():
                results = [m for m in results if m.get('metadata', {}).get(key) == value]

        # 更新访问频率
        for m in results[:k]:
            m['access_frequency'] += 1

        # 按时间倒序返回最近的k条
        results.sort(key=lambda m: m['timestamp'], reverse=True)

        logger.debug(f"{self.region_name} retrieved {len(results[:k])} memories for query: {query}")
        return results[:k]

    def _contains_date_mention(self, query: str, content: str) -> bool:
        """
        检查内容是否包含查询中提到的日期

        例如: query="When did Caroline go to LGBTQ support group?"
              content="On 8 May 2023, Caroline attended an LGBTQ support group"
              返回True (因为同时包含"Caroline", "LGBTQ", "support group")
        """
        import re

        # 提取query中的关键词 (排除疑问词)
        stop_words = {'when', 'did', 'go', 'to', 'the', 'a', 'an', 'what', 'where', 'how', 'is', 'was', 'were'}
        query_keywords = [w.lower() for w in re.findall(r'\b\w+\b', query) if w.lower() not in stop_words]

        # 检查内容是否包含至少2个关键词 + 日期模式
        content_lower = content.lower()
        keyword_matches = sum(1 for kw in query_keywords if kw in content_lower)

        # 检测日期模式: "8 May 2023", "2023-05-08", "May 8"等
        date_patterns = [
            r'\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',
            r'\d{4}-\d{1,2}-\d{1,2}',
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}'
        ]
        has_date = any(re.search(pattern, content, re.IGNORECASE) for pattern in date_patterns)

        return keyword_matches >= 2 and has_date

    def get_size(self) -> int:
        return len(self.memories)


class DistributedMemorySystem:
    """
    分布式记忆系统 - 模拟人脑多区域记忆存储

    每个脑区负责存储和检索特定类型的记忆:
    - Hippocampus: 情景记忆 (episodic) - 事件、对话、经历
    - Temporal Cortex: 语义记忆 (semantic) - 概念、事实、知识
    - Prefrontal Cortex: 工作记忆 (working) - 临时任务信息
    - Amygdala: 情绪记忆 (emotional) - 带有情绪标签的记忆
    - Cerebellum: 程序性记忆 (procedural) - 技能、习惯
    """

    def __init__(self):
        # 初始化各脑区记忆存储
        self.regions: Dict[str, RegionalMemoryStore] = {
            'hippocampus': RegionalMemoryStore('hippocampus', 'episodic', max_capacity=500),
            'temporal': RegionalMemoryStore('temporal', 'semantic', max_capacity=1000),
            'prefrontal': RegionalMemoryStore('prefrontal', 'working', max_capacity=50),  # 工作记忆容量小
            'amygdala': RegionalMemoryStore('amygdala', 'emotional', max_capacity=300),
            'cerebellum': RegionalMemoryStore('cerebellum', 'procedural', max_capacity=200)
        }

        # 记忆类型 -> 脑区映射
        self.type_to_region = {
            'episodic': 'hippocampus',
            'semantic': 'temporal',
            'working': 'prefrontal',
            'emotional': 'amygdala',
            'procedural': 'cerebellum'
        }

        logger.info("🧠 Distributed Memory System initialized with 5 brain regions")

    def store_memory(self, content: str, memory_type: str, metadata: Dict[str, Any] = None) -> str:
        """
        根据记忆类型存储到对应脑区

        Args:
            content: 记忆内容
            memory_type: episodic | semantic | working | emotional | procedural
            metadata: 额外元数据

        Returns:
            memory_id
        """
        region_name = self.type_to_region.get(memory_type, 'hippocampus')
        region = self.regions[region_name]

        memory_id = region.store(content, metadata)
        logger.info(f"📝 Stored {memory_type} memory to {region_name}: {content[:50]}...")
        return memory_id

    def retrieve_from_region(self, region_name: str, query: str = None, k: int = 5) -> List[Dict[str, Any]]:
        """
        从指定脑区检索记忆

        Args:
            region_name: hippocampus | temporal | prefrontal | amygdala | cerebellum
            query: 查询关键词
            k: 返回数量

        Returns:
            记忆列表
        """
        if region_name not in self.regions:
            logger.warning(f"Unknown brain region: {region_name}")
            return []

        region = self.regions[region_name]
        memories = region.retrieve(query, k)

        logger.debug(f"🔍 Retrieved {len(memories)} memories from {region_name}")
        return memories

    def multi_region_retrieval(self, query: str, regions: List[str] = None, k_per_region: int = 3) -> Dict[str, List[Dict]]:
        """
        多脑区并行检索 - 模拟人脑并行激活

        Args:
            query: 查询
            regions: 要查询的脑区列表 (None表示查询所有)
            k_per_region: 每个脑区返回的记忆数

        Returns:
            {region_name: [memories]}
        """
        if regions is None:
            regions = list(self.regions.keys())

        results = {}
        for region_name in regions:
            results[region_name] = self.retrieve_from_region(region_name, query, k_per_region)

        total_memories = sum(len(mems) for mems in results.values())
        logger.info(f"🧠 Multi-region retrieval: {total_memories} memories from {len(regions)} regions")

        return results

    def consolidate_to_longterm(self, working_memory_id: str, target_type: str = 'semantic'):
        """
        记忆巩固: 从工作记忆转移到长期记忆
        模拟睡眠时海马体-新皮层对话

        Args:
            working_memory_id: 工作记忆ID
            target_type: 目标记忆类型 (episodic | semantic)
        """
        # 从工作记忆中获取
        working_region = self.regions['prefrontal']
        working_memory = None
        for m in working_region.memories:
            if m['id'] == working_memory_id:
                working_memory = m
                break

        if not working_memory:
            logger.warning(f"Working memory not found: {working_memory_id}")
            return None

        # 转移到长期记忆
        content = working_memory['content']
        metadata = working_memory['metadata'].copy()
        metadata['consolidated_from'] = 'working_memory'
        metadata['consolidation_time'] = datetime.now().isoformat()

        longterm_id = self.store_memory(content, target_type, metadata)

        # 从工作记忆中移除 (可选)
        working_region.memories = [m for m in working_region.memories if m['id'] != working_memory_id]

        logger.info(f"💾 Consolidated working memory {working_memory_id} -> {target_type} {longterm_id}")
        return longterm_id

    def get_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        stats = {
            'total_memories': sum(r.get_size() for r in self.regions.values()),
            'regions': {}
        }

        for name, region in self.regions.items():
            stats['regions'][name] = {
                'memory_type': region.memory_type,
                'size': region.get_size(),
                'capacity': region.max_capacity,
                'utilization': f"{region.get_size() / region.max_capacity * 100:.1f}%",
                'access_count': region.access_count
            }

        return stats


# Singleton instance
_distributed_memory_system = None


def get_distributed_memory() -> DistributedMemorySystem:
    """获取分布式记忆系统单例"""
    global _distributed_memory_system
    if _distributed_memory_system is None:
        _distributed_memory_system = DistributedMemorySystem()
    return _distributed_memory_system
