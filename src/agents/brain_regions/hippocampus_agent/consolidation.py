"""
Hippocampus Agent - 海马体智能体
对应脑区: 海马体 (Hippocampus)
主要功能: 情节记忆存储+检索+巩固
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)

# Import metrics collector for observability
from src.monitoring.memory_metrics import get_metrics_collector


from .core import EpisodicMemory, HippocampusAgentCore
from ...base import AgentMessage
import asyncio
from sklearn.cluster import DBSCAN
import numpy as np


class ConsolidationMixin:
    """记忆巩固功能"""
    async def _should_consolidate_memory(self, memory: EpisodicMemory) -> bool:
        """
        LLM动态决策是否巩固记忆

        神经科学依据:
        - 海马体根据记忆的"重要性特征"决定是否巩固到新皮层
        - 不是简单的阈值判断,而是综合考虑多个因素

        文献: McClelland et al. (1995) "Systems Consolidation"
        """

        # 构建决策prompt
        decision_prompt = f"""你是海马体的记忆巩固控制器。判断以下情节记忆是否需要巩固到长期记忆。

记忆内容: {memory.content}
记忆属性:
- 重要性: {memory.importance}
- 访问次数: {memory.access_count}
- 情绪标签: {', '.join(memory.emotion_tags) if memory.emotion_tags else '无'}
- 情绪强度: {memory.emotion_intensity}
- 实体: {', '.join(memory.entities) if memory.entities else '无'}

巩固标准 (综合判断,非硬编码阈值):
1. 高重要性 (importance > 0.6) - 但不是唯一标准
2. 强情绪体验 (emotion_intensity > 0.7) - 情绪记忆更易巩固
3. 包含重要实体关系 - 实体间的关系值得长期记住
4. 可提取语义知识 - 有复用价值的经验

请综合考虑以上因素,判断是否巩固。

返回JSON:
{{
    "should_consolidate": true/false,
    "reasoning": "详细理由"
}}

只输出JSON,不要其他文字。"""

        try:
            response = await self.call_llm(decision_prompt, max_tokens=200, temperature=0.3)

            import json
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group())
                should_consolidate = decision.get('should_consolidate', False)
                reasoning = decision.get('reasoning', '')

                if should_consolidate:
                    logger.debug(f"Consolidating memory {memory.id[:8]}: {reasoning}")

                return should_consolidate
            else:
                # Fallback: 使用简化规则
                return memory.importance > 0.6 or memory.emotion_intensity > 0.7

        except (json.JSONDecodeError) as e:
            logger.warning(f"LLM consolidation decision failed: {e}, using fallback")
            # Fallback: 简化规则
            return memory.importance > 0.6 or memory.emotion_intensity > 0.7


    async def _consolidate_to_temporal_lobe(self, memory: EpisodicMemory):
        """
        内部巩固功能: Hippocampus → TemporalLobe (Plan C)
        将重要的情节记忆提取为语义知识

        模拟人脑的记忆巩固过程 (睡眠时海马体向新皮层转移记忆)
        """
        if not self.temporal_lobe:
            return

        try:
            # 使用LLM提取语义知识
            prompt = f"""从以下情节记忆中提取核心的语义知识:

情节内容: {memory.content}
实体: {', '.join(memory.entities)}
情绪: {', '.join(memory.emotion_tags)} (强度: {memory.emotion_intensity})

请提取:
1. 核心事实和知识点
2. 实体之间的关系
3. 可复用的经验或模式

以简洁的语义知识形式输出。"""

            knowledge = await self.call_llm(
                prompt=prompt,
                context={'memory_id': memory.id, 'timestamp': memory.timestamp.isoformat()},
                max_tokens=500,
                temperature=0.3
            )

            # 🔥 提取关系三元组 (Plan C完整实现：LLM提取精细关系)
            relations = []
            if memory.entities:
                try:
                    # 让LLM提取结构化关系
                    relation_prompt = f"""从以下情节记忆中提取结构化的关系三元组。

情节内容: {memory.content}
实体: {', '.join(memory.entities)}

请提取精确的关系类型（不要只用generic的related_to）。

常见关系类型示例：
- attended（参加）: Person attended Event
- researched（研究）: Person researched Topic
- interested_in（对...感兴趣）: Person interested_in Topic
- learned_about（学习）: Person learned_about Topic
- works_in（工作于）: Person works_in Field
- identifies_as（认同为）: Person identifies_as Identity
- supports（支持）: Organization supports Community

