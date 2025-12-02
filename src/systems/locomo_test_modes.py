"""
LOCOMO Test Modes - 4种记忆管理策略

设计目标：
- 证明BMAM是通用记忆框架，可以无缝替换传统的4种记忆管理方式
- 不仅适用于对话场景，也适用于任何需要记忆的下游任务：
  * 对话系统 (Conversation)
  * 文档问答 (Document QA)
  * 代码理解 (Code Understanding)
  * 知识库检索 (Knowledge Base Retrieval)
  * 学习辅助系统 (Learning Assistant)
  * 等等...

理论依据：
- Maharana et al. (2024) - LOCOMO Benchmark（对话场景baseline）
- 对比Long-context、Truncated、RAG、BMAM Full四种模式的性能
- 证明BMAM作为统一记忆后端的通用性
"""

from enum import Enum
from typing import Dict, List, Any, Optional


class LocomoTestMode(Enum):
    """
    4种通用记忆管理策略

    适用于任何需要记忆的下游任务（不限于对话）:
    - 对话系统、文档问答、代码理解、知识库、学习系统等
    """

    LONGCONTEXT = "longcontext"
    """
    模式1: Long-context（长文本一次性输入）
    - 数据存储：外部记录库存储全量
    - 检索策略：返回全部内容
    - BMAM角色：推理引擎（不使用内部5脑区记忆）
    - 适用场景：短期项目、论文摘要、会议纪要等
    - 对应论文：Long-context Models baseline
    """

    TRUNCATED = "truncated"
    """
    模式2: Truncated（固定窗口滑动）
    - 数据存储：外部记录库存储全量
    - 检索策略：只返回最近N条
    - BMAM角色：推理引擎（不使用内部5脑区记忆）
    - 适用场景：简单对话、实时任务、context受限场景
    - 对应论文：Base Models baseline
    """

    RAG = "rag"
    """
    模式3: RAG（简单检索增强）
    - 数据存储：外部向量库存储
    - 检索策略：单次语义向量检索top-k
    - BMAM角色：推理引擎（不使用内部5脑区记忆）
    - 适用场景：文档问答、知识库检索、FAQ系统
    - 对应论文：Standard RAG baseline
    """

    BMAM_FULL = "bmam_full"
    """
    模式4: BMAM Full（类脑记忆系统）
    - 数据存储：5脑区分布式记忆（Episodic/Semantic/Working/Emotional/Procedural）
    - 检索策略：HRM分层迭代检索 + 跨脑区协同
    - BMAM角色：完整系统（记忆塑造+整合+遗忘+检索+推理）
    - 适用场景：长期对话、个性化助手、终身学习系统、复杂推理任务
    - 这是BMAM作为通用记忆框架的完整能力展示
    """


class LocomoTestConfig:
    """LOCOMO测试配置"""

    def __init__(
        self,
        mode: LocomoTestMode,
        window_size: int = 20,
        retrieval_k: int = 10,
        enable_hrm: bool = True,
        enable_consolidation: bool = True
    ):
        """
        Args:
            mode: 测试模式
            window_size: 固定窗口大小（仅TRUNCATED模式）
            retrieval_k: 检索数量（RAG模式）
            enable_hrm: 是否启用HRM（BMAM_FULL模式）
            enable_consolidation: 是否启用记忆整合（BMAM_FULL模式）
        """
        self.mode = mode
        self.window_size = window_size
        self.retrieval_k = retrieval_k
        self.enable_hrm = enable_hrm
        self.enable_consolidation = enable_consolidation

    def should_use_external_memory(self) -> bool:
        """是否使用外部记录库（Mode 1-3使用）"""
        return self.mode in [
            LocomoTestMode.LONGCONTEXT,
            LocomoTestMode.TRUNCATED,
            LocomoTestMode.RAG
        ]

    def should_use_bmam_memory(self) -> bool:
        """是否使用BMAM 5脑区记忆（Mode 4使用）"""
        return self.mode == LocomoTestMode.BMAM_FULL

    def get_retrieval_strategy(self) -> str:
        """获取检索策略"""
        if self.mode == LocomoTestMode.LONGCONTEXT:
            return "full_history"
        elif self.mode == LocomoTestMode.TRUNCATED:
            return "recent_window"
        elif self.mode == LocomoTestMode.RAG:
            return "vector_search"
        elif self.mode == LocomoTestMode.BMAM_FULL:
            return "hrm_multi_region"
        else:
            return "unknown"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'mode': self.mode.value,
            'window_size': self.window_size,
            'retrieval_k': self.retrieval_k,
            'enable_hrm': self.enable_hrm,
            'enable_consolidation': self.enable_consolidation,
            'retrieval_strategy': self.get_retrieval_strategy()
        }

    @classmethod
    def from_mode(cls, mode: str, **kwargs) -> "LocomoTestConfig":
        """从模式字符串创建配置"""
        mode_enum = LocomoTestMode(mode)

        # 根据模式设置默认参数
        if mode_enum == LocomoTestMode.LONGCONTEXT:
            defaults = {'enable_hrm': False, 'enable_consolidation': False}
        elif mode_enum == LocomoTestMode.TRUNCATED:
            defaults = {'window_size': 20, 'enable_hrm': False, 'enable_consolidation': False}
        elif mode_enum == LocomoTestMode.RAG:
            defaults = {'retrieval_k': 10, 'enable_hrm': False, 'enable_consolidation': False}
        elif mode_enum == LocomoTestMode.BMAM_FULL:
            defaults = {'enable_hrm': True, 'enable_consolidation': True}
        else:
            defaults = {}

        # 合并用户提供的参数
        defaults.update(kwargs)

        return cls(mode=mode_enum, **defaults)


def get_mode_description(mode: LocomoTestMode) -> str:
    """获取模式的详细描述"""
    descriptions = {
        LocomoTestMode.LONGCONTEXT: (
            "Long-context模式：全量对话历史一次性输入，"
            "测试BMAM处理超长上下文的能力（模拟16K token上下文）"
        ),
        LocomoTestMode.TRUNCATED: (
            "Truncated模式：只使用最近N条对话，"
            "测试BMAM在信息缺失情况下的表现（模拟4K token窗口）"
        ),
        LocomoTestMode.RAG: (
            "RAG模式：使用外部向量库检索，"
            "测试BMAM作为标准RAG后端的能力"
        ),
        LocomoTestMode.BMAM_FULL: (
            "BMAM Full模式：5脑区分布式记忆 + HRM分层检索，"
            "展示BMAM完整的长期对话系统能力"
        )
    }
    return descriptions.get(mode, "Unknown mode")
