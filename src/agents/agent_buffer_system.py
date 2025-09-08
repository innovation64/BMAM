"""
智能体缓冲系统
Agent Buffer System

为12个类脑Agent提供结构化的缓冲文件系统
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import threading

class AgentBufferSystem:
    """智能体缓冲系统 - 每个Agent都有自己的缓冲文件"""
    
    def __init__(self, buffer_dir: str = "data/agent_buffers"):
        self.buffer_dir = Path(buffer_dir)
        self.buffer_dir.mkdir(parents=True, exist_ok=True)
        
        # 12个Agent的缓冲配置
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
                    'recent_exchanges': []
                }
            },
            'long_term_memory': {
                'name': '长期记忆智能体', 
                'brain_region': 'neocortex',
                'buffer_file': 'long_term_memory_buffer.json',
                'max_items': 1000,
                'structure': {
                    'semantic_memories': [],
                    'user_preferences': {},
                    'knowledge_base': {},
                    'associations': [],
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
                    'recent_exchanges': []
                }
            },
            'memory_consolidation': {
                'name': '记忆巩固智能体',
                'brain_region': 'hippocampus',
                'buffer_file': 'memory_consolidation_buffer.json',
                'max_items': 100,
                'structure': {
                    'consolidation_queue': [],
                    'consolidation_history': [],
                    'importance_scores': {},
                    'scheduled_tasks': [],
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
                    'recent_exchanges': []
                }
            }
        }
        
        # 初始化所有缓冲文件
        self._initialize_buffers()
        
        # 线程锁，用于并发访问控制
        self.locks = {agent_id: threading.Lock() for agent_id in self.agent_buffers}
    
    def _initialize_buffers(self):
        """初始化所有Agent的缓冲文件"""
        for agent_id, config in self.agent_buffers.items():
            buffer_path = self.buffer_dir / config['buffer_file']
            
            # 如果文件不存在，创建初始结构
            if not buffer_path.exists():
                initial_data = {
                    'agent_id': agent_id,
                    'agent_name': config['name'],
                    'brain_region': config['brain_region'],
                    'created_at': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat(),
                    'buffer_content': config['structure'],
                    'metadata': {
                        'total_operations': 0,
                        'last_operation': None
                    }
                }
                
                with open(buffer_path, 'w', encoding='utf-8') as f:
                    json.dump(initial_data, f, indent=2, ensure_ascii=False)
                
                print(f"✅ 初始化 {config['name']} 缓冲文件: {buffer_path}")
    
    def read_buffer(self, agent_id: str) -> Dict[str, Any]:
        """读取Agent的缓冲内容"""
        if agent_id not in self.agent_buffers:
            raise ValueError(f"Unknown agent: {agent_id}")
        
        with self.locks[agent_id]:
            buffer_path = self.buffer_dir / self.agent_buffers[agent_id]['buffer_file']
            
            with open(buffer_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data['buffer_content']
    
    def write_buffer(self, agent_id: str, key: str, value: Any, append: bool = False):
        """写入Agent的缓冲内容"""
        if agent_id not in self.agent_buffers:
            raise ValueError(f"Unknown agent: {agent_id}")
        
        with self.locks[agent_id]:
            buffer_path = self.buffer_dir / self.agent_buffers[agent_id]['buffer_file']
            
            # 读取现有数据
            with open(buffer_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 更新缓冲内容 - 简化版本，专注存储
            if append and isinstance(data['buffer_content'].get(key), list):
                data['buffer_content'][key].append(value)
                
                # 硬限制列表长度，防止内存溢出
                max_items = self.agent_buffers[agent_id]['max_items']
                if len(data['buffer_content'][key]) > max_items:
                    data['buffer_content'][key] = data['buffer_content'][key][-max_items:]
            else:
                data['buffer_content'][key] = value
            
            # 更新元数据
            data['last_updated'] = datetime.now().isoformat()
            data['metadata']['total_operations'] += 1
            data['metadata']['last_operation'] = {
                'type': 'write',
                'key': key,
                'timestamp': datetime.now().isoformat()
            }
            
            # 写回文件
            with open(buffer_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
    
    def exchange_buffers(self, from_agent: str, to_agent: str, data_key: str, data: Any):
        """Agent间交换信息 - 修复版本，避免无限增长"""
        import hashlib
        
        # 为数据生成唯一哈希ID，避免重复存储
        data_str = json.dumps(data, sort_keys=True, default=str)
        data_hash = hashlib.md5(data_str.encode()).hexdigest()[:8]
        
        # 简化的交换记录，只存储引用而不是完整数据
        exchange_record = {
            'data_key': data_key,
            'data_hash': data_hash,
            'data_summary': str(data)[:200] + '...' if len(str(data)) > 200 else str(data),
            'timestamp': datetime.now().isoformat(),
            'from_agent': from_agent,
            'to_agent': to_agent
        }
        
        # 使用固定键名避免无限增长，并启用max_items限制
        self.write_buffer(from_agent, 'recent_exchanges', exchange_record, append=True)
        self.write_buffer(to_agent, 'recent_exchanges', exchange_record, append=True)
        
        return True
    
    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """获取Agent缓冲状态"""
        if agent_id not in self.agent_buffers:
            raise ValueError(f"Unknown agent: {agent_id}")
        
        buffer_path = self.buffer_dir / self.agent_buffers[agent_id]['buffer_file']
        
        with open(buffer_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 计算缓冲区使用情况
        buffer_content = data['buffer_content']
        usage_stats = {}
        
        for key, value in buffer_content.items():
            if isinstance(value, list):
                usage_stats[key] = len(value)
            elif isinstance(value, dict):
                usage_stats[key] = len(value)
            else:
                usage_stats[key] = 1 if value else 0
        
        return {
            'agent_id': agent_id,
            'agent_name': self.agent_buffers[agent_id]['name'],
            'brain_region': self.agent_buffers[agent_id]['brain_region'],
            'last_updated': data['last_updated'],
            'total_operations': data['metadata']['total_operations'],
            'buffer_usage': usage_stats,
            'max_items': self.agent_buffers[agent_id]['max_items']
        }
    
    def clear_buffer(self, agent_id: str):
        """清空Agent缓冲"""
        if agent_id not in self.agent_buffers:
            raise ValueError(f"Unknown agent: {agent_id}")
        
        with self.locks[agent_id]:
            buffer_path = self.buffer_dir / self.agent_buffers[agent_id]['buffer_file']
            
            # 重置为初始结构
            data = {
                'agent_id': agent_id,
                'agent_name': self.agent_buffers[agent_id]['name'],
                'brain_region': self.agent_buffers[agent_id]['brain_region'],
                'created_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat(),
                'buffer_content': self.agent_buffers[agent_id]['structure'].copy(),
                'metadata': {
                    'total_operations': 0,
                    'last_operation': None
                }
            }
            
            with open(buffer_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_all_buffers_status(self) -> List[Dict[str, Any]]:
        """获取所有Agent的缓冲状态"""
        status_list = []
        
        for agent_id in self.agent_buffers:
            status = self.get_agent_status(agent_id)
            status_list.append(status)
        
        return status_list
    
    def save_user_preference(self, preference: str):
        """专门用于保存用户偏好到长期记忆缓冲"""
        self.write_buffer('long_term_memory', 'user_preferences', {
            'preference': preference,
            'timestamp': datetime.now().isoformat(),
            'importance': 0.9
        }, append=True)
        
        # 同时通知记忆巩固智能体
        self.write_buffer('memory_consolidation', 'consolidation_queue', {
            'type': 'user_preference',
            'content': preference,
            'priority': 'high',
            'timestamp': datetime.now().isoformat()
        }, append=True)

# 创建全局缓冲系统实例
agent_buffer_system = AgentBufferSystem()

if __name__ == "__main__":
    # 测试缓冲系统
    print("🧠 智能体缓冲系统初始化完成")
    print("=" * 50)
    
    # 显示所有Agent的缓冲状态
    all_status = agent_buffer_system.get_all_buffers_status()
    
    for status in all_status:
        print(f"\n{status['agent_name']} ({status['brain_region']})")
        print(f"  最后更新: {status['last_updated'][:19]}")
        print(f"  总操作数: {status['total_operations']}")
        print(f"  缓冲使用: {status['buffer_usage']}")
        print(f"  最大容量: {status['max_items']}")