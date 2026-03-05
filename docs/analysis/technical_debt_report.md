# BMAM Technical Debt & Framework Defect Report

**Date**: 2025-12-16
**Analysis Scope**: `/BMAM/src/` (~295 Python files, ~81,879 lines)

---

## Executive Summary

| Category | Count | Severity |
|----------|-------|----------|
| TODO/FIXME Items | 15+ | Medium |
| Empty Implementations (pass) | 60+ | High |
| Mock/Placeholder Code | 30+ | Medium |
| Legacy/Deprecated Code | 50+ | Low-Medium |
| Hardcoded Values | 100+ | Medium |
| Missing Features | 3 | High |
| Confirmed Defects | 4 | Critical |

---

## 1. Confirmed Critical Defects (Must Fix)

### 1.1 Emotion Congruency Disabled
**File**: `src/brain/emotion_modulator.py:58-62`
```python
# DEFECT: congruency_boost 返回 0.0，情绪一致性调节被禁用
def _calculate_mood_congruency(self, current_mood: str, memory_emotion: str) -> float:
    # 当前返回 0.0，导致情绪一致性记忆增强无效
```
**Impact**: Emotion-congruent memory retrieval does not work
**Fix**: Implement actual mood-emotion similarity calculation

### 1.2 Prefrontal route_query Empty
**File**: `src/agents/brain_regions/prefrontal_agent/prefrontal_agent.py:325-335`
```python
async def route_query(self, query: str, context: Dict) -> Dict[str, Any]:
    pass  # DEFECT: 空实现，无法路由查询
```
**Impact**: Prefrontal routing logic is non-functional
**Fix**: Implement query routing to appropriate brain regions

### 1.3 Knowledge Graph Legacy Storage
**File**: `src/utils/knowledge_graph_builder.py:75-77`
```python
# 🔥 2025-12-16: Legacy storage (DEPRECATED)
# self.kg 存储是废弃的，但仍然是主要存储路径
```
**Impact**: KG data may be stored in deprecated format
**Fix**: Migrate to unified KG storage

### 1.4 UI Mock/Placeholder Data
**File**: `src/ui/web_ui_server/handlers.py`
```python
# Line 152: 'avg_importance': 0.5, # Placeholder
# Line 269: 'health_score': 'GOOD' # Dynamic logic can be added later
```
**Impact**: Dashboard shows fake/static data
**Fix**: Connect to actual metrics collectors

---

## 2. Empty Implementations (60+ instances)

### 2.1 Interface Definitions (Expected)
These are abstract interface definitions - NOT defects:
- `core/interfaces/agent_interface.py` (10 methods)
- `core/interfaces/memory_interface.py` (20 methods)
- `core/interfaces/message_bus_interface.py` (8 methods)
- `core/interfaces/search_interface.py` (5 methods)

### 2.2 Actual Missing Implementations (DEFECTS)
| File | Line | Issue |
|------|------|-------|
| `services/remote_brain_service.py` | 62, 67 | `download_file`, `upload_file` - TODO stubs |
| `services/brain_service.py` | 82 | Memory count retrieval incomplete |
| `ui/voice_anime_ui.py` | 357, 363, 409 | STT/TTS/Memory update not implemented |
| `agents/memory_interface.py` | 19-40 | 5 empty interface methods |
| `coordination/learning_manager.py` | 300 | Auto conflict resolution not implemented |

---

## 3. TODO/FIXME Items (15+ items)

### High Priority
| Location | Description |
|----------|-------------|
| `services/remote_brain_service.py:61,66` | File download/upload not implemented |
| `services/brain_service.py:81` | Get real count from DB |
| `coordination/learning_manager.py:300` | Auto conflict resolution needs LLM |
| `brain/collaborative_output.py:217` | Confidence calculation is hardcoded |

### Medium Priority
| Location | Description |
|----------|-------------|
| `ui/voice_anime_ui.py:357` | Integrate with actual STT service |
| `ui/voice_anime_ui.py:363` | Integrate with actual TTS service |
| `agents/environment/data_sources.py:522` | Wikidata search not implemented |
| `memory/memory_system/advanced_memory_system.py:159` | Remove deprecated code in next version |

---

## 4. Mock/Placeholder Code (30+ instances)

### 4.1 Testing Infrastructure (Acceptable)
- `core/adapters/memory_system_adapter.py:28` - Mock testing infrastructure
- `agents/environment/data_sources.py:160-245` - MockDataSource for testing
- `agents/memory_interface.py:43-55` - MockMemorySystem for tests
- `evaluation/ai_evaluator.py:65-396` - SimulatedFeedback for evaluation

### 4.2 Production Code with Placeholders (DEFECTS)
| File | Line | Issue |
|------|------|-------|
| `services/brain_service.py` | 87-89 | Placeholder stats returned |
| `ui/web_ui_server/handlers.py` | 152 | avg_importance hardcoded to 0.5 |
| `ui/web_ui_server/handlers.py` | 269 | health_score hardcoded to 'GOOD' |
| `coordination/memory_coordinator.py` | 344 | Summary placeholder text |
| `ui/voice_anime_ui.py` | 323, 346 | STT/TTS are placeholders |
| `agents/core/stress_response/stress_modulation.py` | 70, 154 | Simulated stress hormones |

### 4.3 Fallback Mock Data (Acceptable but Risky)
| File | Line | Issue |
|------|------|-------|
| `agents/core/memory_retrieval/memory_retrieval.py` | 399-467 | `_mock_exploration` fallback |
| `ui/static/brain-viz.js` | 161-181 | Mock data for testing |

---

## 5. Legacy/Deprecated Code (50+ instances)

