"""
Unified Path Configuration for BMAM Framework
BMAM框架统一路径配置

🔥 Phase 0 Fix: Centralized path management to fix persistence issues

Provides absolute paths for all brain regions and data storage,
preventing inconsistencies between save and load operations.
"""

from pathlib import Path
import os
import logging


class BMAMPaths:
    """
    Centralized Path Management for BMAM Framework
    BMAM框架集中路径管理

    All paths are absolute paths derived from BMAM root.
    This ensures consistency across different execution contexts.

    🔥 Refactored: All data now lives in BMAM/data/
    - DB files, JSON states, vector indices all in one place
    """

    # BMAM root (this file is at BMAM/src/utils/paths.py)
    BMAM_ROOT = Path(__file__).parent.parent.parent.resolve()

    # Project root (parent of BMAM, for legacy compatibility)
    PROJECT_ROOT = BMAM_ROOT.parent

    # 🔥 UNIFIED data directory - everything in BMAM/data/
    # Support BMAM_DATA_DIR env var for parallel testing with isolated data dirs
    DATA_DIR = Path(os.environ.get('BMAM_DATA_DIR', '')) if os.environ.get('BMAM_DATA_DIR') else BMAM_ROOT / "data"
    PROJECT_DATA_DIR = DATA_DIR  # Legacy alias
    BMAM_DATA_DIR = DATA_DIR     # Legacy alias

    @classmethod
    def reinitialize_paths(cls):
        """重新初始化路径 (当环境变量在运行时设置时调用)"""
        env_data_dir = os.environ.get('BMAM_DATA_DIR', '')
        if env_data_dir:
            cls.DATA_DIR = Path(env_data_dir)
        else:
            cls.DATA_DIR = cls.BMAM_ROOT / "data"
        cls.PROJECT_DATA_DIR = cls.DATA_DIR
        cls.BMAM_DATA_DIR = cls.DATA_DIR

        # 更新所有依赖路径
        cls.TEMPORAL_LOBE_DB = cls.PROJECT_DATA_DIR / "temporal_lobe.db"
        cls.BRAIN_MEMORY_DB = cls.PROJECT_DATA_DIR / "brain_memory.db"
        cls.WORKING_MEMORY_DB = cls.PROJECT_DATA_DIR / "working_memory.db"
        cls.HIPPOCAMPUS_STATE = cls.PROJECT_DATA_DIR / "hippocampus_state.json"
        cls.PREFRONTAL_STATE = cls.PROJECT_DATA_DIR / "prefrontal_state.json"
        cls.AMYGDALA_STATE = cls.PROJECT_DATA_DIR / "amygdala_state.json"
        cls.BASAL_GANGLIA_STATE = cls.PROJECT_DATA_DIR / "basal_ganglia_state.json"
        cls.MEMORY_SHAPING_STATE = cls.PROJECT_DATA_DIR / "memory_shaping_state.json"
        cls.MEMORY_VECTORS_INDEX = cls.BMAM_DATA_DIR / "memory_vectors.index"
        cls.MEMORY_VECTORS_MAPPING = cls.BMAM_DATA_DIR / "memory_vectors_mappings.json"
        cls.EMBEDDING_CACHE_DIR = cls.BMAM_DATA_DIR / "embedding_cache"
        cls.KG_CACHE_DIR = cls.PROJECT_DATA_DIR / "knowledge_graph"

    # ============================================================
    # Runtime DB files (in BMAM/data/)
    # ============================================================
    TEMPORAL_LOBE_DB = PROJECT_DATA_DIR / "temporal_lobe.db"
    BRAIN_MEMORY_DB = PROJECT_DATA_DIR / "brain_memory.db"
    WORKING_MEMORY_DB = PROJECT_DATA_DIR / "working_memory.db"

    # Brain region JSON state files (also in PROJECT_DATA_DIR)
    HIPPOCAMPUS_STATE = PROJECT_DATA_DIR / "hippocampus_state.json"
    PREFRONTAL_STATE = PROJECT_DATA_DIR / "prefrontal_state.json"
    AMYGDALA_STATE = PROJECT_DATA_DIR / "amygdala_state.json"
    BASAL_GANGLIA_STATE = PROJECT_DATA_DIR / "basal_ganglia_state.json"
    MEMORY_SHAPING_STATE = PROJECT_DATA_DIR / "memory_shaping_state.json"

    # ============================================================
    # Vector/Embedding files (in BMAM/data/)
    # ============================================================
    MEMORY_VECTORS_INDEX = BMAM_DATA_DIR / "memory_vectors.index"
    # 🔥 Fixed: was .pkl, actual file is .json with plural 's'
    MEMORY_VECTORS_MAPPING = BMAM_DATA_DIR / "memory_vectors_mappings.json"
    EMBEDDING_CACHE_DIR = BMAM_DATA_DIR / "embedding_cache"
    EMBEDDING_CACHE_FILE = EMBEDDING_CACHE_DIR / "embeddings.json"

    # ============================================================
    # Knowledge Graph cache (in BMAM/data/knowledge_graph/)
    # ============================================================
    KG_CACHE_DIR = PROJECT_DATA_DIR / "knowledge_graph"
    KG_GRAPH_PKL = KG_CACHE_DIR / "graph.pkl"
    KG_NODES_JSON = KG_CACHE_DIR / "nodes.json"
    KG_EDGES_JSON = KG_CACHE_DIR / "edges.json"

    # Archive directory (for BMA archives) - now in BMAM/
    # Configurable via BMAM_ARCHIVE_DIR environment variable
    ARCHIVE_DIR = Path(os.getenv('BMAM_ARCHIVE_DIR', '')) if os.getenv('BMAM_ARCHIVE_DIR') else BMAM_ROOT / "archives"

    # Logs directory
    LOGS_DIR = BMAM_ROOT / "logs"

    @classmethod
    def ensure_directories(cls):
        """
        Ensure all required directories exist
        确保所有必需的目录存在
        """
        cls.PROJECT_DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.BMAM_DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.EMBEDDING_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cls.KG_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cls.ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_all_state_files(cls):
        """
        Get list of all brain region state files (JSON states only)
        获取所有脑区状态文件列表

        Returns:
            Dict mapping region name to file path
        """
        return {
            'hippocampus': cls.HIPPOCAMPUS_STATE,
            'prefrontal': cls.PREFRONTAL_STATE,
            'amygdala': cls.AMYGDALA_STATE,
            'basal_ganglia': cls.BASAL_GANGLIA_STATE,
            'memory_shaping': cls.MEMORY_SHAPING_STATE,
        }

    @classmethod
    def get_all_database_files(cls):
        """
        Get list of all SQLite database files
        获取所有SQLite数据库文件列表

        Returns:
            Dict mapping db name to file path
        """
        return {
            'temporal_lobe': cls.TEMPORAL_LOBE_DB,
            'brain_memory': cls.BRAIN_MEMORY_DB,
            'working_memory': cls.WORKING_MEMORY_DB,
        }

    @classmethod
    def get_all_vector_files(cls):
        """
        Get list of all vector/embedding files
        获取所有向量/嵌入文件列表

        Returns:
            Dict mapping file name to file path
        """
        return {
            'vectors_index': cls.MEMORY_VECTORS_INDEX,
            'vectors_mapping': cls.MEMORY_VECTORS_MAPPING,
            'embedding_cache': cls.EMBEDDING_CACHE_FILE,
        }

    @classmethod
    def get_all_kg_cache_files(cls):
        """
        Get list of all knowledge graph cache files
        获取所有知识图谱缓存文件列表

        Returns:
            Dict mapping file name to file path
        """
        return {
            'kg_graph_pkl': cls.KG_GRAPH_PKL,
            'kg_nodes': cls.KG_NODES_JSON,
            'kg_edges': cls.KG_EDGES_JSON,
        }

    @classmethod
    def clean_state_files(cls):
        """
        Clean all brain region state files (JSON only, for testing)
        清除所有脑区状态文件（仅JSON，用于测试）

        Returns:
            List of cleaned file paths
        """
        cleaned = []
        for name, path in cls.get_all_state_files().items():
            if path.exists():
                path.unlink()
                cleaned.append(str(path))
        return cleaned

    @classmethod
    def clean_all_runtime_data(cls):
        """
        🔥 Clean Room Function: Delete ALL runtime data for fresh start
        净室清理函数：删除所有运行时数据以获得干净环境

        This cleans:
        1. All brain region JSON state files (BMAM/data/*.json)
        2. All SQLite databases (BMAM/data/*.db)
        3. All vector indices (BMAM/data/memory_vectors.*)
        4. Embedding cache (BMAM/data/embedding_cache/)
        5. Knowledge Graph cache (BMAM/data/knowledge_graph/)

        Returns:
            Dict with 'cleaned' list and 'errors' list
        """
        result = {'cleaned': [], 'errors': [], 'skipped': []}

        # 1. Clean JSON state files
        for name, path in cls.get_all_state_files().items():
            try:
                if path.exists():
                    path.unlink()
                    result['cleaned'].append(f"[JSON] {path}")
                else:
                    result['skipped'].append(f"[JSON] {path} (not found)")
            except Exception as e:
                result['errors'].append(f"[JSON] {path}: {e}")

        # 2. Clean SQLite databases
        for name, path in cls.get_all_database_files().items():
            try:
                if path.exists():
                    path.unlink()
                    result['cleaned'].append(f"[DB] {path}")
                else:
                    result['skipped'].append(f"[DB] {path} (not found)")
            except Exception as e:
                result['errors'].append(f"[DB] {path}: {e}")

        # 3. Clean vector/embedding files
        for name, path in cls.get_all_vector_files().items():
            try:
                if path.exists():
                    path.unlink()
                    result['cleaned'].append(f"[VEC] {path}")
                else:
                    result['skipped'].append(f"[VEC] {path} (not found)")
            except Exception as e:
                result['errors'].append(f"[VEC] {path}: {e}")

        # 4. Clean knowledge graph cache
        for name, path in cls.get_all_kg_cache_files().items():
            try:
                if path.exists():
                    path.unlink()
                    result['cleaned'].append(f"[KG] {path}")
                else:
                    result['skipped'].append(f"[KG] {path} (not found)")
            except Exception as e:
                result['errors'].append(f"[KG] {path}: {e}")

        # 5. Also clean any legacy .pkl files
        legacy_pkl = cls.BMAM_DATA_DIR / "memory_vectors_mapping.pkl"
        try:
            if legacy_pkl.exists():
                legacy_pkl.unlink()
                result['cleaned'].append(f"[LEGACY] {legacy_pkl}")
        except Exception as e:
            result['errors'].append(f"[LEGACY] {legacy_pkl}: {e}")

        # 6. 🔥 Clean SQLite WAL/SHM journal files (critical for clean room)
        for db_name, db_path in cls.get_all_database_files().items():
            for suffix in ['-wal', '-shm', '-journal']:
                journal_path = Path(str(db_path) + suffix)
                try:
                    if journal_path.exists():
                        journal_path.unlink()
                        result['cleaned'].append(f"[WAL/SHM] {journal_path}")
                except Exception as e:
                    result['errors'].append(f"[WAL/SHM] {journal_path}: {e}")

        # 7. Clean any stale lock files or temp files in data directories
        for data_dir in [cls.PROJECT_DATA_DIR, cls.BMAM_DATA_DIR]:
            try:
                for pattern in ['*.lock', '*.tmp', '*.bak']:
                    for f in data_dir.glob(pattern):
                        f.unlink()
                        result['cleaned'].append(f"[TEMP] {f}")
            except Exception as e:
                result['errors'].append(f"[TEMP] {data_dir}/{pattern}: {e}")

        return result

    @classmethod
    def print_clean_room_status(cls):
        """
        Print current state of all data files (for verification)
        打印所有数据文件的当前状态（用于验证）
        """
        print("\n" + "="*60)
        print("  BMAM Data Files Status (Clean Room Check)")
        print("="*60)

        print(f"\n📂 Project Data Dir: {cls.PROJECT_DATA_DIR}")
        print(f"📂 BMAM Data Dir: {cls.BMAM_DATA_DIR}")

        print("\n--- JSON State Files ---")
        for name, path in cls.get_all_state_files().items():
            status = "✅ EXISTS" if path.exists() else "❌ Not found"
            print(f"  {name}: {status}")

        print("\n--- SQLite Databases ---")
        for name, path in cls.get_all_database_files().items():
            if path.exists():
                size = path.stat().st_size / 1024
                print(f"  {name}: ✅ EXISTS ({size:.1f} KB)")
            else:
                print(f"  {name}: ❌ Not found")

        print("\n--- Vector/Embedding Files ---")
        for name, path in cls.get_all_vector_files().items():
            if path.exists():
                size = path.stat().st_size / 1024
                print(f"  {name}: ✅ EXISTS ({size:.1f} KB)")
            else:
                print(f"  {name}: ❌ Not found")

        print("\n--- Knowledge Graph Cache ---")
        for name, path in cls.get_all_kg_cache_files().items():
            if path.exists():
                size = path.stat().st_size / 1024
                print(f"  {name}: ✅ EXISTS ({size:.1f} KB)")
            else:
                print(f"  {name}: ❌ Not found")

        print("="*60 + "\n")

    @classmethod
    def compute_data_snapshot(cls):
        """
        🔬 Compute snapshot of all data files for reproducibility verification
        计算所有数据文件的快照，用于可复现性验证

        Returns:
            Dict with file hashes and summary
        """
        import hashlib
        from datetime import datetime

        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'files': {},
            'total_size_bytes': 0,
            'clean_room': True,
        }

        all_files = {}
        all_files.update(cls.get_all_state_files())
        all_files.update(cls.get_all_database_files())
        all_files.update(cls.get_all_vector_files())

        for name, path in all_files.items():
            if path.exists():
                size = path.stat().st_size
                if size < 10 * 1024 * 1024:  # < 10MB
                    with open(path, 'rb') as f:
                        file_hash = hashlib.md5(f.read()).hexdigest()[:12]
                else:
                    file_hash = f"size_{size}"

                snapshot['files'][name] = {
                    'path': str(path),
                    'size_bytes': size,
                    'hash': file_hash,
                    'exists': True
                }
                snapshot['total_size_bytes'] += size
                snapshot['clean_room'] = False
            else:
                snapshot['files'][name] = {'path': str(path), 'exists': False}

        return snapshot

    @classmethod
    def verify_clean_room(cls):
        """
        🔬 Verify clean room state - no data files should exist
        验证净室状态 - 所有数据文件应不存在

        Returns:
            (is_clean, list_of_existing_files)
        """
        existing_files = []

        all_files = {}
        all_files.update(cls.get_all_state_files())
        all_files.update(cls.get_all_database_files())
        all_files.update(cls.get_all_vector_files())
        all_files.update(cls.get_all_kg_cache_files())

        for name, path in all_files.items():
            if path.exists():
                existing_files.append(str(path))

        for db_path in cls.get_all_database_files().values():
            for suffix in ['-wal', '-shm', '-journal']:
                journal_path = Path(str(db_path) + suffix)
                if journal_path.exists():
                    existing_files.append(str(journal_path))

        return len(existing_files) == 0, existing_files

    @classmethod
    def clear_embedding_cache(cls) -> bool:
        """
        🔥 Clear embedding cache - should be called when FAISS index is reset
        清除 embedding 缓存 - 当 FAISS 索引重置时应调用

        This ensures consistency between FAISS index and embedding cache.
        """
        try:
            if cls.EMBEDDING_CACHE_FILE.exists():
                cls.EMBEDDING_CACHE_FILE.unlink()
                return True
            return False
        except Exception as e:
            logger.warning(f"Failed to clear embedding cache: {e}")
            return False


