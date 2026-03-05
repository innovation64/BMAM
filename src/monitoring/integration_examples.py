"""
Integration Examples for Brain Region Metrics
脑区指标集成示例

Shows how to add metrics tracking to existing brain region agents.
"""

from typing import List, Dict, Any
from .decorators import track_brain_region_activation, track_collaboration
from .brain_region_metrics import get_global_metrics_collector


# ============================================================================
# 示例 1: 海马体 (Hippocampus) - 记忆存储与检索
# ============================================================================

class HippocampusAgentWithMetrics:
    """海马体代理 - 带指标追踪"""

    @track_brain_region_activation(
        region='hippocampus',
        operation='store_memory',
        output_type='memory_id'
    )
    async def store_memory(self, content: str, importance: float) -> str:
        """存储记忆"""
        # 原有实现...
        memory_id = f"mem_{hash(content)}"
        return memory_id

    @track_brain_region_activation(
        region='hippocampus',
        operation='retrieve',
        output_type='memories'
    )
    async def retrieve_memories(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """检索记忆"""
        # 原有实现...
        memories = []  # 实际检索逻辑
        return memories

    @track_brain_region_activation(
        region='hippocampus',
        operation='consolidate',
        input_source='consolidation',
        output_type='consolidated_memories'
    )
    async def consolidate_memories(self) -> int:
        """记忆巩固"""
        # 原有实现...
        consolidated_count = 0
        return consolidated_count


# ============================================================================
# 示例 2: 颞叶 (Temporal Lobe) - 语义记忆与知识图谱
# ============================================================================

class TemporalLobeAgentWithMetrics:
    """颞叶代理 - 带指标追踪"""

    @track_brain_region_activation(
        region='temporal_lobe',
        operation='extract_entities',
        output_type='entities'
    )
    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """提取实体"""
        entities = []  # 实际提取逻辑
        return entities

    @track_brain_region_activation(
        region='temporal_lobe',
        operation='kg_query',
        output_type='kg_results'
    )
    async def query_knowledge_graph(
        self,
        query: str
    ) -> List[Dict[str, Any]]:
        """查询知识图谱"""
        results = []  # 实际查询逻辑
        return results

    @track_brain_region_activation(
        region='temporal_lobe',
        operation='semantic_search',
        output_type='concepts'
    )
    async def semantic_search(self, query: str) -> List[str]:
        """语义搜索"""
        concepts = []  # 实际搜索逻辑
        return concepts


# ============================================================================
# 示例 3: 前额叶 (Prefrontal Cortex) - 执行控制与推理
# ============================================================================

class PrefrontalAgentWithMetrics:
    """前额叶代理 - 带指标追踪"""

    @track_brain_region_activation(
        region='prefrontal',
        operation='reason',
        output_type='inference'
    )
    async def perform_reasoning(
        self,
        query: str,
        context: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """执行推理"""
        inference = {}  # 实际推理逻辑
        return inference

    @track_brain_region_activation(
        region='prefrontal',
        operation='plan',
        output_type='action_plan'
    )
    async def plan_actions(self, goal: str) -> List[str]:
        """规划行动"""
        actions = []  # 实际规划逻辑
        return actions

    @track_brain_region_activation(
        region='prefrontal',
        operation='detect_conflict',
        output_type='conflicts'
    )
    async def detect_conflicts(
        self,
        memories: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """检测冲突"""
        conflicts = []  # 实际检测逻辑
        return conflicts


# ============================================================================
# 示例 4: 杏仁核 (Amygdala) - 情绪标注
# ============================================================================

class AmygdalaAgentWithMetrics:
    """杏仁核代理 - 带指标追踪"""

    @track_brain_region_activation(
        region='amygdala',
        operation='tag_emotion',
        output_type='emotion_tags'
    )
    async def tag_emotion(
        self,
        content: str
    ) -> Dict[str, float]:
        """情绪标注"""
        emotions = {
            'joy': 0.0,
            'sadness': 0.0,
            'anger': 0.0,
            'fear': 0.0
        }
        # 实际标注逻辑
        return emotions

    @track_brain_region_activation(
        region='amygdala',
        operation='assess_stress',
        output_type='stress_level'
    )
    async def assess_stress_level(
        self,
        context: Dict[str, Any]
    ) -> float:
        """评估压力水平"""
        stress_level = 0.0  # 实际评估逻辑
        return stress_level


# ============================================================================
# 示例 5: 基底节 (Basal Ganglia) - 习惯与程序性记忆
# ============================================================================

class BasalGangliaAgentWithMetrics:
    """基底节代理 - 带指标追踪"""

    @track_brain_region_activation(
        region='basal_ganglia',
        operation='select_action',
        output_type='action'
    )
    async def select_action(
        self,
        state: Dict[str, Any]
    ) -> str:
        """选择动作"""
        action = ""  # 实际选择逻辑
        return action

    @track_brain_region_activation(
        region='basal_ganglia',
        operation='update_habit',
        input_source='learning',
        output_type='habit_strength'
    )
    async def update_habit(
        self,
        action: str,
        reward: float
    ) -> float:
        """更新习惯"""
        habit_strength = 0.0  # 实际更新逻辑
        return habit_strength


# ============================================================================
# 示例 6: 多脑区协作
# ============================================================================

class MultiRegionCoordinatorWithMetrics:
    """多脑区协调器 - 带指标追踪"""

    def __init__(self):
        self.hippocampus = HippocampusAgentWithMetrics()
        self.prefrontal = PrefrontalAgentWithMetrics()
        self.temporal_lobe = TemporalLobeAgentWithMetrics()
        self.amygdala = AmygdalaAgentWithMetrics()

    @track_collaboration('hippocampus', 'prefrontal', 'temporal_lobe')
    async def complex_query_processing(
        self,
        query: str
    ) -> Dict[str, Any]:
        """复杂查询处理 - 多脑区协作"""

        # 1. 海马体检索记忆
        memories = await self.hippocampus.retrieve_memories(query)

        # 2. 颞叶语义分析
        entities = await self.temporal_lobe.extract_entities(query)

        # 3. 前额叶推理
        inference = await self.prefrontal.perform_reasoning(query, memories)

        # 4. 杏仁核情绪标注
        emotions = await self.amygdala.tag_emotion(query)

        return {
            'memories': memories,
            'entities': entities,
            'inference': inference,
            'emotions': emotions
        }


# ============================================================================
# 使用示例
# ============================================================================

async def usage_example():
    """使用示例"""
    from .brain_region_metrics import get_global_metrics_collector

    # 获取全局指标收集器
    collector = get_global_metrics_collector()

    # 创建多脑区协调器
    coordinator = MultiRegionCoordinatorWithMetrics()

    # 处理多个查询
    queries = [
        "What did I have for breakfast yesterday?",
        "Tell me about my meeting with Sarah last week",
        "What are my favorite hobbies?"
    ]

    for query in queries:
        await collector.async_start_new_query()
        result = await coordinator.complex_query_processing(query)
        print(f"Query: {query}")
        print(f"Result: {result}\n")

    # 导出指标
    await collector.async_export_to_json('data/memory_system_metrics.json')

    # 打印摘要
    print(await collector.async_get_summary_report())


# ============================================================================
# 手动记录示例（不使用装饰器）
# ============================================================================

async def manual_tracking_example():
    """手动记录指标示例"""
    from .brain_region_metrics import get_global_metrics_collector
    import time

    collector = get_global_metrics_collector()

    # 开始新查询
    await collector.async_start_new_query()

    # 海马体检索
    start_time = time.time()
    memories = []  # 实际检索逻辑
    processing_time = (time.time() - start_time) * 1000

    await collector.async_record_activation(
        region='hippocampus',
        operation='retrieve',
        input_source='user_query',
        output_type='memories',
        processing_time_ms=processing_time,
        metadata={'memory_count': len(memories)}
    )

    # 前额叶推理
    start_time = time.time()
    inference = {}  # 实际推理逻辑
    processing_time = (time.time() - start_time) * 1000

    await collector.async_record_activation(
        region='prefrontal',
        operation='reason',
        input_source='user_query',
        output_type='inference',
        processing_time_ms=processing_time,
        metadata={'confidence': 0.85}
    )

    # 导出指标
    await collector.async_export_to_json('data/memory_system_metrics.json')