输出JSON格式：
{{
  "relations": [
    ["source_entity", "relation_type", "target_entity"],
    ...
  ]
}}

只输出JSON，不要其他文字。"""

                    rel_result = await self.call_llm(
                        prompt=relation_prompt,
                        max_tokens=300,
                        temperature=0.1
                    )

                    # 解析JSON
                    import json
                    import re
                    json_match = re.search(r'\{.*\}', rel_result, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group())
                        relations = [tuple(r) for r in parsed.get('relations', [])]
                    else:
                        # Fallback to simple related_to
                        if len(memory.entities) >= 2:
                            relations = [(memory.entities[0], "related_to", memory.entities[1])]
                except (json.JSONDecodeError) as e:
                    logger.warning(f"Failed to extract relations via LLM: {e}, using fallback")
                    # Fallback to simple related_to
                    if len(memory.entities) >= 2:
                        for i in range(len(memory.entities) - 1):
                            relations.append((memory.entities[i], "related_to", memory.entities[i+1]))

            # 发送到TemporalLobe (✅ 保留source_episode_id用于回溯)
            await self.temporal_lobe.process_message(AgentMessage(
                sender='hippocampus',
                receiver='temporal_lobe',
                message_type='request',
                content={
                    'action': 'store_semantic',
                    'content': knowledge,
                    'memory_subtype': 'semantic',
                    'entities': memory.entities,
                    'relations': relations,
                    'importance': memory.importance,
                    'event_time': memory.timestamp,  # 🔥 传递事件时间 (而非学习时间)
                    'metadata': {
                        'source_episode_id': memory.id,  # 🔥 保留源情节记忆ID用于回溯
                        'event_id': memory.event_id,     # 🔥 保留事件ID
                        'consolidation_time': datetime.now().isoformat()
                    }
                }
            ))

            self.total_consolidated += 1

        except (Exception) as e:
            logger.error(f"Failed to consolidate memory {memory.id}: {e}")


    async def consolidate_memories(self) -> Dict[str, Any]:
        """
        批量记忆巩固: 找到重要但未巩固的记忆,提取模式 (Plan C)

        这个方法会在后台定期调用,模拟睡眠时的记忆巩固
        """

        if not self.temporal_lobe:
            return {
                'consolidated': 0,
                'message': 'TemporalLobe not connected'
            }

        # 找到重要但访问较少的记忆 (候选巩固对象)
        # ✅ 移除硬编码 consolidation_threshold,使用动态筛选
        # 🔧 P1 FIX: 降低阈值以支持LoCoMo等真实场景 (0.5→0.3, 0.6→0.4)
        consolidation_candidates = [
            mem for mem in self.memories
            if (mem.importance > 0.3 or mem.emotion_intensity > 0.4)  # 动态标准 (降低阈值)
            and mem.access_count < 5  # 避免重复巩固 (放宽限制)
        ]

        consolidated_count = 0

        # 按时间分组,提取模式
        time_groups = defaultdict(list)
        for mem in consolidation_candidates[:100]:  # 限制处理数量
            date_key = mem.timestamp.strftime('%Y-%m-%d')
            time_groups[date_key].append(mem)

        # 对每一天的记忆进行巩固
        # 🔧 P1 FIX: 支持单条记忆巩固 (移除 len(memories) > 1 限制)
        for date_key, memories in time_groups.items():
            if len(memories) >= 1:
                # 合并同一天的一个或多个记忆
                combined_content = "\n".join([f"- {m.content}" for m in memories])
                all_entities = list(set(sum([m.entities for m in memories], [])))

                try:
                    # 提取日摘要和模式
                    if len(memories) == 1:
                        prompt = f"""从以下情节记忆中提取核心知识和语义:

{combined_content}

请提取:
1. 核心事实和知识点
2. 实体及其关系
3. 可复用的经验或模式

以结构化的语义知识输出。"""
                    else:
                        prompt = f"""从以下{len(memories)}条情节记忆中提取关键模式和知识:

{combined_content}

请提取:
1. 这一天的核心主题和模式
2. 重要的事实和知识
3. 实体关系

