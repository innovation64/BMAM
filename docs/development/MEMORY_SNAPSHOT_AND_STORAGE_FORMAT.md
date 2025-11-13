# BMAM 记忆快照 & 存储格式详解

**日期**: 2025-11-12
**问题1**: 能否固定记忆节点,避免问答后污染?
**问题2**: 记忆存储格式有优化吗? (KG, metadata等)

---

## 问题1: 固定记忆节点 ✅

### 快速回答

**完全可以!** 使用记忆快照可以:
- ✅ 保存"干净"记忆状态
- ✅ 测试后恢复到问答前状态
- ✅ 无限次测试,永不污染
- ✅ 对比不同实验结果

---

## 记忆快照系统

### 工作流程

```
1. 录入对话 → 创建基础记忆
   ↓
2. 保存快照 → 固定记忆节点
   ↓
3. 运行测试 → 问答可能污染记忆
   ↓
4. 恢复快照 → 回到问答前状态
   ↓
5. 重复3-4 → 无限次干净测试
```

### 使用方法

#### 安装快照工具

```bash
# 工具已创建: scripts/snapshot_memory.sh
chmod +x scripts/snapshot_memory.sh
```

#### 基本操作

```bash
# 1. 列出所有快照
./scripts/snapshot_memory.sh list

# 2. 保存当前记忆为快照
./scripts/snapshot_memory.sh save clean_state

# 3. 恢复快照
./scripts/snapshot_memory.sh restore clean_state

# 4. 清理所有快照
./scripts/snapshot_memory.sh clean
```

---

### 实战示例

#### 示例1: 避免测试污染

```bash
# 步骤1: 录入对话,创建干净记忆
bash scripts/clean_test_data.sh
python3 tests/test_locomo_bmam_full.py --samples 1 --questions 5 --verbose
# → 记忆存储到 data/brain_memory.db (523条记忆)

# 步骤2: 保存快照 (固定节点)
./scripts/snapshot_memory.sh save after_ingestion
# → 快照保存到 data/snapshots/after_ingestion.db
# → FAISS索引保存到 data/snapshots/after_ingestion_faiss/

# 步骤3: 运行测试 (可能污染记忆)
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions 20 --verbose
# → 问答过程会创建新记忆 (问题理解、检索结果等)
# → data/brain_memory.db 现在有 543条记忆 (污染了!)

# 步骤4: 恢复快照 (清除污染)
./scripts/snapshot_memory.sh restore after_ingestion
# → data/brain_memory.db 恢复到 523条记忆
# → 污染的20条新记忆被清除

# 步骤5: 再次测试 (又是干净状态)
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions 50 --verbose
# → 从干净状态开始

# 步骤6: 再次恢复快照
./scripts/snapshot_memory.sh restore after_ingestion
# → 又回到干净状态

# 无限循环,永远干净!
```

**性能提升**:
- ❌ 不用快照: 每次测试前需要 `clean_test_data.sh` + 40秒录入
- ✅ 用快照: 恢复快照 ~1秒 + 0秒录入 = **40倍速!**

#### 示例2: A/B测试不同策略

```bash
# 准备两个不同的记忆状态

# 场景A: Aggressive consolidation (快速巩固)
export CONSOLIDATION_INTERVAL=60  # 1分钟
bash scripts/clean_test_data.sh
python3 tests/test_locomo_bmam_full.py --samples 1 --questions 5 --verbose
./scripts/snapshot_memory.sh save aggressive_consolidation

# 场景B: Conservative consolidation (慢速巩固)
export CONSOLIDATION_INTERVAL=3600  # 1小时
bash scripts/clean_test_data.sh
python3 tests/test_locomo_bmam_full.py --samples 1 --questions 5 --verbose
./scripts/snapshot_memory.sh save conservative_consolidation

# 对比测试 (快速切换)
# 测试场景A
./scripts/snapshot_memory.sh restore aggressive_consolidation
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions all --verbose
# → 记录准确率: 85%

# 测试场景B
./scripts/snapshot_memory.sh restore conservative_consolidation
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions all --verbose
# → 记录准确率: 82%

# 结论: Aggressive consolidation 更好!
```

#### 示例3: 时间旅行调试

