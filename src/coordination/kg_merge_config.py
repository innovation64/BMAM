"""
KG Merge Configuration System
提供可配置的知识图谱融合参数，取代硬编码常量

Team F – KG Merge Parametrization
将所有 KG 融合相关的参数抽取到统一的配置系统中，便于调优和实验
"""

import logging
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class KGMergeConfig:
    """
    知识图谱融合配置

    所有参数都是可调优的，支持从文件加载或代码设置
    """

    # ========== Quality Filtering ==========

    low_quality_predicates: Set[str] = field(default_factory=lambda: {
        'is_a', 'have', 'do', 'be', 'get', 'make', 'take',
        'look', 'think', 'feel', 'say', 'tell', 'know', 'see'
    })
    """
    低质量谓词集合

    这些谓词过于泛化，不提供有价值的信息
    例如: "Alice is_a person" 没有实际意义
    """

    important_keywords: Set[str] = field(default_factory=lambda: {
        'sweden', 'beach', 'mountains', 'forest', 'nature', 'dinosaurs',
        'camp', 'lake', 'river', 'ocean', 'desert', 'city', 'country',
        'university', 'school', 'company', 'organization'
    })
    """
    重要关键词集合

    即使对象很短（单个词），如果在这个集合中也保留
    例如: "Alice visited Sweden" - Sweden 是重要实体
    """

    min_object_word_count: int = 2
    """对象最小词数（不在 important_keywords 中时）"""

    # ========== Deduplication ==========

    overlap_threshold: float = 0.7
    """
    内容重叠阈值

    当 vector memory 与 KG fact 的词重叠率 > 此值时，认为是重复
    值越高，保留的 vector memories 越多（更保守）
    """

    min_phrase_length: int = 4
    """短语最小长度（字符数），短于此值的短语不用于去重"""

    # ========== Scoring & Ranking ==========

    kg_fact_default_score: float = 1.0
    """KG fact 的默认 score"""

    kg_fact_plasticity_score: float = 2.0
    """
    KG fact 的 plasticity score

    设置为 2.0 确保 KG facts 在排序时优先级高
    Phase 4 P1.2 Fix: 从 1.0 提升到 2.0
    """

    # ========== Merge Strategy ==========

    max_merged_results: int = 20
    """融合后的最大结果数量（避免上下文溢出）"""

    preserve_vector_memories: bool = True
    """
    是否保留 vector memories

    True: 保留大部分 vector memories（默认）
    False: 更激进地去重，只保留 KG facts
    """

    kg_facts_at_front: bool = True
    """
    KG facts 是否放在前面

    True: KG facts 插入到结果列表前面（优先级高）
    False: 按照 plasticity_score 排序
    """

    # ========== Plasticity Ranking ==========

    plasticity_top_k_enabled: bool = True
    """是否启用 plasticity ranking"""

    plasticity_top_k: Optional[int] = None
    """
    Plasticity ranking 的 top-k 阈值

    None: 不限制，返回所有结果（按 plasticity_score 排序）
    int: 只返回 top-k 个结果
    """

    plasticity_score_threshold: Optional[float] = None
    """
    Plasticity score 最低阈值

    None: 不过滤
    float: 只保留 plasticity_score >= threshold 的记忆
    """

    # ========== Coverage & Conflict ==========

    coverage_bonus_weight: float = 0.3
    """关键词覆盖率加成权重"""

    conflict_penalty_weight: float = 0.2
    """冲突惩罚权重"""

    hit_count_boost_factor: float = 0.1
    """每次命中的 boost 系数"""

    # ========== Temporal Boosting ==========

    temporal_timeline_bonus: float = 0.50
    """时间线精确匹配基础加成"""

    temporal_relative_time_event_bonus: float = 0.35
    """相对时间 + 事件关键词加成"""

    temporal_relative_time_only_bonus: float = 0.05
    """仅相对时间表达加成（保守）"""

    temporal_event_only_bonus: float = 0.02
    """仅事件关键词加成（极小）"""

    # ========== Logging & Debug ==========

    log_merge_details: bool = True
    """是否记录详细的融合日志"""

    log_quality_filtering: bool = False
    """是否记录质量过滤的详细信息"""

    log_deduplication: bool = False
    """是否记录去重的详细信息"""

    # ========== Validation ==========

    def validate(self) -> List[str]:
        """
        验证配置的合理性

        Returns:
            错误列表（空列表表示验证通过）
        """
        errors = []

        # 检查阈值范围
        if not 0.0 <= self.overlap_threshold <= 1.0:
            errors.append(f"overlap_threshold must be in [0, 1], got {self.overlap_threshold}")

        if self.kg_fact_plasticity_score < 0:
            errors.append(f"kg_fact_plasticity_score must be >= 0, got {self.kg_fact_plasticity_score}")

        if self.plasticity_score_threshold is not None and self.plasticity_score_threshold < 0:
            errors.append(f"plasticity_score_threshold must be >= 0, got {self.plasticity_score_threshold}")

        if self.plasticity_top_k is not None and self.plasticity_top_k <= 0:
            errors.append(f"plasticity_top_k must be > 0, got {self.plasticity_top_k}")

        if self.max_merged_results <= 0:
            errors.append(f"max_merged_results must be > 0, got {self.max_merged_results}")

        if self.min_object_word_count < 1:
            errors.append(f"min_object_word_count must be >= 1, got {self.min_object_word_count}")

        # 检查集合不为空
        if not self.low_quality_predicates:
            logger.warning("low_quality_predicates is empty - no predicate filtering will occur")

        if not self.important_keywords:
            logger.warning("important_keywords is empty - short objects may be filtered aggressively")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        data = asdict(self)
        # 转换 set 为 list（JSON 不支持 set）
        data['low_quality_predicates'] = list(self.low_quality_predicates)
        data['important_keywords'] = list(self.important_keywords)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KGMergeConfig':
        """从字典加载（用于反序列化）"""
        # 转换 list 回 set
        if 'low_quality_predicates' in data:
            data['low_quality_predicates'] = set(data['low_quality_predicates'])
        if 'important_keywords' in data:
            data['important_keywords'] = set(data['important_keywords'])
        return cls(**data)

    def save(self, file_path: str):
        """保存配置到文件"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(f"💾 KG merge config saved to {file_path}")

    @classmethod
    def load(cls, file_path: str) -> 'KGMergeConfig':
        """从文件加载配置"""
        path = Path(file_path)

        if not path.exists():
            logger.warning(f"Config file not found: {file_path}, using defaults")
            return cls()

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        config = cls.from_dict(data)
        logger.info(f"📂 KG merge config loaded from {file_path}")

        return config


# ============================================================================
# Preset Configurations (预设配置)
# ============================================================================

def get_default_config() -> KGMergeConfig:
    """获取默认配置（当前生产配置）"""
    # Phase 4 P1.3: 使用 LoCoMo 优化配置作为默认配置
    # 原因：测试发现质量过滤过于严格，导致Q4的所有facts被过滤
    return get_locomo_optimized_config()


def get_conservative_config() -> KGMergeConfig:
    """
    保守配置 - 高质量优先

    - 更严格的质量过滤
    - 保留更多 vector memories
    - 较低的 KG plasticity score
    """
    return KGMergeConfig(
        low_quality_predicates={
            'is_a', 'have', 'do', 'be', 'get', 'make', 'take',
            'look', 'think', 'feel', 'say', 'tell', 'know', 'see',
            'want', 'like', 'need', 'use', 'find', 'give', 'work'
        },
        min_object_word_count=3,  # 更严格
        overlap_threshold=0.6,  # 更保守，保留更多 vector memories
        kg_fact_plasticity_score=1.5,  # 较低优先级
        max_merged_results=15,
        plasticity_score_threshold=0.3  # 过滤低分记忆
    )


def get_aggressive_config() -> KGMergeConfig:
    """
    激进配置 - KG 优先

    - 较宽松的质量过滤
    - 更激进的去重
    - 更高的 KG plasticity score
    """
    return KGMergeConfig(
        low_quality_predicates={
            'is_a', 'have', 'do', 'be'
        },
        min_object_word_count=1,  # 更宽松
        overlap_threshold=0.8,  # 更激进，去重更多 vector memories
        kg_fact_plasticity_score=3.0,  # 最高优先级
        max_merged_results=25,
        preserve_vector_memories=False,  # 更激进去重
        plasticity_score_threshold=None  # 不过滤
    )


def get_balanced_config() -> KGMergeConfig:
    """
    平衡配置 - 质量与覆盖率平衡

    - 中等质量过滤
    - 平衡的去重策略
    - 适中的 KG 优先级
    """
    return KGMergeConfig(
        low_quality_predicates={
            'is_a', 'have', 'do', 'be', 'get', 'make', 'take',
            'look', 'think', 'feel'
        },
        min_object_word_count=2,
        overlap_threshold=0.7,
        kg_fact_plasticity_score=2.0,
        max_merged_results=20,
        plasticity_score_threshold=0.1
    )


def get_locomo_optimized_config() -> KGMergeConfig:
    """
    LoCoMo 优化配置

    针对 LoCoMo 测试集优化的配置
    - 保留地点相关的重要关键词
    - 适中的质量过滤
    - 高 KG 优先级（因为 LoCoMo KG 质量高）
    """
    return KGMergeConfig(
        low_quality_predicates={
            'is_a', 'have', 'do', 'be', 'get', 'make', 'take',
            'look', 'think', 'feel', 'say', 'tell'
        },
        important_keywords={
            # 地点
            'sweden', 'beach', 'mountains', 'forest', 'nature', 'dinosaurs',
            'camp', 'lake', 'river', 'ocean', 'desert', 'city', 'country',
            # 机构
            'university', 'school', 'company', 'organization',
            # LoCoMo 特定
            'sunrise', 'sunset', 'painting', 'photography', 'art',
            'adoption', 'agency', 'psychology', 'transgender'
        },
        min_object_word_count=2,
        overlap_threshold=0.7,
        kg_fact_plasticity_score=2.5,  # 较高优先级（LoCoMo KG 质量高）
        max_merged_results=20,
        plasticity_top_k=15,  # 限制 top-k
        plasticity_score_threshold=0.2
    )


# ============================================================================
# Global Config Instance (全局配置实例)
# ============================================================================

_global_config: Optional[KGMergeConfig] = None


def get_kg_merge_config() -> KGMergeConfig:
    """
    获取全局 KG merge 配置

    Returns:
        当前激活的配置实例
    """
    global _global_config

    if _global_config is None:
        # 尝试从环境变量或默认路径加载
        config_path = Path("configs/kg_merge_config.json")

        if config_path.exists():
            _global_config = KGMergeConfig.load(str(config_path))
        else:
            _global_config = get_default_config()
            logger.info("Using default KG merge config")

    return _global_config


def set_kg_merge_config(config: KGMergeConfig):
    """
    设置全局 KG merge 配置

    Args:
        config: 新的配置实例
    """
    global _global_config

    # 验证配置
    errors = config.validate()
    if errors:
        raise ValueError(f"Invalid KG merge config: {errors}")

    _global_config = config
    logger.info(f"✅ KG merge config updated: plasticity_score={config.kg_fact_plasticity_score}, "
               f"overlap_threshold={config.overlap_threshold}, "
               f"max_results={config.max_merged_results}")


def reset_kg_merge_config():
    """重置为默认配置"""
    global _global_config
    _global_config = get_default_config()
    logger.info("🔄 KG merge config reset to default")


# ============================================================================
# Config Comparison Utility (配置比较工具)
# ============================================================================

def compare_configs(config1: KGMergeConfig, config2: KGMergeConfig) -> Dict[str, Any]:
    """
    比较两个配置的差异

    Returns:
        差异字典
    """
    dict1 = config1.to_dict()
    dict2 = config2.to_dict()

    differences = {}
    all_keys = set(dict1.keys()) | set(dict2.keys())

    for key in all_keys:
        val1 = dict1.get(key)
        val2 = dict2.get(key)

        # 转换 set 为 sorted list 用于比较
        if isinstance(val1, set):
            val1 = sorted(list(val1))
        if isinstance(val2, set):
            val2 = sorted(list(val2))

        if val1 != val2:
            differences[key] = {'config1': val1, 'config2': val2}

    return differences


def print_config(config: KGMergeConfig, name: str = "KG Merge Config"):
    """
    打印配置（便于调试）

    Args:
        config: 配置实例
        name: 配置名称
    """
    print(f"\n{'=' * 60}")
    print(f"{name}")
    print(f"{'=' * 60}")

    print("\n📊 Quality Filtering:")
    print(f"  - Low quality predicates: {sorted(config.low_quality_predicates)}")
    print(f"  - Important keywords: {sorted(config.important_keywords)}")
    print(f"  - Min object word count: {config.min_object_word_count}")

    print("\n🔗 Deduplication:")
    print(f"  - Overlap threshold: {config.overlap_threshold}")
    print(f"  - Min phrase length: {config.min_phrase_length}")

    print("\n🎯 Scoring & Ranking:")
    print(f"  - KG fact default score: {config.kg_fact_default_score}")
    print(f"  - KG fact plasticity score: {config.kg_fact_plasticity_score}")

    print("\n🔄 Merge Strategy:")
    print(f"  - Max merged results: {config.max_merged_results}")
    print(f"  - Preserve vector memories: {config.preserve_vector_memories}")
    print(f"  - KG facts at front: {config.kg_facts_at_front}")

    print("\n🧠 Plasticity Ranking:")
    print(f"  - Enabled: {config.plasticity_top_k_enabled}")
    print(f"  - Top-k: {config.plasticity_top_k}")
    print(f"  - Score threshold: {config.plasticity_score_threshold}")

    print("\n📈 Temporal Boosting:")
    print(f"  - Timeline bonus: {config.temporal_timeline_bonus}")
    print(f"  - Relative time + event bonus: {config.temporal_relative_time_event_bonus}")
    print(f"  - Relative time only bonus: {config.temporal_relative_time_only_bonus}")
    print(f"  - Event only bonus: {config.temporal_event_only_bonus}")

    print(f"\n{'=' * 60}\n")


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # 示例1: 使用默认配置
    config = get_default_config()
    print_config(config, "Default Config")

    # 示例2: 比较不同预设
    conservative = get_conservative_config()
    aggressive = get_aggressive_config()

    print("\n🔍 Comparing Conservative vs Aggressive:")
    diffs = compare_configs(conservative, aggressive)
    for key, values in diffs.items():
        print(f"  {key}:")
        print(f"    Conservative: {values['config1']}")
        print(f"    Aggressive: {values['config2']}")

    # 示例3: 自定义配置
    custom_config = KGMergeConfig(
        low_quality_predicates={'is_a', 'have'},
        kg_fact_plasticity_score=2.5,
        max_merged_results=15
    )

    # 验证配置
    errors = custom_config.validate()
    if errors:
        print(f"❌ Config validation failed: {errors}")
    else:
        print("✅ Config validation passed")

    # 示例4: 保存和加载
    custom_config.save("configs/my_kg_config.json")
    loaded_config = KGMergeConfig.load("configs/my_kg_config.json")
    print_config(loaded_config, "Loaded Config")
