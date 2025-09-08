"""
Long-term Memory Agent
长期记忆智能体 - 对应新皮层的分布式存储
"""

from collections import defaultdict
from typing import Dict, Any, List, Optional
import logging

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
            system_prompt="""You are the long-term memory system of a brain-inspired AI.
            Your role is to:
            1. Store and organize permanent memories in distributed semantic networks
            2. Build and maintain knowledge graphs
            3. Create semantic associations between memories
            4. Manage memory consolidation from short-term to long-term
            5. Maintain memory integrity and prevent degradation"""
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
        """Store memory in long-term storage with semantic encoding"""
        
        # Create memory item
        memory = MemoryItem(
            content=memory_data['content'],
            memory_type=memory_data.get('memory_type', 'semantic'),
            brain_region=BrainRegion.NEOCORTEX,
            importance=memory_data.get('importance', 0.5),
            consolidation_level=memory_data.get('consolidation_level', 1),
            emotion_tags=memory_data.get('emotion_tags', []),
            context_tags=memory_data.get('context_tags', [])
        )
        
        # Generate embedding if embedding service is available
        if self.embedding_service:
            memory.embedding = await self.embedding_service.encode_text(memory.content)
            
            # Add to vector database if available
            if self.vector_db:
                embedding_id = self.vector_db.add_vector(memory.id, memory.embedding)
                memory.embedding_id = str(embedding_id)
        
        # Save to persistent storage if available
        success = False
        if self.db_manager:
            success = self.db_manager.save_memory(memory)
            
            if success and self.vector_db:
                self.vector_db.save_index()
        else:
            # Fallback: store in local structure
            self.memory_categories[memory.memory_type].append(memory)
            success = True
        
        if success:
            self.total_memories += 1
            
            # Build initial associations
            await self._build_semantic_associations(memory.id)
            
            # Categorize memory
            self._categorize_memory(memory)
        
        return {
            'stored': success,
            'memory_id': memory.id,
            'memory_type': memory.memory_type,
            'consolidation_level': memory.consolidation_level,
            'total_memories': self.total_memories
        }
    
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
        
        # Build conceptual associations
        conceptual_links = await self._find_conceptual_links(memory)
        associations.extend(conceptual_links)
        
        return {
            'associations_built': len(associations),
            'semantic_links': len([a for a in associations if a in self.semantic_network[memory_id]]),
            'conceptual_links': len(conceptual_links),
            'network_size': len(self.semantic_network)
        }
    
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
        concepts = await self.call_llm(prompt)
        
        # Parse concepts and find related memories
        conceptual_links = []
        
        # This would search for memories with similar concepts
        # Implementation depends on available search capabilities
        
        return conceptual_links
    
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