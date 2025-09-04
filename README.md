# 🧠 Brain-Inspired Multi-Agent Memory Framework

基于人脑认知架构的12智能体协调系统，实现真实的语言模型推理和向量记忆存储。

## ✨ 系统特色

### 🎯 12智能体架构
- **8个核心记忆处理智能体**: 短期记忆、长期记忆、记忆检索、记忆巩固、记忆失真、反思、遗忘、应激反应
- **4个辅助功能智能体**: 对话、执行控制、感知编码、行动执行

### 🚀 核心功能
- **真实LLM推理**: 每个智能体都使用OpenAI API进行真实推理
- **向量记忆存储**: 基于FAISS的高效语义搜索
- **并行处理**: 多智能体并行协作处理复杂任务
- **情绪感知**: 情绪标记和应激反应处理
- **记忆巩固**: 模拟人脑记忆巩固过程
- **实时监控**: 完整的系统状态可视化

## 📁 项目结构

```
Brain-Inspired-Design/
├── src/                   # 核心源代码
│   ├── agents/           # 智能体实现
│   │   ├── core/        # 8个核心记忆处理智能体
│   │   ├── auxiliary/   # 4个辅助功能智能体
│   │   └── adapters/    # 智能体适配器
│   ├── coordination/     # 智能体协调系统
│   ├── memory/          # 记忆系统
│   ├── services/        # OpenAI服务封装
│   └── monitoring/      # 性能监控
├── ui.py               # 主要交互界面
├── main.py             # 程序入口点
└── requirements.txt    # 依赖文件
```

## 🛠️ 快速开始

### 1. 环境设置

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 设置API密钥
export OPENAI_API_KEY="your-api-key-here"
```

### 2. 运行系统

```bash
# 启动交互界面
python ui.py

# 或运行主程序
python main.py
```

## 🎮 使用方法

### 基本对话
- 启动 `ui.py` 进入交互界面
- 输入任意问题或话题
- 系统将调用12个智能体协作处理

### 高级功能
- **记忆查询**: 查看和搜索历史对话记忆
- **情绪分析**: 实时显示对话情绪状态
- **智能体监控**: 观察各智能体的工作状态
- **记忆巩固**: 手动触发重要记忆的巩固过程

## 🏗️ 核心架构

### 记忆智能体
- **短期记忆** (Short-term Memory): 处理即时信息
- **长期记忆** (Long-term Memory): 存储持久化记忆
- **记忆检索** (Memory Retrieval): 智能搜索相关记忆
- **记忆巩固** (Consolidation): 重要记忆的强化存储
- **记忆失真** (Memory Distortion): 模拟记忆变化过程
- **反思** (Reflection): 元认知和自我评估
- **遗忘** (Forgetting): 自然的记忆衰减
- **应激反应** (Stress Response): 情绪和压力处理

### 辅助智能体
- **对话** (Conversation): 自然语言交互
- **执行控制** (Executive Control): 任务调度和控制
- **感知编码** (Perception Encoding): 输入信息处理
- **行动执行** (Action Execution): 输出行为执行

## License

MIT License