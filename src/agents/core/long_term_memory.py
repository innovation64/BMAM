"""
Long-term Memory Agent
长期记忆智能体 - 对应新皮层的分布式存储
"""

from collections import defaultdict
from typing import Dict, Any, List, Optional
import logging
import asyncio
from copy import deepcopy
from datetime import datetime

from ..base import BrainAgent, AgentMessage, BrainRegion
from ...memory.memory_item import MemoryItem

logger = logging.getLogger(__name__)


class LongTermMemoryAgent(BrainAgent):
    """
    Long-term Memory Agent (Neocortex - Distributed Storage)
    
    核心概念：长期
    对应脑区：新皮层（Neocortex）
    主要功能：永久存储，知识图谱，语义网络维护
    """
    
    def __init__(self, db_manager=None, embedding_service=None, vector_db=None):
        super().__init__(
            agent_id="long_term_memory",
            brain_region=BrainRegion.NEOCORTEX,
            system_prompt="""You organize permanent memories into semantic networks.
            Create meaningful associations and ensure memory integrity through consolidation."""
        )
        
        # External services (injected for modularity)
        self.db_manager = db_manager
        self.embedding_service = embedding_service
        self.vector_db = vector_db
        
        # Semantic network for associations
        self.semantic_network = defaultdict(list)
        
        # Memory categories and hierarchies
        self.memory_categories = defaultdict(list)
        self.memory_hierarchy = {}
        
        # Statistics
        self.total_memories = 0
        self.consolidation_count = 0
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process incoming messages for long-term memory operations"""
        action = message.content.get('action')
        
        if action == 'store_long_term':
            memory_content = message.content.get('memory', {}).get('content', 'N/A')
            logger.debug(f"🧠 LongTermMemoryAgent: storing memory content='{memory_content[:50]}...'")
            return await self._store_long_term_memory(message.content['memory'])
        elif action == 'build_associations':
            return await self._build_semantic_associations(message.content['memory_id'])
        elif action == 'strengthen_memory':
            return await self._strengthen_memory_trace(message.content['memory_id'])
        elif action == 'organize_knowledge':
            return await self._organize_knowledge_structure()
        elif action == 'retrieve_semantic':
            return await self._retrieve_by_semantic_similarity(message.content['query'])
        elif action == 'update_hierarchy':
            return await self._update_memory_hierarchy(message.content['memory_id'])
        
        return {'error': f'Unknown action: {action}'}
    
    async def _store_long_term_memory(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store memory in long-term storage with semantic encoding - 统一使用memory_system"""
        
        # 调用统一的memory_system，确保向量库与数据库同步更新
        from ...memory.memory_system import memory_system
        
        memory_payload = deepcopy(memory_data)
        memory_payload['metadata'] = self._initialize_repeat_metadata(memory_payload)

        duplicate_check = await self._find_duplicate_memory(memory_payload)
        if duplicate_check and duplicate_check.get('memory_id'):
            merged_result = await self._merge_with_existing_memory(
                duplicate_check['memory_id'],
                memory_payload,
                duplicate_check.get('similarity', 0.0)
            )
            merged_result['stored'] = False
            merged_result['duplicate_detected'] = True
            return merged_result

        memory_id = await memory_system.store_memory(
            content=memory_payload['content'],
            memory_type=memory_payload.get('memory_type', 'semantic'), 
            importance=memory_payload.get('importance', 0.5),
            emotion_tags=memory_payload.get('emotion_tags', []),
            context_tags=memory_payload.get('context_tags', []),
            metadata=memory_payload.get('metadata', {})
        )
        
        success = memory_id is not None
        
        if success:
            self.total_memories += 1
            logger.info(f"✅ Successfully stored memory {memory_id} via memory_system: '{memory_payload['content'][:50]}...'")
            
            # Build initial associations - 使用返回的memory_id
            await self._build_semantic_associations(memory_id)
        else:
            logger.error(f"❌ Failed to store memory via memory_system: '{memory_payload['content'][:50]}...'")
            memory_id = "failed"
        
        return {
            'stored': success,
            'memory_id': memory_id,
            'memory_type': memory_payload.get('memory_type', 'semantic'),
            'consolidation_level': memory_payload.get('consolidation_level', 1),
            'total_memories': self.total_memories,
            'duplicate_detected': False
        }
    
    def _is_preference_update(self, old_content: str, new_content: str) -> bool:
        """判断新内容是否为偏好更新而非完全重复"""
        # 提取偏好关键词
        preference_patterns = ['喜欢', '偏好', '习惯', '通常', '经常']

        old_has_preference = any(pattern in old_content for pattern in preference_patterns)
        new_has_preference = any(pattern in new_content for pattern in preference_patterns)

        if not (old_has_preference and new_has_preference):
            return False

        # 提取实体（简单实现：提取名词）
        def extract_entities(text):
            # 移除偏好词和标点，提取剩余实体
            for pattern in preference_patterns + ['我', '用户', '：', '。', '，']:
                text = text.replace(pattern, ' ')
            return set([word.strip() for word in text.split() if len(word.strip()) > 1])

        old_entities = extract_entities(old_content)
        new_entities = extract_entities(new_content)

        # 如果有新的实体出现，说明是偏好更新
        return len(new_entities - old_entities) > 0

    async def _build_semantic_associations(self, memory_id: str) -> Dict[str, Any]:
        """Build semantic associations between memories"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        memory = self.db_manager.load_memory(memory_id)
        if not memory:
            return {'error': 'Memory not found'}
        
        associations = []
        
        # Find semantically similar memories using vector search
        if memory.embedding is not None and self.vector_db:
            similar_memories = self.vector_db.search(
                memory.embedding, 
                k=5, 
                threshold=0.4
            )
            
            # Update associations
            associations = [mem_id for mem_id, score in similar_memories 
                          if mem_id != memory_id]
            memory.associations = associations
            
            # Save updated memory
            self.db_manager.save_memory(memory)
            
            # Update bidirectional semantic network
            self.semantic_network[memory_id].extend(associations)
            for assoc_id in associations:
                if memory_id not in self.semantic_network[assoc_id]:
                    self.semantic_network[assoc_id].append(memory_id)
        
        # Build conceptual associations in background (non-blocking)
        asyncio.create_task(self._find_conceptual_links_background(memory, memory.id))
        # Continue without waiting for conceptual links to avoid blocking

        return {
            'associations_built': len(associations),
            'semantic_links': len([a for a in associations if a in self.semantic_network[memory_id]]),
            # 概念链接在后台异步计算，这里不返回数量以避免未定义变量
            'network_size': len(self.semantic_network)
        }

    async def _find_duplicate_memory(self, memory_data: Dict[str, Any], similarity_threshold: float = 0.95) -> Optional[Dict[str, Any]]:
        """Search existing memories to avoid storing near-duplicates."""

        if not memory_data.get('content'):
            return None

        try:
            from ...memory.memory_system import memory_system
        except Exception as exc:
            logger.warning(f"Unable to import memory_system for duplicate check: {exc}")
            return None

        try:
            search_results = await memory_system.search_memories(
                memory_data['content'],
                search_type='semantic',
                k=5,
                threshold=0.4
            )
        except Exception as exc:
            logger.warning(f"Duplicate search failed: {exc}")
            return None

        candidate = None
        highest_similarity = 0.0

        for item in search_results:
            similarity = item.get('similarity_score', 0.0)
            if similarity >= similarity_threshold and item.get('memory_type') == memory_data.get('memory_type', 'semantic'):
                if similarity > highest_similarity:
                    highest_similarity = similarity
                    candidate = {'memory_id': item['id'], 'similarity': similarity}
        
        return candidate

    async def _merge_with_existing_memory(self, memory_id: str, new_data: Dict[str, Any], similarity: float) -> Dict[str, Any]:
        """Merge new memory data into an existing record when a duplicate is detected."""

        if not self.db_manager:
            logger.warning("Duplicate detected but db_manager unavailable; skipping merge")
            return {'error': 'db_manager not available', 'memory_id': memory_id}

        existing = self.db_manager.load_memory(memory_id)
        if not existing:
            return {'error': 'existing memory not found', 'memory_id': memory_id}

        updated = False

        # Merge emotion tags
        new_emotions = set(existing.emotion_tags or []) | set(new_data.get('emotion_tags', []))
        if new_emotions != set(existing.emotion_tags or []):
            existing.emotion_tags = list(new_emotions)
            updated = True

        # Merge context tags
        new_context = set(existing.context_tags or []) | set(new_data.get('context_tags', []))
        if new_context != set(existing.context_tags or []):
            existing.context_tags = list(new_context)
            updated = True

        # Merge metadata (shallow merge, new values take precedence)
        metadata = deepcopy(existing.metadata or {})
        incoming_metadata = new_data.get('metadata', {}) or {}

        repeat_entry = {
            'timestamp': datetime.now().isoformat(),
            'content': new_data.get('content', '')
        }
        repeat_history = list(metadata.get('repeat_history', []))
        repeat_history.append(repeat_entry)
        metadata['repeat_history'] = repeat_history
        metadata['repeat_count'] = len(repeat_history)
        updated = True

        if incoming_metadata:
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

                        # Deduplicate hashable items and combine with non-hashable
                        combined = list(dict.fromkeys(hashable_items)) + non_hashable_items
                        metadata[key] = combined
                    elif isinstance(value, dict) and isinstance(metadata[key], dict):
                        metadata[key].update(value)
                    else:
                        metadata[f"alt_{key}"] = value
            updated = True

        existing.metadata = metadata

        # Track content variants when not identical - with temporal tracking
        new_content = new_data.get('content', '').strip()
        if new_content and new_content != (existing.content or '').strip():
            existing.metadata = existing.metadata or {}

            # Enhanced: track variants with timestamps for temporal reasoning
            variants = existing.metadata.get('content_variants', [])
            if new_content not in [v.get('content') if isinstance(v, dict) else v for v in variants]:
                variant_entry = {
                    'content': new_content,
                    'timestamp': datetime.now().isoformat(),
                    'is_update': self._is_preference_update(existing.content, new_content)
                }
                variants = list(variants) + [variant_entry]
                existing.metadata['content_variants'] = variants

                # If this is a preference update, mark the latest one
                if variant_entry['is_update']:
                    existing.metadata['latest_preference'] = new_content
                    existing.metadata['preference_updated_at'] = variant_entry['timestamp']
                    # Update the main content to reflect latest preference
                    existing.content = f"{existing.content} | 最新偏好：{new_content}"
                    logger.info(f"🔄 Preference updated: {existing.content[:80]}")

                updated = True

        # Boost importance when duplicate encountered frequently
        importance_boost = max(0.02, (1 - similarity) * 0.1)
        proposed_importance = new_data.get('importance', existing.importance)
        new_importance = max(existing.importance, proposed_importance) + importance_boost
        existing.importance = min(1.0, new_importance)

        # Increase consolidation level mildly to reflect reinforcement
        existing.consolidation_level = min(3, existing.consolidation_level + 1)
        existing.access_frequency += 1
        existing.last_accessed = datetime.now()
        updated = True

        if updated:
            self.db_manager.save_memory(existing)

        logger.info(
            "🔁 Duplicate memory merged into %s (similarity %.3f, importance %.2f)",
            memory_id,
            similarity,
            existing.importance
        )

        return {
            'memory_id': memory_id,
            'merged': True,
            'updated_importance': existing.importance,
            'consolidation_level': existing.consolidation_level,
            'duplicate_similarity': similarity
        }

    def _initialize_repeat_metadata(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize repeat tracking metadata for new memories."""

        metadata = deepcopy(memory_data.get('metadata', {}) or {})
        history = list(metadata.get('repeat_history', []))
        history.append({
            'timestamp': datetime.now().isoformat(),
            'content': memory_data.get('content', '')
        })
        metadata['repeat_history'] = history
        metadata['repeat_count'] = len(history)
        return metadata
    
    async def _strengthen_memory_trace(self, memory_id: str) -> Dict[str, Any]:
        """Strengthen memory trace through repeated activation"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        memory = self.db_manager.load_memory(memory_id)
        if not memory:
            return {'error': 'Memory not found'}
        
        # Hebbian learning: "Neurons that fire together, wire together"
        old_consolidation = memory.consolidation_level
        
        # Increase consolidation level
        memory.consolidation_level = min(3, memory.consolidation_level + 1)
        memory.access_frequency += 1
        
        # Reduce decay rate as memory strengthens (LTP simulation)
        memory.decay_rate = max(0.01, memory.decay_rate * 0.9)
        
        # Update importance based on access pattern
        access_boost = min(0.2, memory.access_frequency * 0.02)
        memory.importance = min(1.0, memory.importance + access_boost)
        
        self.db_manager.save_memory(memory)
        
        # Strengthen associated memories (spreading activation)
        strengthened_associations = 0
        for assoc_id in memory.associations[:3]:  # Top 3 associations
            assoc_memory = self.db_manager.load_memory(assoc_id)
            if assoc_memory:
                assoc_memory.importance = min(1.0, assoc_memory.importance + 0.05)
                self.db_manager.save_memory(assoc_memory)
                strengthened_associations += 1
        
        return {
            'strengthened': True,
            'memory_id': memory_id,
            'old_consolidation': old_consolidation,
            'new_consolidation': memory.consolidation_level,
            'access_frequency': memory.access_frequency,
            'decay_rate': memory.decay_rate,
            'strengthened_associations': strengthened_associations
        }
    
    async def _organize_knowledge_structure(self) -> Dict[str, Any]:
        """Organize memories into hierarchical knowledge structures"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        # Load all semantic memories
        semantic_memories = self.db_manager.load_memories_by_criteria(
            memory_type='semantic'
        )
        
        # Build category hierarchy
        hierarchy = {
            'concepts': defaultdict(list),
            'facts': defaultdict(list),
            'procedures': defaultdict(list),
            'episodes': defaultdict(list)
        }
        
        for memory in semantic_memories:
            # Categorize by content type
            if 'concept' in memory.metadata.get('type', ''):
                hierarchy['concepts'][memory.context_tags[0] if memory.context_tags else 'general'].append(memory.id)
            elif 'fact' in memory.metadata.get('type', ''):
                hierarchy['facts'][memory.context_tags[0] if memory.context_tags else 'general'].append(memory.id)
            elif 'procedure' in memory.metadata.get('type', ''):
                hierarchy['procedures'][memory.context_tags[0] if memory.context_tags else 'general'].append(memory.id)
            else:
                hierarchy['episodes'][memory.context_tags[0] if memory.context_tags else 'general'].append(memory.id)
        
        self.memory_hierarchy = hierarchy
        
        # Calculate statistics
        total_organized = sum(
            len(items) for category in hierarchy.values() 
            for items in category.values()
        )
        
        return {
            'organized': True,
            'total_memories': len(semantic_memories),
            'organized_memories': total_organized,
            'categories': {
                'concepts': len(hierarchy['concepts']),
                'facts': len(hierarchy['facts']),
                'procedures': len(hierarchy['procedures']),
                'episodes': len(hierarchy['episodes'])
            }
        }
    
    async def _retrieve_by_semantic_similarity(self, query: str) -> Dict[str, Any]:
        """Retrieve memories by semantic similarity"""
        
        if not self.embedding_service or not self.vector_db:
            return {'error': 'Embedding service or vector database not available'}
        
        # Generate query embedding
        query_embedding = await self.embedding_service.encode_text(query)
        
        # Search for similar memories
        similar_memories = self.vector_db.search(
            query_embedding,
            k=10,
            threshold=0.3
        )
        
        results = []
        if self.db_manager:
            for memory_id, similarity in similar_memories:
                memory = self.db_manager.load_memory(memory_id)
                if memory:
                    results.append({
                        'memory': memory.to_dict(),
                        'similarity': similarity,
                        'consolidation': memory.consolidation_level,
                        'importance': memory.importance
                    })
        
        # Sort by combined score
        results.sort(
            key=lambda x: x['similarity'] * 0.5 + x['importance'] * 0.3 + x['consolidation'] / 3 * 0.2,
            reverse=True
        )
        
        return {
            'retrieved': True,
            'query': query,
            'results': results,
            'count': len(results)
        }
    
    async def _update_memory_hierarchy(self, memory_id: str) -> Dict[str, Any]:
        """Update memory's position in the knowledge hierarchy"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        memory = self.db_manager.load_memory(memory_id)
        if not memory:
            return {'error': 'Memory not found'}
        
        # Determine hierarchical position based on associations
        hierarchy_level = 'leaf'  # Default to leaf node
        
        # Check if memory is referenced by others (makes it higher level)
        referencing_count = sum(
            1 for assocs in self.semantic_network.values() 
            if memory_id in assocs
        )
        
        if referencing_count > 5:
            hierarchy_level = 'branch'
        if referencing_count > 10:
            hierarchy_level = 'trunk'
        if memory.importance > 0.8 and referencing_count > 15:
            hierarchy_level = 'root'
        
        # Update metadata
        memory.metadata['hierarchy_level'] = hierarchy_level
        memory.metadata['reference_count'] = referencing_count
        
        self.db_manager.save_memory(memory)
        
        return {
            'updated': True,
            'memory_id': memory_id,
            'hierarchy_level': hierarchy_level,
            'reference_count': referencing_count
        }
    
    async def _find_conceptual_links(self, memory: MemoryItem) -> List[str]:
        """Find conceptual links based on content analysis"""
        
        # Use LLM to identify key concepts
        prompt = f"Identify 3 key concepts in: {memory.content}"
        concepts = await self.call_llm(prompt, quick_fail=True)
        
        # Parse concepts and find related memories
        conceptual_links = []
        
        # This would search for memories with similar concepts
        # Implementation depends on available search capabilities
        
        return conceptual_links
    
    async def _find_conceptual_links_background(self, memory: MemoryItem, memory_id: str):
        """Find conceptual links in background without blocking main flow"""
        try:
            conceptual_links = await self._find_conceptual_links(memory)
            # Update semantic network with discovered links
            for link in conceptual_links:
                if link not in self.semantic_network[memory_id]:
                    self.semantic_network[memory_id].append(link)
        except Exception as e:
            # Silent fail in background - don't disrupt main flow
            pass
    
    def _categorize_memory(self, memory: MemoryItem):
        """Categorize memory for efficient retrieval"""
        
        # Add to category index
        self.memory_categories[memory.memory_type].append(memory.id)
        
        # Add to context-based categories
        for context_tag in memory.context_tags:
            self.memory_categories[f"context_{context_tag}"].append(memory.id)
        
        # Add to emotion-based categories
        for emotion_tag in memory.emotion_tags:
            self.memory_categories[f"emotion_{emotion_tag}"].append(memory.id)
        
        # Add to importance-based categories
        if memory.importance > 0.8:
            self.memory_categories['high_importance'].append(memory.id)
        elif memory.importance > 0.5:
            self.memory_categories['medium_importance'].append(memory.id)
        else:
            self.memory_categories['low_importance'].append(memory.id)
