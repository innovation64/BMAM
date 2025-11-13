# BMAM 可塑性记忆管理系统

**工具**: `scripts/memory_manager.py`
**类型**: 独立管理工具 (非主框架功能)
**用途**: 快照管理、导入导出、时间回溯、健康检查

---

## 核心概念

### 可塑性记忆 (Plasticity Memory)

你提到的非常关键的概念:
- ❌ **记忆不是静态的**: 长时间运行可能"崩坏"
- ✅ **需要时间回溯**: 回退到任意历史状态
- ✅ **用户主动触发**: 手动保存关键节点
- ✅ **自定义状态**: 带标签、描述的快照

### 与测试优化的关系

| 功能 | 位置 | 说明 |
|------|------|------|
| **主框架** | `src/` | BMAM记忆系统核心代码 |
| **测试脚本** | `tests/test_locomo_bmam_full.py` | LoCoMo测试,`--skip-ingestion`功能 |
| **简单快照** | `scripts/snapshot_memory.sh` | Bash脚本,快速保存/恢复 |
| **记忆管理器** | `scripts/memory_manager.py` | Python工具,完整管理功能 |

**关系**:
```
主框架 (src/)
  ↓ 产生数据
记忆数据库 (data/brain_memory.db)
  ↓ 管理工具
记忆管理器 (scripts/memory_manager.py)
  ↓ 创建快照
快照库 (data/snapshots/)
  ↓ 导出分享
导出包 (exports/)
```

---

## 功能对比

### 简单快照 (snapshot_memory.sh)

```bash
# 保存
./scripts/snapshot_memory.sh save clean_state

# 恢复
./scripts/snapshot_memory.sh restore clean_state

# 列表
./scripts/snapshot_memory.sh list
```

**优点**: 简单快速
**缺点**:
- 没有元数据 (标签、描述、统计)
- 不能对比快照
- 不能导入导出
- 不能健康检查

### 记忆管理器 (memory_manager.py)

```bash
# 创建带标签的快照
python3 scripts/memory_manager.py create clean_state \
  --desc "干净的初始状态" \
  --tags baseline test production

# 列出快照 (带统计信息)
python3 scripts/memory_manager.py list

# 恢复快照
python3 scripts/memory_manager.py restore clean_state

# 导出快照 (可分享)
python3 scripts/memory_manager.py export clean_state --path ./exports

# 导入快照 (从别人那里)
python3 scripts/memory_manager.py import ./exports/clean_state

# 对比两个快照
python3 scripts/memory_manager.py compare before after

# 检查记忆健康度
python3 scripts/memory_manager.py health
```

**优点**:
- ✅ 完整元数据 (标签、描述、统计)
- ✅ 快照对比分析
- ✅ 导入导出功能
- ✅ 健康度检查
- ✅ 去重检测 (MD5 hash)
- ✅ Python API (可编程)

---

## 使用场景

### 场景1: 长时间运行的记忆崩坏防护

**问题**: BMAM运行几天后,记忆可能因为以下原因"崩坏":
- 重复记忆过多 (access_frequency失衡)
- 重要性评分漂移 (importance偏离正常范围)
- KG关联混乱 (associations过度连接)
- 记忆污染 (测试/调试记忆混入)

**解决方案**: 定期快照,发现问题时回溯

```bash
# Day 1: 初始干净状态
python3 scripts/memory_manager.py create day1_clean \
  --desc "第1天,刚录入对话" \
  --tags baseline day1

# Day 2: 运行一天后
python3 scripts/memory_manager.py create day2_after_use \
  --desc "第2天,运行24小时后" \
  --tags day2 checkpoint

# Day 3: 检查健康度
python3 scripts/memory_manager.py health
# 输出: Health Score: 65/100
# Issues: Low average importance (<0.2), many low-value memories

# 对比分析
python3 scripts/memory_manager.py compare day1_clean day2_after_use
# 输出: Memory count delta: +350 (太多新记忆!)

# 决定回溯到Day 1
python3 scripts/memory_manager.py restore day1_clean
# ✅ 记忆恢复到干净状态!
```

### 场景2: 自定义实验状态

**需求**: 测试不同的巩固策略

