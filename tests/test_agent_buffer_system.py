#!/usr/bin/env python3
"""
Unit tests for AgentBufferSystem
测试智能体缓冲系统的所有功能
"""

import asyncio
import tempfile
import shutil
from pathlib import Path
import json
from datetime import datetime
import pytest

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.agent_buffer_system import AgentBufferSystem


class TestAgentBufferSystem:
    """AgentBufferSystem单元测试类"""
    
    def setup_method(self):
        """设置测试环境"""
        # 创建临时目录用于测试
        self.test_dir = tempfile.mkdtemp()
        self.buffer_system = AgentBufferSystem(buffer_dir=self.test_dir)
    
    def teardown_method(self):
        """清理测试环境"""
        # 删除临时目录
        if Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)
    
    async def test_initialization(self):
        """测试初始化功能"""
        # 确保系统初始化
        await self.buffer_system._ensure_initialized()
        
        # 检查目录是否创建
        assert Path(self.test_dir).exists()
        
        # 检查所有agent配置是否存在
        expected_agents = [
            'short_term_memory', 'long_term_memory', 'memory_retrieval',
            'consolidation', 'memory_distortion', 'reflection', 'forgetting',
            'stress_response', 'personality', 'conversation', 'executive_control',
            'perception_encoding', 'action_execution'
        ]
        
        for agent_id in expected_agents:
            assert agent_id in self.buffer_system.agent_buffers
            
        print("✅ 初始化测试通过")
    
    async def test_buffer_creation(self):
        """测试缓冲文件创建"""
        await self.buffer_system._ensure_initialized()
        
        # 检查所有agent的缓冲文件是否创建
        for agent_id, config in self.buffer_system.agent_buffers.items():
            buffer_file = Path(self.test_dir) / config['buffer_file']
            assert buffer_file.exists(), f"Buffer file for {agent_id} not created"
            
            # 检查文件内容结构
            with open(buffer_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            assert 'agent_id' in data
            assert 'buffer_content' in data
            assert 'metadata' in data
            assert data['agent_id'] == agent_id
            
        print("✅ 缓冲文件创建测试通过")
    
    async def test_read_buffer(self):
        """测试读取缓冲功能"""
        await self.buffer_system._ensure_initialized()
        
        # 测试读取现有agent的缓冲
        buffer_content = await self.buffer_system.read_buffer('short_term_memory')
        
        assert isinstance(buffer_content, dict)
        assert 'working_memory' in buffer_content
        assert 'recent_inputs' in buffer_content
        assert 'recent_outputs' in buffer_content
        
        # 测试读取不存在的agent
        try:
            await self.buffer_system.read_buffer('nonexistent_agent')
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
            
        print("✅ 读取缓冲测试通过")
    
    async def test_write_buffer(self):
        """测试写入缓冲功能"""
        await self.buffer_system._ensure_initialized()
        
        # 测试直接写入
        test_data = {'test_key': 'test_value', 'timestamp': datetime.now().isoformat()}
        await self.buffer_system.write_buffer('short_term_memory', 'test_field', test_data)
        
        # 验证写入结果
        buffer_content = await self.buffer_system.read_buffer('short_term_memory')
        assert buffer_content['test_field'] == test_data
        
        # 测试追加写入
        await self.buffer_system.write_buffer('short_term_memory', 'recent_inputs', 
                                              {'input': 'test input 1'}, append=True)
        await self.buffer_system.write_buffer('short_term_memory', 'recent_inputs', 
                                              {'input': 'test input 2'}, append=True)
        
        buffer_content = await self.buffer_system.read_buffer('short_term_memory')
        assert len(buffer_content['recent_inputs']) == 2
        assert buffer_content['recent_inputs'][0]['input'] == 'test input 1'
        assert buffer_content['recent_inputs'][1]['input'] == 'test input 2'
        
        print("✅ 写入缓冲测试通过")
    
    async def test_append_logic(self):
        """测试追加逻辑的边界情况"""
        await self.buffer_system._ensure_initialized()
        
        # 测试追加到不存在的键
        await self.buffer_system.write_buffer('short_term_memory', 'new_list_field', 
                                              'first item', append=True)
        
        buffer_content = await self.buffer_system.read_buffer('short_term_memory')
        assert isinstance(buffer_content['new_list_field'], list)
        assert buffer_content['new_list_field'][0] == 'first item'
        
        # 测试将非列表字段转换为列表
        await self.buffer_system.write_buffer('short_term_memory', 'single_value', 'original')
        await self.buffer_system.write_buffer('short_term_memory', 'single_value', 
                                              'appended', append=True)
        
        buffer_content = await self.buffer_system.read_buffer('short_term_memory')
        assert isinstance(buffer_content['single_value'], list)
        assert buffer_content['single_value'][0] == 'original'
        assert buffer_content['single_value'][1] == 'appended'
        
        print("✅ 追加逻辑测试通过")
    
    async def test_max_items_limit(self):
        """测试最大项目数限制"""
        await self.buffer_system._ensure_initialized()
        
        # 获取short_term_memory的最大限制
        max_items = self.buffer_system.agent_buffers['short_term_memory']['max_items']
        
        # 添加超过限制的项目
        for i in range(max_items + 10):
            await self.buffer_system.write_buffer('short_term_memory', 'recent_inputs', 
                                                  f'input_{i}', append=True)
        
        buffer_content = await self.buffer_system.read_buffer('short_term_memory')
        
        # 验证长度不超过最大值
        assert len(buffer_content['recent_inputs']) == max_items
        
        # 验证保留的是最新的项目
        last_item = buffer_content['recent_inputs'][-1]
        assert last_item == f'input_{max_items + 9}'
        
        print("✅ 最大项目数限制测试通过")
    
    async def test_exchange_buffers(self):
        """测试缓冲区间交换功能"""
        await self.buffer_system._ensure_initialized()
        
        # 测试正常交换
        test_data = {
            'message': 'test exchange data',
            'timestamp': datetime.now().isoformat()
        }
        
        await self.buffer_system.exchange_buffers(
            'memory_retrieval', 'short_term_memory', 'retrieved_data', test_data
        )
        
        # 验证目标agent收到数据
        target_buffer = await self.buffer_system.read_buffer('short_term_memory')
        assert 'retrieved_data' in target_buffer
        assert target_buffer['retrieved_data'][-1] == test_data
        
        # 验证交换记录
        assert 'recent_exchanges' in target_buffer
        assert len(target_buffer['recent_exchanges']) > 0
        
        exchange_record = target_buffer['recent_exchanges'][-1]
        assert exchange_record['source'] == 'memory_retrieval'
        assert exchange_record['target'] == 'short_term_memory'
        assert exchange_record['data_key'] == 'retrieved_data'
        
        print("✅ 缓冲区交换测试通过")
    
    async def test_duplicate_exchange_prevention(self):
        """测试重复交换防护"""
        await self.buffer_system._ensure_initialized()
        
        test_data = {'unique': 'test data for duplication'}
        
        # 执行相同的交换两次
        await self.buffer_system.exchange_buffers(
            'memory_retrieval', 'short_term_memory', 'duplicate_test', test_data
        )
        await self.buffer_system.exchange_buffers(
            'memory_retrieval', 'short_term_memory', 'duplicate_test', test_data
        )
        
        target_buffer = await self.buffer_system.read_buffer('short_term_memory')
        
        # 第二次交换应该被跳过，所以只有一条记录
        duplicate_data_count = sum(1 for item in target_buffer.get('duplicate_test', []) 
                                   if item == test_data)
        assert duplicate_data_count == 1
        
        print("✅ 重复交换防护测试通过")
    
    async def test_clear_buffer(self):
        """测试清空缓冲功能"""
        await self.buffer_system._ensure_initialized()
        
        # 先添加一些数据
        await self.buffer_system.write_buffer('short_term_memory', 'test_data', 'some value')
        await self.buffer_system.write_buffer('short_term_memory', 'recent_inputs', 
                                              'input1', append=True)
        
        # 清空缓冲
        await self.buffer_system.clear_buffer('short_term_memory')
        
        # 验证缓冲被重置为默认结构
        buffer_content = await self.buffer_system.read_buffer('short_term_memory')
        
        # 检查默认字段存在
        expected_fields = self.buffer_system.agent_buffers['short_term_memory']['structure'].keys()
        for field in expected_fields:
            assert field in buffer_content
        
        # 检查自定义数据被清除
        assert 'test_data' not in buffer_content
        
        # 检查列表字段被重置为空
        assert buffer_content['recent_inputs'] == []
        
        print("✅ 清空缓冲测试通过")
    
    async def test_get_agent_status(self):
        """测试获取agent状态功能"""
        await self.buffer_system._ensure_initialized()
        
        # 添加一些数据来测试状态
        await self.buffer_system.write_buffer('short_term_memory', 'recent_inputs', 
                                              'input1', append=True)
        await self.buffer_system.write_buffer('short_term_memory', 'recent_inputs', 
                                              'input2', append=True)
        
        status = await self.buffer_system.get_agent_status('short_term_memory')
        
        assert 'agent_id' in status
        assert 'agent_name' in status
        assert 'brain_region' in status
        assert 'buffer_size' in status
        assert 'last_updated' in status
        assert 'file_size' in status
        
        assert status['agent_id'] == 'short_term_memory'
        assert status['buffer_size'] > 0  # 应该有数据
        
        print("✅ 获取agent状态测试通过")
    
    async def test_get_all_buffers_status(self):
        """测试获取所有缓冲状态功能"""
        await self.buffer_system._ensure_initialized()
        
        all_status = await self.buffer_system.get_all_buffers_status()
        
        assert isinstance(all_status, dict)
        
        # 检查所有agent都有状态
        expected_agents = list(self.buffer_system.agent_buffers.keys())
        for agent_id in expected_agents:
            assert agent_id in all_status
            
        print("✅ 获取所有缓冲状态测试通过")
    
    async def test_save_user_preference(self):
        """测试保存用户偏好功能"""
        await self.buffer_system._ensure_initialized()
        
        preference_data = {
            'drink': 'green tea',
            'time': '3:00 PM daily'
        }
        
        await self.buffer_system.save_user_preference('beverage_preference', preference_data)
        
        # 验证偏好被保存到long_term_memory
        buffer_content = await self.buffer_system.read_buffer('long_term_memory')
        assert 'user_preferences' in buffer_content
        assert len(buffer_content['user_preferences']) > 0
        
        latest_preference = buffer_content['user_preferences'][-1]
        assert latest_preference['type'] == 'beverage_preference'
        assert latest_preference['data'] == preference_data
        
        print("✅ 保存用户偏好测试通过")
    
    async def test_concurrent_access(self):
        """测试并发访问安全性"""
        await self.buffer_system._ensure_initialized()
        
        # 创建多个并发写入任务
        async def write_task(task_id):
            for i in range(10):
                await self.buffer_system.write_buffer(
                    'short_term_memory', 
                    'recent_inputs',
                    f'task_{task_id}_input_{i}',
                    append=True
                )
        
        # 并发执行多个写入任务
        tasks = [write_task(i) for i in range(5)]
        await asyncio.gather(*tasks)
        
        # 验证所有数据都被正确写入
        buffer_content = await self.buffer_system.read_buffer('short_term_memory')
        
        # 应该有5个任务 × 10个输入 = 50个项目（或受限于max_items）
        max_items = self.buffer_system.agent_buffers['short_term_memory']['max_items']
        expected_count = min(50, max_items)
        
        assert len(buffer_content['recent_inputs']) == expected_count
        
        print("✅ 并发访问安全性测试通过")

    @pytest.mark.asyncio 
    async def test_error_handling(self):
        """测试错误处理"""
        await self.buffer_system._ensure_initialized()
        
        # 测试损坏的JSON文件恢复
        agent_id = 'short_term_memory'
        buffer_path = self.buffer_system.buffer_dir / self.buffer_system.agent_buffers[agent_id]['buffer_file']
        
        # 故意损坏JSON文件
        with open(buffer_path, 'w', encoding='utf-8') as f:
            f.write("invalid json content {{{")
        
        # 读取应该触发重新初始化
        buffer_content = await self.buffer_system.read_buffer(agent_id)
        
        # 应该恢复到默认结构
        expected_structure = self.buffer_system.agent_buffers[agent_id]['structure']
        for key in expected_structure:
            assert key in buffer_content
            
        print("✅ 错误处理测试通过")


async def run_all_tests():
    """运行所有测试"""
    print("🧪 开始AgentBufferSystem单元测试...")
    
    test_instance = TestAgentBufferSystem()
    
    tests = [
        test_instance.test_initialization,
        test_instance.test_buffer_creation,
        test_instance.test_read_buffer,
        test_instance.test_write_buffer,
        test_instance.test_append_logic,
        test_instance.test_max_items_limit,
        test_instance.test_exchange_buffers,
        test_instance.test_duplicate_exchange_prevention,
        test_instance.test_clear_buffer,
        test_instance.test_get_agent_status,
        test_instance.test_get_all_buffers_status,
        test_instance.test_save_user_preference,
        test_instance.test_concurrent_access,
        test_instance.test_error_handling
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_instance.setup_method()
            await test_func()
            test_instance.teardown_method()
            passed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} 失败: {e}")
            failed += 1
            test_instance.teardown_method()
    
    print(f"\n🎉 测试完成！通过: {passed}, 失败: {failed}")
    return failed == 0


if __name__ == "__main__":
    result = asyncio.run(run_all_tests())
    exit(0 if result else 1)
