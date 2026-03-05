"""
Agent Storage Proxy
Bridges brain region agents to IBrainRegionStorage interface

Wraps agents (HippocampusAgent, TemporalLobeAgent, etc.) that have their own
APIs (store_memory, search_memories) to match the IBrainRegionStorage contract
(region_store, region_retrieve) expected by MemoryConsolidationPipeline.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .memory_item import MemoryItem
from .brain_region_storage_interface import IBrainRegionStorage

logger = logging.getLogger(__name__)


class AgentStorageProxy(IBrainRegionStorage):
    """
    Proxy that wraps a brain region agent and exposes IBrainRegionStorage interface

    This allows consolidation pipeline to work with agents using a unified API,
    while agents maintain their own specialized methods.
    """

    def __init__(self, agent, region_name: str):
        """
        Args:
            agent: Brain region agent (HippocampusAgent, TemporalLobeAgent, etc.)
            region_name: Name for logging/debugging
        """
        self.agent = agent
        self.region_name = region_name
        self._brain_region_name = region_name  # Required by IBrainRegionStorage
        self.current_step = 0  # HRM timestep (required by IBrainRegionStorage)

        logger.debug(f"AgentStorageProxy created for {region_name}")

    @property
    def brain_region_name(self) -> str:
        """Region name property (required by IBrainRegionStorage)"""
        return self._brain_region_name

    async def region_store(
        self,
        memory: MemoryItem,
        hrm_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store memory via agent's store_memory API

        Args:
            memory: MemoryItem to store
            hrm_metadata: HRM coordination metadata

        Returns:
            Memory ID
        """
        logger.info(f"🔵 [{self.region_name}] region_store called for memory type={memory.memory_type}, "
                   f"content_len={len(memory.content)}, importance={memory.importance}")

        # Agents use store_memory(content, entities, ...) not region_store
        if hasattr(self.agent, 'store_memory'):
            # Extract entities/relations from metadata
            entities = memory.metadata.get('entities', [])
            relations = memory.metadata.get('relations', [])

            # Prepare metadata with HRM info
            agent_metadata = {**memory.metadata}
            if hrm_metadata:
                agent_metadata['hrm'] = hrm_metadata

            # Build kwargs dynamically to handle different agent signatures
            kwargs = {
                'content': memory.content,
                'entities': entities,
                'importance': memory.importance,
                'metadata': agent_metadata
            }

            # Check if agent accepts emotion_tags (hippocampus does, temporal lobe doesn't)
            import inspect
            sig = inspect.signature(self.agent.store_memory)
            if 'emotion_tags' in sig.parameters:
                kwargs['emotion_tags'] = memory.emotion_tags
            else:
                # Store emotion_tags in metadata for agents that don't have it as param
                if memory.emotion_tags:
                    agent_metadata['emotion_tags'] = memory.emotion_tags

            # Check if agent accepts relations (temporal lobe does)
            if 'relations' in sig.parameters:
                kwargs['relations'] = relations

            logger.debug(f"📤 [{self.region_name}] Calling agent.store_memory with kwargs: "
                        f"content_len={len(kwargs['content'])}, entities={len(entities)}, "
                        f"relations={len(relations)}, importance={kwargs['importance']}")

            # Call agent's store_memory with appropriate params
            try:
                result = await self.agent.store_memory(**kwargs)

                logger.debug(f"📥 [{self.region_name}] agent.store_memory returned: {result}")

                if not result:
                    logger.error(f"❌ [{self.region_name}] agent.store_memory returned None/empty!")
                    return memory.id  # Fallback to original ID

                if isinstance(result, dict):
                    memory_id = result.get('memory_id', memory.id)
                    logger.info(f"✅ [{self.region_name}] Successfully stored memory: {memory_id[:16]}")
                    return memory_id
                else:
                    logger.warning(f"⚠️ [{self.region_name}] agent.store_memory returned unexpected type: {type(result)}")
                    return str(result) if result else memory.id

            except Exception as e:
                logger.error(f"❌ [{self.region_name}] agent.store_memory raised exception: {e}")
                logger.error(f"   Exception type: {type(e).__name__}")
                import traceback
                logger.error(f"   Traceback: {traceback.format_exc()}")
                raise  # Re-raise to propagate to caller

        # Fallback: use storage_adapter if available (hippocampus case)
        elif hasattr(self.agent, 'storage_adapter'):
            return await self.agent.storage_adapter.region_store(memory, hrm_metadata)

        else:
            raise AttributeError(
                f"{self.region_name} has no store_memory or storage_adapter"
            )

    async def region_retrieve(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        k: int = 10
    ) -> List[MemoryItem]:
        """
        Retrieve memories via agent's API

        Args:
            query: Search query
            filters: Optional filters (e.g. {'id': '...'} for direct lookup)
            k: Number of results

        Returns:
            List of MemoryItem objects
        """
        # Case 1: Direct ID lookup (prioritize over semantic search)
        mem_id = (filters or {}).get('id')
        if mem_id:
            # Try agent's retrieve_memory_by_id method first
            if hasattr(self.agent, 'retrieve_memory_by_id'):
                try:
                    mem_dict = await self.agent.retrieve_memory_by_id(mem_id)
                    if mem_dict:
                        logger.debug(f"Retrieved {mem_id[:8]} via retrieve_memory_by_id")
                        return [self._dict_to_memory_item(mem_dict)]
                    else:
                        logger.warning(f"Memory {mem_id[:8]} not found via retrieve_memory_by_id")
                        return []
                except Exception as e:
                    logger.error(f"retrieve_memory_by_id failed for {mem_id[:8]}: {e}")
                    # Fall through to other methods

            # Try memory_dict lookup
            if hasattr(self.agent, 'memory_dict'):
                if mem_id in self.agent.memory_dict:
                    mem_obj = self.agent.memory_dict[mem_id]
                    # Convert to MemoryItem if needed
                    if isinstance(mem_obj, MemoryItem):
                        logger.debug(f"Retrieved {mem_id[:8]} via memory_dict")
                        return [mem_obj]
                    elif hasattr(self.agent, '_memory_to_dict'):
                        # Agent has conversion method
                        mem_dict = self.agent._memory_to_dict(mem_obj)
                        return [self._dict_to_memory_item(mem_dict)]
                    else:
                        # Assume it's already a dict-like object
                        return [self._dict_to_memory_item(mem_obj)]
                else:
                    logger.warning(f"Memory {mem_id[:8]} not found in memory_dict")

            # Try storage_adapter with ID filter
            if hasattr(self.agent, 'storage_adapter'):
                try:
                    results = await self.agent.storage_adapter.region_retrieve(query, filters, k)
                    if results:
                        logger.debug(f"Retrieved {mem_id[:8]} via storage_adapter")
                        return results
                except Exception as e:
                    logger.error(f"storage_adapter retrieval failed for {mem_id[:8]}: {e}")

            # All ID lookup methods failed
            logger.error(f"❌ Failed to retrieve memory {mem_id[:8]} - tried all methods")
            return []

        # Case 2: Semantic search using agent's search_memories
        if hasattr(self.agent, 'search_memories'):
            result = await self.agent.search_memories(query=query, k=k)

            # Result format: {'memories': [...], ...} or {'results': [...]}
            memories = result.get('results', result.get('memories', []))

            # Convert to MemoryItem objects
            return [self._dict_to_memory_item(m) for m in memories]

        # Case 3: Fallback to storage_adapter
        elif hasattr(self.agent, 'storage_adapter'):
            return await self.agent.storage_adapter.region_retrieve(query, filters, k)

        else:
            logger.warning(f"{self.region_name} has no search_memories or storage_adapter")
            return []

    async def receive_hrm_signal(
        self,
        signal_type: str,
        payload: Dict[str, Any]
    ):
        """
        Receive HRM coordination signal

        Args:
            signal_type: Type of signal (e.g. 'timestep_update')
            payload: Signal data
        """
        # Update timestep
        if signal_type == 'timestep_update':
            self.current_step = payload.get('step', self.current_step + 1)

        # Forward to agent if it has HRM support
        if hasattr(self.agent, 'receive_hrm_signal'):
            await self.agent.receive_hrm_signal(signal_type, payload)

        # Or forward to storage_adapter
        elif hasattr(self.agent, 'storage_adapter'):
            await self.agent.storage_adapter.receive_hrm_signal(signal_type, payload)

    def _dict_to_memory_item(self, mem_dict: Dict[str, Any]) -> MemoryItem:
        """Convert memory dict to MemoryItem object"""
        # Handle timestamp conversion
        timestamp = mem_dict.get('timestamp', '')
        if isinstance(timestamp, str) and timestamp:
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except (ValueError, AttributeError):
                timestamp = datetime.now()
        elif not timestamp:
            timestamp = datetime.now()

        # Extract entities/relations from metadata
        metadata = mem_dict.get('metadata', {}).copy()
        if 'entities' not in metadata and 'entities' in mem_dict:
            metadata['entities'] = mem_dict.get('entities', [])
        if 'relations' not in metadata and 'relations' in mem_dict:
            metadata['relations'] = mem_dict.get('relations', [])

        return MemoryItem(
            id=mem_dict.get('id', ''),
            content=mem_dict.get('content', ''),
            memory_type=mem_dict.get('memory_type', 'episodic'),
            timestamp=timestamp,
            importance=mem_dict.get('importance', 0.5),
            emotion_tags=mem_dict.get('emotion_tags', []),
            emotion_intensity=mem_dict.get('emotion_intensity', 0.5),
            context_tags=mem_dict.get('context_tags', []),
            metadata=metadata
        )
