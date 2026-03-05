"""
🔬 Experiment Configuration for Reproducibility
实验配置模块 - 用于消融实验和对比实验的可复现性

Records all critical settings for ablation/comparison experiments:
- Random seeds
- Model versions
- Cache settings
- HRM/Feedback loop parameters
- Thresholds
"""

import os
import json
import random
import hashlib
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
from pathlib import Path

# Import paths for data snapshot
try:
    from .paths import BMAMPaths
except ImportError:
    BMAMPaths = None

from src.core.constants import DEFAULT_LLM_MODEL, DEFAULT_EMBEDDING_MODEL


@dataclass
class ExperimentConfig:
    """
    Comprehensive experiment configuration for reproducibility
    完整的实验配置，用于可复现性
    """
    # === Identification ===
    experiment_id: str = ""
    experiment_name: str = ""
    timestamp: str = ""
    framework_version: str = "2.0.0"

    # === Random Seeds ===
    random_seed: int = 42
    numpy_seed: int = 42

    # === LLM Configuration ===
    llm_model: str = DEFAULT_LLM_MODEL
    llm_temperature: float = 0.7
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    embedding_dimension: int = 1536

    # === Cache Settings ===
    llm_cache_enabled: bool = True
    llm_cache_ttl: int = 3600  # seconds
    retrieval_cache_enabled: bool = True
    retrieval_cache_ttl: int = 300  # seconds
    embedding_cache_enabled: bool = True

    # === HRM (Hierarchical Retention Mechanism) ===
    hrm_enabled: bool = True
    hrm_max_iterations: int = 8
    act_base_threshold: float = 0.3
    act_min_retrieval_count: int = 5

    # === Feedback Loop ===
    feedback_loop_enabled: bool = True
    consolidation_threshold: float = 0.5

    # === Routing ===
    spacy_enabled: bool = False  # Disabled to prevent KG pollution
    kg_extraction_enabled: bool = True

    # === Memory Thresholds ===
    similarity_threshold: float = 0.25
    top_k_retrieval: int = 10

    # === Test Configuration ===
    test_mode: str = ""  # small, medium, full, longcontext, truncated, etc.
    sample_id: int = 0
    num_questions: int = 0

    # === Data Snapshot ===
    data_hash: str = ""  # Hash of input data for verification
    clean_room_verified: bool = False

    def __post_init__(self):
        if not self.experiment_id:
            self.experiment_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    @classmethod
    def from_environment(cls, test_mode: str = "", experiment_name: str = "") -> "ExperimentConfig":
        """
        Create config by reading from environment and current system state
        从环境变量和当前系统状态创建配置
        """
        config = cls(
            experiment_name=experiment_name or f"experiment_{test_mode}" if test_mode else "experiment",
            test_mode=test_mode,

            # LLM settings from environment
            llm_model=os.getenv("OPENAI_MODEL", DEFAULT_LLM_MODEL),
            llm_temperature=float(os.getenv("TEMPERATURE", "0.7")),
            embedding_model=os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),

            # Random seed
            random_seed=int(os.getenv("RANDOM_SEED", "42")),

            # Cache settings (check environment flags)
            llm_cache_enabled=os.getenv("LLM_CACHE_ENABLED", "true").lower() == "true",
            retrieval_cache_enabled=os.getenv("RETRIEVAL_CACHE_ENABLED", "true").lower() == "true",
            embedding_cache_enabled=os.getenv("EMBEDDING_CACHE_ENABLED", "true").lower() == "true",

            # HRM settings
            hrm_enabled=os.getenv("HRM_ENABLED", "true").lower() == "true",
            hrm_max_iterations=int(os.getenv("HRM_MAX_ITERATIONS", "8")),

            # Feedback loop
            feedback_loop_enabled=os.getenv("FEEDBACK_LOOP_ENABLED", "true").lower() == "true",

            # spaCy (should be disabled)
            spacy_enabled=os.getenv("SPACY_ENABLED", "false").lower() == "true",
        )

        # Apply random seed
        config.apply_seeds()

        return config

    def apply_seeds(self):
        """Apply random seeds for reproducibility"""
        random.seed(self.random_seed)
        try:
            import numpy as np
            np.random.seed(self.numpy_seed)
        except ImportError:
            pass

    def compute_data_hash(self, data: Any) -> str:
        """Compute hash of input data for verification"""
        data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        self.data_hash = hashlib.md5(data_str.encode()).hexdigest()[:16]
        return self.data_hash

    def capture_data_snapshot(self) -> Dict[str, Any]:
        """
        🔬 Capture data snapshot for reproducibility
        捕获数据快照用于可复现性验证
        """
        if BMAMPaths:
            return BMAMPaths.compute_data_snapshot()
        return {'error': 'BMAMPaths not available'}

    def verify_clean_room_state(self) -> bool:
        """
        🔬 Verify clean room state before experiment
        验证实验前的净室状态
        """
        if BMAMPaths:
            is_clean, existing_files = BMAMPaths.verify_clean_room()
            self.clean_room_verified = is_clean
            return is_clean
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    def save(self, filepath: str):
        """Save config to file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, filepath: str) -> "ExperimentConfig":
        """Load config from file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(**data)


