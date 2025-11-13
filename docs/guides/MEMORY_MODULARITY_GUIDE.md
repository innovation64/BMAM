# BMAM 记忆系统模块化指南

**日期**: 2025-11-12
**问题**: "这个记忆是不是分离的，也就是我储存完成后可以随时插拔来针对不同的回答"

---

## 快速回答

✅ **是的,BMAM的记忆系统是完全模块化和可插拔的!**

你可以:
- 🔄 **切换记忆库**: 不同场景使用不同的记忆数据库
- 📦 **独立存储**: 每个记忆库完全独立,互不影响
- 🔌 **随时插拔**: 通过配置文件或环境变量切换
- 💾 **持久化保存**: 所有记忆存储在文件系统中,可以备份/恢复

---

## 记忆存储架构

### 1. 存储位置

BMAM的记忆系统使用**双存储**架构:

```
data/
├── memories.db           # SQLite数据库 (结构化数据)
│   └── 记忆内容、元数据、时间戳、重要性等
├── faiss_index/          # FAISS向量数据库 (语义搜索)
│   ├── faiss.index       # 向量索引
│   └── metadata.pkl      # ID映射
└── embedding_cache/      # 嵌入向量缓存
    └── *.pkl             # 缓存的embedding向量
```

### 2. 配置文件

记忆系统的存储位置在 `src/core/config.py:34` 定义:

```python
@dataclass(frozen=True)
class MemorySystemConfig:
    database_url: str = "sqlite:///data/memories.db"     # SQLite路径
    vector_db_index_path: str = "data/faiss_index"       # FAISS路径
    cache_dir: str = "data/embedding_cache"              # 缓存路径
```

### 3. 初始化方式

记忆系统在 `src/memory/memory_system/database_manager.py:46-62` 中初始化:

```python
def __init__(self, db_url: str = None):
    self.db_url = db_url or os.getenv(
        "DATABASE_URL",
        "sqlite:///data/brain_memory.db"  # 默认路径
    )

    # Create data directory for SQLite
    if "sqlite://" in self.db_url:
        db_path = self.db_url.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
```

**关键点**: 记忆路径可以通过以下方式指定:
1. **构造参数**: `DatabaseManager(db_url="...")`
2. **环境变量**: `export DATABASE_URL="sqlite:///path/to/your.db"`
3. **默认路径**: `data/brain_memory.db`

---

## 如何切换记忆库?

### 方案1: 通过环境变量 (推荐)

**场景**: 不同场景使用不同记忆库

```bash
# 场景1: 个人助手记忆
export DATABASE_URL="sqlite:///data/personal_assistant.db"
export FAISS_INDEX_PATH="data/faiss_personal"
python3 your_app.py

# 场景2: 客服机器人记忆
export DATABASE_URL="sqlite:///data/customer_service.db"
export FAISS_INDEX_PATH="data/faiss_customer"
python3 your_app.py

# 场景3: 教育辅导记忆
export DATABASE_URL="sqlite:///data/education_tutor.db"
export FAISS_INDEX_PATH="data/faiss_education"
python3 your_app.py
```

**优点**:
- ✅ 无需修改代码
- ✅ 易于自动化部署
- ✅ 不同进程使用不同记忆

### 方案2: 通过代码配置

**场景**: 动态切换记忆库

```python
from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.memory.memory_system import AdvancedMemorySystem

# 方式1: 初始化时指定
coordinator = BrainInspiredCoordinator(
    db_url="sqlite:///data/custom_memory.db"
)

# 方式2: 使用不同的memory_system实例
memory_system_1 = AdvancedMemorySystem(db_url="sqlite:///data/scenario_1.db")
memory_system_2 = AdvancedMemorySystem(db_url="sqlite:///data/scenario_2.db")

# 动态切换
async def handle_request(scenario):
    if scenario == "personal":
        coordinator.memory_system = memory_system_1
    elif scenario == "work":
        coordinator.memory_system = memory_system_2

    result = await coordinator.process_input(user_query)
```

### 方案3: 通过配置文件

**场景**: 管理多个预定义场景

**1. 创建配置文件** `config/memory_scenarios.json`:
```json
{
  "personal": {
    "database_url": "sqlite:///data/personal.db",
    "faiss_index": "data/faiss_personal",
    "description": "个人助手记忆"
  },
  "work": {
    "database_url": "sqlite:///data/work.db",
    "faiss_index": "data/faiss_work",
    "description": "工作相关记忆"
  },
  "learning": {
    "database_url": "sqlite:///data/learning.db",
    "faiss_index": "data/faiss_learning",
    "description": "学习和研究记忆"
  }
}
```

