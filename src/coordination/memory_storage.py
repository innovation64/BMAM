"""
Memory Storage Handler
Handles storage-related operations: store_long_document, chunking, dispatch, consolidation, forgetting
"""

import asyncio
import json
import re
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..utils.config import get_logger, get_settings
from ..utils.model_selector import select_model_for_task
from ..utils.token_utils import estimate_tokens
from ..core.config import get_config
from .clean_agent_system import AgentMessage

logger = get_logger(__name__)


class MemoryStorageHandler:
    """Handles all storage-related operations for MemoryCoordinator"""

    def __init__(self, coordinator: 'MemoryCoordinator'):
        self._coordinator = coordinator

    async def store_long_document(
        self,
        content: str,
        timestamp: datetime,
        document_id: str = None,
        speaker: str = None,
        importance: float = 0.5,
        extract_events: bool = True,
        store_to_external: bool = True,
        async_summary: bool = False
    ) -> Dict[str, Any]:
        """
        Correctly handle long documents by:
        1. Storing original text to external storage
        2. Extracting key events/information
        3. Storing shaped memories (not raw text) to brain regions

        This is the CORRECT way to handle long context - not storing raw chunks.

        Args:
            content: Long document content
            timestamp: Document timestamp
            document_id: Unique ID for this document (generated if not provided)
            speaker: Speaker/author
            importance: Base importance score
            extract_events: Extract event representations (default: True)
            store_to_external: Store original to external storage (default: True)
            async_summary: Generate summary asynchronously (default: False)

        Returns:
            {
                'document_id': str,
                'external_stored': bool,
                'events_extracted': int,
                'memories_created': int,
                'summary': str
            }
        """
        _logger = logging.getLogger(__name__)
        settings = get_settings()
        coord = self._coordinator

        if document_id is None:
            document_id = f"doc_{uuid.uuid4().hex[:12]}"

        result = {
            'document_id': document_id,
            'external_stored': False,
            'events_extracted': 0,
            'memories_created': 0,
            'summary': None
        }

        estimated_tokens = estimate_tokens(content)
        _logger.info(f"Processing document: {estimated_tokens} tokens, id={document_id}")

        _cfg = get_config()

        if estimated_tokens < _cfg.token.short_threshold:
            _logger.info(
                f"   Short content ({estimated_tokens} tokens) -> "
                f"storing ORIGINAL TEXT to Hippocampus"
            )

            await coord.hippocampus.store_memory_with_event_segmentation(
                content=content,
                timestamp=timestamp,
                speaker=speaker,
                importance=importance
            )

            result['memories_created'] = 1
            result['storage_strategy'] = 'original_to_hippocampus'
            _logger.info("Short document stored as original text (no abstraction needed)")

            return result

        # For medium/long documents, continue with external storage + abstraction
        # Step 1: Store original to external storage (if memory_system available)
        if (store_to_external and hasattr(coord, 'memory_system')
                and coord.memory_system):
            try:
                external_metadata = {
                    'document_id': document_id,
                    'timestamp': timestamp.isoformat(),
                    'speaker': speaker,
                    'importance': importance,
                    'token_count': estimated_tokens,
                    'type': 'long_document_original'
                }

                await coord.memory_system.store_memory(
                    content=content,
                    metadata=external_metadata
                )
                result['external_stored'] = True
                _logger.info("   Original document stored to external storage")
            except Exception as e:
                _logger.warning(f"   Failed to store to external: {e}")

        # Step 2: Extract event representations or key paragraphs
        events = []
        if extract_events:
            from src.services.shared_openai_client import shared_client_manager
            client = await shared_client_manager.get_chat_client()

            if estimated_tokens < _cfg.token.medium_threshold:
                _logger.info(
                    f"   Medium content ({estimated_tokens} tokens) -> "
                    f"extracting key paragraphs with original text..."
                )

                try:
                    extraction_prompt = (
                        f"Extract 3-5 most important paragraphs or fragments "
                        f"from the following document.\n\n"
                        f"Document content:\n{content}\n\n"
                        f"Please extract:\n"
                        f"1. Key dialogue fragments (preserve original text)\n"
                        f"2. Important factual paragraphs (preserve original text)\n"
                        f"3. Core viewpoint paragraphs (preserve original text)\n\n"
                        f"Output in JSON format, each fragment containing ORIGINAL TEXT:\n"
                        f"{{\"paragraphs\": [\n"
                        f"  {{\"type\": \"dialogue\", \"original_text\": "
                        f"\"full original text...\", \"importance\": 0.8}},\n"
                        f"  {{\"type\": \"fact\", \"original_text\": "
                        f"\"full original text...\", \"importance\": 0.7}}\n"
                        f"]}}"
                    )

                    extraction_model = select_model_for_task('extraction')

                    response = await client.chat.completions.create(
                        model=extraction_model,
                        messages=[{"role": "user", "content": extraction_prompt}],
                        temperature=_cfg.token.extraction_temperature,
                        max_tokens=2000
                    )

                    response_text = response.choices[0].message.content
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        extracted = json.loads(json_match.group())
                        paragraphs = extracted.get('paragraphs', [])
                        events = [
                            {
                                'type': p.get('type', 'paragraph'),
                                'original_text': p.get('original_text', ''),
                                'importance': p.get('importance', importance)
                            }
                            for p in paragraphs
                        ]
                        _logger.info(
                            f"      Extracted {len(events)} key paragraphs "
                            f"with original text"
                        )

                except Exception as e:
                    _logger.warning(f"   Paragraph extraction failed: {e}")

            else:
                _logger.info(
                    f"   Long content ({estimated_tokens} tokens) -> "
                    f"extracting event abstractions..."
                )

                try:
                    truncated_content = content[:4000]
                    extraction_prompt = (
                        f"Extract key events and important information from "
                        f"the following long document.\n\n"
                        f"Document content:\n{truncated_content}\n\n"
                        f"Please extract:\n"
                        f"1. Key events (time, place, people, actions)\n"
                        f"2. Important facts and data\n"
                        f"3. Core viewpoints and conclusions\n\n"
                        f"Output in JSON format, one object per event/information:\n"
                        f"{{\"events\": [\n"
                        f"  {{\"type\": \"event\", \"description\": \"...\", "
                        f"\"importance\": 0.8}},\n"
                        f"  {{\"type\": \"fact\", \"description\": \"...\", "
                        f"\"importance\": 0.6}}\n"
                        f"]}}"
                    )

                    extraction_model = select_model_for_task('extraction')

                    response = await client.chat.completions.create(
                        model=extraction_model,
                        messages=[{"role": "user", "content": extraction_prompt}],
                        temperature=_cfg.token.extraction_temperature,
                        max_tokens=_cfg.token.max_chunk_tokens
                    )

                    response_text = response.choices[0].message.content
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        extracted = json.loads(json_match.group())
                        events = extracted.get('events', [])
                        _logger.info(f"      Extracted {len(events)} events/facts")

                except Exception as e:
                    _logger.warning(f"   Event extraction failed: {e}")

        # Step 3: Store to Hippocampus + dispatch to other brain regions
        memories_created = 0
        dispatched_summary = {'amygdala': 0, 'prefrontal': 0, 'basal_ganglia': 0}

        for event in events:
            try:
                event_importance = event.get('importance', importance)

                if 'original_text' in event:
                    content_to_store = event['original_text']
                    storage_type = "original paragraph"
                else:
                    content_to_store = (
                        f"[Document: {document_id}] "
                        f"{event.get('description', '')}"
                    )
                    storage_type = "event abstraction"

                _logger.debug(
                    f"   Storing {storage_type}: {content_to_store[:50]}..."
                )

                hippocampus_result = (
                    await coord.hippocampus.store_memory_with_event_segmentation(
                        content=content_to_store,
                        timestamp=timestamp,
                        speaker=speaker,
                        importance=event_importance
                    )
                )
                memories_created += 1

                memory_id = hippocampus_result.get('memory_id')
                dispatched = await self._dispatch_to_other_brain_regions(
                    content=content_to_store,
                    memory_id=memory_id,
                    importance=event_importance,
                    timestamp=timestamp
                )

                for region, ids in dispatched.items():
                    dispatched_summary[region] += len(ids)

            except Exception as e:
                _logger.warning(f"   Failed to store memory: {e}")

        result['events_extracted'] = len(events)
        result['memories_created'] = memories_created
        result['dispatched_to_regions'] = dispatched_summary

        _logger.info(
            f"   Multi-region dispatch: Amygdala={dispatched_summary['amygdala']}, "
            f"Prefrontal={dispatched_summary['prefrontal']}, "
            f"BasalGanglia={dispatched_summary['basal_ganglia']}"
        )

        # Step 4: Summary generation (sync or async based on parameter)
        if async_summary:
            _logger.info("   Launching async post-processing (summary generation)...")
            asyncio.create_task(
                self._async_post_process_summary(
                    document_id=document_id,
                    events=events,
                    timestamp=timestamp
                )
            )
            result['summary'] = '[Generating in background]'
        else:
            try:
                _logger.info("   Creating semantic summary (sync)...")

                summary_model = select_model_for_task('summary')

                summary_prompt = (
                    f"Create a high-level semantic summary (2-3 sentences) "
                    f"for the following document:\n\n"
                    f"Document ID: {document_id}\n"
                    f"Key events: {len(events)}\n\n"
                    f"Briefly summarize the core themes and key information "
                    f"of the document."
                )

                summary_response = await client.chat.completions.create(
                    model=summary_model,
                    messages=[{"role": "user", "content": summary_prompt}],
                    temperature=_cfg.token.extraction_temperature,
                    max_tokens=200
                )

                summary = summary_response.choices[0].message.content.strip()
                result['summary'] = summary

                await coord.temporal_lobe.store_memory(
                    content=f"[Document Summary: {document_id}] {summary}",
                    metadata={
                        'type': 'document_summary',
                        'document_id': document_id,
                        'timestamp': timestamp.isoformat(),
                    }
                )

                _logger.info("      Summary stored to Temporal Lobe")

            except Exception as e:
                _logger.warning(f"   Summary creation failed: {e}")

        _logger.info(
            f"Long document processed: external={result['external_stored']}, "
            f"events={result['events_extracted']}, "
            f"memories={result['memories_created']}"
        )

        return result

    async def store_memory_with_timestamp(
        self,
        content: str,
        timestamp: datetime,
        speaker: str = None,
        importance: float = 0.5,
        auto_chunk: bool = True,
        chunk_threshold: int = 1000,
        chunk_overlap: int = 150,
        async_summary: bool = False,
        inherited_event_time: datetime = None,
        user_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Store memory with custom timestamp (for learning historical conversations)

        Automatically chunks long content with overlap to maintain embedding quality.

        Args:
            content: Memory content
            timestamp: Custom timestamp
            speaker: Speaker name
            importance: Importance score (0.0-1.0)
            auto_chunk: Enable automatic chunking for long content (default: True)
            chunk_threshold: Max tokens per chunk (default: 1000)
            chunk_overlap: Overlap tokens between chunks (default: 150, ~15%)
            inherited_event_time: Inherited event time for [Event] memories
            user_id: User ID for isolation

        Returns:
            {
                'memory_id': str,
                'event_id': str,
                'is_new_event': bool,
                'chunks_created': int,
                'chunk_group_id': str
            }
        """
        _logger = logging.getLogger(__name__)
        coord = self._coordinator

        estimated_tokens = estimate_tokens(content)

        if auto_chunk and estimated_tokens > chunk_threshold:
            _logger.warning(
                f"Memory content is very long ({estimated_tokens} tokens). "
                f"Auto-chunking with {chunk_overlap}-token overlap for better retrieval."
            )

            chunk_group_id = f"chunk_group_{uuid.uuid4().hex[:8]}"

            lines = content.split('\n')
            semantic_units = []
            current_unit = []
            current_tokens = 0

            for line in lines:
                line_tokens = estimate_tokens(line)
                is_turn_boundary = (
                    any(pattern in line for pattern in [':', '\uff1a'])
                    and len(line) < 100
                )

                if is_turn_boundary and current_unit and current_tokens > 200:
                    semantic_units.append('\n'.join(current_unit))
                    current_unit = [line]
                    current_tokens = line_tokens
                else:
                    current_unit.append(line)
                    current_tokens += line_tokens

            if current_unit:
                semantic_units.append('\n'.join(current_unit))

            # Build chunks with overlap
            chunks = []
            i = 0
            while i < len(semantic_units):
                chunk_content = []
                chunk_tokens = 0

                while i < len(semantic_units) and chunk_tokens < chunk_threshold:
                    unit = semantic_units[i]
                    unit_tokens = estimate_tokens(unit)

                    if (chunk_tokens + unit_tokens > chunk_threshold * 1.2
                            and chunk_content):
                        break

                    chunk_content.append(unit)
                    chunk_tokens += unit_tokens
                    i += 1

                if chunk_content:
                    chunks.append('\n'.join(chunk_content))

                # Backtrack for overlap
                if i < len(semantic_units) and len(chunk_content) > 1:
                    overlap_units = chunk_content[-1:]  # noqa: F841
                    i -= 1

            # Fallback: simple splitting
            if (not chunks
                    or len(chunks) == 1
                    and estimated_tokens > chunk_threshold * 2):
                _logger.info("   Falling back to simple token-based chunking")
                chunks = []
                words = content.split()
                current_chunk = []
                current_length = 0

                for word in words:
                    word_tokens = estimate_tokens(word)
                    if (current_length + word_tokens > chunk_threshold
                            and current_chunk):
                        chunks.append(' '.join(current_chunk))
                        overlap_words = current_chunk[-chunk_overlap * 4 // 5:]
                        current_chunk = overlap_words + [word]
                        current_length = sum(
                            estimate_tokens(w) for w in current_chunk
                        )
                    else:
                        current_chunk.append(word)
                        current_length += word_tokens

                if current_chunk:
                    chunks.append(' '.join(current_chunk))

            _logger.info(
                f"Auto-chunked into {len(chunks)} chunks "
                f"(overlap={chunk_overlap} tokens)"
            )

            # Store each chunk with metadata linking them
            date_str = timestamp.strftime("%d %B %Y")

            results = []
            for i, chunk in enumerate(chunks):
                chunk_header = (
                    f"[Context: This conversation is on {date_str}] "
                    f"[Chunk {i+1}/{len(chunks)} | Group: {chunk_group_id}]\n"
                )
                chunk_with_metadata = chunk_header + chunk

                result = (
                    await coord.hippocampus.store_memory_with_event_segmentation(
                        content=chunk_with_metadata,
                        timestamp=timestamp,
                        speaker=speaker,
                        importance=importance,
                        inherited_event_time=inherited_event_time,
                        user_id=user_id
                    )
                )
                results.append(result)

            _logger.info(
                f"   Stored {len(chunks)} chunks with group ID: {chunk_group_id}"
            )

            final_result = results[-1]
            final_result['chunks_created'] = len(chunks)
            final_result['chunk_group_id'] = chunk_group_id
            return final_result

        else:
            # Normal storage for short content
            date_str = timestamp.strftime("%d %B %Y")
            content_with_context = (
                f"[Context: This conversation is on {date_str}] {content}"
            )

            result = (
                await coord.hippocampus.store_memory_with_event_segmentation(
                    content=content_with_context,
                    timestamp=timestamp,
                    speaker=speaker,
                    importance=importance,
                    inherited_event_time=inherited_event_time,
                    user_id=user_id
                )
            )
            result['chunks_created'] = 1

            # Preference extraction for PersonaMemory
            if (speaker == 'user'
                    and hasattr(coord, 'persona_memory')
                    and coord.persona_memory):
                await self._extract_and_store_preferences(
                    content=content,
                    user_id=user_id,
                    timestamp=timestamp
                )

            # 5-Brain Region Collaborative Storage
            memory_id = result.get('memory_id')
            dispatched = await self._dispatch_to_other_brain_regions(
                content=content,
                memory_id=memory_id,
                importance=importance,
                timestamp=timestamp
            )
            result['dispatched_regions'] = dispatched

            dispatch_count = sum(len(ids) for ids in dispatched.values())
            if dispatch_count > 0:
                regions_list = [
                    region for region, ids in dispatched.items() if ids
                ]
                _logger.info(
                    f"   Dispatched to {len(regions_list)} regions: "
                    f"{', '.join(regions_list)}"
                )

            # StoryArc timeline indexing
            try:
                event_time = inherited_event_time or timestamp
                story_event = await coord.story_arc.add_event_from_memory(
                    memory_id=memory_id,
                    content=content,
                    event_time=event_time,
                    metadata={
                        'speaker': speaker,
                        'importance': importance
                    }
                )
                if story_event:
                    result['story_arc_event_id'] = story_event.event_id
                    _logger.debug(
                        f"   StoryArc event: {story_event.event_id} "
                        f"({story_event.event_type})"
                    )
            except Exception as e:
                _logger.warning(f"   StoryArc event extraction failed: {e}")

            # Async Summary Generation
            if async_summary:
                doc_id = result.get(
                    'memory_id', f"mem_{uuid.uuid4().hex[:8]}"
                )

                pseudo_events = [{
                    'type': 'memory_content',
                    'description': (
                        content[:500] + "..."
                        if len(content) > 500 else content
                    ),
                    'importance': importance
                }]

                _logger.info(
                    f"   Launching async summary for memory {doc_id}..."
                )
                asyncio.create_task(
                    self._async_post_process_summary(
                        document_id=doc_id,
                        events=pseudo_events,
                        timestamp=timestamp
                    )
                )
                result['async_summary_triggered'] = True

            return result

    async def _dispatch_to_other_brain_regions(
        self,
        content: str,
        memory_id: str,
        importance: float,
        timestamp: datetime
    ) -> Dict[str, List[str]]:
        """
        Dispatch content to other brain regions (Amygdala/Prefrontal/BasalGanglia)

        Args:
            content: Memory content
            memory_id: Hippocampus-generated memory ID
            importance: Importance score
            timestamp: Timestamp

        Returns:
            {'amygdala': [...], 'prefrontal': [...], 'basal_ganglia': [...]}
        """
        coord = self._coordinator
        dispatched_regions = {
            'amygdala': [],
            'prefrontal': [],
            'basal_ganglia': []
        }

        # 1. Amygdala: Tag emotional content
        from ..utils.emotion_utils import detect_emotions
        _detected, _intensity = detect_emotions(content)
        has_emotion = len(_detected) > 0
        if has_emotion and importance >= 0.6:
            try:
                await coord.amygdala.tag_emotion(
                    reference_id=memory_id,
                    content_summary=content[:100],
                    emotion_tags=[
                        kw for kw in emotion_keywords
                        if kw in content.lower()
                    ],
                    emotion_intensity=importance,
                    metadata={'timestamp': timestamp.isoformat()}
                )
                dispatched_regions['amygdala'].append(memory_id)
                logger.debug(
                    f"   Amygdala tagged emotional memory {memory_id}"
                )
            except Exception as e:
                logger.warning(f"   Amygdala tagging failed: {e}")

        # 2. Prefrontal: Store reasoning traces
        reasoning_keywords = [
            'because', 'therefore', 'if', 'then', 'conclude', 'reason', 'think'
        ]
        has_reasoning = any(
            keyword in content.lower() for keyword in reasoning_keywords
        )
        if has_reasoning:
            try:
                await coord.prefrontal_storage.store_item(
                    content=content,
                    task_type='reasoning',
                    priority=int(importance * 10),
                    metadata={
                        'memory_id': memory_id,
                        'timestamp': timestamp.isoformat()
                    }
                )
                dispatched_regions['prefrontal'].append(memory_id)
                logger.debug(
                    f"   Prefrontal stored reasoning trace {memory_id}"
                )
            except Exception as e:
                logger.warning(f"   Prefrontal storage failed: {e}")

        # 3. BasalGanglia: Store procedural patterns
        action_keywords = [
            'do', 'make', 'create', 'build', 'write', 'run',
            'execute', 'perform'
        ]
        has_action = any(
            keyword in content.lower() for keyword in action_keywords
        )
        if has_action:
            try:
                skill_name = f"skill_{memory_id[:8]}"
                await coord.basal_ganglia.store_skill(
                    skill_name=skill_name,
                    content=content,
                    metadata={
                        'memory_id': memory_id,
                        'timestamp': timestamp.isoformat(),
                        'importance': importance
                    }
                )
                dispatched_regions['basal_ganglia'].append(memory_id)
                logger.debug(
                    f"   BasalGanglia stored procedural pattern {memory_id}"
                )
            except Exception as e:
                logger.warning(f"   BasalGanglia storage failed: {e}")

        return dispatched_regions

    async def _extract_and_store_preferences(
        self,
        content: str,
        user_id: str,
        timestamp: datetime
    ) -> int:
        """
        Extract and store preferences to PersonaMemory using LLM extractor

        Args:
            content: User message content
            user_id: User ID
            timestamp: Timestamp

        Returns:
            Number of preferences stored
        """
        coord = self._coordinator

        if not content or len(content) < 10:
            return 0

        if not hasattr(coord, '_preference_extractor'):
            try:
                from ..optimization.metacognition import get_preference_extractor
                coord._preference_extractor = get_preference_extractor()
            except Exception as e:
                logger.debug(f"Preference extractor not available: {e}")
                coord._preference_extractor = None

        if not coord._preference_extractor:
            return 0

        try:
            extracted = coord._preference_extractor.extract_from_text(content)
            total_stored = 0

            for pref_type, prefs in extracted.items():
                for pref in prefs:
                    if pref and len(pref) > 3:
                        await coord.persona_memory.store_persona({
                            'content': f"User {pref_type}: {pref}",
                            'category': pref_type,
                            'importance': 0.7,
                            'user_id': user_id,
                            'metadata': {
                                'source': 'preference_extraction_shaping',
                                'preference_type': pref_type,
                                'original_statement': content[:200],
                                'timestamp': str(timestamp),
                                'user_id': user_id
                            }
                        })
                        total_stored += 1

            if total_stored > 0:
                logger.debug(
                    f"   Extracted {total_stored} preferences from shaping"
                )

            return total_stored

        except Exception as e:
            logger.debug(f"Preference extraction failed: {e}")
            return 0

    async def store_memory_if_needed(
        self,
        user_input: str,
        response: str,
        context: Dict[str, Any] = None
    ) -> bool:
        """
        Store memory based on input type and context

        Args:
            user_input: User input text
            response: Assistant response
            context: Context dict (supports 'skip_memory_store' to disable storage)

        Returns:
            True if memory was stored
        """
        coord = self._coordinator

        if context is None:
            context = {}

        if context.get('skip_memory_store', False):
            logger.debug("Memory storage skipped (skip_memory_store=True)")
            return False

        try:
            await coord.hippocampus.store_memory(
                content=f"User: {user_input}\nAssistant: {response}",
                metadata={
                    'type': 'conversation',
                    'importance': context.get('importance', 0.5),
                    'timestamp': datetime.now().isoformat()
                }
            )

            return True

        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            return False

    async def trigger_consolidation(
        self,
        strategy: str = 'batch',
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """
        Manually trigger memory consolidation

        Args:
            strategy: Consolidation strategy ('batch', 'system', 'sleep')
            batch_size: Number of memories to process in batch mode

        Returns:
            Dict with consolidation results
        """
        coord = self._coordinator

        action_map = {
            'batch': 'batch_consolidation',
            'system': 'system_consolidation',
            'sleep': 'sleep_consolidation'
        }

        action = action_map.get(strategy, 'batch_consolidation')

        content = {'action': action}
        if strategy == 'batch':
            content['batch_size'] = batch_size

        result = await coord.agent_lifecycle.activate_agent(
            'consolidation',
            AgentMessage(
                sender='coordinator',
                receiver='consolidation',
                message_type='request',
                content=content
            )
        )

        return result

    async def consolidate_memories(
        self, evaluation_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Consolidate memories from Hippocampus to Temporal Lobe

        Args:
            evaluation_mode: Bypass time/access count limits

        Returns:
            Consolidation result dict
        """
        coord = self._coordinator

        try:
            candidates = await coord.hippocampus.get_consolidation_candidates(
                evaluation_mode=evaluation_mode
            )

            if not candidates:
                return {'consolidated': 0, 'message': 'No candidates'}

            consolidated_count = 0
            for memory in candidates:
                try:
                    await coord.temporal_lobe.store_consolidated_memory(memory)
                    consolidated_count += 1
                except Exception as e:
                    logger.warning(f"Failed to consolidate memory: {e}")

            return {
                'consolidated': consolidated_count,
                'candidates': len(candidates),
                'success': True
            }

        except Exception as e:
            logger.error(f"Consolidation failed: {e}")
            return {'consolidated': 0, 'error': str(e), 'success': False}

    async def trigger_forgetting(self, region: str) -> Dict[str, Any]:
        """
        Trigger forgetting process for specified brain region

        Args:
            region: Brain region name ('hippocampus', 'temporal_lobe', etc.)

        Returns:
            Forgetting result dict
        """
        coord = self._coordinator

        try:
            if region == 'hippocampus':
                candidates = await coord.hippocampus.get_forgetting_candidates(
                    bottom_percentile=0.2
                )
                brain_region_agent = coord.hippocampus
            elif region == 'temporal_lobe':
                return {
                    'forgotten': 0,
                    'message': 'TemporalLobe uses internal forgetting logic'
                }
            else:
                logger.warning(f"Unknown brain region: {region}")
                return {
                    'forgotten': 0,
                    'error': f'Unknown region: {region}'
                }

            if not candidates:
                return {
                    'forgotten': 0,
                    'message': 'No candidates for forgetting'
                }

            _fcfg = get_config().forgetting
            to_forget = []
            forgetting_threshold = _fcfg.min_importance_to_keep

            for candidate in candidates:
                importance = candidate.get('importance', 0.5)
                access_count = candidate.get('access_count', 0)

                retention_score = (
                    importance * 0.7
                    + min(access_count / 10, _fcfg.min_importance_to_keep)
                )

                if retention_score < forgetting_threshold:
                    to_forget.append(candidate)

            if not to_forget:
                return {
                    'forgotten': 0,
                    'candidates': len(candidates),
                    'message': 'All memories above retention threshold'
                }

            forgotten_ids = [mem['id'] for mem in to_forget]

            if region == 'hippocampus':
                forgotten_count = await brain_region_agent.forget_memories(
                    forgotten_ids
                )
            else:
                forgotten_count = 0

            return {
                'forgotten': forgotten_count,
                'candidates': len(candidates),
                'region': region,
                'threshold': forgetting_threshold,
                'message': f'Successfully forgot {forgotten_count} memories'
            }

        except Exception as e:
            logger.error(f"Forgetting error for {region}: {e}")
            return {
                'forgotten': 0,
                'error': str(e)
            }

    async def _async_post_process_summary(
        self,
        document_id: str,
        events: List[Dict],
        timestamp: datetime
    ) -> None:
        """
        Async post-processing: generate and store document summary

        This runs in background, not blocking the main flow.

        Args:
            document_id: Document identifier
            events: Extracted events list
            timestamp: Document timestamp
        """
        coord = self._coordinator

        try:
            logger.info(
                f"   [Async] Generating summary for document: {document_id}"
            )

            from ..services.shared_openai_client import shared_client_manager
            client = await shared_client_manager.get_chat_client()

            summary_model = select_model_for_task('summary')

            summary_prompt = (
                f"Create a high-level semantic summary (2-3 sentences) "
                f"for the following document:\n\n"
                f"Document ID: {document_id}\n"
                f"Key events: {len(events)}\n\n"
                f"Briefly summarize the core themes and key information "
                f"of the document."
            )

            summary_response = await client.chat.completions.create(
                model=summary_model,
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=get_config().token.extraction_temperature,
                max_tokens=200
            )

            summary = summary_response.choices[0].message.content.strip()

            await coord.temporal_lobe.store_memory(
                content=f"[Document Summary: {document_id}] {summary}",
                metadata={
                    'type': 'document_summary',
                    'document_id': document_id,
                    'timestamp': timestamp.isoformat(),
                }
            )

            logger.info(
                f"   [Async] Summary stored to Temporal Lobe for {document_id}"
            )

        except Exception as e:
            logger.warning(
                f"   [Async] Summary generation failed for {document_id}: {e}"
            )
