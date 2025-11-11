# 默认使用重构版coordinator (683行，原版7703行已废弃)
from .brain_coordinator_refactored import BrainInspiredCoordinator

from .clean_agent_system import BrainRegion, AgentMessage

__all__ = ['BrainInspiredCoordinator', 'AgentMessage', 'BrainRegion']