@dataclass
class HRMMetadata:
    """
    HRM/Feedback Loop execution metadata
    HRM/反馈闭环执行元数据
    """
    # === HRM Iterations ===
    total_hrm_iterations: int = 0
    avg_iterations_per_query: float = 0.0
    max_iterations_reached: int = 0  # Number of times max iterations hit

    # === ACT (Adaptive Computation Time) ===
    act_decisions: List[Dict[str, Any]] = field(default_factory=list)
    avg_confidence_at_exit: float = 0.0

    # === Consolidation ===
    consolidation_signals_generated: int = 0
    consolidation_completed: int = 0
    consolidation_pending: int = 0

    # === Quality Feedback ===
    low_quality_detections: int = 0
    retry_attempts: int = 0

    # === Memory Operations ===
    total_memories_stored: int = 0
    total_memories_retrieved: int = 0
    kg_extractions: int = 0
    kg_pollution_blocked: int = 0  # Times spaCy was blocked

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def update_from_response(self, response: Dict[str, Any]):
        """Update metadata from a query response"""
        if 'hrm_metadata' in response:
            hrm = response['hrm_metadata']
            self.total_hrm_iterations += hrm.get('iterations', 0)
            if hrm.get('iterations', 0) >= 8:
                self.max_iterations_reached += 1

            if 'act_decision' in hrm:
                self.act_decisions.append(hrm['act_decision'])

        if 'consolidation_triggered' in response:
            self.consolidation_signals_generated += 1

        if 'memories_retrieved' in response:
            self.total_memories_retrieved += response['memories_retrieved']


class ExperimentResultWriter:
    """
    Writes experiment results with full config and metadata
    写入包含完整配置和元数据的实验结果
    """

    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.hrm_metadata = HRMMetadata()
        self.results: List[Dict[str, Any]] = []
        self.start_time = datetime.now()

    def add_result(self, result: Dict[str, Any]):
        """Add a single result"""
        self.results.append(result)
        # Update HRM metadata if available
        self.hrm_metadata.update_from_response(result)

    def finalize(self, output_path: str) -> Dict[str, Any]:
        """
        Finalize and write results with full metadata
        完成并写入包含完整元数据的结果
        """
        end_time = datetime.now()
        elapsed = (end_time - self.start_time).total_seconds()

        # Calculate HRM averages
        if self.results:
            self.hrm_metadata.avg_iterations_per_query = (
                self.hrm_metadata.total_hrm_iterations / len(self.results)
            )
            if self.hrm_metadata.act_decisions:
                confidences = [d.get('confidence', 0) for d in self.hrm_metadata.act_decisions]
                self.hrm_metadata.avg_confidence_at_exit = sum(confidences) / len(confidences)

        final_output = {
            # === Experiment Config (for reproducibility) ===
            'experiment_config': self.config.to_dict(),

            # === HRM/Feedback Loop Metadata ===
            'hrm_metadata': self.hrm_metadata.to_dict(),

            # === Timing ===
            'timing': {
                'start_time': self.start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'elapsed_seconds': round(elapsed, 2),
                'elapsed_minutes': round(elapsed / 60, 2),
            },

            # === Results ===
            'results': self.results,

            # === Summary Statistics ===
            'summary': self._compute_summary(),
        }

        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)

        return final_output

    def _compute_summary(self) -> Dict[str, Any]:
        """Compute summary statistics"""
        if not self.results:
            return {'total': 0, 'correct': 0, 'accuracy': 0.0}

        correct = sum(1 for r in self.results if r.get('correct', False) or r.get('score', 0) >= 0.7)
        total_score = sum(r.get('score', 0) for r in self.results)

        return {
            'total_questions': len(self.results),
            'correct_count': correct,
            'accuracy': round(correct / len(self.results), 4),
            'avg_score': round(total_score / len(self.results), 4),
            'total_score': round(total_score, 2),
        }


# === Cache Toggle Functions ===

def set_cache_enabled(
    llm_cache: Optional[bool] = None,
    retrieval_cache: Optional[bool] = None,
    embedding_cache: Optional[bool] = None
):
    """
    Set cache enabled/disabled via environment variables
    通过环境变量设置缓存启用/禁用

    Usage:
        set_cache_enabled(llm_cache=False)  # Disable LLM cache for ablation
        set_cache_enabled(llm_cache=True, retrieval_cache=True)  # Enable both
    """
    if llm_cache is not None:
        os.environ["LLM_CACHE_ENABLED"] = str(llm_cache).lower()
    if retrieval_cache is not None:
        os.environ["RETRIEVAL_CACHE_ENABLED"] = str(retrieval_cache).lower()
    if embedding_cache is not None:
        os.environ["EMBEDDING_CACHE_ENABLED"] = str(embedding_cache).lower()


def set_hrm_enabled(enabled: bool = True, max_iterations: int = 8):
    """
    Set HRM enabled/disabled via environment variables
    通过环境变量设置 HRM 启用/禁用
    """
    os.environ["HRM_ENABLED"] = str(enabled).lower()
    os.environ["HRM_MAX_ITERATIONS"] = str(max_iterations)


def set_feedback_loop_enabled(enabled: bool = True):
    """
    Set feedback loop enabled/disabled via environment variables
    通过环境变量设置反馈闭环启用/禁用
    """
    os.environ["FEEDBACK_LOOP_ENABLED"] = str(enabled).lower()


# Convenience exports
__all__ = [
    'ExperimentConfig',
    'HRMMetadata',
    'ExperimentResultWriter',
    'set_cache_enabled',
    'set_hrm_enabled',
    'set_feedback_loop_enabled',
]
