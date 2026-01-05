"""
Memory Coordinator Module
Handles memory storage, retrieval, consolidation, and forgetting operations
"""

import asyncio
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from .clean_agent_system import AgentMessage
from ..memory.memory_system import memory_system
from ..utils.config import get_logger, get_settings
from ..monitoring.memory_metrics import get_metrics_collector
from ..utils.model_selector import select_model_for_task  # 🔥 P1-5: Smart model selection
from .confidence_calibrator import get_confidence_calibrator, ConfidenceCalibrator  # 🔥 Phase 3: 置信度校准
from .brain_retrieval_integration import get_brain_retrieval, BrainInspiredRetrieval  # 🔥 Phase 4: 脑仿生检索整合
from ..memory.story_arc import get_story_arc_manager, StoryArcManager  # 🔥 2025-12-20: 时间线索引

logger = get_logger(__name__)


class MemoryCoordinator:
    """Coordinates memory operations across brain regions"""

    def __init__(self, hippocampus, temporal_lobe, consolidation_agent,
                 forgetting_agent, agent_lifecycle_manager, memory_system=None,
                 amygdala=None, prefrontal_storage=None, basal_ganglia=None):
        """
        Initialize Memory Coordinator

        Args:
            hippocampus: Hippocampus agent instance
            temporal_lobe: Temporal lobe agent instance
            consolidation_agent: Consolidation agent instance
            forgetting_agent: Forgetting agent instance
            agent_lifecycle_manager: Agent lifecycle manager for activation
            memory_system: MemorySystem instance for persistent storage (optional)
            amygdala: Amygdala agent for emotional tagging (optional)
            prefrontal_storage: Prefrontal agent for reasoning traces (optional)
            basal_ganglia: Basal ganglia agent for procedural memory (optional)
        """
        self.hippocampus = hippocampus
        self.temporal_lobe = temporal_lobe
        self.consolidation_agent = consolidation_agent
        self.forgetting_agent = forgetting_agent
        self.agent_lifecycle = agent_lifecycle_manager
        self.memory_system = memory_system  # 🔥 NEW: Store memory_system reference

        # 🔥 Phase 1: Additional brain regions for collaborative storage
        self.amygdala = amygdala
        self.prefrontal_storage = prefrontal_storage
        self.basal_ganglia = basal_ganglia

        # 🔥 Phase 3: 跨脑区置信度校准器
        self.confidence_calibrator = get_confidence_calibrator()

        # 🔥 Phase 4: 脑仿生检索系统 (快慢路径 + 迭代检索 + 缺口检测)
        self.brain_retrieval = get_brain_retrieval(
            memory_coordinator=self,
            enable_fast_path=True,
            enable_iterative=True,
            max_iterations=3
        )
        logger.info("MemoryCoordinator: BrainInspiredRetrieval initialized")

        # 🔥 2025-12-20: 时间线索引 (StoryArc) - 提升时间推理精度
        self.story_arc = get_story_arc_manager()
        logger.info(f"MemoryCoordinator: StoryArcManager initialized ({self.story_arc.get_statistics()['total_events']} events)")


    async def store_long_document(
        self,
        content: str,
        timestamp: datetime,
        document_id: str = None,
        speaker: str = None,
        importance: float = 0.5,
        extract_events: bool = True,
        store_to_external: bool = True,
        async_summary: bool = False  # 🔥 P1-5: False for backward compatibility
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
            async_summary: 🔥 P1-5: Generate summary asynchronously (default: False)
                          - False: Summary generated synchronously, immediately available in result
                          - True: Summary generated in background, result['summary'] = '[Generating in background]'

        Returns:
            {
                'document_id': str,
                'external_stored': bool,
                'events_extracted': int,
                'memories_created': int,
                'summary': str  # High-level summary (or '[Generating in background]' if async_summary=True)
            }
        """
        import uuid
        import logging
        logger = logging.getLogger(__name__)
        settings = get_settings()

        if document_id is None:
            document_id = f"doc_{uuid.uuid4().hex[:12]}"

        result = {
            'document_id': document_id,
            'external_stored': False,
            'events_extracted': 0,
            'memories_created': 0,
            'summary': None
        }

        estimated_tokens = len(content) // 4
        logger.info(f"📄 Processing document: {estimated_tokens} tokens, id={document_id}")

        # 🔥 Phase 1: Adaptive Storage Strategy based on content length
        # Short text (<1000 tokens): Store ORIGINAL TEXT in brain regions
        # Medium text (1000-5000 tokens): Store key paragraphs + summary
        # Long text (>5000 tokens): Store event abstractions + summary

        if estimated_tokens < 1000:
            # 🔥 SHORT TEXT: Store original to Hippocampus (like memorizing poems/conversations)
            logger.info(f"   📝 Short content ({estimated_tokens} tokens) → storing ORIGINAL TEXT to Hippocampus")

            await self.hippocampus.store_memory_with_event_segmentation(
                content=content,  # ✅ Store ORIGINAL TEXT, not abstraction
                timestamp=timestamp,
                speaker=speaker,
                importance=importance
            )

            result['memories_created'] = 1
            result['storage_strategy'] = 'original_to_hippocampus'
            logger.info(f"✅ Short document stored as original text (no abstraction needed)")

            return result

        # For medium/long documents, continue with external storage + abstraction
        # Step 1: Store original to external storage (if memory_system available)
        if store_to_external and hasattr(self, 'memory_system') and self.memory_system:
            try:
                # Store full document to external with metadata
                external_metadata = {
                    'document_id': document_id,
                    'timestamp': timestamp.isoformat(),
                    'speaker': speaker,
                    'importance': importance,
                    'token_count': estimated_tokens,
                    'type': 'long_document_original'
                }

                # Memory system stores original
                await self.memory_system.store_memory(
                    content=content,
                    metadata=external_metadata
                )
                result['external_stored'] = True
                logger.info(f"   ✅ Original document stored to external storage")
            except Exception as e:
                logger.warning(f"   ⚠️  Failed to store to external: {e}")

        # Step 2: Extract event representations or key paragraphs
        # 🔥 Phase 1: Different extraction strategy for medium vs long documents
        events = []
        if extract_events:
            from src.services.shared_openai_client import shared_client_manager
            client = await shared_client_manager.get_chat_client()

            if estimated_tokens < 5000:
                # 🔥 MEDIUM TEXT (1000-5000 tokens): Extract key paragraphs with ORIGINAL TEXT
                logger.info(f"   📝 Medium content ({estimated_tokens} tokens) → extracting key paragraphs with original text...")

                try:
                    extraction_prompt = f"""Extract 3-5 most important paragraphs or fragments from the following document.

Document content:
{content}

Please extract:
1. Key dialogue fragments (preserve original text)
2. Important factual paragraphs (preserve original text)
3. Core viewpoint paragraphs (preserve original text)

Output in JSON format, each fragment containing ORIGINAL TEXT:
{{"paragraphs": [
  {{"type": "dialogue", "original_text": "full original text...", "importance": 0.8}},
  {{"type": "fact", "original_text": "full original text...", "importance": 0.7}}
]}}"""

                    # 🔥 P1-5: Use smart model selection for extraction
                    extraction_model = select_model_for_task('extraction')

                    response = await client.chat.completions.create(
                        model=extraction_model,
                        messages=[{"role": "user", "content": extraction_prompt}],
                        temperature=0.3,
                        max_tokens=2000
                    )

                    import json
                    import re
                    response_text = response.choices[0].message.content
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        extracted = json.loads(json_match.group())
                        paragraphs = extracted.get('paragraphs', [])
                        # Convert to events format with original_text
                        events = [
                            {
                                'type': p.get('type', 'paragraph'),
                                'original_text': p.get('original_text', ''),
                                'importance': p.get('importance', importance)
                            }
                            for p in paragraphs
                        ]
                        logger.info(f"      ✅ Extracted {len(events)} key paragraphs with original text")

                except Exception as e:
                    logger.warning(f"   ⚠️  Paragraph extraction failed: {e}")

            else:
                # 🔥 LONG TEXT (>5000 tokens): Extract event abstractions (original behavior)
                logger.info(f"   🧠 Long content ({estimated_tokens} tokens) → extracting event abstractions...")

                try:
                    # Prompt for event extraction
                    # Limit content to 4000 chars to avoid token overflow
                    truncated_content = content[:4000]
                    extraction_prompt = f"""Extract key events and important information from the following long document.

Document content:
{truncated_content}

Please extract:
1. Key events (time, place, people, actions)
2. Important facts and data
3. Core viewpoints and conclusions

Output in JSON format, one object per event/information:
{{"events": [
  {{"type": "event", "description": "...", "importance": 0.8}},
  {{"type": "fact", "description": "...", "importance": 0.6}}
]}}"""

                    # 🔥 P1-5: Use smart model selection for extraction
                    extraction_model = select_model_for_task('extraction')

                    response = await client.chat.completions.create(
                        model=extraction_model,
                        messages=[{"role": "user", "content": extraction_prompt}],
                        temperature=0.3,
                        max_tokens=1000
                    )

                    # Parse extracted events
                    import json
                    import re
                    response_text = response.choices[0].message.content
                    # Extract JSON
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        extracted = json.loads(json_match.group())
                        events = extracted.get('events', [])
                        logger.info(f"      ✅ Extracted {len(events)} events/facts")

                except Exception as e:
                    logger.warning(f"   ⚠️  Event extraction failed: {e}")

        # Step 3: Store to Hippocampus + P1 Fix: Dispatch to other brain regions
        # 🔥 Phase 1: Medium text stores ORIGINAL TEXT, long text stores abstractions
        memories_created = 0
        dispatched_summary = {'amygdala': 0, 'prefrontal': 0, 'basal_ganglia': 0}

        for event in events:
            try:
                event_importance = event.get('importance', importance)

                # 🔥 Check if this is original_text (medium) or description (long)
                if 'original_text' in event:
                    # Medium text: Store ORIGINAL TEXT
                    content_to_store = event['original_text']
                    storage_type = "original paragraph"
                else:
                    # Long text: Store event abstraction
                    content_to_store = f"[Document: {document_id}] {event.get('description', '')}"
                    storage_type = "event abstraction"

                logger.debug(f"   Storing {storage_type}: {content_to_store[:50]}...")

                # Store to Hippocampus
                hippocampus_result = await self.hippocampus.store_memory_with_event_segmentation(
                    content=content_to_store,
                    timestamp=timestamp,
                    speaker=speaker,
                    importance=event_importance
                )
                memories_created += 1

                # P1 Fix: Dispatch to other brain regions (Amygdala/Prefrontal/BasalGanglia)
                memory_id = hippocampus_result.get('memory_id')
                dispatched = await self._dispatch_to_other_brain_regions(
                    content=content_to_store,
                    memory_id=memory_id,
                    importance=event_importance,
                    timestamp=timestamp
                )

                # Accumulate dispatch statistics
                for region, ids in dispatched.items():
                    dispatched_summary[region] += len(ids)

            except Exception as e:
                logger.warning(f"   Failed to store memory: {e}")

        result['events_extracted'] = len(events)
        result['memories_created'] = memories_created
        result['dispatched_to_regions'] = dispatched_summary  # P1: Track multi-region dispatch

        logger.info(f"   📊 Multi-region dispatch: Amygdala={dispatched_summary['amygdala']}, "
                   f"Prefrontal={dispatched_summary['prefrontal']}, "
                   f"BasalGanglia={dispatched_summary['basal_ganglia']}")

        # Step 4: Summary generation (sync or async based on parameter)
        if async_summary:
            # 🔥 P1-5: Async post-processing (non-blocking)
            logger.info(f"   🚀 Launching async post-processing (summary generation)...")
            asyncio.create_task(
                self._async_post_process_summary(
                    document_id=document_id,
                    events=events,
                    timestamp=timestamp
                )
            )
            result['summary'] = '[Generating in background]'  # Placeholder
        else:
            # Synchronous summary generation (backward compatible)
            try:
                logger.info(f"   📝 Creating semantic summary (sync)...")

                summary_model = select_model_for_task('summary')

                summary_prompt = f"""Create a high-level semantic summary (2-3 sentences) for the following document:

Document ID: {document_id}
Key events: {len(events)}

Briefly summarize the core themes and key information of the document."""

                summary_response = await client.chat.completions.create(
                    model=summary_model,
                    messages=[{"role": "user", "content": summary_prompt}],
                    temperature=0.3,
                    max_tokens=200
                )

                summary = summary_response.choices[0].message.content.strip()
                result['summary'] = summary

                # Store summary to Temporal Lobe
                await self.temporal_lobe.store_memory(
                    content=f"[Document Summary: {document_id}] {summary}",
                    metadata={
                        'type': 'document_summary',
                        'document_id': document_id,
                        'timestamp': timestamp.isoformat(),
                    }
                )

                logger.info(f"      ✅ Summary stored to Temporal Lobe")

            except Exception as e:
                logger.warning(f"   Summary creation failed: {e}")

        logger.info(f"✅ Long document processed: external={result['external_stored']}, "
                   f"events={result['events_extracted']}, memories={result['memories_created']}")

        return result

    async def store_memory_with_timestamp(
        self,
        content: str,
        timestamp: datetime,
        speaker: str = None,
        importance: float = 0.5,
        auto_chunk: bool = True,
        chunk_threshold: int = 1000,  # tokens
        chunk_overlap: int = 150,  # overlap tokens between chunks
        async_summary: bool = False,  # 🔥 P1-5: Async summary generation
        inherited_event_time: datetime = None,  # 🔥 2025-12-16: 继承的事件时间
        user_id: str = "default"  # 🔥 2025-12-25: 用户ID隔离
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
            inherited_event_time: 🔥 继承的事件时间 (用于 [Event] 记忆继承原始对话的精确时间)

        Returns:
            {
                'memory_id': str,  # Last chunk's ID if auto-chunked
                'event_id': str,
                'is_new_event': bool,
                'chunks_created': int,  # Number of chunks (1 if not chunked)
                'chunk_group_id': str  # ID linking related chunks (if chunked)
            }
        """
        import logging
        import uuid
        logger = logging.getLogger(__name__)

        # Estimate token count (rough: 1 token ≈ 4 chars for English)
        estimated_tokens = len(content) // 4

        if auto_chunk and estimated_tokens > chunk_threshold:
            # Content too long, auto-chunk with overlap
            logger.warning(
                f"⚠️  Memory content is very long ({estimated_tokens} tokens). "
                f"Auto-chunking with {chunk_overlap}-token overlap for better retrieval."
            )

            # Generate unique chunk group ID to link related chunks
            chunk_group_id = f"chunk_group_{uuid.uuid4().hex[:8]}"

            # Improved semantic-aware chunking
            # 1. Detect conversation turns (Speaker: pattern)
            # 2. Group into semantic units
            # 3. Add overlap between chunks

            lines = content.split('\n')
            semantic_units = []
            current_unit = []
            current_tokens = 0

            for line in lines:
                line_tokens = len(line) // 4
                # Detect conversation turn boundary (e.g., "User:", "Assistant:")
                is_turn_boundary = any(pattern in line for pattern in [':', '：']) and len(line) < 100

                if is_turn_boundary and current_unit and current_tokens > 200:
                    # Save current unit if it's substantial
                    semantic_units.append('\n'.join(current_unit))
                    current_unit = [line]
                    current_tokens = line_tokens
                else:
                    current_unit.append(line)
                    current_tokens += line_tokens

            # Add last unit
            if current_unit:
                semantic_units.append('\n'.join(current_unit))

            # Build chunks with overlap
            chunks = []
            i = 0
            while i < len(semantic_units):
                chunk_content = []
                chunk_tokens = 0

                # Add semantic units until threshold
                while i < len(semantic_units) and chunk_tokens < chunk_threshold:
                    unit = semantic_units[i]
                    unit_tokens = len(unit) // 4

                    if chunk_tokens + unit_tokens > chunk_threshold * 1.2 and chunk_content:
                        # Don't exceed threshold by too much
                        break

                    chunk_content.append(unit)
                    chunk_tokens += unit_tokens
                    i += 1

                if chunk_content:
                    chunks.append('\n'.join(chunk_content))

                # Backtrack for overlap (add last ~150 tokens to next chunk)
                if i < len(semantic_units) and len(chunk_content) > 1:
                    overlap_units = chunk_content[-1:]  # Last unit as overlap
                    i -= 1  # Include in next chunk

            # Fallback: if semantic chunking failed, use simple splitting
            if not chunks or len(chunks) == 1 and estimated_tokens > chunk_threshold * 2:
                logger.info("   Falling back to simple token-based chunking")
                chunks = []
                words = content.split()
                current_chunk = []
                current_length = 0

                for word in words:
                    word_tokens = len(word) // 4 + 1
                    if current_length + word_tokens > chunk_threshold and current_chunk:
                        chunks.append(' '.join(current_chunk))
                        # Add overlap: keep last chunk_overlap tokens
                        overlap_words = current_chunk[-chunk_overlap*4//5:]  # approx tokens
                        current_chunk = overlap_words + [word]
                        current_length = sum(len(w)//4+1 for w in current_chunk)
                    else:
                        current_chunk.append(word)
                        current_length += word_tokens

                if current_chunk:
                    chunks.append(' '.join(current_chunk))

            logger.info(f"📦 Auto-chunked into {len(chunks)} chunks (overlap={chunk_overlap} tokens)")

            # Store each chunk with metadata linking them
            # 🔥 修复: 添加时间上下文前缀
            date_str = timestamp.strftime("%d %B %Y")  # e.g., "08 May 2023"

            results = []
            for i, chunk in enumerate(chunks):
                # Add chunk metadata and time context to content
                chunk_header = f"[Context: This conversation is on {date_str}] [Chunk {i+1}/{len(chunks)} | Group: {chunk_group_id}]\n"
                chunk_with_metadata = chunk_header + chunk

                result = await self.hippocampus.store_memory_with_event_segmentation(
                    content=chunk_with_metadata,
                    timestamp=timestamp,
                    speaker=speaker,
                    importance=importance,
                    inherited_event_time=inherited_event_time,  # 🔥 2025-12-16: 传递继承的事件时间
                    user_id=user_id  # 🔥 2025-12-25: 传递用户ID
                )
                results.append(result)

            logger.info(f"   ✅ Stored {len(chunks)} chunks with group ID: {chunk_group_id}")

            # Return last chunk's result with chunk metadata
            final_result = results[-1]
            final_result['chunks_created'] = len(chunks)
            final_result['chunk_group_id'] = chunk_group_id
            return final_result

        else:
            # Normal storage for short content
            # 🔥 修复: 添加时间上下文前缀，供时间推理使用
            # 时间推理模块需要 "[Context: This conversation is on DATE]" 格式
            date_str = timestamp.strftime("%d %B %Y")  # e.g., "08 May 2023"
            content_with_context = f"[Context: This conversation is on {date_str}] {content}"

            result = await self.hippocampus.store_memory_with_event_segmentation(
                content=content_with_context,
                timestamp=timestamp,
                speaker=speaker,
                importance=importance,
                inherited_event_time=inherited_event_time,  # 🔥 2025-12-16: 传递继承的事件时间
                user_id=user_id  # 🔥 2025-12-25: 传递用户ID
            )
            result['chunks_created'] = 1

            # 🔥 2025-12-27 FIX: 偏好提取并存储到PersonaMemory
            # 解决PersonaMem测试0条记忆问题 - 在系统层而非测试层修复
            if speaker == 'user' and hasattr(self, 'persona_memory') and self.persona_memory:
                await self._extract_and_store_preferences(
                    content=content,
                    user_id=user_id,
                    timestamp=timestamp
                )

            # 🔥 Phase 1: 5-Brain Region Collaborative Storage
            # After storing to Hippocampus, dispatch to other brain regions based on content features
            memory_id = result.get('memory_id')
            dispatched = await self._dispatch_to_other_brain_regions(
                content=content,
                memory_id=memory_id,
                importance=importance,
                timestamp=timestamp
            )
            result['dispatched_regions'] = dispatched

            # Log dispatch summary
            dispatch_count = sum(len(ids) for ids in dispatched.values())
            if dispatch_count > 0:
                regions_list = [region for region, ids in dispatched.items() if ids]
                logger.info(f"   📊 Dispatched to {len(regions_list)} regions: {', '.join(regions_list)}")

            # 🔥 2025-12-20: 提取事件到 StoryArc 时间线索引
            try:
                # 使用 inherited_event_time (精确事件时间) 或 timestamp (对话时间)
                event_time = inherited_event_time or timestamp
                story_event = await self.story_arc.add_event_from_memory(
                    memory_id=memory_id,
                    content=content,
                    event_time=event_time,
                    metadata={'speaker': speaker, 'importance': importance}
                )
                if story_event:
                    result['story_arc_event_id'] = story_event.event_id
                    logger.debug(f"   📅 StoryArc event: {story_event.event_id} ({story_event.event_type})")
            except Exception as e:
                logger.warning(f"   ⚠️ StoryArc event extraction failed: {e}")

            # 🔥 P1-5: Async Summary Generation
            if async_summary:
                # Generate a document ID if not present (using the memory ID)
                doc_id = result.get('memory_id', f"mem_{uuid.uuid4().hex[:8]}")
                
                # Create a pseudo-event list for the summary generator
                # (Since we don't have extracted events here, we use the content itself)
                pseudo_events = [{
                    'type': 'memory_content',
                    'description': content[:500] + "..." if len(content) > 500 else content,
                    'importance': importance
                }]
                
                logger.info(f"   🚀 Launching async summary for memory {doc_id}...")
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
        P1 Fix: 将内容分发到其他脑区（Amygdala/Prefrontal/BasalGanglia）

        这是短文本存储中的5脑区协作存储逻辑，现在被提取为独立方法
        以便长文档存储也能复用。

        Args:
            content: 记忆内容
            memory_id: 海马体生成的记忆ID
            importance: 重要性分数
            timestamp: 时间戳

        Returns:
            {
                'amygdala': [...],  # 分发到的脑区列表
                'prefrontal': [...],
                'basal_ganglia': [...]
            }
        """
        dispatched_regions = {
            'amygdala': [],
            'prefrontal': [],
            'basal_ganglia': []
        }

        # 1. Amygdala: Tag emotional content
        emotion_keywords = ['happy', 'sad', 'angry', 'fear', 'love', 'hate', 'excited', 'worried', 'surprised']
        has_emotion = any(keyword in content.lower() for keyword in emotion_keywords)
        if has_emotion and importance >= 0.6:
            try:
                await self.amygdala.tag_emotion(
                    reference_id=memory_id,
                    content_summary=content[:100],  # Brief summary
                    emotion_tags=[kw for kw in emotion_keywords if kw in content.lower()],
                    emotion_intensity=importance,  # Use importance as proxy for emotion intensity
                    metadata={'timestamp': timestamp.isoformat()}
                )
                dispatched_regions['amygdala'].append(memory_id)
                logger.debug(f"   ✅ Amygdala tagged emotional memory {memory_id}")
            except Exception as e:
                logger.warning(f"   ⚠️  Amygdala tagging failed: {e}")

        # 2. Prefrontal: Store reasoning traces (if contains reasoning keywords)
        reasoning_keywords = ['because', 'therefore', 'if', 'then', 'conclude', 'reason', 'think']
        has_reasoning = any(keyword in content.lower() for keyword in reasoning_keywords)
        if has_reasoning:
            try:
                await self.prefrontal_storage.store_item(
                    content=content,
                    task_type='reasoning',
                    priority=int(importance * 10),  # Convert to 0-10 scale
                    metadata={'memory_id': memory_id, 'timestamp': timestamp.isoformat()}
                )
                dispatched_regions['prefrontal'].append(memory_id)
                logger.debug(f"   ✅ Prefrontal stored reasoning trace {memory_id}")
            except Exception as e:
                logger.warning(f"   ⚠️  Prefrontal storage failed: {e}")

        # 3. BasalGanglia: Store procedural patterns (if contains action verbs)
        action_keywords = ['do', 'make', 'create', 'build', 'write', 'run', 'execute', 'perform']
        has_action = any(keyword in content.lower() for keyword in action_keywords)
        if has_action:
            try:
                # Extract potential skill name (simple heuristic)
                skill_name = f"skill_{memory_id[:8]}"
                await self.basal_ganglia.store_skill(
                    skill_name=skill_name,
                    content=content,
                    metadata={'memory_id': memory_id, 'timestamp': timestamp.isoformat(), 'importance': importance}
                )
                dispatched_regions['basal_ganglia'].append(memory_id)
                logger.debug(f"   ✅ BasalGanglia stored procedural pattern {memory_id}")
            except Exception as e:
                logger.warning(f"   ⚠️  BasalGanglia storage failed: {e}")

        return dispatched_regions

    async def _extract_and_store_preferences(
        self,
        content: str,
        user_id: str,
        timestamp: datetime
    ) -> int:
        """
        🔥 2025-12-27 FIX: 使用LLM偏好提取器提取并存储偏好到PersonaMemory

        Args:
            content: 用户消息内容
            user_id: 用户ID
            timestamp: 时间戳

        Returns:
            存储的偏好数量
        """
        if not content or len(content) < 10:
            return 0

        # 懒加载偏好提取器
        if not hasattr(self, '_preference_extractor'):
            try:
                from ..optimization.metacognition import get_preference_extractor
                self._preference_extractor = get_preference_extractor()
            except Exception as e:
                logger.debug(f"Preference extractor not available: {e}")
                self._preference_extractor = None

        if not self._preference_extractor:
            return 0

        try:
            # 使用LLM提取偏好
            extracted = self._preference_extractor.extract_from_text(content)
            total_stored = 0

            for pref_type, prefs in extracted.items():
                for pref in prefs:
                    if pref and len(pref) > 3:  # 过滤太短的
                        await self.persona_memory.store_persona({
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
                logger.debug(f"   🎯 Extracted {total_stored} preferences from shaping")

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
        if context is None:
            context = {}

        # 🔥 FIX: 支持 skip_memory_store 参数，用于 QA 测试等场景
        # 避免 QA 对话污染检索结果
        if context.get('skip_memory_store', False):
            logger.debug("Memory storage skipped (skip_memory_store=True)")
            return False

        try:
            # Check if this is a simple Q&A that shouldn't pollute memory
            # Add your detection logic here

            # Store to hippocampus
            await self.hippocampus.store_memory(
                content=f"User: {user_input}\nAssistant: {response}",
                metadata={
                    'type': 'conversation',
                    'importance': context.get('importance', 0.5),
                    'timestamp': datetime.now().isoformat()
                }
            )

            return True

        except Exception as e:
            logger.error(f"❌ Failed to store memory: {e}")
            return False

    async def trigger_consolidation(
        self,
        strategy: str = 'batch',
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """
        Manually trigger memory consolidation

        Args:
            strategy: Consolidation strategy
                - 'batch': Batch consolidation (extract N memories from Hippocampus)
                - 'system': System-wide consolidation (evaluate all memories)
                - 'sleep': Sleep consolidation (simulate sleep-time consolidation)
            batch_size: Number of memories to process in batch mode

        Returns:
            Dict with consolidation results
        """

        action_map = {
            'batch': 'batch_consolidation',
            'system': 'system_consolidation',
            'sleep': 'sleep_consolidation'
        }

        action = action_map.get(strategy, 'batch_consolidation')

        content = {'action': action}
        if strategy == 'batch':
            content['batch_size'] = batch_size

        result = await self.agent_lifecycle.activate_agent(
            'consolidation',
            AgentMessage(
                sender='coordinator',
                receiver='consolidation',
                message_type='request',
                content=content
            )
        )

        return result

    async def consolidate_memories(self, evaluation_mode: bool = False) -> Dict[str, Any]:
        """
        Consolidate memories from Hippocampus to Temporal Lobe

        Args:
            evaluation_mode: 🔥 评估模式 - 绕过时间/访问次数限制

        Returns:
            Consolidation result dict
        """
        try:

            # Get memories from hippocampus for consolidation
            # 🔥 2025-12-20: 传递 evaluation_mode 参数
            candidates = await self.hippocampus.get_consolidation_candidates(
                evaluation_mode=evaluation_mode
            )

            if not candidates:
                return {'consolidated': 0, 'message': 'No candidates'}

            # Transfer to temporal lobe
            consolidated_count = 0
            for memory in candidates:
                try:
                    await self.temporal_lobe.store_consolidated_memory(memory)
                    consolidated_count += 1
                except Exception as e:
                    logger.warning(f"Failed to consolidate memory: {e}")


            return {
                'consolidated': consolidated_count,
                'candidates': len(candidates),
                'success': True
            }

        except Exception as e:
            logger.error(f"❌ Consolidation failed: {e}")
            return {'consolidated': 0, 'error': str(e), 'success': False}

    async def trigger_forgetting(self, region: str) -> Dict[str, Any]:
        """
        Trigger forgetting process for specified brain region

        Args:
            region: Brain region name ('hippocampus', 'temporal_lobe', etc.)

        Returns:
            Forgetting result dict
        """

        try:
            # Get forgetting candidates from region
            if region == 'hippocampus':
                candidates = await self.hippocampus.get_forgetting_candidates(
                    bottom_percentile=0.2
                )
                brain_region_agent = self.hippocampus
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


            # Evaluate retention value
            to_forget = []
            forgetting_threshold = 0.3

            for candidate in candidates:
                importance = candidate.get('importance', 0.5)
                access_count = candidate.get('access_count', 0)

                # Calculate retention score
                retention_score = importance * 0.7 + min(access_count / 10, 0.3)

                if retention_score < forgetting_threshold:
                    to_forget.append(candidate)

            if not to_forget:
                return {
                    'forgotten': 0,
                    'candidates': len(candidates),
                    'message': 'All memories above retention threshold'
                }


            # Execute forgetting
            forgotten_ids = [mem['id'] for mem in to_forget]

            if region == 'hippocampus':
                forgotten_count = await brain_region_agent.forget_memories(forgotten_ids)
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
            logger.error(f"❌ Forgetting error for {region}: {e}")
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
        🔥 P1-5: 异步后处理 - 文档摘要生成
        Async post-processing: generate and store document summary

        This runs in background, not blocking the main flow.

        Args:
            document_id: Document identifier
            events: Extracted events list
            timestamp: Document timestamp
        """
        try:
            logger.info(f"   📝 [Async] Generating summary for document: {document_id}")

            from ..services.shared_openai_client import shared_client_manager
            client = await shared_client_manager.get_chat_client()
            settings = get_settings()

            # Use smart model selection for summary
            summary_model = select_model_for_task('summary')

            summary_prompt = f"""Create a high-level semantic summary (2-3 sentences) for the following document:

Document ID: {document_id}
Key events: {len(events)}

Briefly summarize the core themes and key information of the document."""

            summary_response = await client.chat.completions.create(
                model=summary_model,
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.3,
                max_tokens=200
            )

            summary = summary_response.choices[0].message.content.strip()

            # Store summary to Temporal Lobe (semantic knowledge)
            await self.temporal_lobe.store_memory(
                content=f"[Document Summary: {document_id}] {summary}",
                metadata={
                    'type': 'document_summary',
                    'document_id': document_id,
                    'timestamp': timestamp.isoformat(),
                }
            )

            logger.info(f"   ✅ [Async] Summary stored to Temporal Lobe for {document_id}")

        except Exception as e:
            logger.warning(f"   ⚠️  [Async] Summary generation failed for {document_id}: {e}")

    def _calculate_kg_coverage(self, memories: List[Dict], query: str) -> float:
        """
        🔥 P1-4: Calculate KG coverage rate using real KG statistics

        KG coverage measures how well the Knowledge Graph covers the query domain.
        Uses actual KG node/relation counts instead of string matching.

        Coverage formula:
        - Entity coverage: (KG中找到的查询实体数) / (查询实体总数)
        - KG richness: (查询相关的KG三元组数) / (查询实体数 * 预期平均关系数)
        - Final coverage: (Entity coverage * 0.6) + (KG richness * 0.4)

        Args:
            memories: Retrieved memory list (unused, kept for compatibility)
            query: Original query string

        Returns:
            Coverage ratio (0.0-1.0)
        """
        # Extract entities from query
        import re
        query_tokens = set(re.findall(r'\b\w+\b', query.lower()))
        stop_words = {'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but', 'in',
                      'with', 'to', 'for', 'of', 'as', 'by', 'what', 'how', 'why', 'when', 'where', 'who'}
        query_entities = query_tokens - stop_words

        if not query_entities:
            return 1.0  # No entities to check

        # Check if KG is available
        if not (self.temporal_lobe and hasattr(self.temporal_lobe, 'kg')):
            logger.warning("   ⚠️  KG not available, coverage set to 0.5 (unknown)")
            return 0.5  # Unknown KG state

        kg = self.temporal_lobe.kg

        try:
            # 1. Get KG statistics
            kg_stats = kg.get_statistics()
            total_kg_entities = kg_stats.get('total_entities', 0)
            total_kg_triples = kg_stats.get('total_triples', 0)

            if total_kg_entities == 0 or total_kg_triples == 0:
                logger.debug("   📊 KG Coverage: 0.00% (KG is empty)")
                return 0.0  # Empty KG

            # 2. Query KG for each entity and count relations
            covered_entities = set()
            query_related_triples = 0

            for entity in query_entities:
                # Check as source entity
                relations = kg.query_relations(entity)
                if relations:
                    covered_entities.add(entity)
                    query_related_triples += len(relations)
                    continue

                # Check as target entity (reverse index)
                if hasattr(kg, 'reverse_index') and entity in kg.reverse_index:
                    covered_entities.add(entity)
                    query_related_triples += len(kg.reverse_index[entity])

            # 3. Calculate entity coverage
            entity_coverage = len(covered_entities) / len(query_entities)

            # 4. Calculate KG richness (how well-connected the query entities are)
            # Average relations per entity in full KG
            avg_relations_per_entity = total_kg_triples / total_kg_entities if total_kg_entities > 0 else 1
            # Expected triples for query entities
            expected_triples = len(query_entities) * avg_relations_per_entity
            # Actual richness
            kg_richness = min(1.0, query_related_triples / expected_triples) if expected_triples > 0 else 0.0

            # 5. Combined coverage (weighted average)
            # Entity coverage weighted more (60%) as it's more reliable
            coverage = (entity_coverage * 0.6) + (kg_richness * 0.4)

            logger.debug(
                f"   📊 KG Coverage: {coverage:.2%} "
                f"(entities: {len(covered_entities)}/{len(query_entities)}, "
                f"triples: {query_related_triples}, "
                f"KG: {total_kg_entities} entities, {total_kg_triples} triples)"
            )

            return coverage

        except Exception as e:
            logger.warning(f"   ⚠️  KG coverage calculation failed: {e}, assuming low coverage")
            return 0.3  # Conservative fallback

    async def _pure_semantic_fallback(
        self,
        query: str,
        k: int,
        activation_plan: Optional[Dict[str, bool]] = None
    ) -> List[Dict[str, Any]]:
        """
        🔥 P1-4: Pure semantic retrieval fallback (bypass KG, use only embeddings)

        When KG coverage is low, fall back to pure vector similarity search.
        This ensures we can still retrieve relevant memories even if KG is incomplete.

        Args:
            query: Search query
            k: Number of results
            activation_plan: Optional region activation plan

        Returns:
            List of memories retrieved via pure semantic search
        """
        logger.info(f"   🔍 Pure semantic fallback: retrieving {k} memories via embeddings only")

        fallback_memories = []

        # Default activation: prioritize Hippocampus and Temporal Lobe for semantic search
        if activation_plan is None:
            activation_plan = {
                'hippocampus': True,
                'temporal_lobe': True,
                'prefrontal': False,  # Skip reasoning traces in fallback
                'amygdala': False,     # Skip emotional memories in fallback
                'basal_ganglia': False # Skip procedural memories in fallback
            }

        # Retrieve from Hippocampus (episodic, embedding-based)
        if activation_plan.get('hippocampus') and self.hippocampus:
            try:
                result = await self.hippocampus.search_memories(query, k=k)
                hippocampus_mems = result.get('memories', []) if isinstance(result, dict) else result
                for mem in hippocampus_mems:
                    mem['source'] = 'hippocampus'
                    mem['_fallback'] = True  # Mark as fallback result
                fallback_memories.extend(hippocampus_mems)
            except Exception as e:
                logger.warning(f"Semantic fallback from Hippocampus failed: {e}")

        # Retrieve from Temporal Lobe (semantic, embedding-based)
        if activation_plan.get('temporal_lobe') and self.temporal_lobe:
            try:
                result = await self.temporal_lobe.search_memories(query, k=k)
                temporal_mems = result.get('memories', []) if isinstance(result, dict) else result
                for mem in temporal_mems:
                    mem['source'] = 'temporal_lobe'
                    mem['_fallback'] = True  # Mark as fallback result
                fallback_memories.extend(temporal_mems)
            except Exception as e:
                logger.warning(f"Semantic fallback from Temporal Lobe failed: {e}")

        logger.info(f"   ✅ Semantic fallback retrieved {len(fallback_memories)} memories")

        return fallback_memories

    async def smart_retrieve(
        self,
        query: str,
        k: int = 10,
        strategy: str = 'auto',
        context: Dict[str, Any] = None,
        activation_plan: Optional[Dict[str, bool]] = None
    ) -> List[Dict[str, Any]]:
        """
        Smart memory retrieval with automatic strategy selection + P0-1 缓存优化

        Args:
            query: Query text
            k: Number of results
            strategy: Retrieval strategy ('auto', 'episodic', 'semantic', 'hybrid')
            context: Optional context dict
            activation_plan: 🔥 HRM Fix: Optional region activation plan from Thalamus

        Returns:
            List of retrieved memories
        """
        if context is None:
            context = {}

        # P0-1: 尝试从检索缓存获取
        from ..utils.semantic_cache import get_retrieval_cache
        retrieval_cache = get_retrieval_cache()

        # Determine active regions for cache key
        active_regions = None
        if activation_plan:
            active_regions = [region for region, active in activation_plan.items() if active]

        cached_results = retrieval_cache.get(
            query=query,
            k=k,
            strategy=strategy,
            regions=active_regions
        )
        if cached_results:
            logger.debug(f"Retrieval cache HIT: query='{query[:50]}...', k={k}")
            return cached_results

        try:
            # Auto-select strategy if needed
            if strategy == 'auto':
                # Use routing manager to decide
                # For now, default to hybrid
                strategy = 'hybrid'


            # Route to appropriate retrieval method
            if strategy == 'episodic':
                result = await self.hippocampus.search_memories(query, k=k)
                memories = result.get('memories', []) if isinstance(result, dict) else result
                # Add source label
                for mem in memories:
                    mem['source'] = 'hippocampus'
            elif strategy == 'semantic':
                result = await self.temporal_lobe.search_memories(query, k=k)
                memories = result.get('memories', []) if isinstance(result, dict) else result
                # Add source label
                for mem in memories:
                    mem['source'] = 'temporal_lobe'
            elif strategy == 'hybrid':
                # 🔥 Phase 4: Use BrainInspiredRetrieval (integrates all brain-like features)
                # Features:
                # - Fast/slow path detection (FastPathDetector)
                # - Iterative retrieval (HippocampalPrefrontalLoop)
                # - Gap detection & multi-round retrieval (GapDetector)
                # - Enhanced multi-strategy retrieval (semantic + keyword + entity)

                brain_result = await self.brain_retrieval.retrieve(
                    query=query,
                    k=k,
                    context=context,
                    activation_plan=activation_plan
                )

                memories = brain_result.memories

                # Log brain retrieval stats
                logger.info(f"🧠 BrainRetrieval: path={brain_result.path_type}, "
                           f"iterations={brain_result.iterations}, "
                           f"confidence={brain_result.confidence:.2f}, "
                           f"time={brain_result.retrieval_time_ms:.1f}ms")

                if brain_result.debug_info.get('gap_types_detected'):
                    logger.info(f"   Gap types: {brain_result.debug_info['gap_types_detected']}")

                # 🔥 P1-4: KG 覆盖率降级策略 (保留作为额外保障)
                # Check KG coverage and apply fallback if needed
                kg_coverage = self._calculate_kg_coverage(memories, query)

                if kg_coverage < 0.95 and brain_result.confidence < 0.6:
                    logger.warning(f"⚠️ Low KG coverage ({kg_coverage:.2%}) + low confidence ({brain_result.confidence:.2f}), triggering additional fallback")

                    # Pure semantic fallback (skip KG, use only embeddings)
                    adaptive_k = int(k * 1.5)
                    fallback_memories = await self._pure_semantic_fallback(
                        query=query,
                        k=adaptive_k,
                        activation_plan=activation_plan
                    )

                    # Merge with original results and re-rank
                    all_memories = memories + fallback_memories

                    # Deduplicate by ID
                    seen_ids = set()
                    unique_memories = []
                    for mem in all_memories:
                        mem_id = mem.get('id', id(mem))
                        if mem_id not in seen_ids:
                            unique_memories.append(mem)
                            seen_ids.add(mem_id)

                    # Re-rank by relevance/score
                    unique_memories.sort(
                        key=lambda x: x.get('relevance', x.get('score', x.get('resonance_score', 0))),
                        reverse=True
                    )

                    memories = unique_memories[:adaptive_k]
                    logger.info(f"   ✅ Additional fallback: {len(memories)} memories")
            else:
                # Default to hippocampus
                result = await self.hippocampus.search_memories(query, k=k)
                memories = result.get('memories', []) if isinstance(result, dict) else result
                # Add source label
                for mem in memories:
                    mem['source'] = 'hippocampus'

            # 🧩 Chunk-aware retrieval: expand chunks to include neighbors
            try:
                import re
                chunk_groups = {}  # group_id -> list of chunk numbers found

                # Step 1: Identify chunks and their groups
                for mem in memories:
                    content = mem.get('content', '')
                    # Match: [Chunk 2/5 | Group: chunk_group_abc123]
                    match = re.search(r'\[Chunk (\d+)/(\d+) \| Group: (chunk_group_\w+)\]', content)
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

                # Step 2: Expand to include neighboring chunks
                if chunk_groups:
                    logger.info(f"   🧩 Detected {len(chunk_groups)} chunk groups, expanding neighbors...")

                    expanded_memories = []
                    memory_ids_seen = set()  # Deduplicate

                    for mem in memories:
                        mem_id = mem.get('id', id(mem))
                        if mem_id not in memory_ids_seen:
                            expanded_memories.append(mem)
                            memory_ids_seen.add(mem_id)

                    # Retrieve neighboring chunks
                    for group_id, group_info in chunk_groups.items():
                        found_chunks = group_info['found_chunks']
                        total_chunks = group_info['total']
                        source = group_info['source']

                        # Determine which neighboring chunks to fetch
                        neighbors_to_fetch = set()
                        for chunk_num in found_chunks:
                            # Add previous and next chunks
                            if chunk_num > 1:
                                neighbors_to_fetch.add(chunk_num - 1)
                            if chunk_num < total_chunks:
                                neighbors_to_fetch.add(chunk_num + 1)

                        # Remove chunks we already have
                        neighbors_to_fetch -= found_chunks

                        if neighbors_to_fetch:
                            # Search for neighboring chunks by group ID
                            for neighbor_num in neighbors_to_fetch:
                                neighbor_pattern = f"[Chunk {neighbor_num}/{total_chunks} | Group: {group_id}]"

                                # Query source for this specific chunk
                                if source == 'hippocampus':
                                    neighbor_result = await self.hippocampus.search_memories(
                                        query=neighbor_pattern,
                                        k=1
                                    )
                                    neighbor_mems = neighbor_result.get('memories', []) if isinstance(neighbor_result, dict) else neighbor_result
                                elif source == 'temporal_lobe':
                                    neighbor_result = await self.temporal_lobe.search_memories(
                                        query=neighbor_pattern,
                                        k=1
                                    )
                                    neighbor_mems = neighbor_result.get('memories', []) if isinstance(neighbor_result, dict) else neighbor_result
                                else:
                                    neighbor_mems = []

                                # Add neighbor if found and not duplicate
                                for neighbor_mem in neighbor_mems:
                                    neighbor_id = neighbor_mem.get('id', id(neighbor_mem))
                                    if neighbor_id not in memory_ids_seen:
                                        neighbor_mem['source'] = source
                                        neighbor_mem['_is_neighbor_chunk'] = True  # Mark as expanded
                                        expanded_memories.append(neighbor_mem)
                                        memory_ids_seen.add(neighbor_id)

                    # Use expanded memories if we found neighbors
                    if len(expanded_memories) > len(memories):
                        logger.info(f"      ✅ Expanded from {len(memories)} to {len(expanded_memories)} memories (added {len(expanded_memories) - len(memories)} neighbor chunks)")
                        memories = expanded_memories

                        # Re-sort: prioritize original results, then neighbors
                        memories.sort(
                            key=lambda x: (
                                0 if not x.get('_is_neighbor_chunk', False) else 1,  # Original first
                                -x.get('relevance', x.get('score', 0))  # Then by score
                            )
                        )

                        # Limit to reasonable size (k * 2 at most)
                        memories = memories[:k * 2]

            except Exception as e:
                logger.warning(f"Chunk-aware retrieval failed: {e}")
                # Continue with original memories if expansion fails

            # 📊 Record retrieval metrics for observability
            try:
                metrics = get_metrics_collector()

                # Count sources
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

                # Record brain region activations
                for source in source_counts:
                    if source == 'hippocampus':
                        metrics.record_brain_region_activation('hippocampus', 'queried')
                    elif source == 'temporal_lobe':
                        metrics.record_brain_region_activation('temporal_lobe', 'queried')
                    elif source == 'memory_system':
                        metrics.record_brain_region_activation('memory_system', 'queried')
            except Exception as e:
                logger.warning(f"Failed to record retrieval metrics: {e}")

            # 🧠 类脑检索增强: 当检索结果不足时，尝试激活沉默印迹
            # 这模拟人脑在检索失败时的"再搜索"机制
            if len(memories) < k // 2 and self.hippocampus:
                logger.info(f"   🧠 Low retrieval results ({len(memories)}/{k}), attempting silent engram reactivation...")
                try:
                    # 提取查询实体
                    query_entities = [word for word in query.split() if word[0].isupper() and len(word) > 1]

                    # 尝试激活沉默印迹
                    if hasattr(self.hippocampus, 'forgetting_manager') and self.hippocampus.forgetting_manager:
                        reactivated = await self.hippocampus.forgetting_manager.try_reactivate_silent_memories(
                            query_entities=query_entities if query_entities else None,
                            max_reactivations=3,
                            boost_factor=1.2
                        )

                        if reactivated:
                            logger.info(f"   ✅ Reactivated {len(reactivated)} silent engrams")
                            # 将激活的印迹添加到结果中
                            for engram_info in reactivated:
                                # 构建记忆格式
                                reactivated_mem = {
                                    'id': engram_info.get('memory_id'),
                                    'content': f"[Reactivated] Entities: {engram_info.get('entities', [])}, Time: {engram_info.get('timestamp', 'unknown')}",
                                    'source': 'silent_engram',
                                    'relevance': engram_info.get('activation_score', 0.5),
                                    'needs_full_restoration': True
                                }
                                memories.append(reactivated_mem)
                except Exception as e:
                    logger.warning(f"Silent engram reactivation failed: {e}")

            # 🔥 V2.1: StoryArc + ToM 增强检索
            # 不仅限于 temporal 查询，对所有查询都尝试增强
            try:
                augmented = False

                # 1. StoryArc 实体上下文增强
                if self.story_arc:
                    # 提取查询中的实体
                    query_words = query.split()
                    query_entities = [w for w in query_words if len(w) > 1 and w[0].isupper()]

                    for entity in query_entities[:3]:  # 最多处理3个实体
                        entity_context = self.story_arc.get_entity_context(entity, limit=5)
                        if entity_context:
                            for event in entity_context:
                                # 避免重复
                                event_content = event.get('content', '')
                                if not any(event_content in m.get('content', '') for m in memories):
                                    memories.append({
                                        'content': event_content,
                                        'source': 'story_arc',
                                        'event_type': event.get('event_type'),
                                        'event_date': event.get('event_date'),
                                        'relevance': 0.75,  # StoryArc 匹配给予较高分数
                                        'memory_id': event.get('memory_id')
                                    })
                                    augmented = True

                    if augmented:
                        logger.info(f"   📅 StoryArc augmented: +{len([m for m in memories if m.get('source') == 'story_arc'])} events")

                # 2. ToM 心智模型增强 (偏好/意图相关查询)
                try:
                    from ..agents.brain_regions.theory_of_mind_agent import get_theory_of_mind_agent
                    tom = get_theory_of_mind_agent()

                    # 检测是否是偏好/意图相关查询
                    preference_keywords = ['prefer', 'like', 'want', 'favorite', 'choice', 'opinion', 'think', 'feel']
                    is_preference_query = any(kw in query.lower() for kw in preference_keywords)

                    if is_preference_query and query_entities:
                        for entity in query_entities[:2]:
                            mental_model = tom.get_mental_model(entity)
                            if mental_model:
                                # 将心智模型转换为记忆格式
                                for entry in mental_model[:3]:
                                    model_content = f"[Mental Model] {entity}: {entry.entry_type} - {entry.content}"
                                    if not any(model_content in m.get('content', '') for m in memories):
                                        memories.append({
                                            'content': model_content,
                                            'source': 'theory_of_mind',
                                            'relevance': 0.8,  # ToM 匹配给予高分数
                                            'entity': entity,
                                            'entry_type': entry.entry_type
                                        })
                                logger.info(f"   🎭 ToM mental model: +{len(mental_model[:3])} entries for {entity}")
                except Exception as e:
                    logger.debug(f"ToM augmentation skipped: {e}")

                # 重新排序：原始结果优先，然后是增强结果
                if augmented:
                    memories.sort(
                        key=lambda x: (
                            0 if x.get('source') not in ('story_arc', 'theory_of_mind') else 1,
                            -x.get('relevance', x.get('score', 0))
                        )
                    )
                    memories = memories[:k * 2]  # 限制总数

            except Exception as e:
                logger.warning(f"StoryArc/ToM augmentation failed: {e}")

            # P0-1: 存入检索缓存
            retrieval_cache.put(
                query=query,
                results=memories,
                k=k,
                strategy=strategy,
                regions=active_regions
            )

            return memories

        except Exception as e:
            logger.error(f"❌ Smart retrieve failed: {e}")
            return []

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
        # Combine content
        combined_content = "\n".join([
            f"- {ep.get('content', '')[:200]}"
            for ep in episodes[:10]  # Limit to avoid token overflow
        ])

        # Use consolidation agent's LLM capability
        prompt = f"""Extract core semantic knowledge from the following {len(episodes)} episodic memories:

Date: {date}

Episodic memories:
{combined_content}

Please extract:
1. Core facts and knowledge points
2. Common themes or patterns
3. Important entity relationships

Output as concise semantic knowledge (2-3 sentences)."""

        try:
            response = await self.consolidation_agent.call_llm(
                prompt=prompt,
                max_tokens=300,
                temperature=0.3
            )

            semantic_knowledge = response.strip()

            if len(semantic_knowledge) < 10:
                return None

            return f"[{date}] {semantic_knowledge}"

        except Exception as e:
            logger.warning(f"Failed to extract semantic knowledge: {e}")
            return None

    # ========================================================================
    # 🔥 Phase 3: Cross-Region Parallel Retrieval & Fusion
    # ========================================================================

    def _is_multi_hop_query(self, query: str) -> bool:
        """
        🔥 2025-12-14: 识别需要多跳推理的问题

        多跳问题特征:
        - 时间/因果关系 (after, before, because)
        - 计数问题 (how many times)
        - 比较问题 (compare, difference)
        - 关系链问题 (X's Y's Z)

        Returns:
            True 如果是多跳问题
        """
        multi_hop_patterns = [
            r'\b(after|before|since|until|following|prior to)\s+\w+',  # 时间关系
            r'\b(because|due to|as a result|caused by|led to)\b',       # 因果关系
            r'\bhow many (times|people|things|events)\b',               # 计数问题
            r'\bwhat.*and.*what\b',                                     # 多重what
            r'\brelat(ed|ion|ionship|ive)\b',                          # 关系问题
            r'\bcompare|difference|similar|both\b',                     # 比较问题
            r"'s\s+\w+'s\b",                                           # 关系链 (X's Y's)
            r'\ball\s+(the|of)\b',                                     # 全部枚举
        ]
        query_lower = query.lower()
        return any(re.search(p, query_lower) for p in multi_hop_patterns)

    async def cross_region_retrieval(
        self,
        query: str,
        top_k: int = 20,  # 🔥 2025-12-14: 从5增加到20，提高多跳检索覆盖率
        activation_plan: Optional[Dict[str, bool]] = None
    ) -> List[Dict]:
        """
        🔥 Phase 3: Cross-region parallel retrieval with result fusion
        跨脑区并行检索与结果融合

        Retrieves memories from multiple brain regions in parallel,
        then fuses results with resonance scoring.

        Args:
            query: Search query
            top_k: Number of results to return
            activation_plan: Optional dict specifying which regions to activate
                           (from Thalamus dynamic gating)

        Returns:
            List of fused memories with resonance scores
        """
        # 🔥 2025-12-14: 动态调整 top_k based on query complexity
        is_multi_hop = self._is_multi_hop_query(query)
        if is_multi_hop:
            effective_top_k = max(top_k, 30)  # 多跳问题至少30条
            logger.info(f"🧠 Phase 3: Multi-hop query detected, using top_k={effective_top_k}")
        else:
            effective_top_k = top_k

        logger.info(f"🧠 Phase 3: Cross-region retrieval for query: '{query[:50]}...'")

        # Default: activate only core memory regions (hippocampus + temporal_lobe)
        # Other regions (prefrontal, amygdala, basal_ganglia) add noise for factual queries
        if activation_plan is None:
            activation_plan = {
                'hippocampus': True,      # Episodic memory - essential
                'temporal_lobe': True,    # Semantic memory - essential
                'prefrontal': False,      # Working memory - skip by default (adds reasoning traces)
                'amygdala': False,        # Emotional tags - skip by default (adds noise)
                'basal_ganglia': False    # Procedural patterns - skip by default
            }

        # Phase 1: Build parallel retrieval tasks
        retrieval_tasks = {}

        # Hippocampus: Episodic memories
        if activation_plan.get('hippocampus') and self.hippocampus:
            async def retrieve_hippocampus():
                try:
                    # Use search_memories for general query
                    result = await self.hippocampus.search_memories(query, k=effective_top_k * 2)
                    return result.get('memories', [])
                except Exception as e:
                    logger.warning(f"Hippocampus retrieval failed: {e}")
                    return []
            retrieval_tasks['hippocampus'] = retrieve_hippocampus()

        # Temporal Lobe: Semantic knowledge + KG联合检索
        # 🔧 2025-12-02: 优先使用KG联合检索，fallback到普通检索
        if activation_plan.get('temporal_lobe') and self.temporal_lobe:
            async def retrieve_temporal():
                try:
                    # 🔧 优先尝试KG联合检索 (search_kg_memory_joint)
                    if hasattr(self.temporal_lobe, 'search_kg_memory_joint'):
                        result = await self.temporal_lobe.search_kg_memory_joint(
                            query=query,
                            k=top_k * 2,
                            kg_depth=1,  # 单跳关系
                            beta=0.6     # KG权重60%
                        )
                        memories = result.get('memories', [])
                        # 标记来源
                        for mem in memories:
                            mem['kg_enhanced'] = True
                        if memories:
                            logger.debug(f"Temporal Lobe KG-joint retrieval: {len(memories)} memories")
                            return memories

                    # Fallback: 普通检索
                    result = await self.temporal_lobe.search_memories(query, k=top_k * 2)
                    return result.get('memories', [])
                except Exception as e:
                    logger.warning(f"Temporal Lobe retrieval failed: {e}")
                    return []
            retrieval_tasks['temporal_lobe'] = retrieve_temporal()

        # Prefrontal: Reasoning traces
        if activation_plan.get('prefrontal') and self.prefrontal_storage:
            async def retrieve_prefrontal():
                try:
                    # Retrieve items from working memory (use 'k' parameter not 'limit')
                    result = self.prefrontal_storage.retrieve_items(k=top_k)
                    # Convert WorkingMemoryItem dataclass to dict
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
        if activation_plan.get('amygdala') and self.amygdala:
            async def retrieve_amygdala():
                try:
                    # Use search_by_emotion with empty emotion_tags to get all memories
                    result = self.amygdala.search_by_emotion(
                        emotion_tags=None,
                        min_intensity=0.0,
                        k=top_k
                    )
                    # Convert EmotionalMemory dataclass to dict
                    memories = []
                    for mem in result.get('memories', []):
                        if hasattr(mem, '__dict__'):
                            mem_dict = vars(mem).copy()
                            # Convert datetime to string for JSON serialization
                            if 'timestamp' in mem_dict and hasattr(mem_dict['timestamp'], 'isoformat'):
                                mem_dict['timestamp'] = mem_dict['timestamp'].isoformat()
                            if 'last_practiced' in mem_dict and mem_dict['last_practiced'] and hasattr(mem_dict['last_practiced'], 'isoformat'):
                                mem_dict['last_practiced'] = mem_dict['last_practiced'].isoformat()
                            memories.append(mem_dict)
                        else:
                            memories.append(mem)
                    return memories
                except Exception as e:
                    logger.warning(f"Amygdala retrieval failed: {e}")
                    return []
            retrieval_tasks['amygdala'] = retrieve_amygdala()

        # Basal Ganglia: Procedural patterns
        if activation_plan.get('basal_ganglia') and self.basal_ganglia:
            async def retrieve_basal():
                try:
                    # Use search_skills method
                    result = self.basal_ganglia.search_skills(query, k=top_k)
                    # Convert ProceduralMemory dataclass to dict
                    patterns = []
                    for skill in result.get('skills', []):
                        if hasattr(skill, '__dict__'):
                            skill_dict = vars(skill).copy()
                            # Convert datetime to string
                            if 'timestamp' in skill_dict and hasattr(skill_dict['timestamp'], 'isoformat'):
                                skill_dict['timestamp'] = skill_dict['timestamp'].isoformat()
                            if 'last_practiced' in skill_dict and skill_dict['last_practiced'] and hasattr(skill_dict['last_practiced'], 'isoformat'):
                                skill_dict['last_practiced'] = skill_dict['last_practiced'].isoformat()
                            patterns.append(skill_dict)
                        else:
                            patterns.append(skill)
                    return patterns
                except Exception as e:
                    logger.warning(f"Basal Ganglia retrieval failed: {e}")
                    return []
            retrieval_tasks['basal_ganglia'] = retrieve_basal()

        # Execute all retrieval tasks in parallel
        logger.info(f"   Querying {len(retrieval_tasks)} brain regions in parallel")
        results = await asyncio.gather(*retrieval_tasks.values(), return_exceptions=True)

        # Map results back to region names
        region_memories = {}
        for region_name, result in zip(retrieval_tasks.keys(), results):
            if isinstance(result, Exception):
                logger.warning(f"   {region_name}: retrieval exception {result}")
                region_memories[region_name] = []
            else:
                logger.info(f"   {region_name}: retrieved {len(result)} memories")
                region_memories[region_name] = result

        # Phase 2: Fuse results with resonance scoring
        fused_memories = await self._fuse_cross_region_results(region_memories, query)

        logger.info(f"   Final: {len(fused_memories)} fused memories (top {top_k})")
        return fused_memories[:top_k]

    async def _fuse_cross_region_results(
        self,
        region_memories: Dict[str, List],
        query: str
    ) -> List[Dict]:
        """
        🔥 Phase 3: Fuse multi-region results with resonance scoring
        融合多脑区结果，计算共振分数

        Resonance scoring:
        - Base score: Calibrated relevance score (使用置信度校准器)
        - Resonance bonus: +0.15 for each additional region
        - Emotional boost: +0.2 * intensity if from Amygdala

        Args:
            region_memories: Dict mapping region names to memory lists
            query: Original query

        Returns:
            Sorted list of memories with resonance metadata
        """
        logger.debug("   Fusing cross-region results...")

        # 🔥 Phase 3: 使用置信度校准器进行跨脑区分数校准
        # 替换原来的简单归一化方法
        calibrated_region_memories = self.confidence_calibrator.calibrate_scores(
            region_memories, query
        )

        # 同时保留简单归一化作为后备（用于新脑区或校准器未初始化时）
        region_scales = self._calibrate_region_confidence(region_memories)

        memory_resonance = {}  # {memory_id: {memory, regions, scores}}

        # Aggregate memories across regions
        for region_name, memories in calibrated_region_memories.items():
            if not memories:
                continue

            for mem in memories:
                # Get memory identifier
                mem_id = self._get_memory_id(mem)

                if mem_id not in memory_resonance:
                    # 🔥 优先使用校准后的分数，否则使用简单归一化
                    if 'calibrated_score' in mem:
                        base_score = mem['calibrated_score']
                    else:
                        base_score_raw = self._get_memory_score(mem)
                        base_score = base_score_raw * region_scales.get(region_name, 1.0)

                    memory_resonance[mem_id] = {
                        'memory': mem,
                        'regions': set(),
                        'base_score': base_score,
                        'emotional_boost': 0.0,
                        'resonance_score': 0.0,
                        'calibration_info': mem.get('_calibration', {})
                    }

                # Record which regions contain this memory
                memory_resonance[mem_id]['regions'].add(region_name)

                # Amygdala emotional weighting
                if region_name == 'amygdala':
                    intensity = mem.get('intensity', mem.get('emotion_intensity', 0.5))
                    memory_resonance[mem_id]['emotional_boost'] = float(intensity) * 0.2

        # Calculate final resonance scores
        for mem_id, data in memory_resonance.items():
            region_count = len(data['regions'])

            # Resonance bonus: memories appearing in multiple regions are more important
            resonance_bonus = (region_count - 1) * 0.15

            # Final score
            data['resonance_score'] = (
                data['base_score'] +
                resonance_bonus +
                data['emotional_boost']
            )

            logger.debug(f"      Memory {mem_id[:8]}: regions={region_count}, "
                        f"base={data['base_score']:.2f}, "
                        f"resonance={data['resonance_score']:.2f}")

        # Sort by resonance score
        sorted_memories = sorted(
            memory_resonance.values(),
            key=lambda x: x['resonance_score'],
            reverse=True
        )

        # Add resonance metadata to memories
        result_memories = []
        for mem_data in sorted_memories:
            memory = mem_data['memory'].copy() if isinstance(mem_data['memory'], dict) else mem_data['memory']

            # Add metadata
            if isinstance(memory, dict):
                memory['_meta'] = {
                    'regions': list(mem_data['regions']),
                    'resonance_score': mem_data['resonance_score'],
                    'region_count': len(mem_data['regions']),
                    'emotional_boost': mem_data['emotional_boost'],
                    'calibration': mem_data.get('calibration_info', {})  # 🔥 添加校准信息
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
        🔥 Phase 3: 记录检索结果用于校准学习

        Args:
            region_name: 脑区名称
            query: 查询
            memories_used: 使用的记忆
            success: 是否成功
            feedback_score: 反馈分数
        """
        self.confidence_calibrator.record_outcome(
            region_name=region_name,
            query=query,
            memories_used=memories_used,
            success=success,
            feedback_score=feedback_score
        )

    def get_calibration_stats(self) -> Dict[str, Any]:
        """获取校准统计信息"""
        return self.confidence_calibrator.get_calibration_stats()

    def save_calibration(self) -> bool:
        """保存校准状态"""
        return self.confidence_calibrator.save_calibration()

    def _calibrate_region_confidence(self, region_memories: Dict[str, List]) -> Dict[str, float]:
        """
        根据各脑区的平均相关度对分值做缩放，减少单一区域打分过高导致的偏置
        (保留作为后备方法)
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
        return {region: (avg / max_avg) for region, avg in averages.items()}

    def _get_memory_id(self, memory: Any) -> str:
        """Extract memory ID from various memory formats"""
        if isinstance(memory, dict):
            return memory.get('id', memory.get('memory_id', memory.get('reference_id', str(id(memory)))))
        elif hasattr(memory, 'id'):
            return memory.id
        elif hasattr(memory, 'memory_id'):
            return memory.memory_id
        else:
            return str(id(memory))

    def _get_memory_score(self, memory: Any) -> float:
        """Extract relevance score from various memory formats"""
        if isinstance(memory, dict):
            return memory.get('score', memory.get('relevance', memory.get('importance', 0.5)))
        elif hasattr(memory, 'score'):
            return memory.score
        elif hasattr(memory, 'importance'):
            return memory.importance
        else:
            return 0.5  # Default neutral score

    # ═══════════════════════════════════════════════════════════════════════════
    # 🔥 2025-12-20: StoryArc 时间线查询接口
    # ═══════════════════════════════════════════════════════════════════════════

    async def query_event_time(
        self,
        entity: str,
        event_keywords: List[str],
        time_hint: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        查询实体的事件发生时间 (通过 StoryArc 时间线索引)

        Args:
            entity: 实体名称 (e.g., 'Caroline')
            event_keywords: 事件关键词 (e.g., ['museum', 'visit'])
            time_hint: 时间提示 (e.g., 'July 2023', 'summer')

        Returns:
            {
                'event_date': date,
                'formatted_date': str,  # e.g., '5 July 2023'
                'confidence': float,
                'event': TimelineEvent
            }
        """
        return await self.story_arc.query_event_time(entity, event_keywords, time_hint)

    async def calculate_duration(
        self,
        entity: str,
        reference: str,
        reference_date: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """
        计算时间跨度 (通过 StoryArc)

        Args:
            entity: 实体名称
            reference: 参考内容 (e.g., 'friends', 'living in current city')
            reference_date: 参考日期

        Returns:
            {'duration': str, 'start_date': date, 'confidence': float}
        """
        from datetime import date as date_type
        ref_date = reference_date.date() if reference_date else date_type.today()
        return await self.story_arc.calculate_duration(entity, reference, ref_date)

    def get_story_arc_statistics(self) -> Dict[str, Any]:
        """获取 StoryArc 统计信息"""
        return self.story_arc.get_statistics()

    def clear_story_arc(self):
        """清空 StoryArc 时间线 (用于测试重置)"""
        self.story_arc.clear()
        logger.info("StoryArc timeline cleared")
