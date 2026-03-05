"""
Memory Retrieval Handler
Handles retrieval methods: smart_retrieve, brain region retrieval, enhancement
"""

import asyncio
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..utils.config import get_logger
from ..monitoring.memory_metrics import get_metrics_collector
from ..config.ablation_config import is_component_enabled

logger = get_logger(__name__)


class MemoryRetrievalHandler:
    """Handles all retrieval-related operations for MemoryCoordinator"""

    def __init__(self, coordinator: 'MemoryCoordinator'):
        self._coordinator = coordinator

    async def smart_retrieve(
        self,
        query: str,
        k: int = 10,
        strategy: str = 'auto',
        context: Dict[str, Any] = None,
        activation_plan: Optional[Dict[str, bool]] = None
    ) -> List[Dict[str, Any]]:
        """
        Smart memory retrieval with automatic strategy selection + cache optimization

        Args:
            query: Query text
            k: Number of results
            strategy: Retrieval strategy ('auto', 'episodic', 'semantic', 'hybrid')
            context: Optional context dict
            activation_plan: Optional region activation plan from Thalamus

        Returns:
            List of retrieved memories
        """
        coord = self._coordinator

        if context is None:
            context = {}

        # Try retrieval cache
        from ..utils.semantic_cache import get_retrieval_cache
        retrieval_cache = get_retrieval_cache()

        active_regions = None
        if activation_plan:
            active_regions = [
                region for region, active in activation_plan.items() if active
            ]

        cached_results = retrieval_cache.get(
            query=query,
            k=k,
            strategy=strategy,
            regions=active_regions
        )
        if cached_results:
            logger.debug(
                f"Retrieval cache HIT: query='{query[:50]}...', k={k}"
            )
            return cached_results

        try:
            if strategy == 'auto':
                strategy = 'hybrid'

            if strategy == 'episodic':
                result = await coord.hippocampus.search_memories(query, k=k)
                memories = (
                    result.get('memories', [])
                    if isinstance(result, dict) else result
                )
                for mem in memories:
                    mem['source'] = 'hippocampus'
            elif strategy == 'semantic':
                result = await coord.temporal_lobe.search_memories(query, k=k)
                memories = (
                    result.get('memories', [])
                    if isinstance(result, dict) else result
                )
                for mem in memories:
                    mem['source'] = 'temporal_lobe'
            elif strategy == 'hybrid':
                # Use BrainInspiredRetrieval (integrates all brain-like features)
                brain_result = await coord.brain_retrieval.retrieve(
                    query=query,
                    k=k,
                    context=context,
                    activation_plan=activation_plan
                )

                memories = brain_result.memories

                logger.info(
                    f"BrainRetrieval: path={brain_result.path_type}, "
                    f"iterations={brain_result.iterations}, "
                    f"confidence={brain_result.confidence:.2f}, "
                    f"time={brain_result.retrieval_time_ms:.1f}ms"
                )

                if brain_result.debug_info.get('gap_types_detected'):
                    logger.info(
                        f"   Gap types: "
                        f"{brain_result.debug_info['gap_types_detected']}"
                    )

                # KG coverage degradation strategy
                kg_coverage = coord._analysis._calculate_kg_coverage(
                    memories, query
                )

                if kg_coverage < 0.95 and brain_result.confidence < 0.6:
                    logger.warning(
                        f"Low KG coverage ({kg_coverage:.2%}) + "
                        f"low confidence ({brain_result.confidence:.2f}), "
                        f"triggering additional fallback"
                    )

                    adaptive_k = int(k * 1.5)
                    fallback_memories = await self._pure_semantic_fallback(
                        query=query,
                        k=adaptive_k,
                        activation_plan=activation_plan
                    )

                    all_memories = memories + fallback_memories

                    seen_ids = set()
                    unique_memories = []
                    for mem in all_memories:
                        mem_id = mem.get('id', id(mem))
                        if mem_id not in seen_ids:
                            unique_memories.append(mem)
                            seen_ids.add(mem_id)

                    unique_memories.sort(
                        key=lambda x: x.get(
                            'relevance',
                            x.get('score', x.get('resonance_score', 0))
                        ),
                        reverse=True
                    )

                    memories = unique_memories[:adaptive_k]
                    logger.info(
                        f"   Additional fallback: {len(memories)} memories"
                    )
            else:
                result = await coord.hippocampus.search_memories(query, k=k)
                memories = (
                    result.get('memories', [])
                    if isinstance(result, dict) else result
                )
                for mem in memories:
                    mem['source'] = 'hippocampus'

            # Chunk-aware retrieval: expand chunks to include neighbors
            try:
                chunk_groups = {}

                for mem in memories:
                    content = mem.get('content', '')
                    match = re.search(
                        r'\[Chunk (\d+)/(\d+) \| Group: (chunk_group_\w+)\]',
                        content
                    )
                    if match:
                        chunk_num = int(match.group(1))
                        total_chunks = int(match.group(2))
                        group_id = match.group(3)

                        if group_id not in chunk_groups:
                            chunk_groups[group_id] = {
                                'total': total_chunks,
                                'found_chunks': set(),
                                'source': mem.get('source', 'hippocampus')
                            }
                        chunk_groups[group_id]['found_chunks'].add(chunk_num)

                if chunk_groups:
                    logger.info(
                        f"   Detected {len(chunk_groups)} chunk groups, "
                        f"expanding neighbors..."
                    )

                    expanded_memories = []
                    memory_ids_seen = set()

                    for mem in memories:
                        mem_id = mem.get('id', id(mem))
                        if mem_id not in memory_ids_seen:
                            expanded_memories.append(mem)
                            memory_ids_seen.add(mem_id)

                    for group_id, group_info in chunk_groups.items():
                        found_chunks = group_info['found_chunks']
                        total_chunks = group_info['total']
                        source = group_info['source']

                        neighbors_to_fetch = set()
                        for chunk_num in found_chunks:
                            if chunk_num > 1:
                                neighbors_to_fetch.add(chunk_num - 1)
                            if chunk_num < total_chunks:
                                neighbors_to_fetch.add(chunk_num + 1)

                        neighbors_to_fetch -= found_chunks

                        if neighbors_to_fetch:
                            for neighbor_num in neighbors_to_fetch:
                                neighbor_pattern = (
                                    f"[Chunk {neighbor_num}/{total_chunks}"
                                    f" | Group: {group_id}]"
                                )

                                if source == 'hippocampus':
                                    neighbor_result = (
                                        await coord.hippocampus.search_memories(
                                            query=neighbor_pattern,
                                            k=1
                                        )
                                    )
                                    neighbor_mems = (
                                        neighbor_result.get('memories', [])
                                        if isinstance(neighbor_result, dict)
                                        else neighbor_result
                                    )
                                elif source == 'temporal_lobe':
                                    neighbor_result = (
                                        await coord.temporal_lobe.search_memories(
                                            query=neighbor_pattern,
                                            k=1
                                        )
                                    )
                                    neighbor_mems = (
                                        neighbor_result.get('memories', [])
                                        if isinstance(neighbor_result, dict)
                                        else neighbor_result
                                    )
                                else:
                                    neighbor_mems = []

                                for neighbor_mem in neighbor_mems:
                                    neighbor_id = neighbor_mem.get(
                                        'id', id(neighbor_mem)
                                    )
                                    if neighbor_id not in memory_ids_seen:
                                        neighbor_mem['source'] = source
                                        neighbor_mem['_is_neighbor_chunk'] = True
                                        expanded_memories.append(neighbor_mem)
                                        memory_ids_seen.add(neighbor_id)

                    if len(expanded_memories) > len(memories):
                        logger.info(
                            f"      Expanded from {len(memories)} to "
                            f"{len(expanded_memories)} memories "
                            f"(added {len(expanded_memories) - len(memories)} "
                            f"neighbor chunks)"
                        )
                        memories = expanded_memories

                        memories.sort(
                            key=lambda x: (
                                0 if not x.get(
                                    '_is_neighbor_chunk', False
                                ) else 1,
                                -x.get(
                                    'relevance', x.get('score', 0)
                                )
                            )
                        )

                        memories = memories[:k * 2]

            except Exception as e:
                logger.warning(f"Chunk-aware retrieval failed: {e}")

            # Record retrieval metrics
            try:
                metrics = get_metrics_collector()

                source_counts = {}
                for mem in memories:
                    source = mem.get('source', 'unknown')
                    source_counts[source] = source_counts.get(source, 0) + 1

                metrics.record_retrieval_event(
                    query=query,
                    sources=source_counts,
                    total_retrieved=len(memories),
                    strategy=strategy,
                    metadata={'k': k}
                )

                for source in source_counts:
                    if source == 'hippocampus':
                        metrics.record_brain_region_activation(
                            'hippocampus', 'queried'
                        )
                    elif source == 'temporal_lobe':
                        metrics.record_brain_region_activation(
                            'temporal_lobe', 'queried'
                        )
                    elif source == 'memory_system':
                        metrics.record_brain_region_activation(
                            'memory_system', 'queried'
                        )
            except Exception as e:
                logger.warning(f"Failed to record retrieval metrics: {e}")

            # Brain-like retrieval enhancement: silent engram reactivation
            if len(memories) < k // 2 and coord.hippocampus:
                logger.info(
                    f"   Low retrieval results ({len(memories)}/{k}), "
                    f"attempting silent engram reactivation..."
                )
                try:
                    query_entities = [
                        word for word in query.split()
                        if word[0].isupper() and len(word) > 1
                    ]

                    if (hasattr(coord.hippocampus, 'forgetting_manager')
                            and coord.hippocampus.forgetting_manager):
                        reactivated = (
                            await coord.hippocampus.forgetting_manager
                            .try_reactivate_silent_memories(
                                query_entities=(
                                    query_entities if query_entities else None
                                ),
                                max_reactivations=3,
                                boost_factor=1.2
                            )
                        )

                        if reactivated:
                            logger.info(
                                f"   Reactivated {len(reactivated)} "
                                f"silent engrams"
                            )
                            for engram_info in reactivated:
                                reactivated_mem = {
                                    'id': engram_info.get('memory_id'),
                                    'content': (
                                        f"[Reactivated] Entities: "
                                        f"{engram_info.get('entities', [])}, "
                                        f"Time: "
                                        f"{engram_info.get('timestamp', 'unknown')}"
                                    ),
                                    'source': 'silent_engram',
                                    'relevance': engram_info.get(
                                        'activation_score', 0.5
                                    ),
                                    'needs_full_restoration': True
                                }
                                memories.append(reactivated_mem)
                except Exception as e:
                    logger.warning(
                        f"Silent engram reactivation failed: {e}"
                    )

            # StoryArc + ToM retrieval augmentation
            try:
                augmented = False

                # 1. StoryArc entity context augmentation
                if coord.story_arc and is_component_enabled('story_arc'):
                    query_words = query.split()
                    query_entities = [
                        w for w in query_words
                        if len(w) > 1 and w[0].isupper()
                    ]

                    for entity in query_entities[:3]:
                        entity_context = coord.story_arc.get_entity_context(
                            entity, limit=5
                        )
                        if entity_context:
                            for event in entity_context:
                                event_content = event.get('content', '')
                                if not any(
                                    event_content in m.get('content', '')
                                    for m in memories
                                ):
                                    memories.append({
                                        'content': event_content,
                                        'source': 'story_arc',
                                        'event_type': event.get('event_type'),
                                        'event_date': event.get('event_date'),
                                        'relevance': 0.75,
                                        'memory_id': event.get('memory_id')
                                    })
                                    augmented = True

                    if augmented:
                        logger.info(
                            f"   StoryArc augmented: +"
                            f"{len([m for m in memories if m.get('source') == 'story_arc'])}"
                            f" events"
                        )

                # 2. ToM mental model augmentation
                try:
                    from ..agents.brain_regions.theory_of_mind_agent import (
                        get_theory_of_mind_agent
                    )
                    tom = get_theory_of_mind_agent()

                    preference_keywords = [
                        'prefer', 'like', 'want', 'favorite',
                        'choice', 'opinion', 'think', 'feel'
                    ]
                    is_preference_query = any(
                        kw in query.lower() for kw in preference_keywords
                    )

                    if is_preference_query and query_entities:
                        for entity in query_entities[:2]:
                            mental_model = tom.get_mental_model(entity)
                            if mental_model:
                                for entry in mental_model[:3]:
                                    model_content = (
                                        f"[Mental Model] {entity}: "
                                        f"{entry.entry_type} - {entry.content}"
                                    )
                                    if not any(
                                        model_content in m.get('content', '')
                                        for m in memories
                                    ):
                                        memories.append({
                                            'content': model_content,
                                            'source': 'theory_of_mind',
                                            'relevance': 0.8,
                                            'entity': entity,
                                            'entry_type': entry.entry_type
                                        })
                                logger.info(
                                    f"   ToM mental model: "
                                    f"+{len(mental_model[:3])} entries "
                                    f"for {entity}"
                                )
                except Exception as e:
                    logger.debug(f"ToM augmentation skipped: {e}")

                # Re-sort if augmented
                if augmented:
                    memories.sort(
                        key=lambda x: (
                            0 if x.get('source') not in (
                                'story_arc', 'theory_of_mind'
                            ) else 1,
                            -x.get('relevance', x.get('score', 0))
                        )
                    )
                    memories = memories[:k * 2]

            except Exception as e:
                logger.warning(
                    f"StoryArc/ToM augmentation failed: {e}"
                )

            # Store in retrieval cache
            retrieval_cache.put(
                query=query,
                results=memories,
                k=k,
                strategy=strategy,
                regions=active_regions
            )

            return memories

        except Exception as e:
            logger.error(f"Smart retrieve failed: {e}")
            return []

    async def _pure_semantic_fallback(
        self,
        query: str,
        k: int,
        activation_plan: Optional[Dict[str, bool]] = None
    ) -> List[Dict[str, Any]]:
        """
        Pure semantic retrieval fallback (bypass KG, use only embeddings)

        When KG coverage is low, fall back to pure vector similarity search.

        Args:
            query: Search query
            k: Number of results
            activation_plan: Optional region activation plan

        Returns:
            List of memories retrieved via pure semantic search
        """
        coord = self._coordinator

        logger.info(
            f"   Pure semantic fallback: retrieving {k} memories "
            f"via embeddings only"
        )

        fallback_memories = []

        if activation_plan is None:
            activation_plan = {
                'hippocampus': True,
                'temporal_lobe': True,
                'prefrontal': False,
                'amygdala': False,
                'basal_ganglia': False
            }

        if activation_plan.get('hippocampus') and coord.hippocampus:
            try:
                result = await coord.hippocampus.search_memories(query, k=k)
                hippocampus_mems = (
                    result.get('memories', [])
                    if isinstance(result, dict) else result
                )
                for mem in hippocampus_mems:
                    mem['source'] = 'hippocampus'
                    mem['_fallback'] = True
                fallback_memories.extend(hippocampus_mems)
            except Exception as e:
                logger.warning(
                    f"Semantic fallback from Hippocampus failed: {e}"
                )

        if activation_plan.get('temporal_lobe') and coord.temporal_lobe:
            try:
                result = await coord.temporal_lobe.search_memories(query, k=k)
                temporal_mems = (
                    result.get('memories', [])
                    if isinstance(result, dict) else result
                )
                for mem in temporal_mems:
                    mem['source'] = 'temporal_lobe'
                    mem['_fallback'] = True
                fallback_memories.extend(temporal_mems)
            except Exception as e:
                logger.warning(
                    f"Semantic fallback from Temporal Lobe failed: {e}"
                )

        logger.info(
            f"   Semantic fallback retrieved "
            f"{len(fallback_memories)} memories"
        )

        return fallback_memories

    async def extract_semantic_from_episodes(
        self,
        episodes: List[Dict[str, Any]],
        date: str
    ) -> Optional[str]:
        """
        Extract semantic knowledge from episodic memories

        Uses LLM to understand common patterns and core knowledge

        Args:
            episodes: List of episodic memories
            date: Date label

        Returns:
            Extracted semantic knowledge string, or None if extraction fails
        """
        from ..core.config import get_config

        coord = self._coordinator

        combined_content = "\n".join([
            f"- {ep.get('content', '')[:200]}"
            for ep in episodes[:10]
        ])

        prompt = (
            f"Extract core semantic knowledge from the following "
            f"{len(episodes)} episodic memories:\n\n"
            f"Date: {date}\n\n"
            f"Episodic memories:\n{combined_content}\n\n"
            f"Please extract:\n"
            f"1. Core facts and knowledge points\n"
            f"2. Common themes or patterns\n"
            f"3. Important entity relationships\n\n"
            f"Output as concise semantic knowledge (2-3 sentences)."
        )

        try:
            response = await coord.consolidation_agent.call_llm(
                prompt=prompt,
                max_tokens=300,
                temperature=get_config().token.extraction_temperature
            )

            semantic_knowledge = response.strip()

            if len(semantic_knowledge) < 10:
                return None

            return f"[{date}] {semantic_knowledge}"

        except Exception as e:
            logger.warning(
                f"Failed to extract semantic knowledge: {e}"
            )
            return None
