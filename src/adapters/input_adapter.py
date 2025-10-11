"""
Input Adapter - 统一不同场景的输入处理
支持多种输入模式：Session-based, Stream-based, Batch-based
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class InputMode(Enum):
    """输入模式"""
    SESSION_BASED = "session_based"  # 完整对话session (如LoCoMo)
    STREAM_BASED = "stream_based"    # 实时零散输入 (如聊天助手)
    BATCH_BASED = "batch_based"      # 批量导入 (如知识库构建)


class InputAdapter:
    """
    输入适配器 - 根据不同场景自动选择最佳处理方式
    """

    def __init__(self, mode: InputMode = InputMode.STREAM_BASED):
        self.mode = mode
        self.session_buffer = []  # Session缓冲区
        self.current_session_id = None

    async def process_input(
        self,
        coordinator,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        统一入口 - 根据模式处理输入

        Args:
            coordinator: BrainCoordinator实例
            content: 输入内容
            context: 上下文信息 (可选)
                - session_id: Session标识
                - timestamp: 时间戳
                - speaker: 说话人
                - metadata: 其他元数据
        """
        if self.mode == InputMode.SESSION_BASED:
            return await self._process_session_based(coordinator, content, context)
        elif self.mode == InputMode.STREAM_BASED:
            return await self._process_stream_based(coordinator, content, context)
        elif self.mode == InputMode.BATCH_BASED:
            return await self._process_batch_based(coordinator, content, context)

    # =================================================================
    # Session-Based: 适用于超长对话历史 (如LoCoMo测试)
    # =================================================================

    async def _process_session_based(
        self,
        coordinator,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Session-based处理
        - 保留完整的对话结构
        - 记录Session边界
        - 支持记忆巩固
        """
        context = context or {}
        session_id = context.get('session_id')

        # Session开始
        if session_id and session_id != self.current_session_id:
            if self.current_session_id:
                # 前一个Session结束，触发巩固
                await self._consolidate_session(coordinator, self.current_session_id)

            self.current_session_id = session_id
            self.session_buffer = []

            # 存储Session开始标记
            session_start = f"Session {session_id} started"
            if context.get('timestamp'):
                session_start += f" at {context['timestamp']}"

            await coordinator.process_user_input(session_start)

        # 处理当前输入
        result = await coordinator.process_user_input(content)
        self.session_buffer.append({
            'content': content,
            'context': context,
            'result': result
        })

        return result

    async def _consolidate_session(self, coordinator, session_id):
        """Session结束时触发记忆巩固"""
        # TODO: 触发consolidation agent
        # await coordinator.consolidate_memories(session_id)
        pass

    async def end_session(self, coordinator):
        """显式结束当前Session"""
        if self.current_session_id:
            await self._consolidate_session(coordinator, self.current_session_id)
            self.current_session_id = None
            self.session_buffer = []

    # =================================================================
    # Stream-Based: 适用于实时交互 (默认模式)
    # =================================================================

    async def _process_stream_based(
        self,
        coordinator,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Stream-based处理 (默认)
        - 直接处理每条输入
        - 不需要Session概念
        - 适合实时聊天助手
        """
        # 添加时间戳信息 (如果提供)
        if context and context.get('timestamp'):
            enriched_content = f"[{context['timestamp']}] {content}"
        else:
            enriched_content = content

        result = await coordinator.process_user_input(enriched_content)
        return result

    # =================================================================
    # Batch-Based: 适用于批量导入 (如知识库构建)
    # =================================================================

    async def _process_batch_based(
        self,
        coordinator,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Batch-based处理
        - 优化批量导入性能
        - 可以延迟巩固到批次结束
        - 适合一次性导入大量知识
        """
        # Batch模式可以跳过一些实时处理
        # 比如暂时不触发reflection等
        result = await coordinator.process_user_input(
            content,
            skip_reflection=True  # 批量模式跳过反思
        )
        return result

    async def finalize_batch(self, coordinator):
        """批量导入结束，触发全局巩固"""
        # TODO: 批量巩固所有记忆
        # await coordinator.batch_consolidate()
        pass


# =================================================================
# 便捷工厂方法
# =================================================================

def create_session_adapter() -> InputAdapter:
    """创建Session-based适配器 (用于LoCoMo等超长对话测试)"""
    return InputAdapter(mode=InputMode.SESSION_BASED)


def create_stream_adapter() -> InputAdapter:
    """创建Stream-based适配器 (默认，用于实时交互)"""
    return InputAdapter(mode=InputMode.STREAM_BASED)


def create_batch_adapter() -> InputAdapter:
    """创建Batch-based适配器 (用于批量知识导入)"""
    return InputAdapter(mode=InputMode.BATCH_BASED)


# =================================================================
# 使用示例
# =================================================================

"""
# 示例1: Session-based (LoCoMo测试)
adapter = create_session_adapter()

for session in sessions:
    for dialogue in session['dialogues']:
        await adapter.process_input(
            coordinator,
            dialogue['text'],
            context={
                'session_id': session['id'],
                'timestamp': session['date'],
                'speaker': dialogue['speaker']
            }
        )

    await adapter.end_session(coordinator)

# 示例2: Stream-based (实时聊天)
adapter = create_stream_adapter()

user_input = "我今天去了LGBTQ support group"
result = await adapter.process_input(coordinator, user_input)

# 示例3: Batch-based (知识库导入)
adapter = create_batch_adapter()

for doc in documents:
    await adapter.process_input(coordinator, doc['content'])

await adapter.finalize_batch(coordinator)
"""