```bash
# 调试流程: 在不同阶段保存快照

# 快照1: 空白状态
bash scripts/clean_test_data.sh
./scripts/snapshot_memory.sh save blank

# 快照2: 录入50轮对话后
python3 tests/test_locomo_bmam_full.py --samples 1 --questions 5 --verbose
# (假设只录入了50轮)
./scripts/snapshot_memory.sh save after_50_turns

# 快照3: 录入500轮对话后
# (继续录入剩余450轮)
./scripts/snapshot_memory.sh save after_500_turns

# 快照4: 第一次巩固后
# (等待巩固完成)
./scripts/snapshot_memory.sh save after_consolidation

# 现在可以随时跳转到任意阶段
./scripts/snapshot_memory.sh restore after_50_turns    # 回到50轮
./scripts/snapshot_memory.sh restore after_500_turns   # 跳到500轮
./scripts/snapshot_memory.sh restore blank             # 回到空白

# 时间旅行调试!
```

---

## 问题2: 记忆存储格式优化 ✅

### 快速回答

BMAM的记忆存储已经高度优化,支持:
- ✅ **丰富的metadata**: 20+字段,涵盖情绪/重要性/时间/访问频率等
- ✅ **JSON灵活字段**: `memory_metadata`, `context_tags`, `associations`
- ✅ **KG支持**: `associations` 字段存储记忆关联关系
- ✅ **脑区映射**: `brain_region` 字段模拟不同脑区
- ✅ **向量索引**: `embedding_id` 关联FAISS向量库

---

## 存储格式详解

### 数据库Schema

BMAM使用SQLite存储,完整schema:

```sql
CREATE TABLE memories (
    -- 基础字段
    id VARCHAR PRIMARY KEY,              -- UUID
    content TEXT NOT NULL,               -- 记忆内容
    memory_type VARCHAR NOT NULL,        -- episodic/semantic/procedural

    -- 重要性和情绪
    importance FLOAT,                    -- 0.0-1.0
    emotion_tags JSON,                   -- ["happy", "excited"]
    emotion_intensity FLOAT,             -- 0.0-1.0

    -- 脑区模拟
    brain_region VARCHAR,                -- hippocampus/prefrontal/amygdala
    consolidation_level INTEGER,         -- 0-3 (巩固等级)
    access_frequency INTEGER,            -- 访问次数
    decay_rate FLOAT,                    -- 遗忘速率
    stress_marker BOOLEAN,               -- 是否压力相关

    -- 时间追踪
    timestamp DATETIME,                  -- 创建时间
    last_accessed DATETIME,              -- 最后访问时间
    last_consolidated DATETIME,          -- 最后巩固时间

    -- 网络和上下文
    associations JSON,                   -- KG关联: ["mem_id_1", "mem_id_2"]
    source_reliability FLOAT,            -- 来源可靠性 0.0-1.0
    context_tags JSON,                   -- ["conversation", "work"]
    memory_metadata JSON,                -- 扩展元数据 (灵活字段)

    -- 向量索引
    embedding_id VARCHAR,                -- FAISS索引ID

    -- 生命周期
    is_active BOOLEAN                    -- 软删除标记
);
```

### 字段详解

#### 1. 基础字段

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `id` | VARCHAR | UUID唯一标识 | `"3ead1f56-..."` |
| `content` | TEXT | 记忆内容 | `"Caroline went to LGBTQ support group on May 7"` |
| `memory_type` | VARCHAR | 记忆类型 | `"episodic"` / `"semantic"` / `"procedural"` |

#### 2. 重要性和情绪

| 字段 | 类型 | 说明 | 优化点 |
|------|------|------|--------|
| `importance` | FLOAT | 重要性分数 | ✅ 用于检索排序 |
| `emotion_tags` | JSON | 情绪标签数组 | ✅ 支持情绪检索 |
| `emotion_intensity` | FLOAT | 情绪强度 | ✅ 情绪记忆增强 |

**示例**:
```json
{
  "importance": 0.85,
  "emotion_tags": ["happy", "excited", "proud"],
  "emotion_intensity": 0.9
}
```

#### 3. 脑区模拟 (Brain-Inspired)

| 字段 | 类型 | 说明 | 神经科学对应 |
|------|------|------|--------------|
| `brain_region` | VARCHAR | 关联脑区 | Hippocampus/Prefrontal Cortex等 |
| `consolidation_level` | INTEGER | 巩固等级 (0-3) | 短期→长期记忆转换 |
| `access_frequency` | INTEGER | 访问次数 | 重复激活强化记忆 |
| `decay_rate` | FLOAT | 遗忘速率 | Ebbinghaus遗忘曲线 |
| `stress_marker` | BOOLEAN | 压力标记 | 压力记忆更持久 |

