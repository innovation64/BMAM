"""
Background Memory Processes Manager
Phase 2: Metadata-driven consolidation/forgetting with coverage/conflict awareness

Implements three neurobiologically-inspired background processes:
1. Consolidation: Hippocampus → Temporal Lobe (episodic → semantic)
2. Forgetting: Adaptive memory cleanup based on usage patterns
3. Reconsolidation: Strengthening memories on re-activation

Phase 2 Enhancements:
- Coverage-aware consolidation: Prioritize high-coverage memories
- Conflict-aware forgetting: Review conflicted memories before deletion
- Plasticity-driven reconsolidation: Boost frequently accessed memories
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class BackgroundProcessConfig:
    """Configuration for background memory processes"""

    # General settings
    enabled: bool = True
    test_mode: bool = False
    run_on_startup: bool = False

    # Consolidation settings (in seconds for flexibility)
    consolidation_interval_seconds: float = 3600.0  # 1 hour default
    min_hit_count_for_consolidation: int = 3    # Must be accessed 3+ times
    min_confidence_for_consolidation: float = 0.6

    # Forgetting settings
    forgetting_interval_seconds: float = 7200.0     # 2 hours default
    decay_threshold_for_forgetting: float = 0.3
    max_unused_days: int = 30                   # Delete if unused for 30 days

    # Reconsolidation settings
    reconsolidation_interval_seconds: float = 1800.0  # 30 minutes default
    min_hit_count_for_boost: int = 2
    boost_amount: float = 0.1

    # Phase 2: Coverage/Conflict thresholds
    high_coverage_bonus: float = 0.15           # Extra boost for high-coverage memories
    conflict_penalty: float = 0.1               # Penalty for conflicted memories
    min_coverage_for_consolidation: float = 0.5  # Don't consolidate low-coverage memories


class BackgroundMemoryProcessManager:
    """
    Manages background memory processes for the brain-inspired memory system

    Phase 2 Integration:
    - Consolidation prioritizes memories with high keyword coverage
    - Forgetting reviews conflict status before deletion
    - Reconsolidation uses plasticity scores
    """

    def __init__(self, brain_coordinator, config: BackgroundProcessConfig):
        self.coordinator = brain_coordinator
        self.config = config
        self.running = False
        self.tasks = []


    async def start(self):
        """Start all background processes"""
        if self.running:
            logger.warning("Background processes already running")
            return

        self.running = True

        # Start periodic tasks
        self.tasks = [
            asyncio.create_task(self._consolidation_loop()),
            asyncio.create_task(self._forgetting_loop()),
            asyncio.create_task(self._reconsolidation_loop())
        ]


    async def stop(self):
        """Stop all background processes"""
        if not self.running:
            return

        self.running = False

        for task in self.tasks:
            task.cancel()

        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()


    # ============================================================================
    # Consolidation Loop: Hippocampus → Temporal Lobe
    # ============================================================================

    async def _consolidation_loop(self):
        """
        Periodic consolidation: Move high-value episodic memories to semantic storage

        Phase 2 Enhancement:
        - Prioritize memories with high keyword coverage
        - Skip memories with unresolved conflicts
        """
        interval_seconds = self.config.consolidation_interval_seconds

        while self.running:
            try:
                await asyncio.sleep(interval_seconds)

                if not self.running:
                    break

                await self._run_consolidation()

            except asyncio.CancelledError:
                break
            except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                logger.error(f"❌ Consolidation loop error: {e}", exc_info=True)

    async def _run_consolidation(self, force_all: bool = False):
        """
        Execute one consolidation cycle

        Process:
        1. Scan hippocampus for high-frequency episodic memories
        2. Filter by coverage/conflict (Phase 2) [unless force_all=True]
        3. Extract semantic knowledge via MemoryConsolidationPipeline
        4. Store in temporal lobe with source tracking

        Args:
            force_all: If True, consolidate ALL memories without filtering (for testing)

        NEW: Uses MemoryConsolidationPipeline for sophisticated extraction
        """
        if not hasattr(self.coordinator, 'hippocampus') or not self.coordinator.hippocampus:
            logger.warning("⚠️ Hippocampus not available, skipping consolidation")
            return

        if not hasattr(self.coordinator, 'temporal_lobe') or not self.coordinator.temporal_lobe:
            logger.warning("⚠️ Temporal lobe not available, skipping consolidation")
            return

        # Get consolidation pipeline with agent proxies
        from .memory_consolidation_pipeline import MemoryConsolidationPipeline
        from .agent_storage_proxy import AgentStorageProxy

        pipeline = MemoryConsolidationPipeline()

        # Wrap agents in storage proxies (agents don't have region_store API)
        hippocampus_proxy = AgentStorageProxy(self.coordinator.hippocampus, 'hippocampus')
        temporal_lobe_proxy = AgentStorageProxy(self.coordinator.temporal_lobe, 'temporal_lobe')

        # Get all episodic memories from hippocampus
        episodic_memories = await self._get_episodic_memories()

        if not episodic_memories:
            logger.info("No episodic memories to consolidate")
            return

        # Filter memories by consolidation criteria (unless force_all=True)
        candidates = []
        skipped_low_coverage = 0
        skipped_conflicts = 0

        if force_all:
            # Force mode: consolidate ALL memories
            candidates = [mem.get('id') for mem in episodic_memories]
            logger.info(f"Force mode: consolidating ALL {len(candidates)} memories")
        else:
            # Normal mode: filter by criteria
            for mem in episodic_memories:
                mem_id = mem.get('id', 'unknown')
                metadata = mem.get('metadata', {})

                # Check consolidation criteria
                hit_count = metadata.get('hit_count', 0)
                confidence = metadata.get('confidence', 0.5)

                if hit_count < self.config.min_hit_count_for_consolidation:
                    continue

                if confidence < self.config.min_confidence_for_consolidation:
                    continue

                # Phase 2: Check coverage
                coverage = metadata.get('keyword_coverage', 0.0)
                if coverage < self.config.min_coverage_for_consolidation:
                    skipped_low_coverage += 1
                    continue

                # Phase 2: Check conflicts
                conflict_count = metadata.get('conflict_count', 0)
                if conflict_count > 0:
                    skipped_conflicts += 1
                    logger.warning(f"⚠️ Skipping {mem_id[:8]} - has {conflict_count} conflicts")
                    continue

                candidates.append(mem_id)

        if not candidates:
            logger.info(f"No memories passed consolidation criteria "
                       f"({skipped_low_coverage} low coverage, {skipped_conflicts} conflicts)")
            return

        logger.info(f"Consolidating {len(candidates)} episodic memories to semantic knowledge")

        # Use pipeline's batch_consolidate with proxies
        try:
            results = await pipeline.batch_consolidate(
                memory_ids=candidates,
                consolidation_type='episodic_to_semantic',
                source_storage=hippocampus_proxy,
                target_storage=temporal_lobe_proxy,
                priority=0.7
            )

            successful = sum(1 for r in results if r.success)
            logger.info(f"Consolidation complete: {successful}/{len(candidates)} successful, "
                       f"{skipped_low_coverage} skipped (low coverage), "
                       f"{skipped_conflicts} skipped (conflicts)")

        except Exception as e:
            logger.error(f"Batch consolidation failed: {e}")
            import traceback
            traceback.print_exc()

    async def _get_episodic_memories(self) -> List[Dict]:
        """Get all episodic memories from hippocampus"""
        try:
            # Use search_memories with empty query to get all
            result = await self.coordinator.hippocampus.search_memories(
                query='',
                k=1000
            )
            return result.get('results', [])
        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            logger.error(f"Failed to get episodic memories: {e}")
            return []

    # ============================================================================
    # Forgetting Loop: Adaptive Memory Cleanup
    # ============================================================================

    async def _forgetting_loop(self):
        """
        Periodic forgetting: Remove low-value memories

        Phase 2 Enhancement:
        - Review conflict status before deletion
        - Preserve memories involved in unresolved conflicts
        """
        interval_seconds = self.config.forgetting_interval_seconds

        while self.running:
            try:
                await asyncio.sleep(interval_seconds)

                if not self.running:
                    break

                await self._run_forgetting()

            except asyncio.CancelledError:
                break
            except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                logger.error(f"❌ Forgetting loop error: {e}", exc_info=True)

    async def _run_forgetting(self):
        """
        Execute one forgetting cycle

        Criteria for forgetting:
        1. Low decay_factor (< 0.3)
        2. Low hit_count (< 2)
        3. Not accessed in 30+ days
        4. Phase 2: No unresolved conflicts
        """
        if not hasattr(self.coordinator, 'hippocampus') or not self.coordinator.hippocampus:
            logger.warning("⚠️ Hippocampus not available, skipping forgetting")
            return

        episodic_memories = await self._get_episodic_memories()

        if not episodic_memories:
            return

        forgotten_count = 0
        preserved_conflicts = 0
        now = datetime.now()

        for mem in episodic_memories:
            mem_id = mem.get('id', 'unknown')
            metadata = mem.get('metadata', {})

            decay_factor = metadata.get('decay_factor', 1.0)
            hit_count = metadata.get('hit_count', 0)
            last_accessed = metadata.get('last_accessed')

            # Check forgetting criteria
            if decay_factor >= self.config.decay_threshold_for_forgetting:
                continue

            if hit_count >= 2:
                continue

            # Check last access time
            if last_accessed:
                try:
                    last_access_dt = datetime.fromisoformat(last_accessed)
                    days_unused = (now - last_access_dt).days

                    if days_unused < self.config.max_unused_days:
                        continue
                except (ValueError, TypeError) as e:
                    logger.debug(f"Failed to parse last access time: {e}")

            # Phase 2: Check conflict status
            conflict_count = metadata.get('conflict_count', 0)
            if conflict_count > 0:
                preserved_conflicts += 1
                continue

            # Forget this memory
            try:
                await self._delete_memory(mem_id)
                forgotten_count += 1
            except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                logger.error(f"❌ Failed to forget {mem_id[:8]}: {e}")

        logger.info(f"Forgotten {forgotten_count} low-decay memories, "
                   f"{preserved_conflicts} preserved (conflicts)")

    async def _delete_memory(self, memory_id: str):
        """Delete a memory from hippocampus"""
        if hasattr(self.coordinator.hippocampus, 'delete_memory'):
            await self.coordinator.hippocampus.delete_memory(memory_id)
        elif hasattr(self.coordinator.hippocampus, 'delete'):
            await self.coordinator.hippocampus.delete(memory_id)
        else:
            logger.warning(f"No delete method available for memory {memory_id}")

    # ============================================================================
    # Reconsolidation Loop: Strengthen on Re-activation
    # ============================================================================

    async def _reconsolidation_loop(self):
        """
        Periodic reconsolidation: Strengthen frequently accessed memories

        Phase 2 Enhancement:
        - Use plasticity scores for boost amount
        - Apply coverage bonus
        - Apply conflict penalty
        """
        interval_seconds = self.config.reconsolidation_interval_seconds

        while self.running:
            try:
                await asyncio.sleep(interval_seconds)

                if not self.running:
                    break

                await self._run_reconsolidation()

            except asyncio.CancelledError:
                break
            except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                logger.error(f"❌ Reconsolidation loop error: {e}", exc_info=True)

    async def _run_reconsolidation(self):
        """
        Execute one reconsolidation cycle

        Process:
        1. Find memories with hit_count >= 2
        2. Apply Phase 2 plasticity boost (coverage bonus, conflict penalty)
        3. Update confidence and decay_factor
        """
        episodic_memories = await self._get_episodic_memories()

        if not episodic_memories:
            return

        reconsolidated_count = 0

        for mem in episodic_memories:
            mem_id = mem.get('id', 'unknown')
            metadata = mem.get('metadata', {})

            hit_count = metadata.get('hit_count', 0)

            if hit_count < self.config.min_hit_count_for_boost:
                continue

            # Phase 2: Calculate plasticity-based boost
            base_boost = self.config.boost_amount

            # Coverage bonus
            coverage = metadata.get('keyword_coverage', 0.0)
            if coverage > 0.75:  # High coverage
                coverage_bonus = self.config.high_coverage_bonus
            else:
                coverage_bonus = 0.0

            # Conflict penalty
            conflict_count = metadata.get('conflict_count', 0)
            conflict_penalty = conflict_count * self.config.conflict_penalty

            # Total boost
            total_boost = max(0.0, base_boost + coverage_bonus - conflict_penalty)

            if total_boost > 0:
                # Update memory metadata
                new_confidence = min(1.0, metadata.get('confidence', 0.5) + total_boost)
                new_decay = min(1.0, metadata.get('decay_factor', 0.8) + total_boost * 0.5)

                try:
                    await self._update_memory_metadata(mem_id, {
                        'confidence': new_confidence,
                        'decay_factor': new_decay,
                        'last_reconsolidation': datetime.now().isoformat()
                    })

                    reconsolidated_count += 1
                    logger.debug(f"Reconsolidated {mem_id[:8]} "
                               f"(boost={total_boost:.2f}, coverage={coverage:.2f}, conflicts={conflict_count})")

                except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                    logger.error(f"❌ Failed to reconsolidate {mem_id[:8]}: {e}")


    async def _update_memory_metadata(self, memory_id: str, updates: Dict):
        """Update memory metadata"""
        if hasattr(self.coordinator.hippocampus, 'update_metadata'):
            await self.coordinator.hippocampus.update_metadata(memory_id, updates)
        else:
            logger.warning(f"No update_metadata method available for {memory_id}")
