# 知识图谱系统使用指南

## 概述

BMAM集成了轻量级知识图谱系统，基于NetworkX实现，提供实体-关系-实体三元组存储、图遍历、PageRank分析等功能。

## 架构

```
┌─────────────────────────────────────────────────┐
│         Knowledge Graph System                  │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────────┐    ┌──────────────────┐      │
│  │   Nodes     │    │      Edges       │      │
│  │  (实体)     │───▶│   (关系)         │      │
│  └─────────────┘    └──────────────────┘      │
│                                                 │
│  ┌──────────────────────────────────────┐     │
│  │      NetworkX MultiDiGraph          │     │
│  │  • 有向多重图                         │     │
│  │  • 支持多种关系                       │     │
│  │  • 内存高效                           │     │
│  └──────────────────────────────────────┘     │
│                                                 │
│  ┌──────────────────────────────────────┐     │
│  │      Graph Algorithms                │     │
│  │  • PageRank                          │     │
│  │  • 社区检测                           │     │
│  │  • 路径查询                           │     │
│  │  • 中心性分析                         │     │
│  └──────────────────────────────────────┘     │
└─────────────────────────────────────────────────┘
```

## 核心功能

### 1. 实体类型

```python
class EntityType:
    PERSON = "person"          # 人物
    CONCEPT = "concept"        # 概念
    EVENT = "event"           # 事件
    OBJECT = "object"         # 物体
    LOCATION = "location"     # 地点
    TIME = "time"             # 时间
    MEMORY = "memory"         # 记忆
```

### 2. 关系类型

```python
class RelationType:
    RELATED_TO = "related_to"      # 通用关联
    CAUSES = "causes"              # 因果关系
    PART_OF = "part_of"           # 部分-整体
    HAPPENED_AT = "happened_at"    # 发生时间
    LOCATED_AT = "located_at"     # 位置关系
    INVOLVES = "involves"          # 涉及
    SIMILAR_TO = "similar_to"     # 相似
    DERIVED_FROM = "derived_from" # 派生自
    CO_OCCURS = "co_occurs"       # 共现
```

## 基本使用

### 初始化

```python
from src.memory.knowledge_graph import (
    LightweightKnowledgeGraph,
    EntityType,
    RelationType
)

# 创建知识图谱实例
kg = LightweightKnowledgeGraph(save_dir="data/knowledge_graph")
```

### 添加节点

```python
# 添加人物节点
kg.add_node(
    node_id="person_alice",
    entity_type=EntityType.PERSON,
    content="Alice",
    properties={"age": 25, "occupation": "AI研究员"}
)

# 添加概念节点
kg.add_node(
    node_id="concept_ai",
    entity_type=EntityType.CONCEPT,
    content="人工智能",
    properties={"field": "计算机科学"}
)
```

### 添加关系

```python
# 添加"相关"关系
kg.add_edge(
    source_id="person_alice",
    target_id="concept_ai",
    relation_type=RelationType.RELATED_TO,
    strength=0.9,
    properties={"confidence": "high"}
)
```

### 查询操作

```python
# 获取节点
node = kg.get_node("person_alice")

# 获取邻居
neighbors = kg.get_neighbors("person_alice")

# 获取特定关系的邻居
ai_related = kg.get_neighbors(
    "person_alice",
    relation_type=RelationType.RELATED_TO
)

# 查找路径
path = kg.find_shortest_path("person_alice", "concept_ml")

# 查找所有路径
all_paths = kg.find_paths(
    "person_alice",
    "concept_ml",
    max_depth=3
)

# 搜索节点
results = kg.search_nodes("人工智能", entity_type=EntityType.CONCEPT)
```

### 图算法

```python
# PageRank中心性
pagerank = kg.compute_pagerank()
top_nodes = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)[:10]

# 多种中心性指标
centrality = kg.compute_centrality()
print(f"度中心性: {centrality['degree']}")
print(f"PageRank: {centrality['pagerank']}")

# 社区检测
communities = kg.detect_communities()
print(f"检测到 {len(communities)} 个社区")

# 上下文扩展 (k-hop邻居)
context = kg.expand_context("person_alice", depth=2)

# 查找相似节点
similar = kg.find_similar_nodes("person_alice", top_k=5)
```

