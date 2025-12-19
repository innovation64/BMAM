"""
Memory Consolidation Engine - 记忆巩固引擎
基于学习日志自动巩固高价值记忆，实现经验累积
"""

import json
import logging
from typing import Dict, Any, List, Optional
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)
from ..services.shared_openai_client import shared_client_manager
from ..utils.config import get_settings
from ..utils.model_selector import select_model_for_task  # 🔥 消除硬编码


class MemoryConsolidationEngine:
    """
    记忆巩固引擎

    功能:
    1. 扫描学习日志，识别高频使用的记忆
    2. 将情节记忆 (episodic) 提取为语义知识 (semantic)
    3. 自动更新记忆的 hit_count 和 confidence
    4. 遗忘低价值、长期未使用的记忆
    """

    def __init__(
        self,
        memory_system,
        hippocampus_agent,
        temporal_lobe_agent,
        learning_log_path: str = None
    ):
        # 🔥 使用 BMAMPaths 统一路径管理
        from ..utils.paths import BMAMPaths
        self.memory_system = memory_system
        self.hippocampus = hippocampus_agent
        self.temporal_lobe = temporal_lobe_agent
        self.learning_log_path = learning_log_path if learning_log_path else str(BMAMPaths.LEARNING_CASES_LOG)

        # 巩固阈值
        self.consolidation_threshold = 3  # hit_count ≥ 3 触发巩固
        self.semantic_extraction_threshold = 5  # hit_count ≥ 5 提取语义

        # 遗忘阈值
        self.forgetting_decay_threshold = 0.3
        self.forgetting_age_days = 30  # 30天未使用

    async def consolidate_from_learning_log(self) -> Dict[str, Any]:
        """
        从学习日志中巩固高频记忆

        Returns:
            巩固统计信息
        """

        # 1. 加载学习日志
        logs = self._load_learning_logs()
        if not logs:
            return {'consolidated_count': 0, 'semantic_extracted': 0}

        # 2. 统计记忆使用频率
        memory_usage = self._analyze_memory_usage(logs)

        # 3. 更新记忆元数据（hit_count, confidence）
        updated_count = await self._update_memory_metadata(memory_usage)

        # 4. 提取语义知识
        semantic_count = await self._extract_semantic_knowledge(memory_usage)

        # 5. 巩固关联记忆
        association_count = await self._consolidate_associations(memory_usage)

        logger.info(
            f"✅ Consolidated {updated_count} memories, "
            f"{semantic_count} semantic extracted, {association_count} associations")

        return {
            'consolidated_count': updated_count,
            'semantic_extracted': semantic_count,
            'associations_strengthened': association_count,
            'total_logs_processed': len(logs)
        }

    async def adaptive_forgetting(self) -> Dict[str, Any]:
        """
        自适应遗忘：清理低价值记忆

        Returns:
            遗忘统计信息
        """

        # 1. 获取所有记忆
        all_memories = await self._get_all_memories()

        forgotten_count = 0
        decay_adjusted = 0

        now = datetime.now()

        for mem in all_memories:
            metadata = mem.get('metadata', {})
            decay_factor = metadata.get('decay_factor', 1.0)
            hit_count = metadata.get('hit_count', 0)
            last_accessed = metadata.get('last_accessed')

            # 计算年龄
            if last_accessed:
                try:
                    last_accessed_dt = datetime.fromisoformat(last_accessed)
                    age_days = (now - last_accessed_dt).days
                except (ValueError, TypeError) as e:
                    logger.debug(f"Failed to parse last_accessed time: {e}")
                    age_days = 0
            else:
                age_days = 0

            # 遗忘条件: 衰减严重 + 长期未使用
            if (decay_factor < self.forgetting_decay_threshold and
                hit_count < 2 and
                age_days > self.forgetting_age_days):

                try:
                    await self.memory_system.delete_memory(mem['id'])
                    forgotten_count += 1
                    logger.info(f"❌ Forgot memory {mem['id'][:8]} "
                               f"(decay={decay_factor:.2f}, age={age_days}d)")
                except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                    logger.error(f"Failed to forget memory {mem['id']}: {e}")

            # 调整衰减因子（未使用的记忆逐渐衰减）
            elif age_days > 7 and hit_count == 0:
                new_decay = max(0.1, decay_factor - 0.1)
                metadata['decay_factor'] = new_decay

                try:
                    await self.memory_system.update_memory(mem['id'], metadata=metadata)
                    decay_adjusted += 1
                except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                    logger.error(f"Failed to adjust decay for {mem['id']}: {e}")

        logger.info(f"📊 Adaptive forgetting: {forgotten_count} forgotten, "
                   f"{decay_adjusted} decay adjusted")

        return {
            'forgotten_count': forgotten_count,
            'decay_adjusted': decay_adjusted,
            'total_memories_scanned': len(all_memories)
        }

    def _load_learning_logs(self) -> List[Dict[str, Any]]:
        """加载学习日志"""
        logs = []

        if not Path(self.learning_log_path).exists():
            logger.warning(f"Learning log file not found: {self.learning_log_path}")
            return logs

        try:
            with open(self.learning_log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            logs.append(json.loads(line))
                        except (json.JSONDecodeError) as e:
                            logger.warning(f"Failed to parse log line: {e}")
                            continue

        except (IOError, OSError) as e:
            logger.error(f"Failed to load learning logs: {e}")

        return logs

    def _analyze_memory_usage(self, logs: List[Dict[str, Any]]) -> Dict[str, Dict]:
        """
        分析记忆使用情况

        Returns:
            {memory_id: {hit_count, success_count, failure_count, avg_confidence}}
        """
        memory_stats = defaultdict(lambda: {
            'hit_count': 0,
            'success_count': 0,
            'failure_count': 0,
            'confidences': [],
            'queries': []
        })

        for log in logs:
            log_type = log.get('type', 'unknown')
            memories_used = log.get('memories_used', [])

            # 可能是id列表或详细dict列表
            if memories_used and isinstance(memories_used[0], dict):
                memory_ids = [m.get('id') for m in memories_used if m.get('id')]
            else:
                memory_ids = memories_used

            for mem_id in memory_ids:
                memory_stats[mem_id]['hit_count'] += 1
                memory_stats[mem_id]['queries'].append(log.get('query', ''))

                # 成功/失败统计
                if log_type == 'success' or log.get('score', 0) > 0.5:
                    memory_stats[mem_id]['success_count'] += 1
                else:
                    memory_stats[mem_id]['failure_count'] += 1

                # 置信度
                if 'confidence' in log:
                    memory_stats[mem_id]['confidences'].append(log['confidence'])

        # 计算平均置信度
        for mem_id, stats in memory_stats.items():
            if stats['confidences']:
                stats['avg_confidence'] = sum(stats['confidences']) / len(stats['confidences'])
            else:
                stats['avg_confidence'] = 0.5

        logger.info(f"Memory usage analysis: {len(memory_stats)} memories analyzed")
        return dict(memory_stats)

    async def _update_memory_metadata(self, memory_usage: Dict[str, Dict]) -> int:
        """更新记忆元数据（hit_count, confidence）"""
        updated_count = 0

        for mem_id, stats in memory_usage.items():
            try:
                # 获取记忆
                memory = await self.memory_system.get_memory(mem_id)
                if not memory:
                    continue

                metadata = memory.get('metadata', {})

                # 更新 hit_count
                current_hit = metadata.get('hit_count', 0)
                new_hit = current_hit + stats['hit_count']
                metadata['hit_count'] = new_hit

                # 更新 confidence（基于成功率）
                total_uses = stats['success_count'] + stats['failure_count']
                if total_uses > 0:
                    success_rate = stats['success_count'] / total_uses
                    # 结合原始confidence和成功率
                    current_conf = metadata.get('confidence', 0.5)
                    new_conf = 0.7 * current_conf + 0.3 * success_rate
                    metadata['confidence'] = max(0.1, min(1.0, new_conf))

                # 更新 last_accessed
                metadata['last_accessed'] = datetime.now().isoformat()

                # 保存
                await self.memory_system.update_memory(mem_id, metadata=metadata)
                updated_count += 1

                logger.debug(f"Updated {mem_id[:8]} → hit_count={new_hit}, "
                           f"confidence={metadata.get('confidence', 0):.2f}")

            except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                logger.error(f"Failed to update memory {mem_id}: {e}")

        return updated_count

    async def _extract_semantic_knowledge(self, memory_usage: Dict[str, Dict]) -> int:
        """从高频情节记忆提取语义知识"""
        semantic_count = 0

        for mem_id, stats in memory_usage.items():
            # 只处理高频记忆
            if stats['hit_count'] < self.semantic_extraction_threshold:
                continue

            try:
                # 获取记忆
                memory = await self.memory_system.get_memory(mem_id)
                if not memory:
                    continue

                # 只处理 episodic 类型
                if memory.get('memory_type') != 'episodic':
                    continue

                # 检查是否已经提取过
                if memory.get('metadata', {}).get('semantic_extracted'):
                    continue

                # 提取语义（简化版：去除时间细节，保留核心概念）
                semantic_content = await self._extract_semantic_from_episodic(
                    memory.get('content', ''),
                    stats['queries']
                )

                # 存储到 Temporal Lobe
                semantic_memory = {
                    'content': semantic_content,
                    'memory_type': 'semantic',
                    'metadata': {
                        'source_episode': mem_id,
                        'consolidation_count': stats['hit_count'],
                        'extracted_at': datetime.now().isoformat(),
                        'confidence': stats['avg_confidence']
                    }
                }

                await self.temporal_lobe.store(semantic_memory)
                semantic_count += 1

                # 标记原记忆
                memory['metadata']['semantic_extracted'] = True
                await self.memory_system.update_memory(mem_id, metadata=memory['metadata'])

                logger.debug(f"Extracted semantic from {mem_id[:8]}")
            except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                logger.error(f"Failed to extract semantic from {mem_id}: {e}")

        return semantic_count

    async def _consolidate_associations(self, memory_usage: Dict[str, Dict]) -> int:
        """巩固相关记忆的关联"""
        association_count = 0

        # 识别经常一起使用的记忆对
        co_occurrence = defaultdict(lambda: defaultdict(int))

        logs = self._load_learning_logs()
        for log in logs:
            memories_used = log.get('memories_used', [])
            if isinstance(memories_used[0], dict) if memories_used else False:
                memory_ids = [m.get('id') for m in memories_used if m.get('id')]
            else:
                memory_ids = memories_used

            # 记录共现
            for i in range(len(memory_ids)):
                for j in range(i + 1, len(memory_ids)):
                    co_occurrence[memory_ids[i]][memory_ids[j]] += 1
                    co_occurrence[memory_ids[j]][memory_ids[i]] += 1

        # 为高频共现的记忆对建立/加强关联
        for mem1_id, related in co_occurrence.items():
            for mem2_id, count in related.items():
                if count >= 3:  # 共现3次以上
                    try:
                        # 添加关联
                        await self.memory_system.add_association(
                            mem1_id, mem2_id,
                            strength=min(1.0, count / 10),
                            relation_type='frequently_co_accessed'
                        )
                        association_count += 1

                        logger.debug(f"Associated {mem1_id[:8]} ↔ {mem2_id[:8]} "
                                   f"(co-occurrence={count})")

                    except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                        logger.error(f"Failed to add association {mem1_id}-{mem2_id}: {e}")

        return association_count

    async def _extract_semantic_from_episodic(
        self,
        episodic_content: str,
        related_queries: List[str]
    ) -> str:
        """
        从情节记忆提取语义知识
        
        🔥 Optimization: 使用LLM进行深度语义抽象
        将具体的情节 (Episodic) 转化为普适的知识 (Semantic)
        """
        try:
            client = await shared_client_manager.get_chat_client()
            if not client:
                logger.warning("LLM client not available, falling back to regex")
                return self._extract_semantic_regex(episodic_content)

            prompt = f"""
            You are the Hippocampus-Cortex interface of a digital brain.
            Your task is to consolidate a specific Episodic Memory into Semantic Knowledge.
            
            Episodic Memory: "{episodic_content}"
            Context/Queries: {related_queries}
            
            Instructions:
            1. Extract the core timeless fact, rule, or concept.
            2. Remove specific timestamps, transient states, or irrelevant details.
            3. Generalize the information so it applies to future situations.
            4. Output ONLY the consolidated semantic knowledge statement.
            """

            # 🔥 消除硬编码：使用智能模型选择
            consolidation_model = select_model_for_task('consolidation')

            response = await client.chat.completions.create(
                model=consolidation_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=100
            )
            
            semantic = response.choices[0].message.content.strip()
            logger.info(f"🧠 Semantic Consolidation: '{episodic_content}' -> '{semantic}'")
            return semantic

        except Exception as e:
            logger.error(f"LLM consolidation failed: {e}")
            return self._extract_semantic_regex(episodic_content)

    def _extract_semantic_regex(self, episodic_content: str) -> str:
        """
        Regex-based fallback for semantic extraction
        """
        # 移除日期模式
        import re
        semantic = re.sub(r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b', '[DATE]', episodic_content)
        semantic = re.sub(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b', '[DATE]', semantic)

        # 移除具体时间
        semantic = re.sub(r'\b\d{1,2}:\d{2}\s*(AM|PM|am|pm)?\b', '[TIME]', semantic)

        # 移除"yesterday", "last week"等时间词
        temporal_words = ['yesterday', 'today', 'tomorrow', 'last week', 'last month', 'last year']
        for word in temporal_words:
            semantic = semantic.replace(word, '[TIMEREF]')

        # 简化为概念性陈述
        if 'painted' in semantic.lower():
            semantic = re.sub(r'\bon\s+\[DATE\]', '', semantic)
            semantic = re.sub(r'painted', 'paints', semantic)

        return semantic.strip()

    async def _get_all_memories(self) -> List[Dict[str, Any]]:
        """获取所有记忆（简化版）"""
        try:
            # 假设 memory_system 有 get_all 方法
            if hasattr(self.memory_system, 'get_all_memories'):
                return await self.memory_system.get_all_memories()
            else:
                # Fallback: 从不同存储区获取
                memories = []

                if self.hippocampus:
                    hippo_mems = await self.hippocampus.get_all_memories()
                    memories.extend(hippo_mems)

                if self.temporal_lobe:
                    temporal_mems = await self.temporal_lobe.get_all_memories()
                    memories.extend(temporal_mems)

                return memories

        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            logger.error(f"Failed to get all memories: {e}")
            return []


class ConsolidationScheduler:
    """
    巩固调度器

    定期触发巩固和遗忘任务
    """

    def __init__(self, consolidation_engine: MemoryConsolidationEngine):
        self.engine = consolidation_engine
        self.consolidation_interval = timedelta(hours=6)  # 每6小时巩固一次
        self.forgetting_interval = timedelta(days=1)  # 每天遗忘一次
        self.last_consolidation = datetime.now()
        self.last_forgetting = datetime.now()

    async def check_and_run(self):
        """检查是否需要运行巩固/遗忘任务"""
        now = datetime.now()

        # 巩固任务
        if now - self.last_consolidation >= self.consolidation_interval:
            await self.engine.consolidate_from_learning_log()
            self.last_consolidation = now

        # 遗忘任务
        if now - self.last_forgetting >= self.forgetting_interval:
            await self.engine.adaptive_forgetting()
            self.last_forgetting = now
