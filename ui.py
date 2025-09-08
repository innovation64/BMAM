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

import gradio as gr
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入核心组件
from src.coordination.brain_coordinator import coordinator
from src.memory.memory_system import memory_system
from src.coordination.agent_system import AgentMessage

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


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
        
        # 实时监控
        self.monitoring_active = False
        self.monitor_thread = None
        
        logger.info("Brain UI Interface initialized")
    
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
                system_status = coordinator.get_system_status()
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
                
                self.system_metrics.append(metric)
                
                # 保持最近1000条记录
                if len(self.system_metrics) > 1000:
                    self.system_metrics = self.system_metrics[-1000:]
                
                time.sleep(5)  # 每5秒更新一次
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(10)
    
    async def process_conversation(self, user_input: str, history: List[List[str]]) -> Tuple[List[List[str]], str, go.Figure, str, str]:
        """
        处理用户对话
        返回: (updated_history, processing_log, performance_chart, system_status, memory_info)
        """
        if not user_input.strip():
            return history, "等待用户输入...", self._create_empty_chart(), self._get_system_status(), self._get_memory_info()
        
        start_time = datetime.now()
        
        try:
            logger.info(f"Processing conversation: {user_input[:50]}...")
            
            # 更新会话统计
            self.session_stats['total_conversations'] += 1
            
            # 使用协调器处理输入
            result = await coordinator.process_user_input(user_input)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            if result.success:
                # 更新对话历史 - 使用原来的列表格式
                history.append([user_input, result.response])
                
                # 更新统计
                self.session_stats['successful_responses'] += 1
                self.session_stats['processing_times'].append(processing_time)
                if result.memory_stored:
                    self.session_stats['memories_created'] += 1
                self.session_stats['memories_retrieved'] += len(result.memories_retrieved)
                
                # 更新智能体激活统计
                for agent in result.agents_involved:
                    if agent not in self.session_stats['agents_activated']:
                        self.session_stats['agents_activated'][agent] = 0
                    self.session_stats['agents_activated'][agent] += 1
                
                # 生成详细处理日志
                processing_log = self._generate_processing_log(user_input, result, processing_time)
                
                # 记录对话历史用于分析
                conversation_record = {
                    'timestamp': start_time.isoformat(),
                    'user_input': user_input,
                    'assistant_response': result.response,
                    'processing_time': processing_time,
                    'agents_involved': result.agents_involved,
                    'memories_used': len(result.memories_retrieved),
                    'memory_stored': result.memory_stored,
                    'success': True
                }
                self.conversation_history.append(conversation_record)
                
                logger.info(f"Conversation processed successfully in {processing_time:.2f}s")
                
            else:
                # 处理失败
                error_response = f"❌ 处理失败: {result.error}"
                history.append([user_input, error_response])
                processing_log = f"❌ 系统错误: {result.error}"
                
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
            
            return history, processing_log, performance_chart, system_status, memory_info
            
        except Exception as e:
            error_msg = f"❌ 系统异常: {str(e)}"
            logger.error(f"Conversation processing exception: {e}")
            logger.error(traceback.format_exc())
            
            history.append([user_input, error_msg])
            
            return (
                history,
                error_msg,
                self._create_empty_chart(),
                "❌ 系统异常",
                "❌ 无法获取记忆信息"
            )
    
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
        
        # 1. 响应时间趋势
        processing_times = [c.get('processing_time', 0) for c in self.conversation_history[-20:]]
        fig.add_trace(
            go.Scatter(
                x=list(range(len(processing_times))),
                y=processing_times,
                mode='lines+markers',
                name='响应时间',
                line=dict(color='#1f77b4', width=2),
                marker=dict(size=6)
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
                    marker_color='#2ECC71'
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
                marker_colors=['#3498DB', '#E74C3C', '#95A5A6']
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
                    line=dict(color='#27AE60', width=2),
                    fill='tonexty'
                ),
                row=2, col=2
            )
        
        # 更新布局
        fig.update_layout(
            height=700,
            showlegend=False,
            title_text="🚀 类脑智能体系统性能监控",
            title_x=0.5
        )
        
        # 更新坐标轴
        fig.update_xaxes(title_text="对话轮次", row=1, col=1)
        fig.update_yaxes(title_text="时间(秒)", row=1, col=1)
        fig.update_xaxes(title_text="激活次数", row=1, col=2)
        fig.update_xaxes(title_text="对话轮次", row=2, col=2)
        fig.update_yaxes(title_text="成功率(%)", row=2, col=2)
        
        return fig
    
    def _get_system_status(self) -> str:
        """获取系统状态信息"""
        try:
            system_status = coordinator.get_system_status()
            memory_stats = memory_system.get_system_stats()
            
            status = f"""## 🎛️ 系统状态监控

### 🏃 核心系统
**运行状态**: {'🟢 正常运行' if system_status['system']['is_running'] else '🔴 已停止'}
**智能体总数**: {system_status['system']['total_agents']}
**活跃任务**: {system_status['system'].get('active_tasks', 0)}

### 📊 处理统计
**总请求数**: {system_status['processing_stats']['total_requests']}
**成功请求**: {system_status['processing_stats']['successful_requests']}
**失败请求**: {system_status['processing_stats']['failed_requests']}
**内存操作**: {system_status['processing_stats']['memory_operations']}

### 🧠 记忆系统
**记忆总数**: {memory_stats['database'].get('total_memories', 0)}
**语义记忆**: {memory_stats['database'].get('semantic_memories', 0)}
**情节记忆**: {memory_stats['database'].get('episodic_memories', 0)}
**向量索引**: {memory_stats['vectors'].get('vector_count', 0)}

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
    
    def clear_session_data(self):
        """清除会话数据"""
        self.conversation_history.clear()
        self.system_metrics.clear()
        self.agent_activities.clear()
        self.memory_operations.clear()
        
        # 重置统计
        self.session_stats = {
            'total_conversations': 0,
            'successful_responses': 0,
            'memories_created': 0,
            'memories_retrieved': 0,
            'agents_activated': {},
            'processing_times': []
        }
        
        logger.info("Session data cleared")


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
        .main-header { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            padding: 20px; 
            border-radius: 10px; 
            color: white; 
            text-align: center; 
            margin-bottom: 20px;
        }
        .status-card {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #007bff;
            margin: 10px 0;
        }
        .metric-card {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            padding: 15px;
            border-radius: 8px;
            color: white;
            text-align: center;
        }
        """
    ) as demo:
        
        # 页面标题
        gr.HTML("""
        <div class="main-header">
            <h1>🧠 类脑智能体记忆框架</h1>
            <h2>Brain-Inspired Intelligent Agent Memory Framework</h2>
            <p><strong>12智能体协调系统 × 高级记忆管理 × 语义检索</strong></p>
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
                    avatar_images=("👤", "🤖")
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
            
            # 右侧：监控面板
            with gr.Column(scale=2):
                with gr.Tab("📊 系统状态"):
                    system_status = gr.Markdown("## 🎛️ 系统状态\n\n初始化中...")
                
                with gr.Tab("🧠 记忆信息"):
                    memory_info = gr.Markdown("## 🧠 记忆系统\n\n加载中...")
        
        # 详细日志区域
        with gr.Row():
            processing_log = gr.Markdown("## 📋 处理详情\n\n等待对话...", height=200)
        
        # 性能监控图表
        with gr.Row():
            performance_chart = gr.Plot(label="📈 系统性能监控")
        
        # 事件处理函数
        async def handle_conversation(message, history):
            """处理对话的异步函数"""
            if not message.strip():
                return history, "", brain_ui._create_empty_chart(), brain_ui._get_system_status(), brain_ui._get_memory_info()
            
            return await brain_ui.process_conversation(message, history)
        
        def get_current_status():
            """获取当前状态"""
            return brain_ui._get_system_status(), brain_ui._get_memory_info(), brain_ui._create_performance_chart()
        
        def clear_all_data():
            """清除所有数据"""
            brain_ui.clear_session_data()
            return (
                [],  # 清空对话
                "## 🔄 数据已清除\n\n所有会话数据和统计信息已重置。",
                brain_ui._create_empty_chart(),
                brain_ui._get_system_status(),
                brain_ui._get_memory_info()
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
                
                # 保存到文件
                import os
                export_dir = "exports"
                if not os.path.exists(export_dir):
                    os.makedirs(export_dir)
                
                filepath = os.path.join(export_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
                
                return f"📁 对话已导出: {filepath}\n包含 {len(brain_ui.conversation_history)} 轮对话"
            else:
                return "📝 暂无对话记录可导出"
        
        # 绑定事件
        send_btn.click(
            handle_conversation,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, processing_log, performance_chart, system_status, memory_info]
        ).then(lambda: "", outputs=[msg_input])
        
        msg_input.submit(
            handle_conversation,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, processing_log, performance_chart, system_status, memory_info]
        ).then(lambda: "", outputs=[msg_input])
        
        clear_btn.click(
            clear_all_data,
            outputs=[chatbot, processing_log, performance_chart, system_status, memory_info]
        )
        
        refresh_btn.click(
            get_current_status,
            outputs=[system_status, memory_info, performance_chart]
        )
        
        export_btn.click(
            export_conversation,
            outputs=[processing_log]
        )
        
        # 快速测试按钮
        test_btn1.click(lambda: "请记住我喜欢喝绿茶，每天下午3点左右。", outputs=[msg_input])
        test_btn2.click(lambda: "我刚才说我什么时候喝什么茶？", outputs=[msg_input])
        test_btn3.click(lambda: "基于我的偏好，推荐一些适合下午的饮品。", outputs=[msg_input])
        test_btn4.click(lambda: "今天感觉有点焦虑，工作压力很大。", outputs=[msg_input])
        
        # 页面加载时初始化
        demo.load(
            get_current_status,
            outputs=[system_status, memory_info, performance_chart]
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
            from src.coordination.agent_system import cleanup_shared_client
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(cleanup_shared_client())
            loop.close()
        except Exception as cleanup_error:
            logger.warning(f"清理资源时出错: {cleanup_error}")


if __name__ == "__main__":
    main()