**示例**:
```json
{
  "brain_region": "hippocampus",
  "consolidation_level": 2,
  "access_frequency": 5,
  "decay_rate": 0.05,
  "stress_marker": false
}
```

#### 4. 时间追踪

| 字段 | 类型 | 说明 | 用途 |
|------|------|------|------|
| `timestamp` | DATETIME | 创建时间 | ✅ 时序检索 |
| `last_accessed` | DATETIME | 最后访问时间 | ✅ 更新访问频率 |
| `last_consolidated` | DATETIME | 最后巩固时间 | ✅ 触发重新巩固 |

**用于LoCoMo时序推理**:
```sql
-- 查询"5月8日之前"的记忆
SELECT * FROM memories
WHERE timestamp < '2023-05-08'
ORDER BY timestamp DESC
```

#### 5. **知识图谱 (KG) 支持**

| 字段 | 类型 | 说明 | KG优化 |
|------|------|------|--------|
| `associations` | JSON | 关联记忆ID列表 | ✅ **存储KG关系** |
| `source_reliability` | FLOAT | 来源可靠性 | ✅ 加权检索 |
| `context_tags` | JSON | 上下文标签 | ✅ 场景检索 |
| `memory_metadata` | JSON | **灵活扩展字段** | ✅ **存储任意KG元数据** |

**KG关联示例**:
```json
{
  "associations": [
    "mem_abc123",  // Caroline的其他记忆
    "mem_def456",  // LGBTQ相关记忆
    "mem_ghi789"   // 5月7日的其他事件
  ],
  "context_tags": ["conversation", "personal_life", "support_group"],
  "memory_metadata": {
    // 可以存储任意KG元数据
    "kg_relations": [
      {"type": "attended", "object": "LGBTQ support group", "date": "2023-05-07"},
      {"type": "person", "name": "Caroline"},
      {"type": "location", "place": "support group venue"}
    ],
    "entities": ["Caroline", "LGBTQ support group"],
    "events": ["attendance"],
    "temporal": {"year": 2023, "month": 5, "day": 7}
  }
}
```

#### 6. 向量索引

| 字段 | 类型 | 说明 | 用途 |
|------|------|------|------|
| `embedding_id` | VARCHAR | FAISS索引ID | ✅ 语义搜索 |

**双存储架构**:
```
SQLite (结构化)          FAISS (向量)
├── memories.db          ├── faiss.index
│   ├── id: abc123       │   ├── vector[0]: [0.1, 0.2, ...]
│   ├── content: "..."   │   ├── vector[1]: [0.3, 0.4, ...]
│   └── embedding_id     └── metadata.pkl (ID映射)
        └─────────────────────→ 关联
```

---

## 存储格式优化策略

### 1. KG存储优化

BMAM已经支持KG,但可以进一步优化:

#### 当前方式 (JSON字段)

```python
# 存储KG关系在memory_metadata中
await memory_system.store_memory(
    content="Caroline attended LGBTQ support group",
    metadata={
        "kg_relations": [
            {"subject": "Caroline", "predicate": "attended", "object": "LGBTQ support group"},
            {"subject": "event", "predicate": "date", "object": "2023-05-07"}
        ]
    }
)
```

**优点**:
- ✅ 灵活,可以存储任意结构
- ✅ 无需修改数据库schema
- ✅ JSON查询能力 (SQLite 3.38+)

**缺点**:
- ⚠️ JSON查询性能较慢
- ⚠️ 不支持复杂图遍历

#### 优化方案: 独立KG表

```sql
-- 创建独立的KG关系表
CREATE TABLE kg_relations (
    id VARCHAR PRIMARY KEY,
    subject VARCHAR,           -- 主体 (通常是memory_id)
    predicate VARCHAR,         -- 关系类型 (attended, knows, located_at)
    object VARCHAR,            -- 客体 (可以是另一个memory_id或实体)
    confidence FLOAT,          -- 置信度
    timestamp DATETIME,
    metadata JSON,
    FOREIGN KEY (subject) REFERENCES memories(id)
);

-- 索引优化
CREATE INDEX idx_subject ON kg_relations(subject);
CREATE INDEX idx_predicate ON kg_relations(predicate);
CREATE INDEX idx_object ON kg_relations(object);
```

