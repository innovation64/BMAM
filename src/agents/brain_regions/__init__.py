"""
Brain Region Agents - 脑区智能体模块

每个脑区智能体有自己的内部记忆存储和容量管理:
- HippocampusAgent: 情节记忆 (20,000条)
- TemporalLobeAgent: 语义记忆 + KG (70,000条)
- PrefrontalAgent: 工作记忆 (10条)
- AmygdalaAgent: 情绪记忆标记 (1,000条)
- BasalGangliaAgent: 程序记忆 (500条)
"""

from .hippocampus_agent import HippocampusAgent
from .temporal_lobe_agent import TemporalLobeAgent
from .prefrontal_agent import PrefrontalAgent
from .amygdala_agent import AmygdalaAgent
from .basal_ganglia_agent import BasalGangliaAgent

__all__ = [
    'HippocampusAgent',
    'TemporalLobeAgent',
    'PrefrontalAgent',
    'AmygdalaAgent',
    'BasalGangliaAgent'
]
