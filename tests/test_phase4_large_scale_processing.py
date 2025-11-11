"""
Phase 4: 大规模文档处理测试
Tests for Large-scale Document Processing

测试内容:
1. 工作记忆压缩 (compress_working_memory)
2. 分层处理 (hierarchical_process_documents)
3. 增量摄入 (ingest_documents_incrementally)
4. 懒加载 (lazy_load_document)
5. 端到端集成测试
"""

import pytest
import pytest_asyncio
import asyncio
import logging
from datetime import datetime
from typing import Dict, List

from src.agents.brain_regions.prefrontal_agent import PrefrontalAgent
from src.systems.external_memory_system import ExternalMemorySystem
from src.services.openai_embedding_service import OpenAIEmbeddingService
from src.utils.knowledge_graph_builder import KnowledgeGraphBuilder

from openai import AsyncOpenAI
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest_asyncio.fixture
async def prefrontal_agent():
    """创建PrefrontalAgent实例"""
    client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    agent = PrefrontalAgent(capacity=10, client=client)
    return agent


@pytest_asyncio.fixture
async def external_memory():
    """创建ExternalMemorySystem实例"""
    client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    embedding_service = OpenAIEmbeddingService(use_cache=True)
    kg_builder = KnowledgeGraphBuilder(llm_client=client)

    system = ExternalMemorySystem(
        embedding_service=embedding_service,
        kg_builder=kg_builder
    )
    return system


# ============================================================
# Test 1: 工作记忆压缩 (Working Memory Compression)
# ============================================================

@pytest.mark.asyncio
async def test_working_memory_compression(prefrontal_agent):
    """
    测试工作记忆压缩功能

    场景: 100个facts → 7个slots
    验证: 压缩比、聚类效果、摘要质量
    """
    logger.info("\n" + "="*60)
    logger.info("Test 1: Working Memory Compression")
    logger.info("="*60)

    # 准备100个模拟facts (分为几个主题)
    facts = []

    # 主题1: AI研究 (30个facts)
    for i in range(30):
        facts.append({
            'content': f"Artificial Intelligence research finding {i}: neural networks show improved performance on task {i}",
            'topic': 'AI'
        })

    # 主题2: 气候变化 (25个facts)
    for i in range(25):
        facts.append({
            'content': f"Climate change observation {i}: temperature increase of {0.1*i}°C in region {i}",
            'topic': 'climate'
        })

    # 主题3: 经济数据 (20个facts)
    for i in range(20):
        facts.append({
            'content': f"Economic indicator {i}: GDP growth rate {2+0.1*i}% in quarter {i}",
            'topic': 'economy'
        })

    # 主题4: 医疗进展 (25个facts)
    for i in range(25):
        facts.append({
            'content': f"Medical breakthrough {i}: new treatment shows {80+i}% efficacy for disease {i}",
            'topic': 'medicine'
        })

    logger.info(f"📊 Input: {len(facts)} facts across 4 topics")

    # 执行压缩 (不使用LLM,避免API调用过多)
    result = await prefrontal_agent.compress_working_memory(
        information=facts,
        target_slots=7,
        use_llm=False  # 使用规则压缩避免慢速
    )

    # 验证结果
    assert 'compressed_info' in result
    assert 'compression_ratio' in result
    assert 'cluster_count' in result

    compressed_slots = result['compressed_info']
    compression_ratio = result['compression_ratio']

    logger.info(f"✅ Compressed: {len(facts)} → {len(compressed_slots)} slots")
    logger.info(f"✅ Compression ratio: {compression_ratio:.1f}x")
    logger.info(f"✅ Cluster count: {result['cluster_count']}")

    # 断言: 压缩后不超过7个slots
    assert len(compressed_slots) <= 7, f"Expected ≤7 slots, got {len(compressed_slots)}"

    # 断言: 压缩比应该较高
    assert compression_ratio > 10, f"Expected compression ratio >10x, got {compression_ratio:.1f}x"

    # 检查每个slot的结构
    for slot in compressed_slots:
        assert 'cluster_id' in slot
        assert 'summary' in slot
        assert 'item_count' in slot
        assert 'importance' in slot
        logger.info(f"   Slot {slot['cluster_id']}: {slot['item_count']} items, importance={slot['importance']:.2f}")

    logger.info("✅ Test 1 PASSED: Working memory compression successful")


