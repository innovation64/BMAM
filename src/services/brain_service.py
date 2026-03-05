"""
Brain Service - API Facade
脑系统服务层 - 实现前后端分离的 API 门面

功能:
1. 封装 BrainCoordinator 的复杂性
2. 提供标准化的数据接口 (DTOs)
3. 隔离 UI 层与 Brain 内部实现细节
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from ..coordination.brain_coordinator_refactored import BrainInspiredCoordinator

logger = logging.getLogger(__name__)

@dataclass
class SystemStatusDTO:
    """系统状态数据传输对象"""
    is_running: bool
    active_agents: int
    total_memories: int
    uptime_seconds: float
    current_task: str

@dataclass
class MemoryRegionStatsDTO:
    """脑区记忆统计数据传输对象"""
    id: str
    name: str
    capacity: int
    current_count: int
    usage_percentage: float
    total_stored: int
    total_evicted: int

@dataclass
class ProcessingResponseDTO:
    """处理结果数据传输对象"""
    response: str
    emotion: str
    active_regions: List[str]
    memories_retrieved: List[Dict[str, Any]]
    processing_time: float

class BrainService:
    """
    Brain Service
    
    The single point of contact for any UI or external interface.
    """

    def __init__(self, coordinator: BrainInspiredCoordinator):
        self.coordinator = coordinator
        self._start_time = datetime.now()

    async def process_input(self, text: str) -> ProcessingResponseDTO:
        """处理用户输入"""
        result = await self.coordinator.process_user_input(text)
        
        # 提取情绪 (如果有)
        emotion = "neutral"
        if hasattr(result, 'insights') and result.insights:
            emotion = result.insights.get('detected_emotion', 'neutral')

        return ProcessingResponseDTO(
            response=result.response,
            emotion=emotion,
            active_regions=result.agents_involved,
            memories_retrieved=result.memories_retrieved,
            processing_time=result.processing_time
        )

    def get_system_status(self) -> SystemStatusDTO:
        """获取系统整体状态"""
        total_memories = 0
        if hasattr(self.coordinator, 'memory_system') and self.coordinator.memory_system:
            try:
                # Get memory count from database
                stats = self.coordinator.memory_system.get_memory_stats()
                total_memories = stats.get('total_memories', 0)
            except Exception as e:
                logger.warning(f"Failed to get memory count: {e}")

        return SystemStatusDTO(
            is_running=self.coordinator.is_running,
            active_agents=len(self.coordinator.agents),
            total_memories=total_memories,
            uptime_seconds=(datetime.now() - self._start_time).total_seconds(),
            current_task="Idle"
        )

    def get_memory_stats(self) -> List[MemoryRegionStatsDTO]:
        """获取各脑区记忆统计 (替代原 handlers 中的直接访问逻辑)"""
        stats = []
        
        for agent_id, agent in self.coordinator.agents.items():
            # Skip functional agents without storage
            if not hasattr(agent, 'capacity'):
                continue

            capacity = getattr(agent, 'capacity', 0)
            if capacity <= 0:
                continue
                
            current = 0
            if hasattr(agent, 'storage'):
                current = len(agent.storage)
            elif hasattr(agent, 'memory_store'):
                current = len(agent.memory_store)
            
            usage_pct = (current / capacity * 100) if capacity > 0 else 0
            
            stats.append(MemoryRegionStatsDTO(
                id=agent_id,
                name=agent_id.replace('_', ' ').title(),
                capacity=capacity,
                current_count=current,
                usage_percentage=usage_pct,
                total_stored=getattr(agent, 'total_stored', 0),
                total_evicted=getattr(agent, 'total_evicted', 0)
            ))
            
        return stats

    async def update_memory(self, memory_id: str, content: str, importance: float) -> bool:
        """
        更新记忆 (通过 MemorySystem)

        Args:
            memory_id: 记忆ID
            content: 新内容
            importance: 新重要性分数

        Returns:
            是否更新成功
        """
        if not hasattr(self.coordinator, 'memory_system') or not self.coordinator.memory_system:
            logger.warning("Memory system not available for update")
            return False

        try:
            updates = {
                'content': content,
                'importance': importance,
                'updated_at': datetime.now().isoformat()
            }
            return await self.coordinator.memory_system.update_memory(memory_id, updates)
        except Exception as e:
            logger.error(f"Failed to update memory {memory_id}: {e}")
            return False

    async def export_memory(self, output_dir: Any, name: str, description: str) -> Any:
        """导出记忆 (封装 MemoryTransferSystem)"""
        from ..memory.memory_transfer import MemoryTransferSystem
        transfer = MemoryTransferSystem(self.coordinator)
        return await transfer.export_memory(output_dir, name, description)

    async def import_memory(self, archive_path: Any) -> Any:
        """导入记忆 (封装 MemoryTransferSystem)"""
        from ..memory.memory_transfer import MemoryTransferSystem
        transfer = MemoryTransferSystem(self.coordinator)
        return await transfer.import_memory(
            archive_path=archive_path, 
            create_backup=True, 
            validate_before_import=True
        )
