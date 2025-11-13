#!/usr/bin/env python3
"""
BMAM Memory Manager - 可塑性记忆管理系统
支持自定义快照、导入导出、时间回溯

功能:
- 创建带标签的快照 (自定义状态)
- 导入/导出记忆配置
- 时间旅行 (回溯到任意快照)
- 快照对比分析
- 记忆健康度检查
- 自动快照 (可选)

Author: Claude Code
Date: 2025-11-12
"""

import os
import sys
import json
import sqlite3
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import hashlib


class MemoryManager:
    """可塑性记忆管理器"""

    def __init__(self, data_dir: str = "data", snapshot_dir: str = "data/snapshots"):
        self.data_dir = Path(data_dir)
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

        # 快照元数据文件
        self.metadata_file = self.snapshot_dir / "snapshots_metadata.json"
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> Dict:
        """加载快照元数据"""
        if self.metadata_file.exists():
            with open(self.metadata_file) as f:
                return json.load(f)
        return {"snapshots": [], "version": "1.0"}

    def _save_metadata(self):
        """保存快照元数据"""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)

    def _get_memory_stats(self, db_path: Path) -> Dict:
        """获取记忆库统计信息"""
        if not db_path.exists():
            return {"total_memories": 0, "memory_types": {}, "error": "Database not found"}

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

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

            # 访问频率统计
            cursor.execute("SELECT AVG(access_frequency) FROM memories WHERE is_active = 1")
            avg_access = cursor.fetchone()[0] or 0.0

            # 时间范围
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM memories WHERE is_active = 1")
            time_range = cursor.fetchone()

            conn.close()

            return {
                "total_memories": total,
                "memory_types": types,
                "important_memories": important,
                "avg_importance": round(avg_importance, 3),
                "avg_access_frequency": round(avg_access, 2),
                "time_range": {
                    "earliest": time_range[0],
                    "latest": time_range[1]
                }
            }
        except Exception as e:
            return {"error": str(e)}

    def _calculate_db_hash(self, db_path: Path) -> str:
        """计算数据库文件hash (用于去重)"""
        if not db_path.exists():
            return ""

        hasher = hashlib.md5()
        with open(db_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def create_snapshot(
        self,
        name: str,
        description: str = "",
        tags: List[str] = None,
        auto: bool = False
    ) -> Dict:
        """
        创建记忆快照

        Args:
            name: 快照名称 (唯一标识)
            description: 快照描述
            tags: 标签列表 (用于分类)
            auto: 是否自动快照

        Returns:
            快照信息
        """
        timestamp = datetime.now().isoformat()
        snapshot_id = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 检查是否存在同名快照
        existing = [s for s in self.metadata["snapshots"] if s["name"] == name]
        if existing and not auto:
            print(f"⚠️  Warning: Snapshot '{name}' already exists. Creating versioned snapshot.")

        # 复制数据库文件
        db_files = ["brain_memory.db", "memories.db"]
        copied_files = []

        for db_file in db_files:
            src = self.data_dir / db_file
            if src.exists():
                dst = self.snapshot_dir / f"{snapshot_id}_{db_file}"
                shutil.copy2(src, dst)
                copied_files.append(db_file)

        if not copied_files:
            return {"error": "No database files found to snapshot"}

        # 复制FAISS索引 (如果存在)
        faiss_src = self.data_dir / "faiss_index"
        faiss_copied = False
        if faiss_src.exists():
            faiss_dst = self.snapshot_dir / f"{snapshot_id}_faiss"
            shutil.copytree(faiss_src, faiss_dst, dirs_exist_ok=True)
            faiss_copied = True

        # 获取记忆统计
        primary_db = self.data_dir / "brain_memory.db"
        if not primary_db.exists():
            primary_db = self.data_dir / "memories.db"

        stats = self._get_memory_stats(primary_db)
        db_hash = self._calculate_db_hash(primary_db)

        # 保存快照元数据
        snapshot_meta = {
            "snapshot_id": snapshot_id,
            "name": name,
            "description": description,
            "tags": tags or [],
            "timestamp": timestamp,
            "auto": auto,
            "files": {
                "databases": copied_files,
                "faiss_index": faiss_copied
            },
            "stats": stats,
            "db_hash": db_hash
        }

        self.metadata["snapshots"].append(snapshot_meta)
        self._save_metadata()

        return snapshot_meta

    def restore_snapshot(self, identifier: str) -> Dict:
        """
        恢复快照

        Args:
            identifier: 快照名称或snapshot_id

        Returns:
            恢复信息
        """
        # 查找快照
        snapshot = None
        for s in self.metadata["snapshots"]:
            if s["name"] == identifier or s["snapshot_id"] == identifier:
                snapshot = s
                break

        if not snapshot:
            return {"error": f"Snapshot '{identifier}' not found"}

        snapshot_id = snapshot["snapshot_id"]

        # 恢复数据库文件
        restored_files = []
        for db_file in snapshot["files"]["databases"]:
            src = self.snapshot_dir / f"{snapshot_id}_{db_file}"
            if src.exists():
                # 备份当前文件 (保护性措施)
                current = self.data_dir / db_file
                if current.exists():
                    backup = self.data_dir / f"{db_file}.before_restore"
                    shutil.copy2(current, backup)

                # 恢复快照
                shutil.copy2(src, self.data_dir / db_file)
                restored_files.append(db_file)

        # 恢复FAISS索引
        faiss_restored = False
        if snapshot["files"]["faiss_index"]:
            faiss_src = self.snapshot_dir / f"{snapshot_id}_faiss"
            if faiss_src.exists():
                faiss_dst = self.data_dir / "faiss_index"

                # 备份当前FAISS
                if faiss_dst.exists():
                    backup_faiss = self.data_dir / "faiss_index.before_restore"
                    if backup_faiss.exists():
                        shutil.rmtree(backup_faiss)
                    shutil.copytree(faiss_dst, backup_faiss)
                    shutil.rmtree(faiss_dst)

                # 恢复FAISS
                shutil.copytree(faiss_src, faiss_dst)
                faiss_restored = True

        return {
            "snapshot_id": snapshot_id,
            "name": snapshot["name"],
            "timestamp": snapshot["timestamp"],
            "restored_files": {
                "databases": restored_files,
                "faiss_index": faiss_restored
            },
            "stats": snapshot["stats"]
        }

    def list_snapshots(self, tag: Optional[str] = None) -> List[Dict]:
        """
        列出所有快照

        Args:
            tag: 可选,按标签过滤

        Returns:
            快照列表
        """
        snapshots = self.metadata["snapshots"]

        if tag:
            snapshots = [s for s in snapshots if tag in s.get("tags", [])]

        # 按时间倒序排列
        snapshots = sorted(snapshots, key=lambda s: s["timestamp"], reverse=True)

        return snapshots

    def delete_snapshot(self, identifier: str) -> Dict:
        """删除快照"""
        snapshot = None
        for i, s in enumerate(self.metadata["snapshots"]):
            if s["name"] == identifier or s["snapshot_id"] == identifier:
                snapshot = s
                snapshot_idx = i
                break

        if not snapshot:
            return {"error": f"Snapshot '{identifier}' not found"}

        snapshot_id = snapshot["snapshot_id"]

        # 删除文件
        deleted_files = []

        # 删除数据库文件
        for db_file in snapshot["files"]["databases"]:
            file_path = self.snapshot_dir / f"{snapshot_id}_{db_file}"
            if file_path.exists():
                file_path.unlink()
                deleted_files.append(db_file)

        # 删除FAISS索引
        if snapshot["files"]["faiss_index"]:
            faiss_path = self.snapshot_dir / f"{snapshot_id}_faiss"
            if faiss_path.exists():
                shutil.rmtree(faiss_path)
                deleted_files.append("faiss_index")

        # 从元数据中移除
        del self.metadata["snapshots"][snapshot_idx]
        self._save_metadata()

        return {
            "snapshot_id": snapshot_id,
            "name": snapshot["name"],
            "deleted_files": deleted_files
        }

    def export_snapshot(self, identifier: str, export_path: str) -> Dict:
        """
        导出快照为独立包

        Args:
            identifier: 快照名称或ID
            export_path: 导出目录路径

        Returns:
            导出信息
        """
        # 查找快照
        snapshot = None
        for s in self.metadata["snapshots"]:
            if s["name"] == identifier or s["snapshot_id"] == identifier:
                snapshot = s
                break

        if not snapshot:
            return {"error": f"Snapshot '{identifier}' not found"}

        snapshot_id = snapshot["snapshot_id"]
        export_dir = Path(export_path) / snapshot["name"]
        export_dir.mkdir(parents=True, exist_ok=True)

        # 复制数据库文件
        exported_files = []
        for db_file in snapshot["files"]["databases"]:
            src = self.snapshot_dir / f"{snapshot_id}_{db_file}"
            if src.exists():
                dst = export_dir / db_file
                shutil.copy2(src, dst)
                exported_files.append(db_file)

        # 复制FAISS索引
        if snapshot["files"]["faiss_index"]:
            faiss_src = self.snapshot_dir / f"{snapshot_id}_faiss"
            if faiss_src.exists():
                faiss_dst = export_dir / "faiss_index"
                shutil.copytree(faiss_src, faiss_dst, dirs_exist_ok=True)
                exported_files.append("faiss_index")

        # 导出元数据
        export_meta = {
            **snapshot,
            "exported_at": datetime.now().isoformat(),
            "export_version": "1.0"
        }

        with open(export_dir / "snapshot_metadata.json", 'w') as f:
            json.dump(export_meta, f, indent=2)

        return {
            "snapshot_id": snapshot_id,
            "name": snapshot["name"],
            "export_path": str(export_dir),
            "exported_files": exported_files
        }

    def import_snapshot(self, import_path: str, new_name: Optional[str] = None) -> Dict:
        """
        导入外部快照

        Args:
            import_path: 导入目录路径
            new_name: 可选,重命名快照

        Returns:
            导入信息
        """
        import_dir = Path(import_path)

        if not import_dir.exists():
            return {"error": f"Import path not found: {import_path}"}

        # 读取元数据
        meta_file = import_dir / "snapshot_metadata.json"
        if not meta_file.exists():
            return {"error": "No snapshot_metadata.json found"}

        with open(meta_file) as f:
            imported_meta = json.load(f)

        # 生成新的snapshot_id
        name = new_name or imported_meta["name"]
        timestamp = datetime.now().isoformat()
        snapshot_id = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 复制数据库文件
        imported_files = []
        for db_file in imported_meta["files"]["databases"]:
            src = import_dir / db_file
            if src.exists():
                dst = self.snapshot_dir / f"{snapshot_id}_{db_file}"
                shutil.copy2(src, dst)
                imported_files.append(db_file)

        # 复制FAISS索引
        faiss_imported = False
        if imported_meta["files"]["faiss_index"]:
            faiss_src = import_dir / "faiss_index"
            if faiss_src.exists():
                faiss_dst = self.snapshot_dir / f"{snapshot_id}_faiss"
                shutil.copytree(faiss_src, faiss_dst, dirs_exist_ok=True)
                faiss_imported = True

        # 保存新的元数据
        new_meta = {
            "snapshot_id": snapshot_id,
            "name": name,
            "description": imported_meta.get("description", "") + " (Imported)",
            "tags": imported_meta.get("tags", []) + ["imported"],
            "timestamp": timestamp,
            "auto": False,
            "files": {
                "databases": imported_files,
                "faiss_index": faiss_imported
            },
            "stats": imported_meta.get("stats", {}),
            "db_hash": imported_meta.get("db_hash", ""),
            "imported_from": import_path,
            "original_timestamp": imported_meta.get("timestamp", "")
        }

        self.metadata["snapshots"].append(new_meta)
        self._save_metadata()

        return new_meta

    def compare_snapshots(self, id1: str, id2: str) -> Dict:
        """对比两个快照"""
        snapshot1 = next((s for s in self.metadata["snapshots"]
                         if s["name"] == id1 or s["snapshot_id"] == id1), None)
        snapshot2 = next((s for s in self.metadata["snapshots"]
                         if s["name"] == id2 or s["snapshot_id"] == id2), None)

        if not snapshot1 or not snapshot2:
            return {"error": "One or both snapshots not found"}

        stats1 = snapshot1.get("stats", {})
        stats2 = snapshot2.get("stats", {})

        return {
            "snapshot1": {
                "name": snapshot1["name"],
                "timestamp": snapshot1["timestamp"],
                "stats": stats1
            },
            "snapshot2": {
                "name": snapshot2["name"],
                "timestamp": snapshot2["timestamp"],
                "stats": stats2
            },
            "differences": {
                "memory_count_delta": stats2.get("total_memories", 0) - stats1.get("total_memories", 0),
                "importance_delta": round(stats2.get("avg_importance", 0) - stats1.get("avg_importance", 0), 3),
                "access_delta": round(stats2.get("avg_access_frequency", 0) - stats1.get("avg_access_frequency", 0), 2),
                "identical": snapshot1.get("db_hash") == snapshot2.get("db_hash")
            }
        }

    def check_memory_health(self) -> Dict:
        """检查当前记忆系统健康度"""
        primary_db = self.data_dir / "brain_memory.db"
        if not primary_db.exists():
            primary_db = self.data_dir / "memories.db"

        if not primary_db.exists():
            return {"error": "No memory database found", "health_score": 0}

        stats = self._get_memory_stats(primary_db)

        # 计算健康分数
        health_score = 100.0
        issues = []

        # 检查1: 记忆数量异常
        total = stats.get("total_memories", 0)
        if total == 0:
            health_score -= 50
            issues.append("No memories found")
        elif total > 100000:
            health_score -= 20
            issues.append("Very large memory database (>100K), may impact performance")

        # 检查2: 平均重要性异常
        avg_importance = stats.get("avg_importance", 0)
        if avg_importance < 0.2:
            health_score -= 15
            issues.append("Low average importance (<0.2), many low-value memories")

        # 检查3: 访问频率异常
        avg_access = stats.get("avg_access_frequency", 0)
        if avg_access < 0.1 and total > 100:
            health_score -= 10
            issues.append("Low access frequency, memories may not be actively used")

        # 检查4: FAISS索引缺失
        faiss_exists = (self.data_dir / "faiss_index").exists()
        if not faiss_exists and total > 0:
            health_score -= 5
            issues.append("FAISS index missing, semantic search unavailable")

        return {
            "health_score": max(0, health_score),
            "stats": stats,
            "issues": issues,
            "recommendations": self._get_recommendations(health_score, issues)
        }

    def _get_recommendations(self, score: float, issues: List[str]) -> List[str]:
        """根据健康度给出建议"""
        recommendations = []

        if score < 50:
            recommendations.append("Consider creating a snapshot before making changes")

        if "No memories found" in str(issues):
            recommendations.append("Start by ingesting conversation data")

        if "Very large memory database" in str(issues):
            recommendations.append("Consider archiving old memories or enabling forgetting mechanism")

        if "Low average importance" in str(issues):
            recommendations.append("Review importance scoring or clean up low-value memories")

        if "FAISS index missing" in str(issues):
            recommendations.append("Rebuild FAISS index for semantic search")

        if not recommendations:
            recommendations.append("Memory system is healthy!")

        return recommendations


def main():
    parser = argparse.ArgumentParser(
        description="BMAM Memory Manager - 可塑性记忆管理系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 创建快照
  python3 scripts/memory_manager.py create clean_state --desc "干净的初始状态" --tags baseline test

  # 列出所有快照
  python3 scripts/memory_manager.py list

  # 恢复快照
  python3 scripts/memory_manager.py restore clean_state

  # 导出快照
  python3 scripts/memory_manager.py export clean_state --path ./exports

  # 导入快照
  python3 scripts/memory_manager.py import ./exports/clean_state --name imported_clean

  # 对比快照
  python3 scripts/memory_manager.py compare clean_state after_test

  # 检查健康度
  python3 scripts/memory_manager.py health
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # create命令
    create_parser = subparsers.add_parser('create', help='Create a snapshot')
    create_parser.add_argument('name', help='Snapshot name')
    create_parser.add_argument('--desc', default='', help='Description')
    create_parser.add_argument('--tags', nargs='*', default=[], help='Tags')

    # list命令
    list_parser = subparsers.add_parser('list', help='List all snapshots')
    list_parser.add_argument('--tag', help='Filter by tag')

    # restore命令
    restore_parser = subparsers.add_parser('restore', help='Restore a snapshot')
    restore_parser.add_argument('identifier', help='Snapshot name or ID')

    # delete命令
    delete_parser = subparsers.add_parser('delete', help='Delete a snapshot')
    delete_parser.add_argument('identifier', help='Snapshot name or ID')

    # export命令
    export_parser = subparsers.add_parser('export', help='Export snapshot')
    export_parser.add_argument('identifier', help='Snapshot name or ID')
    export_parser.add_argument('--path', default='./exports', help='Export directory')

    # import命令
    import_parser = subparsers.add_parser('import', help='Import snapshot')
    import_parser.add_argument('path', help='Import directory path')
    import_parser.add_argument('--name', help='New snapshot name')

    # compare命令
    compare_parser = subparsers.add_parser('compare', help='Compare two snapshots')
    compare_parser.add_argument('id1', help='First snapshot')
    compare_parser.add_argument('id2', help='Second snapshot')

    # health命令
    health_parser = subparsers.add_parser('health', help='Check memory health')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    manager = MemoryManager()

    if args.command == 'create':
        result = manager.create_snapshot(args.name, args.desc, args.tags)
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Snapshot created: {result['snapshot_id']}")
            print(f"   Name: {result['name']}")
            print(f"   Description: {result['description']}")
            print(f"   Tags: {', '.join(result['tags'])}")
            print(f"   Memories: {result['stats'].get('total_memories', 0)}")

    elif args.command == 'list':
        snapshots = manager.list_snapshots(tag=args.tag)
        if not snapshots:
            print("No snapshots found")
        else:
            print(f"\n{'='*80}")
            print(f"Available Snapshots ({len(snapshots)})")
            print(f"{'='*80}\n")

            for snap in snapshots:
                print(f"📸 {snap['name']}")
                print(f"   ID: {snap['snapshot_id']}")
                print(f"   Created: {snap['timestamp']}")
                print(f"   Description: {snap.get('description', 'N/A')}")
                print(f"   Tags: {', '.join(snap.get('tags', []))}")
                print(f"   Memories: {snap['stats'].get('total_memories', 0)}")
                print(f"   Avg Importance: {snap['stats'].get('avg_importance', 0)}")
                print()

    elif args.command == 'restore':
        result = manager.restore_snapshot(args.identifier)
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Snapshot restored: {result['name']}")
            print(f"   Timestamp: {result['timestamp']}")
            print(f"   Restored databases: {', '.join(result['restored_files']['databases'])}")
            print(f"   FAISS index: {'✅' if result['restored_files']['faiss_index'] else '❌'}")
            print(f"   Memories: {result['stats'].get('total_memories', 0)}")

    elif args.command == 'delete':
        result = manager.delete_snapshot(args.identifier)
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Snapshot deleted: {result['name']}")

    elif args.command == 'export':
        result = manager.export_snapshot(args.identifier, args.path)
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Snapshot exported: {result['name']}")
            print(f"   Export path: {result['export_path']}")
            print(f"   Files: {', '.join(result['exported_files'])}")

    elif args.command == 'import':
        result = manager.import_snapshot(args.path, args.name)
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Snapshot imported: {result['name']}")
            print(f"   ID: {result['snapshot_id']}")
            print(f"   Original timestamp: {result.get('original_timestamp', 'N/A')}")

    elif args.command == 'compare':
        result = manager.compare_snapshots(args.id1, args.id2)
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"\n{'='*80}")
            print("Snapshot Comparison")
            print(f"{'='*80}\n")

            snap1 = result['snapshot1']
            snap2 = result['snapshot2']
            diff = result['differences']

            print(f"Snapshot 1: {snap1['name']} ({snap1['timestamp']})")
            print(f"  Memories: {snap1['stats'].get('total_memories', 0)}")
            print(f"  Avg Importance: {snap1['stats'].get('avg_importance', 0)}")
            print()

            print(f"Snapshot 2: {snap2['name']} ({snap2['timestamp']})")
            print(f"  Memories: {snap2['stats'].get('total_memories', 0)}")
            print(f"  Avg Importance: {snap2['stats'].get('avg_importance', 0)}")
            print()

            print("Differences:")
            print(f"  Memory count delta: {diff['memory_count_delta']:+d}")
            print(f"  Importance delta: {diff['importance_delta']:+.3f}")
            print(f"  Access frequency delta: {diff['access_delta']:+.2f}")
            print(f"  Identical: {'✅ Yes' if diff['identical'] else '❌ No'}")

    elif args.command == 'health':
        result = manager.check_memory_health()
        print(f"\n{'='*80}")
        print("Memory System Health Check")
        print(f"{'='*80}\n")

        print(f"Health Score: {result['health_score']:.1f}/100")
        print()

        if result.get('stats'):
            print("Statistics:")
            stats = result['stats']
            print(f"  Total memories: {stats.get('total_memories', 0)}")
            print(f"  Memory types: {stats.get('memory_types', {})}")
            print(f"  Avg importance: {stats.get('avg_importance', 0)}")
            print(f"  Avg access frequency: {stats.get('avg_access_frequency', 0)}")
            print()

        if result.get('issues'):
            print("Issues:")
            for issue in result['issues']:
                print(f"  ⚠️  {issue}")
            print()

        print("Recommendations:")
        for rec in result.get('recommendations', []):
            print(f"  💡 {rec}")


if __name__ == "__main__":
    main()
