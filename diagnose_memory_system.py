#!/usr/bin/env python3
"""
Memory System Diagnosis Tool
记忆系统诊断工具
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.coordination.brain_coordinator import BrainInspiredCoordinator
from src.memory.memory_system import memory_system
from src.services.openai_embedding_service import OpenAIEmbeddingService
from src.utils.config import get_logger

logger = get_logger(__name__)


async def test_openai_connection():
    """Test OpenAI API connection"""
    print("🔌 Testing OpenAI Connection")
    print("-" * 40)

    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ OPENAI_API_KEY not found in environment")
            return False

        print(f"✅ API Key found: {api_key[:20]}...")

        # Test embedding service
        embedding_service = OpenAIEmbeddingService()
        test_text = "This is a test"
        embedding = await embedding_service.encode_text(test_text)

        if embedding is not None:
            print(f"✅ Embedding service working: {len(embedding)} dimensions")
            return True
        else:
            print("❌ Embedding service returned None")
            return False

    except Exception as e:
        print(f"❌ OpenAI connection failed: {e}")
        return False


async def test_memory_storage():
    """Test direct memory storage"""
    print("\n💾 Testing Memory Storage")
    print("-" * 40)

    try:
        # Test direct storage
        memory_id = await memory_system.store_memory(
            content="测试记忆：用户喜欢绿茶",
            importance=0.8,
            context_tags=['test', 'preference'],
            emotion_tags=['positive']
        )

        if memory_id:
            print(f"✅ Memory stored successfully: {memory_id}")
            return memory_id
        else:
            print("❌ Memory storage returned None")
            return None

    except Exception as e:
        print(f"❌ Memory storage failed: {e}")
        return None


async def test_memory_retrieval(memory_id=None):
    """Test memory retrieval"""
    print("\n🔍 Testing Memory Retrieval")
    print("-" * 40)

    try:
        # Test search
        results = await memory_system.search_memories("绿茶", k=5)

        print(f"✅ Search returned {len(results)} results")

        for i, result in enumerate(results):
            print(f"   Result {i+1}: {str(result)[:100]}...")

        return len(results) > 0

    except Exception as e:
        print(f"❌ Memory retrieval failed: {e}")
        return False


async def test_coordinator_memory():
    """Test coordinator memory processing"""
    print("\n🧠 Testing Coordinator Memory Processing")
    print("-" * 40)

    try:
        coordinator = BrainInspiredCoordinator()
        await coordinator.initialize()

        # Test storing preference
        result1 = await coordinator.process_user_input("请记住我喜欢喝绿茶，每天下午3点。")

        print(f"✅ Storage result:")
        print(f"   Success: {result1.success}")
        print(f"   Memory stored: {result1.memory_stored}")
        print(f"   Error: {result1.error}")
        print(f"   Response: {result1.response[:100]}...")

        # Small delay
        await asyncio.sleep(1)

        # Test retrieving
        result2 = await coordinator.process_user_input("我喜欢什么茶？")

        print(f"\n✅ Retrieval result:")
        print(f"   Success: {result2.success}")
        print(f"   Memories found: {len(result2.memories_retrieved)}")
        print(f"   Response: {result2.response[:100]}...")

        await coordinator.stop_system()

        # Check if retrieval worked
        return len(result2.memories_retrieved) > 0 and "绿茶" in result2.response

    except Exception as e:
        print(f"❌ Coordinator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_database_files():
    """Check database files"""
    print("\n📁 Testing Database Files")
    print("-" * 40)

    # Check critical files
    files_to_check = [
        "data/brain_memory.db",
        "data/memory_vectors.index",
        "data/memory_vectors_mappings.json"
    ]

    for file_path in files_to_check:
        path = Path(file_path)
        if path.exists():
            size = path.stat().st_size
            print(f"✅ {file_path}: {size} bytes")
        else:
            print(f"❌ {file_path}: Not found")

    return True


async def test_agent_system():
    """Test individual agents"""
    print("\n🤖 Testing Individual Agents")
    print("-" * 40)

    try:
        coordinator = BrainInspiredCoordinator()
        await coordinator.initialize()

        # Test memory retrieval agent
        from src.agents.base import AgentMessage

        message = AgentMessage(
            sender='test',
            receiver='memory_retrieval',
            message_type='request',
            content={
                'action': 'semantic_search',
                'query': '绿茶',
                'k': 5
            }
        )

        result = await coordinator._activate_agent('memory_retrieval', message)

        print(f"✅ Memory retrieval agent:")
        print(f"   Result: {result}")

        memories = result.get('memories', [])
        print(f"   Found {len(memories)} memories")

        await coordinator.stop_system()
        return True

    except Exception as e:
        print(f"❌ Agent test failed: {e}")
        return False


async def main():
    """Run all diagnostic tests"""
    print("🚀 Memory System Diagnostic Tool")
    print("="*50)

    test_results = []

    # Test 1: OpenAI Connection
    result1 = await test_openai_connection()
    test_results.append(("OpenAI Connection", result1))

    if not result1:
        print("\n❌ Cannot proceed without OpenAI connection")
        return

    # Test 2: Database Files
    result2 = await test_database_files()
    test_results.append(("Database Files", result2))

    # Test 3: Direct Memory Storage
    memory_id = await test_memory_storage()
    test_results.append(("Memory Storage", memory_id is not None))

    # Test 4: Direct Memory Retrieval
    result4 = await test_memory_retrieval(memory_id)
    test_results.append(("Memory Retrieval", result4))

    # Test 5: Agent System
    result5 = await test_agent_system()
    test_results.append(("Agent System", result5))

    # Test 6: Full Coordinator
    result6 = await test_coordinator_memory()
    test_results.append(("Coordinator Integration", result6))

    # Summary
    print("\n" + "="*50)
    print("📊 DIAGNOSTIC RESULTS")
    print("="*50)

    passed = 0
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{len(test_results)} tests passed")

    if passed < len(test_results):
        print("\n🔧 Suggested fixes:")
        for test_name, result in test_results:
            if not result:
                if test_name == "OpenAI Connection":
                    print("   • Check OPENAI_API_KEY in .env file")
                    print("   • Verify API key is valid and has credits")
                elif test_name == "Memory Storage":
                    print("   • Check embedding service configuration")
                    print("   • Verify database permissions")
                elif test_name == "Memory Retrieval":
                    print("   • Check FAISS index integrity")
                    print("   • Verify vector database setup")
                elif test_name == "Coordinator Integration":
                    print("   • Check coordinator memory processing logic")
                    print("   • Verify agent communication")


if __name__ == "__main__":
    asyncio.run(main())