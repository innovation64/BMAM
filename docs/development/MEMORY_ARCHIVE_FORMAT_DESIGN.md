# BMAM 统一记忆归档格式设计方案

**日期**: 2025-11-12
**目标**: 设计统一的记忆归档和载入格式,支持框架灵活载入不同记忆

---

## 现状审核

### 当前存储结构

```
data/
├── brain_memory.db          # 主记忆数据库 (SQLite)
├── memories.db              # 备用记忆数据库 (可能存在)
├── working_memory.db        # 工作记忆数据库
├── faiss_index/             # 向量索引 (FAISS)
│   ├── faiss.index
│   └── metadata.pkl
├── embedding_cache/         # 嵌入向量缓存
│   └── *.pkl
└── snapshots/               # 快照存储 (当前实现)
    ├── snapshot_id_brain_memory.db
    ├── snapshot_id_faiss/
    └── snapshots_metadata.json
```

### 当前问题

1. **格式不统一**:
   - 有时是 `brain_memory.db`
   - 有时是 `memories.db`
   - coordinator通过环境变量或默认值选择

2. **依赖路径硬编码**:
   ```python
   # src/memory/memory_system/database_manager.py:54-56
   self.db_url = db_url or os.getenv(
       "DATABASE_URL",
       "sqlite:///data/brain_memory.db"  # 硬编码路径
   )
   ```

3. **快照格式不标准**:
   - 文件名包含snapshot_id前缀
   - 没有版本控制
   - 没有兼容性检查

4. **缺少完整性验证**:
   - 没有checksum
   - 没有schema版本
   - 没有必需文件检查

---

## 设计方案: BMAM Memory Archive (BMA格式)

### 核心理念

**记忆芯片** = 自包含、可移植、版本化的记忆包

### 标准格式定义

#### BMA包结构

```
my_memory.bma/              # 记忆包根目录
├── manifest.json           # 清单文件 (必需)
├── memories.db             # 记忆数据库 (必需)
├── faiss_index/            # 向量索引 (可选)
│   ├── faiss.index
│   └── metadata.pkl
├── metadata.json           # 扩展元数据 (可选)
├── checksums.json          # 文件校验和 (推荐)
└── README.md               # 人类可读描述 (可选)
```

#### manifest.json (清单文件)

```json
{
  "format_version": "1.0.0",
  "archive_type": "bmam_memory_archive",
  "created_at": "2025-11-12T14:30:22Z",
  "created_by": "BMAM v1.0.0",

  "memory_info": {
    "name": "locomo_conv26_baseline",
    "description": "LoCoMo conv-26完整对话记忆,523条记忆",
    "tags": ["baseline", "test", "locomo", "conv-26"],
    "language": "en",
    "domain": "conversation"
  },

  "statistics": {
    "total_memories": 523,
    "memory_types": {
      "episodic": 450,
      "semantic": 73
    },
    "important_memories": 125,
    "avg_importance": 0.65,
    "time_range": {
      "earliest": "2023-05-08T00:00:00Z",
      "latest": "2023-06-15T23:59:59Z"
    },
    "total_tokens_approx": 50000
  },

  "files": {
    "database": {
      "path": "memories.db",
      "format": "sqlite3",
      "schema_version": "1.0",
      "size_bytes": 76800,
      "required": true
    },
    "vector_index": {
      "path": "faiss_index/",
      "format": "faiss",
      "dimension": 1536,
      "size_bytes": 800000,
      "required": false
    },
    "embeddings": {
      "model": "text-embedding-3-small",
      "dimension": 1536,
      "cached": true
    }
  },

  "compatibility": {
    "min_bmam_version": "1.0.0",
    "max_bmam_version": "2.0.0",
    "python_version": ">=3.9",
    "required_features": ["sqlite3", "faiss"]
  },

  "provenance": {
    "source": "locomo_dataset",
    "sample_id": "conv-26",
    "ingestion_date": "2025-11-12T10:00:00Z",
    "processing_pipeline": "standard",
    "quality_score": 0.95
  }
}
```

