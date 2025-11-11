"""
Persona Memory Agent
人格/价值观记忆智能体 - 维护价值取向与人格相关长期记忆
"""

from __future__ import annotations
from copy import deepcopy
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

from ..base import BrainAgent, AgentMessage, BrainRegion

logger = logging.getLogger(__name__)


class PersonaMemoryAgent(BrainAgent):
    """
    Persona & Values Memory Agent (Default Mode / Medial Prefrontal)
    
    负责：
    - 存储人格、价值观、长期偏好等信息
    - 检索人格相关记忆，为人格智能体提供上下文
    - 记录重复提及次数，追踪价值观变动
    """

    def __init__(self, db_manager=None, embedding_service=None, vector_db=None):
        super().__init__(
            agent_id="persona_memory",
            brain_region=BrainRegion.DEFAULT_MODE,
            system_prompt="""You are the persona/value memory subsystem of a brain-inspired AI.
            Your role is to:
            1. Store stable persona, preferences and value alignment memories
            2. Provide persona-aligned memories for personality generation
            3. Track repeated mentions to understand enduring preferences
            4. Maintain metadata useful for value alignment and persona evolution"""
        )

        self.db_manager = db_manager
        self.embedding_service = embedding_service
        self.vector_db = vector_db
        self.total_persona_memories = 0

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        action = message.content.get('action')

        if action == 'store_persona_memory':
            return await self._store_persona_memory(message.content.get('memory', {}))
        if action == 'retrieve_persona_memories':
            return await self._retrieve_persona_memories(
                message.content.get('query', ''),
                message.content.get('k', 5)
            )
        if action == 'recent_persona_memories':
            return await self._get_recent_persona_memories(message.content.get('limit', 5))
        if action == 'summarize_persona':
            return await self._summarize_persona_profile()

        return {'error': f'Unknown persona action: {action}'}

    async def store_persona(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        """Public wrapper for storing persona memories."""
        return await self._store_persona_memory(memory)

    async def retrieve_persona(self, query: str, k: int = 5) -> Dict[str, Any]:
        """Public wrapper for retrieving persona memories."""
        return await self._retrieve_persona_memories(query, k)

    async def recent_persona(self, limit: int = 5) -> Dict[str, Any]:
        """Public wrapper for recent persona memories."""
        return await self._get_recent_persona_memories(limit)

    async def _store_persona_memory(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        if not memory or not memory.get('content'):
            return {'error': 'Invalid persona memory payload'}

        payload = deepcopy(memory)
        payload.setdefault('memory_type', 'persona')
        payload.setdefault('importance', 0.6)
        payload.setdefault('emotion_tags', ['neutral'])

        context_tags = set(payload.get('context_tags', []))
        context_tags.update({'persona', payload.get('category', 'general_persona')})
        payload['context_tags'] = list(context_tags)

        metadata = deepcopy(payload.get('metadata', {}) or {})
        metadata.setdefault('persona_category', payload.get('category', 'general_persona'))
        metadata.setdefault('value_alignment', payload.get('value_alignment', 'neutral'))
        metadata.setdefault('source', payload.get('source', 'persona_memory_agent'))

        history = list(metadata.get('repeat_history', []))
        history.append({
            'timestamp': datetime.now().isoformat(),
            'content': payload.get('content', '')
        })
        metadata['repeat_history'] = history
        metadata['repeat_count'] = len(history)
        payload['metadata'] = metadata

        duplicate = await self._find_duplicate_persona(payload)
        if duplicate and duplicate.get('memory_id'):
            merged = await self._merge_persona_memory(
                duplicate['memory_id'],
                payload,
                duplicate.get('similarity', 0.0)
            )
            merged['stored'] = False
            merged['duplicate_detected'] = True
            return merged

        from ...memory.memory_system import memory_system

        memory_id = await memory_system.store_memory(
            content=payload['content'],
            memory_type=payload.get('memory_type', 'persona'),
            importance=payload.get('importance', 0.6),
            emotion_tags=payload.get('emotion_tags', []),
            context_tags=payload.get('context_tags', []),
            metadata=payload.get('metadata', {})
        )

        if memory_id:
            self.total_persona_memories += 1
            logger.debug("🧬 Persona memory stored %s: %s", memory_id, payload['content'][:60])
            await self._link_related_persona_memories(memory_id)
            return {
                'stored': True,
                'memory_id': memory_id,
                'duplicate_detected': False,
                'total_persona_memories': self.total_persona_memories
            }

        logger.error("Failed to store persona memory: %s", payload['content'][:60])
        return {'stored': False, 'error': 'memory_system store failed'}

    async def _retrieve_persona_memories(self, query: str, k: int = 5) -> Dict[str, Any]:
        from ...memory.memory_system import memory_system

        if not query:
            return {'memories': [], 'retrieval_method': 'persona_semantic', 'count': 0}

        try:
            raw_results = await memory_system.search_memories(
                query,
                search_type='semantic',
                k=k * 3,
                threshold=0.15
            )
        except Exception as exc:
            logger.warning(f"Persona memory retrieval failed: {exc}")
            return {'memories': [], 'retrieval_method': 'persona_semantic', 'count': 0}

        persona_memories = []
        for item in raw_results:
            context_tags = set(item.get('context_tags', []))
            if item.get('memory_type') == 'persona' or 'persona' in context_tags:
                persona_memories.append({
                    'memory': item,
                    'retrieval_confidence': item.get('similarity_score', 0.0),
                    'retrieval_method': 'persona_semantic'
                })

        persona_memories.sort(key=lambda x: x['retrieval_confidence'], reverse=True)
        top = persona_memories[:k]

        return {
            'memories': top,
            'retrieval_method': 'persona_semantic',
            'count': len(top)
        }

    async def _get_recent_persona_memories(self, limit: int = 5) -> Dict[str, Any]:
        if not self.db_manager:
            return {'error': 'db_manager not available'}

        memories = self.db_manager.load_memories_by_criteria(
            memory_type='persona',
            limit=limit
        )

        summaries = [memory.to_dict() for memory in memories[:limit]]
        return {
            'recent_persona_memories': summaries,
            'count': len(summaries)
        }

    async def _summarize_persona_profile(self) -> Dict[str, Any]:
        if not self.db_manager:
            return {'error': 'db_manager not available'}

        memories = self.db_manager.load_memories_by_criteria(memory_type='persona')
        preference_counter = {}
        value_counter = {}

        for memory in memories:
            metadata = memory.metadata or {}
            pref_type = metadata.get('preference_type')
            value_alignment = metadata.get('value_alignment')
            if pref_type:
                preference_counter[pref_type] = preference_counter.get(pref_type, 0) + 1
            if value_alignment:
                value_counter[value_alignment] = value_counter.get(value_alignment, 0) + 1

        return {
            'preferences': preference_counter,
            'value_alignment': value_counter,
            'total_persona_memories': len(memories)
        }

    async def _find_duplicate_persona(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        from ...memory.memory_system import memory_system

        try:
            results = await memory_system.search_memories(
                payload['content'],
                search_type='semantic',
                k=5,
                threshold=0.25
            )
        except Exception:
            return None

        best_candidate = None
        best_similarity = 0.0
        for item in results:
            if item.get('memory_type') != 'persona' and 'persona' not in set(item.get('context_tags', [])):
                continue
            similarity = item.get('similarity_score', 0.0)
            if similarity > best_similarity and similarity >= 0.85:
                best_similarity = similarity
                best_candidate = {'memory_id': item['id'], 'similarity': similarity}
        return best_candidate

    async def _merge_persona_memory(self, memory_id: str, payload: Dict[str, Any], similarity: float) -> Dict[str, Any]:
        if not self.db_manager:
            return {'error': 'db_manager not available', 'memory_id': memory_id}

        existing = self.db_manager.load_memory(memory_id)
        if not existing:
            return {'error': 'existing memory not found', 'memory_id': memory_id}

        updated = False

        # Merge context tags
        existing_tags = set(existing.context_tags or [])
        new_tags = set(payload.get('context_tags', []))
        merged_tags = existing_tags | new_tags
        if merged_tags != existing_tags:
            existing.context_tags = list(merged_tags)
            updated = True

        # Merge emotion tags
        existing_emotions = set(existing.emotion_tags or [])
        new_emotions = set(payload.get('emotion_tags', []))
        merged_emotions = existing_emotions | new_emotions
        if merged_emotions != existing_emotions:
            existing.emotion_tags = list(merged_emotions)
            updated = True

        # Merge metadata and repeat history
        metadata = deepcopy(existing.metadata or {})
        incoming_metadata = payload.get('metadata', {}) or {}

        history = list(metadata.get('repeat_history', []))
        history.append({
            'timestamp': datetime.now().isoformat(),
            'content': payload.get('content', '')
        })
        metadata['repeat_history'] = history
        metadata['repeat_count'] = len(history)

        for key, value in incoming_metadata.items():
            if key not in metadata:
                metadata[key] = value
            else:
                if isinstance(value, list) and isinstance(metadata[key], list):
                    # Filter out non-hashable items for deduplication
                    hashable_items = []
                    non_hashable_items = []
                    all_items = metadata[key] + value

                    for item in all_items:
                        try:
                            hash(item)
                            hashable_items.append(item)
                        except TypeError:
                            non_hashable_items.append(item)

                    # Deduplicate hashable items and append non-hashable items
                    merged_list = list(dict.fromkeys(hashable_items)) + non_hashable_items
                    metadata[key] = merged_list
                elif isinstance(value, dict) and isinstance(metadata[key], dict):
                    metadata[key].update(value)
                else:
                    metadata[f"alt_{key}"] = value
        existing.metadata = metadata
        updated = True

        # Importance & consolidation boost
        importance_boost = max(0.03, (1 - similarity) * 0.12)
        proposed_importance = payload.get('importance', existing.importance)
        existing.importance = min(1.0, max(existing.importance, proposed_importance) + importance_boost)
        existing.consolidation_level = min(3, existing.consolidation_level + 1)
        existing.access_frequency += 1
        existing.last_accessed = datetime.now()
        updated = True

        if updated:
            self.db_manager.save_memory(existing)
            logger.debug(
                "🔁 Persona memory merged into %s (similarity %.3f, importance %.2f)",
                memory_id,
                similarity,
                existing.importance
            )

        await self._link_related_persona_memories(memory_id)

        return {
            'memory_id': memory_id,
            'merged': True,
            'duplicate_similarity': similarity,
            'updated_importance': existing.importance,
            'consolidation_level': existing.consolidation_level
        }

    async def _link_related_persona_memories(self, memory_id: str):
        if not self.db_manager or not self.vector_db:
            return

        memory = self.db_manager.load_memory(memory_id)
        if not memory or memory.embedding is None:
            return

        similar = self.vector_db.search(memory.embedding, k=5, threshold=0.35)
        associations = []
        for other_id, score in similar:
            if other_id == memory_id:
                continue
            other = self.db_manager.load_memory(other_id)
            if not other:
                continue
            if other.memory_type != 'persona' and 'persona' not in set(other.context_tags or []):
                continue
            associations.append(other_id)

        if associations:
            memory.associations = list(dict.fromkeys((memory.associations or []) + associations))
            self.db_manager.save_memory(memory)

    def _initialize_repeat_metadata(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        metadata = deepcopy(memory.get('metadata', {}) or {})
        history = list(metadata.get('repeat_history', []))
        history.append({
            'timestamp': datetime.now().isoformat(),
            'content': memory.get('content', '')
        })
        metadata['repeat_history'] = history
        metadata['repeat_count'] = len(history)
        return metadata
