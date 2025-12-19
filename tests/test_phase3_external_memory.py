"""
Phase 3 测试: 外部记忆系统 (External Memory System)
Test External Memory System Integration

测试内容:
1. NotebookStore - 笔记本功能
2. DocumentStore - 文档摄入
3. KnowledgeGraphBuilder - 实体关系提取
4. ExternalMemorySystem - 统一搜索
5. BrainCoordinator Integration - 完整集成
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set environment variable to enable external memory
os.environ['USE_EXTERNAL_MEMORY'] = 'true'

from src.systems.external_memory_system import ExternalMemorySystem, NotebookStore, DocumentStore
from src.utils.knowledge_graph_builder import KnowledgeGraphBuilder
from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator


async def test_notebook_store():
    """测试笔记本存储"""
    print("\n" + "=" * 80)
    print("TEST 1: NotebookStore (笔记本存储)")
    print("=" * 80)

    notebook = NotebookStore()

    # 添加笔记
    note1_id = await notebook.add_note(
        title="Caroline's Profile",
        content="Caroline is a therapist specializing in LGBTQ counseling. She attended a support group recently.",
        metadata={'category': 'profile'}
    )

    note2_id = await notebook.add_note(
        title="Research Notes",
        content="Caroline researched adoption agencies last week.",
        metadata={'category': 'research'}
    )

    print(f"✅ Added 2 notes: {note1_id[:8]}..., {note2_id[:8]}...")

    # 搜索笔记
    results = await notebook.search_notes("Caroline therapist", k=5)

    print(f"✅ Search Results:")
    print(f"   Query: 'Caroline therapist'")
    print(f"   Found: {len(results)} notes")
    for i, note in enumerate(results, 1):
        print(f"   {i}. {note.title}: {note.content[:50]}...")

    return len(results) >= 1  # Pass if at least 1 result


async def test_document_store():
    """测试文档存储"""
    print("\n" + "=" * 80)
    print("TEST 2: DocumentStore (文档存储)")
    print("=" * 80)

    doc_store = DocumentStore(embedding_service=None)  # 不使用embedding

    # 添加文档
    doc_content = """
    Caroline is a 35-year-old therapist who specializes in LGBTQ counseling.
    She has been working in this field for 8 years.
    Recently, Caroline attended an LGBTQ support group to better understand her clients' experiences.
    She is also researching adoption agencies as she plans to adopt a child in the future.
    Caroline is passionate about helping marginalized communities and creating safe spaces for her clients.
    """

    doc_id = await doc_store.add_document(
        title="Caroline's Professional Background",
        content=doc_content,
        metadata={'author': 'Test', 'year': 2025}
    )

    print(f"✅ Document added: {doc_id[:8]}...")

    # 获取文档
    doc = doc_store.get_document(doc_id)
    print(f"   Chunks: {len(doc.chunks) if doc.chunks else 0}")
    print(f"   Content length: {len(doc.content)} characters")

    # 搜索文档 (keyword-based)
    results = await doc_store.search_documents("LGBTQ therapist", k=5, use_embedding=False)

    print(f"✅ Search Results:")
    print(f"   Found: {len(results)} results")
    if results:
        print(f"   Top result: {results[0]['document'].title}")
        print(f"   Relevance: {results[0]['relevance']}")

    return len(results) >= 1  # Pass if at least 1 result


async def test_knowledge_graph_builder():
    """测试知识图谱构建"""
    print("\n" + "=" * 80)
    print("TEST 3: KnowledgeGraphBuilder (知识图谱构建)")
    print("=" * 80)

    kg_builder = KnowledgeGraphBuilder(llm_client=None)  # 不使用LLM

    text = """
    Caroline is a therapist.
    Caroline works as a counselor for LGBTQ clients.
    Caroline attended an LGBTQ support group.
    Caroline researched adoption agencies.
    """

    # 提取实体和关系
    entities, relations = await kg_builder.extract_from_text(text, use_llm=False)

    print(f"✅ Extraction Results:")
    print(f"   Entities: {len(entities)}")
    for entity in entities[:5]:
        print(f"      - {entity['name']} (mentions: {entity.get('mentions', 0)})")

    print(f"   Relations: {len(relations)}")
    for relation in relations[:5]:
        print(f"      - {relation['source']} --[{relation['relation']}]--> {relation['target']}")

    # 添加到图谱
    kg_builder.add_to_graph(entities, relations)

    stats = kg_builder.get_statistics()
    print(f"✅ KG Statistics:")
    print(f"   Total entities: {stats['total_entities']}")
    print(f"   Total relations: {stats['total_relations']}")

    return len(entities) >= 1 and len(relations) >= 1  # Pass if extracted something


async def test_external_memory_system():
    """测试外部记忆系统整合"""
    print("\n" + "=" * 80)
    print("TEST 4: ExternalMemorySystem (外部记忆系统整合)")
    print("=" * 80)

    # 初始化
    external_memory = ExternalMemorySystem(
        embedding_service=None,
        kg_builder=KnowledgeGraphBuilder(llm_client=None),
        search_api_key=None
    )

    # 添加笔记
    note_id = await external_memory.add_note(
        title="Quick Note",
        content="Caroline is interested in adoption",
        metadata={}
    )
    print(f"✅ Added note: {note_id[:8]}...")

    # 摄入文档
    doc_id = await external_memory.ingest_document(
        title="Research Paper",
        content="Caroline is a therapist specializing in LGBTQ counseling. She attended support groups.",
        metadata={'type': 'paper'},
        extract_kg=True
    )
    print(f"✅ Ingested document: {doc_id[:8]}...")

    # 统一搜索
    results = await external_memory.search(
        query="Caroline therapist",
        sources=['notebook', 'documents'],
        k=10
    )

    print(f"✅ Unified Search Results:")
    for source, items in results.items():
        print(f"   {source}: {len(items)} results")

    # 统计信息
    stats = external_memory.get_statistics()
    print(f"✅ System Statistics:")
    print(f"   Notebook notes: {stats['notebook_notes']}")
    print(f"   Documents: {stats['documents']}")
    print(f"   Total chunks: {stats['total_chunks']}")

    total_results = sum(len(v) for v in results.values())
    return total_results >= 1  # Pass if any results


async def test_brain_coordinator_integration():
    """测试BrainCoordinator集成"""
    print("\n" + "=" * 80)
    print("TEST 5: BrainCoordinator Integration (完整集成)")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # 检查外部记忆系统是否已启用
    if not coordinator.external_memory:
        print("⚠️  ExternalMemorySystem not enabled (USE_EXTERNAL_MEMORY=true required)")
        await coordinator.stop_system()
        return False

    print(f"✅ ExternalMemorySystem: enabled")

    # Test 1: 添加笔记
    note_id = await coordinator.add_external_note(
        title="Caroline's Background",
        content="Caroline is a therapist who helps LGBTQ clients",
        metadata={}
    )
    print(f"✅ Added external note: {note_id[:8] if note_id else 'N/A'}...")

    # Test 2: 摄入文档
    doc_result = await coordinator.ingest_external_document(
        title="Caroline's Profile",
        content="""
        Caroline is a 35-year-old therapist specializing in LGBTQ counseling.
        She attended an LGBTQ support group last month to understand her clients better.
        She is also researching adoption agencies for her future plans.
        Caroline has been working as a therapist for 8 years.
        """,
        metadata={'type': 'profile'}
    )

    print(f"✅ Document ingested:")
    print(f"   Document ID: {doc_result.get('document_id', 'N/A')[:8]}...")
    print(f"   Chunks: {doc_result.get('chunks_count', 0)}")
    print(f"   Entities: {doc_result.get('entities_extracted', 0)}")
    print(f"   Relations: {doc_result.get('relations_extracted', 0)}")

    # Test 3: 搜索外部记忆
    search_results = await coordinator.search_external_memory(
        query="Caroline therapist LGBTQ",
        sources=['notebook', 'documents'],
        k=5
    )

    print(f"✅ External memory search:")
    total_results = 0
    for source, items in search_results.items():
        print(f"   {source}: {len(items)} results")
        total_results += len(items)

    # Test 4: 跨时空推理 (集成外部记忆)
    print(f"\n✅ Testing cross-temporal reasoning with external memory...")

    # 先存储一些内部记忆
    from src.agents.base import AgentMessage
    await coordinator.short_term_memory.process_message(AgentMessage(
        sender='test',
        receiver='short_term_memory',
        message_type='request',
        content={
            'action': 'store',
            'content': 'Caroline mentioned wanting to adopt a child',
            'metadata': {}
        }
    ))

    # 执行跨时空推理 (会自动触发外部搜索如果置信度低)
    reasoning_result = await coordinator.cross_time_cross_text_reasoning(
        query="What is Caroline's profession and future plans?"
    )

    print(f"✅ Cross-temporal reasoning result:")
    print(f"   Answer: {reasoning_result.get('answer', 'N/A')[:100]}...")
    print(f"   Confidence: {reasoning_result.get('confidence', 0):.2f}")
    print(f"   Sources used: {reasoning_result.get('sources_used', [])}")
    print(f"   Processing time: {reasoning_result.get('processing_time_ms', 0):.1f}ms")

    await coordinator.stop_system()

    return doc_result.get('status') == 'success' and total_results >= 1


async def main():
    """运行所有Phase 3测试"""
    print("\n" + "🌐" * 40)
    print("PHASE 3 TESTING: External Memory System")
    print("🌐" * 40)

    tests = [
        ("NotebookStore", test_notebook_store),
        ("DocumentStore", test_document_store),
        ("KnowledgeGraphBuilder", test_knowledge_graph_builder),
        ("ExternalMemorySystem", test_external_memory_system),
        ("BrainCoordinator Integration", test_brain_coordinator_integration)
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            passed = await test_func()
            results[test_name] = "✅ PASSED" if passed else "⚠️ PARTIAL"
        except Exception as e:
            results[test_name] = f"❌ FAILED: {str(e)}"
            import traceback
            print(f"\nError traceback:\n{traceback.format_exc()}")

    # 总结
    print("\n" + "=" * 80)
    print("PHASE 3 TEST SUMMARY")
    print("=" * 80)

    for test_name, result in results.items():
        print(f"{result}: {test_name}")

    passed_count = sum(1 for r in results.values() if "PASSED" in r)
    total_count = len(results)

    print(f"\n总计: {passed_count}/{total_count} 测试通过")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
