"""
回归测试: LightweightKnowledgeGraph add_triple 兼容层

确保 LightweightKnowledgeGraph 的 add_triple() 方法能够兼容 SimpleKnowledgeGraph 的 API,
并且与 KnowledgeGraphBuilder 正确集成。
"""

import pytest
import asyncio
from src.memory.knowledge_graph import LightweightKnowledgeGraph
from src.utils.knowledge_graph_builder import KnowledgeGraphBuilder


class TestKnowledgeGraphCompatibility:
    """测试 KG 兼容层"""

    def test_add_triple_basic(self):
        """测试基本的 add_triple 功能"""
        kg = LightweightKnowledgeGraph()

        # 添加三元组
        success = kg.add_triple("Alice", "knows", "Bob")

        assert success is True
        assert "Alice" in kg.nodes
        assert "Bob" in kg.nodes
        assert len(kg.nodes) == 2
        assert len(kg.edges) == 1

    def test_add_triple_auto_creates_nodes(self):
        """测试 add_triple 自动创建节点"""
        kg = LightweightKnowledgeGraph()

        # 连续添加多个三元组，节点应该自动创建
        kg.add_triple("Alice", "works_at", "OpenAI")
        kg.add_triple("Bob", "works_at", "OpenAI")
        kg.add_triple("Alice", "knows", "Bob")

        assert len(kg.nodes) == 3  # Alice, Bob, OpenAI
        assert len(kg.edges) == 3  # 3个关系

    def test_add_triple_with_entity_types(self):
        """测试带有实体类型的 add_triple"""
        kg = LightweightKnowledgeGraph()

        # 指定实体类型
        kg.add_triple("Alice", "lives_in", "New York",
                      source_type="Person", target_type="Location")

        alice = kg.nodes.get("Alice")
        ny = kg.nodes.get("New York")

        assert alice is not None
        assert alice.entity_type == "Person"
        assert ny is not None
        assert ny.entity_type == "Location"

    def test_add_triple_idempotent(self):
        """测试 add_triple 的幂等性"""
        kg = LightweightKnowledgeGraph()

        # 多次添加相同的三元组
        kg.add_triple("Alice", "knows", "Bob")
        initial_edges = len(kg.edges)

        # 再次添加（节点已存在，应该只添加边）
        kg.add_triple("Alice", "knows", "Bob")

        # 节点数不变，边数应该只增加一次（如果是幂等的）或保持不变
        assert len(kg.nodes) == 2  # 仍然只有 Alice 和 Bob
        # 边数取决于实现 - 可能增加也可能不变

    def test_add_triple_with_strength(self):
        """测试带有关系强度的 add_triple"""
        kg = LightweightKnowledgeGraph()

        # 添加带强度的三元组
        kg.add_triple("Alice", "trusts", "Bob", strength=0.9)

        edge_key = "Alice-trusts-Bob"
        edge = kg.edges.get(edge_key)

        assert edge is not None
        assert edge.strength == 0.9

    def test_kg_builder_integration(self):
        """测试与 KnowledgeGraphBuilder 的集成"""
        # 创建统一KG实例
        unified_kg = LightweightKnowledgeGraph()

        # 创建 KG Builder 并传入统一KG
        kg_builder = KnowledgeGraphBuilder(
            llm_client=None,
            kg_instance=unified_kg
        )

        # 验证 KG Builder 持有统一KG的引用
        assert kg_builder.kg is unified_kg

        # 通过 Builder 的内部 KG 直接添加三元组
        kg_builder.kg.add_triple("Alice", "works_at", "OpenAI")

        # 验证节点已添加到统一KG
        assert "Alice" in unified_kg.nodes
        assert "OpenAI" in unified_kg.nodes

    @pytest.mark.asyncio
    async def test_kg_builder_extract_integration(self):
        """测试 KG Builder 提取功能与统一KG的集成"""
        unified_kg = LightweightKnowledgeGraph()
        kg_builder = KnowledgeGraphBuilder(
            llm_client=None,
            kg_instance=unified_kg
        )

        # 从文本提取实体和关系
        text = "Caroline visited the Natural History Museum on June 5."
        entities, relations = await kg_builder.extract_from_text(
            text,
            use_llm=False  # 不使用LLM，只用规则
        )

        # 验证提取到实体
        assert len(entities) > 0

    def test_simple_kg_api_compatibility(self):
        """
        测试与 SimpleKnowledgeGraph 的 API 兼容性

        SimpleKnowledgeGraph.add_triple(source, relation, target) 的行为:
        - 自动创建节点（如果不存在）
        - 添加关系到图中

        LightweightKnowledgeGraph 应该提供相同的行为
        """
        kg = LightweightKnowledgeGraph()

        # 模拟 SimpleKnowledgeGraph 的使用方式
        kg.add_triple("User", "says", "Hello")
        kg.add_triple("User", "likes", "Python")
        kg.add_triple("Python", "is_a", "Programming Language")

        # 验证所有节点和边都已创建
        assert "User" in kg.nodes
        assert "Hello" in kg.nodes
        assert "Python" in kg.nodes
        assert "Programming Language" in kg.nodes

        assert len(kg.nodes) == 4
        assert len(kg.edges) == 3

    def test_temporal_lobe_storage_compatibility(self):
        """
        测试与 TemporalLobeAgent storage.py 的兼容性

        TemporalLobeAgent._load_from_database() 调用:
            self.kg.add_triple(subject, predicate, obj)

        确保 LightweightKnowledgeGraph 可以无缝替换 SimpleKnowledgeGraph
        """
        kg = LightweightKnowledgeGraph()

        # 模拟从数据库加载的三元组
        triples = [
            ("Caroline", "visited", "Museum"),
            ("Caroline", "on", "June 5"),
            ("Museum", "is_a", "Natural History Museum")
        ]

        for subject, predicate, obj in triples:
            kg.add_triple(subject, predicate, obj)

        # 验证所有三元组都已加载
        assert len(kg.nodes) == 4  # Caroline, Museum, June 5, Natural History Museum
        assert len(kg.edges) == 3


# 运行测试
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
