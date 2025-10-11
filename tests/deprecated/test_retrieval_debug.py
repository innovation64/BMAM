import asyncio
import sys
sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')

from src.memory.memory_system import AdvancedMemorySystem
from datetime import datetime

async def test_retrieval():
    memory_system = AdvancedMemorySystem()
    
    # 测试问题
    questions = [
        "When did Caroline go to the LGBTQ support group?",
        "What did Caroline research?",
        "What is Caroline's identity?"
    ]
    
    for q in questions:
        print(f"\n{'='*60}")
        print(f"问题: {q}")
        print(f"{'='*60}")
        
        # 检索记忆
        results = await memory_system.retrieve_memories(
            query=q,
            top_k=10,
            time_range=None
        )
        
        print(f"\n检索到 {len(results)} 条记忆:")
        for i, mem in enumerate(results[:5], 1):
            print(f"\n记忆 {i} (相似度: {mem.get('similarity', 0):.3f}):")
            print(f"  内容: {mem.get('content', '')[:200]}")
            print(f"  时间: {mem.get('timestamp', 'N/A')}")

asyncio.run(test_retrieval())