# Import logger for methods
logger = logging.getLogger(__name__)


class ExperimentConfigSnapshot:
    """
    实验配置快照 - 用于实验可复现性
    Experiment Configuration Snapshot - for reproducibility

    保存完整的实验配置，包括：
    - 模型配置 (model, temperature, max_tokens)
    - 随机种子
    - 数据文件哈希
    - 系统版本
    """

    @classmethod
    def capture(cls, config: dict = None) -> dict:
        """
        捕获当前实验配置快照
        Capture current experiment configuration snapshot

        Args:
            config: Optional additional config to include

        Returns:
            Complete configuration snapshot dict
        """
        import os
        import sys
        from datetime import datetime

        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'python_version': sys.version,
            'bmam_root': str(BMAMPaths.BMAM_ROOT),

            # Environment configuration
            'environment': {
                'OPENAI_API_KEY': '***' if os.getenv('OPENAI_API_KEY') else None,
                'DEFAULT_MODEL': os.getenv('DEFAULT_MODEL', 'gpt-4o-mini'),
                'EMBEDDING_MODEL': os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small'),
                'TEMPERATURE': float(os.getenv('TEMPERATURE', '0.7')),
                'MAX_TOKENS': int(os.getenv('MAX_TOKENS', '1500')),
                'LLM_CALL_TIMEOUT': float(os.getenv('LLM_CALL_TIMEOUT', '30.0')),
            },

            # Data state
            'data_snapshot': BMAMPaths.compute_data_snapshot(),

            # Additional config
            'custom_config': config or {},
        }

        return snapshot

    @classmethod
    def save(cls, filepath: Path = None, config: dict = None) -> Path:
        """
        保存实验配置快照到文件
        Save experiment configuration snapshot to file

        Args:
            filepath: Output file path (default: BMAM/data/experiment_config.json)
            config: Optional additional config to include

        Returns:
            Path to saved config file
        """
        import json
        from datetime import datetime

        snapshot = cls.capture(config)

        if filepath is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = BMAMPaths.DATA_DIR / f'experiment_config_{timestamp}.json'

        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"📸 Experiment config saved to: {filepath}")
        return filepath

    @classmethod
    def compare(cls, snapshot1: dict, snapshot2: dict) -> dict:
        """
        比较两个实验配置快照的差异
        Compare differences between two experiment snapshots

        Returns:
            Dict with differences
        """
        differences = {
            'environment_changes': {},
            'data_changes': {},
            'config_changes': {}
        }

        # Compare environment
        env1 = snapshot1.get('environment', {})
        env2 = snapshot2.get('environment', {})
        for key in set(list(env1.keys()) + list(env2.keys())):
            if env1.get(key) != env2.get(key):
                differences['environment_changes'][key] = {
                    'before': env1.get(key),
                    'after': env2.get(key)
                }

        # Compare data files
        files1 = snapshot1.get('data_snapshot', {}).get('files', {})
        files2 = snapshot2.get('data_snapshot', {}).get('files', {})
        for key in set(list(files1.keys()) + list(files2.keys())):
            f1 = files1.get(key, {})
            f2 = files2.get(key, {})
            if f1.get('hash') != f2.get('hash') or f1.get('exists') != f2.get('exists'):
                differences['data_changes'][key] = {
                    'before': f1,
                    'after': f2
                }

        return differences

    @classmethod
    def print_summary(cls, snapshot: dict = None):
        """
        打印配置快照摘要
        Print configuration snapshot summary
        """
        if snapshot is None:
            snapshot = cls.capture()

        print("\n" + "="*60)
        print("  🔬 Experiment Configuration Snapshot")
        print("="*60)

        print(f"\n📅 Timestamp: {snapshot['timestamp']}")
        print(f"📂 BMAM Root: {snapshot['bmam_root']}")

        print("\n--- Environment ---")
        env = snapshot.get('environment', {})
        print(f"  Model: {env.get('DEFAULT_MODEL')}")
        print(f"  Embedding: {env.get('EMBEDDING_MODEL')}")
        print(f"  Temperature: {env.get('TEMPERATURE')}")
        print(f"  Max Tokens: {env.get('MAX_TOKENS')}")

        print("\n--- Data State ---")
        data = snapshot.get('data_snapshot', {})
        print(f"  Total Size: {data.get('total_size_bytes', 0) / 1024:.1f} KB")
        print(f"  Clean Room: {'✅ Yes' if data.get('clean_room') else '❌ No'}")

        files = data.get('files', {})
        for name, info in files.items():
            if info.get('exists'):
                print(f"  {name}: {info.get('hash', 'N/A')[:8]}...")

        print("="*60 + "\n")


# Singleton instance
paths = BMAMPaths()

# Ensure directories exist on module import
paths.ensure_directories()


# Convenience exports
__all__ = [
    'BMAMPaths',
    'paths',
    'ExperimentConfigSnapshot',
]