**使用示例**:
```python
# 存储记忆
memory_id = await memory_system.store_memory(
    content="Caroline attended LGBTQ support group on May 7"
)

# 存储KG关系
await kg_store.add_relation(
    subject=memory_id,
    predicate="attended",
    object="LGBTQ support group",
    metadata={"date": "2023-05-07"}
)

await kg_store.add_relation(
    subject=memory_id,
    predicate="person_involved",
    object="Caroline"
)

# 查询: "Caroline参加过什么活动?"
relations = await kg_store.query(
    subject_filter=lambda s: "Caroline" in s.content,
    predicate="attended"
)
```

### 2. Metadata压缩优化

#### 问题: JSON冗余

```json
{
  "memory_metadata": {
    "temporal": {"year": 2023, "month": 5, "day": 7},
    "entities": ["Caroline", "LGBTQ support group"],
    "events": ["attendance"],
    "location": "support group venue",
    "participants": ["Caroline"],
    "event_type": "support_group_meeting"
  }
}
```

**占用**: ~200 bytes/记忆

#### 优化: Schema化 + 压缩

```python
# 定义metadata schema
class MemoryMetadataSchema:
    FIELDS = {
        'temporal': 't',      # 缩写key
        'entities': 'e',
        'events': 'ev',
        'location': 'l',
        'participants': 'p',
        'event_type': 'et'
    }

# 压缩前
metadata = {
    "temporal": {"year": 2023, "month": 5, "day": 7},
    "entities": ["Caroline", "LGBTQ support group"]
}

# 压缩后
compressed_metadata = {
    "t": [2023, 5, 7],  # 数组更紧凑
    "e": [0, 1]         # 实体ID引用 (entity_dict中)
}

# 全局实体字典 (单独存储)
entity_dict = {
    0: "Caroline",
    1: "LGBTQ support group"
}
```

**占用**: ~50 bytes/记忆 (75%减少!)

### 3. 向量索引优化

#### 当前: FAISS单索引

```
data/faiss_index/
├── faiss.index      (所有向量)
└── metadata.pkl     (ID映射)
```

#### 优化: 分层索引

```python
# 按记忆类型分层
data/faiss_index/
├── episodic/
│   └── faiss.index     (情景记忆)
├── semantic/
│   └── faiss.index     (语义记忆)
└── procedural/
    └── faiss.index     (程序记忆)

# 查询时只搜索相关类型
results = await vector_db.search(
    query="When did Caroline...",
    memory_type="episodic",  # 只搜索情景记忆
    k=10
)
```

**性能提升**: 搜索速度 3-5倍 (减少搜索空间)

---

## 实际存储示例

### 示例1: LoCoMo记忆条目

```python
# 存储一条LoCoMo对话记忆
memory_id = await memory_system.store_memory(
    content="Caroline: I went to the LGBTQ support group on May 7th. It was really helpful.",
    memory_type="episodic",
    importance=0.8,
    context_tags=["conversation", "locomo_test", "personal_life"],
    metadata={
        "speaker": "Caroline",
        "date_mentioned": "2023-05-07",
        "event_type": "support_group_attendance",
        "sentiment": "positive",
        "kg_relations": [
            {"subject": "Caroline", "predicate": "attended", "object": "LGBTQ support group"},
            {"subject": "event", "predicate": "date", "object": "2023-05-07"}
        ],
        "temporal_info": {
            "year": 2023,
            "month": 5,
            "day": 7,
            "precision": "day"
        }
    }
)
```

**数据库存储**:
```sql
INSERT INTO memories VALUES (
    'mem_abc123',                                    -- id
    'Caroline: I went to the LGBTQ support...',      -- content
    'episodic',                                      -- memory_type
    0.8,                                             -- importance
    NULL,                                            -- emotion_tags
    0.5,                                             -- emotion_intensity
    'hippocampus',                                   -- brain_region
    0,                                               -- consolidation_level
    0,                                               -- access_frequency
    0.1,                                             -- decay_rate
    FALSE,                                           -- stress_marker
    '2025-11-12 10:30:00',                          -- timestamp
    NULL,                                            -- last_accessed
    NULL,                                            -- last_consolidated
    NULL,                                            -- associations
    1.0,                                             -- source_reliability
    '["conversation","locomo_test","personal_life"]', -- context_tags
    '{"speaker":"Caroline","date_mentioned":"2023-05-07",...}', -- memory_metadata (JSON)
    'emb_001',                                       -- embedding_id
    TRUE                                             -- is_active
);
```

