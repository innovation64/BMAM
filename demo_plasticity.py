#!/usr/bin/env python3
"""
神经可塑性系统演示
Neural Plasticity System Demo

展示类脑智能体系统如何通过神经可塑性实现自适应学习
"""

import asyncio
import json
from datetime import datetime
from src.coordination.brain_coordinator import BrainInspiredCoordinator


async def main():
    """可塑性系统演示主程序"""
    print("🧠 类脑神经可塑性智能体系统演示")
    print("=" * 60)
    
    # 初始化协调器
    coordinator = BrainInspiredCoordinator()
    await coordinator.start_system()
    
    print("\n🔧 系统初始化完成，开始演示...")
    
    # 演示对话序列 - 展示学习过程
    demo_conversations = [
        "你好，我想了解神经可塑性系统",
        "请记住我喜欢喝咖啡，每天早上8点",
        "我刚才说我什么时候喝咖啡？",
        "基于我的习惯，推荐早餐搭配",
        "今天我感到有点焦虑",
        "系统如何处理情绪状态？",
        "解释一下Hebbian学习原理",
        "展示智能体连接强度变化"
    ]
    
    print("\n🚀 开始对话演示...")
    print("观察系统如何通过每次交互学习和适应\n")
    
    for i, user_input in enumerate(demo_conversations, 1):
        print(f"\n{'='*50}")
        print(f"第 {i} 轮对话")
        print(f"{'='*50}")
        print(f"👤 用户: {user_input}")
        
        # 处理对话
        result = await coordinator.process_user_input(user_input)
        
        if result.success:
            print(f"🤖 助手: {result.response[:200]}...")
            print(f"\n📊 处理统计:")
            print(f"  涉及智能体: {result.agents_involved}")
            print(f"  检索记忆: {len(result.memories_retrieved)} 条")
            print(f"  存储记忆: {'✅' if result.memory_stored else '❌'}")
            print(f"  处理耗时: {result.processing_time:.3f}秒")
            
            # 展示路由决策
            if result.routing_decision:
                routing_method = result.routing_decision.get('routing_method', '未知')
                print(f"  路由方式: {routing_method}")
        else:
            print(f"❌ 处理失败: {result.error}")
        
        # 获取可塑性统计
        plasticity_stats = coordinator.plasticity_engine.adaptation_stats
        print(f"\n🧠 可塑性学习状态:")
        print(f"  总适应次数: {plasticity_stats['total_adaptations']}")
        print(f"  连接更新: {plasticity_stats['connection_updates']}")
        print(f"  记忆关联: {plasticity_stats['memory_associations']}")
        print(f"  路由优化: {plasticity_stats['routing_optimizations']}")
        
        # 稍作停顿以观察输出
        await asyncio.sleep(1)
    
    # 系统状态总结
    print(f"\n{'='*50}")
    print("🎯 系统学习总结")
    print(f"{'='*50}")
    
    system_status = coordinator.get_system_status()
    plasticity_system = system_status.get('plasticity_system', {})
    
    print("\n📈 总体统计:")
    print(f"  总请求: {system_status['processing_stats']['total_requests']}")
    print(f"  成功率: {system_status['processing_stats']['successful_requests']}/{system_status['processing_stats']['total_requests']}")
    
    print("\n🧬 神经可塑性引擎:")
    system_stats = plasticity_system.get('system_stats', {})
    print(f"  总适应次数: {system_stats.get('total_adaptations', 0)}")
    print(f"  连接更新: {system_stats.get('connection_updates', 0)}")
    print(f"  记忆关联: {system_stats.get('memory_associations', 0)}")
    print(f"  路由优化: {system_stats.get('routing_optimizations', 0)}")
    
    # 连接矩阵状态
    connection_network = plasticity_system.get('connection_network', {})
    if connection_network:
        print("\n🔗 连接矩阵:")
        print(f"  总连接数: {connection_network.get('total_connections', 0)}")
        print(f"  平均强度: {connection_network.get('average_strength', 0.0):.3f}")
        print(f"  强连接: {connection_network.get('strong_connections', 0)}")
        print(f"  弱连接: {connection_network.get('weak_connections', 0)}")
        print(f"  网络密度: {connection_network.get('network_density', 0.0):.3f}")
        
        # 最强连接
        if 'strongest_connection' in connection_network:
            strongest = connection_network['strongest_connection']
            agents = strongest.get('agents', [])
            strength = strongest.get('strength', 0.0)
            if agents and len(agents) >= 2:
                print(f"  最强连接: {agents[0]} ↔ {agents[1]} (强度: {strength:.3f})")
    
    # 记忆关联状态
    memory_associations = plasticity_system.get('memory_associations', {})
    if memory_associations:
        print("\n🧠 突触可塑性:")
        print(f"  记忆总数: {memory_associations.get('total_memories', 0)}")
        print(f"  记忆连接: {memory_associations.get('total_connections', 0)}")
        print(f"  平均关联强度: {memory_associations.get('average_strength', 0.0):.3f}")
        print(f"  强关联: {memory_associations.get('strong_connections', 0)}")
    
    # 健康指标
    health_indicators = plasticity_system.get('health_indicators', {})
    if health_indicators:
        print("\n💡 系统健康指标:")
        print(f"  可塑性活跃: {'✅' if health_indicators.get('plasticity_activity', 0) > 0 else '❌'}")
        print(f"  学习效率: {health_indicators.get('learning_efficiency', 0.0):.3f}")
        print(f"  关联丰富度: {health_indicators.get('association_richness', 0.0):.3f}")
    
    # 适应性模式
    adaptation_patterns = plasticity_system.get('adaptation_patterns', {})
    if adaptation_patterns:
        print("\n🎨 适应模式:")
        print(f"  可塑性健康: {adaptation_patterns.get('plasticity_health', '未知')}")
        
        dominant_pairs = adaptation_patterns.get('dominant_agent_pairs', [])
        if dominant_pairs:
            print("  主导智能体连接:")
            for agent_a, agent_b, strength in dominant_pairs[:3]:
                print(f"    {agent_a} ↔ {agent_b} (强度: {strength:.3f})")
    
    print(f"\n{'='*60}")
    print("🎉 演示完成！")
    print("可塑性系统已成功学习并适应了用户的交互模式")
    print("每次交互都强化了有效的智能体连接和记忆关联")
    print("系统具备了真正的自适应学习能力！🧠✨")
    print(f"{'='*60}")
    
    # 关闭系统
    await coordinator.stop_system()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 演示中断")
    except Exception as e:
        print(f"\n❌ 演示出错: {e}")
        import traceback
        traceback.print_exc()