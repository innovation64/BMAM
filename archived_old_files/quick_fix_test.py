#!/usr/bin/env python3
"""
快速修复验证 - 测试主要的修复是否成功
"""

import sys
import asyncio
from pathlib import Path

# 添加src路径
sys.path.append(str(Path(__file__).parent))

async def test_basic_fixes():
    """测试基本修复"""
    print("🧪 开始测试主要修复...")
    
    try:
        # 测试1: 检查ProcessingResult类定义
        from src.coordination.brain_coordinator import ProcessingResult
        pr = ProcessingResult(
            response="test",
            routing_decision={},
            agents_involved=[],
            memories_retrieved=[],
            memory_stored=False,
            processing_time=0.0,
            agent_logs={},
            insights={},
            success=True,
            error=None
        )
        
        # 验证属性访问（ui.py修复的关键）
        assert pr.error is None
        assert pr.success is True
        print("✅ ProcessingResult属性访问修复验证通过")
        
        # 测试2: 检查import路径修复
        try:
            from src.coordination.clean_agent_system import _global_semaphore
            print("✅ _global_semaphore 导入路径修复验证通过")
        except ImportError as e:
            print(f"❌ _global_semaphore 导入失败: {e}")
            return False
        
        # 测试3: 检查buffer system的基本结构
        from src.agents.agent_buffer_system import AgentBufferSystem
        
        # 创建临时目录测试
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            buffer_system = AgentBufferSystem(buffer_dir=temp_dir)
            
            # 验证所有agents都有正确的结构定义
            for agent_id, config in buffer_system.agent_buffers.items():
                structure = config['structure']
                
                # 检查修复的字段
                if 'recent_inputs' not in structure:
                    print(f"❌ {agent_id} 缺少 recent_inputs 字段")
                    return False
                if 'recent_outputs' not in structure:
                    print(f"❌ {agent_id} 缺少 recent_outputs 字段")
                    return False
                    
                # 验证字段类型
                if not isinstance(structure['recent_inputs'], list):
                    print(f"❌ {agent_id} 的 recent_inputs 不是列表")
                    return False
                if not isinstance(structure['recent_outputs'], list):
                    print(f"❌ {agent_id} 的 recent_outputs 不是列表")
                    return False
            
            # 检查long_term_memory的user_preferences修复
            ltm_structure = buffer_system.agent_buffers['long_term_memory']['structure']
            if not isinstance(ltm_structure['user_preferences'], list):
                print("❌ long_term_memory 的 user_preferences 不是列表")
                return False
                
            print("✅ AgentBufferSystem 结构修复验证通过")
        
        # 测试4: 检查embedding service的API修复
        from src.services.openai_embedding_service import EmbeddingCache
        
        # 创建临时缓存测试
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = EmbeddingCache(cache_dir=temp_dir)
            
            # 验证修复的方法存在
            if not hasattr(cache, 'get_embedding'):
                print("❌ EmbeddingCache 缺少 get_embedding 方法")
                return False
            if not hasattr(cache, 'get_batch_embeddings'):
                print("❌ EmbeddingCache 缺少 get_batch_embeddings 方法")
                return False
                
            print("✅ EmbeddingCache API修复验证通过")
        
        # 测试5: 检查路径修复
        from src.utils.config import get_absolute_path, get_project_root
        
        project_root = get_project_root()
        abs_path = get_absolute_path("data/test")
        
        # 验证路径是绝对路径
        if not abs_path.is_absolute():
            print("❌ get_absolute_path 没有返回绝对路径")
            return False
            
        print("✅ 路径工具修复验证通过")
        
        print("\n🎉 所有主要修复验证通过！")
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_ui_compatibility():
    """测试UI兼容性"""
    try:
        print("\n🧪 测试UI兼容性...")
        
        # 测试ProcessingResult在UI中的使用
        from src.coordination.brain_coordinator import ProcessingResult
        
        # 模拟ui.py中的错误情况处理
        result = ProcessingResult(
            response="",
            routing_decision={},
            agents_involved=[],
            memories_retrieved=[],
            memory_stored=False,
            processing_time=0.0,
            agent_logs={},
            insights={},
            success=False,
            error="测试错误"
        )
        
        # 模拟ui.py:245的代码
        error_response = f"❌ 处理失败: {result.error or '未知错误'}"
        processing_log = f"❌ 系统错误: {result.error or '未知错误'}"
        
        assert "测试错误" in error_response
        assert "测试错误" in processing_log
        
        print("✅ UI错误处理兼容性验证通过")
        return True
        
    except Exception as e:
        print(f"❌ UI兼容性测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("🚀 开始快速修复验证测试")
    
    success1 = await test_basic_fixes()
    success2 = await test_ui_compatibility()
    
    if success1 and success2:
        print("\n✅ 所有修复验证通过！系统应该可以正常运行了。")
        return True
    else:
        print("\n❌ 仍有问题需要修复")
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)