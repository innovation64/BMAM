"""
类脑智能体记忆框架 - 现代化Gradio界面
Brain-Inspired Intelligent Agent Memory Framework - Modern Gradio Interface

全新设计的交互式界面，完美集成12智能体协调系统与高级记忆系统
"""

import os
import sys
import json
import asyncio
import logging
import traceback
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import threading
import time
from pathlib import Path

# 全局事件循环管理
_global_loop = None
_loop_thread = None

def _get_or_create_event_loop():
    """获取或创建全局事件循环"""
    global _global_loop, _loop_thread
    
    if _global_loop is None or _global_loop.is_closed():
        def run_loop():
            global _global_loop
            _global_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_global_loop)
            _global_loop.run_forever()
        
        _loop_thread = threading.Thread(target=run_loop, daemon=True)
        _loop_thread.start()
        
        # 等待循环启动
        import time
        while _global_loop is None:
            time.sleep(0.01)
    
    return _global_loop

def _run_async_in_global_loop(coro):
    """在全局事件循环中运行协程"""
    loop = _get_or_create_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()

import gradio as gr
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# 导入核心组件 - 使用简洁的协调器系统
from src.coordination.brain_coordinator import BrainInspiredCoordinator
from src.memory.memory_system import memory_system
from src.coordination.clean_agent_system import AgentMessage
from src.agents.agent_buffer_system import agent_buffer_system
from src.memory.knowledge_graph import knowledge_graph
from src.memory.kg_integration import kg_integration

# 初始化协调器
brain_coordinator = BrainInspiredCoordinator()

# 配置日志
from src.utils.config import get_logger
logger = get_logger(__name__)


class BrainUIInterface:
    """类脑智能体UI界面控制器"""
    
    def __init__(self):
        self.conversation_history = []
        self.system_metrics = []
        self.agent_activities = []
        self.memory_operations = []
        self.session_stats = {
            'total_conversations': 0,
            'successful_responses': 0,
            'memories_created': 0,
            'memories_retrieved': 0,
            'agents_activated': {},
            'processing_times': []
        }
        
        # 会话级的记忆追踪（避免跨会话污染）
        self.session_context = {
            'last_user_preference_id': None,  # 本会话最近的偏好记忆ID
            'conversation_start': datetime.now()
        }

        self.available_agents = sorted(agent_buffer_system.agent_buffers.keys())
        self.default_agent = self.available_agents[0] if self.available_agents else None

        # 连续对话上下文管理
        self.dialogue_history = []  # 保持最近的对话记录
        self.max_history_turns = 10  # 最多保留10轮对话
        self.max_context_tokens = 2000  # 上下文最大token限制

        # KG增强检索开关
        self.kg_enhanced_search = False  # 默认关闭
        
        # 实时监控
        self.monitoring_active = False
        self.monitor_thread = None
        
        logger.info("Brain UI Interface initialized")
    
    def _estimate_tokens(self, text: str) -> int:
        """粗略估算文本token数（中文约1.5字符/token，英文约4字符/token）"""
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)
    
    def _manage_dialogue_history(self, user_input: str, assistant_response: str):
        """管理对话历史，保持在token限制内"""
        # 添加新对话
        new_turn = {
            'user': user_input,
            'assistant': assistant_response,
            'timestamp': datetime.now().isoformat()
        }
        self.dialogue_history.append(new_turn)
        
        # 计算总token数并修剪历史
        total_tokens = 0
        valid_history = []
        
        # 从最新的开始计算，保留在token限制内的对话
        for turn in reversed(self.dialogue_history):
            turn_tokens = self._estimate_tokens(turn['user'] + turn['assistant'])
            if total_tokens + turn_tokens <= self.max_context_tokens:
                valid_history.insert(0, turn)
                total_tokens += turn_tokens
            else:
                break
        
        self.dialogue_history = valid_history[-self.max_history_turns:]  # 最多保留指定轮数
        
        logger.debug(f"对话历史管理: 保留{len(self.dialogue_history)}轮, 约{total_tokens}tokens")
    
    def _get_conversation_context(self) -> List[Dict[str, str]]:
        """获取格式化的对话上下文"""
        context = []
        for turn in self.dialogue_history:
            context.append({"role": "user", "content": turn['user']})
            context.append({"role": "assistant", "content": turn['assistant']})
        return context
    
    def start_monitoring(self):
        """启动实时系统监控"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("Real-time monitoring started")
    
    def stop_monitoring(self):
        """停止实时监控"""
        self.monitoring_active = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
        logger.info("Real-time monitoring stopped")
    
    def _monitor_loop(self):
        """系统监控循环"""
        while self.monitoring_active:
            try:
                # 收集系统指标
                timestamp = datetime.now()
                
                # 获取系统状态
                try:
                    system_status = brain_coordinator.get_system_status()
                    memory_stats = memory_system.get_system_stats()
                    
                    # 记录指标
                    metric = {
                        'timestamp': timestamp.isoformat(),
                        'system_running': system_status['system']['is_running'],
                        'active_agents': system_status['system']['total_agents'],
                        'total_memories': memory_stats['database'].get('total_memories', 0),
                        'vector_count': memory_stats['vectors'].get('vector_count', 0),
                        'processing_requests': system_status['processing_stats']['total_requests'],
                        'successful_requests': system_status['processing_stats']['successful_requests']
                    }
                except Exception as status_error:
                    # 使用简化状态作为备用
                    metric = {
                        'timestamp': timestamp.isoformat(),
                        'system_running': True,
                        'active_agents': 13,
                        'total_memories': 0,
                        'vector_count': 0,
                        'processing_requests': 0,
                        'successful_requests': 0
                    }
                
                self.system_metrics.append(metric)
                
                # 保持最近1000条记录
                if len(self.system_metrics) > 1000:
                    self.system_metrics = self.system_metrics[-1000:]
                
                time.sleep(5)  # 每5秒更新一次
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(10)
    
    async def process_conversation(self, user_input: str, history: List[List[str]]) -> Tuple[List[List[str]], str, go.Figure, str, str, str]:
        """
        处理用户对话
        返回: (updated_history, processing_log, performance_chart, system_status, memory_info, capability_analysis)
        """
        if not user_input.strip():
            return history, "等待用户输入...", self._create_empty_chart(), self._get_system_status(), self._get_memory_info(), "## 🧠 能力分析\n\n等待用户输入..."

        start_time = datetime.now()

        try:
            logger.info(f"Processing conversation: {user_input[:50]}...")

            # 🧠 先进行能力分析 (新增!)
            from src.reasoning.capability_analyzer import CapabilityAnalyzer
            analyzer = CapabilityAnalyzer()
            capability_result = await analyzer.analyze(user_input)

            # 更新会话统计
            self.session_stats['total_conversations'] += 1
            
            # 使用可塑性协调器处理输入，传递会话上下文和对话历史
            context = {
                'session_context': self.session_context,  # 传递会话级上下文
                'dialogue_history': self._get_conversation_context(),  # 传递对话历史
                'kg_enhanced_search': self.kg_enhanced_search  # 传递KG增强检索开关
            }
            result = await brain_coordinator.process_user_input(user_input, context)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            if result.success:
                # 更新对话历史 - 使用原来的列表格式
                response = result.response
                history.append({"role": "user", "content": user_input})
                history.append({"role": "assistant", "content": response})
                
                # 管理连续对话上下文
                self._manage_dialogue_history(user_input, response)
                
                # 更新统计
                self.session_stats['successful_responses'] += 1
                self.session_stats['processing_times'].append(processing_time)
                
                # 更新记忆操作统计
                if result.memory_stored:
                    self.session_stats['memories_created'] += 1
                self.session_stats['memories_retrieved'] += len(result.memories_retrieved)
                
                # 更新智能体激活统计
                for agent in result.agents_involved:
                    if agent not in self.session_stats['agents_activated']:
                        self.session_stats['agents_activated'][agent] = 0
                    self.session_stats['agents_activated'][agent] += 1
                
                # 生成详细处理日志 - 使用新的可塑性处理日志格式
                processing_log = self._generate_processing_log(user_input, result, processing_time)
                
                # 记录对话历史用于分析
                conversation_record = {
                    'timestamp': start_time.isoformat(),
                    'user_input': user_input,
                    'assistant_response': response,
                    'processing_time': processing_time,
                    'agents_involved': result.agents_involved,
                    'memories_retrieved': len(result.memories_retrieved),
                    'memory_stored': result.memory_stored,
                    'routing_decision': result.routing_decision,
                    'success': True
                }
                self.conversation_history.append(conversation_record)
                
                logger.info(f"Conversation processed successfully in {processing_time:.2f}s")
                
            else:
                # 处理失败
                error_response = f"❌ 处理失败: {result.error or '未知错误'}"
                history.append({"role": "user", "content": user_input})
                history.append({"role": "assistant", "content": error_response})
                processing_log = f"❌ 系统错误: {result.error or '未知错误'}"
                
                conversation_record = {
                    'timestamp': start_time.isoformat(),
                    'user_input': user_input,
                    'assistant_response': error_response,
                    'processing_time': processing_time,
                    'error': result.error,
                    'success': False
                }
                self.conversation_history.append(conversation_record)
                
                logger.error(f"Conversation processing failed: {result.error}")
            
            # 生成可视化
            performance_chart = self._create_performance_chart()
            system_status = self._get_system_status()
            memory_info = self._get_memory_info()

            # 🧠 格式化能力分析结果 (新增!)
            capability_analysis = self._format_capability_analysis(capability_result, user_input)

            return history, processing_log, performance_chart, system_status, memory_info, capability_analysis
            
        except Exception as e:
            error_msg = f"❌ 系统异常: {str(e)}"
            logger.error(f"Conversation processing exception: {e}")
            logger.error(traceback.format_exc())
            
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": error_msg})
            
            return (
                history,
                error_msg,
                self._create_empty_chart(),
                "❌ 系统异常",
                "❌ 无法获取记忆信息",
                "❌ 能力分析失败"
            )
    
    def _generate_plastic_processing_log(self, user_input: str, result: dict, processing_time: float) -> str:
        """生成可塑性处理日志"""
        
        activation_pathway = result.get('activation_pathway', [])
        connection_strength = result.get('connection_strength', [])
        
        log = f"""## 🧠 可塑性记忆系统处理报告

