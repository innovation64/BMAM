"""
智能体缓冲系统
Agent Buffer System

为12个类脑Agent提供结构化的缓冲文件系统
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import asyncio
import aiofiles
from ..utils.config import get_logger, get_absolute_path

logger = get_logger(__name__)

class AgentBufferSystem:
    """智能体缓冲系统 - 每个Agent都有自己的缓冲文件"""
    
    def __init__(self, buffer_dir: str = "data/agent_buffers"):
        self.buffer_dir = get_absolute_path(buffer_dir)
        self.buffer_dir.mkdir(parents=True, exist_ok=True)
        
        # 12个Agent的缓冲配置 - 所有agent都有统一的recent_inputs和recent_outputs字段
        self.agent_buffers = {
            'short_term_memory': {
                'name': '短期记忆智能体',
                'brain_region': 'prefrontal',
                'buffer_file': 'short_term_memory_buffer.json',
                'max_items': 100,
                'structure': {
                    'working_memory': [],
                    'attention_focus': None,
                    'recent_inputs': [],
                    'processing_queue': [],
                    'recent_exchanges': [],
                    'recent_outputs': []
                }
            },
            'long_term_memory': {
                'name': '长期记忆智能体', 
                'brain_region': 'neocortex',
                'buffer_file': 'long_term_memory_buffer.json',
                'max_items': 1000,
                'structure': {
                    'semantic_memories': [],
                    'user_preferences': [],  # 修复：改为列表而不是字典
                    'knowledge_base': {},
                    'associations': [],
                    'recent_inputs': [],
                    'recent_outputs': [],
                    'recent_exchanges': []
                }
            },
            'memory_retrieval': {
                'name': '记忆检索智能体',
                'brain_region': 'hippocampus',
                'buffer_file': 'memory_retrieval_buffer.json',
                'max_items': 200,
                'structure': {
                    'recent_queries': [],
                    'retrieval_cache': {},
                    'search_patterns': [],
                    'index_mappings': {},
                    'recent_inputs': [],
                    'recent_outputs': [],
                    'recent_exchanges': []
                }
            },
            'consolidation': {
                'name': '记忆巩固智能体',
                'brain_region': 'hippocampus',
                'buffer_file': 'consolidation_buffer.json',
                'max_items': 100,
                'structure': {
                    'consolidation_queue': [],
                    'consolidation_history': [],
                    'importance_scores': {},
                    'scheduled_tasks': [],
                    'recent_inputs': [],
                    'recent_outputs': [],
                    'recent_exchanges': []
                }
            },
            'memory_distortion': {
                'name': '记忆失真智能体',
                'brain_region': 'thalamus',
                'buffer_file': 'memory_distortion_buffer.json',
                'max_items': 100,
                'structure': {
                    'distortion_patterns': [],
                    'modified_memories': [],
                    'noise_levels': {},
                    'reality_checks': [],
                    'recent_inputs': [],
                    'recent_outputs': [],
                    'recent_exchanges': []
                }
            },
            'reflection': {
                'name': '反思智能体',
                'brain_region': 'default_mode',
                'buffer_file': 'reflection_buffer.json',
                'max_items': 100,
                'structure': {
                    'insights': [],
                    'patterns_discovered': [],
                    'meta_thoughts': [],
                    'connections_made': [],
                    'recent_inputs': [],
                    'recent_outputs': [],
                    'recent_exchanges': []
                }
            },
            'forgetting': {
                'name': '遗忘智能体',
                'brain_region': 'inhibition',
                'buffer_file': 'forgetting_buffer.json',
                'max_items': 100,
                'structure': {
                    'forgetting_schedule': [],
                    'removed_memories': [],
                    'decay_rates': {},
                    'importance_threshold': 0.3,
                    'recent_inputs': [],
                    'recent_outputs': [],
                    'recent_exchanges': []
                }
            },
            'stress_response': {
                'name': '应激反应智能体',
                'brain_region': 'amygdala',
                'buffer_file': 'stress_response_buffer.json',
                'max_items': 100,
                'structure': {
                    'emotional_states': [],
                    'threat_assessments': [],
                    'emotional_memories': [],
                    'arousal_levels': {},
                    'recent_inputs': [],
                    'recent_outputs': [],
                    'recent_exchanges': []
                }
            },
            'personality': {
                'name': '人格智能体',
                'brain_region': 'default_mode',
                'buffer_file': 'personality_buffer.json',
                'max_items': 100,
                'structure': {
                    'personality_traits': {},
                    'behavior_patterns': [],
                    'preference_history': [],
                    'interaction_style': {},
                    'recent_inputs': [],
                    'recent_outputs': [],
                    'recent_exchanges': []
                }
            },
            'conversation': {
                'name': '对话智能体',
                'brain_region': 'broca_wernicke',
                'buffer_file': 'conversation_buffer.json',
                'max_items': 200,
                'structure': {
                    'dialogue_history': [],
                    'response_templates': {},
                    'context_stack': [],
                    'user_model': {},
                    'recent_inputs': [],
                    'recent_outputs': [],
                    'recent_exchanges': []
                }
            },
            'executive_control': {
                'name': '执行控制智能体',
                'brain_region': 'acc',
                'buffer_file': 'executive_control_buffer.json',
                'max_items': 100,
                'structure': {
                    'task_queue': [],
                    'agent_routing': {},
                    'coordination_plans': [],
                    'resource_allocation': {},
                    'recent_inputs': [],
                    'recent_outputs': [],
                    'recent_exchanges': []
                }
            },
            'perception_encoding': {
                'name': '感知编码智能体',
                'brain_region': 'sensory_cortex',
                'buffer_file': 'perception_encoding_buffer.json',
                'max_items': 100,
                'structure': {
                    'encoded_inputs': [],
                    'feature_vectors': {},
                    'pattern_library': [],
                    'sensory_cache': {},
                    'recent_inputs': [],
                    'recent_outputs': [],
                    'recent_exchanges': []
                }
            },
            'action_execution': {
                'name': '行动执行智能体',
                'brain_region': 'motor_cortex',
                'buffer_file': 'action_execution_buffer.json',
                'max_items': 100,
                'structure': {
                    'action_queue': [],
                    'execution_history': [],
                    'motor_plans': {},
                    'feedback_signals': [],
                    'recent_inputs': [],
                    'recent_outputs': [],
                    'recent_exchanges': []
                }
            }
        }
        
        # 延迟初始化所有缓冲文件（异步）
        
        # 异步锁，用于并发访问控制
        self.locks = {agent_id: asyncio.Lock() for agent_id in self.agent_buffers}
        self._initialized = False
    
    async def _initialize_buffers(self):
        """初始化所有缓冲文件"""
        tasks = [self._initialize_buffer_file(agent_id) for agent_id in self.agent_buffers]
        await asyncio.gather(*tasks)
    
    async def _initialize_buffer_file(self, agent_id: str):
        """初始化单个Agent的缓冲文件"""
        config = self.agent_buffers[agent_id]
        buffer_path = self.buffer_dir / config['buffer_file']
        
        if not buffer_path.exists():
            initial_data = {
                'agent_id': agent_id,
                'agent_name': config['name'],
                'brain_region': config['brain_region'],
                'buffer_content': config['structure'].copy(),
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat(),
                    'version': '1.0'
                }
            }
            
            async with aiofiles.open(buffer_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(initial_data, indent=2, ensure_ascii=False))
            
            logger.info(f"初始化 {config['name']} 缓冲文件: {buffer_path}")
    
    async def _ensure_initialized(self):
        """确保缓冲系统已初始化"""
        if not self._initialized:
            await self._initialize_buffers()
            self._initialized = True
    
    async def read_buffer(self, agent_id: str) -> Dict[str, Any]:
        """读取Agent的缓冲内容"""
        if agent_id not in self.agent_buffers:
            raise ValueError(f"Unknown agent: {agent_id}")
        
        await self._ensure_initialized()
        
        async with self.locks[agent_id]:
            return await self._read_buffer_unlocked(agent_id)
    
    async def _read_buffer_unlocked(self, agent_id: str) -> Dict[str, Any]:
        """读取Agent缓冲内容（假设锁已持有）"""
        buffer_path = self.buffer_dir / self.agent_buffers[agent_id]['buffer_file']
        
        try:
            async with aiofiles.open(buffer_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
            return data['buffer_content']
        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            # 文件损坏或不存在，重新初始化
            logger.warning(f"Buffer file corrupted for {agent_id}, reinitializing: {e}")
            await self._initialize_buffer_file(agent_id)
            # 返回默认结构
            return self.agent_buffers[agent_id]['structure'].copy()
    
    async def write_buffer(self, agent_id: str, key: str, value: Any, append: bool = False):
        """写入Agent的缓冲内容"""
        if agent_id not in self.agent_buffers:
            raise ValueError(f"Unknown agent: {agent_id}")
        
        await self._ensure_initialized()
        
        async with self.locks[agent_id]:
            buffer_path = self.buffer_dir / self.agent_buffers[agent_id]['buffer_file']
            
            # 读取现有数据，带错误处理
            try:
                async with aiofiles.open(buffer_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    data = json.loads(content)
            except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
                # 文件损坏或不存在，重新初始化
                logger.warning(f"Buffer file corrupted for {agent_id} during write, reinitializing: {e}")
                await self._initialize_buffer_file(agent_id)
                async with aiofiles.open(buffer_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    data = json.loads(content)
            
            # 更新缓冲内容 - 改进的append逻辑
            if append:
                # 如果键不存在，创建为列表
                if key not in data['buffer_content']:
                    data['buffer_content'][key] = []
                
                # 确保目标是列表，如果不是则转换为列表
                if not isinstance(data['buffer_content'][key], list):
                    data['buffer_content'][key] = [data['buffer_content'][key]]
                
                # 添加新值
                data['buffer_content'][key].append(value)
                
                # 应用长度限制
                max_items = self.agent_buffers[agent_id]['max_items']
                if len(data['buffer_content'][key]) > max_items:
                    data['buffer_content'][key] = data['buffer_content'][key][-max_items:]
            else:
                # 直接设置值
                data['buffer_content'][key] = value
            
            # 更新元数据
            data['metadata']['last_updated'] = datetime.now().isoformat()
            
            # 写回文件
            async with aiofiles.open(buffer_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2, ensure_ascii=False))

    async def _write_buffer_unlocked(self, agent_id: str, key: str, value: Any, append: bool = False):
        """写入Agent缓冲内容（不获取锁，调用方需保证已持有相应锁）。"""
        if agent_id not in self.agent_buffers:
            raise ValueError(f"Unknown agent: {agent_id}")

        await self._ensure_initialized()

        buffer_path = self.buffer_dir / self.agent_buffers[agent_id]['buffer_file']

        # 读取现有数据，带错误处理
        try:
            async with aiofiles.open(buffer_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            # 文件损坏或不存在，重新初始化
            logger.warning(f"Buffer file corrupted for {agent_id} during unlocked write, reinitializing: {e}")
            await self._initialize_buffer_file(agent_id)
            async with aiofiles.open(buffer_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)

        # 更新缓冲内容 - 改进的append逻辑（与write_buffer保持一致）
        if append:
            if key not in data['buffer_content']:
                data['buffer_content'][key] = []
            if not isinstance(data['buffer_content'][key], list):
                data['buffer_content'][key] = [data['buffer_content'][key]]
            data['buffer_content'][key].append(value)
            max_items = self.agent_buffers[agent_id]['max_items']
            if len(data['buffer_content'][key]) > max_items:
                data['buffer_content'][key] = data['buffer_content'][key][-max_items:]
        else:
            data['buffer_content'][key] = value

        # 更新元数据并写回
        data['metadata']['last_updated'] = datetime.now().isoformat()
        async with aiofiles.open(buffer_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, indent=2, ensure_ascii=False))
    
    async def clear_buffer(self, agent_id: str):
        """清空Agent的缓冲内容"""
        if agent_id not in self.agent_buffers:
            raise ValueError(f"Unknown agent: {agent_id}")
        
        await self._ensure_initialized()
        
        async with self.locks[agent_id]:
            buffer_path = self.buffer_dir / self.agent_buffers[agent_id]['buffer_file']
            
            # 读取现有数据
            async with aiofiles.open(buffer_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
            
            # 深拷贝避免共享引用
            import copy
            data['buffer_content'] = copy.deepcopy(self.agent_buffers[agent_id]['structure'])
            data['metadata']['last_updated'] = datetime.now().isoformat()
            
            # 写回文件
            async with aiofiles.open(buffer_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2, ensure_ascii=False))
    
    async def exchange_buffers(self, source_agent: str, target_agent: str, data_key: str, data: Any):
        """在两个Agent之间交换缓冲数据"""
        if source_agent not in self.agent_buffers or target_agent not in self.agent_buffers:
            raise ValueError("Invalid agent IDs for buffer exchange")

        await self._ensure_initialized()

        if source_agent == target_agent:
            async with self.locks[source_agent]:
                await self._write_buffer_unlocked(target_agent, data_key, data, append=True)
                await self._write_buffer_unlocked(
                    target_agent,
                    'recent_exchanges',
                    {
                        'source': source_agent,
                        'target': target_agent,
                        'data_key': data_key,
                        'data_summary': str(data)[:200],
                        'data_hash': hashlib.md5(str(data).encode()).hexdigest(),
                        'timestamp': datetime.now().isoformat()
                    },
                    append=True
                )
            return

        # 使用有序锁避免死锁
        first_lock = self.locks[min(source_agent, target_agent)]
        second_lock = self.locks[max(source_agent, target_agent)]

        async with first_lock, second_lock:
            # 计算数据摘要用于去重检查
            data_hash = hashlib.md5(str(data).encode()).hexdigest()
            
            # 直接读取目标agent数据，避免重入锁
            target_buffer = await self._read_buffer_unlocked(target_agent)
            
            # 去重检查
            if 'recent_exchanges' in target_buffer:
                for exchange in target_buffer['recent_exchanges']:
                    if exchange.get('data_hash') == data_hash:
                        logger.debug(f"Duplicate exchange detected, skipping: {data_hash[:8]}")
                        return
            
            # 记录交换
            exchange_record = {
                'source': source_agent,
                'target': target_agent,
                'data_key': data_key,
                'data_summary': str(data)[:200],  # 限制长度避免敏感信息
                'data_hash': data_hash,
                'timestamp': datetime.now().isoformat()
            }
            
            # 写入目标agent（已持有锁，使用unlocked写入避免重入同一把锁）
            await self._write_buffer_unlocked(target_agent, data_key, data, append=True)
            await self._write_buffer_unlocked(target_agent, 'recent_exchanges', exchange_record, append=True)

            logger.debug(f"Buffer exchange: {source_agent} -> {target_agent} ({data_key})")

    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """获取Agent的缓冲状态"""
        if agent_id not in self.agent_buffers:
            raise ValueError(f"Unknown agent: {agent_id}")
        
        await self._ensure_initialized()
        buffer_path = self.buffer_dir / self.agent_buffers[agent_id]['buffer_file']
        
        try:
            async with aiofiles.open(buffer_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
            
            status = {
                'agent_id': agent_id,
                'agent_name': data.get('agent_name', 'Unknown'),
                'brain_region': data.get('brain_region', 'Unknown'),
                'buffer_size': sum(len(v) if isinstance(v, list) else 1 for v in data['buffer_content'].values()),
                'last_updated': data.get('metadata', {}).get('last_updated', 'Unknown'),
                'file_size': buffer_path.stat().st_size if buffer_path.exists() else 0
            }
            return status
        except Exception as e:
            return {
                'agent_id': agent_id,
                'error': str(e),
                'status': 'corrupted'
            }
    
    async def get_all_buffers_status(self) -> Dict[str, Any]:
        """获取所有Agent的缓冲状态"""
        await self._ensure_initialized()
        tasks = [self.get_agent_status(agent_id) for agent_id in self.agent_buffers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {agent_id: result for agent_id, result in zip(self.agent_buffers.keys(), results)}

    async def save_user_preference(self, preference_type: str, preference_data: Dict[str, Any]):
        """保存用户偏好到长期记忆"""
        preference_entry = {
            'type': preference_type,
            'data': preference_data,
            'timestamp': datetime.now().isoformat()
        }

        # 修复：user_preferences现在是列表，可以正常append
        await self.write_buffer('long_term_memory', 'user_preferences', preference_entry, append=True)
        logger.info(f"Saved user preference: {preference_type}")

    async def cleanup_stale_entries(self, max_age_hours: int = 24):
        """Remove stale recent_* entries to keep buffer footprint bounded."""
        await self._ensure_initialized()
        cutoff = datetime.now() - timedelta(hours=max_age_hours)

        for agent_id in self.agent_buffers:
            async with self.locks[agent_id]:
                buffer_path = self.buffer_dir / self.agent_buffers[agent_id]['buffer_file']
                try:
                    async with aiofiles.open(buffer_path, 'r', encoding='utf-8') as f:
                        data = json.loads(await f.read())
                except Exception as exc:
                    logger.warning(f"Failed to load buffer for cleanup ({agent_id}): {exc}")
                    continue

                content = data.get('buffer_content', {})
                cleaned = False

                for key in ['recent_inputs', 'recent_outputs', 'recent_exchanges']:
                    entries = content.get(key)
                    if isinstance(entries, list) and entries:
                        filtered = []
                        for entry in entries:
                            timestamp = None
                            if isinstance(entry, dict):
                                timestamp = entry.get('timestamp') or entry.get('time')
                            if isinstance(timestamp, str):
                                try:
                                    timestamp = datetime.fromisoformat(timestamp)
                                except ValueError:
                                    timestamp = None
                            if not isinstance(timestamp, datetime) or timestamp >= cutoff:
                                filtered.append(entry)
                        if len(filtered) != len(entries):
                            content[key] = filtered
                            cleaned = True

                if cleaned:
                    data['buffer_content'] = content
                    data.setdefault('metadata', {})['last_updated'] = datetime.now().isoformat()
                    async with aiofiles.open(buffer_path, 'w', encoding='utf-8') as f:
                        await f.write(json.dumps(data, indent=2, ensure_ascii=False))
                    logger.debug(f"Cleaned stale buffer entries for {agent_id}")


# 创建全局实例，但不立即初始化文件
agent_buffer_system = AgentBufferSystem()


async def get_buffer_system_status():
    """获取缓冲系统状态的便捷函数"""
    all_status = await agent_buffer_system.get_all_buffers_status()
    
    print("🧠 Agent Buffer System Status")
    print("=" * 40)
    
    for agent_id, status in all_status.items():
        if 'error' in status:
            print(f"❌ {agent_id}: {status['error']}")
        else:
            print(f"✅ {agent_id}: {status['buffer_size']} items, {status['file_size']} bytes")


if __name__ == "__main__":
    asyncio.run(get_buffer_system_status())
