"""
Storage Coordinator - 存储协调器
动态协作管理，防止文件损坏和数据不同步

核心功能：
1. 原子写入 - 使用临时文件+重命名防止写入中断导致损坏
2. 写入锁 - 防止并发写入冲突
3. 自动序列化 - 处理 ndarray 等特殊类型
4. 统一存储接口 - 协调 KV 存储和状态文件
"""

import json
import os
import threading
import logging
import shutil
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class NumpyEncoder(json.JSONEncoder):
    """处理 numpy 类型的 JSON 编码器"""
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


@dataclass
class WriteOperation:
    """写入操作记录"""
    file_path: str
    timestamp: datetime
    success: bool
    error: Optional[str] = None


class StorageCoordinator:
    """
    存储协调器 - 动态协作管理

    解决的问题：
    1. ndarray 序列化错误 → 自动转换
    2. 并发写入导致文件损坏 → 写入锁 + 原子写入
    3. 多存储系统不同步 → 统一协调
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._file_locks: Dict[str, threading.RLock] = {}
        self._global_lock = threading.RLock()
        self._write_history: List[WriteOperation] = []
        self._max_history = 100

        # 备份目录
        self._backup_dir = Path("data/storage_backups")
        self._backup_dir.mkdir(parents=True, exist_ok=True)

        self._initialized = True
        logger.info("StorageCoordinator initialized")

    def _get_file_lock(self, file_path: str) -> threading.RLock:
        """获取文件级别的锁"""
        with self._global_lock:
            if file_path not in self._file_locks:
                self._file_locks[file_path] = threading.RLock()
            return self._file_locks[file_path]

    @contextmanager
    def file_operation(self, file_path: str):
        """文件操作上下文管理器"""
        lock = self._get_file_lock(file_path)
        lock.acquire()
        try:
            yield
        finally:
            lock.release()

    def safe_json_dump(self, data: Any, file_path: str, create_backup: bool = True) -> bool:
        """
        安全的 JSON 写入

        特性：
        1. 自动处理 ndarray 等特殊类型
        2. 原子写入（先写临时文件再重命名）
        3. 可选备份
        4. 文件锁防止并发写入

        Args:
            data: 要写入的数据
            file_path: 目标文件路径
            create_backup: 是否创建备份

        Returns:
            是否成功
        """
        file_path = str(file_path)
        lock = self._get_file_lock(file_path)

        operation = WriteOperation(
            file_path=file_path,
            timestamp=datetime.now(),
            success=False
        )

        with lock:
            try:
                # 1. 创建备份（如果文件存在且需要备份）
                if create_backup and os.path.exists(file_path):
                    backup_name = f"{Path(file_path).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    backup_path = self._backup_dir / backup_name
                    try:
                        shutil.copy2(file_path, backup_path)
                        # 只保留最近10个备份
                        self._cleanup_old_backups(Path(file_path).stem, keep=10)
                    except Exception as e:
                        logger.warning(f"Backup failed: {e}")

                # 2. 写入临时文件
                temp_path = f"{file_path}.tmp"
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, cls=NumpyEncoder, ensure_ascii=False, indent=2)

                # 3. 验证临时文件
                with open(temp_path, 'r', encoding='utf-8') as f:
                    json.load(f)  # 确保可以正确读取

                # 4. 原子重命名
                os.replace(temp_path, file_path)

                operation.success = True
                logger.debug(f"Safe write completed: {file_path}")

            except Exception as e:
                operation.error = str(e)
                logger.error(f"Safe write failed for {file_path}: {e}")

                # 清理临时文件
                temp_path = f"{file_path}.tmp"
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass

            finally:
                self._record_operation(operation)

        return operation.success

    def safe_json_load(self, file_path: str) -> Optional[Any]:
        """
        安全的 JSON 读取

        特性：
        1. 文件锁防止读取时被修改
        2. 如果主文件损坏，尝试从备份恢复

        Args:
            file_path: 文件路径

        Returns:
            读取的数据，失败返回 None
        """
        file_path = str(file_path)
        lock = self._get_file_lock(file_path)

        with lock:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in {file_path}: {e}")

                # 尝试从备份恢复
                backup = self._find_latest_backup(Path(file_path).stem)
                if backup:
                    logger.info(f"Attempting to restore from backup: {backup}")
                    try:
                        with open(backup, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        # 恢复成功，覆盖损坏的文件
                        shutil.copy2(backup, file_path)
                        logger.info(f"Successfully restored from backup")
                        return data
                    except Exception as be:
                        logger.error(f"Backup restore failed: {be}")

                return None
            except FileNotFoundError:
                return None
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")
                return None

    def _cleanup_old_backups(self, prefix: str, keep: int = 10):
        """清理旧备份，只保留最近的 keep 个"""
        backups = sorted(
            self._backup_dir.glob(f"{prefix}_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        for old_backup in backups[keep:]:
            try:
                old_backup.unlink()
            except:
                pass

    def _find_latest_backup(self, prefix: str) -> Optional[Path]:
        """找到最新的有效备份"""
        backups = sorted(
            self._backup_dir.glob(f"{prefix}_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        for backup in backups:
            try:
                with open(backup, 'r') as f:
                    json.load(f)  # 验证备份有效
                return backup
            except:
                continue
        return None

    def _record_operation(self, operation: WriteOperation):
        """记录写入操作"""
        self._write_history.append(operation)
        if len(self._write_history) > self._max_history:
            self._write_history = self._write_history[-self._max_history:]

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        recent_ops = self._write_history[-20:]
        success_count = sum(1 for op in recent_ops if op.success)

        return {
            'total_operations': len(self._write_history),
            'recent_success_rate': success_count / len(recent_ops) if recent_ops else 1.0,
            'active_locks': len(self._file_locks),
            'backup_dir': str(self._backup_dir),
            'backup_count': len(list(self._backup_dir.glob("*.json")))
        }

    def convert_for_json(self, obj: Any) -> Any:
        """
        递归转换对象为可 JSON 序列化的格式

        处理：ndarray, datetime, dataclass 等
        """
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: self.convert_for_json(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self.convert_for_json(item) for item in obj]
        if hasattr(obj, '__dict__'):
            return self.convert_for_json(obj.__dict__)

        # 尝试转字符串
        try:
            return str(obj)
        except:
            return None


# 全局单例
_storage_coordinator = None

def get_storage_coordinator() -> StorageCoordinator:
    """获取存储协调器单例"""
    global _storage_coordinator
    if _storage_coordinator is None:
        _storage_coordinator = StorageCoordinator()
    return _storage_coordinator