**2. 加载器脚本** `scripts/load_memory_scenario.py`:
```python
import json
import os
from pathlib import Path

def load_scenario(scenario_name: str):
    """加载指定场景的记忆配置"""
    config_path = Path("config/memory_scenarios.json")

    with open(config_path) as f:
        scenarios = json.load(f)

    if scenario_name not in scenarios:
        raise ValueError(f"Unknown scenario: {scenario_name}")

    config = scenarios[scenario_name]

    # 设置环境变量
    os.environ["DATABASE_URL"] = config["database_url"]
    os.environ["FAISS_INDEX_PATH"] = config["faiss_index"]

    print(f"✅ Loaded scenario: {scenario_name}")
    print(f"   Database: {config['database_url']}")
    print(f"   FAISS: {config['faiss_index']}")

    return config

# 使用示例
if __name__ == "__main__":
    import sys
    scenario = sys.argv[1] if len(sys.argv) > 1 else "personal"
    load_scenario(scenario)
```

**3. 使用方式**:
```bash
# 加载不同场景
python3 scripts/load_memory_scenario.py personal
python3 scripts/load_memory_scenario.py work
python3 scripts/load_memory_scenario.py learning
```

### 方案4: 运行时动态切换

**场景**: API服务,根据用户ID使用不同记忆

```python
from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.memory.memory_system import AdvancedMemorySystem
from typing import Dict

class MultiUserMemoryManager:
    """多用户记忆管理器"""

    def __init__(self):
        self.coordinators: Dict[str, BrainInspiredCoordinator] = {}

    async def get_coordinator(self, user_id: str) -> BrainInspiredCoordinator:
        """获取或创建用户专属的coordinator"""
        if user_id not in self.coordinators:
            # 为每个用户创建独立的记忆库
            db_url = f"sqlite:///data/users/{user_id}/memories.db"
            faiss_path = f"data/users/{user_id}/faiss_index"

            coordinator = BrainInspiredCoordinator(db_url=db_url)
            coordinator.memory_system.vector_db.index_path = faiss_path

            await coordinator.initialize()
            self.coordinators[user_id] = coordinator

        return self.coordinators[user_id]

    async def process_user_input(self, user_id: str, query: str):
        """处理用户输入,自动使用该用户的记忆"""
        coordinator = await self.get_coordinator(user_id)
        return await coordinator.process_input(query)

# API使用示例
manager = MultiUserMemoryManager()

# 用户A的对话
await manager.process_user_input("user_A", "我喜欢打篮球")
# 存储到 data/users/user_A/memories.db

# 用户B的对话
await manager.process_user_input("user_B", "我喜欢看书")
# 存储到 data/users/user_B/memories.db

# 各用户的记忆完全独立!
```

---

## 记忆备份与恢复

### 备份记忆

```bash
#!/bin/bash
# scripts/backup_memory.sh

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 备份SQLite数据库
cp data/memories.db "$BACKUP_DIR/"
cp data/brain_memory.db "$BACKUP_DIR/" 2>/dev/null || true

# 备份FAISS索引
cp -r data/faiss_index "$BACKUP_DIR/"

# 备份缓存 (可选)
cp -r data/embedding_cache "$BACKUP_DIR/" 2>/dev/null || true

echo "✅ Backup completed: $BACKUP_DIR"
ls -lh "$BACKUP_DIR"
```

### 恢复记忆

```bash
#!/bin/bash
# scripts/restore_memory.sh

BACKUP_DIR=$1

if [ -z "$BACKUP_DIR" ]; then
    echo "Usage: ./restore_memory.sh <backup_directory>"
    exit 1
fi

# 恢复SQLite数据库
cp "$BACKUP_DIR/memories.db" data/ 2>/dev/null || true
cp "$BACKUP_DIR/brain_memory.db" data/ 2>/dev/null || true

# 恢复FAISS索引
rm -rf data/faiss_index
cp -r "$BACKUP_DIR/faiss_index" data/

echo "✅ Restore completed from: $BACKUP_DIR"
```

### 合并记忆库

**场景**: 将多个记忆库合并成一个

```python
# scripts/merge_memories.py
import asyncio
from src.memory.memory_system import AdvancedMemorySystem

async def merge_memories(source_dbs: list, target_db: str):
    """合并多个记忆库到目标库"""

    # 初始化目标库
    target_system = AdvancedMemorySystem(db_url=f"sqlite:///{target_db}")

    total_merged = 0

    for source_db in source_dbs:
        print(f"\n📥 Merging from: {source_db}")
        source_system = AdvancedMemorySystem(db_url=f"sqlite:///{source_db}")

        # 获取所有记忆
        memories = source_system.db_manager.get_all_memories()

        # 复制到目标库
        for memory in memories:
            await target_system.store_memory(
                content=memory.content,
                memory_type=memory.memory_type,
                importance=memory.importance,
                metadata=memory.metadata
            )
            total_merged += 1

        print(f"   ✅ Merged {len(memories)} memories")

    print(f"\n✅ Total merged: {total_merged} memories → {target_db}")

# 使用示例
if __name__ == "__main__":
    asyncio.run(merge_memories(
        source_dbs=[
            "data/personal.db",
            "data/work.db",
            "data/learning.db"
        ],
        target_db="data/merged_memories.db"
    ))
```

---

## 实际应用场景

### 场景1: 多角色聊天机器人

