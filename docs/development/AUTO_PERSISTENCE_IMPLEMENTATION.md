# BMAM自动持久化机制实现方案

## 📋 背景

**当前问题**:
- 所有brain regions使用内存存储 (List/Dict)
- 记忆只有在手动调用`export_memory_archive()`时才持久化
- 进程结束后记忆全部丢失
- LoCoMo 419个turns导入后，因未导出BMA而全部丢失

**设计目标**:
1. 系统启动时自动加载最新记忆
2. 每次记忆变更后自动持久化
3. BMA归档作为手动快照功能，独立于自动持久化
4. 支持切换到某个BMA归档继续塑造

---

## 🎯 实现方案

### 1. 双层记忆架构

```
📂 data/ (最新记忆 - 自动加载/保存)
├── temporal_lobe.db           # TemporalLobe SQLite数据库
├── hippocampus_state.json     # Hippocampus状态
├── prefrontal_state.json      # PrefrontalCortex状态
├── amygdala_state.json        # Amygdala状态
└── basal_ganglia_state.json   # BasalGanglia状态

📂 data/memory_archives/ (手动归档 - BMA格式)
├── baseline_20251112.bma/     # 特定时间点快照
└── locomo_imported.bma/       # 导入后的归档
```

### 2. TemporalLobe SQLite持久化

**文件**: `src/agents/brain_regions/temporal_lobe_agent/storage.py`

**实现**:
```python
class StorageMixin:
    def __init__(self):
        self.db_path = Path("data/temporal_lobe.db")
        self._init_database()
        self._load_from_database()  # 启动时自动加载

    def _init_database(self):
        """初始化SQLite数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS semantic_memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                memory_subtype TEXT,
                timestamp TEXT,
                entities TEXT,
                relations TEXT,
                importance REAL,
                event_time TEXT,
                embedding BLOB,
                memory_type TEXT,
                consolidation_level REAL,
                access_count INTEGER,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_graph (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT,
                predicate TEXT,
                object TEXT,
                confidence REAL,
                timestamp TEXT
            )
        """)

        conn.commit()
        conn.close()

    def _load_from_database(self):
        """系统启动时加载记忆"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM semantic_memories")
        rows = cursor.fetchall()

        for row in rows:
            memory = self._row_to_memory(row)
            self.memories.append(memory)
            self.memory_dict[memory.id] = memory

        conn.close()
        logger.info(f"✅ Loaded {len(self.memories)} memories from database")

    async def store_memory(self, **kwargs):
        """存储记忆 + 自动持久化"""
        memory = self._create_memory(**kwargs)

        # 内存存储
        self.memories.append(memory)
        self.memory_dict[memory.id] = memory

        # 自动持久化到SQLite
        self._save_to_database(memory)

        return memory.id

    def _save_to_database(self, memory: SemanticMemory):
        """保存单条记忆到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO semantic_memories
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory.id,
            memory.content,
            memory.memory_subtype,
            memory.timestamp.isoformat(),
            json.dumps(memory.entities),
            json.dumps(memory.relations),
            memory.importance,
            memory.event_time.isoformat() if memory.event_time else None,
            pickle.dumps(memory.embedding) if memory.embedding else None,
            memory.memory_type.value if memory.memory_type else None,
            memory.consolidation_level,
            memory.access_count,
            json.dumps(memory.metadata)
        ))

        conn.commit()
        conn.close()
```

### 3. Hippocampus/Amygdala/BasalGanglia JSON持久化

**实现**: 扩展现有的`export_state()`方法

```python
class HippocampusAgent:
    def __init__(self):
        self.state_file = Path("data/hippocampus_state.json")
        self._load_state_from_file()  # 启动时加载

    def _load_state_from_file(self):
        """启动时自动加载状态"""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                self.load_state(state)

    async def store_memory(self, **kwargs):
        """存储记忆 + 自动保存状态"""
        result = await super().store_memory(**kwargs)

        # 自动持久化
        self._save_state_to_file()

        return result

    def _save_state_to_file(self):
        """自动保存当前状态"""
        state = self.export_state()
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
```

### 4. BrainCoordinator集成

**文件**: `src/coordination/brain_coordinator_refactored.py`

```python
class BrainInspiredCoordinator:
    async def initialize(self):
        """初始化时自动加载所有brain regions的最新状态"""
        # 初始化所有agents (会自动加载各自的状态文件)
        await self._init_agents()

        logger.info("✅ All brain regions loaded with latest memories")

    async def shutdown(self):
        """关闭时确保所有状态已保存"""
        # 所有记忆变更应该已经自动保存了
        # 这里只做最终检查
        logger.info("✅ Coordinator shutdown - all memories persisted")
```

### 5. BMA归档功能保持独立

**BMA归档**继续作为手动快照功能：
- 用于特定时间点的完整快照
- 用于实验对比
- 用于切换到某个归档继续塑造

```python
# 手动创建归档
coordinator.export_memory_archive(
    archive_name="baseline_after_locomo_import",
    description="LoCoMo 419 turns导入后的基线状态"
)

# 切换到某个归档继续塑造
coordinator.load_memory_archive(
    archive_path="data/memory_archives/baseline_20251112.bma"
)
# 从归档加载后，继续塑造的记忆会自动保存到data/
```

---

## 🚀 实施步骤

### Phase 1: TemporalLobe SQLite持久化 ⭐️
1. 修改`storage.py`添加数据库初始化
2. 实现`_load_from_database()`
3. 修改`store_memory()`添加自动保存
4. 测试: 导入记忆→重启→验证记忆仍在

### Phase 2: 其他Brain Regions JSON持久化
1. Hippocampus + 自动save/load
2. Amygdala + 自动save/load
3. BasalGanglia + 自动save/load
4. PrefrontalCortex + 自动save/load
5. 测试: 多次重启验证状态保持

### Phase 3: 集成测试
1. LoCoMo 419 turns完整导入
2. 重启coordinator验证记忆保持
3. 手动导出BMA归档
4. 测试归档切换功能

---

## ✅ 验证标准

1. **自动持久化**:
   - 导入记忆后，关闭进程，重新启动
   - 所有记忆应该自动加载

2. **BMA归档独立性**:
   - 不需要手动导出BMA也能保持记忆
   - BMA归档用于特定快照和切换

3. **性能**:
   - 自动保存不应显著影响导入速度
   - SQLite批量写入优化

---

## 📊 预期成果

- ✅ 记忆在进程间持久化
- ✅ 系统启动立即可用
- ✅ BMA归档作为可选快照功能
- ✅ 支持归档切换和继续塑造
- ✅ LoCoMo导入后记忆永久保存

---

**实施时间**: ~2-3小时
**Git Checkpoint**: 已创建 (commit: 9cca7f4)