### 5.1 Adapter Pattern (Intentional - OK)
The `core/adapters/` directory contains adapters to bridge legacy code:
- `EmbeddingServiceAdapter` - bridges legacy embedding service
- `MemorySystemAdapter` - bridges legacy memory system
- `VectorDatabaseAdapter` - bridges legacy FAISS
- `AgentAdapter` - bridges legacy agents

**Status**: Working as designed, not technical debt.

### 5.2 Deprecated Modules (Should Migrate)
| File | Issue |
|------|-------|
| `memory/memory_system/advanced_memory_system.py:158-165` | Direct import deprecated |
| `memory/memory_system/__init__.py:69,94-102` | Backward compatibility shim |
| `memory/brain_regions/prefrontal_inference_rules.py:4` | Deprecated in Phase 2 |
| `utils/knowledge_graph_builder.py:599-686` | Legacy memory dict storage |

### 5.3 Legacy Format Support (Archive - OK)
| File | Issue |
|------|-------|
| `memory/memory_archive.py:570-724` | v1.0.0 legacy format support |

---

## 6. Hardcoded Values (100+ instances)

### 6.1 Critical Hardcoded Values (Should Externalize)
| File | Line | Value | Should Be |
|------|------|-------|-----------|
| `brain/emotion_modulator.py` | 59 | `base_weight: float = 1.0` | Config |
| `brain/region_activation.py` | 78-79 | `inhibition_strength = 0.3`, `winner_threshold = 0.6` | Config |
| `memory/silent_engram.py` | 55-60 | Multiple threshold values | Config |
| `learning/feedback_loop.py` | 65 | `confidence_threshold: float = 0.6` | Config |
| `brain/habit_learner.py` | 51 | `alpha = 0.1` (learning rate) | Config |
| `memory/knowledge_graph.py` | 394 | PageRank `alpha: float = 0.85` | Config |

### 6.2 Acceptable Default Values
Many numeric defaults (0.0, 0.5, 1.0) are acceptable initialization values.

---

## 7. Missing Features (High Priority)

### 7.1 Theory of Mind
**Status**: Not implemented
**Design**: See `docs/design/cognitive_enhancement_design.md`
**Configs**: Created in `configs/theory_of_mind/`

### 7.2 Story Arc / Narrative Tracking
**Status**: Not implemented
**Design**: See `docs/design/cognitive_enhancement_design.md`
**Configs**: Created in `configs/story_arc/`

### 7.3 Amygdala Attention Enhancement
**Status**: Partially implemented
**Design**: See `docs/design/cognitive_enhancement_design.md`
**Configs**: Created in `configs/amygdala/`

---

## 8. Error Handling Issues

### 8.1 Silent Exception Swallowing
Multiple instances of:
```python
except Exception:
    pass
```

**Locations**:
- `utils/experiment_config.py:137`
- `services/shared_openai_client.py:113`
- `coordination/learning_manager.py:76,441`
- `memory/storage_coordinator.py:169,232`
- `agents/brain_regions/hippocampus_agent/storage.py:116,377`

**Risk**: Errors are silently ignored, making debugging difficult.

### 8.2 Overly Broad Exception Handling
Many files use `except Exception as e:` which catches all exceptions.
**Recommendation**: Use specific exception types where possible.

---

## 9. Disabled/Skipped Features

### 9.1 Intentionally Disabled
| File | Line | Feature |
|------|------|---------|
| `utils/experiment_config.py` | 69 | `spacy_enabled: bool = False` - Prevents KG pollution |
| `archived/disabled_plasticity/` | - | Hebbian plasticity disabled |

### 9.2 Skip Conditions in Code
| File | Line | Condition |
|------|------|-----------|
| `coordination/memory_coordinator.py` | 1077-1079 | Skip prefrontal/amygdala/basal_ganglia in fallback |
| `memory/background_memory_processes.py` | 344 | Skip memories with negative feedback |
| `coordination/agent_lifecycle.py` | 129,134 | Skip stress analysis for greetings |

---

## 10. Architectural Observations

### 10.1 Positive Patterns
- Clean interface definitions in `core/interfaces/`
- Adapter pattern for legacy code migration
- Configuration externalization started (YAML configs)
- Dependency injection container in `core/container.py`

### 10.2 Areas for Improvement
1. **Inconsistent logging levels**: Mix of `logger.debug`, `logger.info`, `logger.warning`
2. **Large files**: Some files exceed 1000 lines (e.g., `brain_coordinator_refactored.py`)
3. **Circular dependencies**: Some modules have complex import chains
4. **Test coverage**: No comprehensive test suite observed

---

## 11. Recommended Priorities

### Immediate (P0) - 1 Week
1. Fix emotion congruency calculation (`emotion_modulator.py`)
2. Implement prefrontal `route_query` method
3. Replace UI placeholder values with real metrics

### Short-term (P1) - 2 Weeks
1. Implement Theory of Mind module
2. Implement Story Arc tracking
3. Enhance Amygdala attention system

### Medium-term (P2) - 1 Month
1. Migrate legacy KG storage to unified system
2. Externalize remaining hardcoded values to configs
3. Improve error handling (no silent `pass`)

### Long-term (P3) - 3 Months
1. Complete STT/TTS integration
2. Remove deprecated code paths
3. Add comprehensive test suite

---

## Appendix: File Statistics

| Category | Files | Lines |
|----------|-------|-------|
| Total Python files | ~295 | ~81,879 |
| Core interfaces | 5 | ~500 |
| Brain regions | 15 | ~8,000 |
| Memory system | 25 | ~12,000 |
| Coordination | 20 | ~15,000 |
| Agents | 40 | ~20,000 |
| Utils | 30 | ~8,000 |
| UI | 15 | ~3,000 |
