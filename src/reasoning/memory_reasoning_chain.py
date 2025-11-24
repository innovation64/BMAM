"""
Memory Reasoning Chain - 记忆推理链引擎
类脑设计：模拟人脑如何串联分散的记忆片段构建完整推理链

核心理念：
1. 记忆分散存储（短期/长期/知识图谱）- 符合人脑多区域存储
2. 检索时跨区域协调 - 模拟前额叶的工作记忆整合
3. 构建时间线和因果链 - 模拟海马体的情节记忆序列化
4. 推理综合 - 模拟前额叶的高阶推理

Brain Regions Involved:
- Hippocampus: 短期情节记忆
- Temporal Lobe: 长期语义记忆
- Prefrontal Cortex: 工作记忆整合和推理
- Knowledge Graph: 实体关系网络
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import asyncio
import logging

from ..utils.config import get_settings
from ..utils.model_selector import select_model_for_query, select_model_for_task  # 🔥 消除硬编码

logger = logging.getLogger(__name__)


@dataclass
class MemoryFragment:
    """
    记忆片段
    来自不同存储位置的记忆项的统一表示
    """
    id: str
    content: str
    timestamp: datetime
    source: str  # 'hippocampus', 'memory_system', 'temporal_lobe'
    entities: List[str] = field(default_factory=list)
    importance: float = 0.5
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)


@dataclass
class CausalLink:
    """
    因果关联
    模拟海马体对事件序列的因果推理
    """
    cause: MemoryFragment
    effect: MemoryFragment
    relation_type: str  # 'temporal', 'causal', 'thematic'
    strength: float  # 0.0-1.0
    evidence: str = ""


@dataclass
class ReasoningChain:
    """
    推理链
    完整的记忆串联和推理路径
    """
    memories: List[MemoryFragment]
    causal_links: List[CausalLink]
    timeline: List[Tuple[datetime, MemoryFragment]]
    kg_context: List[Dict[str, Any]]  # KG facts
    confidence: float
    reasoning_steps: List[str] = field(default_factory=list)


class MemoryReasoningChain:
    """
    记忆推理链引擎

    类脑设计：
    1. 多区域检索 - 模拟大脑跨区域信息整合
    2. 工作记忆整合 - 前额叶功能
    3. 时间序列化 - 海马体功能
    4. 因果推理 - 高阶认知功能
    """

    def __init__(
        self,
        hippocampus_agent=None,      # 短期情节记忆
        memory_system=None,           # 长期记忆系统
        kg_builder=None,              # 知识图谱
        temporal_lobe_agent=None,     # 语义记忆
        client_manager=None,          # SharedOpenAIClientManager for LLM
        memory_coordinator=None       # Use coordinator's smart_retrieve instead of custom retrieval
    ):
        """
        Initialize Memory Reasoning Chain Engine

        Args:
            hippocampus_agent: 海马体agent (短期情节记忆)
            memory_system: 全局记忆系统 (长期存储)
            kg_builder: 知识图谱构建器 (实体关系)
            temporal_lobe_agent: 颞叶agent (语义记忆)
            client_manager: SharedOpenAIClientManager (推理综合)
            memory_coordinator: MemoryCoordinator for unified retrieval (避免重复实现检索)
        """
        self.hippocampus = hippocampus_agent
        self.memory_system = memory_system
        self.kg = kg_builder
        self.temporal_lobe = temporal_lobe_agent
        self.client_manager = client_manager
        self.memory_coordinator = memory_coordinator  # Use existing retrieval pipeline

        # Lazy-initialized LLM client (cached after first use)
        self._llm_client = None

        # Statistics
        self.total_retrievals = 0
        self.total_chains_built = 0
        self.avg_chain_length = 0.0

        logger.info(
            f"MemoryReasoningChain initialized "
            f"(hippocampus={'yes' if hippocampus_agent else 'no'}, "
            f"memory_system={'yes' if memory_system else 'no'}, "
            f"kg={'yes' if kg_builder else 'no'}, "
            f"coordinator={'yes' if memory_coordinator else 'no'})"
        )

    async def retrieve_with_reasoning_chain(
        self,
        query: str,
        max_memories: int = 20,
        include_kg: bool = True
    ) -> ReasoningChain:
        """
        跨所有存储位置检索并构建推理链

        Brain-inspired process:
        1. Parallel retrieval from multiple brain regions (分布式检索)
        2. Working memory integration in prefrontal cortex (工作记忆整合)
        3. Timeline construction by hippocampus (时间序列化)
        4. Causal reasoning by prefrontal cortex (因果推理)

        Args:
            query: 查询字符串
            max_memories: 最大记忆数量
            include_kg: 是否包含KG信息

        Returns:
            ReasoningChain: 完整推理链
        """
        self.total_retrievals += 1

        logger.info(f"Building reasoning chain for query: '{query[:50]}...'")

        # Step 1: Use coordinator's unified retrieval (避免重复实现检索)
        raw_memories = []
        all_memories = []

        if self.memory_coordinator:
            # 🔥 Phase 3 Integration: Use cross_region_retrieval for parallel + resonance
            try:
                logger.info(f"🧠 Using MemoryCoordinator.cross_region_retrieval() for parallel multi-region retrieval")

                # cross_region_retrieval() provides:
                # - Parallel retrieval from 5 brain regions (asyncio.gather)
                # - Resonance scoring (cross-region memories ranked higher)
                # - Thalamus dynamic gating integration (selective activation)
                # - Emotional boost (Amygdala memories weighted)
                raw_memories = await self.memory_coordinator.cross_region_retrieval(
                    query=query,
                    top_k=max_memories * 2,  # Retrieve more for reasoning chain construction
                    activation_plan=None  # Use default: activate all regions
                )

                logger.info(f"🧠 Retrieved {len(raw_memories)} memories with resonance scoring")

                # Convert to MemoryFragment format
                all_memories = [
                    self._convert_to_fragment(m, source=m.get('_meta', {}).get('regions', ['coordinator'])[0] if '_meta' in m else 'coordinator')
                    for m in raw_memories
                ]

            except Exception as e:
                logger.warning(f"MemoryCoordinator.cross_region_retrieval() failed: {e}, falling back to smart_retrieve")
                import traceback
                logger.warning(f"Traceback: {traceback.format_exc()}")

                # Fallback to smart_retrieve if cross_region_retrieval fails
                try:
                    raw_memories = await self.memory_coordinator.smart_retrieve(
                        query=query,
                        k=max_memories * 2,
                        strategy='hybrid'
                    )
                    all_memories = [
                        self._convert_to_fragment(m, source=m.get('source', 'coordinator'))
                        for m in raw_memories
                    ]
                except Exception as e2:
                    logger.error(f"Both cross_region_retrieval and smart_retrieve failed: {e2}")
                    all_memories = []
        else:
            logger.warning("No MemoryCoordinator available, cannot retrieve memories")
            all_memories = []

        # Step 3: Retrieve KG context if enabled
        kg_facts = []
        if include_kg and self.kg:
            kg_facts = await self._retrieve_from_kg(query, all_memories)
            logger.debug(f"Retrieved {len(kg_facts)} KG facts")

        # Step 4: Build timeline (海马体时间序列化)
        timeline = self._build_timeline(all_memories)

        # Step 5: Identify causal relationships (因果推理)
        causal_links = self._identify_causal_links(all_memories, timeline, kg_facts)

        logger.debug(f"Identified {len(causal_links)} causal links")

        # Step 6: Calculate confidence
        confidence = self._calculate_chain_confidence(all_memories, causal_links, kg_facts)

        # Step 7: Construct reasoning chain
        reasoning_chain = ReasoningChain(
            memories=all_memories[:max_memories],
            causal_links=causal_links,
            timeline=timeline,
            kg_context=kg_facts,
            confidence=confidence,
            reasoning_steps=self._extract_reasoning_steps(all_memories, causal_links)
        )

        self.total_chains_built += 1
        self.avg_chain_length = (
            (self.avg_chain_length * (self.total_chains_built - 1) + len(all_memories))
            / self.total_chains_built
        )

        logger.info(
            f"Reasoning chain built: {len(all_memories)} memories, "
            f"{len(causal_links)} causal links, "
            f"confidence={confidence:.2f}"
        )

        return reasoning_chain

    async def _retrieve_from_hippocampus(
        self,
        query: str,
        k: int = 10
    ) -> List[MemoryFragment]:
        """
        从海马体检索短期情节记忆
        """
        if not self.hippocampus:
            return []

        try:
            # Hippocampus has rich retrieval methods
            memories = []

            # Try semantic retrieval
            if hasattr(self.hippocampus, 'retrieve_semantic'):
                results = await self.hippocampus.retrieve_semantic(query, k=k)
                memories.extend(results)

            # Try entity-based retrieval
            if hasattr(self.hippocampus, 'retrieve_by_entity'):
                # Extract potential entities from query
                entities = self._extract_entities_from_query(query)
                for entity in entities[:3]:  # Top 3 entities
                    entity_results = self.hippocampus.retrieve_by_entity(entity, limit=k//2)
                    memories.extend(entity_results)

            # Convert to MemoryFragment
            fragments = [
                self._convert_to_fragment(m, source='hippocampus')
                for m in memories
            ]

            return fragments[:k]

        except Exception as e:
            logger.warning(f"Failed to retrieve from hippocampus: {e}")
            return []

    async def _retrieve_from_memory_system(
        self,
        query: str,
        k: int = 10
    ) -> List[MemoryFragment]:
        """
        从全局记忆系统检索长期记忆
        """
        if not self.memory_system:
            return []

        try:
            # MemorySystem typically has search_memories method
            if hasattr(self.memory_system, 'search_memories'):
                results = await self.memory_system.search_memories(query, k=k)

                fragments = [
                    self._convert_to_fragment(m, source='memory_system')
                    for m in results
                ]

                return fragments
            else:
                return []

        except Exception as e:
            logger.warning(f"Failed to retrieve from memory_system: {e}")
            return []

    async def _retrieve_from_temporal_lobe(
        self,
        query: str,
        k: int = 10
    ) -> List[MemoryFragment]:
        """
        从颞叶检索语义记忆
        """
        if not self.temporal_lobe:
            return []

        try:
            # TemporalLobe has semantic memory
            if hasattr(self.temporal_lobe, 'retrieve_semantic_memory'):
                results = await self.temporal_lobe.retrieve_semantic_memory(query, k=k)

                fragments = [
                    self._convert_to_fragment(m, source='temporal_lobe')
                    for m in results
                ]

                return fragments
            else:
                return []

        except Exception as e:
            logger.warning(f"Failed to retrieve from temporal_lobe: {e}")
            return []

    async def _retrieve_from_kg(
        self,
        query: str,
        memories: List[MemoryFragment]
    ) -> List[Dict[str, Any]]:
        """
        从知识图谱检索相关事实
        """
        if not self.kg:
            return []

        try:
            # Extract entities from query and memories
            all_entities = set()
            all_entities.update(self._extract_entities_from_query(query))

            for mem in memories:
                all_entities.update(mem.entities)

            # Query KG for relations involving these entities
            kg_facts = []

            if hasattr(self.kg, 'knowledge_graph'):
                kg = self.kg.knowledge_graph

                # Get relations for each entity
                for entity in list(all_entities)[:10]:  # Limit to top 10 entities
                    if 'relations' in kg:
                        for r in kg['relations']:
                            # Handle both tuple (subject, predicate, object) and dict formats
                            if isinstance(r, tuple):
                                if len(r) >= 3:
                                    subject, predicate, obj = r[0], r[1], r[2]
                                    if entity.lower() in str(subject).lower() or entity.lower() in str(obj).lower():
                                        kg_facts.append({
                                            'subject': subject,
                                            'predicate': predicate,
                                            'object': obj
                                        })
                            elif isinstance(r, dict):
                                if (entity.lower() in str(r.get('subject', '')).lower() or
                                    entity.lower() in str(r.get('object', '')).lower()):
                                    kg_facts.append(r)

            return kg_facts[:20]  # Max 20 KG facts

        except Exception as e:
            logger.warning(f"Failed to retrieve from KG: {e}")
            return []

    def _normalize_timestamp(self, timestamp: Any) -> datetime:
        """
        规范化时间戳为 datetime 对象
        处理字符串、datetime、None 等各种格式
        """
        if timestamp is None:
            return datetime.now()

        if isinstance(timestamp, datetime):
            return timestamp

        if isinstance(timestamp, str):
            # Try to parse ISO format timestamp
            try:
                from dateutil import parser
                return parser.parse(timestamp)
            except:
                try:
                    # Fallback to basic ISO format
                    return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except:
                    logger.warning(f"Failed to parse timestamp: {timestamp}, using current time")
                    return datetime.now()

        # Fallback for any other type
        return datetime.now()

    def _convert_to_fragment(
        self,
        memory: Any,
        source: str
    ) -> MemoryFragment:
        """
        转换不同格式的记忆为统一的MemoryFragment
        """
        # Handle different memory formats
        if hasattr(memory, 'id'):
            # EpisodicMemory or similar
            raw_timestamp = memory.timestamp if hasattr(memory, 'timestamp') else None
            return MemoryFragment(
                id=memory.id,
                content=memory.content if hasattr(memory, 'content') else str(memory),
                timestamp=self._normalize_timestamp(raw_timestamp),
                source=source,
                entities=memory.entities if hasattr(memory, 'entities') else [],
                importance=memory.importance if hasattr(memory, 'importance') else 0.5,
                embedding=memory.embedding if hasattr(memory, 'embedding') else None,
                metadata=memory.metadata if hasattr(memory, 'metadata') else {}
            )
        elif isinstance(memory, dict):
            # Dict format
            return MemoryFragment(
                id=memory.get('id', memory.get('memory_id', str(hash(str(memory))))),
                content=memory.get('content', memory.get('text', str(memory))),
                timestamp=self._normalize_timestamp(memory.get('timestamp')),
                source=source,
                entities=memory.get('entities', []),
                importance=memory.get('importance', 0.5),
                embedding=memory.get('embedding'),
                metadata=memory.get('metadata', {})
            )
        else:
            # Fallback
            return MemoryFragment(
                id=str(hash(str(memory))),
                content=str(memory),
                timestamp=datetime.now(),
                source=source
            )

    def _merge_and_deduplicate(
        self,
        *memory_lists: List[MemoryFragment]
    ) -> List[MemoryFragment]:
        """
        合并并去重记忆片段

        模拟前额叶工作记忆的整合功能
        """
        seen_ids = set()
        merged = []

        for mem_list in memory_lists:
            for mem in mem_list:
                if mem.id not in seen_ids:
                    seen_ids.add(mem.id)
                    merged.append(mem)

        # Sort by importance and timestamp
        merged.sort(key=lambda m: (m.importance, m.timestamp), reverse=True)

        return merged

    def _build_timeline(
        self,
        memories: List[MemoryFragment]
    ) -> List[Tuple[datetime, MemoryFragment]]:
        """
        构建时间线

        模拟海马体的时间序列化功能
        """
        timeline = [(m.timestamp, m) for m in memories]
        timeline.sort(key=lambda x: x[0])  # Sort by time

        return timeline

    def _identify_causal_links(
        self,
        memories: List[MemoryFragment],
        timeline: List[Tuple[datetime, MemoryFragment]],
        kg_facts: List[Dict[str, Any]]
    ) -> List[CausalLink]:
        """
        识别因果关联

        模拟前额叶的因果推理功能
        """
        causal_links = []

        # Temporal causality: events close in time
        for i, (time1, mem1) in enumerate(timeline):
            for time2, mem2 in timeline[i+1:i+4]:  # Look ahead 3 events
                time_diff = (time2 - time1).total_seconds() / 3600  # hours

                if time_diff < 24:  # Within 24 hours
                    # Check for entity overlap
                    entity_overlap = set(mem1.entities) & set(mem2.entities)

                    if entity_overlap:
                        strength = 0.5 + 0.3 * len(entity_overlap) / max(len(mem1.entities), 1)
                        strength = min(strength, 1.0)

                        causal_links.append(CausalLink(
                            cause=mem1,
                            effect=mem2,
                            relation_type='temporal',
                            strength=strength,
                            evidence=f"Time proximity ({time_diff:.1f}h) + entity overlap: {entity_overlap}"
                        ))

        # Thematic causality: similar topics/entities
        for i, mem1 in enumerate(memories):
            for mem2 in memories[i+1:]:
                if mem1.id != mem2.id:
                    # Entity-based thematic link
                    shared_entities = set(mem1.entities) & set(mem2.entities)

                    if len(shared_entities) >= 2:  # At least 2 shared entities
                        strength = 0.4 + 0.2 * len(shared_entities)
                        strength = min(strength, 0.9)

                        causal_links.append(CausalLink(
                            cause=mem1,
                            effect=mem2,
                            relation_type='thematic',
                            strength=strength,
                            evidence=f"Shared entities: {shared_entities}"
                        ))

        # Sort by strength
        causal_links.sort(key=lambda x: x.strength, reverse=True)

        return causal_links[:15]  # Top 15 strongest links

    def _calculate_chain_confidence(
        self,
        memories: List[MemoryFragment],
        causal_links: List[CausalLink],
        kg_facts: List[Dict[str, Any]]
    ) -> float:
        """
        计算推理链置信度
        """
        if not memories:
            return 0.0

        # Factors
        memory_count_score = min(len(memories) / 10, 1.0)  # More memories = higher confidence
        causal_score = min(len(causal_links) / 5, 1.0)  # More links = higher confidence
        kg_score = min(len(kg_facts) / 10, 1.0) * 0.5  # KG facts boost confidence

        # Average importance of memories
        avg_importance = sum(m.importance for m in memories) / len(memories)

        # Weighted combination
        confidence = (
            memory_count_score * 0.3 +
            causal_score * 0.3 +
            avg_importance * 0.3 +
            kg_score * 0.1
        )

        return min(confidence, 1.0)

    def _extract_reasoning_steps(
        self,
        memories: List[MemoryFragment],
        causal_links: List[CausalLink]
    ) -> List[str]:
        """
        提取推理步骤
        """
        steps = []

        # Add memory retrieval step
        steps.append(f"Retrieved {len(memories)} relevant memories from distributed storage")

        # Add causal reasoning steps
        if causal_links:
            steps.append(f"Identified {len(causal_links)} causal/temporal relationships")

            # Highlight strongest link
            if causal_links:
                strongest = causal_links[0]
                steps.append(
                    f"Strongest link ({strongest.relation_type}, "
                    f"strength={strongest.strength:.2f}): "
                    f"{strongest.cause.content[:50]}... → "
                    f"{strongest.effect.content[:50]}..."
                )

        return steps

    def _extract_entities_from_query(self, query: str) -> List[str]:
        """
        从查询中提取可能的实体

        简单版本：提取首字母大写的词
        """
        words = query.split()
        entities = [
            word.strip('.,?!')
            for word in words
            if word and word[0].isupper() and len(word) > 1
        ]
        return entities

    async def answer_with_reasoning_chain(
        self,
        question: str,
        max_memories: int = 20
    ) -> Dict[str, Any]:
        """
        使用推理链回答问题

        完整的类脑推理流程：
        1. 跨区域检索记忆
        2. 构建推理链
        3. LLM综合推理生成答案

        Args:
            question: 问题
            max_memories: 最大记忆数量

        Returns:
            Dict包含answer, reasoning_chain, confidence等
        """
        # Step 1: Build reasoning chain
        chain = await self.retrieve_with_reasoning_chain(
            query=question,
            max_memories=max_memories,
            include_kg=True
        )

        # Step 2: Synthesize answer using LLM
        answer = await self._synthesize_answer_with_llm(question, chain)

        # Step 3: Format result
        result = {
            'answer': answer,
            'confidence': chain.confidence,
            'memory_count': len(chain.memories),
            'causal_links_count': len(chain.causal_links),
            'reasoning_steps': chain.reasoning_steps,
            'sources': [
                {
                    'id': m.id,
                    'content': m.content[:100],
                    'source': m.source,
                    'timestamp': m.timestamp.isoformat()
                }
                for m in chain.memories[:5]  # Top 5 sources
            ],
            'causal_chain': [
                {
                    'cause': link.cause.content[:80],
                    'effect': link.effect.content[:80],
                    'type': link.relation_type,
                    'strength': link.strength
                }
                for link in chain.causal_links[:3]  # Top 3 links
            ]
        }

        return result

    async def _synthesize_answer_with_llm(
        self,
        question: str,
        chain: ReasoningChain
    ) -> str:
        """
        使用LLM综合推理链生成答案
        """
        if not self.client_manager:
            # Fallback: concatenate memories
            return " ".join([m.content for m in chain.memories[:3]])

        # Build context from reasoning chain
        context_parts = []

        # Add memories in chronological order
        context_parts.append("Relevant memories (chronological order):")
        for i, (timestamp, mem) in enumerate(chain.timeline[:10], 1):
            context_parts.append(
                f"{i}. [{timestamp.strftime('%Y-%m-%d')}] {mem.content}"
            )

        # Add causal relationships
        if chain.causal_links:
            context_parts.append("\nIdentified relationships:")
            for i, link in enumerate(chain.causal_links[:5], 1):
                context_parts.append(
                    f"{i}. {link.cause.content[:60]} → {link.effect.content[:60]} "
                    f"({link.relation_type}, strength={link.strength:.2f})"
                )

        # Add KG facts
        if chain.kg_context:
            context_parts.append("\nKnowledge graph facts:")
            for i, fact in enumerate(chain.kg_context[:5], 1):
                context_parts.append(
                    f"{i}. {fact.get('subject')} - {fact.get('predicate')} - {fact.get('object')}"
                )

        context = "\n".join(context_parts)

        # Build prompt
        prompt = f"""Based on the following memories and their relationships, answer the question.