**⏰ 时间**: {datetime.now().strftime('%H:%M:%S')}
**📝 用户输入**: {user_input}
**⏱️ 处理耗时**: {processing_time:.3f} 秒
**✅ 处理状态**: {'成功' if result.get('success') else '失败'}
**🔗 可塑性**: {'已应用' if result.get('plasticity_applied') else '未应用'}
**🆔 交互ID**: {result.get('interaction_id', 'N/A')}

### 🤖 激活路径 ({len(activation_pathway)} 个Agent)
"""
        
        for i, agent in enumerate(activation_pathway):
            agent_name = self._get_agent_chinese_name(agent)
            strength = connection_strength[i-1] if i > 0 and i-1 < len(connection_strength) else 1.0
            strength_bar = "🟩" * int(strength * 10) + "⬜" * (10 - int(strength * 10))
            log += f"{i+1}. **{agent_name}** (`{agent}`)\n"
            if i > 0:
                log += f"   连接强度: {strength:.2f} {strength_bar}\n"
        
        log += f"\n### 🔬 可塑性学习\n"
        log += f"**连接更新**: {'✅ 已更新' if result.get('plasticity_applied') else '➖ 未更新'}\n"
        log += f"**学习类型**: Hebbian学习 + 稳态调节\n"
        
        return log
    
    def _generate_processing_log(self, user_input: str, result, processing_time: float) -> str:
        """生成详细的处理日志"""
        
        log = f"""## 🧠 类脑智能体处理报告

**⏰ 时间**: {datetime.now().strftime('%H:%M:%S')}
**📝 用户输入**: {user_input}
**⏱️ 处理耗时**: {processing_time:.3f} 秒
**✅ 处理状态**: {'成功' if result.success else '失败'}

### 🤖 激活的智能体 ({len(result.agents_involved)})
"""
        
        for i, agent in enumerate(result.agents_involved, 1):
            agent_name = self._get_agent_chinese_name(agent)
            log += f"{i}. **{agent_name}** (`{agent}`)\n"
        
        log += f"\n### 🧠 记忆系统\n"
        log += f"**检索记忆**: {len(result.memories_retrieved)} 条\n"
        log += f"**存储记忆**: {'✅ 已存储' if result.memory_stored else '➖ 未存储'}\n"
        
        if result.memories_retrieved:
            log += "\n### 📋 相关记忆 (前3条)\n"
            for i, memory in enumerate(result.memories_retrieved[:3], 1):
                content = memory.get('content', '')[:80]
                similarity = memory.get('similarity_score', 0)
                memory_type = memory.get('memory_type', 'unknown')
                timestamp = memory.get('timestamp', 'Unknown')
                
                log += f"{i}. **[{similarity:.3f}] [{memory_type}]** {content}...\n"
                log += f"   *时间: {timestamp}*\n\n"
        
        # 智能体执行日志
        if result.agent_logs:
            log += "\n### 🔧 智能体执行详情\n"
            for agent_id, logs in result.agent_logs.items():
                agent_name = self._get_agent_chinese_name(agent_id)
                if logs:
                    recent_log = logs[-1] if isinstance(logs, list) and logs else logs
                    log += f"**{agent_name}**: {recent_log.get('action', 'N/A')}\n"
        
        # 系统洞察
        if result.insights:
            log += f"\n### 💡 系统洞察\n"
            for key, value in result.insights.items():
                log += f"- **{key}**: {value}\n"
        
        return log
    
    def _format_capability_analysis(self, capability_result: dict, user_input: str) -> str:
        """格式化能力分析结果 - 展示动态推理过程"""
        capabilities = capability_result.get('capabilities', [])
        confidence = capability_result.get('confidence', 0)
        execution_plan = capability_result.get('execution_plan', 'N/A')

        # 能力中文映射
        capability_names = {
            'memory_retrieval': '📚 记忆检索',
            'fact_extraction': '🔍 事实提取',
            'temporal_calculation': '⏰ 时间计算',
            'duration_inference': '⌛ 时长推理',
            'identity_inference': '👤 身份推断',
            'pattern_recognition': '🎯 模式识别',
            'interest_inference': '💡 兴趣推断',
            'causal_reasoning': '🔗 因果推理',
            'counterfactual_reasoning': '🤔 反事实推理',
            'comparison': '⚖️ 对比分析',
            'multi_hop_inference': '🔀 多跳推理'
        }

        analysis = f"""## 🧠 动态能力分析

### 📝 用户问题
> {user_input}

### 🎯 检测到的推理能力 ({len(capabilities)}个)
"""

        for i, cap in enumerate(capabilities, 1):
            cap_name = cap.get('name', 'unknown')
            priority = cap.get('priority', 0)
            reason = cap.get('reason', 'N/A')
            display_name = capability_names.get(cap_name, cap_name.replace('_', ' ').title())

            priority_bar = "🟦" * priority + "⬜" * (5 - priority)

            analysis += f"""