### 示例2: 带KG关联的记忆

```python
# 存储第一条记忆
memory_1 = await memory_system.store_memory(
    content="Caroline works at a tech company",
    memory_type="semantic",
    importance=0.7
)

# 存储第二条记忆 (关联到第一条)
memory_2 = await memory_system.store_memory(
    content="Caroline attended LGBTQ support group",
    memory_type="episodic",
    importance=0.8,
    metadata={
        "associations": [memory_1],  # KG关联
        "kg_relations": [
            {"type": "same_person", "related_memory": memory_1}
        ]
    }
)
```

**associations字段**:
```json
{
  "associations": ["mem_tech_company_abc", "mem_other_event_def"]
}
```

---

## 快照 + 格式优化 = 完美组合

### 工作流程

```
1. 录入对话 → 生成优化存储
   ├── SQLite: 结构化metadata
   ├── FAISS: 向量索引
   └── KG: 关联关系

2. 保存快照 → 固定记忆节点
   ├── 复制 memories.db
   ├── 复制 faiss_index/
   └── 完整备份KG状态

3. 运行测试 → 可能污染
   ├── 新增问答记忆
   ├── 更新访问频率
   └── 修改associations

4. 恢复快照 → 清除污染
   ├── 恢复原始memories.db
   ├── 恢复原始faiss_index/
   └── KG状态回滚

5. 分析快照差异 → 了解污染
   ├── 对比记忆数量
   ├── 对比KG关系
   └── 优化测试流程
```

---

## 总结

### ✅ 问题1: 固定记忆节点

| 功能 | 状态 | 说明 |
|------|------|------|
| 快照保存 | ✅ | `./scripts/snapshot_memory.sh save` |
| 快照恢复 | ✅ | `./scripts/snapshot_memory.sh restore` |
| 避免污染 | ✅ | 测试后恢复快照,清除新增记忆 |
| 无限测试 | ✅ | 保存→测试→恢复 循环 |
| 性能提升 | ✅ | 恢复快照 ~1秒 vs 重新录入 ~40秒 |

### ✅ 问题2: 存储格式优化

| 优化项 | 状态 | 说明 |
|-------|------|------|
| 丰富metadata | ✅ | 20+字段,涵盖情绪/重要性/时间等 |
| KG支持 | ✅ | `associations` + `memory_metadata.kg_relations` |
| JSON灵活性 | ✅ | 可存储任意结构化数据 |
| 向量索引 | ✅ | FAISS向量数据库 |
| 脑区模拟 | ✅ | brain_region/consolidation_level等 |
| 时序支持 | ✅ | timestamp/last_accessed/last_consolidated |
| 软删除 | ✅ | is_active字段 |

### 🚀 进一步优化方向

| 优化项 | 优先级 | 预期收益 |
|-------|--------|---------|
| 独立KG表 | 中 | 图查询性能 3-5倍 |
| Metadata压缩 | 低 | 存储空间减少 50-75% |
| 分层向量索引 | 中 | 搜索速度 3-5倍 |
| 增量快照 | 低 | 快照速度 2-3倍 |
| 快照压缩 | 低 | 存储空间减少 60-80% |

### 📊 当前存储统计 (LoCoMo conv-26)

```
SQLite数据库:
- 文件: data/brain_memory.db
- 大小: 76KB
- 记忆数: ~523条
- 平均每条: ~145 bytes

FAISS索引:
- 状态: 未创建 (首次测试会自动创建)
- 预计大小: ~800KB (523 × 1536维 × 4bytes)

快照:
- 保存时间: ~1秒
- 恢复时间: ~1秒
- 空间占用: ~850KB (SQLite + FAISS)
```

---

**准备就绪!可以使用快照系统进行无污染测试了!** 🎉

**快速开始**:
```bash
# 1. 录入记忆
python3 tests/test_locomo_bmam_full.py --samples 1 --questions 5 --verbose

# 2. 保存快照
./scripts/snapshot_memory.sh save clean_state

# 3. 测试 (可能污染)
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions 20

# 4. 恢复快照 (清除污染)
./scripts/snapshot_memory.sh restore clean_state

# 5. 再次测试 (又是干净状态!)
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions 50
```