#### checksums.json (校验和)

```json
{
  "algorithm": "sha256",
  "files": {
    "manifest.json": "a1b2c3d4e5f6...",
    "memories.db": "f6e5d4c3b2a1...",
    "faiss_index/faiss.index": "1a2b3c4d5e6f...",
    "faiss_index/metadata.pkl": "6f5e4d3c2b1a..."
  },
  "verified_at": "2025-11-12T14:30:22Z"
}
```

---

## 实现设计

### 1. MemoryArchive类 (核心)

```python
# src/memory/memory_archive.py

from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import shutil
import hashlib
from datetime import datetime

class MemoryArchive:
    """
    BMAM Memory Archive (BMA) - 统一记忆归档格式

    功能:
    - 打包记忆为标准BMA格式
    - 解包BMA格式到运行时
    - 验证完整性和兼容性
    - 导出/导入记忆芯片
    """

    FORMAT_VERSION = "1.0.0"

    def __init__(self, archive_path: Path):
        self.archive_path = Path(archive_path)
        self.manifest: Optional[Dict] = None

    @classmethod
    def create(
        cls,
        name: str,
        source_db_path: Path,
        output_dir: Path,
        description: str = "",
        tags: List[str] = None,
        include_faiss: bool = True,
        include_embeddings: bool = False
    ) -> 'MemoryArchive':
        """
        创建新的BMA记忆包

        Args:
            name: 记忆包名称
            source_db_path: 源数据库路径
            output_dir: 输出目录
            description: 描述
            tags: 标签列表
            include_faiss: 是否包含FAISS索引
            include_embeddings: 是否包含嵌入缓存

        Returns:
            MemoryArchive实例
        """
        # 创建归档目录
        archive_path = output_dir / f"{name}.bma"
        archive_path.mkdir(parents=True, exist_ok=True)

        # 收集统计信息
        stats = cls._collect_statistics(source_db_path)

        # 复制数据库
        shutil.copy2(source_db_path, archive_path / "memories.db")

        # 复制FAISS索引 (如果需要)
        files_info = {
            "database": {
                "path": "memories.db",
                "format": "sqlite3",
                "schema_version": "1.0",
                "size_bytes": (archive_path / "memories.db").stat().st_size,
                "required": True
            }
        }

        if include_faiss:
            faiss_src = source_db_path.parent / "faiss_index"
            if faiss_src.exists():
                faiss_dst = archive_path / "faiss_index"
                shutil.copytree(faiss_src, faiss_dst, dirs_exist_ok=True)

                files_info["vector_index"] = {
                    "path": "faiss_index/",
                    "format": "faiss",
                    "dimension": 1536,
                    "size_bytes": cls._get_dir_size(faiss_dst),
                    "required": False
                }

        # 创建manifest
        manifest = {
            "format_version": cls.FORMAT_VERSION,
            "archive_type": "bmam_memory_archive",
            "created_at": datetime.now().isoformat() + "Z",
            "created_by": f"BMAM {cls.FORMAT_VERSION}",
            "memory_info": {
                "name": name,
                "description": description,
                "tags": tags or [],
                "language": "en",
                "domain": "general"
            },
            "statistics": stats,
            "files": files_info,
            "compatibility": {
                "min_bmam_version": "1.0.0",
                "max_bmam_version": "2.0.0",
                "python_version": ">=3.9",
                "required_features": ["sqlite3"]
            }
        }

        # 保存manifest
        with open(archive_path / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)

        # 生成校验和
        checksums = cls._generate_checksums(archive_path)
        with open(archive_path / "checksums.json", 'w') as f:
            json.dump(checksums, f, indent=2)

        # 创建README
        cls._create_readme(archive_path, manifest)

        return cls(archive_path)

    def load(self, target_dir: Path, validate: bool = True) -> Dict[str, Any]:
        """
        加载BMA记忆包到目标目录

        Args:
            target_dir: 目标目录 (通常是data/)
            validate: 是否验证完整性

        Returns:
            加载结果信息
        """
        if validate:
            validation_result = self.validate()
            if not validation_result['valid']:
                raise ValueError(f"Archive validation failed: {validation_result['errors']}")

        # 读取manifest
        with open(self.archive_path / "manifest.json") as f:
            self.manifest = json.load(f)

        # 复制数据库
        db_src = self.archive_path / self.manifest['files']['database']['path']
        db_dst = target_dir / "brain_memory.db"

        # 备份现有数据库 (如果存在)
        if db_dst.exists():
            backup_path = target_dir / f"brain_memory.db.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(db_dst, backup_path)

        shutil.copy2(db_src, db_dst)

        # 复制FAISS索引 (如果存在)
        if "vector_index" in self.manifest['files']:
            faiss_src = self.archive_path / self.manifest['files']['vector_index']['path']
            if faiss_src.exists():
                faiss_dst = target_dir / "faiss_index"

                # 备份现有索引
                if faiss_dst.exists():
                    backup_faiss = target_dir / f"faiss_index.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    if backup_faiss.exists():
                        shutil.rmtree(backup_faiss)
                    shutil.copytree(faiss_dst, backup_faiss)
                    shutil.rmtree(faiss_dst)

                shutil.copytree(faiss_src, faiss_dst)

        return {
            "archive_name": self.manifest['memory_info']['name'],
            "statistics": self.manifest['statistics'],
            "loaded_files": {
                "database": str(db_dst),
                "vector_index": str(target_dir / "faiss_index") if "vector_index" in self.manifest['files'] else None
            },
            "backup_created": True
        }

    def validate(self) -> Dict[str, Any]:
        """验证BMA包的完整性和兼容性"""
        errors = []
        warnings = []

        # 检查manifest
        manifest_path = self.archive_path / "manifest.json"
        if not manifest_path.exists():
            return {"valid": False, "errors": ["manifest.json not found"]}

        with open(manifest_path) as f:
            manifest = json.load(f)

        # 检查格式版本
        if manifest.get('format_version') != self.FORMAT_VERSION:
            warnings.append(f"Format version mismatch: {manifest.get('format_version')} vs {self.FORMAT_VERSION}")

        # 检查必需文件
        for file_key, file_info in manifest.get('files', {}).items():
            if file_info.get('required', False):
                file_path = self.archive_path / file_info['path']
                if not file_path.exists():
                    errors.append(f"Required file missing: {file_info['path']}")

        # 验证校验和
        checksums_path = self.archive_path / "checksums.json"
        if checksums_path.exists():
            with open(checksums_path) as f:
                checksums = json.load(f)

            for file_path, expected_hash in checksums.get('files', {}).items():
                full_path = self.archive_path / file_path
                if full_path.exists():
                    actual_hash = self._calculate_file_hash(full_path)
                    if actual_hash != expected_hash:
                        errors.append(f"Checksum mismatch for {file_path}")
        else:
            warnings.append("No checksums.json found, skipping integrity check")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "manifest": manifest
        }

    @staticmethod
    def _collect_statistics(db_path: Path) -> Dict[str, Any]:
        """从数据库收集统计信息"""
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        try:
            # 总记忆数
            cursor.execute("SELECT COUNT(*) FROM memories WHERE is_active = 1")
            total = cursor.fetchone()[0]

            # 按类型统计
            cursor.execute("""
                SELECT memory_type, COUNT(*)
                FROM memories
                WHERE is_active = 1
                GROUP BY memory_type
            """)
            types = dict(cursor.fetchall())

            # 重要记忆数
            cursor.execute("SELECT COUNT(*) FROM memories WHERE importance > 0.7 AND is_active = 1")
            important = cursor.fetchone()[0]

            # 平均重要性
            cursor.execute("SELECT AVG(importance) FROM memories WHERE is_active = 1")
            avg_importance = cursor.fetchone()[0] or 0.0

            # 时间范围
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM memories WHERE is_active = 1")
            time_range = cursor.fetchone()

            return {
                "total_memories": total,
                "memory_types": types,
                "important_memories": important,
                "avg_importance": round(avg_importance, 3),
                "time_range": {
                    "earliest": time_range[0],
                    "latest": time_range[1]
                }
            }
        finally:
            conn.close()

    @staticmethod
    def _calculate_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
        """计算文件hash"""
        hasher = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def _get_dir_size(path: Path) -> int:
        """计算目录大小"""
        total = 0
        for entry in path.rglob('*'):
            if entry.is_file():
                total += entry.stat().st_size
        return total

    @staticmethod
    def _generate_checksums(archive_path: Path) -> Dict[str, Any]:
        """生成所有文件的校验和"""
        checksums = {
            "algorithm": "sha256",
            "files": {},
            "verified_at": datetime.now().isoformat() + "Z"
        }

        for file_path in archive_path.rglob('*'):
            if file_path.is_file() and file_path.name != "checksums.json":
                rel_path = file_path.relative_to(archive_path)
                checksums['files'][str(rel_path)] = MemoryArchive._calculate_file_hash(file_path)

        return checksums

    @staticmethod
    def _create_readme(archive_path: Path, manifest: Dict):
        """创建人类可读的README"""
        readme_content = f"""# BMAM Memory Archive

## {manifest['memory_info']['name']}

{manifest['memory_info']['description']}

### Statistics

- **Total Memories**: {manifest['statistics']['total_memories']}
- **Memory Types**: {manifest['statistics']['memory_types']}
- **Important Memories**: {manifest['statistics']['important_memories']}
- **Average Importance**: {manifest['statistics']['avg_importance']}

### Tags

{', '.join(manifest['memory_info']['tags'])}

### Created

- **Date**: {manifest['created_at']}
- **By**: {manifest['created_by']}

### Usage

```python
from src.memory.memory_archive import MemoryArchive