# ============================================================
# Test 2: 分层处理 (Hierarchical Processing)
# ============================================================

@pytest.mark.asyncio
async def test_hierarchical_processing(external_memory, prefrontal_agent):
    """
    测试分层处理大规模文档

    场景: 10篇模拟论文 → 分块 → key points → 7个summaries
    验证: 分块数量、key points提取、最终压缩
    """
    logger.info("\n" + "="*60)
    logger.info("Test 2: Hierarchical Document Processing")
    logger.info("="*60)

    # 准备10篇模拟论文 (每篇5000字符)
    documents = []
    for i in range(10):
        content = f"""
        Paper {i}: Research on Topic {i % 3}

        Abstract: This paper investigates topic {i % 3} with focus on aspect {i}.
        We conducted experiments with {100 + i*10} participants over {12 + i} months.

        Introduction: Previous research has shown that topic {i % 3} is important.
        Our hypothesis is that aspect {i} plays a crucial role in understanding the phenomenon.

        Methodology: We used experimental design {i} with control group {i}.
        Data was collected using instrument {i} with accuracy {95 + i*0.1}%.

        Results: We found significant correlation (p<0.01) between variable {i} and outcome {i}.
        Effect size was measured at Cohen's d = {0.5 + i*0.1}.

        Discussion: These findings suggest that aspect {i} of topic {i % 3} is critical.
        Implications for practice include consideration {i} and application {i}.

        Conclusion: Our research contributes to understanding of topic {i % 3}.
        Future work should explore dimension {i+1} and context {i+1}.
        """ * 5  # 重复5次达到约5000字符

        documents.append({
            'title': f"Paper_{i}_Topic_{i % 3}",
            'content': content
        })

    logger.info(f"📚 Input: {len(documents)} papers (~{sum(len(d['content']) for d in documents):,} characters)")

    # 执行分层处理
    result = await external_memory.hierarchical_process_documents(
        documents=documents,
        target_summaries=7,
        prefrontal_agent=prefrontal_agent
    )

    # 验证结果
    assert 'summaries' in result
    assert 'key_points' in result
    assert 'total_chunks' in result
    assert 'compression_ratio' in result

    summaries = result['summaries']
    key_points = result['key_points']
    total_chunks = result['total_chunks']
    compression_ratio = result['compression_ratio']

    logger.info(f"✅ Step 1: {len(documents)} papers → {total_chunks} chunks")
    logger.info(f"✅ Step 2: {total_chunks} chunks → {len(key_points)} key points")
    logger.info(f"✅ Step 3: {len(key_points)} key points → {len(summaries)} summaries")
    logger.info(f"✅ Overall compression: {compression_ratio:.1f}x in {result['processing_time_ms']:.0f}ms")

    # 断言: chunks数量合理 (每篇约5000字符, chunk_size=1000, 所以每篇~5 chunks)
    expected_chunks = len(documents) * 5
    assert 30 <= total_chunks <= 60, f"Expected ~{expected_chunks} chunks, got {total_chunks}"

    # 断言: key points数量 (应该接近chunks数量,因为每个chunk 1个key point)
    assert len(key_points) > 0, "Should extract key points"

    # 断言: 最终summaries不超过7个
    assert len(summaries) <= 7, f"Expected ≤7 summaries, got {len(summaries)}"

    # 检查summary结构
    for summary in summaries:
        assert 'cluster_id' in summary or 'content' in summary
        logger.info(f"   Summary: {str(summary)[:100]}...")

    logger.info("✅ Test 2 PASSED: Hierarchical processing successful")


