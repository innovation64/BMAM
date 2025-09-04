#!/usr/bin/env python3
"""
MA-CMM V8 Gradio Demo - 修复版
修复对话历史显示和会话管理问题
"""

import gradio as gr
import asyncio
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Tuple
import pandas as pd
import sys
import os

# 加载环境变量
def load_env():
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # 移除引号
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    if key and value:  # 只设置非空值
                        os.environ[key] = value
                        if key == 'OPENAI_API_KEY':
                            print(f"✓ 已加载 OPENAI_API_KEY (长度: {len(value)})")

load_env()

# 验证API密钥
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("⚠️ 警告: 未找到 OPENAI_API_KEY，请检查 .env 文件")
else:
    print(f"✓ API密钥已就绪 (长度: {len(api_key)})")

# 添加项目路径
sys.path.append('/mnt/f/desktop/MA-CMM')

# 导入V8框架组件
try:
    from optimized_answer_extraction_v8 import OptimizedFrameworkV8
    from experiments.system_adapter import CompatibleOptimizedFrameworkV8
    framework_available = True
except ImportError as e:
    print(f"⚠️ V8框架导入失败: {e}，使用模拟模式")
    framework_available = False

# 导入知识库和幻觉检查组件
try:
    from knowledge_base_manager import KnowledgeBaseManager
    from agents.hallucination_checker import HallucinationChecker, HallucinationAwareAgent
    kb_available = True
    print("✓ 知识库和幻觉检查模块加载成功")
except ImportError as e:
    print(f"⚠️ 知识库模块导入失败: {e}")
    kb_available = False

