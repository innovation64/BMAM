"""
Knowledge Graph Test Suite
知识图谱测试套件
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.memory.knowledge_graph import (
    LightweightKnowledgeGraph,
    EntityType,
    RelationType
)
from src.memory.kg_integration import KGMemoryIntegration
from src.memory.memory_system import memory_system


async def test_basic_kg_operations():
    """测试KG基本操作"""
    print("\n" + "="*60)
    print("测试1: KG基本操作")
    print("="*60)

    kg = LightweightKnowledgeGraph(save_dir="data/test_kg")

    # 添加节点
    print("\n添加节点...")
    kg.add_node("person_alice", EntityType.PERSON, "Alice", {"age": 25})
    kg.add_node("person_bob", EntityType.PERSON, "Bob", {"age": 30})
    kg.add_node("concept_ai", EntityType.CONCEPT, "人工智能")
    kg.add_node("concept_ml", EntityType.CONCEPT, "机器学习")

    print(f"✅ 添加了 {kg.stats['total_nodes']} 个节点")

    # 添加边
    print("\n添加关系...")
    kg.add_edge("person_alice", "concept_ai", RelationType.RELATED_TO, 0.9)
    kg.add_edge("person_bob", "concept_ai", RelationType.RELATED_TO, 0.8)
    kg.add_edge("concept_ml", "concept_ai", RelationType.PART_OF, 1.0)

    print(f"✅ 添加了 {kg.stats['total_edges']} 条边")

    # 查询邻居
    print("\n查询Alice的邻居...")
    neighbors = kg.get_neighbors("person_alice")
    print(f"邻居: {neighbors}")

    # 查找路径
    print("\n查找Alice到机器学习的路径...")
    path = kg.find_shortest_path("person_alice", "concept_ml")
    print(f"最短路径: {path}")

    # 计算中心性
    print("\n计算PageRank...")
    pagerank = kg.compute_pagerank()
    for node_id, score in sorted(pagerank.items(), key=lambda x: x[1], reverse=True):
        print(f"  {node_id}: {score:.4f}")

    # 保存
    kg.save_graph()
    print("\n✅ 图已保存")

    return kg


async def test_kg_memory_integration():
    """测试KG与记忆系统集成"""
    print("\n" + "="*60)
    print("测试2: KG与记忆系统集成")
    print("="*60)

    # 记忆系统已经在导入时初始化，无需再次初始化
    # await memory_system.initialize()  # 移除此行

    # 存储测试记忆
    print("\n存储测试记忆...")
    test_memories = [
        "Alice在北京学习人工智能",
        "Bob昨天去了上海参加机器学习会议",
        "机器学习是人工智能的一个重要分支",
        "Alice和Bob一起研究深度学习"
    ]

    memory_ids = []
    for content in test_memories:
        memory_id = await memory_system.store_memory(
            content=content,
            metadata={'source': 'test'}
        )
        memory_ids.append(memory_id)
        print(f"✅ 存储记忆: {memory_id}")

    # 从记忆构建KG
    print("\n从记忆构建知识图谱...")
    from src.memory.kg_integration import kg_integration

    for memory_id in memory_ids:
        result = await kg_integration.build_kg_from_memory(memory_id)
        print(f"记忆 {memory_id}: +{result.get('nodes_added', 0)}节点, "
              f"+{result.get('edges_added', 0)}边")

    # 统计
    stats = kg_integration.kg.get_statistics()
    print(f"\n图统计:")
    print(f"  节点: {stats['basic']['total_nodes']}")
    print(f"  边: {stats['basic']['total_edges']}")

    # 图增强检索
    print("\n测试图增强检索...")
    results = await kg_integration.graph_enhanced_retrieval(
        "Alice学习什么",
        k=5
    )
    print(f"✅ 检索到 {len(results)} 条结果:")
    for i, result in enumerate(results[:3], 1):
        print(f"  {i}. {result.get('content', '')[:50]}...")
        print(f"     来源: {result.get('_source', 'vector_search')}")

    # 查找关联
    if memory_ids:
        print(f"\n查找记忆 {memory_ids[0]} 的关联...")
        associations = await kg_integration.find_memory_associations(
            memory_ids[0],
            max_depth=2
        )

        if associations.get('found'):
            print(f"✅ 相关记忆: {len(associations['related_memories'])}个")
            print(f"✅ 相关实体: {len(associations['related_entities'])}个")
            print(f"✅ 路径数: {len(associations['paths'])}条")

            # 显示实体
            print("\n提取的实体:")
            for entity in associations['related_entities'][:5]:
                print(f"  - {entity['entity']} ({entity['type']})")

    return kg_integration


async def test_graph_algorithms():
    """测试图算法"""
    print("\n" + "="*60)
    print("测试3: 图算法")
    print("="*60)

    kg = LightweightKnowledgeGraph(save_dir="data/test_kg")

    # 加载之前的图
    if kg.stats['total_nodes'] == 0:
        print("图为空，跳过测试")
        return

    print(f"\n当前图: {kg.stats['total_nodes']}节点, {kg.stats['total_edges']}边")

    # 社区检测
    print("\n社区检测...")
    communities = kg.detect_communities()
    print(f"✅ 检测到 {len(communities)} 个社区:")
    for i, community in enumerate(communities, 1):
        print(f"  社区{i}: {len(community)}个节点")
        # 显示社区成员
        for node_id in list(community)[:5]:
            node = kg.get_node(node_id)
            if node:
                print(f"    - {node.content}")

    # 中心性分析
    print("\n中心性分析...")
    centrality = kg.compute_centrality()

    print("\n度中心性Top 5:")
    for node_id, degree in sorted(
        centrality.get('degree', {}).items(),
        key=lambda x: x[1], reverse=True
    )[:5]:
        node = kg.get_node(node_id)
        content = node.content if node else node_id
        print(f"  {content}: {degree}")

    # PageRank
    if 'pagerank' in centrality:
        print("\nPageRank Top 5:")
        for node_id, score in sorted(
            centrality['pagerank'].items(),
            key=lambda x: x[1], reverse=True
        )[:5]:
            node = kg.get_node(node_id)
            content = node.content if node else node_id
            print(f"  {content}: {score:.4f}")

    # 上下文扩展
    print("\n上下文扩展测试...")
    if kg.nodes:
        first_node = list(kg.nodes.keys())[0]
        context = kg.expand_context(first_node, depth=2)
        print(f"✅ 从 {first_node} 扩展得到 {len(context)} 个节点")

    return kg


async def test_kg_export():
    """测试图导出"""
    print("\n" + "="*60)
    print("测试4: 图导出和持久化")
    print("="*60)

    kg = LightweightKnowledgeGraph(save_dir="data/test_kg")

    if kg.stats['total_nodes'] == 0:
        print("图为空，跳过测试")
        return

    # 导出JSON
    output_path = "data/test_kg/export.json"
    kg.export_to_json(output_path)
    print(f"✅ 导出到: {output_path}")

    # 获取统计
    stats = kg.get_statistics()
    print("\n图属性:")
    print(f"  连通性: {stats['graph_properties']['is_connected']}")
    print(f"  连通分量数: {stats['graph_properties']['num_components']}")
    print(f"  密度: {stats['graph_properties']['density']:.4f}")
    print(f"  平均度: {stats['graph_properties']['avg_degree']:.2f}")

    return stats


async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🧠 BMAM 知识图谱测试套件")
    print("="*60)

    try:
        # 测试1: 基本操作
        kg = await test_basic_kg_operations()

        # 测试2: 记忆集成
        kg_integration = await test_kg_memory_integration()

        # 测试3: 图算法
        await test_graph_algorithms()

        # 测试4: 导出
        stats = await test_kg_export()

        print("\n" + "="*60)
        print("✅ 所有测试完成!")
        print("="*60)

        print("\n📊 最终统计:")
        print(f"  节点数: {kg.stats['total_nodes']}")
        print(f"  边数: {kg.stats['total_edges']}")
        print(f"  实体类型: {len(kg.stats['entity_types'])}")
        print(f"  关系类型: {len(kg.stats['relation_types'])}")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 清理 (记忆系统无需手动关闭)
        pass


if __name__ == "__main__":
    asyncio.run(main())