# ============================================================
# Test 3: 增量摄入 (Incremental Ingestion)
# ============================================================

@pytest.mark.asyncio
async def test_incremental_ingestion(external_memory):
    """
    测试增量摄入文档

    场景: 10篇论文分3批摄入 (batch_size=3)
    验证: 批次数量、摄入成功率、时间控制
    """
    logger.info("\n" + "="*60)
    logger.info("Test 3: Incremental Document Ingestion")
    logger.info("="*60)

    # 准备10篇文档
    documents = []
    for i in range(10):
        documents.append({
            'title': f"Document_{i}",
            'content': f"This is document {i} about topic {i % 3}. " * 100,  # ~1000字符
            'metadata': {'index': i, 'topic': i % 3}
        })

    logger.info(f"📚 Input: {len(documents)} documents to ingest incrementally")

    # 执行增量摄入 (batch_size=3)
    result = await external_memory.ingest_documents_incrementally(
        document_list=documents,
        batch_size=3,
        delay_between_batches=0.05  # 50ms延迟
    )

    # 验证结果
    assert 'ingested_count' in result
    assert 'failed_count' in result
    assert 'batch_count' in result
    assert 'total_time_ms' in result

    ingested_count = result['ingested_count']
    failed_count = result['failed_count']
    batch_count = result['batch_count']

    logger.info(f"✅ Ingested: {ingested_count}/{len(documents)} documents")
    logger.info(f"✅ Failed: {failed_count}")
    logger.info(f"✅ Batches: {batch_count} (batch_size=3)")
    logger.info(f"✅ Time: {result['total_time_ms']:.0f}ms")

    # 断言: 应该全部成功摄入
    assert ingested_count == len(documents), f"Expected {len(documents)} ingested, got {ingested_count}"
    assert failed_count == 0, f"Expected 0 failures, got {failed_count}"

    # 断言: 批次数量 (10篇, batch_size=3, 应该是4个batch)
    expected_batches = (len(documents) + 2) // 3  # ceiling division
    assert batch_count == expected_batches, f"Expected {expected_batches} batches, got {batch_count}"

    # 验证文档确实被存储
    stats = external_memory.get_statistics()
    logger.info(f"✅ Storage stats: {stats['documents']} documents, {stats['total_chunks']} chunks")

    assert stats['documents'] >= len(documents), "Documents should be stored"

    logger.info("✅ Test 3 PASSED: Incremental ingestion successful")


# ============================================================
# Test 4: 懒加载 (Lazy Loading)
# ============================================================

@pytest.mark.asyncio
async def test_lazy_loading(external_memory):
    """
    测试按需懒加载文档

    场景: 根据query相关性决定是否加载文档
    验证: 高相关性加载, 低相关性跳过
    """
    logger.info("\n" + "="*60)
    logger.info("Test 4: Lazy Loading Documents")
    logger.info("="*60)

    # 先摄入3篇文档
    doc_ids = []
    for i in range(3):
        doc_id = await external_memory.ingest_document(
            title=f"LazyDoc_{i}",
            content=f"Content of document {i} about topic {i}" * 50,
            metadata={'index': i}
        )
        doc_ids.append(doc_id)

    logger.info(f"📚 Prepared {len(doc_ids)} documents for lazy loading")

    # 测试高相关性 (应该加载)
    doc_high = await external_memory.lazy_load_document(
        document_id=doc_ids[0],
        query_relevance=0.8
    )

    assert doc_high is not None, "High relevance document should be loaded"
    logger.info(f"✅ Loaded high-relevance document: {doc_high.title} (relevance=0.8)")

    # 测试低相关性 (应该跳过)
    doc_low = await external_memory.lazy_load_document(
        document_id=doc_ids[1],
        query_relevance=0.2
    )

    assert doc_low is None, "Low relevance document should not be loaded"
    logger.info(f"✅ Skipped low-relevance document (relevance=0.2)")

    # 测试边界情况 (0.5)
    doc_border = await external_memory.lazy_load_document(
        document_id=doc_ids[2],
        query_relevance=0.5
    )

    logger.info(f"✅ Border case (relevance=0.5): {'Loaded' if doc_border else 'Skipped'}")

    logger.info("✅ Test 4 PASSED: Lazy loading successful")