# Load this archive
archive = MemoryArchive(Path("{archive_path.name}"))
archive.load(Path("data/"))
```

### Format Version

{manifest['format_version']}
"""

        with open(archive_path / "README.md", 'w') as f:
            f.write(readme_content)
```

### 2. BrainInspiredCoordinator集成

```python
# src/coordination/brain_coordinator_refactored.py 添加方法

class BrainInspiredCoordinator:

    def load_memory_archive(self, archive_path: str, validate: bool = True) -> Dict[str, Any]:
        """
        加载BMA记忆包

        Args:
            archive_path: BMA包路径
            validate: 是否验证完整性

        Returns:
            加载结果

        Example:
            coordinator = BrainInspiredCoordinator()
            result = coordinator.load_memory_archive("exports/baseline.bma")
            await coordinator.initialize()  # 使用新载入的记忆
        """
        from ..memory.memory_archive import MemoryArchive

        archive = MemoryArchive(Path(archive_path))

        # 加载到data目录
        result = archive.load(Path("data"), validate=validate)

        logger.info(f"Loaded memory archive: {result['archive_name']}")
        logger.info(f"Total memories: {result['statistics']['total_memories']}")

        return result

    def export_memory_archive(
        self,
        name: str,
        output_dir: str = "exports",
        description: str = "",
        tags: List[str] = None
    ) -> str:
        """
        导出当前记忆为BMA包

        Args:
            name: 导出包名称
            output_dir: 输出目录
            description: 描述
            tags: 标签

        Returns:
            导出包路径

        Example:
            coordinator = BrainInspiredCoordinator()
            await coordinator.initialize()
            # ... 使用coordinator ...

            # 导出记忆
            archive_path = coordinator.export_memory_archive(
                "my_memory",
                description="My custom memory state",
                tags=["production", "v1.0"]
            )
        """
        from ..memory.memory_archive import MemoryArchive

        source_db = Path("data/brain_memory.db")
        if not source_db.exists():
            raise FileNotFoundError("No memory database found")

        archive = MemoryArchive.create(
            name=name,
            source_db_path=source_db,
            output_dir=Path(output_dir),
            description=description,
            tags=tags or [],
            include_faiss=True
        )

        logger.info(f"Exported memory archive: {archive.archive_path}")

        return str(archive.archive_path)
```

