"""
测试KG与UI集成
"""

import asyncio
from src.memory.knowledge_graph import knowledge_graph
from src.memory.kg_integration import kg_integration
from src.memory.memory_system import memory_system

async def test_kg_ui():
    """测试KG UI集成"""

    print("=" * 60)
    print("测试 KG-UI 集成")
    print("=" * 60)

    # 测试1: 添加测试数据到KG
    print("\n📊 测试1: 添加测试数据到知识图谱")

    # 添加一些测试节点
    knowledge_graph.add_node("person_test", "person", "测试用户", properties={"age": 25})
    knowledge_graph.add_node("concept_ai", "concept", "人工智能", properties={})
    knowledge_graph.add_node("concept_kg", "concept", "知识图谱", properties={})

    # 添加边
    knowledge_graph.add_edge("person_test", "concept_ai", "related_to", strength=0.9)
    knowledge_graph.add_edge("person_test", "concept_kg", "related_to", strength=0.8)
    knowledge_graph.add_edge("concept_kg", "concept_ai", "part_of", strength=1.0)

    print("✅ 添加了3个节点和3条边")

    # 测试2: 获取统计信息
    print("\n📊 测试2: 获取知识图谱统计信息")

    stats = knowledge_graph.get_statistics()
    basic = stats.get('basic', {})

    print(f"  节点总数: {basic.get('total_nodes', 0)}")
    print(f"  边总数: {basic.get('total_edges', 0)}")
    print(f"  实体类型: {basic.get('entity_types', {})}")
    print(f"  关系类型: {basic.get('relation_types', {})}")

    # 测试3: 从UI模块导入并测试
    print("\n📊 测试3: 测试UI模块的KG方法")

    from ui import brain_ui

    kg_info = brain_ui._get_kg_info()
    print(f"  KG信息长度: {len(kg_info)} 字符")
    print(f"  包含'知识图谱状态': {'知识图谱状态' in kg_info}")
    print(f"  包含'基本统计': {'基本统计' in kg_info}")

    # 测试4: 创建测试记忆并查找关联
    print("\n📊 测试4: 测试记忆关联查找")

    # 创建一个测试记忆
    memory_id = await memory_system.store_memory(
        content="我今天学习了人工智能和知识图谱",
        memory_type="episodic",
        importance=0.8
    )

    print(f"  创建测试记忆: {memory_id}")

    # 从记忆构建KG
    result = await kg_integration.build_kg_from_memory(memory_id)
    print(f"  从记忆构建KG: +{result.get('nodes_added', 0)}节点, +{result.get('edges_added', 0)}边")

    # 查找关联
    associations_text = brain_ui._find_memory_associations(memory_id)
    print(f"  关联信息长度: {len(associations_text)} 字符")
    print(f"  包含'关联信息': {'关联信息' in associations_text}")

    # 测试5: 测试图增强检索开关
    print("\n📊 测试5: 测试图增强检索开关")

    print(f"  初始状态: kg_enhanced_search = {brain_ui.kg_enhanced_search}")
    brain_ui.kg_enhanced_search = True
    print(f"  启用后: kg_enhanced_search = {brain_ui.kg_enhanced_search}")
    brain_ui.kg_enhanced_search = False
    print(f"  关闭后: kg_enhanced_search = {brain_ui.kg_enhanced_search}")

    print("\n" + "=" * 60)
    print("✅ 所有KG-UI集成测试完成!")
    print("=" * 60)

    # 最终统计
    final_stats = knowledge_graph.get_statistics()
    print("\n📈 最终知识图谱统计:")
    print(f"  节点: {final_stats['basic']['total_nodes']}")
    print(f"  边: {final_stats['basic']['total_edges']}")

    return True


if __name__ == "__main__":
    asyncio.run(test_kg_ui())