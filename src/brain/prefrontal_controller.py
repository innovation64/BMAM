"""
Prefrontal Controller - 前额叶控制器
对应脑区: 前额叶皮层 (Prefrontal Cortex)

功能:
1. 查询路由: 决定使用快速路径(海马体)还是慢速路径(颞叶)
2. 元记忆监控: 集成MetamemoryMonitor
3. 策略调整: 根据反馈调整检索策略
"""

import logging
from typing import Dict, List, Any, Optional
import numpy as np

from ..memory.metamemory import MetamemoryMonitor, MetamemoryController, FOKJudgment, TOTState
from ..agents.base import AgentMessage

logger = logging.getLogger(__name__)

class PrefrontalController:
    """
    前额叶控制器
    
    负责协调记忆检索和元认知监控
    """
    
    def __init__(self, persistence_path: Optional[str] = None):
        # 🔥 使用 BMAMPaths 统一路径管理
        from ..utils.paths import BMAMPaths
        actual_path = persistence_path if persistence_path else str(BMAMPaths.METAMEMORY_STATE)
        # 初始化元记忆监控器
        self.monitor = MetamemoryMonitor(persistence_path=actual_path)
        self.meta_controller = MetamemoryController(monitor=self.monitor)
        
    async def route_query(
        self,
        query: str,
        context: Dict[str, Any],
        hippocampus_agent=None,
        temporal_lobe_agent=None
    ) -> Dict[str, Any]:
        """
        路由查询请求
        
        Args:
            query: 查询文本
            context: 上下文信息
            hippocampus_agent: 海马体代理 (Fast Path)
            temporal_lobe_agent: 颞叶代理 (Slow Path)
            
        Returns:
            检索结果
        """
        logger.info(f"🧠 [Prefrontal] Routing query: '{query[:50]}...'")
        
        # 1. 快速路径: 尝试海马体检索 (Key Index)
        fast_results = []
        if hippocampus_agent:
            try:
                # 假设海马体有search_episodes方法
                # 注意: 这里需要适配实际的Agent接口
                response = await hippocampus_agent.process_message(AgentMessage(
                    sender="prefrontal",
                    receiver="hippocampus",
                    message_type="query",
                    content={
                        'action': 'search_episodes',
                        'query': query,
                        'k': 5
                    }
                ))
                fast_results = response.get('memories', [])
            except Exception as e:
                logger.warning(f"Fast path (Hippocampus) failed: {e}")
                
        # 2. 元记忆评估
        # 计算相似度分数 (模拟)
        similarity_scores = [m.get('importance', 0.5) for m in fast_results] # 简化: 使用重要性作为分数代理
        
        # 检测TOT和FOK
        tot_state = self.monitor.detect_tot_state(
            query=query,
            query_vector=None, # 暂无向量
            partial_matches=fast_results,
            activation_levels=similarity_scores
        )
        
        fok_judgment = self.monitor.compute_fok(
            query=query,
            query_vector=None,
            candidate_memories=fast_results,
            similarity_scores=similarity_scores
        )
        
        # 3. 决策: 是否需要慢速路径 (颞叶)
        use_slow_path = False
        reason = "Fast path sufficient"
        
        if not fast_results:
            use_slow_path = True
            reason = "No fast path results"
        elif tot_state:
            use_slow_path = True
            reason = "TOT state detected"
        elif fok_judgment.fok_score < 0.4:
            use_slow_path = True
            reason = "Low confidence (FOK)"
            
        # 4. 执行慢速路径 (如果需要)
        slow_results = []
        if use_slow_path and temporal_lobe_agent:
            logger.info(f"🐢 [Prefrontal] Triggering slow path (Reason: {reason})")
            try:
                response = await temporal_lobe_agent.process_message(AgentMessage(
                    sender="prefrontal",
                    receiver="temporal_lobe",
                    message_type="query",
                    content={
                        'action': 'search_semantic',
                        'query': query,
                        'k': 5
                    }
                ))
                slow_results = response.get('memories', [])
            except Exception as e:
                logger.warning(f"Slow path (Temporal Lobe) failed: {e}")
                
        # 5. 合并结果
        final_results = fast_results + slow_results
        
        # 6. 记录检索尝试
        self.monitor.record_retrieval_attempt(
            query=query,
            retrieved_ids=[m['id'] for m in final_results],
            was_successful=len(final_results) > 0,
            confidence=fok_judgment.fok_score
        )
        
        return {
            'results': final_results,
            'fast_path_count': len(fast_results),
            'slow_path_count': len(slow_results),
            'meta_info': {
                'tot_detected': tot_state is not None,
                'fok_score': fok_judgment.fok_score,
                'routing_reason': reason
            }
        }
        
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.monitor.get_retrieval_statistics()