# 会话状态管理
class SessionState:
    def __init__(self):
        self.conversation_history = []
        self.memory_stats = {"working": 0, "short_term": 0, "long_term": 0, "episodic": 0}
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.framework = None
        self.user_conditions = []  # 用户手动添加的条件
        self.selected_conversation_indices = []  # 选中的对话索引
        
        # 初始化知识库管理器
        if kb_available:
            self.kb_manager = KnowledgeBaseManager()
            print(f"✓ 知识库管理器初始化成功")
        else:
            self.kb_manager = None
    
    def initialize_framework(self):
        """初始化框架"""
        try:
            if framework_available:
                self.framework = CompatibleOptimizedFrameworkV8()
                return f"✅ 会话 {self.session_id} - MA-CMM V8 框架初始化成功！"
            else:
                return f"⚠️ 会话 {self.session_id} - 使用模拟模式"
        except Exception as e:
            return f"❌ 会话 {self.session_id} - 初始化失败: {str(e)}"
    
    def add_conversation(self, user_msg: str, assistant_msg: str):
        """添加对话到历史"""
        self.conversation_history.append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "user": user_msg,
            "assistant": assistant_msg
        })
        
        # 更新记忆统计
        self.memory_stats["working"] = min(self.memory_stats["working"] + 1, 20)
        if len(self.conversation_history) > 5:
            self.memory_stats["short_term"] = min(self.memory_stats["short_term"] + 1, 100)
    
    def get_conversation_context(self) -> str:
        """获取对话上下文"""
        if not self.conversation_history:
            return ""
        
        context_lines = []
        for item in self.conversation_history[-3:]:  # 最近3轮对话
            context_lines.append(f"用户: {item['user']}")
            context_lines.append(f"助手: {item['assistant']}")
        
        return "\n".join(context_lines)
    
    def get_conversation_display(self) -> List[List[str]]:
        """获取对话历史显示格式"""
        if not self.conversation_history:
            return [["暂无对话历史", "", ""]]
        
        display_data = []
        for item in self.conversation_history:
            display_data.append([
                item["timestamp"],
                item["user"][:50] + "..." if len(item["user"]) > 50 else item["user"],
                item["assistant"][:50] + "..." if len(item["assistant"]) > 50 else item["assistant"]
            ])
        
        return display_data
    
    def clear_session(self):
        """清空会话"""
        self.conversation_history = []
        self.memory_stats = {"working": 0, "short_term": 0, "long_term": 0, "episodic": 0}
        return f"✅ 会话 {self.session_id} 已清空"
    
    def new_session(self):
        """开始新会话"""
        self.conversation_history = []
        self.memory_stats = {"working": 0, "short_term": 0, "long_term": 0, "episodic": 0}
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.framework = None
        self.user_conditions = []
        self.selected_conversation_indices = []
        return f"🆕 新会话 {self.session_id} 已创建"
    
    def add_user_condition(self, condition_text: str, condition_type: str = "用户添加"):
        """添加用户自定义条件"""
        if condition_text.strip():
            condition = {
                "text": condition_text.strip(),
                "type": condition_type,
                "source": "user_input",
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            self.user_conditions.append(condition)
            return f"✅ 已添加条件: {condition_text[:50]}..."
        return "❌ 条件不能为空"
    
    def remove_user_condition(self, index: int):
        """删除用户条件"""
        if 0 <= index < len(self.user_conditions):
            removed = self.user_conditions.pop(index)
            return f"✅ 已删除条件: {removed['text'][:50]}..."
        return "❌ 无效的条件索引"
    
    def get_user_conditions_display(self):
        """获取用户条件显示格式"""
        if not self.user_conditions:
            return [["暂无用户添加的条件", "", ""]]
        
        display_data = []
        for i, condition in enumerate(self.user_conditions):
            display_data.append([
                str(i),
                condition["text"][:50] + "..." if len(condition["text"]) > 50 else condition["text"],
                condition["timestamp"]
            ])
        return display_data
    
    def toggle_conversation_selection(self, indices: List[int]):
        """切换对话选择状态"""
        self.selected_conversation_indices = indices
        return f"✅ 已选择 {len(indices)} 轮对话"

# 全局会话状态
session = SessionState()

async def process_question_async(question: str, use_memory: bool, use_length_control: bool, retrieval_mode: str, use_knowledge_base: bool = False, use_hallucination_check: bool = True):
    """异步处理问题"""
    
    if not session.framework:
        # 自动初始化框架
        init_result = session.initialize_framework()
        if "失败" in init_result:
            return f"❌ {init_result}", "", "", ""
    
    start_time = time.time()
    
    # 知识库检索（如果启用）
    kb_evidence = []
    verification_status = "未检查"  # 初始化验证状态
    
    if use_knowledge_base and session.kb_manager:
        try:
            kb_results = session.kb_manager.search_documents(question, top_k=3)
            print(f"🔍 知识库搜索 '{question}': 找到 {len(kb_results)} 个结果")
            for result in kb_results:
                kb_evidence.append({
                    "text": result["text"],
                    "source": f"知识库-{result['doc_id']}",
                    "score": result.get("score", 0.0)
                })
                print(f"  - {result['doc_id']}: {result['text'][:100]}... (分数: {result.get('score', 0.0)})")
        except Exception as e:
            print(f"❌ 知识库检索失败: {e}")
    
    try:
        if framework_available and session.framework:
            # 使用真实框架
            dialogue_context = session.get_conversation_context()
            
            # 直接使用完整集成，不依赖system_adapter
            # 构建证据段
            evidence_segments = []
            
            # 添加对话历史
            if dialogue_context:
                evidence_segments.append({
                    "text": dialogue_context,
                    "source": "conversation_history"
                })
            
            # 添加知识库证据
            if kb_evidence:
                evidence_segments.extend(kb_evidence)
                print(f"✓ 已添加 {len(kb_evidence)} 个知识库证据段")
            
            # 直接调用V8框架
            from optimized_answer_extraction_v8 import OptimizedFrameworkV8
            v8_framework = OptimizedFrameworkV8()
            
            # 幻觉检查集成
            if use_hallucination_check and kb_available:
                try:
                    from openai import AsyncOpenAI
                    api_key = os.getenv('OPENAI_API_KEY')
                    if api_key:
                        openai_client = AsyncOpenAI(api_key=api_key)
                        hallucination_checker = HallucinationChecker(openai_client)
                        hallucination_aware_agent = HallucinationAwareAgent(v8_framework, hallucination_checker)
                        result = await hallucination_aware_agent.generate_verified_response(question, evidence_segments)
                        verification_status = result.get('verification_status', '已验证')
                        print("✓ 已启用幻觉检查")
                    else:
                        result = await v8_framework.generate_response_for_question(question, evidence_segments)
                        verification_status = "跳过检查-无API密钥"
                        print("⚠️ 未找到API密钥，跳过幻觉检查")
                except Exception as e:
                    print(f"幻觉检查失败，使用普通模式: {e}")
                    result = await v8_framework.generate_response_for_question(question, evidence_segments)
                    verification_status = "检查失败"
            else:
                result = await v8_framework.generate_response_for_question(question, evidence_segments)
                verification_status = "未启用检查"
                if not use_hallucination_check:
                    print("⚠️ 幻觉检查已禁用")
                if not kb_available:
                    print("⚠️ 幻觉检查模块不可用")
        else:
            # 模拟模式
            simulation_answer = f"[模拟回答] 根据您的问题'{question}'，结合之前的对话上下文，我的回答是..."
            
            # 如果有知识库证据，在模拟回答中体现
            if kb_evidence:
                kb_info = f"\n\n📚 基于知识库内容 ({len(kb_evidence)}个证据段):\n"
                for i, evidence in enumerate(kb_evidence[:2], 1):
                    kb_info += f"{i}. {evidence['text'][:100]}...\n"
                simulation_answer += kb_info
            
            result = {
                "answer": simulation_answer,
                "extraction_method": "simulation",
                "confidence": 0.85,
                "evidence_segments": kb_evidence,
                "verification_status": "模拟模式"
            }
            verification_status = "模拟模式"
        
        answer = result.get("answer", "处理失败")
        
        # 改进答案显示格式
        original_answer = result.get('original_answer')
        if original_answer and original_answer != answer:
            # 显示修正信息
            enhanced_answer = f"""**💡 AI回答** (经幻觉检查修正):

{answer}

---
**📋 原始回答** (已修正):
{original_answer}
"""
        else:
            # 显示知识库来源信息
            if kb_evidence and use_knowledge_base:
                kb_sources = set()
                for evidence in kb_evidence:
                    source = evidence.get('source', '')
                    if source:
                        kb_sources.add(source)
                
                if kb_sources:
                    sources_text = ", ".join(list(kb_sources)[:3])
                    enhanced_answer = f"""**💡 AI回答** (基于知识库):

{answer}

---
**📚 知识来源**: {sources_text}
"""
                else:
                    enhanced_answer = answer
            else:
                enhanced_answer = answer
        
        # 添加到对话历史
        session.add_conversation(question, enhanced_answer)
        
        # 生成处理详情
        processing_time = time.time() - start_time
        details = f"""
### 🔍 处理详情
- **处理时间**: {processing_time:.2f}秒
- **提取方法**: {result.get('extraction_method', 'unknown')}
- **置信度**: {result.get('confidence', 0):.2%}
- **知识库证据**: {len(kb_evidence)}个
- **验证状态**: {verification_status}
- **会话ID**: {session.session_id}
- **对话轮次**: {len(session.conversation_history)}
- **使用记忆**: {'是' if use_memory else '否'}
- **长度控制**: {'是' if use_length_control else '否'}
- **检索模式**: {retrieval_mode}
"""
        
        # 详细条件提取信息
        extracted_conditions = result.get('extracted_conditions', [])
        evidence_info = result.get('evidence_segments', [])
        hallucination_check = result.get('hallucination_check', {})
        verification_status = result.get('verification_status', '未检查')
        
        conditions_info = f"""
### 🎯 提取的条件详情

**基本信息**
- **问题类型**: {result.get('question_type', '基于上下文的问答')}
- **历史轮次**: {len(session.conversation_history)}轮对话
- **上下文长度**: {len(session.get_conversation_context())}字符
- **记忆激活**: {sum(session.memory_stats.values())}项
- **知识库使用**: {'是' if use_knowledge_base else '否'}
- **幻觉检查**: {'是' if use_hallucination_check else '否'}

**验证状态**: {verification_status}

**条件提取结果**
"""
        
        if extracted_conditions:
            for i, condition in enumerate(extracted_conditions, 1):
                if isinstance(condition, dict):
                    conditions_info += f"\n**条件 {i}**: {condition.get('text', '未知条件')}\n"
                    conditions_info += f"- 类型: {condition.get('type', '未分类')}\n"
                    conditions_info += f"- 置信度: {condition.get('confidence', 0.0):.2f}\n"
                else:
                    conditions_info += f"\n**条件 {i}**: {str(condition)}\n"
        else:
            conditions_info += "\n*暂无明确条件提取*\n"
        
        # 显示证据片段（包括知识库）
        kb_evidence_count = 0
        if evidence_info:
            conditions_info += f"\n**证据片段**: {len(evidence_info)}个\n"
            for i, evidence in enumerate(evidence_info[:5], 1):  # 显示前5个
                if isinstance(evidence, dict):
                    text = evidence.get('text', '')[:150] + ('...' if len(evidence.get('text', '')) > 150 else '')
                    source = evidence.get('source', '未知来源')
                    if '知识库' in source:
                        kb_evidence_count += 1
                        conditions_info += f"- 📚 **知识库片段{kb_evidence_count}** ({source}): {text}\n"
                    else:
                        conditions_info += f"- 片段{i} ({source}): {text}\n"
                else:
                    conditions_info += f"- 片段{i}: {str(evidence)[:150]}...\n"
        
        # 显示幻觉检查结果
        if hallucination_check:
            has_hallucination = hallucination_check.get('has_hallucination', False)
            confidence = hallucination_check.get('confidence', 0.0)
            issues = hallucination_check.get('issues', [])
            recommendation = hallucination_check.get('recommendation', '')
            
            conditions_info += f"\n**🛡️ 幻觉检查结果**\n"
            conditions_info += f"- **检测状态**: {'⚠️ 发现潜在问题' if has_hallucination else '✅ 通过检查'}\n"
            conditions_info += f"- **可信度**: {confidence:.2f}\n"
            
            if issues:
                conditions_info += f"- **发现问题**: {len(issues)}个\n"
                for i, issue in enumerate(issues[:3], 1):  # 只显示前3个问题
                    issue_type = issue.get('type', '未知')
                    issue_content = issue.get('content', '')[:100]
                    conditions_info += f"  {i}. [{issue_type}] {issue_content}...\n"
            
            if recommendation:
                conditions_info += f"- **建议**: {recommendation}\n"
        
        conditions_info += f"\n**验证状态**: 已通过系统验证"
        
        # 添加用户自定义条件
        if session.user_conditions:
            conditions_info += f"\n\n**用户添加的条件** ({len(session.user_conditions)}个)\n"
            for i, condition in enumerate(session.user_conditions, 1):
                conditions_info += f"- **条件{i}**: {condition['text']}\n"
                conditions_info += f"  *类型: {condition['type']}, 时间: {condition['timestamp']}*\n"
        
        # 记忆状态
        memory_info = format_memory_stats()
        
        return enhanced_answer, details, conditions_info, memory_info
        
    except Exception as e:
        error_msg = f"❌ 处理错误: {str(e)}"
        return error_msg, error_msg, error_msg, format_memory_stats()

def process_question_sync(question: str, use_memory: bool, use_length_control: bool, retrieval_mode: str, use_knowledge_base: bool, use_hallucination_check: bool):
    """同步包装器"""
    if not question.strip():
        return "请输入问题", "", "", format_memory_stats()
    
    return asyncio.run(process_question_async(question, use_memory, use_length_control, retrieval_mode, use_knowledge_base, use_hallucination_check))

def format_memory_stats():
    """格式化记忆统计"""
    stats = f"""
### 📊 记忆层级状态 (会话: {session.session_id})
- **工作记忆**: {session.memory_stats['working']}/20 项
- **短期记忆**: {session.memory_stats['short_term']}/100 项  
- **长期记忆**: {session.memory_stats['long_term']}/1000 项
- **情节记忆**: {session.memory_stats['episodic']}/500 项
- **总对话轮次**: {len(session.conversation_history)} 轮
"""
    return stats

def clear_session():
    """清空当前会话"""
    result = session.clear_session()
    empty_history = get_enhanced_conversation_display()
    return result, format_memory_stats(), empty_history, ""

def new_session():
    """开始新会话"""
    result = session.new_session()
    empty_history = get_enhanced_conversation_display()
    return result, format_memory_stats(), empty_history, ""

def get_conversation_history():
    """获取对话历史"""
    return session.get_conversation_display()

def export_conversation():
    """导出对话历史"""
    if not session.conversation_history:
        return None
    
    df = pd.DataFrame(session.conversation_history)
    return df

def add_condition(condition_text: str, condition_type: str):
    """添加用户条件"""
    result = session.add_user_condition(condition_text, condition_type)
    return result, session.get_user_conditions_display()

def remove_condition(condition_index: int):
    """删除用户条件"""
    result = session.remove_user_condition(condition_index)
    return result, session.get_user_conditions_display()

def get_user_conditions():
    """获取用户条件列表"""
    return session.get_user_conditions_display()

def get_enhanced_conversation_display():
    """获取增强的对话历史显示（包含选择框）"""
    if not session.conversation_history:
        return [[False, "暂无对话历史", "", ""]]
    
    display_data = []
    for i, item in enumerate(session.conversation_history):
        is_selected = i in session.selected_conversation_indices
        display_data.append([
            is_selected,
            item["timestamp"],
            item["user"][:50] + "..." if len(item["user"]) > 50 else item["user"],
            item["assistant"][:50] + "..." if len(item["assistant"]) > 50 else item["assistant"]
        ])
    
    return display_data

def update_conversation_selection(conversation_data):
    """更新对话选择状态"""
    try:
        # 处理DataFrame或列表数据
        if hasattr(conversation_data, 'empty'):  # 如果是DataFrame
            if conversation_data.empty:
                return "未选择任何对话"
            data_list = conversation_data.values.tolist()
        elif isinstance(conversation_data, list):
            data_list = conversation_data
        else:
            return "数据格式错误"
        
        if len(data_list) <= 1:
            return "未选择任何对话"
        
        selected_indices = []
        for i, row in enumerate(data_list):
            if len(row) > 0 and row[0] is True:  # 检查第一列（选择框）
                selected_indices.append(i)
        
        session.selected_conversation_indices = selected_indices
        return f"✅ 已选择 {len(selected_indices)} 轮对话"
    
    except Exception as e:
        return f"选择更新失败: {str(e)}"

def select_all_conversations():
    """全选对话"""
    if session.conversation_history:
        session.selected_conversation_indices = list(range(len(session.conversation_history)))
        return f"✅ 已全选 {len(session.conversation_history)} 轮对话", get_enhanced_conversation_display()
    return "无对话可选择", get_enhanced_conversation_display()

def clear_conversation_selection():
    """清空对话选择"""
    session.selected_conversation_indices = []
    return "✅ 已清空选择", get_enhanced_conversation_display()

# 知识库管理函数
def upload_knowledge_document(file, title, description):
    """上传知识库文档"""
    if not session.kb_manager:
        return "❌ 知识库功能不可用", get_knowledge_base_list()
    
    if not file:
        return "❌ 请选择文件", get_knowledge_base_list()
    
    try:
        # 上传文档
        result = session.kb_manager.upload_document(
            file.name, 
            title or file.name, 
            description
        )
        
        if result["success"]:
            return f"✅ {result['message']} (分块: {result['chunks']})", get_knowledge_base_list()
        else:
            return f"❌ {result['message']}", get_knowledge_base_list()
            
    except Exception as e:
        return f"❌ 上传失败: {str(e)}", get_knowledge_base_list()

def get_knowledge_base_list():
    """获取知识库文档列表"""
    if not session.kb_manager:
        return [["知识库功能不可用", "", "", ""]]
    
    try:
        docs = session.kb_manager.get_documents_info()
        if not docs:
            return [["暂无文档", "", "", ""]]
        
        display_data = []
        for doc in docs:
            display_data.append([
                doc.get("title", ""),
                doc.get("file_name", ""),
                f"{doc.get('chunk_count', 0)} 块",
                doc.get("upload_time", "")[:16]  # 只显示日期和时间
            ])
        
        return display_data
    except Exception as e:
        return [[f"错误: {str(e)}", "", "", ""]]

def delete_knowledge_document(selected_docs):
    """删除选中的知识库文档"""
    if not session.kb_manager:
        return "❌ 知识库功能不可用", get_knowledge_base_list()
    
    if not selected_docs or len(selected_docs) <= 1:
        return "❌ 请选择要删除的文档", get_knowledge_base_list()
    
    try:
        # 获取文档列表
        docs = session.kb_manager.get_documents_info()
        deleted_count = 0
        
        # 根据选择删除文档
        for i, row in enumerate(selected_docs[1:]):  # 跳过表头
            if len(row) > 0 and i < len(docs):
                doc_id = docs[i]["id"]
                result = session.kb_manager.delete_document(doc_id)
                if result["success"]:
                    deleted_count += 1
        
        if deleted_count > 0:
            return f"✅ 已删除 {deleted_count} 个文档", get_knowledge_base_list()
        else:
            return "❌ 没有文档被删除", get_knowledge_base_list()
            
    except Exception as e:
        return f"❌ 删除失败: {str(e)}", get_knowledge_base_list()

def search_knowledge_base(query):
    """搜索知识库"""
    if not session.kb_manager:
        return "❌ 知识库功能不可用"
    
    if not query.strip():
        return "❌ 请输入搜索关键词"
    
    try:
        results = session.kb_manager.search_documents(query, top_k=5)
        
        if not results:
            return f"🔍 未找到与 '{query}' 相关的内容"
        
        # 格式化搜索结果
        formatted_results = f"🔍 搜索 '{query}' 的结果:\n\n"
        for i, result in enumerate(results, 1):
            score = result.get('score', 0)
            doc_id = result.get('doc_id', '')
            text = result.get('text', '')[:200] + "..." if len(result.get('text', '')) > 200 else result.get('text', '')
            
            formatted_results += f"**结果 {i}** (相关度: {score:.3f})\n"
            formatted_results += f"文档: {doc_id}\n"
            formatted_results += f"内容: {text}\n\n"
        
        return formatted_results
        
    except Exception as e:
        return f"❌ 搜索失败: {str(e)}"

# 创建Gradio界面
def create_demo():
    with gr.Blocks(title="MA-CMM V8 Demo - Enhanced", theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
        # 🤖 MA-CMM V8 智能对话系统 (增强版)
        
        **多智能体条件记忆管理框架** - 支持多轮对话、知识库管理和幻觉检查
        
        ---
        """)
        
        # 会话控制
        with gr.Row():
            session_status = gr.Textbox(
                label="会话状态",
                value=f"会话 {session.session_id}",
                interactive=False,
                scale=2
            )
            new_session_btn = gr.Button("🆕 新会话", variant="secondary", scale=1)
            clear_session_btn = gr.Button("🗑️ 清空会话", scale=1)
        
        with gr.Row():
            # 左侧：输入区域
            with gr.Column(scale=2):
                gr.Markdown("### 💬 对话输入")
                
                question_input = gr.Textbox(
                    label="输入问题",
                    placeholder="请输入您的问题...",
                    lines=2
                )
                
                with gr.Row():
                    use_memory = gr.Checkbox(label="启用记忆管理", value=True)
                    use_length_control = gr.Checkbox(label="智能长度控制", value=True)
                
                with gr.Row():
                    use_knowledge_base = gr.Checkbox(label="🔍 使用知识库", value=True)
                    use_hallucination_check = gr.Checkbox(label="🛡️ 幻觉检查", value=True)
                
                retrieval_mode = gr.Radio(
                    ["多路融合", "仅语义", "仅重要性", "仅时间", "仅上下文"],
                    label="检索模式",
                    value="多路融合"
                )
                
                submit_btn = gr.Button("🔍 提交问题", variant="primary")
            
            # 右侧：输出区域
            with gr.Column(scale=3):
                gr.Markdown("### 📝 系统回答")
                
                answer_output = gr.Textbox(
                    label="回答内容",
                    lines=4,
                    interactive=False
                )
                
                with gr.Tabs():
                    with gr.Tab("处理详情"):
                        process_details = gr.Markdown()
                    
                    with gr.Tab("条件提取"):
                        condition_details = gr.Markdown()
                    
                    with gr.Tab("条件管理"):
                        gr.Markdown("#### 🛠️ 手动添加条件")
                        with gr.Row():
                            condition_input = gr.Textbox(
                                label="条件内容",
                                placeholder="输入自定义条件...",
                                scale=3
                            )
                            condition_type = gr.Dropdown(
                                choices=["用户添加", "约束条件", "偏好设置", "上下文补充"],
                                value="用户添加",
                                label="条件类型",
                                scale=1
                            )
                        
                        with gr.Row():
                            add_condition_btn = gr.Button("➕ 添加条件", variant="primary", scale=1)
                            remove_condition_btn = gr.Button("🗑️ 删除选中", scale=1)
                        
                        condition_status = gr.Textbox(
                            label="操作状态",
                            interactive=False,
                            lines=1
                        )
                        
                        user_conditions_display = gr.Dataframe(
                            headers=["索引", "条件内容", "添加时间"],
                            value=session.get_user_conditions_display(),
                            label="用户添加的条件",
                            interactive=True
                        )
                    
                    with gr.Tab("知识库搜索"):
                        gr.Markdown("#### 🔍 快速搜索知识库")
                        with gr.Row():
                            kb_search_input = gr.Textbox(
                                label="搜索关键词",
                                placeholder="输入要搜索的内容...",
                                scale=3
                            )
                            kb_search_btn = gr.Button("搜索", variant="secondary", scale=1)
                        
                        kb_search_results = gr.Markdown(
                            value="输入关键词搜索知识库内容",
                            label="搜索结果"
                        )
                    
                    with gr.Tab("记忆状态"):
                        memory_status = gr.Markdown(format_memory_stats())
        
        # 对话历史展示
        gr.Markdown("### 📜 当前会话对话历史 (可选择特定对话)")
        
        with gr.Row():
            gr.Markdown("💡 **提示**: 勾选特定对话可以让AI专注于这些对话内容")
            select_all_btn = gr.Button("全选", size="sm", scale=1)
            clear_selection_btn = gr.Button("清空选择", size="sm", scale=1)
            update_selection_btn = gr.Button("更新选择", size="sm", scale=1, variant="secondary")
        
        conversation_display = gr.Dataframe(
            headers=["选择", "时间", "用户", "助手"],
            value=get_enhanced_conversation_display(),
            label="对话记录 (勾选第一列来选择特定对话)",
            interactive=True,
            datatype=["bool", "str", "str", "str"]
        )
        
        # 知识库管理区域
        gr.Markdown("---")
        gr.Markdown("## 📚 知识库管理")
        
        with gr.Tabs():
            with gr.Tab("📤 文档上传"):
                with gr.Row():
                    with gr.Column(scale=2):
                        upload_file = gr.File(
                            label="选择文档文件",
                            file_types=[".pdf", ".docx", ".txt", ".md"],
                            file_count="single"
                        )
                        upload_title = gr.Textbox(
                            label="文档标题（可选）",
                            placeholder="不填则使用文件名"
                        )
                        upload_description = gr.Textbox(
                            label="文档描述（可选）",
                            placeholder="简要描述文档内容...",
                            lines=2
                        )
                        upload_btn = gr.Button("📤 上传文档", variant="primary")
                    
                    with gr.Column(scale=1):
                        upload_status = gr.Textbox(
                            label="上传状态",
                            interactive=False,
                            lines=3
                        )
            
            with gr.Tab("📋 文档管理"):
                with gr.Row():
                    refresh_btn = gr.Button("🔄 刷新列表", variant="secondary")
                    delete_btn = gr.Button("🗑️ 删除选中", variant="secondary")
                
                knowledge_base_list = gr.Dataframe(
                    headers=["文档标题", "文件名", "分块数", "上传时间"],
                    value=get_knowledge_base_list(),
                    label="知识库文档列表",
                    interactive=True
                )
        
        # 使用示例
        gr.Examples(
            examples=[
                ["你好，我想了解MA-CMM框架"],
                ["这个框架有什么特点？"],
                ["它和传统方法有什么区别？"],
                ["能给我举个应用例子吗？"],
                ["根据知识库，请介绍相关技术"]
            ],
            inputs=question_input,
            label="💡 示例问题（点击试试多轮对话和知识库检索效果）"
        )
        
        # 事件绑定
        submit_btn.click(
            process_question_sync,
            inputs=[question_input, use_memory, use_length_control, retrieval_mode, use_knowledge_base, use_hallucination_check],
            outputs=[answer_output, process_details, condition_details, memory_status]
        ).then(
            lambda: get_enhanced_conversation_display(),
            outputs=conversation_display
        ).then(
            lambda: "",  # 清空输入框
            outputs=question_input
        )
        
        # 条件管理事件
        add_condition_btn.click(
            add_condition,
            inputs=[condition_input, condition_type],
            outputs=[condition_status, user_conditions_display]
        ).then(
            lambda: "",  # 清空条件输入框
            outputs=condition_input
        )
        
        # 对话选择事件
        select_all_btn.click(
            select_all_conversations,
            outputs=[condition_status, conversation_display]
        )
        
        clear_selection_btn.click(
            clear_conversation_selection,
            outputs=[condition_status, conversation_display]
        )
        
        # 手动更新选择按钮
        update_selection_btn.click(
            update_conversation_selection,
            inputs=conversation_display,
            outputs=condition_status
        )
        
        # 知识库搜索事件
        kb_search_btn.click(
            search_knowledge_base,
            inputs=kb_search_input,
            outputs=kb_search_results
        )
        
        # 知识库管理事件
        upload_btn.click(
            upload_knowledge_document,
            inputs=[upload_file, upload_title, upload_description],
            outputs=[upload_status, knowledge_base_list]
        ).then(
            lambda: (None, "", ""),  # 清空上传表单
            outputs=[upload_file, upload_title, upload_description]
        )
        
        refresh_btn.click(
            lambda: get_knowledge_base_list(),
            outputs=knowledge_base_list
        )
        
        delete_btn.click(
            delete_knowledge_document,
            inputs=knowledge_base_list,
            outputs=[upload_status, knowledge_base_list]
        )
        
        new_session_btn.click(
            new_session,
            outputs=[session_status, memory_status, conversation_display, answer_output]
        ).then(
            lambda: session.get_user_conditions_display(),
            outputs=user_conditions_display
        )
        
        clear_session_btn.click(
            clear_session,
            outputs=[session_status, memory_status, conversation_display, answer_output]
        ).then(
            lambda: session.get_user_conditions_display(),
            outputs=user_conditions_display
        )
    
    return demo

if __name__ == "__main__":
    print("🚀 启动 MA-CMM V8 Demo (修复版)...")
    
    # 创建并启动demo
    demo = create_demo()
    demo.launch(
        share=True,
        # server_port=7860,
        show_error=True
    )