## 与记忆系统集成

### 自动构建KG

```python
from src.memory.kg_integration import kg_integration

# 从单个记忆构建
result = await kg_integration.build_kg_from_memory(memory_id)

# 批量构建
result = await kg_integration.batch_build_kg(limit=100)
```

### 图增强检索

```python
# 普通检索
normal_results = await memory_system.search_memories("Alice学习AI", k=5)

# 图增强检索 (会扩展上下文)
enhanced_results = await kg_integration.graph_enhanced_retrieval(
    "Alice学习AI",
    k=5
)
# 返回结果包含直接匹配 + 图扩展的相关记忆
```

### 查找记忆关联

```python
# 查找某条记忆的关联
associations = await kg_integration.find_memory_associations(
    memory_id="abc-123",
    max_depth=2
)

print(f"相关记忆: {associations['related_memories']}")
print(f"相关实体: {associations['related_entities']}")
print(f"连接路径: {associations['paths']}")
```

### 分析记忆重要性

```python
# 基于PageRank分析记忆重要性
important_memories = await kg_integration.analyze_memory_importance()

for memory in important_memories[:10]:
    print(f"记忆 {memory['memory_id']}")
    print(f"  PageRank: {memory['pagerank']:.4f}")
    print(f"  度: {memory['degree']}")
    print(f"  内容: {memory['content'][:50]}...")
```

### 检测记忆聚类

```python
# 检测记忆聚类
clusters = await kg_integration.detect_memory_clusters()

for i, cluster in enumerate(clusters):
    print(f"聚类 {i}: {len(cluster)} 条记忆")
    # 聚类中的记忆在语义上相关
```

## 高级功能

### 节点合并

```python
# 合并两个相似节点
merged_id = kg.merge_nodes("person_alice1", "person_alice2")
```

### 边强度更新

```python
# 更新关系强度 (基于共现或其他信号)
kg.update_edge_strength(
    "person_alice",
    "concept_ai",
    RelationType.RELATED_TO,
    strength=0.95
)
```

### 弱连接修剪

```python
# 删除强度低于阈值的连接
removed = await kg_integration.prune_weak_connections(threshold=0.1)
print(f"修剪了 {removed} 条弱连接")
```

### 图导出

```python
# 导出为JSON
kg.export_to_json("knowledge_graph_export.json")

# 获取统计信息
stats = kg.get_statistics()
print(f"节点数: {stats['basic']['total_nodes']}")
print(f"边数: {stats['basic']['total_edges']}")
print(f"密度: {stats['graph_properties']['density']}")
```

## 实体和关系提取

系统支持简单的实体和关系提取：

```python
from src.memory.kg_integration import kg_integration

# 提取实体
text = "Alice在北京学习人工智能"
entities = kg_integration.extract_entities(text)
# 结果: [('Alice', 'person'), ('北京', 'location'), ('人工智能', 'concept')]

# 提取关系
relations = kg_integration.extract_relations(text, entities)
# 结果: [('Alice', 'located_at', '北京'), ...]
```

## 性能优化

### 1. 索引优化

系统维护多个索引：
- `entity_type_index`: 按实体类型索引
- `relation_type_index`: 按关系类型索引

```python
# 快速获取某类实体
persons = kg.get_nodes_by_type(EntityType.PERSON)
```

### 2. 批量操作

```python
# 批量添加节点
for entity in entities:
    kg.add_node(entity['id'], entity['type'], entity['content'])

# 批量添加边
for relation in relations:
    kg.add_edge(relation['source'], relation['target'], relation['type'])

# 最后保存
kg.save_graph()
```

### 3. 内存管理

- 图存储在内存中，适合中小规模 (< 100万节点)
- 定期持久化：`kg.save_graph()`
- 自动加载：初始化时自动加载已有数据