以结构化的语义知识输出。"""

                    pattern = await self.call_llm(
                        prompt=prompt,
                        context={'date': date_key, 'memory_count': len(memories)},
                        max_tokens=800,
                        temperature=0.3
                    )

                    # 发送到TemporalLobe
                    await self.temporal_lobe.process_message(AgentMessage(
                        sender='hippocampus',
                        receiver='temporal_lobe',
                        message_type='request',
                        content={
                            'action': 'store_semantic',
                            'content': f"[{date_key}] {pattern}",
                            'memory_subtype': 'semantic',
                            'entities': all_entities,
                            'relations': [],
                            'importance': 0.8,
                            'metadata': {
                                'consolidated_from': [m.id for m in memories],
                                'consolidation_date': datetime.now().isoformat()
                            }
                        }
                    ))

                    # 🔥 NEW: 并行存储到 MemorySystem (向量数据库)
                    if hasattr(self, 'storage_adapter') and self.storage_adapter and hasattr(self.storage_adapter, 'memory_system') and self.storage_adapter.memory_system:
                        try:
                            await self.storage_adapter.memory_system.store_memory(
                                content=f"[{date_key}] {pattern}",
                                metadata={
                                    'type': 'consolidated',
                                    'source': 'hippocampus_consolidation',
                                    'consolidated_from': [m.id for m in memories],
                                    'consolidation_date': datetime.now().isoformat(),
                                    'date_key': date_key,
                                    'entities': all_entities,
                                    'importance': 0.8
                                }
                            )
                            logger.info(f"✅ Consolidated memory stored in MemorySystem for {date_key}")
                        except Exception as e:
                            logger.error(f"Failed to store consolidated memory in MemorySystem: {e}")

                    consolidated_count += 1

                except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                    logger.error(f"Failed to consolidate memories for {date_key}: {e}")

        self.total_consolidated += consolidated_count

        # 📊 Record consolidation metrics for observability
        try:
            metrics = get_metrics_collector()
            metrics.record_consolidation_event(
                trigger='automatic',
                memories_processed=len(consolidation_candidates),
                patterns_extracted=consolidated_count,
                success=consolidated_count > 0,
                metadata={
                    'date_keys': list(time_groups.keys()),
                    'consolidation_timestamp': datetime.now().isoformat()
                }
            )
            metrics.record_brain_region_activation('hippocampus', 'consolidated')
        except Exception as e:
            logger.warning(f"Failed to record consolidation metrics: {e}")

        return {
            'consolidated': consolidated_count,
            'total_consolidated': self.total_consolidated,
            'message': f'Successfully consolidated {consolidated_count} memory patterns'
        }


    async def batch_consolidate(
        self,
        batch_size: int = 50,
        similarity_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        批量记忆巩固 (Batch Consolidation) - Phase 1核心功能

        模拟人脑的睡眠巩固过程:
        1. 每50条记忆触发一次巩固
        2. 聚类相似记忆 (topic clustering)
        3. 提取语义知识
        4. 存储到TemporalLobe
        5. 释放Hippocampus容量

        人脑机制 (Rasch & Born, 2013):
        - 慢波睡眠时,海马体重播记忆序列
        - 新皮层接收并整合为长期知识
        - 海马体释放容量以接收新记忆

        Args:
            batch_size: 批量大小 (默认50条)
            similarity_threshold: 相似度阈值 (默认0.7)

        Returns:
            {
                'consolidated_clusters': int,
                'total_memories_processed': int,
                'clusters': List[Dict]
            }
        """

        if not self.temporal_lobe:
            return {
                'consolidated_clusters': 0,
                'message': 'TemporalLobe not connected'
            }

        if len(self.memories) < batch_size:
            return {
                'consolidated_clusters': 0,
                'message': f'Not enough memories for consolidation (current={len(self.memories)}, required={batch_size})'
            }

        # Step 1: 取最后batch_size条记忆
        batch_memories = self.memories[-batch_size:]

        # Step 2: 聚类相似记忆
        clusters = await self._cluster_memories_by_topic(
            memories=batch_memories,
            similarity_threshold=similarity_threshold
        )

        consolidated_count = 0
        cluster_details = []

        # Step 3: 对每个cluster提取语义知识
        for cluster_id, cluster_mems in clusters.items():
            if len(cluster_mems) < 2:
                continue  # 跳过单个记忆的cluster

            # 提取语义知识
            semantic_knowledge = await self._extract_semantic_knowledge(cluster_mems)

            # 存储到TemporalLobe
            try:
                await self.temporal_lobe.process_message(AgentMessage(
                    sender='hippocampus',
                    receiver='temporal_lobe',
                    message_type='request',
                    content={
                        'action': 'store_semantic',
                        'content': semantic_knowledge['summary'],
                        'memory_subtype': 'consolidated_cluster',
                        'entities': semantic_knowledge['entities'],
                        'relations': semantic_knowledge['relations'],
                        'importance': 0.8,
                        'metadata': {
                            'consolidated_from': [m.id for m in cluster_mems],
                            'cluster_id': cluster_id,
                            'consolidation_time': datetime.now().isoformat(),
                            'cluster_topic': semantic_knowledge.get('topic', 'unknown')
                        }
                    }
                ))

                consolidated_count += 1
                cluster_details.append({
                    'cluster_id': cluster_id,
                    'memory_count': len(cluster_mems),
                    'topic': semantic_knowledge.get('topic', 'unknown'),
                    'entities': semantic_knowledge['entities']
                })


            except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                logger.error(f"Failed to consolidate cluster {cluster_id}: {e}")

        self.total_consolidated += consolidated_count

        return {
            'consolidated_clusters': consolidated_count,
            'total_memories_processed': len(batch_memories),
            'clusters': cluster_details,
            'total_consolidated': self.total_consolidated
        }


    async def _cluster_memories_by_topic(
        self,
        memories: List[EpisodicMemory],
        similarity_threshold: float = 0.7
    ) -> Dict[str, List[EpisodicMemory]]:
        """
        按主题聚类记忆 (Topic Clustering)

        使用简单的贪婪聚类算法:
        1. 按时间顺序遍历记忆
        2. 如果与当前cluster相似度 > threshold,加入
        3. 否则创建新cluster

        Args:
            memories: 记忆列表
            similarity_threshold: 相似度阈值

        Returns:
            {cluster_id: [EpisodicMemory, ...]}
        """

        if not memories:
            return {}

        clusters: Dict[str, List[EpisodicMemory]] = {}
        current_cluster_id = None
        current_cluster_embedding = None

        for mem in memories:
            if not mem.embedding:
                # 没有embedding的记忆单独成cluster
                single_cluster_id = f"cluster_{mem.id[:8]}"
                clusters[single_cluster_id] = [mem]
                continue

            # 如果是第一个记忆,创建第一个cluster
            if current_cluster_id is None:
                current_cluster_id = f"cluster_{len(clusters)}"
                clusters[current_cluster_id] = [mem]
                current_cluster_embedding = mem.embedding
                continue

            # 计算与当前cluster的相似度
            similarity = self._cosine_similarity(mem.embedding, current_cluster_embedding)

            if similarity >= similarity_threshold:
                # 加入当前cluster
                clusters[current_cluster_id].append(mem)
                # 更新cluster embedding (平均)
                current_cluster_embedding = self._average_embeddings(
                    [m.embedding for m in clusters[current_cluster_id] if m.embedding]
                )
            else:
                # 创建新cluster
                current_cluster_id = f"cluster_{len(clusters)}"
                clusters[current_cluster_id] = [mem]
                current_cluster_embedding = mem.embedding

        return clusters


    def _average_embeddings(self, embeddings: List[List[float]]) -> List[float]:
        """计算embedding的平均值"""
        import numpy as np

        if not embeddings:
            return []

        arr = np.array(embeddings)
        avg = np.mean(arr, axis=0)
        return avg.tolist()


    async def _extract_semantic_knowledge(
        self,
        cluster_memories: List[EpisodicMemory]
    ) -> Dict[str, Any]:
        """
        从记忆cluster中提取语义知识

        使用LLM提取:
        1. 主题 (topic)
        2. 核心事实 (core facts)
        3. 实体关系 (entity relations)
        4. 摘要 (summary)

        Args:
            cluster_memories: 聚类的记忆列表

        Returns:
            {
                'topic': str,
                'summary': str,
                'entities': List[str],
                'relations': List[tuple]
            }
        """

        # 合并记忆内容
        combined_content = "\n".join([
            f"[{m.timestamp.strftime('%H:%M')}] {m.speaker or 'Unknown'}: {m.content}"
            for m in cluster_memories
        ])

        # 收集所有实体
        all_entities = list(set(sum([m.entities for m in cluster_memories], [])))

        # 使用LLM提取语义知识
        prompt = f"""从以下{len(cluster_memories)}条情节记忆中提取核心语义知识:

{combined_content}

请提取:
1. **主题**: 这些记忆的共同主题 (1-5个词)
2. **核心事实**: 最重要的3-5个事实
3. **实体关系**: 实体之间的关系 (如果有)
4. **摘要**: 简洁的总结 (2-3句话)

以JSON格式输出:
{{
  "topic": "主题",
  "core_facts": ["事实1", "事实2", ...],
  "relations": [["实体1", "关系", "实体2"], ...],
  "summary": "摘要"
}}

只输出JSON,不要其他文字。"""

        try:
            result = await self.call_llm(
                prompt=prompt,
                max_tokens=800,
                temperature=0.3
            )

            # 解析JSON
            import json
            import re
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())

                return {
                    'topic': parsed.get('topic', 'unknown'),
                    'summary': parsed.get('summary', combined_content[:200]),
                    'entities': all_entities,
                    'relations': [tuple(r) for r in parsed.get('relations', [])]
                }
            else:
                raise ValueError("No JSON found in LLM response")

        except (json.JSONDecodeError) as e:
            logger.warning(f"Failed to extract semantic knowledge via LLM: {e}")
            # Fallback
            return {
                'topic': 'consolidated_memories',
                'summary': f"Consolidated {len(cluster_memories)} memories",
                'entities': all_entities,
                'relations': []
            }

    # ============================================================================
    # Phase 1: Temporal Reasoning (时间推理检索)
    # ============================================================================


    async def get_consolidation_candidates(
        self,
        min_access_count: int = 3,
        min_age_hours: float = 24,
        max_count: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取待巩固的情节记忆候选

        用于协调层的巩固流程:
        - 被访问多次的重要记忆
        - 存在超过一定时间的记忆
        - 未被标记为已巩固的记忆

        Args:
            min_access_count: 最小访问次数 (默认3次)
            min_age_hours: 最小存在时间(小时) (默认24小时)
            max_count: 最大返回数量 (默认50)

        Returns:
            候选记忆列表 (字典格式)
        """
        now = datetime.now()
        candidates = []

        for mem in self.memories:
            # 检查是否满足巩固条件
            age_hours = (now - mem.timestamp).total_seconds() / 3600

            # 条件1: 访问次数足够
            if mem.access_count < min_access_count:
                continue

            # 条件2: 存在时间足够
            if age_hours < min_age_hours:
                continue

            # 条件3: 未被标记为已巩固
            if mem.metadata.get('consolidated', False):
                continue

            # 条件4: 重要性或情绪强度足够
            if mem.importance < 0.5 and mem.emotion_intensity < 0.6:
                continue

            candidates.append(self._memory_to_dict(mem))

        # 按重要性和访问次数排序
        candidates.sort(
            key=lambda m: (m['importance'], m['access_count']),
            reverse=True
        )

        # 限制返回数量
        candidates = candidates[:max_count]

        # 🎯 P2优化: 增强日志显示阈值信息
        if min_age_hours < 1:
            age_display = f"{min_age_hours * 60:.1f}min"
        else:
            age_display = f"{min_age_hours}h"

        logger.info(f"Forgetting candidates found: {len(candidates)} memories "
                   f"(min_access={min_access_count}, min_age={age_display})")

        return candidates


    async def mark_as_consolidated(
        self,
        episode_ids: List[str],
        semantic_id: str
    ) -> int:
        """
        标记情节记忆为已巩固

        在协调层成功巩固后调用，防止重复巩固

        Args:
            episode_ids: 情节记忆ID列表
            semantic_id: 对应的语义记忆ID

        Returns:
            标记的记忆数量
        """
        marked_count = 0

        for episode_id in episode_ids:
            if episode_id in self.memory_dict:
                mem = self.memory_dict[episode_id]
                mem.metadata['consolidated'] = True
                mem.metadata['semantic_id'] = semantic_id
                mem.metadata['consolidation_time'] = datetime.now().isoformat()
                marked_count += 1

                logger.debug(f"Marked {episode_id[:8]} consolidated "
                   f"(semantic_id={semantic_id[:8]})")

        return marked_count

    # ============================================================================
    # Forgetting Interface Methods (for BrainCoordinator)
    # ============================================================================


