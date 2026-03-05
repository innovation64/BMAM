"""
Learnable Agent Router - 可学习的智能体路由器
基于向量学习，无硬编码规则

神经科学依据:
- 前额叶任务选择性神经元 (Stokes et al., 2013)
- 基于反馈的向量空间学习 (强化学习调制)
- 语义嵌入的泛化能力

设计理念:
- 用向量空间几何替代if-else规则
- 持续学习: 每次反馈都更新
- 泛化能力: 相似查询自动路由到合适Agent

🔥 2025-12-16: 统一使用 OpenAI embedding (text-embedding-3-small)
"""

import numpy as np
import json
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

from ..base import BrainAgent, AgentMessage, BrainRegion
from ...utils.config import get_logger
from ...services.openai_embedding_service import OpenAIEmbeddingService

logger = get_logger(__name__)


@dataclass
class RoutingFeedback:
    """路由反馈记录"""
    query: str
    selected_agents: List[str]
    success: bool
    user_satisfaction: float  # 0-1
    timestamp: str

    def to_dict(self):
        return asdict(self)


class LearnableAgentRouter(BrainAgent):
    """
    可学习的智能体路由器

    核心机制:
    1. 查询编码: query → embedding (512维向量)
    2. Agent向量: 每个Agent有一个任务向量 (可学习)
    3. 相似度计算: score = cosine(query_emb, agent_emb)
    4. 反馈学习: 成功→拉近，失败→推远

    真正可塑性:
    - 无硬编码规则
    - 向量持续更新
    - 自动泛化到新查询
    """

    def __init__(
        self,
        agent_names: List[str],
        embedding_model: str = None,  # Uses DEFAULT_EMBEDDING_MODEL from constants
        learning_rate: float = 0.05,
        checkpoint_dir: str = "./checkpoints"
    ):
        super().__init__(
            agent_id="learnable_router",
            brain_region=BrainRegion.PREFRONTAL,
            system_prompt="可学习的智能体路由器，基于向量学习选择最佳Agent"
        )

        # 🔥 2025-12-16: 使用 OpenAI embedding (统一模型)
        self.encoder = OpenAIEmbeddingService(use_cache=True)
        self.embedding_dim = self.encoder.dimension  # 1536 for text-embedding-3-small

        # 每个Agent的任务向量 (可学习参数)
        self.agent_names = agent_names
        self.agent_embeddings = {}

        # 初始化: 随机向量 (L2归一化)
        for agent_name in agent_names:
            random_vec = np.random.randn(self.embedding_dim)
            self.agent_embeddings[agent_name] = random_vec / np.linalg.norm(random_vec)

        # 学习参数
        self.learning_rate = learning_rate

        # 温度参数 (控制分布锐度)
        self.temperature = 0.1

        # 统计信息
        self.routing_stats = {agent: 0 for agent in agent_names}
        self.feedback_history: List[RoutingFeedback] = []

        # checkpoint路径
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path = self.checkpoint_dir / "learnable_router.json"

        # 尝试加载已有checkpoint
        self._load_checkpoint()


    async def process_message(self, message: AgentMessage) -> Dict:
        """处理路由请求"""
        action = message.content.get('action')

        if action == 'route':
            query = message.content['query']
            top_k = message.content.get('top_k', 3)
            return await self.route(query, top_k)

        elif action == 'feedback':
            return await self.update_from_feedback(
                query=message.content['query'],
                selected_agents=message.content['selected_agents'],
                success=message.content.get('success', False),
                satisfaction=message.content.get('satisfaction', 0.5)
            )

        elif action == 'stats':
            return self.get_statistics()

        return {'error': f'Unknown action: {action}'}

    async def route(self, query: str, top_k: int = 3) -> Dict[str, any]:
        """
        路由查询到最合适的Agents

        Args:
            query: 用户查询
            top_k: 返回前k个Agent

        Returns:
            {
                'selected_agents': ['hippocampus', 'temporal_lobe'],
                'scores': {'hippocampus': 0.85, 'temporal_lobe': 0.72, ...},
                'reasoning': "时间相关查询，选择海马体..."
            }
        """
        # 1. 编码查询 (🔥 2025-12-16: 使用 OpenAI async API)
        query_emb = await self.encoder.encode_text(query)
        norm = np.linalg.norm(query_emb)
        if norm > 0:
            query_emb = query_emb / norm  # L2归一化

        # 2. 计算每个Agent的相似度分数
        scores = {}
        for agent_name, agent_emb in self.agent_embeddings.items():
            # Cosine相似度
            cosine_sim = np.dot(query_emb, agent_emb)

            # Temperature缩放 + Sigmoid
            score = 1.0 / (1.0 + np.exp(-cosine_sim / self.temperature))
            scores[agent_name] = float(score)

        # 3. 选择top_k个Agent
        sorted_agents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        selected_agents = [agent for agent, _ in sorted_agents[:top_k]]

        # 4. 更新统计
        for agent in selected_agents:
            self.routing_stats[agent] += 1

        # 5. 生成推理说明 (可选)
        reasoning = self._generate_reasoning(query, selected_agents, scores)


        return {
            'selected_agents': selected_agents,
            'scores': scores,
            'reasoning': reasoning,
            'query_embedding': query_emb.tolist()  # 用于调试
        }

    async def update_from_feedback(
        self,
        query: str,
        selected_agents: List[str],
        success: bool,
        satisfaction: float = 0.5
    ) -> Dict:
        """
        根据反馈更新Agent向量

        学习规则:
        - 成功: agent向量朝query方向移动 (拉近)
        - 失败: agent向量远离query方向 (推远)

        这模拟了突触可塑性: 正确的连接被强化，错误的被削弱
        """
        # 1. 编码查询 (🔥 2025-12-16: 使用 OpenAI async API)
        query_emb = await self.encoder.encode_text(query)
        norm = np.linalg.norm(query_emb)
        if norm > 0:
            query_emb = query_emb / norm

        # 2. 更新每个被选中的Agent
        for agent_name in selected_agents:
            if agent_name not in self.agent_embeddings:
                logger.warning(f"Unknown agent: {agent_name}")
                continue

            agent_emb = self.agent_embeddings[agent_name]

            # 计算梯度方向
            if success or satisfaction > 0.5:
                # 成功: 拉近向量 (增强语义关联)
                direction = query_emb - agent_emb
                effective_lr = self.learning_rate * satisfaction
            else:
                # 失败: 推远向量 (削弱错误关联)
                direction = agent_emb - query_emb
                effective_lr = self.learning_rate * (1.0 - satisfaction)

            # 更新向量
            new_emb = agent_emb + effective_lr * direction

            # L2归一化 (保持在单位球面上)
            new_emb = new_emb / np.linalg.norm(new_emb)

            self.agent_embeddings[agent_name] = new_emb

            logger.debug(f"Updated {agent_name} embedding with "
                        f"lr={effective_lr:.3f}")

        # 3. 记录反馈
        from datetime import datetime
        feedback = RoutingFeedback(
            query=query,
            selected_agents=selected_agents,
            success=success,
            user_satisfaction=satisfaction,
            timestamp=datetime.now().isoformat()
        )
        self.feedback_history.append(feedback)

        # 4. 定期保存checkpoint
        if len(self.feedback_history) % 10 == 0:
            self._save_checkpoint()
            logger.info(f"Router checkpoint saved "
                   f"satisfaction={satisfaction:.2f}")

        return {
            'status': 'updated',
            'agents_updated': selected_agents,
            'total_feedbacks': len(self.feedback_history)
        }

    def _generate_reasoning(
        self,
        query: str,
        selected_agents: List[str],
        scores: Dict[str, float]
    ) -> str:
        """生成路由推理说明"""
        reasoning_parts = [f"Query: '{query[:50]}...'"]

        for i, agent in enumerate(selected_agents[:3], 1):
            score = scores[agent]
            reasoning_parts.append(
                f"{i}. {agent} (score={score:.2f})"
            )

        return " | ".join(reasoning_parts)

    def _save_checkpoint(self):
        """保存学习到的Agent向量"""
        checkpoint = {
            'agent_embeddings': {
                name: emb.tolist() for name, emb in self.agent_embeddings.items()
            },
            'routing_stats': self.routing_stats,
            'total_feedbacks': len(self.feedback_history),
            'learning_rate': self.learning_rate,
            'temperature': self.temperature
        }

        with open(self.checkpoint_path, 'w') as f:
            json.dump(checkpoint, f, indent=2)


    def _load_checkpoint(self):
        """加载已保存的Agent向量"""
        if not self.checkpoint_path.exists():
            return

        try:
            with open(self.checkpoint_path, 'r') as f:
                checkpoint = json.load(f)

            # 恢复Agent向量
            for agent_name, emb_list in checkpoint['agent_embeddings'].items():
                if agent_name in self.agent_embeddings:
                    loaded_emb = np.array(emb_list)
                    # 🔥 2025-12-16: 检查维度是否匹配 (旧模型384维 vs 新模型1536维)
                    if loaded_emb.shape[0] == self.embedding_dim:
                        self.agent_embeddings[agent_name] = loaded_emb
                    else:
                        logger.warning(f"Dimension mismatch for {agent_name}: "
                                      f"checkpoint={loaded_emb.shape[0]}, expected={self.embedding_dim}. "
                                      f"Re-initializing with random vector.")
                        # 维度不匹配，重新初始化
                        random_vec = np.random.randn(self.embedding_dim)
                        self.agent_embeddings[agent_name] = random_vec / np.linalg.norm(random_vec)

            # 恢复统计
            self.routing_stats = checkpoint.get('routing_stats', self.routing_stats)

        except (json.JSONDecodeError) as e:
            logger.warning(f"Failed to load checkpoint: {e}")

    def get_statistics(self) -> Dict:
        """获取路由统计"""
        total_routes = sum(self.routing_stats.values())

        # 计算每个Agent的成功率 (基于反馈)
        agent_success_rates = {}
        for agent in self.agent_names:
            agent_feedbacks = [
                fb for fb in self.feedback_history
                if agent in fb.selected_agents
            ]
            if agent_feedbacks:
                avg_satisfaction = np.mean([fb.user_satisfaction for fb in agent_feedbacks])
                agent_success_rates[agent] = float(avg_satisfaction)
            else:
                agent_success_rates[agent] = 0.5  # 默认

        return {
            'total_routes': total_routes,
            'routing_distribution': self.routing_stats,
            'total_feedbacks': len(self.feedback_history),
            'agent_success_rates': agent_success_rates,
            'learning_rate': self.learning_rate,
            'checkpoint_path': str(self.checkpoint_path)
        }

    def visualize_agent_space(self, output_path: str = "./agent_space.png"):
        """
        可视化Agent向量空间 (降维到2D)

        用于调试: 查看哪些Agent在向量空间中相邻
        """
        try:
            from sklearn.decomposition import PCA
            import matplotlib.pyplot as plt

            # PCA降维到2D
            agent_vecs = np.array([self.agent_embeddings[name] for name in self.agent_names])
            pca = PCA(n_components=2)
            agent_vecs_2d = pca.fit_transform(agent_vecs)

            # 绘图
            plt.figure(figsize=(12, 8))
            for i, agent_name in enumerate(self.agent_names):
                x, y = agent_vecs_2d[i]
                plt.scatter(x, y, s=100)
                plt.text(x, y, agent_name, fontsize=9)

            plt.title("Agent Vector Space (PCA 2D)")
            plt.xlabel("PC1")
            plt.ylabel("PC2")
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(output_path)
            plt.close()

            return output_path

        except (RuntimeError, ValueError) as e:
            logger.warning(f"Failed to visualize: {e}")
            return None


