#!/usr/bin/env python3
"""
BMAM 消融实验配置

支持禁用以下组件来测试各组件贡献:
1. 脑区级别消融:
   - Hippocampus (情景记忆编码)
   - Temporal Lobe (语义记忆巩固 + KG)
   - Amygdala (显著性标记)
   - Prefrontal (工作记忆 + 路由控制)
   - Basal Ganglia (程序性记忆 + 模式检测)

2. 功能模块消融:
   - StoryArc (时间线索引)
   - Temporal Reasoning (时间推理)
   - Hybrid Retrieval (混合检索)
   - Memory Consolidation (记忆巩固)
   - HRM (层次记忆管理)

Usage:
    from src.config.ablation_config import AblationConfig, get_ablation_config

    # 获取预定义配置
    config = get_ablation_config('no_hippocampus')

    # 创建自定义配置
    config = AblationConfig(
        name='custom',
        enable_hippocampus=True,
        enable_temporal_lobe=False,
        ...
    )
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class AblationConfig:
    """消融实验配置"""

    name: str = 'full'
    description: str = '完整系统'

    # 脑区开关
    enable_hippocampus: bool = True      # 情景记忆
    enable_temporal_lobe: bool = True    # 语义记忆 + KG
    enable_amygdala: bool = True         # 显著性标记
    enable_prefrontal: bool = True       # 工作记忆控制
    enable_basal_ganglia: bool = True    # 程序性记忆

    # 功能模块开关
    enable_story_arc: bool = True        # 时间线索引
    enable_temporal_reasoning: bool = True  # 时间推理
    enable_kg: bool = True               # 知识图谱
    enable_hybrid_retrieval: bool = True  # 混合检索
    enable_consolidation: bool = True    # 记忆巩固
    enable_hrm: bool = True              # 层次记忆管理
    enable_salience: bool = True         # 显著性加权

    def to_env_vars(self) -> Dict[str, str]:
        """转换为环境变量"""
        return {
            'BMAM_ABLATION_NAME': self.name,
            'BMAM_DISABLE_HIPPOCAMPUS': str(not self.enable_hippocampus).lower(),
            'BMAM_DISABLE_TEMPORAL_LOBE': str(not self.enable_temporal_lobe).lower(),
            'BMAM_DISABLE_AMYGDALA': str(not self.enable_amygdala).lower(),
            'BMAM_DISABLE_PREFRONTAL': str(not self.enable_prefrontal).lower(),
            'BMAM_DISABLE_BASAL_GANGLIA': str(not self.enable_basal_ganglia).lower(),
            'BMAM_DISABLE_STORY_ARC': str(not self.enable_story_arc).lower(),
            'BMAM_DISABLE_TEMPORAL_REASONING': str(not self.enable_temporal_reasoning).lower(),
            'BMAM_DISABLE_KG': str(not self.enable_kg).lower(),
            'BMAM_DISABLE_HYBRID_RETRIEVAL': str(not self.enable_hybrid_retrieval).lower(),
            'BMAM_DISABLE_CONSOLIDATION': str(not self.enable_consolidation).lower(),
            'BMAM_DISABLE_HRM': str(not self.enable_hrm).lower(),
            'BMAM_DISABLE_SALIENCE': str(not self.enable_salience).lower(),
        }

    def apply_to_env(self):
        """应用配置到环境变量"""
        for key, value in self.to_env_vars().items():
            os.environ[key] = value

    @classmethod
    def from_env(cls) -> 'AblationConfig':
        """从环境变量读取配置"""
        def is_disabled(key: str) -> bool:
            return os.getenv(key, 'false').lower() == 'true'

        return cls(
            name=os.getenv('BMAM_ABLATION_NAME', 'full'),
            enable_hippocampus=not is_disabled('BMAM_DISABLE_HIPPOCAMPUS'),
            enable_temporal_lobe=not is_disabled('BMAM_DISABLE_TEMPORAL_LOBE'),
            enable_amygdala=not is_disabled('BMAM_DISABLE_AMYGDALA'),
            enable_prefrontal=not is_disabled('BMAM_DISABLE_PREFRONTAL'),
            enable_basal_ganglia=not is_disabled('BMAM_DISABLE_BASAL_GANGLIA'),
            enable_story_arc=not is_disabled('BMAM_DISABLE_STORY_ARC'),
            enable_temporal_reasoning=not is_disabled('BMAM_DISABLE_TEMPORAL_REASONING'),
            enable_kg=not is_disabled('BMAM_DISABLE_KG'),
            enable_hybrid_retrieval=not is_disabled('BMAM_DISABLE_HYBRID_RETRIEVAL'),
            enable_consolidation=not is_disabled('BMAM_DISABLE_CONSOLIDATION'),
            enable_hrm=not is_disabled('BMAM_DISABLE_HRM'),
            enable_salience=not is_disabled('BMAM_DISABLE_SALIENCE'),
        )


# 预定义消融配置
ABLATION_PRESETS: Dict[str, AblationConfig] = {
    # 完整系统
    'full': AblationConfig(
        name='full',
        description='完整 BMAM 系统'
    ),

    # === 脑区级别消融 ===
    'no_hippocampus': AblationConfig(
        name='no_hippocampus',
        description='禁用海马体 (情景记忆编码)',
        enable_hippocampus=False
    ),

    'no_temporal_lobe': AblationConfig(
        name='no_temporal_lobe',
        description='禁用颞叶 (语义记忆 + KG)',
        enable_temporal_lobe=False,
        enable_kg=False  # 颞叶负责KG巩固
    ),

    'no_amygdala': AblationConfig(
        name='no_amygdala',
        description='禁用杏仁核 (显著性标记)',
        enable_amygdala=False,
        enable_salience=False
    ),

    'no_prefrontal': AblationConfig(
        name='no_prefrontal',
        description='禁用前额叶 (工作记忆控制)',
        enable_prefrontal=False
    ),

    'no_basal_ganglia': AblationConfig(
        name='no_basal_ganglia',
        description='禁用基底神经节 (程序性记忆)',
        enable_basal_ganglia=False
    ),

    # === 功能模块消融 ===
    'no_story_arc': AblationConfig(
        name='no_story_arc',
        description='禁用 StoryArc 时间线索引',
        enable_story_arc=False
    ),

    'no_temporal_reasoning': AblationConfig(
        name='no_temporal_reasoning',
        description='禁用时间推理模块',
        enable_temporal_reasoning=False
    ),

    'no_kg': AblationConfig(
        name='no_kg',
        description='禁用知识图谱',
        enable_kg=False
    ),

    'no_hybrid_retrieval': AblationConfig(
        name='no_hybrid_retrieval',
        description='禁用混合检索 (仅用向量检索)',
        enable_hybrid_retrieval=False
    ),

    'no_consolidation': AblationConfig(
        name='no_consolidation',
        description='禁用记忆巩固',
        enable_consolidation=False
    ),

    'no_hrm': AblationConfig(
        name='no_hrm',
        description='禁用层次记忆管理',
        enable_hrm=False
    ),

    'no_salience': AblationConfig(
        name='no_salience',
        description='禁用显著性加权',
        enable_salience=False
    ),

    # === 极端消融 ===
    'hippocampus_only': AblationConfig(
        name='hippocampus_only',
        description='仅保留海马体基础记忆',
        enable_hippocampus=True,
        enable_temporal_lobe=False,
        enable_amygdala=False,
        enable_prefrontal=False,
        enable_basal_ganglia=False,
        enable_story_arc=False,
        enable_temporal_reasoning=False,
        enable_kg=False,
        enable_hybrid_retrieval=False,
        enable_consolidation=False,
        enable_hrm=False,
        enable_salience=False
    ),

    'vector_only': AblationConfig(
        name='vector_only',
        description='仅使用向量检索 (类RAG基线)',
        enable_hippocampus=True,
        enable_temporal_lobe=False,
        enable_amygdala=False,
        enable_prefrontal=False,
        enable_basal_ganglia=False,
        enable_story_arc=False,
        enable_temporal_reasoning=False,
        enable_kg=False,
        enable_hybrid_retrieval=False,
        enable_consolidation=False,
        enable_hrm=False,
        enable_salience=False
    ),
}


def get_ablation_config(name: str = 'full') -> AblationConfig:
    """获取预定义消融配置"""
    if name not in ABLATION_PRESETS:
        raise ValueError(f"Unknown ablation config: {name}. Available: {list(ABLATION_PRESETS.keys())}")
    return ABLATION_PRESETS[name]


def list_ablation_configs() -> Dict[str, str]:
    """列出所有预定义消融配置"""
    return {name: config.description for name, config in ABLATION_PRESETS.items()}


# 当前活跃的消融配置 (可通过 set_active_ablation 修改)
_active_ablation: Optional[AblationConfig] = None


def set_active_ablation(config: AblationConfig):
    """设置当前活跃的消融配置"""
    global _active_ablation
    _active_ablation = config
    config.apply_to_env()


def get_active_ablation() -> AblationConfig:
    """获取当前活跃的消融配置"""
    global _active_ablation
    if _active_ablation is None:
        _active_ablation = AblationConfig.from_env()
    return _active_ablation


def clear_ablation():
    """清除消融配置，恢复完整系统"""
    global _active_ablation
    _active_ablation = None
    # 清除环境变量
    import os
    for key in list(os.environ.keys()):
        if key.startswith('BMAM_DISABLE_') or key.startswith('BMAM_ENABLE_'):
            del os.environ[key]


def is_component_enabled(component: str) -> bool:
    """检查组件是否启用"""
    config = get_active_ablation()
    attr_name = f'enable_{component}'
    if hasattr(config, attr_name):
        return getattr(config, attr_name)
    # 也支持检查环境变量
    env_key = f'BMAM_DISABLE_{component.upper()}'
    return os.getenv(env_key, 'false').lower() != 'true'
