"""
Knowledge Graph Builder - 知识图谱构建器

理论依据:
- Knowledge graphs for information integration
- Entity-Relation extraction from unstructured text
- Semantic networks (Collins & Quillian, 1969)

⚠️ 这是一个工具,不是人脑Agent!
用于从外部文档中提取结构化知识

Enhancement (Phase 3A):
- 集成 spaCy NER 进行准确的实体识别
- 支持多种实体类型 (Person, Location, Organization, Date, etc.)
- 扩展关系模式，支持更丰富的关系类型
- 实体消歧和合并功能
"""

import logging
from typing import List, Dict, Tuple, Any, Optional, Set
import re

logger = logging.getLogger(__name__)

# Optional spaCy support
try:
    import spacy
    SPACY_AVAILABLE = True
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        logger.warning("spaCy model 'en_core_web_sm' not found. Install with: python -m spacy download en_core_web_sm")
        nlp = None
        SPACY_AVAILABLE = False
except ImportError:
    logger.warning("spaCy not installed. Install with: pip install spacy")
    SPACY_AVAILABLE = False
    nlp = None


class KnowledgeGraphBuilder:
    """
    知识图谱构建器

    功能:
    1. 从文本中提取实体 (Entity Extraction)
    2. 从文本中提取关系 (Relation Extraction)
    3. 构建知识图谱 (Knowledge Graph Construction)

    实现策略:
    - 简化版: 使用规则+LLM
    - 完整版: 可以集成SpaCy NER, OpenIE等工具
    """

    def __init__(self, llm_client=None, use_spacy: bool = True,
                 kg_instance=None):
        """
        初始化知识图谱构建器

        Args:
            llm_client: LLM客户端 (用于复杂的实体关系提取)
            use_spacy: 是否使用spaCy进行NER (更准确)
            kg_instance: LightweightKnowledgeGraph 实例 (用于持久化)
                        如果为 None，则只提取不持久化（向后兼容）
        """
        self.llm_client = llm_client
        self.use_spacy = use_spacy and SPACY_AVAILABLE and nlp is not None

        # Unified knowledge graph (new architecture)
        self.kg = kg_instance

        # Legacy storage (deprecated, kept for backward compatibility)
        # TODO: Remove in next major version
        self.knowledge_graph = {
            'entities': {},  # {entity_name: {type, mentions, aliases, ...}}
            'relations': []  # [(source, relation, target), ...]
        }

        # Entity aliases for disambiguation (alias_lower -> canonical with original casing)
        self.entity_aliases: Dict[str, str] = {}

        # Known person names from conversation context
        self.known_persons: Set[str] = set()

        mode = "spaCy+Rules+LLM" if self.use_spacy else "Rules+LLM"
        persistence = "with persistent KG" if self.kg else "memory only (legacy)"
        logger.debug(f"🔧 KnowledgeGraphBuilder initialized (mode: {mode}, {persistence})")

    async def extract_from_text(
        self,
        text: str,
        use_llm: bool = True,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        从文本中提取实体和关系

        Args:
            text: 输入文本
            use_llm: 是否使用LLM (更准确,但slower)
            context: 上下文信息 (e.g., speaker names, dates)

        Returns:
            (entities, relations)
            entities: [{'name': 'Caroline', 'type': 'Person', 'mentions': 3}, ...]
            relations: [{'source': 'Caroline', 'relation': 'works_as', 'target': 'therapist'}, ...]
        """
        # Update known persons from context
        if context:
            if 'speakers' in context:
                self.known_persons.update(context['speakers'])

        # Multi-strategy extraction
        entities_all = []
        relations_all = []

        # Strategy 1: spaCy NER (most accurate)
        if self.use_spacy and nlp:
            spacy_entities, spacy_relations = await self._extract_with_spacy(text)
            entities_all.extend(spacy_entities)
            relations_all.extend(spacy_relations)

        # Strategy 2: Rules (fallback and complement)
        rule_entities, rule_relations = await self._extract_with_rules(text)
        entities_all.extend(rule_entities)
        relations_all.extend(rule_relations)

        # Strategy 3: LLM (most comprehensive, but slowest)
        if use_llm and self.llm_client:
            llm_entities, llm_relations = await self._extract_with_llm(text)
            entities_all.extend(llm_entities)
            relations_all.extend(llm_relations)

        # Merge and deduplicate
        entities = self._merge_entities(entities_all)
        relations = self._deduplicate_relations(relations_all)

        # NEW: Persist to unified knowledge graph if available
        if self.kg:
            self._persist_to_kg(entities, relations)

        return entities, relations

    def _persist_to_kg(self, entities: List[Dict], relations: List[Dict]) -> None:
        """
        Persist extracted entities and relations to unified KG

        This eliminates the duplication between builder and persistent graph.
        """
        if not self.kg:
            return

        # Add entities to persistent graph
        for entity in entities:
            entity_name = entity.get('name', '')
            entity_type = entity.get('type', 'Concept')

            # Map builder types to KG types
            type_mapping = {
                'Person': 'person',
                'Location': 'location',
                'Organization': 'concept',
                'Date': 'time',
                'Time': 'time',
                'Event': 'event',
                'Concept': 'concept',
                'Group': 'concept'
            }
            kg_type = type_mapping.get(entity_type, 'concept')

            # Add node to KG
            self.kg.add_node(
                node_id=entity_name,
                entity_type=kg_type,
                content=entity_name,
                properties={
                    'mentions': entity.get('mentions', 1),
                    'extraction_method': entity.get('source', 'unknown')
                }
            )

        # Add relations to persistent graph
        # First, collect all entity names mentioned in relations
        entity_names = {e.get('name', '') for e in entities}

        for relation in relations:
            source = relation.get('source', '')
            target = relation.get('target', '')
            rel_type = relation.get('relation', 'related_to')

            if source and target:
                # Ensure both source and target nodes exist (create implicit nodes if needed)
                for node_id in [source, target]:
                    if node_id not in entity_names and not self.kg.get_node(node_id):
                        # Create implicit entity node for relation endpoints
                        self.kg.add_node(
                            node_id=node_id,
                            entity_type='concept',  # Default type for implicit nodes
                            content=node_id,
                            properties={
                                'mentions': 1,
                                'extraction_method': 'implicit_from_relation'
                            }
                        )

                # Now add the edge
                self.kg.add_edge(
                    source_id=source,
                    target_id=target,
                    relation_type=rel_type,
                    strength=relation.get('confidence', 0.5),
                    properties={
                        'extraction_method': relation.get('source', 'unknown')
                    }
                )

    async def _extract_with_spacy(self, text: str) -> Tuple[List[Dict], List[Dict]]:
        """使用spaCy NER提取实体"""
        entities = []
        relations = []

        if not nlp:
            return entities, relations

        # Process with spaCy
        doc = nlp(text)

        # Entity type mapping
        entity_type_map = {
            'PERSON': 'Person',
            'GPE': 'Location',  # Geopolitical entity
            'LOC': 'Location',
            'ORG': 'Organization',
            'DATE': 'Date',
            'TIME': 'Time',
            'EVENT': 'Event',
            'WORK_OF_ART': 'Concept',
            'FAC': 'Location',  # Facility
            'NORP': 'Group',  # Nationalities, religious/political groups
        }

        # Extract entities
        entity_counts: Dict[str, int] = {}
        for ent in doc.ents:
            entity_type = entity_type_map.get(ent.label_, 'Concept')
            entity_name = ent.text.strip()

            # Skip single letters or very short entities
            if len(entity_name) <= 1:
                continue

            entity_counts[entity_name] = entity_counts.get(entity_name, 0) + 1

        # Create entity list
        for entity_name, count in entity_counts.items():
            # Determine type (check if it's a known person)
            entity_type = 'Person' if entity_name in self.known_persons else 'Concept'

            # Try to get type from spaCy
            for ent in doc.ents:
                if ent.text.strip() == entity_name:
                    entity_type = entity_type_map.get(ent.label_, entity_type)
                    break

            entities.append({
                'name': entity_name,
                'type': entity_type,
                'mentions': count
            })

        # Extract relations using dependency parsing
        for sent in doc.sents:
            # Simple subject-verb-object extraction
            for token in sent:
                if token.dep_ == "ROOT" and token.pos_ == "VERB":
                    # Find subject
                    subject = None
                    for child in token.children:
                        if child.dep_ in ("nsubj", "nsubjpass"):
                            # Get the full noun phrase
                            subject = self._get_entity_span(child)
                            break

                    # Find object
                    obj = None
                    for child in token.children:
                        if child.dep_ in ("dobj", "attr", "prep"):
                            obj = self._get_entity_span(child)
                            break

                    # Create relation if both found
                    if subject and obj and subject != obj:
                        relations.append({
                            'source': subject,
                            'relation': token.lemma_,  # Use verb lemma as relation
                            'target': obj
                        })

        logger.debug(f"🔍 spaCy extracted {len(entities)} entities, {len(relations)} relations")
        return entities, relations

    def _get_entity_span(self, token) -> str:
        """获取完整的实体短语（包括修饰词）"""
        # Get subtree to include modifiers
        span = list(token.subtree)
        # Filter out some function words
        words = [t.text for t in span if t.pos_ not in ('DET', 'ADP', 'PUNCT')]
        return ' '.join(words).strip().title()

    async def _extract_with_llm(self, text: str) -> Tuple[List[Dict], List[Dict]]:
        """使用LLM提取实体和关系 (Phase 3A 增强版)"""
        # 限制文本长度 (避免超出token限制)
        if len(text) > 3000:
            text = text[:3000]

        # Enhanced prompt for better entity/relation extraction
        prompt = f"""Extract entities and their relations from this conversational text. Focus on:
- People (names, identities, occupations)
- Locations (cities, countries, places)
- Organizations (companies, schools, groups)
- Events and activities
- Attributes and characteristics

Text:
{text}

Extract as many meaningful entities and relations as possible. For relations, use specific verbs like:
- works_as, works_at, studied_at, lived_in, moved_from
- is_a (identity/occupation), identity_is (personal identity)
- researched, attended_event, painted, participated_in
- likes, interested_in, has_relationship

Output JSON format:
{{
  "entities": [
    {{"name": "Caroline", "type": "Person"}},
    {{"name": "Sweden", "type": "Location"}},
    {{"name": "counseling", "type": "Concept"}},
    ...
  ],
  "relations": [
    {{"source": "Caroline", "relation": "identity_is", "target": "transgender woman"}},
    {{"source": "Caroline", "relation": "moved_from", "target": "Sweden"}},
    {{"source": "Caroline", "relation": "interested_in", "target": "counseling"}},
    ...
  ]
}}

Only output valid JSON, no explanation.
"""

        try:
            from ...services.shared_openai_client import shared_client_manager
            client = await shared_client_manager.get_chat_client()

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a knowledge extraction expert. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )

            result_text = response.choices[0].message.content.strip()

            # 解析JSON
            import json
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                entities = result.get('entities', [])
                relations = result.get('relations', [])

                logger.debug(f"🔍 LLM extracted {len(entities)} entities, {len(relations)} relations")

                return entities, relations
            else:
                logger.warning("Failed to parse LLM output, falling back to rules")
                return await self._extract_with_rules(text)

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return await self._extract_with_rules(text)

    async def _extract_with_rules(self, text: str) -> Tuple[List[Dict], List[Dict]]:
        """使用规则提取实体和关系 (增强版)"""
        entities = []
        relations = []

        # 提取实体: 大写开头的词 + 已知人名
        capitalized_words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        entity_counts = {}

        # Common stopwords to filter
        stopwords = {
            'The', 'A', 'An', 'This', 'That', 'These', 'Those',
            'I', 'You', 'He', 'She', 'It', 'We', 'They',
            'My', 'Your', 'His', 'Her', 'Its', 'Our', 'Their',
            'Am', 'Is', 'Are', 'Was', 'Were', 'Be', 'Been', 'Being',
            'Have', 'Has', 'Had', 'Do', 'Does', 'Did',
            'Will', 'Would', 'Could', 'Should', 'May', 'Might', 'Must',
            'Can', 'Could', 'What', 'When', 'Where', 'Who', 'Why', 'How'
        }

        for word in capitalized_words:
            if word in stopwords:
                continue

            # Normalize entity name
            normalized = word.strip()
            entity_counts[normalized] = entity_counts.get(normalized, 0) + 1

        # Add known persons (even if not capitalized in text)
        for person in self.known_persons:
            # Case-insensitive search
            person_count = len(re.findall(rf'\b{re.escape(person)}\b', text, re.IGNORECASE))
            if person_count > 0:
                entity_counts[person] = person_count

        # Create entity list
        for entity, count in entity_counts.items():
            # Determine type
            entity_type = 'Person' if entity in self.known_persons else 'Unknown'

            entities.append({
                'name': entity,
                'type': entity_type,
                'mentions': count
            })

        # 🎯 Phase 3A: 扩展关系模式 - 覆盖 LoCoMo 场景
        # More flexible patterns to match conversational text
        relation_patterns = [
            # Career and occupation - be more flexible
            (r'([A-Z]\w+)\s+(?:\'d|would)\s+be\s+a\s+great\s+(\w+)', 'suitable_for'),
            (r'([A-Z]\w+)\s+(?:is|was|\'s|am)\s+(?:a\s+)?(\w+\s+\w+|therapist|counselor|engineer|scientist|artist|teacher)', 'is_a'),
            (r'([A-Z]\w+)\s+works?\s+as\s+(?:a\s+)?(.+?)(?:\.|,|!|\sand)', 'works_as'),
            (r'([A-Z]\w+)\s+works?\s+(?:at|for|in)\s+([A-Z][\w\s]+?)(?:\.|,|!)', 'works_at'),

            # Education and learning
            (r'([A-Z]\w+)\s+(?:attended|studied|went to)\s+([A-Z][\w\s]+?)(?:\.|,|!)', 'attended'),
            (r'([A-Z]\w+)\s+(?:studying|pursuin g|continue)\s+(?:my\s+)?(\w+)', 'studies'),

            # Research and interests - more flexible
            (r'([A-Z]\w+)\s+researched\s+(.+?)(?:\.|,|!)', 'researched'),
            (r"([A-Z]\w+)(?:'s|is)?\s+(?:keen on|interested in|passionate about)\s+(.+?)(?:\.|,|!|-)", 'interested_in'),
            (r'([A-Z]\w+)\s+(?:likes?|loves?|enjoys?)\s+(.+?)(?:\.|,|!)', 'likes'),
            (r'([A-Z]\w+)\s+check out\s+(.+?)(?:\.|,|!)', 'exploring'),

            # Identity and attributes
            (r'The\s+(\w+)\s+stories', 'story_about'),  # "The transgender stories"
            (r'([A-Z]\w+)\s+is\s+(single|married|divorced)', 'relationship_status'),

            # Location and residence
            (r'([A-Z]\w+)\s+(?:lives?|lived|moved|came)\s+(?:in|from)\s+([A-Z][\w\s]+?)(?:\.|,|!)', 'lived_in'),
            (r'moved\s+from\s+([A-Z]\w+)', 'origin_location'),

            # Activities and events - flexible matching
            (r'([A-Z]\w+)\s+(?:went to|attended)\s+(?:a\s+)?([\w\s]+(?:group|meeting|event|support group|conference))' , 'attended_event'),
            (r'([A-Z]\w+)\s+painted\s+(?:a\s+|that\s+)?([\w\s]+?)(?:\.|,|!)', 'painted'),
            (r'([A-Z]\w+)\s+(?:ran|completed)\s+(?:a\s+)?([\w\s]+race)', 'participated_in'),
            (r'([A-Z]\w+)\s+gave\s+(?:a\s+)?(speech|presentation)', 'gave_speech'),
            (r'([A-Z]\w+)\s+(?:gonna|going to)\s+(.+?)(?:\sand|,|\.)', 'planning_to'),

            # Relationships and interactions
            (r'([A-Z]\w+)\s+(?:has|had)\s+([\w\s]+(?:friends|family|mentors|kids))', 'has_relationship'),
            (r'([A-Z]\w+)\s+met\s+(?:with|up with)?\s*([A-Z][\w\s]+)', 'met_with'),
            (r'support\s+(?:for|those\s+with)\s+([\w\s]+)', 'support_for'),

            # General verb-object patterns (catch-all)
            (r'([A-Z]\w+)\s+(feels?|feels)\s+(\w+)', 'feels'),
            (r'([A-Z]\w+)\s+(?:made|makes)\s+me\s+feel\s+(\w+)', 'made_feel'),
        ]

        for pattern, relation_type in relation_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match) == 2:
                    source, target = match
                    source = source.strip().title()
                    target = target.strip().lower()  # Keep targets lowercase for concepts

                    # Resolve aliases
                    source = self.entity_aliases.get(source, source)

                    relations.append({
                        'source': source,
                        'relation': relation_type,
                        'target': target
                    })

        logger.debug(f"🔍 Rule-based extracted {len(entities)} entities, {len(relations)} relations")

        return entities, relations

    def _merge_entities(self, entities: List[Dict]) -> List[Dict]:
        """合并重复实体并解决别名"""
        entity_map = {}

        for entity in entities:
            name = entity['name']

            # Resolve alias
            canonical_name = self.entity_aliases.get(name.lower(), name)

            if canonical_name in entity_map:
                # Merge with existing
                existing = entity_map[canonical_name]
                existing['mentions'] = existing.get('mentions', 1) + entity.get('mentions', 1)

                # Prefer more specific types
                if entity.get('type', 'Unknown') != 'Unknown':
                    existing['type'] = entity['type']
            else:
                # Add new entity
                entity['name'] = canonical_name  # Use canonical name
                entity_map[canonical_name] = entity

        return list(entity_map.values())

    def _deduplicate_relations(self, relations: List[Dict]) -> List[Dict]:
        """去重关系三元组"""
        seen = set()
        unique_relations = []

        for rel in relations:
            source = self.entity_aliases.get(rel['source'].lower(), rel['source'])
            target = rel['target']
            relation = rel['relation']

            triple = (source, relation, target)

            if triple not in seen:
                seen.add(triple)
                rel['source'] = source  # Use canonical name
                unique_relations.append(rel)

        return unique_relations

    def register_alias(self, alias: str, canonical: str):
        """注册实体别名 (e.g., "Mel" -> "Melanie")"""
        alias_key = alias.strip().lower()
        canonical_name = canonical.strip()
        if not alias_key or not canonical_name:
            return
        self.entity_aliases[alias_key] = canonical_name
        logger.debug(f"📝 Registered alias: {alias} -> {canonical_name}")
        logger.debug(f"📝 Registered alias: {alias} -> {canonical}")

    def register_known_person(self, name: str):
        """注册已知人名 (用于提高识别准确性)"""
        if not name:
            return
        canonical = name.strip()
        if not canonical:
            return
        self.known_persons.add(canonical)
        # Ensure canonical maps to itself (case-insensitive)
        self.entity_aliases.setdefault(canonical.lower(), canonical)
        logger.debug(f"👤 Registered known person: {canonical}")

    async def extract_entities(self, text: str) -> List[str]:
        """快速提取实体名称 (用于查询)"""
        entities, _ = await self.extract_from_text(text, use_llm=False)
        return [e['name'] for e in entities]

    async def query_relations(self, entity: str) -> List[Dict]:
        """查询知识图谱中与某个实体相关的关系"""
        results = []

        for relation in self.knowledge_graph['relations']:
            if relation[0] == entity or relation[2] == entity:
                results.append({
                    'source': relation[0],
                    'relation': relation[1],
                    'target': relation[2]
                })

        return results

    def add_to_graph(self, entities: List[Dict], relations: List[Dict]):
        """
        将实体和关系添加到知识图谱（同步到统一KG）
        Add entities and relations to knowledge graph (syncs to unified KG)

        This method now syncs to both:
        1. Legacy memory dict (for backward compatibility)
        2. Unified NetworkX KG (if kg_instance was provided)
        """
        # 添加实体到内存字典 (Legacy storage for backward compatibility)
        for entity in entities:
            name = entity['name']
            if name not in self.knowledge_graph['entities']:
                self.knowledge_graph['entities'][name] = entity
            else:
                # 合并mentions
                self.knowledge_graph['entities'][name]['mentions'] = \
                    self.knowledge_graph['entities'][name].get('mentions', 0) + \
                    entity.get('mentions', 0)

        # 添加关系到内存字典 (Legacy storage for backward compatibility)
        for relation in relations:
            triple = (relation['source'], relation['relation'], relation['target'])
            if triple not in self.knowledge_graph['relations']:
                self.knowledge_graph['relations'].append(triple)

        # ✅ NEW: Sync to unified NetworkX KG
        if self.kg:
            try:
                before_stats = self.kg.get_statistics()
                self._persist_to_kg(entities, relations)
                after_stats = self.kg.get_statistics()

                logger.info(
                    f"✅ KG Sync: {before_stats.get('total_nodes', 0)} → {after_stats.get('total_nodes', 0)} nodes, "
                    f"{before_stats.get('total_edges', 0)} → {after_stats.get('total_edges', 0)} edges"
                )
            except Exception as e:
                logger.error(f"❌ Failed to sync to unified KG: {e}", exc_info=True)
        else:
            logger.warning(
                f"⚠️ No unified KG instance - {len(entities)} entities and {len(relations)} relations "
                f"stored in memory dict only (not persistent)"
            )

        logger.debug(f"📊 Memory Dict KG stats: {len(self.knowledge_graph['entities'])} entities, "
                   f"{len(self.knowledge_graph['relations'])} relations")

    def get_statistics(self) -> Dict[str, Any]:
        """获取知识图谱统计信息"""
        entity_count = len(self.knowledge_graph['entities'])
        relation_count = len(self.knowledge_graph['relations'])

        return {
            'total_entities': entity_count,
            'entity_count': entity_count,
            'total_relations': relation_count,
            'relation_count': relation_count,
            'triple_count': relation_count,
            'entities_by_type': self._count_by_type(),
            'top_entities': self._get_top_entities(5)
        }

    def _count_by_type(self) -> Dict[str, int]:
        """按类型统计实体"""
        type_counts = {}
        for entity in self.knowledge_graph['entities'].values():
            entity_type = entity.get('type', 'Unknown')
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
        return type_counts

    def _get_top_entities(self, k: int) -> List[Tuple[str, int]]:
        """获取top-k高频实体"""
        entities_with_mentions = [
            (name, data.get('mentions', 0))
            for name, data in self.knowledge_graph['entities'].items()
        ]
        entities_with_mentions.sort(key=lambda x: x[1], reverse=True)
        return entities_with_mentions[:k]

    def export_graph(self) -> Dict[str, Any]:
        """导出知识图谱"""
        return {
            'entities': list(self.knowledge_graph['entities'].values()),
            'relations': [
                {'source': s, 'relation': r, 'target': t}
                for s, r, t in self.knowledge_graph['relations']
            ]
        }

    def get_all_triples(self) -> List[Tuple[str, str, str]]:
        """返回当前知识图谱中的所有三元组"""
        return list(self.knowledge_graph['relations'])

    def clear(self):
        """清空知识图谱"""
        self.knowledge_graph = {
            'entities': {},
            'relations': []
        }
        logger.debug("🗑️ Knowledge graph cleared")
