"""
Memory Consolidation Pipeline - 跨脑区记忆巩固管道
Cross-region memory consolidation with HRM coordination

Handles:
1. Episodic → Semantic consolidation (Hippocampus → Temporal Lobe)
2. Emotional enhancement (Amygdala → Hippocampus/Temporal Lobe)
3. Procedural learning (Basal Ganglia)
4. Strategic planning integration (Prefrontal)
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

from .memory_item import MemoryItem
from .brain_region_storage_interface import (
    IBrainRegionStorage,
    HippocampusStorage,
    TemporalLobeStorage,
    AmygdalaStorage
)

logger = logging.getLogger(__name__)


@dataclass
class ConsolidationRequest:
    """
    Memory Consolidation Request
    记忆巩固请求
    """
    memory_id: str
    source_region: str
    target_region: str
    consolidation_type: str  # 'episodic_to_semantic', 'emotional_enhancement', etc.
    priority: float
    metadata: Dict[str, Any]


@dataclass
class ConsolidationResult:
    """
    Memory Consolidation Result
    记忆巩固结果
    """
    success: bool
    source_memory_id: str
    target_memory_id: Optional[str]
    consolidation_type: str
    timestamp: datetime
    metadata: Dict[str, Any]


class MemoryConsolidationPipeline:
    """
    Memory Consolidation Pipeline
    记忆巩固管道

    Coordinates memory consolidation across brain regions:
    - Episodic → Semantic (Hippocampus → Temporal Lobe)
    - Emotional tagging and enhancement (Amygdala)
    - HRM-aware consolidation timing
    """

    def __init__(
        self,
        memory_system=None,
        brain_region_storages: Optional[Dict[str, IBrainRegionStorage]] = None
    ):
        """
        Initialize Consolidation Pipeline

        Args:
            memory_system: Global memory system
            brain_region_storages: Dictionary of brain region storage adapters
        """
        self.memory_system = memory_system
        self.brain_region_storages = brain_region_storages or {}

        # Consolidation queue
        self.consolidation_queue: List[ConsolidationRequest] = []

        # Consolidation history
        self.consolidation_history: List[ConsolidationResult] = []

        # Statistics
        self.stats = {
            'total_consolidations': 0,
            'episodic_to_semantic': 0,
            'emotional_enhancements': 0,
            'failed_consolidations': 0,
            'avg_consolidation_time_ms': 0.0
        }

        logger.info("MemoryConsolidationPipeline initialized")

    def register_storage(
        self,
        region_name: str,
        storage: IBrainRegionStorage
    ) -> None:
        """
        Register Brain Region Storage
        注册脑区存储

        Args:
            region_name: Brain region name
            storage: Storage adapter
        """
        self.brain_region_storages[region_name] = storage
        logger.info(f"Registered storage for region: {region_name}")

    async def consolidate_episodic_to_semantic(
        self,
        episodic_memory_id: str,
        hippocampus_storage: HippocampusStorage,
        temporal_lobe_storage: TemporalLobeStorage,
        priority: float = 0.7
    ) -> ConsolidationResult:
        """
        Consolidate Episodic Memory to Semantic Memory
        将情节记忆巩固为语义记忆

        This is the core consolidation process:
        1. Retrieve episodic memory from Hippocampus
        2. Extract semantic knowledge (entities, relations, concepts)
        3. Store as semantic memory in Temporal Lobe
        4. Update knowledge graph

        Args:
            episodic_memory_id: Episodic memory ID
            hippocampus_storage: Hippocampus storage adapter
            temporal_lobe_storage: Temporal Lobe storage adapter
            priority: Consolidation priority

        Returns:
            ConsolidationResult
        """
        start_time = datetime.now()
        logger.info(f"🔄 Consolidating episodic memory {episodic_memory_id[:16]}... to semantic")

        try:
            # Step 1: Retrieve episodic memory by ID using unified interface
            # Use region_retrieve with ID filter (proxies handle the lookup)
            logger.debug(f"Retrieving memory {episodic_memory_id[:16]}... from hippocampus")

            memory_items = await hippocampus_storage.region_retrieve(
                query='',  # Empty query for ID lookup
                filters={'id': episodic_memory_id},
                k=1
            )

            if not memory_items:
                logger.error(f"❌ Failed to retrieve memory {episodic_memory_id[:16]}... from hippocampus "
                           f"(region_retrieve returned empty list)")
                return self._create_failure_result(
                    episodic_memory_id,
                    'episodic_to_semantic',
                    f'Memory {episodic_memory_id[:16]} not found in hippocampus'
                )

            episodic_memory = memory_items[0]
            logger.info(f"✅ Retrieved episodic memory {episodic_memory_id[:16]}... "
                       f"(content: {episodic_memory.content[:60]}...)")

            # Ensure metadata has entities/relations
            if not episodic_memory.metadata:
                episodic_memory.metadata = {}

            # Validate that we have useful content
            if not episodic_memory.content or len(episodic_memory.content.strip()) < 10:
                logger.warning(f"⚠️  Memory {episodic_memory_id[:16]}... has very short content: "
                             f"'{episodic_memory.content[:50]}'")

            logger.debug(f"Memory metadata keys: {list(episodic_memory.metadata.keys())}")

            # Step 2: Extract semantic knowledge
            semantic_content = self._extract_semantic_knowledge(episodic_memory)

            # Step 3: Create semantic memory
            semantic_memory = MemoryItem(
                content=semantic_content['content'],
                memory_type='semantic',
                importance=episodic_memory.importance * 1.2,  # Boost importance
                context_tags=semantic_content['concepts'],
                metadata={
                    'source': 'episodic_consolidation',
                    'source_memory_id': episodic_memory_id,
                    'consolidated_at': datetime.now().isoformat(),
                    'entities': semantic_content['entities'],
                    'relations': semantic_content['relations']
                }
            )

            logger.debug(f"📝 Created semantic memory: content_len={len(semantic_memory.content)}, "
                        f"importance={semantic_memory.importance:.2f}, "
                        f"metadata={semantic_memory.metadata}")

            # Step 4: Store semantic memory
            logger.info(f"🔄 Calling temporal_lobe_storage.region_store for memory {episodic_memory_id[:8]}...")
            try:
                semantic_memory_id = await temporal_lobe_storage.region_store(
                    memory=semantic_memory,
                    hrm_metadata={
                        'consolidation_step': temporal_lobe_storage.current_step,
                        'source_region': 'hippocampus'
                    }
                )

                if semantic_memory_id:
                    logger.info(f"✅ temporal_lobe_storage.region_store returned ID: {semantic_memory_id[:16]}")
                else:
                    logger.error(f"❌ temporal_lobe_storage.region_store returned None!")
                    return self._create_failure_result(
                        episodic_memory_id,
                        'episodic_to_semantic',
                        'region_store returned None'
                    )
            except Exception as store_error:
                logger.error(f"❌ temporal_lobe_storage.region_store raised exception: {store_error}")
                logger.error(f"   Exception type: {type(store_error).__name__}")
                import traceback
                logger.error(f"   Traceback: {traceback.format_exc()}")
                raise

            # Step 5: Update statistics
            self.stats['total_consolidations'] += 1
            self.stats['episodic_to_semantic'] += 1

            # Calculate consolidation time
            consolidation_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_avg_time(consolidation_time)

            logger.info(
                f"✅ Episodic→Semantic consolidation complete: "
                f"{episodic_memory_id} → {semantic_memory_id}"
            )

            result = ConsolidationResult(
                success=True,
                source_memory_id=episodic_memory_id,
                target_memory_id=semantic_memory_id,
                consolidation_type='episodic_to_semantic',
                timestamp=datetime.now(),
                metadata={
                    'entities': semantic_content['entities'],
                    'concepts': semantic_content['concepts'],
                    'consolidation_time_ms': consolidation_time
                }
            )

            self.consolidation_history.append(result)

            return result

        except Exception as e:
            logger.error(f"Consolidation failed for {episodic_memory_id}: {e}")
            self.stats['failed_consolidations'] += 1
            return self._create_failure_result(
                episodic_memory_id,
                'episodic_to_semantic',
                str(e)
            )

    async def enhance_with_emotion(
        self,
        memory_id: str,
        amygdala_storage: AmygdalaStorage,
        target_storage: IBrainRegionStorage,
        emotion_tags: List[str],
        emotion_intensity: float
    ) -> ConsolidationResult:
        """
        Enhance Memory with Emotional Tags
        用情绪标签增强记忆

        Amygdala adds emotional significance to memories,
        enhancing their encoding and retrieval.

        Args:
            memory_id: Memory ID to enhance
            amygdala_storage: Amygdala storage adapter
            target_storage: Target memory storage (Hippocampus/Temporal Lobe)
            emotion_tags: Emotion tags to add
            emotion_intensity: Emotional intensity (0.0-1.0)

        Returns:
            ConsolidationResult
        """
        start_time = datetime.now()
        logger.info(f"Enhancing memory {memory_id} with emotions: {emotion_tags}")

        try:
            # Step 1: Retrieve original memory
            memories = await target_storage.region_retrieve(
                query=memory_id,
                filters={'id': memory_id},
                k=1
            )

            if not memories:
                return self._create_failure_result(
                    memory_id,
                    'emotional_enhancement',
                    'Memory not found'
                )

            memory = memories[0]

            # Step 2: Create emotional tag
            emotional_tag = MemoryItem(
                content=f"Emotional tag for: {memory.content[:100]}",
                memory_type='emotional',
                importance=memory.importance * (1 + emotion_intensity),
                emotion_tags=emotion_tags,
                emotion_intensity=emotion_intensity,
                metadata={
                    'reference_memory_id': memory_id,
                    'tagged_at': datetime.now().isoformat()
                }
            )

            # Step 3: Store emotional tag
            tag_id = await amygdala_storage.region_store(
                memory=emotional_tag,
                hrm_metadata={
                    'regulation': 'normal',
                    'source_region': target_storage.brain_region_name
                }
            )

            # Step 4: Update original memory with emotion tags (in-place, no duplication)
            if target_storage.memory_system:
                updated_tags = list(set(memory.emotion_tags + emotion_tags))  # Merge & deduplicate
                updated_intensity = max(memory.emotion_intensity, emotion_intensity)

                await target_storage.memory_system.update_memory(
                    memory_id=memory_id,
                    updates={
                        'emotion_tags': updated_tags,
                        'emotion_intensity': updated_intensity,
                        'metadata': {
                            **memory.metadata,
                            'emotion_enhanced': True,
                            'emotion_enhanced_at': datetime.now().isoformat()
                        }
                    }
                )
                # Update local object to reflect changes
                memory.emotion_tags = updated_tags
                memory.emotion_intensity = updated_intensity
            else:
                logger.warning("Memory system not available for emotion update")

            # Step 5: Update statistics
            self.stats['total_consolidations'] += 1
            self.stats['emotional_enhancements'] += 1

            consolidation_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_avg_time(consolidation_time)

            logger.info(
                f"✅ Emotional enhancement complete: "
                f"{memory_id} (intensity={emotion_intensity})"
            )

            result = ConsolidationResult(
                success=True,
                source_memory_id=memory_id,
                target_memory_id=tag_id,
                consolidation_type='emotional_enhancement',
                timestamp=datetime.now(),
                metadata={
                    'emotion_tags': emotion_tags,
                    'emotion_intensity': emotion_intensity,
                    'consolidation_time_ms': consolidation_time
                }
            )

            self.consolidation_history.append(result)

            return result

        except Exception as e:
            logger.error(f"Emotional enhancement failed for {memory_id}: {e}")
            self.stats['failed_consolidations'] += 1
            return self._create_failure_result(
                memory_id,
                'emotional_enhancement',
                str(e)
            )

    async def batch_consolidate(
        self,
        memory_ids: List[str],
        consolidation_type: str,
        source_storage: IBrainRegionStorage,
        target_storage: IBrainRegionStorage,
        **kwargs
    ) -> List[ConsolidationResult]:
        """
        Batch Consolidate Multiple Memories
        批量巩固多个记忆

        Args:
            memory_ids: List of memory IDs
            consolidation_type: Type of consolidation
            source_storage: Source storage adapter
            target_storage: Target storage adapter
            **kwargs: Additional arguments

        Returns:
            List of ConsolidationResults
        """
        logger.info(
            f"Batch consolidation: {len(memory_ids)} memories "
            f"({consolidation_type})"
        )

        results = []

        for memory_id in memory_ids:
            if consolidation_type == 'episodic_to_semantic':
                result = await self.consolidate_episodic_to_semantic(
                    episodic_memory_id=memory_id,
                    hippocampus_storage=source_storage,
                    temporal_lobe_storage=target_storage,
                    priority=kwargs.get('priority', 0.7)
                )
            elif consolidation_type == 'emotional_enhancement':
                result = await self.enhance_with_emotion(
                    memory_id=memory_id,
                    amygdala_storage=kwargs.get('amygdala_storage'),
                    target_storage=target_storage,
                    emotion_tags=kwargs.get('emotion_tags', []),
                    emotion_intensity=kwargs.get('emotion_intensity', 0.5)
                )
            else:
                logger.warning(f"Unknown consolidation type: {consolidation_type}")
                result = self._create_failure_result(
                    memory_id,
                    consolidation_type,
                    'Unknown consolidation type'
                )

            results.append(result)

        successful = sum(1 for r in results if r.success)
        logger.info(
            f"Batch consolidation complete: {successful}/{len(memory_ids)} successful"
        )

        return results

    def _extract_semantic_knowledge(
        self,
        episodic_memory: MemoryItem
    ) -> Dict[str, Any]:
        """
        Extract Semantic Knowledge from Episodic Memory
        从情节记忆中提取语义知识

        Args:
            episodic_memory: Episodic memory item

        Returns:
            Dictionary with extracted knowledge
        """
        # Extract entities (people, places, concepts)
        entities = episodic_memory.context_tags or []

        # Extract relations (simple co-occurrence for now)
        relations = []
        if len(entities) >= 2:
            relations.append((entities[0], 'related_to', entities[1]))

        # Extract concepts (generalize from content)
        concepts = self._generalize_concepts(episodic_memory.content)

        # Create semantic content
        semantic_content = self._create_semantic_summary(episodic_memory, concepts)

        return {
            'content': semantic_content,
            'entities': entities,
            'relations': relations,
            'concepts': concepts
        }

    def _generalize_concepts(self, content: str) -> List[str]:
        """
        Generalize Concepts from Content
        从内容中泛化概念

        Args:
            content: Memory content

        Returns:
            List of concepts
        """
        # Simple keyword extraction for concepts
        concepts = []

        concept_keywords = [
            'learn', 'understand', 'knowledge', 'concept',
            'theory', 'principle', 'method', 'technique'
        ]

        content_lower = content.lower()

        for keyword in concept_keywords:
            if keyword in content_lower:
                concepts.append(keyword)

        return concepts or ['general_knowledge']

    def _create_semantic_summary(
        self,
        episodic_memory: MemoryItem,
        concepts: List[str]
    ) -> str:
        """
        Create Semantic Summary
        创建语义摘要

        Args:
            episodic_memory: Episodic memory
            concepts: Extracted concepts

        Returns:
            Semantic summary string
        """
        # For now, use original content as base
        # In production, use LLM to create abstracted summary
        summary = f"[Semantic] {episodic_memory.content[:200]}"

        if concepts:
            summary += f" | Concepts: {', '.join(concepts)}"

        return summary

    def _create_failure_result(
        self,
        memory_id: str,
        consolidation_type: str,
        error_message: str
    ) -> ConsolidationResult:
        """Create failure result"""
        return ConsolidationResult(
            success=False,
            source_memory_id=memory_id,
            target_memory_id=None,
            consolidation_type=consolidation_type,
            timestamp=datetime.now(),
            metadata={'error': error_message}
        )

    def _update_avg_time(self, consolidation_time: float) -> None:
        """Update average consolidation time"""
        current_avg = self.stats['avg_consolidation_time_ms']
        total = self.stats['total_consolidations']

        if total > 1:
            new_avg = ((current_avg * (total - 1)) + consolidation_time) / total
            self.stats['avg_consolidation_time_ms'] = new_avg
        else:
            self.stats['avg_consolidation_time_ms'] = consolidation_time

    def get_consolidation_stats(self) -> Dict[str, Any]:
        """
        Get Consolidation Statistics
        获取巩固统计信息

        Returns:
            Statistics dictionary
        """
        return {
            'total_consolidations': self.stats['total_consolidations'],
            'by_type': {
                'episodic_to_semantic': self.stats['episodic_to_semantic'],
                'emotional_enhancements': self.stats['emotional_enhancements']
            },
            'failed_consolidations': self.stats['failed_consolidations'],
            'success_rate': (
                (self.stats['total_consolidations'] - self.stats['failed_consolidations']) /
                max(1, self.stats['total_consolidations'])
            ),
            'avg_consolidation_time_ms': self.stats['avg_consolidation_time_ms'],
            'history_size': len(self.consolidation_history)
        }