**{i}. {display_name}** (`{cap_name}`)
- **优先级**: {priority}/5 {priority_bar}
- **理由**: {reason}
"""

        # 从能力推断问题类型
        inferred_type = "unknown"
        if any(c['name'] in ['temporal_calculation', 'duration_inference'] for c in capabilities):
            inferred_type = "temporal (时间问题)"
        elif any(c['name'] == 'identity_inference' for c in capabilities):
            inferred_type = "identity (身份问题)"
        elif any(c['name'] == 'interest_inference' for c in capabilities):
            inferred_type = "multi_hop (多跳推理)"
        elif any(c['name'] == 'fact_extraction' for c in capabilities):
            inferred_type = "factual (事实问题)"

        analysis += f"""
### 🎲 推断的问题类型
**{inferred_type}**

### 📈 置信度
**{confidence:.2f}** {'🟢 高' if confidence > 0.8 else '🟡 中' if confidence > 0.5 else '🔴 低'}

### 📋 执行计划
{execution_plan}

---
💡 **说明**: 这是基于LLM动态分析的结果,系统会根据检测到的能力自动调整推理策略,而非依赖硬编码规则。
"""

        return analysis

    def _get_agent_chinese_name(self, agent_id: str) -> str:
        """获取智能体中文名称"""
        name_mapping = {
            'short_term_memory': '短期记忆智能体',
            'long_term_memory': '长期记忆智能体',
            'memory_retrieval': '记忆检索智能体',
            'consolidation': '记忆巩固智能体',
            'memory_distortion': '记忆失真智能体',
            'reflection': '反思智能体',
            'forgetting': '遗忘智能体',
            'stress_response': '应激反应智能体',
            'conversation': '对话智能体',
            'executive_control': '执行控制智能体',
            'perception_encoding': '感知编码智能体',
            'action_execution': '行动执行智能体'
        }
        return name_mapping.get(agent_id, agent_id.replace('_', ' ').title())
    
    def _create_performance_chart(self) -> go.Figure:
        """创建性能监控图表"""
        
        if not self.conversation_history:
            return self._create_empty_chart()
        
        # 创建子图
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                '📈 响应时间趋势',
                '🤖 智能体激活频率',
                '🧠 记忆操作统计',
                '✅ 成功率趋势'
            ),
            specs=[[{"secondary_y": False}, {"type": "bar"}],
                   [{"type": "pie"}, {"secondary_y": False}]],
            vertical_spacing=0.15,
            horizontal_spacing=0.12
        )
        
        # 1. 响应时间趋势 - 渐变色优化
        processing_times = [c.get('processing_time', 0) for c in self.conversation_history[-20:]]
        fig.add_trace(
            go.Scatter(
                x=list(range(len(processing_times))),
                y=processing_times,
                mode='lines+markers',
                name='响应时间',
                line=dict(color='#667eea', width=3, shape='spline'),
                marker=dict(size=8, color='#764ba2', line=dict(color='white', width=2)),
                fill='tozeroy',
                fillcolor='rgba(102, 126, 234, 0.1)'
            ),
            row=1, col=1
        )
        
        # 2. 智能体激活频率
        if self.session_stats['agents_activated']:
            agents = list(self.session_stats['agents_activated'].keys())[:8]  # 显示前8个
            counts = [self.session_stats['agents_activated'][agent] for agent in agents]
            agent_names = [self._get_agent_chinese_name(agent) for agent in agents]
            
            fig.add_trace(
                go.Bar(
                    x=counts,
                    y=agent_names,
                    orientation='h',
                    name='激活次数',
                    marker=dict(
                        color=counts,
                        colorscale=[[0, '#667eea'], [1, '#764ba2']],
                        line=dict(color='white', width=1)
                    ),
                    text=counts,
                    textposition='outside'
                ),
                row=1, col=2
            )
        
        # 3. 记忆操作统计
        memory_data = {
            '创建记忆': self.session_stats['memories_created'],
            '检索记忆': self.session_stats['memories_retrieved'],
            '未存储': self.session_stats['total_conversations'] - self.session_stats['memories_created']
        }
        
        fig.add_trace(
            go.Pie(
                labels=list(memory_data.keys()),
                values=list(memory_data.values()),
                name="记忆操作",
                marker=dict(
                    colors=['#667eea', '#764ba2', '#e0e7ff'],
                    line=dict(color='white', width=2)
                ),
                hole=0.4,  # 甜甜圈图
                textinfo='label+percent',
                textfont=dict(size=12, color='white'),
                hovertemplate='<b>%{label}</b><br>数量: %{value}<br>占比: %{percent}<extra></extra>'
            ),
            row=2, col=1
        )
        
        # 4. 成功率趋势
        if len(self.conversation_history) > 1:
            success_data = []
            window_size = min(5, len(self.conversation_history))
            
            for i in range(len(self.conversation_history)):
                start_idx = max(0, i - window_size + 1)
                window = self.conversation_history[start_idx:i+1]
                success_rate = sum(1 for c in window if c.get('success', False)) / len(window)
                success_data.append(success_rate * 100)
            
            fig.add_trace(
                go.Scatter(
                    x=list(range(len(success_data))),
                    y=success_data,
                    mode='lines+markers',
                    name='成功率',
                    line=dict(color='#27ae60', width=3, shape='spline'),
                    marker=dict(size=6, color='#2ecc71', line=dict(color='white', width=2)),
                    fill='tozeroy',
                    fillcolor='rgba(39, 174, 96, 0.2)'
                ),
                row=2, col=2
            )
        
        # 更新布局 - 现代化主题
        fig.update_layout(
            height=700,
            showlegend=False,
            title_text="🚀 类脑智能体系统性能监控",
            title_x=0.5,
            title_font=dict(size=20, color='#667eea', family='Arial Black'),
            paper_bgcolor='rgba(255, 255, 255, 0.95)',
            plot_bgcolor='rgba(248, 249, 250, 0.5)',
            font=dict(family='Inter, sans-serif', color='#2c3e50'),
            margin=dict(t=60, b=40, l=40, r=40)
        )
        
        # 更新坐标轴 - 精致样式
        fig.update_xaxes(
            title_text="对话轮次",
            row=1, col=1,
            gridcolor='rgba(102, 126, 234, 0.1)',
            showline=True,
            linecolor='rgba(102, 126, 234, 0.3)'
        )
        fig.update_yaxes(
            title_text="时间(秒)",
            row=1, col=1,
            gridcolor='rgba(102, 126, 234, 0.1)',
            showline=True,
            linecolor='rgba(102, 126, 234, 0.3)'
        )
        fig.update_xaxes(
            title_text="激活次数",
            row=1, col=2,
            gridcolor='rgba(102, 126, 234, 0.1)'
        )
        fig.update_xaxes(
            title_text="对话轮次",
            row=2, col=2,
            gridcolor='rgba(102, 126, 234, 0.1)',
            showline=True,
            linecolor='rgba(102, 126, 234, 0.3)'
        )
        fig.update_yaxes(
            title_text="成功率(%)",
            row=2, col=2,
            gridcolor='rgba(102, 126, 234, 0.1)',
            showline=True,
            linecolor='rgba(102, 126, 234, 0.3)'
        )
        
        return fig
    
    def _get_kg_info(self) -> str:
        """获取知识图谱统计信息"""
        try:
            stats = knowledge_graph.get_statistics()

            basic = stats.get('basic', {})
            centrality = stats.get('centrality', {})
            graph_props = stats.get('graph_properties', {})

            info = f"""## 🕸️ 知识图谱状态