# ============================================================
# Test 5: 端到端集成测试 (End-to-End Integration)
# ============================================================

@pytest.mark.asyncio
async def test_phase4_integration(external_memory, prefrontal_agent):
    """
    端到端集成测试: 大规模文档处理完整流程

    场景:
    1. 增量摄入10篇论文
    2. 分层处理 → 7个summaries
    3. 压缩到工作记忆 (7 slots)
    4. 验证完整流程

    对应ROADMAP场景2: 单次大规模文本 (10篇论文/8本书)
    """
    logger.info("\n" + "="*60)
    logger.info("Test 5: Phase 4 End-to-End Integration")
    logger.info("="*60)

    # Step 1: 增量摄入10篇论文
    documents = []
    for i in range(10):
        documents.append({
            'title': f"Research_Paper_{i}",
            'content': f"""
            Title: Advanced Research on Topic {i % 3}

            This paper explores the fundamental aspects of topic {i % 3}.
            Our research methodology includes {i+5} different experimental setups.
            We collected data from {100*i} participants across {i+1} different locations.

            Key findings:
            1. Finding {i}: Significant correlation with factor {i}
            2. Finding {i+1}: Moderate effect size in condition {i}
            3. Finding {i+2}: Unexpected results in scenario {i}

            Conclusion: Topic {i % 3} requires further investigation.
            """ * 20  # 重复达到合理长度
        })

    # 增量摄入
    ingest_result = await external_memory.ingest_documents_incrementally(
        document_list=documents,
        batch_size=3,
        delay_between_batches=0.05
    )

    logger.info(f"📚 Step 1: Ingested {ingest_result['ingested_count']} documents in {ingest_result['batch_count']} batches")

    # Step 2: 分层处理
    hierarchical_result = await external_memory.hierarchical_process_documents(
        documents=documents,
        target_summaries=7,
        prefrontal_agent=prefrontal_agent
    )

    logger.info(f"🔍 Step 2: Hierarchical processing → {len(hierarchical_result['summaries'])} summaries")
    logger.info(f"   Compression: {hierarchical_result['total_chunks']} chunks → {len(hierarchical_result['summaries'])} summaries")

    # Step 3: 压缩到工作记忆
    compression_result = await prefrontal_agent.compress_working_memory(
        information=hierarchical_result['key_points'],
        target_slots=7,
        use_llm=False
    )

    logger.info(f"🧠 Step 3: Compressed to working memory: {len(compression_result['compressed_info'])} slots")

    # 验证完整流程
    assert ingest_result['ingested_count'] == 10, "Should ingest all documents"
    assert len(hierarchical_result['summaries']) <= 7, "Should produce ≤7 summaries"
    assert len(compression_result['compressed_info']) <= 7, "Should compress to ≤7 slots"

    # 计算总体压缩比
    original_chunks = hierarchical_result['total_chunks']
    final_slots = len(compression_result['compressed_info'])
    overall_compression = original_chunks / final_slots if final_slots > 0 else 0

    logger.info(f"\n📊 Overall Results:")
    logger.info(f"   Input: 10 papers")
    logger.info(f"   Chunks: {original_chunks}")
    logger.info(f"   Key points: {len(hierarchical_result['key_points'])}")
    logger.info(f"   Final slots: {final_slots}")
    logger.info(f"   Overall compression: {overall_compression:.1f}x")
    logger.info(f"   符合Miller's 7±2法则: {'✅' if final_slots <= 7 else '❌'}")

    logger.info("\n✅ Test 5 PASSED: Phase 4 integration successful")
    logger.info("="*60)


# ============================================================
# 运行所有测试
# ============================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