```bash
# 实验A: Aggressive consolidation
export CONSOLIDATION_INTERVAL=60
bash scripts/clean_test_data.sh
python3 tests/test_locomo_bmam_full.py --samples 1 --questions 20

python3 scripts/memory_manager.py create exp_aggressive \
  --desc "Aggressive consolidation (1min interval)" \
  --tags experiment aggressive consolidation
# 记录准确率: 85%

# 实验B: Conservative consolidation
export CONSOLIDATION_INTERVAL=3600
bash scripts/clean_test_data.sh
python3 tests/test_locomo_bmam_full.py --samples 1 --questions 20

python3 scripts/memory_manager.py create exp_conservative \
  --desc "Conservative consolidation (1hour interval)" \
  --tags experiment conservative consolidation
# 记录准确率: 82%

# 对比实验
python3 scripts/memory_manager.py compare exp_aggressive exp_conservative
# Memory count delta: -50 (Aggressive巩固更多)
# Importance delta: +0.15 (Aggressive重要性更高)

# 结论: Aggressive更好,恢复这个状态用于生产
python3 scripts/memory_manager.py restore exp_aggressive
python3 scripts/memory_manager.py create production_v1 \
  --desc "生产环境v1 - Aggressive consolidation" \
  --tags production v1
```

### 场景3: 时间旅行调试

**需求**: 调试记忆系统bug,需要在不同时间点检查状态

```bash
# T0: 空白状态
bash scripts/clean_test_data.sh
python3 scripts/memory_manager.py create t0_blank \
  --desc "T0: 空白状态" \
  --tags debug timeline t0

# T1: 录入50轮对话
python3 tests/test_locomo_bmam_full.py --samples 1 --questions 5 --verbose
# (假设只录入了50轮)
python3 scripts/memory_manager.py create t1_after_50_turns \
  --desc "T1: 录入50轮对话后" \
  --tags debug timeline t1

# T2: 录入500轮对话
# (继续录入剩余450轮)
python3 scripts/memory_manager.py create t2_after_500_turns \
  --desc "T2: 录入500轮对话后" \
  --tags debug timeline t2

# T3: 第一次巩固
# (等待巩固完成)
python3 scripts/memory_manager.py create t3_after_consolidation \
  --desc "T3: 第一次巩固后" \
  --tags debug timeline t3

# T4: 运行100次查询后
# (运行测试)
python3 scripts/memory_manager.py create t4_after_100_queries \
  --desc "T4: 运行100次查询后" \
  --tags debug timeline t4

# 发现bug: T4的访问频率异常高
python3 scripts/memory_manager.py health
# Health Score: 55/100
# Issues: Very high access frequency (avg 50+)

# 时间旅行: 跳转到T2检查
python3 scripts/memory_manager.py restore t2_after_500_turns
python3 scripts/memory_manager.py health
# Health Score: 95/100  (正常!)

# 时间旅行: 跳转到T3检查
python3 scripts/memory_manager.py restore t3_after_consolidation
python3 scripts/memory_manager.py health
# Health Score: 90/100  (还算正常)

# 结论: Bug出现在T3→T4之间,定位到查询逻辑!
```

### 场景4: 导入导出 & 分享

**需求**: 团队成员共享测试状态

```bash
# 成员A: 准备好的记忆状态
python3 scripts/memory_manager.py create team_baseline \
  --desc "团队基线 - LoCoMo conv-26" \
  --tags team baseline locomo

# 导出给成员B
python3 scripts/memory_manager.py export team_baseline --path ./exports
# ✅ Exported to: ./exports/team_baseline

# 打包发送
tar -czf team_baseline.tar.gz ./exports/team_baseline
# 发送给成员B: team_baseline.tar.gz

# 成员B: 接收并导入
tar -xzf team_baseline.tar.gz
python3 scripts/memory_manager.py import ./exports/team_baseline
# ✅ Snapshot imported: team_baseline

# 成员B: 使用导入的快照
python3 scripts/memory_manager.py restore team_baseline
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions 20
# 立即开始测试,无需自己录入数据!
```

### 场景5: 生产环境回滚

**需求**: 生产环境记忆崩坏,紧急回滚

