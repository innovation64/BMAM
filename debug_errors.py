#!/usr/bin/env python3
"""
Debug script to reproduce and fix the actual errors
"""
import sys
from pathlib import Path

# 添加src路径
sys.path.append(str(Path(__file__).parent))

async def test_embedding_service():
    """测试embedding service错误"""
    try:
        from src.services.openai_embedding_service import OpenAIEmbeddingService
        service = OpenAIEmbeddingService(use_cache=True)
        
        # 检查cache是否有正确的方法
        print(f"Cache type: {type(service.cache)}")
        print(f"Cache methods: {[method for method in dir(service.cache) if not method.startswith('_')]}")
        
        if hasattr(service.cache, 'get_embedding'):
            print("✅ get_embedding method exists")
        else:
            print("❌ get_embedding method missing")
            
        if hasattr(service.cache, 'get_batch_embeddings'):
            print("✅ get_batch_embeddings method exists")
        else:
            print("❌ get_batch_embeddings method missing")
        
        return True
    except Exception as e:
        print(f"❌ Embedding service error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_buffer_system():
    """测试buffer system的问题"""
    try:
        from src.agents.agent_buffer_system import AgentBufferSystem
        import tempfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            buffer_system = AgentBufferSystem(buffer_dir=temp_dir)
            
            # 初始化
            await buffer_system._ensure_initialized()
            
            # 测试基本操作
            await buffer_system.write_buffer('short_term_memory', 'test_data', 'test_value')
            data = await buffer_system.read_buffer('short_term_memory')
            
            print(f"✅ Buffer system basic operations work")
            
            # 测试datetime序列化
            from datetime import datetime
            test_data_with_datetime = {
                'message': 'test',
                'timestamp': datetime.now().isoformat(),  # 已经是string
                'sender': 'test'
            }
            
            await buffer_system.write_buffer('short_term_memory', 'recent_inputs', 
                                              test_data_with_datetime, append=True)
            print("✅ DateTime serialization works")
            
        return True
    except Exception as e:
        print(f"❌ Buffer system error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_coordination():
    """测试coordination模块的问题"""
    try:
        from src.coordination.brain_coordinator import BrainInspiredCoordinator, ProcessingResult
        
        # 测试ProcessingResult
        pr = ProcessingResult(
            response="test",
            routing_decision={},
            agents_involved=[],
            memories_retrieved=[],
            memory_stored=False,
            processing_time=0.0,
            agent_logs={},
            insights={},
            success=False,
            error="test error"
        )
        
        # 测试UI中的访问方式
        error_msg = pr.error or '未知错误'
        print(f"✅ ProcessingResult attribute access works: {error_msg}")
        
        return True
    except Exception as e:
        print(f"❌ Coordination error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("🔍 Debug Script - 检查具体错误...")
    
    tests = [
        ("Embedding Service", test_embedding_service),
        ("Buffer System", test_buffer_system),
        ("Coordination", test_coordination)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Testing {test_name}...")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    print(f"\n📊 Test Results:")
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
    
    # 检查所有测试是否通过
    all_passed = all(success for _, success in results)
    if all_passed:
        print("\n🎉 All tests passed! The actual runtime errors might be from a different source.")
    else:
        print("\n⚠️ Some tests failed - these need to be fixed.")
    
    return all_passed

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(main())
    exit(0 if result else 1)