### 📊 基本统计
**节点总数**: {basic.get('total_nodes', 0)}
**边总数**: {basic.get('total_edges', 0)}
**平均度数**: {graph_props.get('avg_degree', 0.0):.2f}

### 🏷️ 实体类型分布
"""
            entity_types = basic.get('entity_types', {})
            for etype, count in sorted(entity_types.items(), key=lambda x: x[1], reverse=True):
                info += f"- **{etype}**: {count}\n"

            info += "\n### 🔗 关系类型分布\n"
            relation_types = basic.get('relation_types', {})
            for rtype, count in sorted(relation_types.items(), key=lambda x: x[1], reverse=True):
                info += f"- **{rtype}**: {count}\n"

            info += f"""
### 📈 图属性
**连通性**: {'✅ 连通' if graph_props.get('is_connected', False) else '❌ 非连通'}
**连通分量数**: {graph_props.get('num_components', 0)}
**图密度**: {graph_props.get('density', 0.0):.4f}

### ⭐ 重要节点 (PageRank Top 5)
"""
            top_pr = centrality.get('top_pagerank', [])
            for i, (node_id, score) in enumerate(top_pr[:5], 1):
                node = knowledge_graph.get_node(node_id)
                content = node.content if node else node_id
                info += f"{i}. **{content}** (得分: {score:.4f})\n"

            info += "\n### 🎯 连接最多的节点 (Degree Top 5)\n"
            top_degree = centrality.get('top_degree', [])
            for i, (node_id, degree) in enumerate(top_degree[:5], 1):
                node = knowledge_graph.get_node(node_id)
                content = node.content if node else node_id
                info += f"{i}. **{content}** (度数: {degree})\n"

            return info

        except Exception as e:
            logger.error(f"获取KG信息失败: {e}")
            return f"## ⚠️ 获取知识图谱信息失败\n\n错误: {str(e)}"

    def _find_memory_associations(self, memory_id: str) -> str:
        """查找记忆关联"""
        if not memory_id or not memory_id.strip():
            return "## 📊 关联信息\n\n⚠️ 请输入有效的记忆ID"

        try:
            # 异步调用需要在同步环境中运行
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                kg_integration.find_memory_associations(memory_id.strip(), max_depth=2)
            )
            loop.close()

            if not result.get('found'):
                return f"## 📊 关联信息\n\n⚠️ 未找到记忆 `{memory_id}` 在知识图谱中"

            info = f"""## 📊 记忆 `{memory_id}` 的关联信息

### 🔗 关联记忆 ({len(result.get('related_memories', []))})
"""
            for mem in result.get('related_memories', [])[:10]:
                content_preview = mem['content'][:50] + "..." if len(mem['content']) > 50 else mem['content']
                info += f"- **ID**: `{mem['memory_id']}` (重要度: {mem['importance']:.2f})\n"
                info += f"  {content_preview}\n\n"

            info += f"\n### 🏷️ 关联实体 ({len(result.get('related_entities', []))})\n"
            for entity in result.get('related_entities', [])[:10]:
                info += f"- **{entity['entity']}** ({entity['type']}, 重要度: {entity['importance']:.2f})\n"

            info += f"\n### 🛤️ 连接路径 ({len(result.get('paths', []))})\n"
            for path_info in result.get('paths', [])[:5]:
                path_str = " → ".join(path_info['path'])
                info += f"- 到 `{path_info['target']}`: {path_str} (长度: {path_info['length']})\n"

            info += f"\n**总上下文节点数**: {result.get('total_context', 0)}"

            return info

        except Exception as e:
            logger.error(f"查找记忆关联失败: {e}")
            return f"## ⚠️ 查找失败\n\n错误: {str(e)}"

    def _get_system_status(self) -> str:
        """获取系统状态信息"""
        try:
            # 获取可塑性系统状态
            system_status = brain_coordinator.get_system_status()
            memory_stats = memory_system.get_system_stats()
            
            # 可塑性统计
            plasticity_stats = system_status.get('plasticity_system', {})
            connection_metrics = plasticity_stats.get('connection_network', {})
            memory_associations = plasticity_stats.get('memory_associations', {})
            health_indicators = plasticity_stats.get('health_indicators', {})
            
            status = f"""## 🎛️ 可塑性智能体系统状态

### 🏃 核心系统
**运行状态**: {'🟢 正常运行' if system_status['system']['is_running'] else '🔴 已停止'}
**智能体总数**: {system_status['system']['total_agents']}
**活跃任务**: {system_status['system']['active_tasks']}

### 📊 处理统计  
**总请求数**: {system_status['processing_stats']['total_requests']}
**成功请求**: {system_status['processing_stats']['successful_requests']}
**失败请求**: {system_status['processing_stats']['failed_requests']}

### 🧠 神经可塑性引擎
**总适应次数**: {plasticity_stats.get('system_stats', {}).get('total_adaptations', 0)}
**连接更新**: {plasticity_stats.get('system_stats', {}).get('connection_updates', 0)}
**记忆关联**: {plasticity_stats.get('system_stats', {}).get('memory_associations', 0)}
**路由优化**: {plasticity_stats.get('system_stats', {}).get('routing_optimizations', 0)}

### 🔗 连接矩阵
**总连接数**: {connection_metrics.get('total_connections', 0)}
**平均强度**: {connection_metrics.get('average_strength', 0.0):.3f}
**强连接**: {connection_metrics.get('strong_connections', 0)}
**弱连接**: {connection_metrics.get('weak_connections', 0)}
**网络密度**: {connection_metrics.get('network_density', 0.0):.3f}

### 🧬 突触可塑性
**记忆总数**: {memory_associations.get('total_memories', 0)}
**记忆连接**: {memory_associations.get('total_connections', 0)}
**平均关联强度**: {memory_associations.get('average_strength', 0.0):.3f}
**强关联**: {memory_associations.get('strong_connections', 0)}

### 💡 健康指标
**可塑性活跃**: {'✅ 是' if health_indicators.get('plasticity_activity', 0) > 0 else '❌ 否'}
**学习效率**: {health_indicators.get('learning_efficiency', 0.0):.3f}
**关联丰富度**: {health_indicators.get('association_richness', 0.0):.3f}

### 🧠 记忆系统
**记忆总数**: {memory_stats['database'].get('total_memories', 0)}
**向量索引**: {memory_stats['vectors'].get('vector_count', 0)}

### 🚀 缓存性能
"""
            # 获取缓存统计
            try:
                # Embedding缓存
                emb_cache_stats = memory_system.embedding_service.cache.get_stats()
                status += f"**Embedding缓存**: {emb_cache_stats['cache_size']}/{emb_cache_stats['max_size']} ({emb_cache_stats['hit_rate']})\n"

                # Retrieval缓存
                ret_cache_stats = brain_coordinator.memory_retrieval.get_cache_stats()
                status += f"**检索缓存**: {ret_cache_stats['cache_size']}/{ret_cache_stats['max_cache_size']} ({ret_cache_stats['hit_rate']})\n"
            except Exception as e:
                status += f"**缓存统计**: 暂不可用\n"

            status += """
### 💬 会话统计
**本次对话**: {self.session_stats['total_conversations']}
**成功响应**: {self.session_stats['successful_responses']}
**创建记忆**: {self.session_stats['memories_created']}
**检索记忆**: {self.session_stats['memories_retrieved']}

