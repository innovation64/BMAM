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

    # 🔥 NEW Phase 3: Emotion-aware thresholds
    emotion_consolidation_bonus: float = 0.2    # Bonus for emotionally significant memories
    high_emotion_intensity_threshold: float = 0.6  # Threshold for high emotion
    negative_feedback_penalty: float = 0.15     # Penalty for memories with negative feedback
    max_negative_feedback_for_consolidation: int = 3  # Skip if too much negative feedback
    emotion_protection_threshold: float = 0.7   # Don't forget highly emotional memories

    # 🔥 NEW Phase 3: Load-aware scheduling thresholds
    load_aware_enabled: bool = True             # Enable load-aware scheduling
    cpu_high_threshold: float = 70.0            # CPU% above which to throttle
    cpu_critical_threshold: float = 85.0        # CPU% above which to skip entirely
    memory_high_threshold: float = 75.0         # Memory% above which to throttle
    memory_critical_threshold: float = 90.0     # Memory% above which to skip entirely
    interval_scale_factor_high_load: float = 2.0   # Multiply interval by this when high load
    interval_scale_factor_critical: float = 5.0    # Multiply interval by this when critical
    min_interval_between_processes: float = 10.0   # Minimum seconds between any two process runs


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
        self._loop_lock = asyncio.Lock()

        # 🔥 NEW Phase 3: Load-aware scheduling state
        self._last_process_time = datetime.now()
        self._load_stats = {
            'cpu': 0.0,
            'memory': 0.0,
            'last_check': None,
            'skipped_runs': 0,
            'throttled_runs': 0
        }

    # ============================================================================
    # 🔥 Phase 3: Load-Aware Scheduling
    # ============================================================================

    def _get_system_load(self) -> Dict[str, float]:
        """
        获取当前系统负载

        Returns:
            {'cpu': float, 'memory': float}
        """
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent

            self._load_stats['cpu'] = cpu_percent
            self._load_stats['memory'] = memory_percent
            self._load_stats['last_check'] = datetime.now()

            return {'cpu': cpu_percent, 'memory': memory_percent}
        except ImportError:
            logger.debug("psutil not available, assuming low load")
            return {'cpu': 0.0, 'memory': 0.0}
        except Exception as e:
            logger.warning(f"Failed to get system load: {e}")
            return {'cpu': 0.0, 'memory': 0.0}

    def _should_skip_due_to_load(self, process_name: str) -> bool:
        """
        判断是否因系统负载过高而跳过执行

        Args:
            process_name: 进程名称（用于日志）

        Returns:
            True if should skip
        """
        if not self.config.load_aware_enabled:
            return False

        load = self._get_system_load()

        # Critical load - skip entirely
        if load['cpu'] >= self.config.cpu_critical_threshold:
            logger.warning(f"⚠️ Skipping {process_name}: CPU critical ({load['cpu']:.1f}%)")
            self._load_stats['skipped_runs'] += 1
            return True

        if load['memory'] >= self.config.memory_critical_threshold:
            logger.warning(f"⚠️ Skipping {process_name}: Memory critical ({load['memory']:.1f}%)")
            self._load_stats['skipped_runs'] += 1
            return True

        return False

    def _get_adjusted_interval(self, base_interval: float) -> float:
        """
        根据系统负载调整执行间隔

        Args:
            base_interval: 基础间隔（秒）

        Returns:
            调整后的间隔
        """
        if not self.config.load_aware_enabled:
            return base_interval

        load = self._get_system_load()

        # High load - throttle (increase interval)
        if (load['cpu'] >= self.config.cpu_high_threshold or
            load['memory'] >= self.config.memory_high_threshold):

            adjusted = base_interval * self.config.interval_scale_factor_high_load
            self._load_stats['throttled_runs'] += 1
            logger.debug(f"📊 High load detected (CPU={load['cpu']:.1f}%, MEM={load['memory']:.1f}%), "
                        f"interval adjusted: {base_interval:.0f}s → {adjusted:.0f}s")
            return adjusted

        return base_interval

    async def _wait_for_process_slot(self) -> None:
        """
        等待进程执行槽位（确保进程间有最小间隔）
        """
        now = datetime.now()
        elapsed = (now - self._last_process_time).total_seconds()

        if elapsed < self.config.min_interval_between_processes:
            wait_time = self.config.min_interval_between_processes - elapsed
            logger.debug(f"⏳ Waiting {wait_time:.1f}s for process slot")
            await asyncio.sleep(wait_time)

        self._last_process_time = datetime.now()

    def get_load_stats(self) -> Dict[str, Any]:
        """获取负载统计信息"""
        return {
            **self._load_stats,
            'load_aware_enabled': self.config.load_aware_enabled
        }


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

        🔥 Phase 3 Enhancement:
        - Load-aware scheduling
        - Dynamic interval adjustment
        """
        base_interval = self.config.consolidation_interval_seconds

        while self.running:
            try:
                # 🔥 Phase 3: 根据负载调整间隔
                interval_seconds = self._get_adjusted_interval(base_interval)
                await asyncio.sleep(interval_seconds)

                if not self.running:
                    break

                # 🔥 Phase 3: 负载过高时跳过
                if self._should_skip_due_to_load('consolidation'):
                    continue

                # 🔥 Phase 3: 等待进程槽位
                await self._wait_for_process_slot()

                async with self._loop_lock:
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
            skipped_negative_feedback = 0
            prioritized_emotional = 0

            for mem in episodic_memories:
                mem_id = mem.get('id', 'unknown')
                metadata = mem.get('metadata', {})

                # Check consolidation criteria
                hit_count = metadata.get('hit_count', 0)
                confidence = metadata.get('confidence', 0.5)

                # 🔥 NEW Phase 3: Check emotion factors
                emotion_intensity = mem.get('emotion_intensity', 0.0)
                emotion_modulations = metadata.get('emotion_modulations', [])
                negative_feedback_count = metadata.get('negative_feedback_count', 0)

                # Skip memories with too much negative feedback
                if negative_feedback_count >= self.config.max_negative_feedback_for_consolidation:
                    skipped_negative_feedback += 1
                    continue

                # Emotionally significant memories get priority (lower thresholds)
                is_emotional = (
                    emotion_intensity >= self.config.high_emotion_intensity_threshold or
                    len(emotion_modulations) > 0
                )

                # Adjust thresholds for emotional memories
                min_hit_count = self.config.min_hit_count_for_consolidation
                min_confidence = self.config.min_confidence_for_consolidation
                if is_emotional:
                    min_hit_count = max(1, min_hit_count - 1)  # Lower threshold
                    min_confidence = max(0.3, min_confidence - 0.2)  # Lower threshold
                    prioritized_emotional += 1

                if hit_count < min_hit_count:
                    continue

                if confidence < min_confidence:
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

            if prioritized_emotional > 0:
                logger.info(f"📊 Emotion-aware consolidation: {prioritized_emotional} emotional memories prioritized")
            if skipped_negative_feedback > 0:
                logger.info(f"📊 Skipped {skipped_negative_feedback} memories with negative feedback")

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
            # 🔥 2025-12-11 修复: search_memories 返回键是 'memories' 不是 'results'
            return result.get('memories', [])
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

        🔥 Phase 3 Enhancement:
        - Load-aware scheduling
        - Dynamic interval adjustment
        """
        base_interval = self.config.forgetting_interval_seconds

        while self.running:
            try:
                # 🔥 Phase 3: 根据负载调整间隔
                interval_seconds = self._get_adjusted_interval(base_interval)
                await asyncio.sleep(interval_seconds)

                if not self.running:
                    break

                # 🔥 Phase 3: 负载过高时跳过
                if self._should_skip_due_to_load('forgetting'):
                    continue

                # 🔥 Phase 3: 等待进程槽位
                await self._wait_for_process_slot()

                async with self._loop_lock:
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
        preserved_emotional = 0  # 🔥 NEW Phase 3
        now = datetime.now()

        for mem in episodic_memories:
            mem_id = mem.get('id', 'unknown')
            metadata = mem.get('metadata', {})

            decay_factor = metadata.get('decay_factor', 1.0)
            hit_count = metadata.get('hit_count', 0)
            last_accessed = metadata.get('last_accessed')

            # 🔥 NEW Phase 3: Check emotion protection
            # Highly emotional memories should not be forgotten
            emotion_intensity = mem.get('emotion_intensity', 0.0)
            emotion_modulations = metadata.get('emotion_modulations', [])
            is_highly_emotional = (
                emotion_intensity >= self.config.emotion_protection_threshold or
                len(emotion_modulations) >= 2  # Multiple emotional modulations = important
            )

            if is_highly_emotional:
                preserved_emotional += 1
                continue  # Protect from forgetting

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
                   f"{preserved_conflicts} preserved (conflicts), "
                   f"{preserved_emotional} preserved (emotional)")

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

        🔥 Phase 3 Enhancement:
        - Load-aware scheduling
        - Dynamic interval adjustment
        """
        base_interval = self.config.reconsolidation_interval_seconds

        while self.running:
            try:
                # 🔥 Phase 3: 根据负载调整间隔
                interval_seconds = self._get_adjusted_interval(base_interval)
                await asyncio.sleep(interval_seconds)

                if not self.running:
                    break

                # 🔥 Phase 3: 负载过高时跳过
                if self._should_skip_due_to_load('reconsolidation'):
                    continue

                # 🔥 Phase 3: 等待进程槽位
                await self._wait_for_process_slot()

                async with self._loop_lock:
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