```python
# 3个不同角色,3个独立记忆库
roles = {
    "personal_assistant": "sqlite:///data/role_personal.db",
    "tech_support": "sqlite:///data/role_support.db",
    "creative_writer": "sqlite:///data/role_creative.db"
}

async def chat_with_role(role: str, message: str):
    coordinator = BrainInspiredCoordinator(db_url=roles[role])
    await coordinator.initialize()
    return await coordinator.process_input(message)

# 使用
await chat_with_role("personal_assistant", "提醒我明天的会议")
await chat_with_role("tech_support", "Python如何处理异步?")
await chat_with_role("creative_writer", "帮我写一首诗")
```

### 场景2: A/B测试不同记忆策略

```python
# 测试不同记忆巩固策略
strategies = {
    "aggressive_consolidation": {
        "db": "sqlite:///data/test_aggressive.db",
        "config": {"consolidation_interval": 60}  # 1分钟
    },
    "conservative_consolidation": {
        "db": "sqlite:///data/test_conservative.db",
        "config": {"consolidation_interval": 3600}  # 1小时
    }
}

# 运行LoCoMo测试,比较性能
for strategy, settings in strategies.items():
    coordinator = BrainInspiredCoordinator(db_url=settings["db"])
    # ... 运行测试 ...
    print(f"{strategy}: accuracy={accuracy}")
```

### 场景3: 时间旅行 - 记忆快照

```bash
# 创建每日记忆快照
mkdir -p snapshots/
cp data/memories.db "snapshots/memories_$(date +%Y%m%d).db"

# 回退到某一天的状态
cp snapshots/memories_20251110.db data/memories.db
```

### 场景4: 多语言独立记忆

```python
# 不同语言的记忆分开存储
language_memories = {
    "zh": "sqlite:///data/memories_chinese.db",
    "en": "sqlite:///data/memories_english.db",
    "ja": "sqlite:///data/memories_japanese.db"
}

async def process_multilingual(text: str, lang: str):
    coordinator = BrainInspiredCoordinator(db_url=language_memories[lang])
    await coordinator.initialize()
    return await coordinator.process_input(text)
```

---

## 注意事项

### 1. 线程安全

✅ **SQLite自带线程安全**: DatabaseManager使用了`threading.Lock()`保护并发访问 (database_manager.py:67)

⚠️ **多进程需要不同数据库**: 如果使用multiprocessing,确保每个进程使用独立的db文件

### 2. FAISS索引同步

⚠️ **警告**: FAISS索引和SQLite数据库需要保持同步

**解决方案**: 使用同一个备份/恢复脚本,确保两者一起操作

```bash
# ✅ 正确: 同时备份
cp data/memories.db backups/
cp -r data/faiss_index backups/

# ❌ 错误: 只备份一个
cp data/memories.db backups/  # FAISS索引不匹配!
```

### 3. 路径配置优先级

记忆路径的配置优先级 (从高到低):
1. **代码传参**: `DatabaseManager(db_url="...")`
2. **环境变量**: `os.getenv("DATABASE_URL")`
3. **默认值**: `"sqlite:///data/brain_memory.db"`

### 4. 数据迁移

如果修改了数据库schema,需要迁移工具:

```python
# 简单迁移示例
from src.memory.memory_system import AdvancedMemorySystem

async def migrate_to_new_schema():
    old_system = AdvancedMemorySystem(db_url="sqlite:///data/old_memories.db")
    new_system = AdvancedMemorySystem(db_url="sqlite:///data/new_memories.db")

    memories = old_system.db_manager.get_all_memories()

    for memory in memories:
        # 添加新字段或转换格式
        new_metadata = {**memory.metadata, "migrated_at": "2025-11-12"}

        await new_system.store_memory(
            content=memory.content,
            memory_type=memory.memory_type,
            importance=memory.importance,
            metadata=new_metadata
        )
```

---

## 总结

### ✅ 可以做的

1. ✅ **切换记忆库**: 通过环境变量或代码配置
2. ✅ **独立存储**: 每个场景使用独立的db文件
3. ✅ **备份恢复**: 简单的文件复制即可
4. ✅ **合并拆分**: 通过脚本迁移记忆
5. ✅ **多用户隔离**: 每个用户独立的记忆空间
6. ✅ **A/B测试**: 并行测试不同配置

### 📊 架构优势

- **完全模块化**: 记忆系统与业务逻辑分离
- **插拔式设计**: 可以随时切换不同记忆库
- **持久化存储**: 所有数据存在文件系统,不依赖外部服务
- **轻量级**: SQLite + FAISS,无需额外数据库服务

### 🚀 快速开始

**最简单的切换方式**:

```bash
# 场景1
export DATABASE_URL="sqlite:///data/scenario_1.db"
python3 your_app.py

# 场景2
export DATABASE_URL="sqlite:///data/scenario_2.db"
python3 your_app.py
```

就这么简单!每次运行会自动使用不同的记忆库。

---

**准备就绪!可以开始使用模块化记忆系统了!** 🎉
