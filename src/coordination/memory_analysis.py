"""
Memory Analysis Handler
Handles analysis methods: KG coverage, multi-hop detection, cross-region retrieval,
result fusion, calibration, StoryArc queries
"""

import asyncio
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..utils.config import get_logger
from ..core.config import get_config

# Task 3.3: Adaptive semantic/episodic weights for fusion
try:
    from src.coordination.adaptive_config import (
        get_adaptive_config_manager,
    )
    _ADAPTIVE_CONFIG_AVAILABLE = True
except ImportError:
    _ADAPTIVE_CONFIG_AVAILABLE = False

logger = get_logger(__name__)


class MemoryAnalysisHandler:
    """Handles all analysis-related operations for MemoryCoordinator"""

    def __init__(self, coordinator: 'MemoryCoordinator'):
        self._coordinator = coordinator

    def _calculate_kg_coverage(
        self, memories: List[Dict], query: str
    ) -> float:
        """
        Calculate KG coverage rate using real KG statistics

        KG coverage measures how well the Knowledge Graph covers the query domain.
        Uses actual KG node/relation counts instead of string matching.

        Coverage formula:
        - Entity coverage: (found query entities in KG) / (total query entities)
        - KG richness: (query-related triples) / (expected triples)
        - Final coverage: (Entity coverage * 0.6) + (KG richness * 0.4)

        Args:
            memories: Retrieved memory list (unused, kept for compatibility)
            query: Original query string

        Returns:
            Coverage ratio (0.0-1.0)
        """
        coord = self._coordinator

        query_tokens = set(re.findall(r'\b\w+\b', query.lower()))
        stop_words = {
            'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or',
            'but', 'in', 'with', 'to', 'for', 'of', 'as', 'by', 'what',
            'how', 'why', 'when', 'where', 'who'
        }
        query_entities = query_tokens - stop_words

        if not query_entities:
            return 1.0

        if not (coord.temporal_lobe and hasattr(coord.temporal_lobe, 'kg')):
            logger.warning(
                "   KG not available, coverage set to 0.5 (unknown)"
            )
            return 0.5

        kg = coord.temporal_lobe.kg

        try:
            kg_stats = kg.get_statistics()
            total_kg_entities = kg_stats.get('total_entities', 0)
            total_kg_triples = kg_stats.get('total_triples', 0)

            if total_kg_entities == 0 or total_kg_triples == 0:
                logger.debug("   KG Coverage: 0.00% (KG is empty)")
                return 0.0

            covered_entities = set()
            query_related_triples = 0

            for entity in query_entities:
                relations = kg.query_relations(entity)
                if relations:
                    covered_entities.add(entity)
                    query_related_triples += len(relations)
                    continue

                if (hasattr(kg, 'reverse_index')
                        and entity in kg.reverse_index):
                    covered_entities.add(entity)
                    query_related_triples += len(kg.reverse_index[entity])

            entity_coverage = len(covered_entities) / len(query_entities)

            avg_relations_per_entity = (
                total_kg_triples / total_kg_entities
                if total_kg_entities > 0 else 1
            )
            expected_triples = (
                len(query_entities) * avg_relations_per_entity
            )
            kg_richness = (
                min(1.0, query_related_triples / expected_triples)
                if expected_triples > 0 else 0.0
            )

            coverage = (entity_coverage * 0.6) + (kg_richness * 0.4)

            logger.debug(
                f"   KG Coverage: {coverage:.2%} "
                f"(entities: {len(covered_entities)}/{len(query_entities)}, "
                f"triples: {query_related_triples}, "
                f"KG: {total_kg_entities} entities, "
                f"{total_kg_triples} triples)"
            )

            return coverage

        except Exception as e:
            logger.warning(
                f"   KG coverage calculation failed: {e}, "
                f"assuming low coverage"
            )
            return get_config().retrieval.quality_threshold

    def _is_multi_hop_query(self, query: str) -> bool:
        """
        Detect multi-hop reasoning queries

        Multi-hop patterns:
        - Temporal/causal (after, before, because)
        - Counting (how many times)
        - Comparison (compare, difference)
        - Relation chains (X's Y's Z)

        Returns:
            True if multi-hop query
        """
        multi_hop_patterns = [
            r'\b(after|before|since|until|following|prior to)\s+\w+',
            r'\b(because|due to|as a result|caused by|led to)\b',
            r'\bhow many (times|people|things|events)\b',
            r'\bwhat.*and.*what\b',
            r'\brelat(ed|ion|ionship|ive)\b',
            r'\bcompare|difference|similar|both\b',
            r"'s\s+\w+'s\b",
            r'\ball\s+(the|of)\b',
        ]
        query_lower = query.lower()
        return any(re.search(p, query_lower) for p in multi_hop_patterns)

    async def cross_region_retrieval(
        self,
        query: str,
        top_k: int = 20,
        activation_plan: Optional[Dict[str, bool]] = None
    ) -> List[Dict]:
        """
        Cross-region parallel retrieval with result fusion

        Retrieves memories from multiple brain regions in parallel,
        then fuses results with resonance scoring.

        Args:
            query: Search query
            top_k: Number of results to return
            activation_plan: Optional dict specifying which regions to activate

        Returns:
            List of fused memories with resonance scores
        """
        coord = self._coordinator

        is_multi_hop = self._is_multi_hop_query(query)
        if is_multi_hop:
            effective_top_k = max(top_k, 30)
            logger.info(
                f"Phase 3: Multi-hop query detected, "
                f"using top_k={effective_top_k}"
            )
        else:
            effective_top_k = top_k

        logger.info(
            f"Phase 3: Cross-region retrieval for query: '{query[:50]}...'"
        )

        if activation_plan is None:
            activation_plan = {
                'hippocampus': True,
                'temporal_lobe': True,
                'prefrontal': False,
                'amygdala': False,
                'basal_ganglia': False
            }

        # Phase 1: Build parallel retrieval tasks
        retrieval_tasks = {}

        # Hippocampus: Episodic memories
        if activation_plan.get('hippocampus') and coord.hippocampus:
            async def retrieve_hippocampus():
                try:
                    result = await coord.hippocampus.search_memories(
                        query, k=effective_top_k * 2
                    )
                    return result.get('memories', [])
                except Exception as e:
                    logger.warning(f"Hippocampus retrieval failed: {e}")
                    return []
            retrieval_tasks['hippocampus'] = retrieve_hippocampus()

        # Temporal Lobe: Semantic knowledge + KG joint retrieval
        if activation_plan.get('temporal_lobe') and coord.temporal_lobe:
            async def retrieve_temporal():
                try:
                    if hasattr(coord.temporal_lobe, 'search_kg_memory_joint'):
                        result = (
                            await coord.temporal_lobe.search_kg_memory_joint(
                                query=query,
                                k=top_k * 2,
                                kg_depth=1,
                                beta=0.6
                            )
                        )
                        memories = result.get('memories', [])
                        for mem in memories:
                            mem['kg_enhanced'] = True
                        if memories:
                            logger.debug(
                                f"Temporal Lobe KG-joint retrieval: "
                                f"{len(memories)} memories"
                            )
                            return memories

                    result = await coord.temporal_lobe.search_memories(
                        query, k=top_k * 2
                    )
                    return result.get('memories', [])
                except Exception as e:
                    logger.warning(f"Temporal Lobe retrieval failed: {e}")
                    return []
            retrieval_tasks['temporal_lobe'] = retrieve_temporal()

        # Prefrontal: Reasoning traces
        if activation_plan.get('prefrontal') and coord.prefrontal_storage:
            async def retrieve_prefrontal():
                try:
                    result = coord.prefrontal_storage.retrieve_items(k=top_k)
                    items = []
                    for item in result.get('items', []):
                        if hasattr(item, '__dict__'):
                            items.append(vars(item))
                        else:
                            items.append(item)
                    return items
                except Exception as e:
                    logger.warning(f"Prefrontal retrieval failed: {e}")
                    return []
            retrieval_tasks['prefrontal'] = retrieve_prefrontal()

        # Amygdala: Emotional memories
        if activation_plan.get('amygdala') and coord.amygdala:
            async def retrieve_amygdala():
                try:
                    result = coord.amygdala.search_by_emotion(
                        emotion_tags=None,
                        min_intensity=0.0,
                        k=top_k
                    )
                    memories = []
                    for mem in result.get('memories', []):
                        if hasattr(mem, '__dict__'):
                            mem_dict = vars(mem).copy()
                            if ('timestamp' in mem_dict
                                    and hasattr(
                                        mem_dict['timestamp'], 'isoformat'
                                    )):
                                mem_dict['timestamp'] = (
                                    mem_dict['timestamp'].isoformat()
                                )
                            if ('last_practiced' in mem_dict
                                    and mem_dict['last_practiced']
                                    and hasattr(
                                        mem_dict['last_practiced'], 'isoformat'
                                    )):
                                mem_dict['last_practiced'] = (
                                    mem_dict['last_practiced'].isoformat()
                                )
                            memories.append(mem_dict)
                        else:
                            memories.append(mem)
                    return memories
                except Exception as e:
                    logger.warning(f"Amygdala retrieval failed: {e}")
                    return []
            retrieval_tasks['amygdala'] = retrieve_amygdala()

        # Basal Ganglia: Procedural patterns
        if activation_plan.get('basal_ganglia') and coord.basal_ganglia:
            async def retrieve_basal():
                try:
                    result = coord.basal_ganglia.search_skills(
                        query, k=top_k
                    )
                    patterns = []
                    for skill in result.get('skills', []):
                        if hasattr(skill, '__dict__'):
                            skill_dict = vars(skill).copy()
                            if ('timestamp' in skill_dict
                                    and hasattr(
                                        skill_dict['timestamp'], 'isoformat'
                                    )):
                                skill_dict['timestamp'] = (
                                    skill_dict['timestamp'].isoformat()
                                )
                            if ('last_practiced' in skill_dict
                                    and skill_dict['last_practiced']
                                    and hasattr(
                                        skill_dict['last_practiced'],
                                        'isoformat'
                                    )):
                                skill_dict['last_practiced'] = (
                                    skill_dict['last_practiced'].isoformat()
                                )
                            patterns.append(skill_dict)
                        else:
                            patterns.append(skill)
                    return patterns
                except Exception as e:
                    logger.warning(f"Basal Ganglia retrieval failed: {e}")
                    return []
            retrieval_tasks['basal_ganglia'] = retrieve_basal()

        # Execute all retrieval tasks in parallel
        logger.info(
            f"   Querying {len(retrieval_tasks)} brain regions in parallel"
        )
        results = await asyncio.gather(
            *retrieval_tasks.values(), return_exceptions=True
        )

        region_memories = {}
        for region_name, result in zip(retrieval_tasks.keys(), results):
            if isinstance(result, Exception):
                logger.warning(
                    f"   {region_name}: retrieval exception {result}"
                )
                region_memories[region_name] = []
            else:
                logger.info(
                    f"   {region_name}: retrieved {len(result)} memories"
                )
                region_memories[region_name] = result

        # Phase 2: Fuse results with resonance scoring
        fused_memories = await self._fuse_cross_region_results(
            region_memories, query
        )

        logger.info(
            f"   Final: {len(fused_memories)} fused memories (top {top_k})"
        )
        return fused_memories[:top_k]

    async def _fuse_cross_region_results(
        self,
        region_memories: Dict[str, List],
        query: str
    ) -> List[Dict]:
        """
        Fuse multi-region results with resonance scoring

        Resonance scoring:
        - Base score: Calibrated relevance score
        - Resonance bonus: +0.15 for each additional region
        - Emotional boost: +0.2 * intensity if from Amygdala
        - Task 3.3: Adaptive weight per brain region

        Args:
            region_memories: Dict mapping region names to memory
                lists
            query: Original query

        Returns:
            Sorted list of memories with resonance metadata
        """
        coord = self._coordinator

        logger.debug("   Fusing cross-region results...")

        calibrated_region_memories = (
            coord.confidence_calibrator.calibrate_scores(
                region_memories, query
            )
        )

        region_scales = self._calibrate_region_confidence(
            region_memories
        )

        # Task 3.3: Get adaptive weights for semantic/episodic
        _adaptive_region_weights = {}
        if _ADAPTIVE_CONFIG_AVAILABLE:
            try:
                _acm = get_adaptive_config_manager()
                _aw = _acm.get_adaptive_weights(query)
                _adaptive_region_weights = {
                    'hippocampus': _aw.episodic_weight,
                    'temporal_lobe': _aw.semantic_weight,
                }
                logger.debug(
                    "Task 3.3 fusion weights: "
                    f"hippo={_aw.episodic_weight:.2f}, "
                    f"temp={_aw.semantic_weight:.2f}"
                )
            except Exception as e:
                logger.debug(
                    "Task 3.3 adaptive weights "
                    f"fallback: {e}"
                )

        memory_resonance = {}

        for region_name, memories in (
            calibrated_region_memories.items()
        ):
            if not memories:
                continue

            # Task 3.3: adaptive weight for this region
            adap_w = _adaptive_region_weights.get(
                region_name, 1.0
            )

            for mem in memories:
                mem_id = self._get_memory_id(mem)

                if mem_id not in memory_resonance:
                    if 'calibrated_score' in mem:
                        base_score = mem['calibrated_score']
                    else:
                        base_score_raw = (
                            self._get_memory_score(mem)
                        )
                        base_score = (
                            base_score_raw
                            * region_scales.get(
                                region_name, 1.0
                            )
                        )

                    # Task 3.3: scale by adaptive weight
                    base_score *= adap_w

                    memory_resonance[mem_id] = {
                        'memory': mem,
                        'regions': set(),
                        'base_score': base_score,
                        'emotional_boost': 0.0,
                        'resonance_score': 0.0,
                        'calibration_info': mem.get(
                            '_calibration', {}
                        ),
                    }

                memory_resonance[mem_id]['regions'].add(
                    region_name
                )

                if region_name == 'amygdala':
                    intensity = mem.get(
                        'intensity',
                        mem.get('emotion_intensity', 0.5),
                    )
                    memory_resonance[mem_id][
                        'emotional_boost'
                    ] = (float(intensity) * 0.2)

        for mem_id, data in memory_resonance.items():
            region_count = len(data['regions'])
            resonance_bonus = (region_count - 1) * 0.15
            data['resonance_score'] = (
                data['base_score']
                + resonance_bonus
                + data['emotional_boost']
            )

            logger.debug(
                f"      Memory {mem_id[:8]}: "
                f"regions={region_count}, "
                f"base={data['base_score']:.2f}, "
                f"resonance={data['resonance_score']:.2f}"
            )

        sorted_memories = sorted(
            memory_resonance.values(),
            key=lambda x: x['resonance_score'],
            reverse=True
        )

        result_memories = []
        for mem_data in sorted_memories:
            memory = (
                mem_data['memory'].copy()
                if isinstance(mem_data['memory'], dict)
                else mem_data['memory']
            )

            if isinstance(memory, dict):
                memory['_meta'] = {
                    'regions': list(mem_data['regions']),
                    'resonance_score': mem_data['resonance_score'],
                    'region_count': len(mem_data['regions']),
                    'emotional_boost': mem_data['emotional_boost'],
                    'calibration': mem_data.get('calibration_info', {})
                }

            result_memories.append(memory)

        return result_memories

    def record_retrieval_outcome(
        self,
        region_name: str,
        query: str,
        memories_used: List[Dict],
        success: bool,
        feedback_score: Optional[float] = None
    ) -> None:
        """
        Record retrieval outcome for calibration learning

        Args:
            region_name: Brain region name
            query: Query
            memories_used: Memories used
            success: Whether successful
            feedback_score: Feedback score
        """
        self._coordinator.confidence_calibrator.record_outcome(
            region_name=region_name,
            query=query,
            memories_used=memories_used,
            success=success,
            feedback_score=feedback_score
        )

    def get_calibration_stats(self) -> Dict[str, Any]:
        """Get calibration statistics"""
        return self._coordinator.confidence_calibrator.get_calibration_stats()

    def save_calibration(self) -> bool:
        """Save calibration state"""
        return self._coordinator.confidence_calibrator.save_calibration()

    def _calibrate_region_confidence(
        self, region_memories: Dict[str, List]
    ) -> Dict[str, float]:
        """
        Calibrate region confidence based on average scores
        (kept as backup method)
        """
        averages = {}
        for region, memories in region_memories.items():
            if not memories:
                continue
            scores = [self._get_memory_score(m) for m in memories]
            if scores:
                averages[region] = sum(scores) / len(scores)

        if not averages:
            return {}

        max_avg = max(averages.values()) or 1.0
        return {
            region: (avg / max_avg) for region, avg in averages.items()
        }

    def _get_memory_id(self, memory: Any) -> str:
        """Extract memory ID from various memory formats"""
        if isinstance(memory, dict):
            return memory.get(
                'id',
                memory.get(
                    'memory_id',
                    memory.get('reference_id', str(id(memory)))
                )
            )
        elif hasattr(memory, 'id'):
            return memory.id
        elif hasattr(memory, 'memory_id'):
            return memory.memory_id
        else:
            return str(id(memory))

    def _get_memory_score(self, memory: Any) -> float:
        """Extract relevance score from various memory formats"""
        if isinstance(memory, dict):
            return memory.get(
                'score',
                memory.get('relevance', memory.get('importance', 0.5))
            )
        elif hasattr(memory, 'score'):
            return memory.score
        elif hasattr(memory, 'importance'):
            return memory.importance
        else:
            return 0.5

    # ===================================================================
    # StoryArc Timeline Query Interface
    # ===================================================================

    async def query_event_time(
        self,
        entity: str,
        event_keywords: List[str],
        time_hint: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Query entity event time via StoryArc timeline index

        Args:
            entity: Entity name (e.g., 'Caroline')
            event_keywords: Event keywords (e.g., ['museum', 'visit'])
            time_hint: Time hint (e.g., 'July 2023', 'summer')

        Returns:
            {
                'event_date': date,
                'formatted_date': str,
                'confidence': float,
                'event': TimelineEvent
            }
        """
        return await self._coordinator.story_arc.query_event_time(
            entity, event_keywords, time_hint
        )

    async def calculate_duration(
        self,
        entity: str,
        reference: str,
        reference_date: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate time duration via StoryArc

        Args:
            entity: Entity name
            reference: Reference content (e.g., 'friends', 'living in city')
            reference_date: Reference date

        Returns:
            {'duration': str, 'start_date': date, 'confidence': float}
        """
        from datetime import date as date_type
        ref_date = (
            reference_date.date() if reference_date else date_type.today()
        )
        return await self._coordinator.story_arc.calculate_duration(
            entity, reference, ref_date
        )

    def get_story_arc_statistics(self) -> Dict[str, Any]:
        """Get StoryArc statistics"""
        return self._coordinator.story_arc.get_statistics()

    def clear_story_arc(self):
        """Clear StoryArc timeline (for test reset)"""
        self._coordinator.story_arc.clear()
        logger.info("StoryArc timeline cleared")