{context}

Question: {question}

Answer concisely based on the evidence above. If you need to infer, explain your reasoning."""

        try:
            if self.client_manager:
                # Lazy initialization: get client once and cache
                if self._llm_client is None:
                    self._llm_client = await self.client_manager.get_chat_client()

                # 🔥 消除硬编码：使用智能模型选择（基于查询复杂度）
                reasoning_model = select_model_for_query(question, task_type='default')

                # OpenAI-style client (cached)
                response = await self._llm_client.chat.completions.create(
                    model=reasoning_model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that answers questions based on provided memories and relationships."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=500
                )
                answer = response.choices[0].message.content
            else:
                # Fallback
                answer = f"Based on {len(chain.memories)} memories: " + " ".join([m.content for m in chain.memories[:2]])

            return answer

        except Exception as e:
            logger.error(f"LLM synthesis failed: {e}")
            # Fallback answer
            return f"Based on {len(chain.memories)} memories retrieved from {set(m.source for m in chain.memories)}"

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_retrievals': self.total_retrievals,
            'total_chains_built': self.total_chains_built,
            'avg_chain_length': round(self.avg_chain_length, 2),
            'components': {
                'hippocampus': self.hippocampus is not None,
                'memory_system': self.memory_system is not None,
                'kg': self.kg is not None,
                'temporal_lobe': self.temporal_lobe is not None,
                'llm': self.client_manager is not None
            }
        }