```bash
# 生产环境每天自动快照
# (添加到crontab)
0 0 * * * cd /path/to/BMAM && python3 scripts/memory_manager.py create "production_$(date +\%Y\%m\%d)" --desc "Daily auto snapshot" --tags production auto

# 某天发现问题
python3 scripts/memory_manager.py health
# Health Score: 30/100
# Issues: Very large memory database (>100K), many low-value memories

# 列出最近的快照
python3 scripts/memory_manager.py list --tag production
# 📸 production_20251112 (昨天)
# 📸 production_20251111 (前天)
# 📸 production_20251110 (3天前)

# 对比昨天和今天
python3 scripts/memory_manager.py compare production_20251111 production_20251112
# Memory count delta: +50000 (异常增长!)

# 紧急回滚到前天
python3 scripts/memory_manager.py restore production_20251111
# ✅ Restored!

# 重新检查
python3 scripts/memory_manager.py health
# Health Score: 85/100 (恢复正常!)
```

---

## 完整命令参考

### 创建快照

```bash
python3 scripts/memory_manager.py create <name> \
  --desc "描述" \
  --tags tag1 tag2 tag3
```

**示例**:
```bash
python3 scripts/memory_manager.py create clean_baseline \
  --desc "干净的基线状态,用于所有测试" \
  --tags baseline test clean
```

### 列出快照

```bash
# 列出所有
python3 scripts/memory_manager.py list

# 按标签过滤
python3 scripts/memory_manager.py list --tag production
python3 scripts/memory_manager.py list --tag experiment
```

**输出示例**:
```
================================================================================
Available Snapshots (5)
================================================================================

📸 production_v1
   ID: production_v1_20251112_143022
   Created: 2025-11-12T14:30:22
   Description: 生产环境v1
   Tags: production, v1
   Memories: 523
   Avg Importance: 0.65

📸 exp_aggressive
   ID: exp_aggressive_20251112_102045
   Created: 2025-11-12T10:20:45
   Description: Aggressive consolidation实验
   Tags: experiment, aggressive
   Memories: 480
   Avg Importance: 0.72
```

### 恢复快照

```bash
python3 scripts/memory_manager.py restore <name_or_id>
```

**示例**:
```bash
# 按名称恢复
python3 scripts/memory_manager.py restore clean_baseline

# 按ID恢复
python3 scripts/memory_manager.py restore production_v1_20251112_143022
```

### 删除快照

```bash
python3 scripts/memory_manager.py delete <name_or_id>
```

### 导出快照

```bash
python3 scripts/memory_manager.py export <name_or_id> --path <export_dir>
```

**示例**:
```bash
python3 scripts/memory_manager.py export clean_baseline --path ./exports
# 创建: ./exports/clean_baseline/
#   ├── brain_memory.db
#   ├── faiss_index/
#   └── snapshot_metadata.json
```

### 导入快照

```bash
python3 scripts/memory_manager.py import <import_dir> --name <new_name>
```

**示例**:
```bash
python3 scripts/memory_manager.py import ./exports/clean_baseline --name imported_baseline
```

### 对比快照

```bash
python3 scripts/memory_manager.py compare <id1> <id2>
```

**输出示例**:
```
================================================================================
Snapshot Comparison
================================================================================

Snapshot 1: before_test (2025-11-12T10:00:00)
  Memories: 523
  Avg Importance: 0.65

Snapshot 2: after_test (2025-11-12T11:00:00)
  Memories: 543
  Avg Importance: 0.62

Differences:
  Memory count delta: +20
  Importance delta: -0.030
  Access frequency delta: +5.20
  Identical: ❌ No
```

### 健康检查

```bash
python3 scripts/memory_manager.py health
```

**输出示例**:
```
================================================================================
Memory System Health Check
================================================================================

Health Score: 85.0/100

Statistics:
  Total memories: 523
  Memory types: {'episodic': 450, 'semantic': 73}
  Avg importance: 0.65
  Avg access frequency: 2.5

Issues:
  ⚠️  FAISS index missing, semantic search unavailable

Recommendations:
  💡 Rebuild FAISS index for semantic search
```

---

## Python API使用

除了命令行,也可以在Python代码中使用:

```python
from scripts.memory_manager import MemoryManager

# 初始化管理器
manager = MemoryManager()

# 创建快照
snapshot = manager.create_snapshot(
    name="my_snapshot",
    description="My custom snapshot",
    tags=["test", "experiment"]
)
print(f"Created: {snapshot['snapshot_id']}")
print(f"Memories: {snapshot['stats']['total_memories']}")

# 列出快照
snapshots = manager.list_snapshots(tag="test")
for snap in snapshots:
    print(f"{snap['name']}: {snap['stats']['total_memories']} memories")

# 恢复快照
result = manager.restore_snapshot("my_snapshot")
print(f"Restored: {result['name']}")

# 对比快照
comparison = manager.compare_snapshots("snapshot1", "snapshot2")
print(f"Delta: {comparison['differences']['memory_count_delta']} memories")

# 健康检查
health = manager.check_memory_health()
print(f"Health Score: {health['health_score']}/100")

# 导出快照
export_result = manager.export_snapshot("my_snapshot", "./exports")
print(f"Exported to: {export_result['export_path']}")

# 导入快照
import_result = manager.import_snapshot("./exports/my_snapshot")
print(f"Imported: {import_result['snapshot_id']}")
```

---

## 快照元数据格式

每个快照存储以下元数据:

```json
{
  "snapshot_id": "clean_state_20251112_143022",
  "name": "clean_state",
  "description": "干净的初始状态",
  "tags": ["baseline", "test", "clean"],
  "timestamp": "2025-11-12T14:30:22",
  "auto": false,
  "files": {
    "databases": ["brain_memory.db"],
    "faiss_index": true
  },
  "stats": {
    "total_memories": 523,
    "memory_types": {"episodic": 450, "semantic": 73},
    "important_memories": 125,
    "avg_importance": 0.65,
    "avg_access_frequency": 2.5,
    "time_range": {
      "earliest": "2025-11-12T10:00:00",
      "latest": "2025-11-12T14:00:00"
    }
  },
  "db_hash": "a1b2c3d4e5f6..."
}
```

---

## 与主框架的关系

### 完全独立

记忆管理器 **不修改主框架**:
- ✅ 独立工具脚本
- ✅ 只操作数据文件
- ✅ 不依赖BMAM代码
- ✅ 可以单独运行

### 数据流

```
主框架运行
  ↓ 写入
data/brain_memory.db (记忆数据)
  ↓ 管理
scripts/memory_manager.py (独立工具)
  ↓ 创建
data/snapshots/ (快照存储)
  ↓ 导出
exports/ (可分享的包)
```

### 互补关系

| 主框架 | 记忆管理器 |
|--------|-----------|
| 创建记忆 | 管理快照 |
| 检索记忆 | 时间回溯 |
| 巩固记忆 | 健康检查 |
| 遗忘记忆 | 导入导出 |
| 运行时功能 | 离线管理工具 |

---

## 总结

### ✅ 你的洞察完全正确

1. **可塑性记忆**: 记忆会随时间"崩坏",需要回溯
2. **自定义状态**: 用户手动触发保存关键节点
3. **时间旅行**: 回退到任意历史快照
4. **导入导出**: 分享和备份记忆状态

### 🎯 记忆管理器解决的问题

| 问题 | 解决方案 |
|------|---------|
| 记忆崩坏 | 定期快照,发现问题回滚 |
| 测试污染 | 保存干净状态,测试后恢复 |
| 实验对比 | 创建多个快照,对比分析 |
| 团队协作 | 导出分享,统一基线 |
| 生产回滚 | 自动快照,紧急恢复 |
| 调试定位 | 时间旅行,二分查找bug |

### 🚀 快速开始

```bash
# 1. 创建快照
python3 scripts/memory_manager.py create my_snapshot --desc "我的快照" --tags test

# 2. 列出快照
python3 scripts/memory_manager.py list

# 3. 恢复快照
python3 scripts/memory_manager.py restore my_snapshot

# 4. 检查健康
python3 scripts/memory_manager.py health
```

---

**这是一个完全独立的工具,不是主框架的一部分!**
**你可以安全使用,不会影响BMAM核心代码!**