### ⏱️ 性能指标
"""
            
            if self.session_stats['processing_times']:
                avg_time = sum(self.session_stats['processing_times']) / len(self.session_stats['processing_times'])
                status += f"**平均响应时间**: {avg_time:.3f}秒\n"
                status += f"**最快响应**: {min(self.session_stats['processing_times']):.3f}秒\n"
                status += f"**最慢响应**: {max(self.session_stats['processing_times']):.3f}秒\n"
            else:
                status += "**平均响应时间**: N/A\n"
            
            success_rate = (self.session_stats['successful_responses'] / max(1, self.session_stats['total_conversations'])) * 100
            status += f"**成功率**: {success_rate:.1f}%\n"
            
            return status
            
        except Exception as e:
            return f"❌ 获取系统状态失败: {str(e)}"
    
    def _get_memory_info(self) -> str:
        """获取记忆系统信息"""
        try:
            memory_stats = memory_system.get_system_stats()
            
            info = f"""## 🧠 记忆系统详情

### 📚 记忆库状态
**数据库**: {memory_stats['database'].get('database_url', 'N/A').split('/')[-1]}
**总记忆数**: {memory_stats['database'].get('total_memories', 0)}
**情节记忆**: {memory_stats['database'].get('episodic_memories', 0)}
**语义记忆**: {memory_stats['database'].get('semantic_memories', 0)}

### 🔍 向量搜索
**嵌入模型**: {memory_stats.get('embedding_model', 'N/A')}
**模型类型**: {memory_stats.get('embedding_type', 'N/A')}
**向量维度**: {memory_stats['vectors'].get('vector_dimension', 0)}
**索引大小**: {memory_stats['vectors'].get('vector_count', 0)}

### 🏷️ 本次会话记忆
**新增记忆**: {self.session_stats['memories_created']}
**检索总计**: {self.session_stats['memories_retrieved']}
**存储效率**: {(self.session_stats['memories_created'] / max(1, self.session_stats['total_conversations']) * 100):.1f}%

