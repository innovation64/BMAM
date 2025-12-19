#!/usr/bin/env python3
"""
BMAM Adapter - 统一的 BMAM 接口适配器
用于所有评估脚本与 BMAM 系统的交互
"""

import asyncio
import os
import sys
import shutil
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# Setup path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Suppress logging
import warnings
warnings.filterwarnings('ignore')
logging.getLogger().setLevel(logging.CRITICAL)
for name in ['src', 'openai', 'httpx', 'httpcore', 'urllib3', 'faiss']:
    logging.getLogger(name).setLevel(logging.CRITICAL)
os.environ['TOKENIZERS_PARALLELISM'] = 'false'


class BMAMAdapter:
    """BMAM 系统适配器"""

    def __init__(self, data_dir: Optional[Path] = None, enable_hrm: bool = True):
        self.data_dir = data_dir or PROJECT_ROOT / 'data'
        self.enable_hrm = enable_hrm
        self.coordinator = None
        self._initialized = False

    async def initialize(self):
        """初始化 BMAM 系统"""
        from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

        base_coord = BrainInspiredCoordinator()

        if self.enable_hrm:
            from src.coordination.hrm_coordinator_wrapper import HRMCoordinatorWrapper, HRMConfig
            hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
            self.coordinator = HRMCoordinatorWrapper(base_coord, hrm_config)
        else:
            self.coordinator = base_coord

        await self.coordinator.start_system()
        self._initialized = True

    async def shutdown(self):
        """关闭系统"""
        if self.coordinator and hasattr(self.coordinator, 'stop_system'):
            await self.coordinator.stop_system()
        self._initialized = False

    def clear_memory(self):
        """清空所有记忆文件"""
        files = [
            'hippocampus_state.json', 'basal_ganglia_state.json',
            'prefrontal_state.json', 'amygdala_state.json',
            'brain_memory.db', 'temporal_lobe.db', 'working_memory.db',
            'story_arc_state.json', 'tom_state.json', 'kv_value_store.db'
        ]
        for f in files:
            p = self.data_dir / f
            if p.exists():
                p.unlink()

        for d in ['embedding_cache', 'knowledge_graph', 'faiss_index']:
            p = self.data_dir / d
            if p.exists():
                shutil.rmtree(p)

    async def store_memory(self, content: str, timestamp: Optional[datetime] = None,
                          speaker: str = "user", importance: float = 0.6) -> bool:
        """存储记忆"""
        if not self._initialized:
            raise RuntimeError("BMAM not initialized. Call initialize() first.")

        ts = timestamp or datetime.now()
        try:
            await self.coordinator.store_memory_with_timestamp(content, ts, speaker, importance)
            return True
        except Exception as e:
            logging.warning(f"Store memory failed: {e}")
            return False

    async def store_conversation(self, messages: List[Dict[str, str]],
                                 session_date: Optional[datetime] = None) -> int:
        """存储对话 (多条消息)"""
        count = 0
        ts = session_date or datetime.now()

        for msg in messages:
            speaker = msg.get('speaker', msg.get('role', 'user'))
            content = msg.get('text', msg.get('content', ''))
            if content:
                success = await self.store_memory(f"{speaker}: {content}", ts, speaker)
                if success:
                    count += 1
        return count

    async def query(self, question: str, evaluation_mode: bool = True) -> Tuple[str, Dict[str, Any]]:
        """
        查询系统

        Args:
            question: 问题
            evaluation_mode: 评估模式 (禁止外部探索和主动询问)

        Returns:
            (answer, metadata)
        """
        if not self._initialized:
            raise RuntimeError("BMAM not initialized. Call initialize() first.")

        start_time = time.time()

        context = {
            'skip_memory_store': True,
            'evaluation_mode': evaluation_mode
        }

        result = await self.coordinator.process_user_input(question, context=context)

        # 提取响应
        if hasattr(result, 'response'):
            answer = result.response
        elif isinstance(result, dict):
            answer = result.get('response', str(result))
        else:
            answer = str(result)

        # 提取元数据
        metadata = {
            'response_duration_ms': (time.time() - start_time) * 1000,
            'search_duration_ms': getattr(result, 'search_duration_ms', 0),
        }

        # 提取检索到的记忆
        if hasattr(result, 'retrieved_memories'):
            metadata['retrieved_memories'] = result.retrieved_memories
        if hasattr(result, 'search_context'):
            metadata['search_context'] = result.search_context

        return answer, metadata

    async def search_memories(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        """搜索记忆"""
        if not self._initialized:
            raise RuntimeError("BMAM not initialized. Call initialize() first.")

        try:
            # 使用 coordinator 的搜索功能
            if hasattr(self.coordinator, 'smart_retrieve'):
                results = await self.coordinator.smart_retrieve(query, top_k=top_k)
            elif hasattr(self.coordinator, 'retrieve_memories'):
                results = await self.coordinator.retrieve_memories(query, limit=top_k)
            else:
                results = []

            return results if isinstance(results, list) else []
        except Exception as e:
            logging.warning(f"Search memories failed: {e}")
            return []

    async def consolidate(self, wait_time: float = 3.0):
        """触发记忆巩固"""
        if hasattr(self.coordinator, 'trigger_consolidation'):
            await self.coordinator.trigger_consolidation()
        await asyncio.sleep(wait_time)


class BMAMAblationAdapter(BMAMAdapter):
    """消融实验适配器 - 支持禁用特定模块"""

    def __init__(self,
                 data_dir: Optional[Path] = None,
                 enable_story_arc: bool = True,
                 enable_tom: bool = True,
                 enable_kg: bool = True,
                 enable_emotion: bool = True,
                 enable_hrm: bool = True):
        super().__init__(data_dir, enable_hrm)
        self.enable_story_arc = enable_story_arc
        self.enable_tom = enable_tom
        self.enable_kg = enable_kg
        self.enable_emotion = enable_emotion

    async def initialize(self):
        """初始化带消融设置的系统"""
        # 设置环境变量来控制模块
        if not self.enable_story_arc:
            os.environ['BMAM_DISABLE_STORY_ARC'] = 'true'
        if not self.enable_tom:
            os.environ['BMAM_DISABLE_TOM'] = 'true'
        if not self.enable_kg:
            os.environ['BMAM_DISABLE_KG'] = 'true'
        if not self.enable_emotion:
            os.environ['BMAM_DISABLE_EMOTION'] = 'true'

        await super().initialize()

    def get_ablation_config(self) -> Dict[str, bool]:
        """获取消融配置"""
        return {
            'story_arc': self.enable_story_arc,
            'tom': self.enable_tom,
            'kg': self.enable_kg,
            'emotion': self.enable_emotion,
            'hrm': self.enable_hrm
        }


def parse_date(s: str) -> datetime:
    """解析日期字符串"""
    if not s:
        return datetime.now()
    try:
        from dateutil import parser
        return parser.parse(s, fuzzy=True)
    except:
        return datetime.now()
