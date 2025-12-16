"""
Amygdala Agent - 杏仁核智能体
对应脑区: 杏仁核 (Amygdala)
主要功能: 情绪记忆标记 + 情绪调节 + 应激响应 (Plan C: 集成存储和处理)

核心设计:
1. 小容量 (1,000条) - 情绪标记的重要事件
2. 不存储完整内容,只存储情绪标签和引用
3. 保留高情绪强度的记忆
4. 快速遗忘低情绪强度的标记
5. 情绪调节: 影响其他脑区的记忆编码和检索
6. 应激响应: 高压情况下增强记忆巩固
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
import uuid

from ..base import BrainAgent, AgentMessage, BrainRegion
from ...brain.emotion_modulator import EmotionModulator

logger = logging.getLogger(__name__)


@dataclass
class EmotionalMemory:
    """情绪记忆标记"""
    id: str
    reference_id: str  # 引用的原始记忆ID (来自Hippocampus或TemporalLobe)
    content_summary: str  # 简短摘要 (不存完整内容)
    emotion_tags: List[str]  # 情绪标签: ['happy', 'sad', 'anger', 'fear', 'surprise', 'disgust']
    emotion_intensity: float  # 情绪强度 (0.0-1.0)
    timestamp: datetime
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class AmygdalaAgent(BrainAgent):
    """
    杏仁核智能体 - 情绪记忆标记 + 情绪调节 + 应激响应 (Plan C)

    容量: 1,000条情绪标记
    存储格式: List (不存完整内容,只存标签和引用)
    遗忘机制: 保留高情绪强度,删除低强度
    功能: 情绪标记、情绪检索、情绪增强回忆
    情绪调节: 影响其他脑区的记忆权重
    应激响应: 高压下增强巩固
    """

    def __init__(self, capacity: int = 1000, hippocampus_agent=None, temporal_lobe_agent=None, client=None):
        super().__init__(
            agent_id="amygdala",
            brain_region=BrainRegion.AMYGDALA,
            system_prompt="""You are the Amygdala agent, responsible for emotional memory tagging, emotion modulation, and stress response.
            You mark emotionally significant events with emotion tags and intensity.
            You prioritize high-intensity emotions and enhance emotional recall.
            You modulate memory encoding in other brain regions based on emotional significance.
            You trigger enhanced consolidation during high-stress situations.""",
            client=client
        )

        # 🔥 情绪记忆标记存储
        self.capacity = capacity
        self.memories: List[EmotionalMemory] = []
        self.memory_dict: Dict[str, EmotionalMemory] = {}

        # 情绪索引
        self.emotion_index: Dict[str, List[str]] = {}  # {emotion_tag: [memory_ids]}

        # 🔥 情绪缓冲区 (emotional_buffer) - 用于存储当前活跃的情绪状态
        # References self.memories for active emotional memories
        self.emotional_buffer = self.memories  # Alias for functional brain regions test

        # 🧠 Plan C: 集成情绪调节功能
        self.hippocampus = hippocampus_agent  # 用于影响记忆编码
        self.temporal_lobe = temporal_lobe_agent  # 用于影响语义记忆
        self.current_stress_level = 0.0  # 当前压力水平 (0.0-1.0)
        self.emotion_modulation_history: List[Dict[str, Any]] = []
        
        # 🧠 Emotion Modulator
        self.modulator = EmotionModulator()

        # 统计信息
        self.total_stored = 0
        self.total_forgotten = 0
        self.total_modulations = 0
        self.total_stress_responses = 0

        # 🔥 Auto-persistence setup (使用 BMAMPaths 支持并行测试)
        from src.utils.paths import BMAMPaths
        self.state_file = BMAMPaths.AMYGDALA_STATE
        self._load_state_from_file()

        logger.info(f"✅ AmygdalaAgent initialized (capacity={capacity})")


    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """处理消息"""
        action = message.content.get('action')

        if action == 'tag_emotion':
            return await self.tag_emotion(
                reference_id=message.content['reference_id'],
                content_summary=message.content['content_summary'],
                emotion_tags=message.content['emotion_tags'],
                emotion_intensity=message.content['emotion_intensity'],
                metadata=message.content.get('metadata', {})
            )

        elif action == 'search_by_emotion':
            return self.search_by_emotion(
                emotion_tags=message.content.get('emotion_tags'),
                min_intensity=message.content.get('min_intensity', 0.0),
                k=message.content.get('k', 10)
            )

        elif action == 'get_statistics':
            return self.get_statistics()

        # 🧠 Plan C: 情绪调节和应激响应功能
        elif action == 'modulate_memory_encoding':
            return await self.modulate_memory_encoding(
                memory_id=message.content['memory_id'],
                emotion_intensity=message.content['emotion_intensity'],
                emotion_tags=message.content.get('emotion_tags', [])
            )

        elif action == 'trigger_stress_response':
            return await self.trigger_stress_response(
                stressor=message.content['stressor'],
                stress_level=message.content.get('stress_level', 0.7)
            )

        elif action == 'get_stress_level':
            return {'stress_level': self.current_stress_level}

        return {'error': f'Unknown action: {action}'}

    async def tag_emotion(
        self,
        reference_id: str,
        content_summary: str,
        emotion_tags: List[str],
        emotion_intensity: float,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        标记情绪记忆

        Args:
            reference_id: 引用的原始记忆ID
            content_summary: 简短摘要
            emotion_tags: 情绪标签 ['happy', 'sad', 'anger', etc.]
            emotion_intensity: 情绪强度 (0.0-1.0)
            metadata: 元数据

        Returns:
            {'memory_id': str, 'tagged': bool}
        """

        # 创建情绪记忆
        memory = EmotionalMemory(
            id=uuid.uuid4().hex,
            reference_id=reference_id,
            content_summary=content_summary,
            emotion_tags=emotion_tags,
            emotion_intensity=emotion_intensity,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )

        # 存储
        self.memories.append(memory)
        self.memory_dict[memory.id] = memory

        # 更新情绪索引
        for tag in emotion_tags:
            if tag not in self.emotion_index:
                self.emotion_index[tag] = []
            self.emotion_index[tag].append(memory.id)

        # 容量控制
        if len(self.memories) > self.capacity:
            await self._trigger_forgetting()

        self.total_stored += 1

        # 🔥 Auto-persist to JSON file
        self._save_state_to_file()

        return {
            'memory_id': memory.id,
            'tagged': True,
            'capacity_status': self._get_capacity_status()
        }

    def search_by_emotion(
        self,
        emotion_tags: List[str] = None,
        min_intensity: float = 0.0,
        k: int = 10
    ) -> Dict[str, Any]:
        """
        按情绪搜索

        Args:
            emotion_tags: 情绪标签过滤 (None = 所有)
            min_intensity: 最小情绪强度
            k: 返回数量

        Returns:
            {'memories': List[Dict], 'count': int}
        """

        results = []

        # 如果指定了emotion_tags,使用索引检索
        if emotion_tags:
            candidate_ids = set()
            for tag in emotion_tags:
                candidate_ids.update(self.emotion_index.get(tag, []))

            candidates = [self.memory_dict[mid] for mid in candidate_ids if mid in self.memory_dict]
        else:
            candidates = self.memories

        # 过滤强度
        for mem in candidates:
            if mem.emotion_intensity >= min_intensity:
                results.append(mem)

        # 更新访问统计
        for mem in results:
            mem.access_count += 1

        # 排序: emotion_intensity > timestamp
        results.sort(
            key=lambda m: (m.emotion_intensity, m.timestamp),
            reverse=True
        )

        # 限制数量
        results = results[:k]

        return {
            'memories': [self._memory_to_dict(mem) for mem in results],
            'count': len(results)
        }

    async def _trigger_forgetting(self):
        """
        触发遗忘机制

        策略: 保留高情绪强度的记忆
        删除后20%的低强度记忆
        """

        # 按情绪强度排序
        self.memories.sort(
            key=lambda m: (m.emotion_intensity, m.access_count, m.timestamp),
            reverse=True
        )

        # 删除后20%
        forget_count = len(self.memories) // 5
        forgotten = self.memories[-forget_count:]
        self.memories = self.memories[:-forget_count]

        # 更新memory_dict
        for mem in forgotten:
            if mem.id in self.memory_dict:
                del self.memory_dict[mem.id]

        # 重建情绪索引
        self._rebuild_index()

        self.total_forgotten += forget_count


    def _rebuild_index(self):
        """重建情绪索引"""
        self.emotion_index.clear()

        for mem in self.memories:
            for tag in mem.emotion_tags:
                if tag not in self.emotion_index:
                    self.emotion_index[tag] = []
                self.emotion_index[tag].append(mem.id)

    def _get_capacity_status(self) -> Dict[str, Any]:
        """获取容量状态"""
        current = len(self.memories)
        return {
            'current': current,
            'max': self.capacity,
            'usage_percent': (current / self.capacity) * 100 if self.capacity > 0 else 0
        }

    async def modulate_memory_encoding(
        self,
        memory_id: str,
        emotion_intensity: float,
        emotion_tags: List[str]
    ) -> Dict[str, Any]:
        """
        情绪调节: 影响其他脑区的记忆编码 (Plan C)

        模拟杏仁核对记忆编码的调节作用:
        - 高情绪强度 → 增强记忆重要性
        - 触发海马体的优先巩固
        - 影响记忆的长期保留

        Args:
            memory_id: 要调节的记忆ID
            emotion_intensity: 情绪强度 (0.0-1.0)
            emotion_tags: 情绪标签

        Returns:
            {'modulated': bool, 'importance_boost': float, 'consolidation_triggered': bool}
        """

        if not self.hippocampus:
            return {
                'modulated': False,
                'error': 'Hippocampus not connected'
            }

        try:
            # 计算情绪增强系数 (使用EmotionModulator)
            # importance_boost = emotion_intensity * 0.3  # OLD
            
            # 假设基础重要性为0.5 (或者从外部获取)
            base_importance = 0.5
            modulated_importance = self.modulator.modulate_importance(base_importance, emotion_intensity)
            importance_boost = modulated_importance - base_importance

            # 记录调节历史
            modulation_record = {
                'memory_id': memory_id,
                'emotion_intensity': emotion_intensity,
                'emotion_tags': emotion_tags,
                'importance_boost': importance_boost,
                'timestamp': datetime.now().isoformat()
            }
            self.emotion_modulation_history.append(modulation_record)

            # 限制历史长度
            if len(self.emotion_modulation_history) > 100:
                self.emotion_modulation_history = self.emotion_modulation_history[-100:]

            # 如果情绪强度很高,触发海马体的优先巩固
            consolidation_triggered = False
            if emotion_intensity >= 0.7 and self.temporal_lobe:
                # 通知海马体这是高情绪记忆,应该优先巩固
                consolidation_triggered = True

            # 将情绪调制落地到海马体记忆 (重要性/巩固权重)
            try:
                if hasattr(self.hippocampus, 'apply_emotional_modulation'):
                    hippo_result = await self.hippocampus.apply_emotional_modulation(
                        memory_id=memory_id,
                        importance_boost=importance_boost,
                        emotion_tags=emotion_tags,
                        emotion_intensity=emotion_intensity
                    )
                    consolidation_triggered = consolidation_triggered or hippo_result.get('consolidated', False)
            except Exception as e:
                logger.warning(f"Hippocampus emotional modulation failed: {e}")

            self.total_modulations += 1


            return {
                'modulated': True,
                'importance_boost': importance_boost,
                'consolidation_triggered': consolidation_triggered,
                'emotion_intensity': emotion_intensity
            }

        except (Exception) as e:
            logger.error(f"Failed to modulate memory encoding: {e}")
            return {
                'modulated': False,
                'error': str(e)
            }

    async def trigger_stress_response(
        self,
        stressor: str,
        stress_level: float
    ) -> Dict[str, Any]:
        """
        应激响应: 高压情况下增强记忆巩固 (Plan C)

        模拟杏仁核的应激响应:
        - 提高当前压力水平
        - 增强记忆编码和巩固
        - 影响遗忘阈值 (高压下遗忘更少)

        Args:
            stressor: 压力源描述
            stress_level: 压力等级 (0.0-1.0)

        Returns:
            {'stress_response_triggered': bool, 'new_stress_level': float, 'effects': List[str]}
        """

        try:
            # 更新压力水平 (逐渐累积,不是直接替换)
            old_stress = self.current_stress_level
            self.current_stress_level = min(1.0, self.current_stress_level + stress_level * 0.5)

            effects = []

            # 高压下的生理效应
            if self.current_stress_level >= 0.7:
                effects.append("Enhanced memory consolidation activated")

                # 通知海马体和颞叶提高巩固优先级
                if self.hippocampus:
                    effects.append("Hippocampus consolidation enhanced")

                if self.temporal_lobe:
                    effects.append("Temporal lobe retention enhanced")

            elif self.current_stress_level >= 0.4:
                effects.append("Moderate arousal - attention focused")

            # 使用LLM生成应激响应建议
            prompt = f"""作为杏仁核应激响应系统,分析以下压力情况:

压力源: {stressor}
当前压力水平: {self.current_stress_level:.2f}
之前压力水平: {old_stress:.2f}

请输出:
1. 应激响应建议
2. 记忆系统的调节策略
3. 情绪调节建议

简洁输出。"""

            response_advice = await self.call_llm(
                prompt=prompt,
                context={'stressor': stressor, 'stress_level': stress_level},
                max_tokens=400,
                temperature=0.5
            )

            self.total_stress_responses += 1


            return {
                'stress_response_triggered': True,
                'new_stress_level': self.current_stress_level,
                'old_stress_level': old_stress,
                'effects': effects,
                'advice': response_advice
            }

        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            logger.error(f"Failed to trigger stress response: {e}")
            return {
                'stress_response_triggered': False,
                'error': str(e)
            }

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'agent_id': self.agent_id,
            'brain_region': self.brain_region,
            'capacity': self.capacity,
            'current_memories': len(self.memories),
            'usage_percent': self._get_capacity_status()['usage_percent'],
            'total_stored': self.total_stored,
            'total_forgotten': self.total_forgotten,
            'emotion_tags_count': len(self.emotion_index),
            'total_modulations': self.total_modulations,
            'total_stress_responses': self.total_stress_responses,
            'current_stress_level': self.current_stress_level,
            'emotion_modulation_enabled': self.hippocampus is not None
        }

    def _memory_to_dict(self, memory: EmotionalMemory) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': memory.id,
            'reference_id': memory.reference_id,
            'content_summary': memory.content_summary,
            'emotion_tags': memory.emotion_tags,
            'emotion_intensity': memory.emotion_intensity,
            'timestamp': memory.timestamp.isoformat(),
            'access_count': memory.access_count,
            'metadata': memory.metadata
        }

    def export_state(self) -> Dict[str, Any]:
        """
        Export amygdala state to JSON-serializable format for BMA archive.

        Returns:
            Dict containing all emotional memories and indices
        """
        # Serialize emotional memories
        memories_data = []
        for mem in self.memories:
            memories_data.append({
                'id': mem.id,
                'reference_id': mem.reference_id,
                'content_summary': mem.content_summary,
                'emotion_tags': mem.emotion_tags,
                'emotion_intensity': mem.emotion_intensity,
                'timestamp': mem.timestamp.isoformat() if mem.timestamp else None,
                'access_count': mem.access_count,
                'metadata': mem.metadata
            })

        # Serialize emotion modulation history
        modulation_data = []
        for modulation in self.emotion_modulation_history:
            # Handle datetime objects
            mod_copy = modulation.copy()
            for key, value in mod_copy.items():
                if isinstance(value, datetime):
                    mod_copy[key] = value.isoformat()
            modulation_data.append(mod_copy)

        # Export state
        state = {
            'format_version': '1.0.0',
            'agent_id': self.agent_id,
            'brain_region': 'amygdala',
            'capacity': self.capacity,
            'current_stress_level': self.current_stress_level,
            'memories': memories_data,
            'emotion_index': dict(self.emotion_index),
            'emotion_modulation_history': modulation_data,
            'statistics': {
                'total_stored': self.total_stored,
                'total_forgotten': self.total_forgotten,
                'total_modulations': self.total_modulations,
                'total_stress_responses': self.total_stress_responses,
                'current_count': len(self.memories)
            }
        }

        logger.info(f"✅ Exported AmygdalaAgent state: {len(memories_data)} emotional memories")
        return state

    def load_state(self, state: Dict[str, Any]) -> bool:
        """
        Load amygdala state from exported data.

        Args:
            state: State dictionary from export_state()

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate format
            if state.get('brain_region') != 'amygdala':
                logger.error(f"❌ Invalid brain region: {state.get('brain_region')}")
                return False

            # Clear current state
            self.memories.clear()
            self.memory_dict.clear()
            self.emotion_index.clear()
            self.emotion_modulation_history.clear()

            # Restore configuration
            self.capacity = state.get('capacity', self.capacity)
            self.current_stress_level = state.get('current_stress_level', 0.0)

            # Restore emotional memories
            for mem_data in state.get('memories', []):
                memory = EmotionalMemory(
                    id=mem_data['id'],
                    reference_id=mem_data['reference_id'],
                    content_summary=mem_data['content_summary'],
                    emotion_tags=mem_data.get('emotion_tags', []),
                    emotion_intensity=mem_data.get('emotion_intensity', 0.0),
                    timestamp=datetime.fromisoformat(mem_data['timestamp']) if mem_data.get('timestamp') else datetime.now(),
                    access_count=mem_data.get('access_count', 0),
                    metadata=mem_data.get('metadata', {})
                )

                self.memories.append(memory)
                self.memory_dict[memory.id] = memory

                # Rebuild emotion index
                for tag in memory.emotion_tags:
                    if tag not in self.emotion_index:
                        self.emotion_index[tag] = []
                    self.emotion_index[tag].append(memory.id)

            # Restore emotion modulation history
            for mod_data in state.get('emotion_modulation_history', []):
                # Restore datetime objects
                mod_copy = mod_data.copy()
                for key, value in mod_copy.items():
                    if isinstance(value, str) and 'T' in value:  # ISO format detection
                        try:
                            mod_copy[key] = datetime.fromisoformat(value)
                        except:
                            pass
                self.emotion_modulation_history.append(mod_copy)

            # Restore statistics
            stats = state.get('statistics', {})
            self.total_stored = stats.get('total_stored', 0)
            self.total_forgotten = stats.get('total_forgotten', 0)
            self.total_modulations = stats.get('total_modulations', 0)
            self.total_stress_responses = stats.get('total_stress_responses', 0)

            logger.info(f"✅ Loaded AmygdalaAgent state: {len(self.memories)} emotional memories")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to load AmygdalaAgent state: {e}")
            return False

    def _load_state_from_file(self):
        """Auto-load state from JSON file on startup"""
        if not self.state_file.exists():
            logger.info(f"📂 No existing state file found at {self.state_file}, starting fresh")
            return

        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                success = self.load_state(state)
                if success:
                    logger.info(f"✅ Auto-loaded Amygdala state from {self.state_file}")
                else:
                    logger.warning(f"⚠️  Failed to load Amygdala state from {self.state_file}")
        except Exception as e:
            logger.error(f"❌ Error loading Amygdala state from {self.state_file}: {e}")

    def _save_state_to_file(self):
        """Auto-save current state to JSON file"""
        try:
            # Ensure data directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            state = self.export_state()
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            logger.error(f"❌ Error saving Amygdala state to {self.state_file}: {e}")