---

## 使用示例

### 创建BMA包

```python
from src.memory.memory_archive import MemoryArchive
from pathlib import Path

# 创建记忆包
archive = MemoryArchive.create(
    name="locomo_baseline",
    source_db_path=Path("data/brain_memory.db"),
    output_dir=Path("exports"),
    description="LoCoMo conv-26完整对话记忆",
    tags=["baseline", "test", "locomo"],
    include_faiss=True
)

print(f"Created: {archive.archive_path}")
```

### 加载BMA包

```python
from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

# 创建coordinator
coordinator = BrainInspiredCoordinator()

# 加载记忆包
result = coordinator.load_memory_archive("exports/locomo_baseline.bma")
print(f"Loaded {result['statistics']['total_memories']} memories")

# 初始化 (使用载入的记忆)
await coordinator.initialize()

# 开始使用
response = await coordinator.process_input("When did Caroline go to the support group?")
```

### 验证BMA包

```python
from src.memory.memory_archive import MemoryArchive

archive = MemoryArchive(Path("exports/locomo_baseline.bma"))
validation = archive.validate()

if validation['valid']:
    print("✅ Archive is valid")
else:
    print(f"❌ Errors: {validation['errors']}")
```

---

## 向后兼容性

### 自动迁移现有快照

```python
# scripts/migrate_old_snapshots.py

from pathlib import Path
from src.memory.memory_archive import MemoryArchive
import json

def migrate_old_snapshot(snapshot_id: str, output_dir: Path):
    """将旧格式快照迁移到BMA格式"""

    # 读取旧格式元数据
    metadata_file = Path("data/snapshots/snapshots_metadata.json")
    with open(metadata_file) as f:
        metadata = json.load(f)

    # 查找快照
    snapshot = next((s for s in metadata['snapshots'] if s['snapshot_id'] == snapshot_id), None)
    if not snapshot:
        raise ValueError(f"Snapshot {snapshot_id} not found")

    # 旧格式数据库路径
    old_db = Path(f"data/snapshots/{snapshot_id}_brain_memory.db")

    # 创建BMA包
    archive = MemoryArchive.create(
        name=snapshot['name'],
        source_db_path=old_db,
        output_dir=output_dir,
        description=snapshot.get('description', ''),
        tags=snapshot.get('tags', []),
        include_faiss=snapshot['files'].get('faiss_index', False)
    )

    print(f"Migrated {snapshot_id} → {archive.archive_path}")
```

---

## 总结

### ✅ 设计优势

1. **统一格式**: 所有记忆包使用标准BMA格式
2. **自包含**: 包含所有必需文件和元数据
3. **可验证**: 校验和保证完整性
4. **可移植**: 可在不同环境间传输
5. **版本化**: 支持格式演进和兼容性检查
6. **人类可读**: 包含manifest.json和README.md

### 📦 BMA格式特性

| 特性 | 说明 |
|------|------|
| **标准化** | 固定的目录结构和文件命名 |
| **完整性** | 校验和验证 |
| **元数据** | 丰富的统计和描述信息 |
| **兼容性** | 版本检查和特性要求 |
| **可扩展** | 支持添加自定义文件 |

### 🎯 使用流程

```
1. 创建记忆 → 2. 导出BMA包 → 3. 分享/存档 → 4. 加载BMA包 → 5. 使用记忆
```

---

**准备开始实现?** 我将:
1. 备份当前代码
2. 创建 `src/memory/memory_archive.py`
3. 集成到 `BrainInspiredCoordinator`
4. 创建迁移脚本
5. 更新文档

请确认后开始执行!
