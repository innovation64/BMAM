# Knowledge Graph Unification Plan
# 知识图谱统一方案

**Date:** 2025-11-10
**Status:** 🔴 Critical Issue - Dual KG Systems Not Synchronized
**Priority:** P0 - High Priority Fix

---

## Problem Analysis | 问题分析

### Current Situation | 当前状况

**两套KG系统并存且不同步：**

```
┌─────────────────────────────────────────────────────────┐
│  System 1: KnowledgeGraphBuilder (Memory Dict)          │
│  File: src/utils/knowledge_graph_builder.py            │
│  Storage: self.knowledge_graph = {                      │
│      'entities': {},                                    │
│      'relations': []                                    │
│  }                                                      │
│  Status: ✅ 被Hippocampus使用                            │
└─────────────────────────────────────────────────────────┘
                            ⊥ 不同步
┌─────────────────────────────────────────────────────────┐
│  System 2: LightweightKnowledgeGraph (NetworkX)         │
│  File: src/memory/knowledge_graph.py                   │
│  Storage: NetworkX.DiGraph + 持久化到文件                 │
│  Status: ❌ 未被使用（或仅部分使用）                       │
└─────────────────────────────────────────────────────────┘
```

---

## Root Cause | 根本原因

### Code Flow Analysis | 代码流程分析

**场景1：Hippocampus存储记忆**

```python
# File: src/agents/brain_regions/hippocampus_agent/storage.py (line 165)
await self._update_knowledge_graph(memory, kg_entity_payload, extracted_relations)

# Line 198
self.kg_builder.add_to_graph(builder_entities, builder_relations)
                    ↓
# File: src/utils/knowledge_graph_builder.py (line 565)
def add_to_graph(self, entities: List[Dict], relations: List[Dict]):
    # ❌ 只更新内存字典
    for entity in entities:
        self.knowledge_graph['entities'][name] = entity

    for relation in relations:
        self.knowledge_graph['relations'].append(triple)

    # ❌ 没有调用 self.kg.add_node() 或 self.kg.add_edge()
```

**结果：**
- ✅ KnowledgeGraphBuilder内存字典有数据
- ❌ LightweightKnowledgeGraph NetworkX图为空

---

**场景2：KnowledgeGraphBuilder提取实体**

```python
# File: src/utils/knowledge_graph_builder.py (line 139)
if self.kg:
    self._persist_to_kg(entities, relations)  # ✅ 会同步到NetworkX

# Line 172-189
self.kg.add_node(...)
self.kg.add_edge(...)
```

**结果：**
- ✅ 如果调用`extract_from_text()`，会同步到NetworkX
- ❌ 但Hippocampus通过`add_to_graph()`添加，不会同步

---

## Evidence | 证据

### 1. Hippocampus调用路径

```
storage.py:165  →  _update_knowledge_graph()
              ↓
storage.py:198  →  kg_builder.add_to_graph()  ← ❌ 这里不同步
```

### 2. add_to_graph()源码

```python
# knowledge_graph_builder.py:565-585
def add_to_graph(self, entities: List[Dict], relations: List[Dict]):
    """将实体和关系添加到知识图谱"""
    # 只更新内存字典
    for entity in entities:
        name = entity['name']
        if name not in self.knowledge_graph['entities']:
            self.knowledge_graph['entities'][name] = entity
        # ... 没有 self.kg.add_node() 调用

    for relation in relations:
        triple = (relation['source'], relation['relation'], relation['target'])
        if triple not in self.knowledge_graph['relations']:
            self.knowledge_graph['relations'].append(triple)
        # ... 没有 self.kg.add_edge() 调用
```

**问题：** `add_to_graph()` 完全忽略 `self.kg` 实例！

---

## Verification Test | 验证测试

### Test 1: Check Memory Dict (应该有数据)