## 数据持久化

### 存储格式

```
data/knowledge_graph/
├── graph.pkl        # NetworkX图 (pickle格式)
├── nodes.json       # 节点详细信息
└── edges.json       # 边详细信息
```

### 手动保存/加载

```python
# 保存
kg.save_graph()

# 加载 (初始化时自动)
kg = LightweightKnowledgeGraph(save_dir="data/knowledge_graph")
```

## 可视化

虽然系统不包含可视化功能，但可以导出数据用于可视化：

```python
# 导出JSON
kg.export_to_json("graph_export.json")

# 使用第三方工具可视化
# - Gephi: 导入JSON
# - Cytoscape: 转换格式
# - D3.js: Web可视化
```

## 使用示例

### 示例1: 构建知识网络

```python
import asyncio
from src.memory.kg_integration import kg_integration

async def build_knowledge_network():
    # 存储一系列相关记忆
    memories = [
        "Alice在北京大学学习人工智能",
        "Bob是Alice的导师，研究机器学习",
        "机器学习是人工智能的一个分支",
        "深度学习是机器学习的重要方法"
    ]

    memory_ids = []
    for content in memories:
        mid = await memory_system.store_memory(content)
        memory_ids.append(mid)

    # 批量构建KG
    result = await kg_integration.batch_build_kg(limit=10)
    print(f"构建完成: {result}")

    # 分析网络
    stats = kg_integration.kg.get_statistics()
    print(f"网络统计: {stats}")

asyncio.run(build_knowledge_network())
```

### 示例2: 智能检索

```python
async def smart_retrieval():
    # 普通检索
    normal = await memory_system.search_memories("Alice", k=3)

    # 图增强检索 (会扩展相关实体和记忆)
    enhanced = await kg_integration.graph_enhanced_retrieval("Alice", k=3)

    print(f"普通检索: {len(normal)}条")
    print(f"增强检索: {len(enhanced)}条")

    # 增强检索可能返回:
    # - Alice相关的记忆
    # - Bob相关的记忆 (因为Bob是Alice的导师)
    # - 人工智能相关的记忆 (因为Alice学习AI)

asyncio.run(smart_retrieval())
```

### 示例3: 发现隐藏关联

```python
async def discover_connections():
    # 查找两个看似无关实体的连接
    path = kg_integration.kg.find_shortest_path(
        "person_alice",
        "concept_deep_learning"
    )

    if path:
        print(f"发现连接路径: {' -> '.join(path)}")
        # 可能的路径: Alice -> 人工智能 -> 机器学习 -> 深度学习

    # 扩展上下文
    context = kg_integration.kg.expand_context("person_alice", depth=2)
    print(f"Alice的2-hop上下文包含 {len(context)} 个实体")

asyncio.run(discover_connections())
```

## 最佳实践

1. **定期保存**: 在批量操作后调用`kg.save_graph()`
2. **控制规模**: 定期修剪弱连接，避免图过大
3. **语义一致性**: 使用统一的实体和关系命名
4. **增量构建**: 新记忆产生时实时更新图
5. **定期分析**: 运行PageRank和社区检测发现重要节点

## 限制和注意事项

1. **内存限制**: 适合中小规模图 (< 100万节点)
2. **实体提取**: 当前使用简单规则，可能不够准确
3. **关系识别**: 基于关键词匹配，可能漏掉隐含关系
4. **计算复杂度**: 某些算法 (如PageRank) 在大图上较慢

## 未来扩展

- [ ] 集成NER模型提升实体识别准确率
- [ ] 添加关系抽取模型
- [ ] 支持图嵌入 (Node2Vec, GraphSAGE)
- [ ] 添加可视化接口
- [ ] 支持增量更新PageRank
- [ ] 添加时序图分析

## 参考资料

- NetworkX文档: https://networkx.org/
- 图算法: https://en.wikipedia.org/wiki/Graph_theory
- PageRank: https://en.wikipedia.org/wiki/PageRank
- 社区检测: https://en.wikipedia.org/wiki/Community_structure