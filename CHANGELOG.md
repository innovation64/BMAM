# Changelog

All notable changes to the BMAM project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Regression tests for KG compatibility layer (`tests/test_kg_compatibility.py`)
- Batch consolidation test script for end-to-end validation
- `add_triple()` compatibility method to `LightweightKnowledgeGraph`
- Unified KG documentation in `CONSENSUS_FIX_ANALYSIS.md`

### Fixed
- **[CRITICAL]** Entity/relation extraction now reads from `metadata['entities']` and `metadata['kg_relations']` instead of non-existent `context_tags` field (#1)
- **[CRITICAL]** Added `hasattr()` check for `memory_system` attribute in consolidation pipeline to prevent AttributeError (#2)
- **[CRITICAL]** Added missing `relational_keywords` to `config/query_patterns.json` and `relation_keywords` to `config/kg_query_patterns.json` (#3)
- **[CRITICAL]** Configured unified `LightweightKnowledgeGraph` instance shared across all brain regions via `BrainCoordinator` (#4)
- **[CRITICAL]** Added `add_triple()` method to `LightweightKnowledgeGraph` for API compatibility with `SimpleKnowledgeGraph` (#5)

### Changed
- `TemporalLobeAgent` now accepts optional `unified_kg` parameter for shared knowledge graph
- `KnowledgeGraphBuilder` now accepts optional `kg_instance` parameter for persistent KG storage
- Consolidation pipeline now extracts entities and relations with priority: metadata → context_tags (fallback)

### Performance
- Batch consolidation: 20 memories in 0.15s (7.4ms avg per memory)
- 100% consolidation success rate in end-to-end tests
- Average 4.0 entities extracted per semantic memory

---

## [Phase 4 P1] - 2025-11-13

### Fixed - Memory Consolidation Pipeline
Five critical bugs in memory consolidation and knowledge graph management:

1. **Entity Extraction Bug**: Semantic memories lacked entities/relations due to reading from wrong field
2. **Proxy Attribute Bug**: AgentStorageProxy missing parent class attributes caused potential AttributeError
3. **Config Missing Keys**: Query analysis failed due to missing configuration keys
4. **Unified KG Missing**: Brain regions used separate KG instances instead of shared one
5. **API Incompatibility**: LightweightKnowledgeGraph lacked add_triple() method causing startup failure

**Impact**: End-to-end consolidation pipeline now fully functional with 100% success rate.

**Documentation**: See `docs/development/CONSENSUS_FIX_ANALYSIS.md` for detailed analysis.

---

## [Phase 4 P0] - 2025-11-10

### Achieved
- LoCoMo benchmark: 94% average accuracy (5Q)
- Q2 temporal reasoning: 93% (+14% from Phase 3a)
- Q3 multi-hop reasoning: 95% (+14%)
- Q4 summarization: 94% (+21%)

### Added
- Adaptive memory shaping with event-driven consolidation
- Background memory processes for scheduled consolidation
- Five brain region auto-persistence (Hippocampus, TemporalLobe, Amygdala, Prefrontal, BasalGanglia)
- Memory checkpoint management for version control

---

## [Phase 3] - 2025-11-05

### Added
- Complete memory loop: encoding → consolidation → retrieval → forgetting
- Hippocampus → Temporal Lobe consolidation pipeline
- Hybrid retrieval strategy (BM25 + Vector + KG)
- Auto-persistence with SQLite + JSON dual storage

---

## [Phase 1-2] - 2025-10-20

### Added
- Five brain region architecture
- Basic episodic and semantic memory storage
- Simple knowledge graph implementation
- OpenAI embedding service integration

---

## Release Tags

- **Phase 4 P1**: Memory Consolidation Fixed (2025-11-13)
- **Phase 4 P0**: LoCoMo 94% Accuracy (2025-11-10)
- **Phase 3**: Memory Loop Complete (2025-11-05)
- **Phase 1-2**: Foundation (2025-10-20)