```python
from src.utils.knowledge_graph_builder import KnowledgeGraphBuilder

kg_builder = KnowledgeGraphBuilder()

# 模拟Hippocampus调用
entities = [{'name': 'Caroline', 'type': 'Person', 'mentions': 1}]
relations = [{'source': 'Caroline', 'relation': 'researches', 'target': 'adoption'}]

kg_builder.add_to_graph(entities, relations)

stats = kg_builder.get_statistics()
print(stats)
# Expected: {'total_entities': 1, 'total_relations': 1}
# ✅ 应该有数据（内存字典）
```

### Test 2: Check NetworkX Graph (应该为空)

```python
from src.memory.knowledge_graph import LightweightKnowledgeGraph
from src.utils.knowledge_graph_builder import KnowledgeGraphBuilder

# 创建统一KG
kg = LightweightKnowledgeGraph(save_dir="data/test_kg_unified")
kg_builder = KnowledgeGraphBuilder(kg_instance=kg)

# 模拟Hippocampus调用
entities = [{'name': 'Caroline', 'type': 'Person', 'mentions': 1}]
relations = [{'source': 'Caroline', 'relation': 'researches', 'target': 'adoption'}]

kg_builder.add_to_graph(entities, relations)  # ❌ 不会同步到kg

# 检查NetworkX
kg_stats = kg.get_statistics()
print(kg_stats)
# Expected: {'total_nodes': 0, 'total_edges': 0}
# ❌ 应该为空（因为add_to_graph不同步）
```

### Test 3: Compare extract_from_text vs add_to_graph

```python
# 方式1：使用extract_from_text（会同步）
entities1, relations1 = await kg_builder.extract_from_text(
    "Caroline researched adoption agencies in Sweden"
)
print("After extract_from_text:")
print("Memory Dict:", kg_builder.get_statistics())
print("NetworkX:", kg.get_statistics())
# ✅ 两者都有数据

# 方式2：使用add_to_graph（不会同步）
kg_builder.add_to_graph(entities1, relations1)
print("\nAfter add_to_graph:")
print("Memory Dict:", kg_builder.get_statistics())
print("NetworkX:", kg.get_statistics())
# ❌ Memory Dict有数据，NetworkX没变化
```

---

## Solution | 解决方案

### Option 1: Fix add_to_graph() (Quick Fix - 推荐)

**修改 `src/utils/knowledge_graph_builder.py`**

```python
def add_to_graph(self, entities: List[Dict], relations: List[Dict]):
    """将实体和关系添加到知识图谱"""

    # 1. 添加到内存字典（向后兼容）
    for entity in entities:
        name = entity['name']
        if name not in self.knowledge_graph['entities']:
            self.knowledge_graph['entities'][name] = entity
        else:
            self.knowledge_graph['entities'][name]['mentions'] = \
                self.knowledge_graph['entities'][name].get('mentions', 0) + \
                entity.get('mentions', 0)

    for relation in relations:
        triple = (relation['source'], relation['relation'], relation['target'])
        if triple not in self.knowledge_graph['relations']:
            self.knowledge_graph['relations'].append(triple)

    # ✅ 2. 同步到NetworkX（新增）
    if self.kg:
        self._persist_to_kg(entities, relations)

    logger.debug(f"📊 KG stats: {len(self.knowledge_graph['entities'])} entities, "
                f"{len(self.knowledge_graph['relations'])} relations")
```

**优点：**
- ✅ 最小改动（1行代码）
- ✅ 向后兼容
- ✅ 立即生效

**缺点：**
- ⚠️ 仍然维护双重存储

---

### Option 2: Create Unified KG Interface (正确但复杂)

**创建统一接口 `src/core/interfaces/knowledge_graph_interface.py`**

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional

class IKnowledgeGraph(ABC):
    """
    Unified Knowledge Graph Interface
    统一知识图谱接口
    """

    @abstractmethod
    def add_node(
        self,
        node_id: str,
        entity_type: str,
        content: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add entity node"""
        pass

    @abstractmethod
    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        strength: float = 1.0,
        properties: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add relation edge"""
        pass

    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """Get KG statistics"""
        pass

    @abstractmethod
    def query_neighbors(
        self,
        node_id: str,
        max_depth: int = 1
    ) -> List[Dict[str, Any]]:
        """Query node neighbors"""
        pass
```

**让 LightweightKnowledgeGraph 实现接口**

```python
class LightweightKnowledgeGraph(IKnowledgeGraph):
    """NetworkX-based KG implementation"""

    def add_node(self, node_id: str, entity_type: str, content: str,
                 properties: Optional[Dict[str, Any]] = None) -> str:
        # 现有实现
        pass

    def add_edge(self, source_id: str, target_id: str, relation_type: str,
                 strength: float = 1.0, properties: Optional[Dict[str, Any]] = None) -> str:
        # 现有实现
        pass
```

**KnowledgeGraphBuilder 只提取，不存储**

```python
class KnowledgeGraphBuilder:
    """KG Extraction Tool (no storage)"""

    def __init__(self, llm_client=None, use_spacy: bool = True, kg: IKnowledgeGraph = None):
        self.llm_client = llm_client
        self.use_spacy = use_spacy
        self.kg = kg  # ✅ 强制使用统一接口

        # ❌ 移除内存字典（或标记为废弃）
        # self.knowledge_graph = {...}

    def add_to_graph(self, entities: List[Dict], relations: List[Dict]):
        """添加到KG（通过统一接口）"""
        if not self.kg:
            logger.warning("No KG instance provided, entities/relations discarded")
            return

        # ✅ 直接使用统一接口
        for entity in entities:
            self.kg.add_node(
                node_id=entity['name'],
                entity_type=entity.get('type', 'Concept'),
                content=entity['name'],
                properties={'mentions': entity.get('mentions', 1)}
            )

        for relation in relations:
            self.kg.add_edge(
                source_id=relation['source'],
                target_id=relation['target'],
                relation_type=relation['relation']
            )
```

**优点：**
- ✅ 单一数据源
- ✅ 符合DI架构
- ✅ 可测试性强
- ✅ 易于扩展（可替换不同KG实现）

**缺点：**
- ⚠️ 需要修改所有调用方
- ⚠️ 破坏向后兼容性

---

### Option 3: Hybrid Approach (折中方案)

**阶段1：修复同步（立即）**
- 在`add_to_graph()`中调用`_persist_to_kg()`
- 保持双重存储但同步

**阶段2：统一接口（2周内）**
- 创建`IKnowledgeGraph`接口
- `LightweightKnowledgeGraph`实现接口
- 注册到DI容器

**阶段3：迁移（4周内）**
- 逐步将`KnowledgeGraphBuilder`改为只提取
- 废弃内存字典
- 统一使用`IKnowledgeGraph`

**阶段4：清理（8周内）**
- 移除遗留代码
- 更新文档
- 性能优化

---

## Implementation Steps | 实施步骤

### Step 1: Quick Fix (Today - 30分钟)

```python
# File: src/utils/knowledge_graph_builder.py

def add_to_graph(self, entities: List[Dict], relations: List[Dict]):
    """将实体和关系添加到知识图谱（同步到统一KG）"""

    # Legacy storage (backward compatibility)
    for entity in entities:
        name = entity['name']
        if name not in self.knowledge_graph['entities']:
            self.knowledge_graph['entities'][name] = entity
        else:
            self.knowledge_graph['entities'][name]['mentions'] = \
                self.knowledge_graph['entities'][name].get('mentions', 0) + \
                entity.get('mentions', 0)

    for relation in relations:
        triple = (relation['source'], relation['relation'], relation['target'])
        if triple not in self.knowledge_graph['relations']:
            self.knowledge_graph['relations'].append(triple)

    # ✅ NEW: Sync to unified KG
    if self.kg:
        logger.debug(f"Syncing {len(entities)} entities and {len(relations)} relations to unified KG")
        self._persist_to_kg(entities, relations)
    else:
        logger.warning("⚠️ No unified KG instance - using legacy memory dict only")

    logger.debug(f"📊 KG stats: {len(self.knowledge_graph['entities'])} entities, "
                f"{len(self.knowledge_graph['relations'])} relations")
```

### Step 2: Verification Test (Today - 15分钟)

创建 `tests/integration/test_kg_unified.py`:

```python
import pytest
from src.memory.knowledge_graph import LightweightKnowledgeGraph
from src.utils.knowledge_graph_builder import KnowledgeGraphBuilder

@pytest.mark.integration
def test_add_to_graph_syncs_to_networx():
    """Test that add_to_graph() syncs to NetworkX"""

    # Setup
    kg = LightweightKnowledgeGraph(save_dir="data/test_kg_sync")
    kg_builder = KnowledgeGraphBuilder(kg_instance=kg)

    # Add via add_to_graph
    entities = [{'name': 'Caroline', 'type': 'Person', 'mentions': 1}]
    relations = [{'source': 'Caroline', 'relation': 'researches', 'target': 'adoption'}]

    kg_builder.add_to_graph(entities, relations)

    # Verify memory dict
    memory_stats = kg_builder.get_statistics()
    assert memory_stats['total_entities'] == 1
    assert memory_stats['total_relations'] == 1

    # ✅ Verify NetworkX (should now have data)
    kg_stats = kg.get_statistics()
    assert kg_stats['total_nodes'] >= 2  # Caroline + adoption
    assert kg_stats['total_edges'] >= 1

    # Verify specific nodes
    caroline_node = kg.get_node('Caroline')
    assert caroline_node is not None
    assert caroline_node.entity_type == 'person'

@pytest.mark.integration
async def test_hippocampus_kg_persistence():
    """Test that Hippocampus memory storage persists to NetworkX"""

    from src.agents.brain_regions.hippocampus_agent.core import HippocampusAgentCore
    from src.memory.knowledge_graph import LightweightKnowledgeGraph
    from src.utils.knowledge_graph_builder import KnowledgeGraphBuilder

    # Setup unified KG
    kg = LightweightKnowledgeGraph(save_dir="data/test_hippocampus_kg")
    kg_builder = KnowledgeGraphBuilder(kg_instance=kg)

    # Create Hippocampus with unified KG
    hippocampus = HippocampusAgentCore(
        kg_builder=kg_builder
    )

    # Store memory with entities
    result = await hippocampus.store_memory(
        content="Caroline researched adoption agencies in Sweden",
        entities=['Caroline', 'Sweden'],
        auto_extract_kg=True
    )

    # Verify entities extracted
    assert len(result['entities_extracted']) > 0

    # ✅ Verify NetworkX has data
    kg_stats = kg.get_statistics()
    assert kg_stats['total_nodes'] > 0
    assert kg_stats['total_edges'] > 0

    print(f"✅ NetworkX KG: {kg_stats['total_nodes']} nodes, {kg_stats['total_edges']} edges")
```

### Step 3: Update Hippocampus Initialization (Today - 10分钟)

```python
# File: src/coordination/brain_coordinator_refactored.py

def _initialize_agents(self):
    """初始化所有智能体"""

    # 1. 创建统一KG
    from src.memory.knowledge_graph import LightweightKnowledgeGraph
    from src.utils.knowledge_graph_builder import KnowledgeGraphBuilder

    self.unified_kg = LightweightKnowledgeGraph(save_dir="data/unified_kg")
    self.kg_builder = KnowledgeGraphBuilder(
        llm_client=self.client,
        use_spacy=True,
        kg_instance=self.unified_kg  # ✅ 传入统一KG
    )

    # 2. 创建Hippocampus（使用统一KG）
    self.hippocampus = HippocampusAgent(
        kg_builder=self.kg_builder  # ✅ 使用带统一KG的builder
    )
```

### Step 4: Add Logging/Debugging (Today - 5分钟)

```python
# In add_to_graph()
if self.kg:
    before_stats = self.kg.get_statistics()
    self._persist_to_kg(entities, relations)
    after_stats = self.kg.get_statistics()

    logger.info(
        f"✅ KG Sync: {before_stats['total_nodes']} → {after_stats['total_nodes']} nodes, "
        f"{before_stats['total_edges']} → {after_stats['total_edges']} edges"
    )
else:
    logger.warning("⚠️ No unified KG - data only in memory dict")
```

---

## Expected Outcomes | 预期结果

### Before Fix | 修复前

```python
kg_builder.add_to_graph(entities, relations)

# Memory Dict: ✅ Has data
kg_builder.get_statistics()
# → {'total_entities': 10, 'total_relations': 15}

# NetworkX: ❌ Empty
kg.get_statistics()
# → {'total_nodes': 0, 'total_edges': 0}
```

### After Fix | 修复后

```python
kg_builder.add_to_graph(entities, relations)

# Memory Dict: ✅ Has data
kg_builder.get_statistics()
# → {'total_entities': 10, 'total_relations': 15}

# NetworkX: ✅ Also has data
kg.get_statistics()
# → {'total_nodes': 12, 'total_edges': 15}
```

---

## Testing Checklist | 测试清单

- [ ] **Test 1:** `add_to_graph()` syncs to NetworkX
- [ ] **Test 2:** `extract_from_text()` still works
- [ ] **Test 3:** Hippocampus storage persists to NetworkX
- [ ] **Test 4:** `get_statistics()` matches between memory dict and NetworkX
- [ ] **Test 5:** File persistence works (`data/unified_kg/nodes.json`)
- [ ] **Test 6:** Query operations work on NetworkX
- [ ] **Test 7:** Backward compatibility (existing code still works)

---

## Monitoring | 监控

### Log Messages to Watch

```
✅ Good:
- "Syncing X entities and Y relations to unified KG"
- "KG Sync: 10 → 15 nodes, 8 → 12 edges"

⚠️ Warning:
- "No unified KG instance - using legacy memory dict only"

❌ Error:
- "Failed to persist to unified KG: <error>"
```

### Debug Commands

```python
# Check memory dict
stats_mem = kg_builder.get_statistics()
print(f"Memory Dict: {stats_mem}")

# Check NetworkX
stats_nx = kg_builder.kg.get_statistics() if kg_builder.kg else {}
print(f"NetworkX: {stats_nx}")

# Compare
if stats_mem != stats_nx:
    print("⚠️ MISMATCH DETECTED!")
```

---

## Next Steps | 后续步骤

**Phase 1 (Today):**
1. ✅ Fix `add_to_graph()` to sync to NetworkX
2. ✅ Write verification tests
3. ✅ Update coordinator initialization

**Phase 2 (This Week):**
4. Create `IKnowledgeGraph` interface
5. Register to DI container
6. Update documentation

**Phase 3 (Next 2 Weeks):**
7. Deprecate memory dict storage
8. Migrate all code to use `IKnowledgeGraph`
9. Remove legacy code

---

## Conclusion | 结论

**当前问题：**
- ❌ `add_to_graph()` 只更新内存字典
- ❌ NetworkX图为空
- ❌ 推理链无法访问KG

**解决方案：**
- ✅ 在`add_to_graph()`中调用`_persist_to_kg()`
- ✅ 1行代码修复
- ✅ 立即生效

**长期目标：**
- 统一KG接口
- 单一数据源
- DI架构集成

---

**Status:** ⏳ Ready for Implementation
**ETA:** 1 hour
**Risk:** Low (minimal code change)
