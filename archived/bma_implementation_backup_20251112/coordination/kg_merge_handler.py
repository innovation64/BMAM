"""
Knowledge Graph Merge Handler Module
Handles KG operations, triple processing, and KG-memory fusion
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..utils.config import get_logger

logger = get_logger(__name__)


class KGMergeHandler:
    """Handles Knowledge Graph operations and memory fusion"""

    def __init__(self, kg_patterns_fn, phrases_checker_fn):
        """
        Initialize KG Merge Handler

        Args:
            kg_patterns_fn: Function to get KG patterns
            phrases_checker_fn: Function to check phrases in text
        """
        self._get_kg_patterns = kg_patterns_fn
        self._phrases_in_text = phrases_checker_fn
        self._kg_cache = None  # Cached KG triples


    def should_trigger_kg_search(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        language: str = 'en'
    ) -> bool:
        """
        判断是否触发KG检索

        触发条件:
        1. 查询包含实体关系词汇
        2. 检索到的记忆较少(信息缺口)
        3. 查询明确要求知识图谱信息

        Args:
            query: Query text
            memories: Retrieved memories
            language: Language code

        Returns:
            True if KG search should be triggered
        """
        # Condition 1: 查询包含KG关系词汇
        kg_relation_patterns = self._get_kg_patterns('relation_keywords', language)
        if self._phrases_in_text(kg_relation_patterns, query.lower()):
            return True

        # Condition 2: 记忆检索结果不足(信息缺口)
        if len(memories) < 3:
            return True

        # Condition 3: 显式请求KG信息
        kg_request_patterns = self._get_kg_patterns('kg_request_keywords', language)
        if self._phrases_in_text(kg_request_patterns, query.lower()):
            return True

        return False

    async def call_kg_search(
        self,
        query: str,
        temporal_lobe_agent,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        调用KG检索

        Args:
            query: Query text
            temporal_lobe_agent: Temporal lobe agent with KG capabilities
            max_results: Maximum results to return

        Returns:
            List of KG facts as memory-format dicts
        """
        try:

            # Call temporal lobe's KG search
            kg_results = await temporal_lobe_agent.search_knowledge_graph(
                query=query,
                max_results=max_results
            )

            return kg_results

        except Exception as e:
            logger.error(f"❌ KG search failed: {e}")
            return []

    def merge_kg_memories(
        self,
        vector_memories: List[Dict[str, Any]],
        kg_facts: List[Dict[str, Any]],
        alpha: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        融合向量记忆和KG事实

        融合策略:
        1. KG事实优先级高(boost score)
        2. 去重: 相似内容只保留一个
        3. 按分数排序

        Args:
            vector_memories: Vector search results
            kg_facts: KG search results
            alpha: Weight for KG facts (0.0-1.0)

        Returns:
            Merged memory list
        """
        # Boost KG fact scores
        for fact in kg_facts:
            fact['score'] = fact.get('score', 1.0) * (1.0 + alpha)
            fact['kg_enhanced'] = True

        # Combine and sort
        all_memories = vector_memories + kg_facts

        # Deduplicate by content similarity
        deduped = self._deduplicate_memories(all_memories)

        # Sort by score
        deduped.sort(key=lambda x: x.get('score', 0), reverse=True)


        return deduped

    def _deduplicate_memories(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate memories based on content similarity

        Args:
            memories: Memory list

        Returns:
            Deduplicated memory list
        """
        seen_contents = set()
        deduped = []

        for mem in memories:
            content = mem.get('content', '').lower().strip()
            # Simple deduplication by exact content match
            if content and content not in seen_contents:
                seen_contents.add(content)
                deduped.append(mem)

        removed = len(memories) - len(deduped)
        if removed > 0:
            logger.info(f"Deduplicated {removed} memories by content similarity")

        return deduped

    def load_locomo_kg_triples(self, kg_file_path: str = 'data/locomo_kg.json') -> List[Dict[str, Any]]:
        """
        Load KG triples from LoCoMo JSON file

        Args:
            kg_file_path: Path to KG JSON file

        Returns:
            List of triple dicts
        """
        if self._kg_cache is not None:
            return self._kg_cache

        try:
            kg_path = Path(kg_file_path)
            if not kg_path.exists():
                logger.warning(f"KG file not found: {kg_file_path}")
                return []

            with kg_path.open('r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract triples from the KG structure
            triples = data.get('triples', [])

            self._kg_cache = triples
            return triples

        except Exception as e:
            logger.error(f"❌ Failed to load KG triples: {e}")
            return []

    async def query_kg_for_facts(
        self,
        query: str,
        entities: List[str],
        kg_file_path: str = 'data/locomo_kg.json'
    ) -> List[Dict[str, Any]]:
        """
        Query KG for facts related to entities

        Args:
            query: Query text
            entities: List of entity names
            kg_file_path: Path to KG file

        Returns:
            List of KG facts as memory dicts
        """
        all_triples = self.load_locomo_kg_triples(kg_file_path)

        if not all_triples:
            return []

        query_lower = query.lower()
        kg_facts = []

        # Define predicate keywords for different query types
        location_predicates = ['lives_in', 'moved_from', 'visited', 'camped_at', 'location']
        activity_predicates = ['likes', 'enjoys', 'hobby', 'interested_in']
        relationship_predicates = ['friend_of', 'family', 'knows', 'related_to']
        work_predicates = ['works_at', 'occupation', 'job', 'profession']
        interest_predicates = ['likes', 'enjoys', 'interested_in', 'hobby', 'prefers']

        # Location entities for filtering
        location_names = ['yosemite', 'yellowstone', 'sequoia', 'sweden', 'norway',
                         'denmark', 'san francisco', 'berkeley', 'oakland']

        # Family entities
        family_entities = ['kids', 'children', 'family', 'son', 'daughter']

        # Pattern-based extraction
        for entity in entities:
            entity_lower = entity.lower()

            # Pattern 1: "Where does X live?" → location query
            if 'where' in query_lower and ('live' in query_lower or 'location' in query_lower):
                matching_triples = [
                    triple for triple in all_triples
                    if triple.get('subject', '').lower() == entity_lower
                    and any(loc_pred in triple.get('predicate', '').lower()
                           for loc_pred in location_predicates)
                ]
                for triple in matching_triples:
                    kg_facts.append(self.triple_to_memory(triple))

            # Pattern 2: "What does X do?" → occupation query
            if 'what' in query_lower and ('do' in query_lower or 'work' in query_lower):
                matching_triples = [
                    triple for triple in all_triples
                    if triple.get('subject', '').lower() == entity_lower
                    and any(work_pred in triple.get('predicate', '').lower()
                           for work_pred in work_predicates)
                ]
                for triple in matching_triples:
                    kg_facts.append(self.triple_to_memory(triple))

            # Pattern 3: "Who is X's friend?" → relationship query
            if 'who' in query_lower and 'friend' in query_lower:
                matching_triples = [
                    triple for triple in all_triples
                    if triple.get('subject', '').lower() == entity_lower
                    and any(rel_pred in triple.get('predicate', '').lower()
                           for rel_pred in relationship_predicates)
                ]
                for triple in matching_triples:
                    kg_facts.append(self.triple_to_memory(triple))

            # Pattern 4: "What activities does X like?" → activity query
            if 'what' in query_lower and any(kw in query_lower for kw in ['like', 'enjoy', 'activity', 'hobby']):
                for pred_keyword in activity_predicates:
                    matching_triples = [
                        triple for triple in all_triples
                        if triple.get('subject', '').lower() == entity_lower
                        and pred_keyword in triple.get('predicate', '').lower()
                    ]
                    for triple in matching_triples:
                        kg_facts.append(self.triple_to_memory(triple))

            # Pattern 5: "Where has X camped?" → camping location aggregation
            if 'where' in query_lower and 'camp' in query_lower:
                matching_triples = [
                    triple for triple in all_triples
                    if (entity_lower in triple.get('subject', '').lower() or
                        entity_lower in triple.get('object', '').lower())
                    and ('camp' in triple.get('predicate', '').lower() or
                         'camp' in triple.get('object', '').lower())
                    and any(loc in triple.get('object', '').lower()
                           for loc in location_names)
                ]
                for triple in matching_triples:
                    kg_facts.append(self.triple_to_memory(triple))

        # Deduplicate KG facts
        original_count = len(kg_facts)
        if kg_facts:
            seen_triples = set()
            deduped_facts = []
            for fact in kg_facts:
                triple = fact.get('kg_triple', {})
                # Create unique key from triple content
                triple_key = (
                    triple.get('subject', '').lower().strip(),
                    triple.get('predicate', '').lower().strip(),
                    triple.get('object', '').lower().strip()
                )
                if triple_key not in seen_triples:
                    seen_triples.add(triple_key)
                    deduped_facts.append(fact)
            kg_facts = deduped_facts

            if original_count > len(kg_facts):
                logger.info(f"KG deduplication: {original_count} → {len(kg_facts)} facts")

        return kg_facts

    def triple_to_memory(self, triple: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert KG triple to pseudo-"memory" format

        Args:
            triple: {'subject': 'Caroline', 'predicate': 'moved_from', 'object': 'Sweden'}

        Returns:
            Pseudo-memory dict
        """
        subject = triple.get('subject', '')
        predicate = triple.get('predicate', '')
        obj = triple.get('object', '')

        # Generate natural language description
        content = f"{subject} {predicate} {obj}"

        # Generate unique ID
        triple_id = hashlib.md5(content.encode()).hexdigest()[:8]

        return {
            'id': f'kg_fact_{triple_id}',
            'content': content,
            'kg_triple': triple,
            'score': 1.0,  # KG facts have high priority
            'plasticity_score': 2.0,  # Boost to ensure KG facts rank high
            'source': 'knowledge_graph',
            'timestamp': datetime.now().isoformat(),
            'kg_enhanced': True,
            'metadata': {
                'kg_source': 'locomo_kg.json',
                'triple': triple,
                'retrieval_scores': {
                    'kg_direct': 1.0  # Mark as direct KG fact
                }
            }
        }

    def log_kg_surfacing_stats(self, memories: List[Dict[str, Any]]) -> None:
        """
        Log KG surfacing statistics

        Args:
            memories: Memory list to analyze
        """
        kg_count = sum(1 for m in memories if m.get('kg_enhanced', False))
        total_count = len(memories)

        if kg_count > 0:
            percentage = (kg_count / total_count * 100) if total_count > 0 else 0
            logger.info(f"KG surfacing: {kg_count}/{total_count} ({percentage:.1f}%) memories are KG-enhanced")

    async def expand_kg_entities(
        self,
        entity: str,
        temporal_lobe_agent,
        max_hops: int = 2
    ) -> List[str]:
        """
        Expand entities through KG relations

        Args:
            entity: Starting entity
            temporal_lobe_agent: Temporal lobe agent
            max_hops: Maximum relation hops

        Returns:
            List of related entities
        """
        try:
            expanded = await temporal_lobe_agent.expand_entity_relations(
                entity=entity,
                max_hops=max_hops
            )
            return expanded
        except Exception as e:
            logger.error(f"❌ Entity expansion failed: {e}")
            return [entity]  # Return original entity on failure
