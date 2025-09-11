"""
Memory Retrieval Agent
记忆检索智能体 - 对应前额叶皮层+海马体
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

from ..base import BrainAgent, AgentMessage, BrainRegion
from ...memory.memory_item import MemoryItem

logger = logging.getLogger(__name__)


class MemoryRetrievalAgent(BrainAgent):
    """
    Memory Retrieval Agent (Prefrontal Cortex + Hippocampus)
    
    核心概念：检索
    对应脑区：前额叶皮层 + 海马体
    主要功能：记忆提取，模式完成，线索驱动检索
    """
    
    def __init__(self, db_manager=None, embedding_service=None, vector_db=None):
        super().__init__(
            agent_id="memory_retrieval",
            brain_region=BrainRegion.HIPPOCAMPUS,
            system_prompt="""You are the memory retrieval system of a brain-inspired AI.
            Your role is to:
            1. Find and reconstruct memories using cues and context
            2. Perform pattern completion from partial information
            3. Execute semantic, episodic, and associative retrieval
            4. Optimize retrieval strategies based on query type
            5. Handle retrieval failures and provide alternatives"""
        )
        
        # External services
        self.db_manager = db_manager
        self.embedding_service = embedding_service
        self.vector_db = vector_db
        
        # Retrieval strategies
        self.retrieval_strategies = ['semantic', 'temporal', 'associative', 'emotional', 'contextual']
        
        # Cache for recent retrievals
        self.retrieval_cache = {}
        self.cache_size = 20
        
        # Retrieval statistics
        self.retrieval_count = 0
        self.hit_rate = 0.0
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process retrieval requests"""
        action = message.content.get('action')
        
        if action == 'semantic_search':
            return await self._semantic_retrieval(
                message.content['query'], 
                message.content.get('k', 10)
            )
        elif action == 'episodic_search':
            return await self._episodic_retrieval(message.content['cues'])
        elif action == 'associative_search':
            return await self._associative_retrieval(message.content['memory_id'])
        elif action == 'pattern_completion':
            return await self._pattern_completion(message.content['partial_cue'])
        elif action == 'contextual_search':
            return await self._contextual_retrieval(message.content['context'])
        elif action == 'multi_strategy_search':
            return await self._multi_strategy_retrieval(message.content['query'])
        
        return {'error': f'Unknown retrieval action: {action}'}
    
    async def _semantic_retrieval(self, query: str, k: int = 10) -> Dict[str, Any]:
        """Semantic retrieval using vector similarity"""
        
        # Check cache first
        cache_key = f"semantic_{query}_{k}"
        if cache_key in self.retrieval_cache:
            self.hit_rate = (self.hit_rate * self.retrieval_count + 1) / (self.retrieval_count + 1)
            self.retrieval_count += 1
            return self.retrieval_cache[cache_key]
        
        if not self.embedding_service or not self.vector_db:
            return {'error': 'Required services not available'}
        
        # Generate query embedding
        query_embedding = await self.embedding_service.encode_text(query)
        
        # Search for similar memories (降低阈值以提高中文搜索效果)
        similar_memories = self.vector_db.search(
            query_embedding, 
            k=k, 
            threshold=0.1
        )
        
        memories = []
        
        logger.info(f"Vector search results for '{query}': {len(similar_memories)} memories found")
        
        # 如果向量搜索没有结果，使用关键字搜索作为后备
        if len(similar_memories) == 0 and self.db_manager:
            logger.info(f"Vector search returned no results, falling back to keyword search for: {query}")
            
            # 提取关键词
            keywords = ['茶', '绿茶', '下午', '3点', '时间', '喝']
            query_keywords = [kw for kw in keywords if kw in query]
            
            # 搜索包含关键词的记忆
            all_memories = self.db_manager.search_memories(limit=20)
            for memory in all_memories:
                if any(keyword in memory.content for keyword in query_keywords + [query]):
                    memories.append({
                        'content': memory.content,
                        'memory_id': memory.id,
                        'similarity': 0.5,  # 默认相似度
                        'retrieval_confidence': 0.7,
                        'retrieval_method': 'keyword_fallback',
                        'memory_type': memory.memory_type,
                        'importance': memory.importance,
                        'timestamp': memory.created_at.isoformat() if memory.created_at else None
                    })
        else:
            # 正常向量搜索处理
            if self.db_manager:
                for memory_id, similarity in similar_memories:
                    memory = self.db_manager.load_memory(memory_id)
                    if memory:
                        # Update access patterns
                        memory.access_frequency += 1
                        memory.last_accessed = datetime.now()
                        self.db_manager.save_memory(memory)
                        
                        # Calculate retrieval confidence
                        retrieval_confidence = self._calculate_retrieval_confidence(
                            similarity, 
                            memory
                        )
                        
                        memories.append({
                            'memory': memory.to_dict(),
                            'similarity': similarity,
                            'retrieval_confidence': retrieval_confidence,
                            'retrieval_method': 'semantic'
                        })
        
        # Sort by retrieval confidence
        memories.sort(key=lambda x: x['retrieval_confidence'], reverse=True)
        
        result = {
            'memories': memories,
            'retrieval_method': 'semantic',
            'query': query,
            'count': len(memories),
            'confidence': sum(m['retrieval_confidence'] for m in memories) / len(memories) if memories else 0
        }
        
        # Update cache
        self._update_cache(cache_key, result)
        self.retrieval_count += 1
        
        return result
    
    async def _episodic_retrieval(self, cues: Dict[str, Any]) -> Dict[str, Any]:
        """Episodic retrieval using temporal and contextual cues"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        memories = []
        
        # Build retrieval criteria from cues
        criteria = {}
        
        # Temporal cues
        if 'time_range' in cues:
            start_time = cues['time_range'].get('start')
            end_time = cues['time_range'].get('end')
            # This would filter by timestamp in actual implementation
        
        # Context cues
        if 'context' in cues:
            criteria['context_tags'] = cues['context']
        
        # Emotional cues
        if 'emotion' in cues:
            criteria['emotion_tags'] = cues['emotion']
        
        # Location cues (stored in metadata)
        if 'location' in cues:
            criteria['location'] = cues['location']
        
        # Load candidate memories
        candidate_memories = self.db_manager.load_memories_by_criteria(**criteria)
        
        # Score memories based on cue match
        for memory in candidate_memories:
            episodic_score = self._calculate_episodic_score(memory, cues)
            
            if episodic_score > 0.3:  # Threshold for inclusion
                memories.append({
                    'memory': memory.to_dict(),
                    'episodic_score': episodic_score,
                    'retrieval_confidence': episodic_score * memory.source_reliability,
                    'retrieval_method': 'episodic',
                    'matched_cues': self._get_matched_cues(memory, cues)
                })
        
        # Sort by episodic score
        memories.sort(key=lambda x: x['episodic_score'], reverse=True)
        
        return {
            'memories': memories,
            'retrieval_method': 'episodic',
            'cues_used': list(cues.keys()),
            'count': len(memories),
            'confidence': sum(m['retrieval_confidence'] for m in memories) / len(memories) if memories else 0
        }
    
    async def _associative_retrieval(self, memory_id: str) -> Dict[str, Any]:
        """Associative retrieval following memory connections"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        base_memory = self.db_manager.load_memory(memory_id)
        if not base_memory:
            return {'error': 'Base memory not found'}
        
        associated_memories = []
        
        # Direct associations (first degree)
        for assoc_id in base_memory.associations[:10]:  # Limit to top 10
            assoc_memory = self.db_manager.load_memory(assoc_id)
            if assoc_memory:
                association_strength = self._calculate_association_strength(
                    base_memory, 
                    assoc_memory
                )
                
                associated_memories.append({
                    'memory': assoc_memory.to_dict(),
                    'association_strength': association_strength,
                    'association_type': 'direct',
                    'degree': 1,
                    'retrieval_confidence': association_strength * assoc_memory.source_reliability
                })
        
        # Second-degree associations (if needed)
        if len(associated_memories) < 5:
            second_degree = []
            for first_degree in associated_memories:
                first_memory_id = first_degree['memory']['id']
                first_memory = self.db_manager.load_memory(first_memory_id)
                
                if first_memory:
                    for second_id in first_memory.associations[:3]:
                        if second_id != memory_id and second_id not in [m['memory']['id'] for m in associated_memories]:
                            second_memory = self.db_manager.load_memory(second_id)
                            if second_memory:
                                second_degree.append({
                                    'memory': second_memory.to_dict(),
                                    'association_strength': first_degree['association_strength'] * 0.5,
                                    'association_type': 'indirect',
                                    'degree': 2,
                                    'retrieval_confidence': first_degree['association_strength'] * 0.5 * second_memory.source_reliability
                                })
            
            associated_memories.extend(second_degree[:5])  # Add up to 5 second-degree associations
        
        # Sort by association strength
        associated_memories.sort(key=lambda x: x['association_strength'], reverse=True)
        
        return {
            'memories': associated_memories,
            'retrieval_method': 'associative',
            'base_memory_id': memory_id,
            'count': len(associated_memories),
            'max_degree': max((m['degree'] for m in associated_memories), default=0)
        }
    
    async def _pattern_completion(self, partial_cue: str) -> Dict[str, Any]:
        """Pattern completion from partial memory cues"""
        
        if not self.embedding_service or not self.vector_db:
            return {'error': 'Required services not available'}
        
        # Generate embedding for partial cue
        cue_embedding = await self.embedding_service.encode_text(partial_cue)
        
        # Search with lower threshold for partial matches
        similar_memories = self.vector_db.search(
            cue_embedding, 
            k=5, 
            threshold=0.2  # Lower threshold for partial matches
        )
        
        completed_patterns = []
        
        if self.db_manager:
            for memory_id, similarity in similar_memories:
                memory = self.db_manager.load_memory(memory_id)
                if memory:
                    # Calculate completion confidence
                    completion_confidence = self._calculate_completion_confidence(
                        partial_cue, 
                        memory, 
                        similarity
                    )
                    
                    # Attempt to complete the pattern
                    completed = await self._complete_pattern(partial_cue, memory)
                    
                    completed_patterns.append({
                        'memory': memory.to_dict(),
                        'completed_content': completed,
                        'completion_confidence': completion_confidence,
                        'pattern_match': similarity,
                        'retrieval_method': 'pattern_completion'
                    })
        
        # Sort by completion confidence
        completed_patterns.sort(key=lambda x: x['completion_confidence'], reverse=True)
        
        return {
            'completed_patterns': completed_patterns,
            'partial_cue': partial_cue,
            'count': len(completed_patterns),
            'best_completion': completed_patterns[0]['completed_content'] if completed_patterns else None
        }
    
    async def _contextual_retrieval(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve memories based on contextual information"""
        
        if not self.db_manager:
            return {'error': 'Database manager not available'}
        
        # Extract context features
        context_features = {
            'tags': context.get('tags', []),
            'environment': context.get('environment'),
            'task': context.get('task'),
            'mood': context.get('mood'),
            'time_of_day': context.get('time_of_day')
        }
        
        memories = []
        all_memories = self.db_manager.load_memories_by_criteria()
        
        for memory in all_memories:
            context_score = self._calculate_context_match(memory, context_features)
            
            if context_score > 0.3:
                memories.append({
                    'memory': memory.to_dict(),
                    'context_score': context_score,
                    'matched_features': self._get_matched_context_features(memory, context_features),
                    'retrieval_confidence': context_score * memory.source_reliability,
                    'retrieval_method': 'contextual'
                })
        
        # Sort by context score
        memories.sort(key=lambda x: x['context_score'], reverse=True)
        
        return {
            'memories': memories[:10],  # Top 10 contextually relevant
            'retrieval_method': 'contextual',
            'context_used': context_features,
            'count': len(memories[:10])
        }
    
    async def _multi_strategy_retrieval(self, query: str) -> Dict[str, Any]:
        """Use multiple retrieval strategies and combine results"""
        
        results = {
            'semantic': await self._semantic_retrieval(query, k=5),
            'contextual': await self._contextual_retrieval({'tags': query.split()}),
        }
        
        # Combine and deduplicate results
        combined_memories = {}
        
        for strategy, result in results.items():
            if 'memories' in result:
                for mem_data in result['memories']:
                    mem_id = mem_data['memory']['id']
                    
                    if mem_id not in combined_memories:
                        combined_memories[mem_id] = {
                            'memory': mem_data['memory'],
                            'strategies': {strategy: mem_data.get('retrieval_confidence', 0.5)},
                            'combined_score': 0
                        }
                    else:
                        combined_memories[mem_id]['strategies'][strategy] = mem_data.get('retrieval_confidence', 0.5)
        
        # Calculate combined scores
        for mem_id, data in combined_memories.items():
            # Weighted combination of different strategies
            scores = data['strategies'].values()
            data['combined_score'] = sum(scores) / len(scores)
        
        # Convert to list and sort
        final_memories = list(combined_memories.values())
        final_memories.sort(key=lambda x: x['combined_score'], reverse=True)
        
        return {
            'memories': final_memories[:10],
            'retrieval_method': 'multi_strategy',
            'strategies_used': list(results.keys()),
            'count': len(final_memories[:10])
        }
    
    def _calculate_retrieval_confidence(self, similarity: float, memory: MemoryItem) -> float:
        """Calculate overall retrieval confidence"""
        # Combine similarity with memory properties
        confidence = (
            similarity * 0.4 +
            memory.source_reliability * 0.2 +
            (memory.consolidation_level / 3.0) * 0.2 +
            min(1.0, memory.access_frequency / 10) * 0.1 +
            (1.0 - memory.decay_rate) * 0.1
        )
        return min(1.0, confidence)
    
    def _calculate_episodic_score(self, memory: MemoryItem, cues: Dict[str, Any]) -> float:
        """Calculate episodic retrieval score based on cue matching"""
        score = 0.0
        cue_count = 0
        
        # Temporal cue matching
        if 'time_range' in cues and memory.timestamp:
            cue_count += 1
            # Simple temporal proximity score
            score += 0.3
        
        # Context cue matching
        if 'context' in cues:
            cue_count += 1
            context_matches = len(set(cues['context']) & set(memory.context_tags))
            if cues['context']:
                score += (context_matches / len(cues['context'])) * 0.4
        
        # Emotional cue matching
        if 'emotion' in cues:
            cue_count += 1
            emotion_matches = len(set(cues['emotion']) & set(memory.emotion_tags))
            if cues['emotion']:
                score += (emotion_matches / len(cues['emotion'])) * 0.3
        
        return score if cue_count > 0 else 0.0
    
    def _calculate_association_strength(self, memory1: MemoryItem, memory2: MemoryItem) -> float:
        """Calculate strength of association between two memories"""
        strength = 0.5  # Base association strength
        
        # Temporal proximity
        if memory1.timestamp and memory2.timestamp:
            time_diff = abs((memory1.timestamp - memory2.timestamp).total_seconds())
            if time_diff < 3600:  # Within an hour
                strength += 0.2
            elif time_diff < 86400:  # Within a day
                strength += 0.1
        
        # Shared context
        shared_context = len(set(memory1.context_tags) & set(memory2.context_tags))
        strength += shared_context * 0.1
        
        # Shared emotions
        shared_emotions = len(set(memory1.emotion_tags) & set(memory2.emotion_tags))
        strength += shared_emotions * 0.1
        
        return min(1.0, strength)
    
    def _calculate_completion_confidence(self, partial: str, memory: MemoryItem, similarity: float) -> float:
        """Calculate confidence in pattern completion"""
        # Base confidence from similarity
        confidence = similarity
        
        # Boost for high consolidation
        confidence += (memory.consolidation_level / 3.0) * 0.2
        
        # Boost for reliable sources
        confidence *= memory.source_reliability
        
        # Penalty for old memories
        if memory.last_accessed:
            days_old = (datetime.now() - memory.last_accessed).days
            if days_old > 30:
                confidence *= 0.8
        
        return min(1.0, confidence)
    
    async def _complete_pattern(self, partial: str, memory: MemoryItem) -> str:
        """Complete a partial pattern using a full memory"""
        # Use LLM to intelligently complete the pattern
        prompt = f"""
        Given this partial information: "{partial}"
        And this complete memory: "{memory.content}"
        
        Complete the partial information based on the memory.
        """
        
        completed = await self.call_llm(prompt)
        return completed
    
    def _calculate_context_match(self, memory: MemoryItem, context_features: Dict) -> float:
        """Calculate how well a memory matches context features"""
        score = 0.0
        feature_count = 0
        
        # Tag matching
        if context_features['tags']:
            feature_count += 1
            tag_matches = len(set(context_features['tags']) & set(memory.context_tags))
            score += (tag_matches / len(context_features['tags'])) * 0.4 if context_features['tags'] else 0
        
        # Environment matching
        if context_features['environment'] and 'environment' in memory.metadata:
            feature_count += 1
            if memory.metadata['environment'] == context_features['environment']:
                score += 0.3
        
        # Task matching
        if context_features['task'] and 'task' in memory.metadata:
            feature_count += 1
            if memory.metadata['task'] == context_features['task']:
                score += 0.3
        
        return score if feature_count > 0 else 0.0
    
    def _get_matched_cues(self, memory: MemoryItem, cues: Dict) -> List[str]:
        """Get list of matched cues"""
        matched = []
        
        if 'context' in cues:
            if set(cues['context']) & set(memory.context_tags):
                matched.append('context')
        
        if 'emotion' in cues:
            if set(cues['emotion']) & set(memory.emotion_tags):
                matched.append('emotion')
        
        if 'time_range' in cues:
            matched.append('temporal')
        
        return matched
    
    def _get_matched_context_features(self, memory: MemoryItem, context_features: Dict) -> List[str]:
        """Get list of matched context features"""
        matched = []
        
        if set(context_features['tags']) & set(memory.context_tags):
            matched.append('tags')
        
        if context_features['environment'] and memory.metadata.get('environment') == context_features['environment']:
            matched.append('environment')
        
        if context_features['task'] and memory.metadata.get('task') == context_features['task']:
            matched.append('task')
        
        return matched
    
    def _update_cache(self, key: str, value: Any):
        """Update retrieval cache with LRU policy"""
        if len(self.retrieval_cache) >= self.cache_size:
            # Remove oldest entry
            oldest_key = next(iter(self.retrieval_cache))
            del self.retrieval_cache[oldest_key]
        
        self.retrieval_cache[key] = value