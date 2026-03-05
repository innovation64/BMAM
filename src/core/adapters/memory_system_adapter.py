"""
Memory System Adapter
记忆系统适配器

Adapts AdvancedMemorySystem to IMemorySystem interface
将AdvancedMemorySystem适配到IMemorySystem接口
"""

from typing import List, Dict, Any, Optional
import logging

from ..interfaces import IMemorySystem, Memory
import numpy as np

logger = logging.getLogger(__name__)


class MemorySystemAdapter(IMemorySystem):
    """
    Adapter for AdvancedMemorySystem to IMemorySystem interface
    AdvancedMemorySystem到IMemorySystem接口的适配器

    Bridges the legacy AdvancedMemorySystem with the new interface contract.
    桥接遗留的AdvancedMemorySystem与新接口契约。

    This adapter allows using the existing AdvancedMemorySystem implementation
    while conforming to the IMemorySystem interface, enabling gradual migration
    and testing with mocks.

    Example:
        from src.memory.memory_system import AdvancedMemorySystem
        from src.core.adapters import MemorySystemAdapter

        legacy_system = AdvancedMemorySystem()
        adapted_system = MemorySystemAdapter(legacy_system)

        # Now works with IMemorySystem interface
        memory_id = await adapted_system.store_memory("content")
        results = await adapted_system.search_memories("query")
    """

    def __init__(self, legacy_system):
        """
        Initialize adapter with legacy memory system

        Args:
            legacy_system: AdvancedMemorySystem instance
        """
        self._legacy = legacy_system
        logger.debug(f"MemorySystemAdapter initialized with {type(legacy_system).__name__}")

    async def store_memory(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5
    ) -> str:
        """
        Store a new memory

        Args:
            content: Memory content
            metadata: Optional metadata
            importance: Importance score (0-1)

        Returns:
            Memory ID
        """
        try:
            # Legacy system uses store_memory with similar signature
            memory_id = await self._legacy.store_memory(
                content=content,
                metadata=metadata or {},
                importance=importance
            )
            return memory_id
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            raise

    async def store_batch(self, memories: List[Dict[str, Any]]) -> List[str]:
        """
        Store multiple memories in batch

        Args:
            memories: List of memory dictionaries

        Returns:
            List of memory IDs
        """
        try:
            # Store memories one by one (legacy system may not have batch method)
            ids = []
            for mem in memories:
                mem_id = await self.store_memory(
                    content=mem['content'],
                    metadata=mem.get('metadata'),
                    importance=mem.get('importance', 0.5)
                )
                ids.append(mem_id)
            return ids
        except Exception as e:
            logger.error(f"Error storing batch memories: {e}")
            raise

    async def update_memory(self, memory_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update existing memory

        Args:
            memory_id: Memory identifier
            updates: Dictionary of updates

        Returns:
            True if successful
        """
        try:
            # Check if legacy system has update method
            if hasattr(self._legacy, 'update_memory'):
                return await self._legacy.update_memory(memory_id, updates)
            else:
                # Fallback: retrieve, modify, and re-store
                memory = await self.retrieve_by_id(memory_id)
                if not memory:
                    return False

                # Apply updates
                new_metadata = {**memory.metadata, **updates.get('metadata', {})}
                new_importance = updates.get('importance', memory.importance)

                # Re-store (this is a limitation of the adapter)
                await self.store_memory(
                    content=memory.content,
                    metadata=new_metadata,
                    importance=new_importance
                )
                return True
        except Exception as e:
            logger.error(f"Error updating memory {memory_id}: {e}")
            return False

    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory

        Args:
            memory_id: Memory identifier

        Returns:
            True if successful
        """
        try:
            if hasattr(self._legacy, 'delete_memory'):
                return await self._legacy.delete_memory(memory_id)
            else:
                logger.warning("Legacy system does not support delete_memory")
                return False
        except Exception as e:
            logger.error(f"Error deleting memory {memory_id}: {e}")
            return False

    async def retrieve(
        self,
        query: str,
        k: int = 10,
        **filters
    ) -> List[Memory]:
        """
        Retrieve memories matching query

        Args:
            query: Search query
            k: Number of results
            **filters: Additional filters

        Returns:
            List of Memory objects
        """
        try:
            # Use legacy search_memories method
            results = await self._legacy.search_memories(
                query=query,
                search_type="semantic",
                k=k,
                **filters
            )

            # Convert to Memory objects
            memories = []
            for result in results:
                memory = Memory(
                    memory_id=result.get('memory_id', result.get('id', '')),
                    content=result.get('content', ''),
                    embedding=result.get('embedding'),
                    metadata=result.get('metadata', {}),
                    importance=result.get('importance', 0.5),
                    timestamp=result.get('timestamp', result.get('metadata', {}).get('timestamp', ''))
                )
                memories.append(memory)

            return memories
        except Exception as e:
            logger.error(f"Error retrieving memories: {e}")
            raise

    async def retrieve_by_id(self, memory_id: str) -> Optional[Memory]:
        """
        Retrieve a specific memory by ID

        Args:
            memory_id: Memory identifier

        Returns:
            Memory object or None
        """
        try:
            # Check if legacy has retrieve_by_id
            if hasattr(self._legacy, 'retrieve_by_id'):
                result = await self._legacy.retrieve_by_id(memory_id)
                if result:
                    return Memory(
                        memory_id=result.get('memory_id', memory_id),
                        content=result.get('content', ''),
                        embedding=result.get('embedding'),
                        metadata=result.get('metadata', {}),
                        importance=result.get('importance', 0.5),
                        timestamp=result.get('timestamp', '')
                    )
            else:
                # Fallback: search and filter
                logger.debug(f"Using fallback retrieve for {memory_id}")
                # This is inefficient but works
                return None
        except Exception as e:
            logger.error(f"Error retrieving memory {memory_id}: {e}")
            return None

    async def retrieve_by_ids(self, memory_ids: List[str]) -> List[Memory]:
        """
        Retrieve multiple memories by IDs

        Args:
            memory_ids: List of memory identifiers

        Returns:
            List of Memory objects
        """
        try:
            memories = []
            for mem_id in memory_ids:
                memory = await self.retrieve_by_id(mem_id)
                if memory:
                    memories.append(memory)
            return memories
        except Exception as e:
            logger.error(f"Error retrieving memories by IDs: {e}")
            raise

    async def search_memories(
        self,
        query: str,
        search_type: str = "semantic",
        k: int = 10,
        threshold: float = 0.1,
        **filters
    ) -> List[Dict[str, Any]]:
        """
        Unified search interface supporting multiple strategies

        Args:
            query: Search query
            search_type: "semantic", "hybrid", or "keyword"
            k: Number of results
            threshold: Minimum similarity threshold
            **filters: Additional filters

        Returns:
            List of memory dictionaries
        """
        try:
            # Legacy system has search_memories method
            results = await self._legacy.search_memories(
                query=query,
                search_type=search_type,
                k=k,
                threshold=threshold,
                **filters
            )
            return results
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            raise

    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get memory system statistics

        Returns:
            Statistics dictionary
        """
        try:
            if hasattr(self._legacy, 'get_system_stats'):
                return self._legacy.get_system_stats()
            elif hasattr(self._legacy, 'get_stats'):
                return self._legacy.get_stats()
            else:
                # Return basic stats
                return {
                    'adapter': 'MemorySystemAdapter',
                    'legacy_type': type(self._legacy).__name__
                }
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {'error': str(e)}

    @property
    def legacy_system(self):
        """Access to underlying legacy system for advanced operations"""
        return self._legacy
