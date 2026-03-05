from ..utils.parameters import LLMParams, MemoryParams, RetrievalParams, ProcessingParams, ThresholdParams
"""
Adaptive Consolidation Manager - 自适应巩固管理器

类脑原理:
- 模拟睡眠时的记忆巩固过程（memory consolidation during sleep）
- 接收反馈信号 → 找到相关记忆 → 重新提取事实 → 更新存储
- 不硬编码提取规则，而是根据反馈信号中的 hints 动态调整

核心功能:
1. 接收 ConsolidationFeedbackSignal
2. 根据 query_entities 找到相关记忆
3. 使用 LLM 根据 missing_fact_hints 重新提取事实
4. 将新事实存储到语义存储（KG/Temporal Lobe）

数据流:
MemoryQualityMonitor → ConsolidationFeedbackSignal → AdaptiveConsolidationManager
                                                           |
                                                           v
                                                    IterativeConsolidation
                                                           |
                                                           v
                                                    KG / Temporal Lobe

Reference: BMAM_FEEDBACK_LOOP_DESIGN.md Section 3.3
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class AdaptiveConsolidationManager:
    """
    Adaptive Consolidation Manager
    自适应巩固管理器

    类脑映射:
    - 海马体 → 皮层的记忆转移（hippocampal-cortical memory transfer）
    - 睡眠期间的记忆重播（memory replay during sleep）
    - 系统性巩固（systems consolidation）

    关键设计:
    1. 不硬编码提取规则 - 根据 missing_fact_hints 动态生成 prompt
    2. 迭代巩固 - 多轮提取，每轮聚焦不同方面
    3. 自适应阈值 - 根据历史效果调整巩固策略
    """

    def __init__(
        self,
        hippocampus=None,
        temporal_lobe=None,
        memory_coordinator=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化自适应巩固管理器

        Args:
            hippocampus: HippocampusAgent 实例（用于检索相关记忆）
            temporal_lobe: TemporalLobeAgent 实例（用于存储提取的事实）
            memory_coordinator: MemoryCoordinator 实例（可选，用于完整功能）
            config: 配置参数
        """
        self.hippocampus = hippocampus
        self.temporal_lobe = temporal_lobe
        self.memory_coordinator = memory_coordinator
        self.config = config or {}

        # 巩固配置
        self.max_consolidation_rounds = self.config.get('max_consolidation_rounds', 3)
        self.batch_size = self.config.get('batch_size', 10)
        self.min_urgency_for_immediate = self.config.get('min_urgency_for_immediate', 0.8)

        # 巩固历史（用于效果评估）
        self.consolidation_history: List[Dict[str, Any]] = []
        self.max_history = self.config.get('max_history', 100)

        # 待处理信号队列
        self.pending_signals: List[Dict[str, Any]] = []

        logger.info("AdaptiveConsolidationManager initialized")

    async def receive_feedback(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        接收反馈信号并决定处理方式

        类脑原理:
        - 高紧迫度信号 → 立即处理（类似紧急记忆巩固）
        - 低紧迫度信号 → 加入队列，批量处理（类似睡眠巩固）

        Args:
            signal: ConsolidationFeedbackSignal 字典

        Returns:
            处理结果
        """
        urgency = signal.get('urgency', 0.5)
        feedback_type = signal.get('feedback_type', 'refine')
        entities = signal.get('query_entities', [])

        logger.info(
            f"📥 Received feedback signal: type={feedback_type}, "
            f"urgency={urgency:.2f}, entities={entities}"
        )

        if urgency >= self.min_urgency_for_immediate:
            # 高紧迫度：立即处理
            logger.info(f"⚡ High urgency ({urgency:.2f}) - processing immediately")
            return await self._process_signal_immediately(signal)
        else:
            # 低紧迫度：加入队列
            self.pending_signals.append({
                'signal': signal,
                'received_at': datetime.now().isoformat()
            })
            logger.info(
                f"📋 Low urgency ({urgency:.2f}) - queued for batch processing "
                f"(queue size: {len(self.pending_signals)})"
            )
            return {
                'status': 'queued',
                'queue_size': len(self.pending_signals),
                'urgency': urgency
            }

    async def _process_signal_immediately(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        立即处理高紧迫度信号

        Args:
            signal: ConsolidationFeedbackSignal 字典

        Returns:
            处理结果
        """
        entities = signal.get('query_entities', [])
        missing_hints = signal.get('missing_fact_hints', [])
        failed_query = signal.get('failed_query', '')

        if not entities:
            logger.warning("No entities in signal, cannot process")
            return {'status': 'skipped', 'reason': 'no_entities'}

        # Step 1: 检索相关记忆
        related_memories = await self._retrieve_related_memories(entities)

        if not related_memories:
            logger.warning(f"No related memories found for entities: {entities}")
            return {'status': 'skipped', 'reason': 'no_memories'}

        logger.info(f"📚 Found {len(related_memories)} related memories")

        # Step 2: 迭代巩固
        consolidation_result = await self._iterative_consolidation(
            memories=related_memories,
            entities=entities,
            missing_hints=missing_hints,
            original_query=failed_query
        )

        # Step 3: 记录历史
        self._record_consolidation(signal, consolidation_result)

        return consolidation_result

    async def _retrieve_related_memories(self, entities: List[str]) -> List[Dict[str, Any]]:
        """
        检索与实体相关的记忆

        Args:
            entities: 实体列表

        Returns:
            相关记忆列表
        """
        memories = []

        if self.hippocampus:
            try:
                # 使用海马体的实体索引检索
                for entity in entities:
                    entity_memories = await self.hippocampus.retrieve_by_entity(
                        entity=entity,
                        limit=self.batch_size
                    )
                    memories.extend(entity_memories)
            except Exception as e:
                logger.warning(f"Failed to retrieve from hippocampus: {e}")

        if self.memory_coordinator:
            try:
                # 使用 memory coordinator 的智能检索
                for entity in entities:
                    result = await self.memory_coordinator.smart_retrieve(
                        query=f"Information about {entity}",
                        k=self.batch_size
                    )
                    if isinstance(result, list):
                        memories.extend(result)
            except Exception as e:
                logger.warning(f"Failed to retrieve from memory coordinator: {e}")

        # 去重
        seen_ids = set()
        unique_memories = []
        for mem in memories:
            mem_id = mem.get('id') if isinstance(mem, dict) else getattr(mem, 'id', None)
            if mem_id and mem_id not in seen_ids:
                seen_ids.add(mem_id)
                unique_memories.append(mem)

        return unique_memories[:self.batch_size * 2]  # 限制总量

    async def _iterative_consolidation(
        self,
        memories: List[Dict[str, Any]],
        entities: List[str],
        missing_hints: List[str],
        original_query: str
    ) -> Dict[str, Any]:
        """
        迭代巩固：多轮提取，每轮聚焦不同方面

        类脑原理:
        - 模拟睡眠时的多次记忆重播
        - 每次重播强化不同类型的连接

        Args:
            memories: 相关记忆列表
            entities: 实体列表
            missing_hints: 缺失事实类型提示（来自 LLM 推断，非硬编码）
            original_query: 原始失败的查询

        Returns:
            巩固结果
        """
        all_extracted_facts = []
        all_extracted_triples = []

        # 合并记忆内容
        memory_contents = []
        for mem in memories[:10]:  # 限制数量
            if isinstance(mem, dict):
                content = mem.get('content', '')
            elif hasattr(mem, 'content'):
                content = mem.content
            else:
                content = str(mem)

            if content:
                memory_contents.append(content)

        combined_content = '\n'.join(memory_contents)

        if not combined_content:
            return {
                'status': 'no_content',
                'facts_extracted': 0,
                'triples_extracted': 0
            }

        # 多轮巩固
        for round_num in range(self.max_consolidation_rounds):
            logger.info(f"  🔄 Consolidation round {round_num + 1}/{self.max_consolidation_rounds}")

            # 生成动态 prompt（基于 missing_hints，不硬编码）
            facts, triples = await self._extract_facts_with_llm(
                content=combined_content,
                entities=entities,
                focus_hints=missing_hints,
                round_num=round_num,
                original_query=original_query
            )

            all_extracted_facts.extend(facts)
            all_extracted_triples.extend(triples)

            # 如果提取到足够的事实，提前结束
            if len(all_extracted_facts) >= 5 or len(all_extracted_triples) >= 5:
                logger.info(f"  ✅ Sufficient facts extracted, stopping early")
                break

        # 存储提取的事实
        storage_result = await self._store_extracted_facts(
            facts=all_extracted_facts,
            triples=all_extracted_triples,
            entities=entities
        )

        return {
            'status': 'completed',
            'rounds': round_num + 1,
            'facts_extracted': len(all_extracted_facts),
            'triples_extracted': len(all_extracted_triples),
            'storage_result': storage_result
        }

    async def _extract_facts_with_llm(
        self,
        content: str,
        entities: List[str],
        focus_hints: List[str],
        round_num: int,
        original_query: str
    ) -> tuple[List[str], List[Dict[str, str]]]:
        """
        使用 LLM 提取事实（动态 prompt，不硬编码）

        类脑原理:
        - 不硬编码"提取 is_a 关系"
        - 根据 focus_hints 动态生成提取重点
        - LLM 自己决定如何解释和提取

        Args:
            content: 记忆内容
            entities: 相关实体
            focus_hints: 提取重点提示（来自 MemoryQualityMonitor 的 LLM 推断）
            round_num: 当前轮次
            original_query: 原始查询（用于上下文）

        Returns:
            (facts, triples)
        """
        try:
            from ..services.shared_openai_client import shared_client_manager
            from ..utils.model_selector import select_model_for_task

            client = await shared_client_manager.get_chat_client()
            model = select_model_for_task('consolidation')

            # 动态生成 prompt（基于 hints，不硬编码）
            focus_description = ', '.join(focus_hints) if focus_hints else 'general facts'
            entities_str = ', '.join(entities)

            prompt = f"""Extract SPECIFIC FACTS from the text below about: {entities_str}

**Context**: A question "{original_query}" failed to get a good answer.
The system needs facts about: {focus_description}

**Extraction Focus (Round {round_num + 1})**:
{self._get_round_focus(round_num, focus_hints)}

**Text to analyze**:
{content[:2000]}

**Output Requirements**:
1. Extract concrete, verifiable facts (not opinions or dialogue markers)
2. Focus on {focus_description}
3. Be PRECISE - use exact terms from the text

**Output JSON**:
{{
  "facts": [
    "Person X has characteristic Y",
    "Person X performed action Z",
    ...
  ],
  "triples": [
    {{"subject": "Person", "predicate": "is_a", "object": "characteristic"}},
    {{"subject": "Person", "predicate": "action", "object": "object"}},
    ...
  ]
}}

Only output valid JSON. Extract 3-5 facts/triples maximum."""

            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a fact extraction expert. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=LLMParams.temperature_low(),
                max_tokens=LLMParams.max_tokens_long()
            )

            result_text = response.choices[0].message.content.strip()

            # 解析 JSON
            import json
            import re
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                facts = result.get('facts', [])
                triples = result.get('triples', [])

                logger.debug(f"Round {round_num + 1}: extracted {len(facts)} facts, {len(triples)} triples")
                return facts, triples

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")

        return [], []

    def _get_round_focus(self, round_num: int, hints: List[str]) -> str:
        """
        获取当前轮次的提取重点

        不硬编码，而是根据 hints 和轮次动态调整
        """
        if not hints:
            hints = ['identity', 'activities', 'relationships']

        # 轮流聚焦不同 hint
        if round_num < len(hints):
            current_focus = hints[round_num]
        else:
            current_focus = hints[round_num % len(hints)]

        focus_descriptions = {
            'identity': 'Focus on WHO the person is, their identity, characteristics, and attributes.',
            'occupation': 'Focus on WHAT they do, their job, profession, or role.',
            'location': 'Focus on WHERE they are/were, places they lived or visited.',
            'activity': 'Focus on WHAT they do, their activities, research, or interests.',
            'relationship': 'Focus on WHO they know, relationships with other people.',
            'general_fact': 'Extract any important factual information.',
        }

        return focus_descriptions.get(current_focus, f"Focus on: {current_focus}")

    async def _store_extracted_facts(
        self,
        facts: List[str],
        triples: List[Dict[str, str]],
        entities: List[str]
    ) -> Dict[str, Any]:
        """
        存储提取的事实到语义存储

        Args:
            facts: 提取的事实列表
            triples: 提取的三元组列表
            entities: 相关实体

        Returns:
            存储结果
        """
        stored_facts = 0
        stored_triples = 0

        # 存储到 Temporal Lobe（如果可用）
        if self.temporal_lobe and triples:
            try:
                # 转换为 KG 格式
                relations = [
                    {
                        'source': t.get('subject', ''),
                        'relation': t.get('predicate', ''),
                        'target': t.get('object', ''),
                        'confidence': 0.9,  # 高置信度（来自巩固）
                        'extraction_source': 'consolidation'  # 标记来源
                    }
                    for t in triples
                    if t.get('subject') and t.get('predicate') and t.get('object')
                ]

                if relations and hasattr(self.temporal_lobe, 'ingest_kg_relations'):
                    await self.temporal_lobe.ingest_kg_relations(
                        relations,
                        source_region='adaptive_consolidation'
                    )
                    stored_triples = len(relations)
                    logger.info(f"✅ Stored {stored_triples} triples to Temporal Lobe KG")

            except Exception as e:
                logger.error(f"Failed to store triples to Temporal Lobe: {e}")

        # 存储事实文本（如果 memory coordinator 可用）
        if self.memory_coordinator and facts:
            try:
                for fact in facts[:5]:  # 限制数量
                    await self.memory_coordinator.store_memory(
                        content=fact,
                        memory_type='semantic',
                        metadata={
                            'source': 'consolidation',
                            'entities': entities,
                            'importance': 0.9
                        }
                    )
                    stored_facts += 1

                logger.info(f"✅ Stored {stored_facts} facts to memory system")

            except Exception as e:
                logger.error(f"Failed to store facts: {e}")

        return {
            'stored_facts': stored_facts,
            'stored_triples': stored_triples
        }

    def _record_consolidation(self, signal: Dict[str, Any], result: Dict[str, Any]):
        """记录巩固历史"""
        record = {
            'signal': signal,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }

        self.consolidation_history.append(record)

        # 限制历史大小
        if len(self.consolidation_history) > self.max_history:
            self.consolidation_history = self.consolidation_history[-self.max_history:]

    async def process_pending_batch(self) -> Dict[str, Any]:
        """
        批量处理待处理的低紧迫度信号

        类脑原理:
        - 模拟睡眠期间的批量记忆巩固
        - 低紧迫度信号累积后一起处理

        Returns:
            批量处理结果
        """
        if not self.pending_signals:
            return {'processed': 0, 'queue_empty': True}

        logger.info(f"🌙 Processing batch of {len(self.pending_signals)} pending signals")

        processed = 0
        errors = 0

        for pending in self.pending_signals[:self.batch_size]:
            signal = pending.get('signal', {})
            try:
                await self._process_signal_immediately(signal)
                processed += 1
            except Exception as e:
                logger.error(f"Failed to process signal: {e}")
                errors += 1

        # 清除已处理的信号
        self.pending_signals = self.pending_signals[self.batch_size:]

        return {
            'processed': processed,
            'errors': errors,
            'remaining': len(self.pending_signals)
        }

    def get_statistics(self) -> Dict[str, Any]:
        """获取巩固管理器统计"""
        return {
            'pending_signals': len(self.pending_signals),
            'consolidation_history_size': len(self.consolidation_history),
            'max_consolidation_rounds': self.max_consolidation_rounds,
            'batch_size': self.batch_size,
            'min_urgency_for_immediate': self.min_urgency_for_immediate
        }