# ============ 使用示例 ============

async def demo_learnable_router():
    """演示可学习路由器"""

    # 初始化
    agent_names = [
        'hippocampus', 'temporal_lobe', 'amygdala', 'prefrontal_storage',
        'basal_ganglia', 'short_term_memory', 'long_term_memory',
        'memory_retrieval', 'consolidation', 'reasoning_validator'
    ]

    router = LearnableAgentRouter(
        agent_names=agent_names,
        learning_rate=0.05
    )

    # 测试查询
    test_queries = [
        "Person什么时候参加的活动?",  # 期望: hippocampus (时间)
        "她的教育背景是什么?",  # 期望: temporal_lobe (知识)
        "她现在的情绪状态如何?",  # 期望: amygdala (情绪)
        "总结一下最近的对话",  # 期望: short_term_memory
    ]


    # 第一轮: 初始路由 (随机)
    for query in test_queries:
        result = await router.route(query, top_k=2)
        scores_list = [(a, result['scores'][a]) for a in result['selected_agents']]

    # 模拟反馈学习

    feedback_examples = [
        ("Person什么时候参加的活动?", ['hippocampus'], True, 1.0),
        ("她的教育背景是什么?", ['temporal_lobe'], True, 0.9),
        ("她现在的情绪状态如何?", ['amygdala'], True, 0.95),
        ("总结一下最近的对话", ['short_term_memory'], True, 0.85),
    ]

    for query, correct_agents, success, satisfaction in feedback_examples:
        await router.update_from_feedback(
            query=query,
            selected_agents=correct_agents,
            success=success,
            satisfaction=satisfaction
        )

    # 第二轮: 学习后的路由

    for query in test_queries:
        result = await router.route(query, top_k=2)
        scores_list = [(a, result['scores'][a]) for a in result['selected_agents']]

    # 测试泛化能力

    new_queries = [
        "上周发生了什么事?",  # 应该自动路由到hippocampus
        "她学过哪些课程?",  # 应该自动路由到temporal_lobe
    ]

    for query in new_queries:
        result = await router.route(query, top_k=2)
        scores_list = [(a, result['scores'][a]) for a in result['selected_agents']]

    # 统计信息
    stats = router.get_statistics()

    # 可视化 (可选)
    # router.visualize_agent_space()


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_learnable_router())