### 🎯 智能体激活
"""
            
            if self.session_stats['agents_activated']:
                sorted_agents = sorted(
                    self.session_stats['agents_activated'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]  # 显示前5个最活跃的智能体
                
                for agent_id, count in sorted_agents:
                    agent_name = self._get_agent_chinese_name(agent_id)
                    info += f"**{agent_name}**: {count}次\n"
            else:
                info += "**暂无激活记录**\n"

            return info

        except Exception as e:
            return f"❌ 获取记忆信息失败: {str(e)}"

    def get_plasticity_overview(self) -> str:
        """格式化神经可塑性洞察"""
        try:
            insights = brain_coordinator.get_system_status().get('plasticity_system', {})
            connection_metrics = insights.get('connection_network', {})
            adaptation_patterns = insights.get('adaptation_patterns', {})
            system_stats = insights.get('system_stats', {})

            dominant_pairs = adaptation_patterns.get('dominant_agent_pairs', [])

            overview = "## 🔗 神经可塑性洞察\n\n"
            overview += "### 📡 网络指标\n"
            overview += f"- 总连接数：{connection_metrics.get('total_connections', 0)}\n"
            overview += f"- 平均连接强度：{connection_metrics.get('average_strength', 0.0):.3f}\n"
            overview += f"- 网络密度：{connection_metrics.get('network_density', 0.0):.3f}\n"
            overview += f"- 强连接数量：{connection_metrics.get('strong_connections', 0)}\n\n"

            overview += "### 🧠 学习活动\n"
            overview += f"- 总适应次数：{system_stats.get('total_adaptations', 0)}\n"
            overview += f"- 连接更新：{system_stats.get('connection_updates', 0)}\n"
            overview += f"- 记忆关联：{system_stats.get('memory_associations', 0)}\n"
            overview += f"- 路由优化：{system_stats.get('routing_optimizations', 0)}\n"
            overview += f"- 学习速度指标：{insights.get('learning_velocity', 0.0):.3f}\n\n"

            if dominant_pairs:
                overview += "### 🧬 活跃连接对\n"
                for pair in dominant_pairs[:5]:
                    src, dst, strength = pair
                    overview += f"- {self._get_agent_chinese_name(src)} ↔ {self._get_agent_chinese_name(dst)}：{strength:.3f}\n"
                overview += "\n"

            associated = insights.get('memory_associations', {})
            overview += "### 📚 记忆关联\n"
            overview += f"- 总记忆数：{associated.get('total_memories', 0)}\n"
            overview += f"- 关联连接数：{associated.get('total_connections', 0)}\n"
            overview += f"- 平均关联强度：{associated.get('average_strength', 0.0):.3f}\n"

            return overview
        except Exception as e:
            return f"❌ 获取可塑性洞察失败: {str(e)}"

    def get_buffer_snapshot(self, agent_id: Optional[str]) -> str:
        """读取并格式化智能体缓冲信息"""
        if not agent_id:
            return "请选择智能体查看缓冲内容"
        try:
            buffer_content = _run_async_in_global_loop(agent_buffer_system.read_buffer(agent_id))
            recent_inputs = buffer_content.get('recent_inputs', [])[-5:]
            recent_outputs = buffer_content.get('recent_outputs', [])[-5:]
            recent_exchanges = buffer_content.get('recent_exchanges', [])[-5:]

            snapshot = f"## 📦 {self._get_agent_chinese_name(agent_id)} 缓冲概览\n"
            snapshot += f"- 最近输入：{len(buffer_content.get('recent_inputs', []))} 条\n"
            snapshot += f"- 最近输出：{len(buffer_content.get('recent_outputs', []))} 条\n"
            snapshot += f"- 最近交换：{len(buffer_content.get('recent_exchanges', []))} 条\n\n"

            def _format_entries(entries, title):
                if not entries:
                    return f"### {title}\n无记录\n\n"
                section = f"### {title}\n"
                for item in reversed(entries):
                    timestamp = item.get('timestamp', 'N/A')
                    try:
                        summary = json.dumps({k: v for k, v in item.items() if k != 'timestamp'}, ensure_ascii=False)
                    except Exception:
                        summary = str({k: v for k, v in item.items() if k != 'timestamp'})
                    section += f"- `{timestamp}` \n  - {summary}\n"
                section += "\n"
                return section

            snapshot += _format_entries(recent_inputs, "最近输入（最新5条）")
            snapshot += _format_entries(recent_outputs, "最近输出（最新5条）")
            snapshot += _format_entries(recent_exchanges, "最近交换（最新5条）")

            return snapshot
        except Exception as e:
            return f"❌ 读取缓冲失败: {str(e)}"

    def get_agent_logs(self, agent_id: Optional[str]) -> str:
        """获取智能体执行日志"""
        if not agent_id:
            return "请选择智能体查看执行日志"
        agent = brain_coordinator.agents.get(agent_id)
        if not agent:
            return f"⚠️ 未找到智能体 `{agent_id}`"

        logs = agent.execution_log[-10:]
        if not logs:
            return f"## 📜 {self._get_agent_chinese_name(agent_id)} 最近执行日志\n暂无记录"

        markdown = f"## 📜 {self._get_agent_chinese_name(agent_id)} 最近执行日志\n"
        for entry in reversed(logs):
            timestamp = entry.get('timestamp', 'N/A')
            action = entry.get('action', 'unknown')
            status = entry.get('status', 'info')
            details = entry.get('details')
            markdown += f"- `{timestamp}` **{action}** (状态: {status})\n"
            if details:
                try:
                    markdown += f"  - 详情: {json.dumps(details, ensure_ascii=False)}\n"
                except Exception:
                    markdown += f"  - 详情: {details}\n"
        return markdown
    
    def _create_empty_chart(self) -> go.Figure:
        """创建空图表占位符"""
        fig = go.Figure()
        fig.add_annotation(
            text="📊 等待数据...",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=20, color="gray")
        )
        fig.update_layout(
            height=400,
            margin=dict(t=50, b=50),
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False)
        )
        return fig

    def _create_cache_performance_chart(self) -> go.Figure:
        """创建缓存性能图表"""
        try:
            # 获取缓存统计
            emb_cache = memory_system.embedding_service.cache.get_stats()
            ret_cache = brain_coordinator.memory_retrieval.get_cache_stats()

            # 解析命中率百分比
            emb_hit_rate = float(emb_cache['hit_rate'].strip('%')) if isinstance(emb_cache['hit_rate'], str) else 0
            ret_hit_rate = float(ret_cache['hit_rate'].strip('%')) if isinstance(ret_cache['hit_rate'], str) else 0

            # 创建子图
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=(
                    '缓存命中率', '缓存使用率',
                    'Embedding缓存详情', 'Retrieval缓存详情'
                ),
                specs=[
                    [{'type': 'bar'}, {'type': 'indicator'}],
                    [{'type': 'indicator'}, {'type': 'indicator'}]
                ]
            )

            # 1. 命中率对比柱状图
            fig.add_trace(
                go.Bar(
                    x=['Embedding', 'Retrieval'],
                    y=[emb_hit_rate, ret_hit_rate],
                    marker_color=['#36a9e1', '#f39c12'],
                    text=[f"{emb_hit_rate:.1f}%", f"{ret_hit_rate:.1f}%"],
                    textposition='auto'
                ),
                row=1, col=1
            )

            # 2. 总体缓存使用率
            total_used = emb_cache['cache_size'] + ret_cache['cache_size']
            total_max = emb_cache['max_size'] + ret_cache['max_cache_size']
            usage_rate = (total_used / total_max * 100) if total_max > 0 else 0

            fig.add_trace(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=usage_rate,
                    title={'text': "总使用率"},
                    delta={'reference': 50},
                    gauge={
                        'axis': {'range': [None, 100]},
                        'bar': {'color': "#27ae60"},
                        'steps': [
                            {'range': [0, 50], 'color': "lightgray"},
                            {'range': [50, 80], 'color': "lightyellow"},
                            {'range': [80, 100], 'color': "lightcoral"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 90
                        }
                    }
                ),
                row=1, col=2
            )

            # 3. Embedding缓存详情
            fig.add_trace(
                go.Indicator(
                    mode="number+delta",
                    value=emb_cache['cache_size'],
                    title={'text': f"Embedding<br>({emb_cache['hit_count']} hits)"},
                    delta={'reference': emb_cache['max_size'] * 0.5, 'relative': False},
                    number={'suffix': f"/{emb_cache['max_size']}"}
                ),
                row=2, col=1
            )

            # 4. Retrieval缓存详情
            fig.add_trace(
                go.Indicator(
                    mode="number+delta",
                    value=ret_cache['cache_size'],
                    title={'text': f"Retrieval<br>({ret_cache['cache_hits']} hits)"},
                    delta={'reference': ret_cache['max_cache_size'] * 0.5, 'relative': False},
                    number={'suffix': f"/{ret_cache['max_cache_size']}"}
                ),
                row=2, col=2
            )

            fig.update_layout(
                height=500,
                showlegend=False,
                title_text="🚀 缓存性能监控",
                title_x=0.5
            )

            return fig

        except Exception as e:
            logger.warning(f"Failed to create cache chart: {e}")
            return self._create_empty_chart()

    def clear_session_data(self):
        """清除会话数据"""
        self.conversation_history.clear()
        self.system_metrics.clear()
        self.agent_activities.clear()
        self.memory_operations.clear()
        
        # 清除连续对话上下文
        self.dialogue_history.clear()
        
        # 重置统计
        self.session_stats = {
            'total_conversations': 0,
            'successful_responses': 0,
            'memories_created': 0,
            'memories_retrieved': 0,
            'agents_activated': {},
            'processing_times': []
        }
        
        logger.info("Session data cleared (including dialogue history)")


# 全局UI控制器实例
brain_ui = BrainUIInterface()


def create_brain_interface():
    """创建类脑智能体界面"""
    
    # 启动监控
    brain_ui.start_monitoring()
    
    # 使用现代化主题
    theme = gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="gray",
        neutral_hue="gray"
    )
    
    with gr.Blocks(
        title="类脑智能体记忆框架",
        theme=theme,
        css="""
        /* 全局样式优化 */
        .gradio-container {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%) !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        }

        /* 主标题区域 - 更现代的玻璃态设计 */
        .main-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            backdrop-filter: blur(10px);
            padding: 32px;
            border-radius: 16px;
            color: white;
            text-align: center;
            margin-bottom: 24px;
            box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.18);
        }

        .main-header h1 {
            font-size: 2.5em;
            font-weight: 700;
            margin-bottom: 8px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }

        .main-header h2 {
            font-size: 1.2em;
            font-weight: 400;
            opacity: 0.95;
            margin-bottom: 12px;
        }

        .main-header p {
            font-size: 1em;
            opacity: 0.9;
        }

        /* 卡片样式 - 新拟态设计 */
        .status-card {
            background: rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(10px);
            padding: 20px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
            margin: 12px 0;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .status-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
        }

        /* 指标卡片 - 渐变优化 */
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 12px;
            color: white;
            text-align: center;
            box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3);
            transition: transform 0.2s ease;
        }

        .metric-card:hover {
            transform: scale(1.03);
        }

        /* 聊天框优化 */
        .message-user {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important;
            border-radius: 12px 12px 4px 12px !important;
            padding: 12px 16px !important;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3) !important;
        }

        .message-bot {
            background: rgba(255, 255, 255, 0.95) !important;
            color: #2c3e50 !important;
            border-radius: 12px 12px 12px 4px !important;
            padding: 12px 16px !important;
            border: 1px solid rgba(102, 126, 234, 0.2) !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08) !important;
        }

        /* 按钮优化 */
        .primary-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 10px 24px !important;
            font-weight: 600 !important;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3) !important;
            transition: all 0.2s ease !important;
        }

        .primary-btn:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4) !important;
        }

        .secondary-btn {
            background: rgba(255, 255, 255, 0.9) !important;
            border: 2px solid #667eea !important;
            color: #667eea !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
        }

        .secondary-btn:hover {
            background: #667eea !important;
            color: white !important;
            transform: translateY(-2px) !important;
        }

        /* 标签页优化 */
        .tab-nav {
            background: rgba(255, 255, 255, 0.6) !important;
            backdrop-filter: blur(10px) !important;
            border-radius: 12px !important;
            padding: 4px !important;
        }

        .tab-nav button {
            border-radius: 8px !important;
            font-weight: 500 !important;
            transition: all 0.2s ease !important;
        }

        .tab-nav button.selected {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3) !important;
        }

        /* 输入框优化 */
        textarea, input[type="text"] {
            border-radius: 8px !important;
            border: 2px solid rgba(102, 126, 234, 0.3) !important;
            background: rgba(255, 255, 255, 0.95) !important;
            transition: all 0.2s ease !important;
        }

        textarea:focus, input[type="text"]:focus {
            border-color: #667eea !important;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1) !important;
        }

        /* Markdown内容优化 */
        .markdown-text h2 {
            color: #667eea;
            font-weight: 700;
            margin-top: 16px;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 2px solid rgba(102, 126, 234, 0.2);
        }

        .markdown-text h3 {
            color: #764ba2;
            font-weight: 600;
            margin-top: 12px;
            margin-bottom: 8px;
        }

        .markdown-text code {
            background: rgba(102, 126, 234, 0.1);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Fira Code', monospace;
        }

        .markdown-text pre {
            background: rgba(44, 62, 80, 0.95);
            color: #ecf0f1;
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
        }

        /* 下拉菜单优化 */
        select {
            border-radius: 8px !important;
            border: 2px solid rgba(102, 126, 234, 0.3) !important;
            background: rgba(255, 255, 255, 0.95) !important;
            padding: 8px 12px !important;
        }

        /* 加载动画 */
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .loading {
            animation: pulse 1.5s ease-in-out infinite;
        }

        /* 滚动条优化 */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }

        ::-webkit-scrollbar-track {
            background: rgba(0, 0, 0, 0.05);
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(135deg, #5568d3 0%, #653a8b 100%);
        }

        /* 响应式优化 */
        @media (max-width: 768px) {
            .main-header h1 {
                font-size: 1.8em;
            }
            .main-header h2 {
                font-size: 1em;
            }
        }
        """
    ) as demo:
        
        # 页面标题
        gr.HTML("""
        <div class="main-header">
            <h1>🧠 类脑神经可塑性智能体系统</h1>
            <h2>Brain-Inspired Neural Plasticity Agent Framework</h2>
            <p><strong>12智能体协调系统 × 神经可塑性引擎 × 动态学习 × 高级记忆管理</strong></p>
            <p style="font-size: 14px; margin-top: 10px;">
                ✨ Hebbian学习 | 🔗 动态连接强化 | 🧬 突触可塑性 | 📈 适应性路由 | 💫 记忆关联
            </p>
        </div>
        """)
        
        with gr.Row():
            # 左侧：主要交互区域
            with gr.Column(scale=3):
                # 对话区域
                chatbot = gr.Chatbot(
                    label="💬 智能对话助手",
                    height=500,
                    show_label=True,
                    avatar_images=("👤", "🤖"),
                    type='messages'  # 消除未来版本警告
                )
                
                # 输入区域
                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="与类脑智能体对话，体验真正的记忆连续性和智能推理...",
                        scale=5,
                        show_label=False,
                        container=False
                    )
                    send_btn = gr.Button("💬 发送", variant="primary", scale=1)
                
                # 控制按钮
                with gr.Row():
                    clear_btn = gr.Button("🗑️ 清除会话", variant="secondary")
                    refresh_btn = gr.Button("🔄 刷新状态", variant="secondary")
                    export_btn = gr.Button("📥 导出对话", variant="secondary")
                
                # 快速测试区域
                with gr.Accordion("🚀 快速测试", open=False):
                    gr.HTML("<p>点击下面的按钮快速测试不同功能：</p>")
                    with gr.Row():
                        test_btn1 = gr.Button("💭 记忆测试", size="sm")
                        test_btn2 = gr.Button("🔍 检索测试", size="sm")
                        test_btn3 = gr.Button("💡 推理测试", size="sm")
                        test_btn4 = gr.Button("😊 情感测试", size="sm")
                    with gr.Row():
                        test_btn5 = gr.Button("🧠 可塑性测试", size="sm")
                        test_btn6 = gr.Button("🔗 连接学习", size="sm")
                        test_btn7 = gr.Button("📈 适应性路由", size="sm")
                        test_btn8 = gr.Button("🧬 记忆关联", size="sm")
            
            # 右侧：监控面板
            with gr.Column(scale=2):
                with gr.Tab("📊 系统状态"):
                    system_status = gr.Markdown("## 🎛️ 系统状态\n\n初始化中...")
                
                with gr.Tab("🧠 记忆信息"):
                    memory_info = gr.Markdown("## 🧠 记忆系统\n\n加载中...")

                with gr.Tab("🔗 可塑性洞察"):
                    plasticity_info = gr.Markdown("## 🔗 神经可塑性洞察\n\n加载中...")

                with gr.Tab("🧠 能力分析"):
                    capability_analysis = gr.Markdown("## 🧠 动态能力分析\n\n等待用户输入...")

                with gr.Tab("📦 缓冲监控"):
                    agent_selector = gr.Dropdown(
                        choices=brain_ui.available_agents,
                        value=brain_ui.default_agent,
                        label="选择智能体",
                        interactive=bool(brain_ui.available_agents),
                        info="查看指定智能体的缓冲内容"
                    )
                    buffer_info = gr.Markdown("## 📦 智能体缓冲\n\n等待选择...")

                with gr.Tab("📜 Agent日志"):
                    agent_logs = gr.Markdown("## 📜 智能体执行日志\n\n等待选择...")

                with gr.Tab("🕸️ 知识图谱"):
                    kg_info = gr.Markdown("## 🕸️ 知识图谱\n\n加载中...")
                    with gr.Row():
                        kg_enhanced_checkbox = gr.Checkbox(
                            label="启用图增强检索",
                            value=False,
                            info="开启后将使用知识图谱扩展检索上下文"
                        )
                        kg_refresh_btn = gr.Button("🔄 刷新图谱", size="sm")

                    gr.Markdown("### 🔍 记忆关联查看")
                    with gr.Row():
                        memory_id_input = gr.Textbox(
                            placeholder="输入记忆ID查看关联...",
                            label="记忆ID",
                            scale=3
                        )
                        find_associations_btn = gr.Button("🔎 查找关联", scale=1)
                    kg_associations = gr.Markdown("## 📊 关联信息\n\n等待查询...")

        # 详细日志区域
        with gr.Row():
            processing_log = gr.Markdown("## 📋 处理详情\n\n等待对话...", height=200)
        
        # 性能监控图表
        with gr.Row():
            performance_chart = gr.Plot(label="📈 系统性能监控")

        selected_agent_state = gr.State(brain_ui.default_agent)

        # 事件处理函数
        def handle_conversation(message, history, agent_id):
            """处理对话的包装函数 - UI优化版本"""
            target_agent = agent_id or brain_ui.default_agent
            if not message.strip():
                return (
                    history,
                    "",
                    brain_ui._create_empty_chart(),
                    brain_ui._get_system_status(),
                    brain_ui._get_memory_info(),
                    brain_ui.get_plasticity_overview(),
                    "## 🧠 能力分析\n\n等待用户输入...",
                    brain_ui.get_buffer_snapshot(target_agent),
                    brain_ui.get_agent_logs(target_agent)
                )
            
            # UI环境修复：在每次对话前强制重置客户端连接
            try:
                from src.services.shared_openai_client import shared_client_manager
                shared_client_manager.reset_clients()
                logger.info("UI对话前重置客户端连接")
            except Exception as e:
                logger.warning(f"重置客户端失败: {e}")
            
            # 使用全局事件循环，避免频繁创建/销毁
            try:
                updated = _run_async_in_global_loop(
                    brain_ui.process_conversation(message, history)
                )
                updated_history, processing_log, performance_chart, system_status_md, memory_info_md, capability_analysis_md = updated
                return (
                    updated_history,
                    processing_log,
                    performance_chart,
                    system_status_md,
                    memory_info_md,
                    brain_ui.get_plasticity_overview(),
                    capability_analysis_md,
                    brain_ui.get_buffer_snapshot(target_agent),
                    brain_ui.get_agent_logs(target_agent)
                )
            except Exception as e:
                logger.error(f"UI对话处理异常: {e}")
                # 返回错误响应而不是崩溃
                history.append({"role": "user", "content": message})
                history.append({"role": "assistant", "content": f"抱歉，处理过程中出现网络连接问题：{str(e)}"})
                return (
                    history,
                    f"❌ 连接错误: {str(e)}",
                    brain_ui._create_empty_chart(),
                    brain_ui._get_system_status(),
                    brain_ui._get_memory_info(),
                    brain_ui.get_plasticity_overview(),
                    "❌ 能力分析失败",
                    brain_ui.get_buffer_snapshot(target_agent),
                    brain_ui.get_agent_logs(target_agent)
                )

        def get_current_status(agent_id):
            """获取当前状态"""
            target_agent = agent_id or brain_ui.default_agent
            return (
                brain_ui._get_system_status(),
                brain_ui._get_memory_info(),
                brain_ui._create_performance_chart(),
                brain_ui.get_plasticity_overview(),
                "## 🧠 能力分析\n\n等待用户输入...",
                brain_ui.get_buffer_snapshot(target_agent),
                brain_ui.get_agent_logs(target_agent)
            )

        def clear_all_data(agent_id):
            """清除所有数据"""
            brain_ui.clear_session_data()
            target_agent = agent_id or brain_ui.default_agent
            return (
                [],  # 清空对话
                "## 🔄 数据已清除\n\n所有会话数据和统计信息已重置。",
                brain_ui._create_empty_chart(),
                brain_ui._get_system_status(),
                brain_ui._get_memory_info(),
                brain_ui.get_plasticity_overview(),
                "## 🧠 能力分析\n\n等待用户输入...",
                brain_ui.get_buffer_snapshot(target_agent),
                brain_ui.get_agent_logs(target_agent)
            )

        def on_agent_change(agent_id, current_state):
            target_agent = agent_id or current_state or brain_ui.default_agent
            return (
                target_agent,
                brain_ui.get_buffer_snapshot(target_agent),
                brain_ui.get_agent_logs(target_agent)
            )

        def export_conversation():
            """导出对话记录"""
            if brain_ui.conversation_history:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"brain_conversation_{timestamp}.json"
                
                export_data = {
                    'export_time': datetime.now().isoformat(),
                    'total_conversations': len(brain_ui.conversation_history),
                    'session_stats': brain_ui.session_stats,
                    'conversations': brain_ui.conversation_history
                }
                
                # 这里可以保存到文件或返回下载链接
                return f"📁 对话已导出: {filename}\n包含 {len(brain_ui.conversation_history)} 轮对话"
            else:
                return "📝 暂无对话记录可导出"
        
        # 绑定事件
        send_btn.click(
            handle_conversation,
            inputs=[msg_input, chatbot, selected_agent_state],
            outputs=[chatbot, processing_log, performance_chart, system_status, memory_info, plasticity_info, capability_analysis, buffer_info, agent_logs]
        ).then(lambda: "", outputs=[msg_input])

        msg_input.submit(
            handle_conversation,
            inputs=[msg_input, chatbot, selected_agent_state],
            outputs=[chatbot, processing_log, performance_chart, system_status, memory_info, plasticity_info, capability_analysis, buffer_info, agent_logs]
        ).then(lambda: "", outputs=[msg_input])

        clear_btn.click(
            clear_all_data,
            inputs=[selected_agent_state],
            outputs=[chatbot, processing_log, performance_chart, system_status, memory_info, plasticity_info, capability_analysis, buffer_info, agent_logs]
        )

        refresh_btn.click(
            get_current_status,
            inputs=[selected_agent_state],
            outputs=[system_status, memory_info, performance_chart, plasticity_info, capability_analysis, buffer_info, agent_logs]
        )

        export_btn.click(
            export_conversation,
            outputs=[processing_log]
        )

        # KG相关事件
        kg_refresh_btn.click(
            lambda: brain_ui._get_kg_info(),
            outputs=[kg_info]
        )

        kg_enhanced_checkbox.change(
            lambda checked: setattr(brain_ui, 'kg_enhanced_search', checked) or f"✅ 图增强检索已{'开启' if checked else '关闭'}",
            inputs=[kg_enhanced_checkbox],
            outputs=[processing_log]
        )

        find_associations_btn.click(
            brain_ui._find_memory_associations,
            inputs=[memory_id_input],
            outputs=[kg_associations]
        )

        if brain_ui.available_agents:
            agent_selector.change(
                on_agent_change,
                inputs=[agent_selector, selected_agent_state],
                outputs=[selected_agent_state, buffer_info, agent_logs]
            )
        
        # 快速测试按钮
        test_btn1.click(lambda: "请记住我喜欢喝绿茶，每天下午3点左右。", outputs=[msg_input])
        test_btn2.click(lambda: "我刚才说我什么时候喝什么茶？", outputs=[msg_input])
        test_btn3.click(lambda: "基于我的偏好，推荐一些适合下午的饮品。", outputs=[msg_input])
        test_btn4.click(lambda: "今天感觉有点焦虑，工作压力很大。", outputs=[msg_input])
        # 可塑性测试按钮
        test_btn5.click(lambda: "介绍一下神经可塑性系统是如何工作的？", outputs=[msg_input])
        test_btn6.click(lambda: "重复激活记忆检索和对话智能体，测试连接强化。", outputs=[msg_input])
        test_btn7.click(lambda: "系统会如何根据历史模式优化智能体路由？", outputs=[msg_input])
        test_btn8.click(lambda: "展示相关记忆之间的动态关联是如何建立的。", outputs=[msg_input])
        
        # 页面加载时初始化
        demo.load(
            get_current_status,
            inputs=[selected_agent_state],
            outputs=[system_status, memory_info, performance_chart, plasticity_info, capability_analysis, buffer_info, agent_logs]
        )

        # 页面加载时初始化KG信息
        demo.load(
            lambda: brain_ui._get_kg_info(),
            outputs=[kg_info]
        )
    
    return demo


def main():
    """主函数"""
    try:
        print("🧠 类脑智能体记忆框架启动")
        print("=" * 60)
        print("✨ 12智能体协调系统")
        print("🧠 高级记忆管理")
        print("🔍 语义向量搜索")
        print("📊 实时性能监控")
        print("💬 智能对话交互")
        print()
        print("🌐 访问地址: http://127.0.0.1:7870")
        print("🚀 现代化界面设计")
        print("\n按 Ctrl+C 停止服务器")
        
        # 创建并启动界面
        demo = create_brain_interface()
        
        demo.launch(
            server_name="127.0.0.1", # 本地访问避免网络问题
            server_port=7870,        # 使用新端口避免冲突
            share=False,             # 不创建公共链接
            debug=False,             # 生产环境关闭调试
            show_error=True,         # 显示错误信息
            quiet=True,              # 减少网络请求
            show_api=False,          # 不显示API文档
            favicon_path=None,       # 可以添加自定义图标
            auth=None,               # 可以添加身份验证
            inbrowser=False,         # 不自动打开浏览器
            prevent_thread_lock=False # 使用默认设置
        )
        
    except KeyboardInterrupt:
        logger.info("正在关闭类脑智能体界面...")
        brain_ui.stop_monitoring()
        print("\n👋 感谢使用类脑智能体记忆框架！")
        
    except Exception as e:
        logger.error(f"启动界面失败: {e}")
        logger.error(traceback.format_exc())
        print(f"❌ 启动失败: {e}")
        
    finally:
        brain_ui.stop_monitoring()
        # 清理资源
        try:
            from src.services.shared_openai_client import shared_client_manager
            # 使用全局事件循环进行清理
            _run_async_in_global_loop(shared_client_manager.close())
            logger.info("资源清理完成")
        except Exception as cleanup_error:
            logger.warning(f"清理资源时出错: {cleanup_error}")


if __name__ == "__main__":
    main()
