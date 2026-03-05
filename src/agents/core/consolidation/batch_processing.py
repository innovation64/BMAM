"""
Batch Processing Mixin
批处理模块 - 批量巩固和队列处理
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class BatchProcessingMixin:
    """批处理Mixin - 处理批量巩固和队列"""

    async def _batch_consolidation(self, batch_size: int = 10) -> Dict[str, Any]:
        """Process a batch of memories for consolidation"""

        # First evaluate candidates
        evaluation = await self._evaluate_consolidation_candidates()

        if 'error' in evaluation:
            return evaluation

        # Process immediate candidates first
        immediate_candidates = evaluation['candidates']['immediate'][:batch_size]

        batch_results = []

        for candidate in immediate_candidates:
            result = await self._consolidate_single_memory(candidate['memory_id'])
            batch_results.append(result)

        # If we have room, process delayed candidates
        remaining_capacity = batch_size - len(batch_results)
        if remaining_capacity > 0:
            delayed_candidates = evaluation['candidates']['delayed'][:remaining_capacity]

            for candidate in delayed_candidates:
                result = await self._consolidate_single_memory(candidate['memory_id'])
                batch_results.append(result)

        successful_consolidations = [r for r in batch_results if r.get('consolidated')]

        return {
            'batch_consolidation_complete': True,
            'batch_size': batch_size,
            'processed': len(batch_results),
            'successful': len(successful_consolidations),
            'success_rate': len(successful_consolidations) / len(batch_results) if batch_results else 0,
            'results': batch_results
        }

    async def _process_chunked_text_queue(self) -> Dict[str, Any]:
        """Process queued chunked text segments for consolidation - now handles ALL segments"""
        from ....memory.memory_system import memory_system

        try:
            # Use class variable instead of buffer system
            chunked_queue = self.chunked_text_queue

            if not chunked_queue:
                return {'processed': 0, 'message': 'No chunked text in queue'}

            processed_batches = 0
            stored_segments = 0
            processed_segments = 0

            # Process each entry (now potentially batched)
            for entry in chunked_queue:
                try:
                    overview = entry.get('overview', {})
                    segments = entry.get('segments', [])
                    entry_type = entry.get('type', 'chunked_text')

                    # Determine storage worthiness
                    storage_priority = overview.get('storage_priority', 'low')
                    batch_number = entry.get('batch_number', 1)
                    total_segments = entry.get('total_segments', len(segments))

                    logger.debug(f"Processing {entry_type} batch {batch_number} with {len(segments)} segments")

                    # Store segments based on priority and batch position
                    should_store = self._should_store_batch(storage_priority, batch_number, total_segments)

                    if should_store:
                        # Store ALL segments in this batch (no truncation)
                        for seg in segments:
                            try:
                                # Adjust importance based on segment position and batch
                                importance = self._calculate_segment_importance(
                                    seg, storage_priority, batch_number, total_segments
                                )

                                memory_id = await memory_system.store_memory(
                                    content=seg['summary'],
                                    memory_type='episodic',
                                    importance=importance,
                                    context_tags=['chunked_text', 'consolidation_processed', 'complete_set'],
                                    metadata={
                                        'segment_index': seg['index'],
                                        'batch_number': batch_number,
                                        'total_segments': total_segments,
                                        'parent_theme': overview.get('theme', ''),
                                        'keywords': seg.get('keywords', []),
                                        'processing_method': seg.get('processing_method', 'local'),
                                        'storage_priority': storage_priority,
                                        'consolidated_at': datetime.now().isoformat()
                                    }
                                )

                                if memory_id:
                                    stored_segments += 1

                                processed_segments += 1

                            except Exception as seg_error:
                                logger.warning(f"Failed to store segment {seg.get('index', '?')}: {seg_error}")
                                processed_segments += 1  # Count as processed even if failed
                                continue
                    else:
                        # Even if not storing, count as processed
                        processed_segments += len(segments)
                        logger.debug(f"Skipped storing batch {batch_number} (priority: {storage_priority})")

                    processed_batches += 1

                except Exception as entry_error:
                    logger.warning(f"Failed to process chunked text entry: {entry_error}")
                    continue

            # Clear the processed queue (use class variable)
            self.chunked_text_queue = []

            logger.debug(f"Processed {processed_batches} batches ({processed_segments} segments total), stored {stored_segments} segments")

            return {
                'processed_batches': processed_batches,
                'processed_segments': processed_segments,
                'stored_segments': stored_segments,
                'storage_rate': stored_segments / processed_segments if processed_segments > 0 else 0,
                'status': 'completed'
            }

        except Exception as e:
            logger.error(f"Failed to process chunked text queue: {e}")
            return {'error': str(e)}

    def _should_store_batch(self, storage_priority: str, batch_number: int, total_segments: int) -> bool:
        """Determine if a batch should be stored based on priority and position"""
        if storage_priority == 'high':
            return True  # Store all batches for high priority
        elif storage_priority == 'medium':
            # Store first 3 batches (up to 15 segments)
            return batch_number <= 3
        else:  # low priority
            # Store only first batch (up to 5 segments)
            return batch_number == 1

    def _calculate_segment_importance(self, segment: Dict, priority: str, batch_number: int, total_segments: int) -> float:
        """Calculate importance score for a segment based on position and priority"""
        base_importance = {
            'high': 0.7,
            'medium': 0.5,
            'low': 0.3
        }.get(priority, 0.3)

        # Reduce importance for later batches
        batch_penalty = (batch_number - 1) * 0.1
        importance = max(0.2, base_importance - batch_penalty)

        # First few segments get slight boost
        segment_index = segment.get('index', 0)
        if segment_index < 3:
            importance += 0.1

        return min(1.0, importance)

    async def _consolidate_preference(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Consolidate user preference information"""
        try:
            # Apply preference boost
            importance_boost = content.get('importance_boost', 0.2)

            # This is primarily a preference consolidation marker
            # The actual preference storage happens in background in brain_coordinator

            return {
                'preference_consolidation_triggered': True,
                'importance_boost_applied': importance_boost,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to consolidate preference: {e}")
            return {'error': str(e)}
