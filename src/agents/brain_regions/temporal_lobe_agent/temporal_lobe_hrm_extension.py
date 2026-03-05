"""
Temporal Lobe Agent HRM Extension - 颞叶智能体HRM扩展
Hierarchical Reasoning Model (HRM) Enhancements for Temporal Lobe

Adds HRM's H module (slow, strategic) capabilities:
1. Slow timescale semantic consolidation (every T=10 steps)
2. Strategic knowledge integration and schema abstraction
3. Multi-hop reasoning coordination
4. Knowledge graph refinement and concept generalization

Key Design:
- H module: Updates every T=10 steps with strategic semantic integration
- Coordinates semantic consolidation from episodic memories (Hippocampus)
- Integrates TemporalConceptGraph for structured knowledge
- Provides abstract conceptual representations to guide L modules
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SemanticConsolidationPlan:
    """
    Semantic Consolidation Plan (H Module Output)
    语义巩固计划（H模块输出）
    """
    consolidation_goal: str
    source_memories: List[str]  # IDs from hippocampus
    target_concepts: List[str]  # Concepts to extract/strengthen
    knowledge_schema: Dict[str, Any]  # Abstract knowledge structure
    expected_kg_updates: int  # Expected KG node/edge additions
    confidence: float


@dataclass
class ConsolidationSignal:
    """
    Consolidation Signal to L Modules
    向L模块的巩固信号
    """
    target_region: str  # 'hippocampus', 'amygdala'
    action: str  # 'promote_to_semantic', 'retain_episodic'
    memory_ids: List[str]
    consolidation_priority: float


class TemporalLobeHRMExtension:
    """
    HRM Extension for Temporal Lobe Agent
    颞叶智能体的HRM扩展

    Mixin class that adds HRM H module (slow) capabilities to
    the existing TemporalLobeAgent.

    Usage:
        class TemporalLobeAgentV2(TemporalLobeHRMExtension, TemporalLobeAgent):
            pass

    HRM Features:
    1. slow_semantic_consolidation() - Slow timescale semantic integration
    2. generate_consolidation_signals() - Send guidance to fast regions
    3. abstract_schema_extraction() - Extract abstract knowledge structures
    4. strategic_kg_refinement() - Refine knowledge graph strategically
    """

    def __init__(self, *args, **kwargs):
        """Initialize HRM extension"""
        super().__init__(*args, **kwargs)

        # HRM-specific state
        self.consolidation_plan: Optional[SemanticConsolidationPlan] = None
        self.last_consolidation_step = -1
        self.consolidation_interval = 10  # T = 10 steps (H module timescale)

        # Abstract knowledge representation
        self.abstract_schemas: Dict[str, Any] = {
            'concept_hierarchies': {},  # {concept: parent_concept}
            'schema_templates': [],     # Generalized knowledge patterns
            'consolidation_queue': []   # Memories pending consolidation
        }

        # Consolidation signals history
        self.consolidation_signals_sent: List[ConsolidationSignal] = []

        # Performance metrics
        self.hrm_metrics = {
            'consolidations_performed': 0,
            'schemas_extracted': 0,
            'kg_nodes_added': 0,
            'kg_edges_added': 0,
            'episodic_to_semantic_conversions': 0
        }

        logger.info("TemporalLobeHRMExtension initialized (H module, slow semantic consolidation)")

    async def slow_semantic_consolidation(
        self,
        global_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Slow Semantic Consolidation (H Module - Slow Timescale)
        慢速语义巩固（H模块 - 慢时间尺度）

        Called every T=10 steps by Thalamus.
        Performs strategic semantic integration and knowledge consolidation.

        Args:
            global_context: Context from all brain regions

        Returns:
            Dictionary with:
            - consolidation_plan: SemanticConsolidationPlan
            - consolidation_signals: Signals to send to L modules
            - abstract_schemas: Updated abstract knowledge structures
            - kg_updates: Knowledge graph updates performed
        """
        current_step = global_context.get('step', 0)
        logger.info(f"Temporal Lobe H module consolidation at step {current_step}")

        # Step 1: Analyze episodic memories from Hippocampus
        episodic_analysis = await self._analyze_episodic_memories(global_context)

        # Step 2: Generate consolidation plan
        consolidation_plan = await self._generate_consolidation_plan(
            episodic_analysis,
            global_context
        )
        self.consolidation_plan = consolidation_plan

        # Step 3: Extract abstract schemas
        schemas_extracted = self._extract_abstract_schemas(consolidation_plan)

        # Step 4: Perform knowledge graph refinement
        kg_updates = await self._strategic_kg_refinement(consolidation_plan)

        # Step 5: Generate consolidation signals for L modules
        consolidation_signals = self._generate_consolidation_signals(consolidation_plan)

        # Step 6: Record consolidation
        self.last_consolidation_step = current_step
        self.hrm_metrics['consolidations_performed'] += 1

        return {
            'consolidation_plan': {
                'goal': consolidation_plan.consolidation_goal,
                'source_count': len(consolidation_plan.source_memories),
                'target_concepts': consolidation_plan.target_concepts,
                'confidence': consolidation_plan.confidence
            },
            'consolidation_signals': consolidation_signals,
            'abstract_schemas': self.abstract_schemas,
            'kg_updates': kg_updates,
            'schemas_extracted': schemas_extracted
        }

    async def _analyze_episodic_memories(
        self,
        global_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze Episodic Memories from Hippocampus
        分析来自海马体的情节记忆

        Args:
            global_context: Global context

        Returns:
            Analysis dictionary
        """
        region_outputs = global_context.get('region_outputs', {})
        hippocampus_output = region_outputs.get('hippocampus', {})

        # Extract episodic memories
        episodic_memories = hippocampus_output.get('memories', [])

        # Filter high-importance memories for consolidation
        consolidation_candidates = [
            mem for mem in episodic_memories
            if isinstance(mem, dict) and mem.get('importance', 0) > 0.7
        ]

        # Identify recurring themes/entities
        entity_frequency = {}
        for mem in consolidation_candidates:
            entities = mem.get('entities', [])
            for entity in entities:
                entity_frequency[entity] = entity_frequency.get(entity, 0) + 1

        # Find high-frequency entities (worthy of semantic consolidation)
        significant_entities = [
            entity for entity, freq in entity_frequency.items()
            if freq >= 2  # Appeared at least twice
        ]

        return {
            'total_episodic': len(episodic_memories),
            'consolidation_candidates': len(consolidation_candidates),
            'significant_entities': significant_entities,
            'entity_frequency': entity_frequency,
            'candidate_memories': consolidation_candidates
        }

    async def _generate_consolidation_plan(
        self,
        episodic_analysis: Dict[str, Any],
        global_context: Dict[str, Any]
    ) -> SemanticConsolidationPlan:
        """
        Generate Consolidation Plan
        生成巩固计划

        Args:
            episodic_analysis: Analysis of episodic memories
            global_context: Global context

        Returns:
            SemanticConsolidationPlan
        """
        candidates = episodic_analysis.get('candidate_memories', [])
        significant_entities = episodic_analysis.get('significant_entities', [])

        # Determine consolidation goal
        if significant_entities:
            goal = f"Consolidate knowledge about: {', '.join(significant_entities[:3])}"
        else:
            goal = "Maintain semantic knowledge base"

        # Extract source memory IDs
        source_memories = [mem.get('id', '') for mem in candidates if mem.get('id')]

        # Determine target concepts
        target_concepts = significant_entities[:5]  # Top 5 entities

        # Build knowledge schema
        knowledge_schema = {
            'domain': 'general',
            'key_concepts': target_concepts,
            'relationships': self._infer_relationships(candidates, target_concepts)
        }

        # Estimate KG updates
        expected_kg_updates = len(target_concepts) + len(knowledge_schema.get('relationships', []))

        # Calculate confidence
        confidence = self._calculate_consolidation_confidence(episodic_analysis)

        return SemanticConsolidationPlan(
            consolidation_goal=goal,
            source_memories=source_memories,
            target_concepts=target_concepts,
            knowledge_schema=knowledge_schema,
            expected_kg_updates=expected_kg_updates,
            confidence=confidence
        )

    def _infer_relationships(
        self,
        memories: List[Dict[str, Any]],
        target_concepts: List[str]
    ) -> List[Tuple[str, str, str]]:
        """
        Infer Relationships Between Concepts
        推断概念之间的关系

        Args:
            memories: Memory list
            target_concepts: Target concepts

        Returns:
            List of (subject, relation, object) triples
        """
        relationships = []

        # Simple co-occurrence-based relationship inference
        for mem in memories:
            entities = mem.get('entities', [])

            # If multiple target concepts co-occur, infer relationship
            co_occurring = [e for e in entities if e in target_concepts]

            if len(co_occurring) >= 2:
                # Infer "related_to" relationship
                for i in range(len(co_occurring) - 1):
                    relationships.append((
                        co_occurring[i],
                        'related_to',
                        co_occurring[i + 1]
                    ))

        # Deduplicate
        return list(set(relationships))

    def _calculate_consolidation_confidence(
        self,
        episodic_analysis: Dict[str, Any]
    ) -> float:
        """
        Calculate Consolidation Confidence
        计算巩固置信度

        Args:
            episodic_analysis: Analysis of episodic memories

        Returns:
            Confidence score (0.0 to 1.0)
        """
        candidate_count = episodic_analysis.get('consolidation_candidates', 0)
        total_count = max(1, episodic_analysis.get('total_episodic', 1))

        # High confidence if many high-importance memories
        ratio = candidate_count / total_count

        # Also consider entity frequency
        entity_freq = episodic_analysis.get('entity_frequency', {})
        avg_freq = sum(entity_freq.values()) / max(1, len(entity_freq)) if entity_freq else 0

        confidence = min(1.0, ratio * 0.6 + min(avg_freq / 5, 1.0) * 0.4)

        return confidence

    def _extract_abstract_schemas(
        self,
        consolidation_plan: SemanticConsolidationPlan
    ) -> int:
        """
        Extract Abstract Schemas
        提取抽象模式

        Args:
            consolidation_plan: Consolidation plan

        Returns:
            Number of schemas extracted
        """
        schemas_extracted = 0

        # Extract concept hierarchy
        for concept in consolidation_plan.target_concepts:
            # Simple generalization: if concept is specific, infer category
            if concept and isinstance(concept, str):
                # Placeholder: in production, use LLM or ontology
                category = self._infer_category(concept)
                if category:
                    self.abstract_schemas['concept_hierarchies'][concept] = category
                    schemas_extracted += 1

        self.hrm_metrics['schemas_extracted'] += schemas_extracted

        logger.debug(f"Extracted {schemas_extracted} abstract schemas")

        return schemas_extracted

    def _infer_category(self, concept: str) -> Optional[str]:
        """
        Infer Category for Concept
        推断概念的类别

        Args:
            concept: Concept name

        Returns:
            Category name or None
        """
        # Simple heuristic-based categorization
        concept_lower = concept.lower()

        if any(word in concept_lower for word in ['person', 'name', 'doctor', 'friend']):
            return 'Person'
        elif any(word in concept_lower for word in ['place', 'location', 'city', 'building']):
            return 'Location'
        elif any(word in concept_lower for word in ['event', 'meeting', 'session', 'class']):
            return 'Event'
        elif any(word in concept_lower for word in ['concept', 'idea', 'theory', 'principle']):
            return 'Concept'
        else:
            return 'General'

    async def _strategic_kg_refinement(
        self,
        consolidation_plan: SemanticConsolidationPlan
    ) -> Dict[str, Any]:
        """
        Strategic Knowledge Graph Refinement
        战略性知识图谱精炼

        Args:
            consolidation_plan: Consolidation plan

        Returns:
            KG update summary
        """
        nodes_added = 0
        edges_added = 0

        # Add target concepts as nodes (if using integrated KG)
        if hasattr(self, 'kg') and self.kg:
            for concept in consolidation_plan.target_concepts:
                if concept and isinstance(concept, str):
                    # Check if concept exists in KG
                    if hasattr(self.kg, 'add_entity'):
                        # Use TemporalConceptGraph
                        existing = self.kg.get_entity(concept)
                        if not existing:
                            category = self._infer_category(concept)
                            self.kg.add_entity(concept, category or 'Concept')
                            nodes_added += 1

            # Add relationships
            for (subj, rel, obj) in consolidation_plan.knowledge_schema.get('relationships', []):
                if subj and rel and obj:
                    if hasattr(self.kg, 'add_relation'):
                        self.kg.add_relation(subj, rel, obj)
                        edges_added += 1

        self.hrm_metrics['kg_nodes_added'] += nodes_added
        self.hrm_metrics['kg_edges_added'] += edges_added

        logger.info(f"KG refinement: +{nodes_added} nodes, +{edges_added} edges")

        return {
            'nodes_added': nodes_added,
            'edges_added': edges_added,
            'total_nodes': len(self.kg.entities) if hasattr(self, 'kg') and hasattr(self.kg, 'entities') else 0,
            'total_edges': len(self.kg.relations) if hasattr(self, 'kg') and hasattr(self.kg, 'relations') else 0
        }

    def _generate_consolidation_signals(
        self,
        consolidation_plan: SemanticConsolidationPlan
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate Consolidation Signals for L Modules
        为L模块生成巩固信号

        Args:
            consolidation_plan: Consolidation plan

        Returns:
            Dictionary of consolidation signals
        """
        consolidation_signals = {}

        # Signal to Hippocampus: promote high-importance episodic to semantic
        if consolidation_plan.source_memories:
            hippocampus_signal = ConsolidationSignal(
                target_region='hippocampus',
                action='promote_to_semantic',
                memory_ids=consolidation_plan.source_memories,
                consolidation_priority=consolidation_plan.confidence
            )

            consolidation_signals['hippocampus'] = {
                'action': hippocampus_signal.action,
                'memory_ids': hippocampus_signal.memory_ids,
                'priority': hippocampus_signal.consolidation_priority
            }

            self.consolidation_signals_sent.append(hippocampus_signal)
            self.hrm_metrics['episodic_to_semantic_conversions'] += len(consolidation_plan.source_memories)

        logger.debug(f"Generated {len(consolidation_signals)} consolidation signals")

        return consolidation_signals

    def get_hrm_status(self) -> Dict[str, Any]:
        """
        Get HRM-specific status
        获取HRM特定状态

        Returns:
            Status dictionary
        """
        return {
            'last_consolidation_step': self.last_consolidation_step,
            'consolidation_interval': self.consolidation_interval,
            'current_consolidation_plan': {
                'goal': self.consolidation_plan.consolidation_goal if self.consolidation_plan else None,
                'target_concepts': self.consolidation_plan.target_concepts if self.consolidation_plan else [],
                'confidence': self.consolidation_plan.confidence if self.consolidation_plan else 0.0
            } if self.consolidation_plan else None,
            'abstract_schemas': {
                'concept_hierarchies_count': len(self.abstract_schemas['concept_hierarchies']),
                'schema_templates_count': len(self.abstract_schemas['schema_templates']),
                'consolidation_queue_count': len(self.abstract_schemas['consolidation_queue'])
            },
            'consolidation_signals_sent': len(self.consolidation_signals_sent),
            'metrics': self.hrm_metrics
        }
