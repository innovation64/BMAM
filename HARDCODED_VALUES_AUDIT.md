# BMAM 硬编码值完整审计报告

> 审计日期: 2026-03-24
> 扫描范围: `BMAM/src/` 全部 Python 文件
> 发现总计: **350+ 硬编码值**, 分布在 **70+ 文件**中

---

## 目录

1. [LLM 参数 (temperature / max_tokens)](#1-llm-参数-temperature--max_tokens) — ~80处
2. [阈值 (Thresholds)](#2-阈值-thresholds) — ~70处
3. [权重与评分 (Weights & Scoring)](#3-权重与评分-weights--scoring) — ~60处
4. [搜索K值 (Search K)](#4-搜索k值-search-k) — ~30处
5. [容量与大小限制 (Capacity & Limits)](#5-容量与大小限制-capacity--limits) — ~30处
6. [衰减率 (Decay Rates)](#6-衰减率-decay-rates)
7. [时间与间隔 (Timing & Intervals)](#7-时间与间隔-timing--intervals)
8. [模型名称与URL (Models & URLs)](#8-模型名称与url-models--urls)
9. [学习率 (Learning Rates)](#9-学习率-learning-rates)
10. [遗忘比率 (Forgetting Ratios)](#10-遗忘比率-forgetting-ratios)
11. [HRM 收敛参数](#11-hrm-收敛参数)
12. [记忆巩固参数 (Consolidation)](#12-记忆巩固参数-consolidation)
13. [工作记忆容量 (Working Memory)](#13-工作记忆容量-working-memory)
14. [KG 合并配置](#14-kg-合并配置)
15. [迭代限制 (Iteration Limits)](#15-迭代限制-iteration-limits)
16. [批处理大小 (Batch Sizes)](#16-批处理大小-batch-sizes)
17. [嵌入维度 (Embedding Dimension)](#17-嵌入维度-embedding-dimension)
18. [文本截断限制 (Truncation)](#18-文本截断限制-truncation)
19. [置信度初始值 (Confidence)](#19-置信度初始值-confidence)
20. [统计总结](#统计总结)

---

## 1. LLM 参数 (temperature / max_tokens)

**最严重的硬编码类别** — 几乎每个调用 `call_llm()` 的文件都有内联参数。

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/utils/knowledge_graph_builder.py` | 372-373 | temperature=0.1, max_tokens=1000 | KG 抽取 |
| `src/agents/brain_regions/hippocampus_agent/forgetting.py` | 208 | max_tokens=100, temperature=0.3 | 遗忘决策 |
| `src/agents/brain_regions/hippocampus_agent/consolidation.py` | 69 | max_tokens=200, temperature=0.3 | 巩固决策 |
| `src/agents/brain_regions/hippocampus_agent/consolidation.py` | 130-131 | max_tokens=500, temperature=0.3 | 巩固处理 |
| `src/agents/brain_regions/hippocampus_agent/consolidation.py` | 171-172 | max_tokens=300, temperature=0.1 | 巩固细节 |
| `src/agents/brain_regions/hippocampus_agent/consolidation.py` | 289-290 | max_tokens=800, temperature=0.3 | 巩固批处理 |
| `src/agents/brain_regions/hippocampus_agent/consolidation.py` | 601-602 | max_tokens=800, temperature=0.3 | 巩固输出 |
| `src/agents/brain_regions/hippocampus_agent/advanced_search/entity_action_extraction.py` | 53 | max_tokens=200, temperature=0.3 | 实体动作抽取 |
| `src/agents/brain_regions/hippocampus_agent/advanced_search/temporal_ranking.py` | 321 | max_tokens=400, temperature=0.3 | 时序排序 |
| `src/agents/brain_regions/hippocampus_agent/advanced_search/event_boundary_llm.py` | 68-69 | max_tokens=150, temperature=0.3 | 事件边界检测 |
| `src/agents/brain_regions/hippocampus_agent/advanced_search/temporal_cue_extraction.py` | 51 | max_tokens=200, temperature=0.3 | 时间线索抽取 |
| `src/agents/brain_regions/hippocampus_agent/advanced_search/entity_action_ranking.py` | 44 | max_tokens=500, temperature=0.3 | 实体动作排序 |
| `src/agents/brain_regions/prefrontal_agent/task_coordination.py` | 62-63 | max_tokens=800, temperature=0.5 | 任务规划 |
| `src/agents/brain_regions/prefrontal_agent/task_coordination.py` | 144-145 | max_tokens=1000, temperature=0.4 | 任务协调 |
| `src/agents/brain_regions/prefrontal_agent/memory_compression.py` | 179-180 | max_tokens=200, temperature=0.3 | 记忆压缩 |
| `src/agents/brain_regions/prefrontal_agent/core_operations.py` | 183-184 | max_tokens=800, temperature=0.5 | 核心操作 |
| `src/agents/brain_regions/prefrontal_agent/core_operations.py` | 268-269 | max_tokens=1000, temperature=0.4 | 核心操作2 |
| `src/agents/brain_regions/theory_of_mind_agent.py` | 255 | temperature=0.1, max_tokens=400 | 对抗分析 |
| `src/agents/brain_regions/theory_of_mind_agent.py` | 340 | temperature=0.1, max_tokens=500 | 欺骗检测 |
| `src/agents/brain_regions/theory_of_mind_agent.py` | 414 | temperature=0.3, max_tokens=500 | 意图推理 |
| `src/agents/brain_regions/theory_of_mind_agent.py` | 754 | temperature=0.3, max_tokens=300 | 换位思考 |
| `src/agents/brain_regions/amygdala_agent.py` | 450-451 | max_tokens=400, temperature=0.5 | 情绪处理 |
| `src/agents/brain_regions/temporal_lobe_agent/index_management.py` | 94 | max_tokens=200 | 索引管理 |
| `src/agents/brain_regions/temporal_lobe_agent/extractors.py` | 116-117 | max_tokens=500, temperature=0.3 | 颞叶抽取 |
| `src/agents/core/learnable_router.py` | 90 | self.temperature = 0.1 | 路由softmax温度 |
| `src/agents/core/personality/style/style_generator.py` | 68-69 | max_tokens=220, temperature=0.7 | 风格生成 |
| `src/agents/core/reflection/scenario_simulation.py` | 237 | temperature=0.3, max_tokens=200 | 情景模拟 |
| `src/agents/core/reflection/scenario_simulation.py` | 274 | temperature=0.4, max_tokens=200 | 预测 |
| `src/agents/core/reflection/scenario_simulation.py` | 328 | temperature=0.6, max_tokens=150 | 创意场景生成 |
| `src/agents/core/reflection/reflection.py` | 577 | temperature=0.3, max_tokens=400 | 反思生成 |
| `src/agents/core/context_compaction.py` | 87-88 | max_tokens=400, temperature=0.3 | 上下文压缩 |
| `src/agents/core/persona_memory.py` | 734 | temperature=0.3, max_tokens=150 | 人格记忆推理 |
| `src/agents/core/reasoning_validator/general_reasoning.py` | 66-67 | temperature=0.2, max_tokens=300 | 通用推理验证 |
| `src/agents/core/reasoning_validator/general_reasoning.py` | 160-161 | temperature=0.1, max_tokens=300 | 推理精炼 |
| `src/agents/core/reasoning_validator/temporal_reasoning.py` | 512-513 | temperature=0.1, max_tokens=500 | 时序推理 |
| `src/agents/core/reasoning_validator/temporal_reasoning.py` | 623-624 | temperature=0.1, max_tokens=400 | 时序推理2 |
| `src/agents/core/reasoning_validator/identity_reasoning.py` | 132-133 | temperature=0.3, max_tokens=500 | 身份推理 |
| `src/agents/core/reasoning_validator/multi_hop_reasoning.py` | 181-182 | temperature=0.4, max_tokens=600 | 多跳推理 |
| `src/agents/core/reasoning_validator/retrieval_guidance.py` | 129 | max_tokens=100, temperature=0 | 检索引导 |
| `src/agents/core/consolidation/inference.py` | 74-75 | max_tokens=600, temperature=0.2 | 事实整合推理 |
| `src/agents/core/consolidation/inference.py` | 165-166 | max_tokens=600, temperature=0.1 | 身份推理 |
| `src/agents/core/perception_encoding.py` | 431-432 | max_tokens=150, temperature=0.3 | 感知编码 |
| `src/agents/core/perception_encoding.py` | 528-529 | max_tokens=300, temperature=0.3 | 感知编码2 |
| `src/coordination/brain_retrieval_integration.py` | 1416-1417 | temperature=0, max_tokens=200 | 脑区检索整合 |
| `src/coordination/memory_consolidation.py` | 402-403 | temperature=0.3, max_tokens=100 | 记忆巩固 |
| `src/coordination/adaptive_config.py` | 276-277 | temperature=0.0, max_tokens=100 | 自适应配置分析 |
| `src/coordination/memory_retrieval.py` | 603 | max_tokens=300 | 记忆检索 |
| `src/coordination/clean_agent_system.py` | 376 | max_tokens=600 | Agent系统LLM调用 |
| `src/coordination/clean_agent_system.py` | 408 | max_tokens=50, temperature=0.3 | 快速分类 |
| `src/coordination/clean_agent_system.py` | 617 | max_tokens=200 | 摘要生成 |
| `src/coordination/brain_coordinator_refactored.py` | 2035 | temperature=0.0, max_tokens=30 | 答案精炼 |
| `src/coordination/brain_coordinator_refactored.py` | 3374 | temperature=0.0, max_tokens=50 | 语言转换 |
| `src/coordination/memory_storage.py` | 165 | max_tokens=2000 | 记忆存储分析 |
| `src/coordination/memory_storage.py` | 319 | max_tokens=200 | 记忆存储 |
| `src/coordination/memory_storage.py` | 1031 | max_tokens=200 | 记忆存储 |
| `src/coordination/semantic_router.py` | 78 | temperature=0.0 | 语义路由 |
| `src/brain/collaborative_output.py` | 288-289 | temperature=0.1, max_tokens=200 | 协作输出 |
| `src/brain/collaborative_output.py` | 446-447 | temperature=0.3, max_tokens=100 | 协作输出2 |
| `src/brain/collaborative_output.py` | 512-513 | temperature=0.2, max_tokens=150 | 协作输出3 |
| `src/brain/collaborative_output.py` | 589-590 | temperature=0.2, max_tokens=200 | 协作输出4 |
| `src/brain/collaborative_output.py` | 729-730 | temperature=0.1, max_tokens=50 | 协作输出5 |
| `src/brain/region_activation.py` | 172-173 | temperature=0.1, max_tokens=300 | 脑区激活分析 |
| `src/brain/region_activation.py` | 308-309 | temperature=0.2, max_tokens=400 | 脑区激活2 |
| `src/brain/hippocampal_loop.py` | 342-343 | temperature=0.2, max_tokens=300 | 海马环路推理 |
| `src/brain/semantic_memory_tagger.py` | 90 | temperature=0.1, max_tokens=300 | 语义记忆标注 |
| `src/evaluation/ai_evaluator.py` | 217-218 | temperature=0.1, max_tokens=500 | AI评估 |
| `src/reasoning/memory_reasoning_chain.py` | 792-793 | temperature=0.3, max_tokens=500 | 记忆推理链 |
| `src/reasoning/capability_analyzer.py` | 269-270 | temperature=0.2, max_tokens=500 | 能力分析 |
| `src/reasoning/conditional_constraint_engine.py` | 179 | temperature=0.2, max_tokens=800 | 约束引擎 |
| `src/reasoning/input_analyzer.py` | 97 | temperature=0.1, max_tokens=300 | 输入分析 |
| `src/reasoning/capability_orchestrator/basic_capabilities.py` | 99-100 | temperature=0.1, max_tokens=300 | 基础能力分析 |
| `src/reasoning/capability_orchestrator/reasoning_capabilities.py` | 82+ | temperature=0.2, max_tokens=400 | 推理能力(~10处调用) |
| `src/reasoning/capability_orchestrator/answer_synthesis.py` | 145-146 | temperature=0.0, max_tokens=10 | 答案合成决策 |
| `src/reasoning/capability_orchestrator/answer_synthesis.py` | 220 | temperature=0.1, max_tokens=10 | 答案选择 |
| `src/reasoning/capability_orchestrator/answer_synthesis.py` | 272 | temperature=0.1, max_tokens=50 | 答案抽取 |

---

## 2. 阈值 (Thresholds)

### 相似度阈值

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/agents/brain_regions/hippocampus_agent/forgetting.py` | 55-57 | default=0.85, min=0.6 | 遗忘相似度阈值 |
| `src/agents/brain_regions/hippocampus_agent/advanced_search/temporal_ranking.py` | 31 | 0.70 | 语义相似度最低阈值 |
| `src/agents/brain_regions/hippocampus_agent/advanced_search/event_boundary_fallback.py` | 54 | 0.3 (base) | 话题转换相似度 |
| `src/agents/brain_regions/hippocampus_agent/advanced_search/event_boundary_fallback.py` | 67 | 0.2 (base) | 关键词重叠阈值 |
| `src/agents/brain_regions/hippocampus_agent/hippocampus_hrm_extension.py` | 203 | 0.8 | HRM置信度阈值 |
| `src/agents/brain_regions/hippocampus_agent/hippocampus_hrm_extension.py` | 547 | 0.8 (80%) | 收敛稳定性阈值 |
| `src/agents/brain_regions/basal_ganglia_hrm_extension.py` | 98 | 3 | 固定点出现次数阈值 |
| `src/agents/brain_regions/basal_ganglia_hrm_extension.py` | 368/370 | 0.8, 0.5 | 收敛比率阈值 |
| `src/agents/brain_regions/basal_ganglia_hrm_extension.py` | 404 | 0.7 | 模式匹配相似度 |
| `src/agents/core/long_term_memory.py` | 164/209 | 0.4 | 向量搜索相似度 |
| `src/agents/core/long_term_memory.py` | 472 | 0.3 | 宽范围搜索阈值 |
| `src/agents/core/memory_retrieval/strategies/semantic_retrieval.py` | 124 | 0.15 | 低语义相似度阈值 |
| `src/agents/core/memory_retrieval/strategies/pattern_completion.py` | 64 | 0.2 | 模式补全阈值 |
| `src/agents/core/memory_retrieval/strategies/contextual_retrieval.py` | 79 | 0.3 | 上下文过滤阈值 |
| `src/agents/core/persona_memory.py` | 220 | 0.10 | 人格记忆检索低阈值 |
| `src/agents/core/persona_memory.py` | 473 | 0.25 | 中等人格搜索阈值 |
| `src/agents/core/persona_memory.py` | 590 | 0.35 | 去重检测阈值 |
| `src/memory/memory_system/semantic_search.py` | 127 | 0.15 | 重试低阈值 |
| `src/memory/memory_system/semantic_search.py` | 136 | 0.05 | 超低回退阈值 |
| `src/memory/brain_regions/hippocampal_event_graph.py` | 82-83 | similarity=0.7, min_separation=0.3 | 事件图相似度/分离度 |
| `src/memory/preference_aware_retrieval.py` | 232 | 0.4 | 心智理论阈值 |
| `src/memory/preference_aware_retrieval.py` | 242 | 0.85 | 默认偏好阈值 |
| `src/memory/contrastive_key_optimizer.py` | 604 | 0.5 | 相似度检查阈值 |
| `src/systems/external_memory_system.py` | 211 | 0.3 | 外部记忆相似度阈值 |

### 注意力/显著性阈值

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/agents/environment/stimulus_processor.py` | 67 | 0.3 | 注意力过滤阈值 |
| `src/agents/environment/stimulus_processor.py` | 221-227 | 0.8, 0.6, 0.4, 0.2 | 显著性等级阈值 |

### 记忆失真阈值

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/agents/core/memory_distortion/memory_distortion.py` | 46-47 | distortion=0.3, false_memory=0.7 | 记忆失真检测 |
| `src/agents/core/memory_distortion/false_memory.py` | 79 | 0.4 | 污染分数阈值 |
| `src/agents/core/memory_distortion/source_confusion.py` | 69 | 0.6 | 来源真实性阈值 |
| `src/agents/core/memory_distortion/source_confusion.py` | 150 | 0.7, 0.4 | 置信度分级阈值 |
| `src/agents/core/memory_distortion/source_confusion.py` | 184-190 | 0.8, 0.6, 0.4, 0.2 | 分数区间阈值 |
| `src/agents/core/memory_distortion/distortion_detection.py` | 79-85 | 1, 7, 30, 365 (天) | 年龄风险区间 |
| `src/agents/core/memory_distortion/distortion_detection.py` | 176-180 | 0.8, 0.5, 0.3 | 风险等级阈值 |

### 容量压力阈值

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/agents/brain_regions/hippocampus_agent/forgetting.py` | 109/111 | 0.9, 0.7 | 容量压力阈值 |
| `src/optimization/capacity_manager.py` | 271 | 70, 90 (%) | 容量使用警告阈值 |
| `src/optimization/capacity_manager.py` | 159 | 10000000 | 上限安全检查 |

### 协调层阈值

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/coordination/brain_retrieval_integration.py` | 996 | 0.6 | 检索质量阈值 |
| `src/coordination/dataset_aware_config.py` | 62/79/96/112/127 | 0.80 | KG覆盖阈值(重复5次) |
| `src/coordination/memory_consolidation.py` | 45 | 3 | 巩固触发命中数 |
| `src/coordination/memory_consolidation.py` | 46 | 5 | 语义抽取命中数 |
| `src/coordination/memory_consolidation.py` | 49 | 0.3 | 遗忘衰减阈值 |
| `src/coordination/soul_state.py` | 971-972 | calm=0.7, critical=0.9 | 情绪调节阈值 |
| `src/coordination/proactive_inquiry.py` | 68-70 | contradiction=0.6, inquiry=0.7, low_confidence=0.4 | 主动询问阈值 |
| `src/coordination/clean_agent_system.py` | 474-475 | relative=0.5, absolute=3.0 | 记忆过滤阈值 |
| `src/coordination/result_arbiter.py` | 52-53 | missing_keyword=0.5, low_confidence=0.3 | 结果质量阈值 |
| `src/coordination/brain_coordinator_refactored.py` | 650 | 0.6 | 脑协调器置信度阈值 |
| `src/coordination/brain_coordinator_refactored.py` | 2970 | 0.6 | 不确定性决策阈值 |

### 其他阈值

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/agents/brain_regions/hippocampus_agent/advanced_search/event_boundary.py` | 62 | 6.0 (小时) | 事件边界时间间隔 |
| `src/agents/core/long_term_memory.py` | 519/521 | 5, 10 | 巩固引用次数阈值 |
| `src/agents/core/reflection/scenario_simulation.py` | 44 | 0.4 | 推测置信度阈值 |
| `src/agents/core/reflection/reflection.py` | 81 | 0.4 | 模式检测阈值 |
| `src/agents/core/context_compaction.py` | 43 | 10 | 压缩触发轮数 |
| `src/agents/core/reasoning_validator/retrieval_feedback.py` | 28 | 0.5 | 反馈置信度阈值 |
| `src/agents/core/forgetting/core.py` | 37 | 0.2 | 遗忘重要性阈值 |
| `src/agents/core/forgetting/core.py` | 39 | 0.7 | 记忆干扰检测阈值 |
| `src/agents/core/multi_round_retrieval.py` | 132 | 0.6 | 扩展平均分阈值 |
| `src/agents/core/multi_round_retrieval.py` | 211 | 0.7 | 追加检索置信度 |
| `src/agents/core/short_term_memory.py` | 367/369 | 20, 30 (秒) | STM衰减时间区间 |
| `src/optimization/fast_path.py` | 146 | 0.6 | 快速路径相关性阈值 |
| `src/optimization/fast_path.py` | 335 | 0.85 | 高置信快速路径阈值 |
| `src/optimization/metacognition.py` | 438-444 | 0.8, 0.6, 0.4, 0.2 | 置信度区间阈值 |
| `src/optimization/metacognition.py` | 711 | 0.5 | 平均置信度警报 |
| `src/services/openai_embedding_service.py` | 51 | 10 | 批量写入累积阈值 |
| `src/brain/brain_network.py` | 359 | 0.5 | 脑网络激活阈值 |
| `src/brain/region_activation.py` | 79 | 0.6 | 赢者通吃阈值 |
| `src/brain/hippocampal_loop.py` | 448 | 0.35 | 海马检索阈值 |
| `src/brain/hippocampal_loop.py` | 486 | 0.4 | 优化召回阈值 |
| `src/brain/hippocampal_loop.py` | 506 | 0.4 | 关键词检索阈值 |

---

## 3. 权重与评分 (Weights & Scoring)

### 检索评分权重

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/agents/brain_regions/hippocampus_agent/retrieval.py` | 311 | 0.5 | 部分匹配分数 |
| `src/agents/brain_regions/hippocampus_agent/retrieval.py` | 575/577 | 0.15, 0.1 | KG关系匹配加分 |
| `src/agents/brain_regions/hippocampus_agent/retrieval.py` | 605 | 0.15 | 协作加分因子 |
| `src/agents/brain_regions/hippocampus_agent/retrieval.py` | 638/641/644/647 | 1.0, 0.5, 0.2, 0.1 | 时序优先级加分层级 |
| `src/agents/brain_regions/hippocampus_agent/hippocampus_hrm_extension.py` | 476 | 0.3, 0.5, 0.2 | 置信度计算权重 |
| `src/agents/brain_regions/hippocampus_agent/advanced_search/temporal_candidate_retrieval.py` | 198-262 | 3.0, 1.5, 1.0, 0.5, 2.0, 0.0 | 时序评分权重(多个) |
| `src/agents/brain_regions/hippocampus_agent/advanced_search/entity_action_ranking.py` | 91/93 | 0.6, 0.3 | 实体匹配评分 |
| `src/agents/brain_regions/temporal_lobe_agent/search.py` | 113/116 | 1.2, 0.5 | BM25分数乘数 |
| `src/agents/brain_regions/temporal_lobe_agent/search.py` | 135 | 0.7, 0.3 | BM25 vs 嵌入 混合权重 |
| `src/agents/brain_regions/thalamus_agent.py` | 695/698/701 | 1.5, 0.7, 1.0 | 复杂度调整因子 |
| `src/agents/brain_regions/anterior_cingulate_agent.py` | 456 | 0.3 | 冲突惩罚分 |
| `src/agents/brain_regions/anterior_cingulate_agent.py` | 632 | 0.05 | 置信度增量阈值 |
| `src/agents/brain_regions/tom_advisor.py` | 118 | min(0.95, 0.5+max_score*0.15) | 置信度计算公式 |

### 上下文评分权重

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/agents/core/memory_retrieval/strategies/contextual_retrieval.py` | 142-182 | 0.3, 0.2, 0.2, 0.15, 0.1, 0.05 | 上下文评分组件权重 |
| `src/agents/core/memory_retrieval/strategies/associative_retrieval.py` | 99 | 0.3 | 联想匹配加分 |
| `src/agents/core/memory_retrieval/confidence/confidence_calculator.py` | 151 | 0.7 + 0.6 * importance | 重要性因子公式 |
| `src/agents/core/memory_retrieval/confidence/confidence_calculator.py` | 169 | 1.0 + min(0.2, log/10) | 访问因子公式 |

### 记忆失真权重

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/agents/core/memory_distortion/false_memory.py` | 126/128 | 0.4, 0.2 | 时间邻近污染分数 |
| `src/agents/core/memory_distortion/source_confusion.py` | 125-135 | 0.2, 0.15 (多处) | 来源混淆评分组件 |

### 人格与情绪权重

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/agents/core/persona_memory.py` | 251 | 0.05 + pref_boost * 0.30 | 人格类别加分公式 |
| `src/agents/core/persona_memory.py` | 259-268 | 0.7, 0.9, 0.8, 0.15 | 类别特定加分乘数 |
| `src/agents/core/stress_response/threat_detection.py` | 105-180 | 0.6, 0.5, 0.2, 1.2, 0.7 | 威胁评分组件 |
| `src/agents/core/stress_response/threat_detection.py` | 268/272/276 | 0.5, 0.6, 0.3 | 情绪状态更新乘数 |
| `src/agents/core/stress_response/emotional_processing.py` | 170 | 0.1 | 负面情绪加分 |
| `src/agents/core/stress_response/regulation_strategies.py` | 67-72 | 0.8, 0.6, 0.4 | 威胁等级阈值 |
| `src/agents/core/mbti_personality/interaction.py` | 105 | 0.2 | 单次交互最大人格变化 |

### 遗忘权重

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/agents/core/forgetting/pruning.py` | 201/205/207 | 0.1, 0.1, -0.05 | 修剪分数调整 |
| `src/agents/core/forgetting/context_dependent.py` | 128-152 | 0.3, 0.3, 0.2, 0.2 | 上下文匹配评分组件 |
| `src/agents/core/forgetting/context_dependent.py` | 179 | 0.6 + match * 0.4 | 上下文衰减因子公式 |
| `src/agents/core/forgetting/interference.py` | 232/234 | 0.3, 0.2 | 干扰评分 |
| `src/agents/core/forgetting/motivated_forgetting.py` | 436 | 0.3 | 动机遗忘分数 |

### 巩固权重

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/agents/core/consolidation/rehearsal.py` | 56 | 0.1 | 强回放重要性加分 |
| `src/agents/core/consolidation/rehearsal.py` | 121 | 0.1, 0.05 | 巩固加分值 |

### 协调层权重

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/coordination/storage_router.py` | 213-255 | 0.4, 0.2, 0.25, 0.3, 0.35, 0.1 | 记忆存储评分权重(多处) |
| `src/coordination/routing_manager.py` | 245-517 | 0.3, 0.15, 0.2, 0.5, 0.6, 0.4 | 路由策略评分权重(大量) |
| `src/coordination/brain_retrieval_integration.py` | 211 | (quality - 0.5) * 2 | 奖励信号映射公式 |
| `src/coordination/brain_retrieval_integration.py` | 1317/1326 | 0.5, 0.10 | 实体奖励和缩放 |
| `src/coordination/brain_retrieval_integration.py` | 1331/1333 | 1.05, 1.08 | 分数乘数 |
| `src/coordination/brain_retrieval_integration.py` | 1474 | 0.05 | 问题间隔惩罚 |
| `src/coordination/adaptive_config.py` | 105 | 0.1 + 0.7 * pref_score | 偏好权重公式 |
| `src/coordination/adaptive_config.py` | 108 | 0.05 + 0.45 * pref_score | 偏好加分公式 |
| `src/coordination/adaptive_config.py` | 112/119/129/130 | 0.4+0.6*s, 0.6+0.4*s | 自适应权重公式 |
| `src/coordination/dataset_aware_config.py` | 74/91/107 | 0.3, 0.3, 0.2 | 数据集特定偏好权重 |
| `src/coordination/brain_coordinator_refactored.py` | 618 | 0.3 | 默认偏好加分权重 |
| `src/memory/preference_aware_retrieval.py` | 343 | 0.5 | 偏好分数激活乘数 |
| `src/memory/forgetting_coordinator.py` | 374/377/384 | (多个) | 重要性/访问/情绪因子公式 |
| `src/memory/metamemory.py` | 780 | 1.5 | 元记忆加分因子 |

---

## 4. 搜索K值 (Search K)

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/agents/brain_regions/hippocampus_agent/advanced_search/temporal_candidate_retrieval.py` | 365 | k=50 | 时序候选宽搜索 |
| `src/agents/brain_regions/hippocampus_agent/advanced_search/entity_action_retrieval.py` | 59 | k=50 | 实体动作宽搜索 |
| `src/agents/brain_regions/hippocampus_agent/hippocampus_hrm_extension.py` | 207-214 | k=10, 7, 5, 10 | HRM搜索阶段 |
| `src/agents/brain_regions/thalamus_agent.py` | 511 | k=5 | 丘脑区域搜索 |
| `src/agents/core/long_term_memory.py` | 163/208/471 | k=5, 5, 10 | 长期记忆搜索 |
| `src/agents/core/persona_memory.py` | 472/590 | k=5, k=5 | 人格记忆搜索 |
| `src/agents/core/personality/core.py` | 196 | k=3 | 人格检索 |
| `src/agents/core/reasoning_validator/general_reasoning.py` | 94 | k=10 | 通用推理搜索 |
| `src/agents/core/reasoning_validator/temporal_reasoning.py` | 565 | k=5 | 时序推理搜索 |
| `src/agents/core/reasoning_validator/identity_reasoning.py` | 152 | k=10 | 身份推理搜索 |
| `src/agents/core/learnable_router.py` | 405/428/439 | top_k=2 | 可学习路由选择 |
| `src/coordination/brain_retrieval_integration.py` | 719 | k=5 | 脑区检索时序搜索 |
| `src/coordination/brain_coordinator_refactored.py` | 2278 | top_k=4 | 可学习路由top-k |
| `src/coordination/brain_coordinator_refactored.py` | 2357 | max_memories=20 | 整合最大记忆数 |
| `src/coordination/brain_coordinator_refactored.py` | 3132 | max_results=3 | 探索最大结果数 |
| `src/coordination/adaptive_config.py` | 123/126 | 5+int(15*score) | 自适应人格/情景k(5-20) |
| `src/coordination/dataset_aware_config.py` | 60/77/94/110/125 | 3, 8, 15, 8, 5 | 数据集特定检索k |
| `src/coordination/kg_merge_config.py` | 346 | plasticity_top_k=15 | KG合并可塑性top-k |
| `src/brain/hippocampal_loop.py` | 258 | top_k=30 | 海马环路排序top-k |
| `src/brain/hippocampal_loop.py` | 447/505 | k=8, k=5 | 海马环路检索k |
| `src/memory/preference_evolution.py` | 642-647 | top_k=10, 5, 10, 5, 5, 10 | 偏好检索k(按类型) |
| `src/reasoning/capability_orchestrator/reasoning_capabilities.py` | 545 | k=30 | 推理能力宽搜索 |

---

## 5. 容量与大小限制 (Capacity & Limits)

### 记忆类型容量

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/optimization/capacity_manager.py` | 93-126 | 10, 20000, 100000, 1000, 500 | 各记忆类型最大条目 |
| `src/optimization/capacity_manager.py` | 94-126 | 7, 50, 100, 20, 10 | 各记忆类型最大上下文条目 |
| `src/coordination/brain_coordinator_refactored.py` | 894-922 | 70000, 20000, 1000, 10, 500 | 脑区存储容量 |
| `src/brain/distributed_memory.py` | 194-198 | 500, 1000, 50, 300, 200 | 区域记忆存储容量 |
| `src/memory/adaptive_memory_shaping.py` | 149/151 | 20000, 70000 | 海马/颞叶容量 |
| `src/memory/preference_aware_retrieval.py` | 241 | max_engrams=5000 | 最大engram数 |
| `src/core/constants.py` | 37-40 | 50000, 5000, 10000, 1000 | 各脑区最大条目(常量) |
| `src/core/constants.py` | 43-45 | 100, 1000, 1000 | 最大历史限制(常量) |
| `src/core/constants.py` | 48 | MAX_ENGRAMS = 10000 | 最大engram数(常量) |

### 缓存与历史限制

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/memory/storage_adapter.py` | 86 | 1000 | 存储缓存大小 |
| `src/memory/storage_coordinator.py` | 78 | 100 | 存储历史限制 |
| `src/utils/semantic_cache.py` | 763/777 | 500, 1000 | 语义缓存大小(KG/实体) |
| `src/agents/core/memory_retrieval/cache/lru_cache_manager.py` | 26 | 200 | LRU缓存默认大小 |
| `src/agents/core/context_compaction.py` | 40 | 10 | 压缩最大历史 |
| `src/agents/environment/environment_agent/core.py` | 51 | 1000 | 环境历史限制 |
| `src/coordination/brain_retrieval_integration.py` | 119 | 100 | 检索整合历史 |
| `src/coordination/learning_manager.py` | 45 | 1000 | 学习历史限制 |

### 其他限制

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/coordination/result_arbiter.py` | 50-51 | min=5, max=500 | 答案长度范围 |
| `src/coordination/proactive_inquiry.py` | 71 | 2 | 每轮最大主动询问 |
| `src/api/routes/archives.py` | 25 | 500MB | 上传大小限制 |
| `src/services/sentence_splitter.py` | 24/26 | min=10, max=200 | 句子分块长度范围 |
| `src/systems/external_memory_system.py` | 122 | 1000 | 外部记忆分块大小 |
| `src/api/routes/brain.py` | 208 | 50 | 流式分块大小(字符) |
| `src/core/constants.py` | 56 | 8000 | 最大上下文token |
| `src/core/constants.py` | 59 | 500 | 最大答案长度 |

---

## 6. 衰减率 (Decay Rates)

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/agents/core/memory_distortion/false_memory.py` | 26 | 0.9 | 高衰减率(快速遗忘) |
| `src/agents/core/memory_distortion/false_memory.py` | 105 | 0.95 | 虚假记忆衰减率 |
| `src/agents/core/stress_response/trauma_handler.py` | 35 | 0.01 | 极慢创伤记忆衰减 |
| `src/agents/core/short_term_memory.py` | 59 | 0.1 | STM每秒衰减10% |
| `src/agents/core/short_term_memory.py` | 358 | 0.5^(t/15) | STM半衰期15秒 |
| `src/agents/core/forgetting/context_dependent.py` | 179 | 0.6 + match * 0.4 | 上下文衰减因子 |
| `src/agents/core/consolidation/data_models.py` | 53 | 0.05 | 巩固强度衰减 |
| `src/agents/core/consolidation/data_models.py` | 51-52 | initial=0.3, boost=0.15 | 巩固强度参数 |
| `src/agents/core/consolidation/memory_strengthening.py` | 193-201 | 0.5, 1.0, 0.8, 0.6 | 近因因子层级 |
| `src/agents/brain_regions/hippocampus_agent/forgetting.py` | 56 | 0.005/天 | 每日阈值衰减 |

---

## 7. 时间与间隔 (Timing & Intervals)

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/agents/environment/data_sources.py` | 318/362/492 | timeout=10 | HTTP请求超时(3处) |
| `src/services/shared_openai_client.py` | 44/61 | timeout=30.0 | OpenAI客户端超时 |
| `src/coordination/message_bus.py` | 124 | timeout=0.5 | 消息总线获取超时 |
| `src/core/config.py` | 317/324 | 5.0, 5.0 | 测试模式超时 |
| `src/agents/base.py` | 140 | max_retries=15 | LLM调用重试限制 |
| `src/coordination/coordinator_v2.py` | 186 | 3600 (秒) | 后台循环1小时间隔 |
| `src/coordination/learning_manager.py` | 39 | 1800 | 30分钟学习间隔 |
| `src/coordination/learning_manager.py` | 178 | 60 | 错误恢复等待 |
| `src/agents/brain_regions/prefrontal_agent/prefrontal_hrm_extension.py` | 77 | 10 | HRM战略更新步数 |
| `src/agents/brain_regions/temporal_lobe_agent/temporal_lobe_hrm_extension.py` | 78 | 10 | HRM巩固步数 |
| `src/core/constants.py` | 67 | 300 | 询问冷却5分钟 |
| `src/core/constants.py` | 70-72 | 3600, 7200, 1800 | 巩固/遗忘/再巩固间隔 |
| `src/core/constants.py` | 76-77 | 2.0, 5.0, 10.0 | 负载缩放因子和最小间隔 |
| `src/agents/core/consolidation/data_models.py` | 46 | 300 | 最小排练间隔(5分钟) |

---

## 8. 模型名称与URL (Models & URLs)

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/core/constants.py` | 111 | `"gpt-4o-mini"` | 默认LLM模型 |
| `src/core/constants.py` | 112 | `"text-embedding-3-small"` | 默认嵌入模型 |
| `src/core/constants.py` | 115 | `"gpt-4"` | 默认分词器模型 |
| `src/core/constants.py` | 118 | `"qwen3.5-35b"` | 默认本地LLM模型 |
| `src/core/constants.py` | 119 | `http://localhost:8000/v1` | 本地LLM基础URL |
| `src/core/constants.py` | 123 | `"en_core_web_sm"` | SpaCy模型 |
| `src/core/constants.py` | 144-145 | 8080, 8000 | 默认Web UI和API端口 |
| `src/integrations/openclaw_plugin.py` | 7/43 | `http://localhost:8100` | OpenClaw集成URL |
| `src/integrations/langchain_adapter.py` | 7/45/118 | `http://localhost:8100` | LangChain适配器URL |
| `src/services/remote_brain_service.py` | 26 | `http://localhost:8000` | 远程脑服务URL |
| `src/services/tts_backends/openai_tts.py` | 32 | `https://api.openai.com/v1` | OpenAI TTS回退URL |

---

## 9. 学习率 (Learning Rates)

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/agents/brain_regions/basal_ganglia_hrm_extension.py` | 441 | alpha=0.3 | 基底节学习率 |
| `src/agents/core/learnable_router.py` | 391 | 0.05 | 可学习路由学习率 |
| `src/coordination/routing_manager.py` | 56 | 0.1 | 路由管理器学习率 |
| `src/coordination/brain_coordinator_refactored.py` | 572 | 0.05 | 脑协调器路由学习率 |
| `src/coordination/memory_analysis.py` | 229 | beta=0.6 | 记忆分析beta参数 |
| `src/brain/habit_learner.py` | 53 | alpha=0.1 | 习惯学习率 |
| `src/memory/preference_aware_retrieval.py` | 223 | 0.01 | 偏好学习率 |

---

## 10. 遗忘比率 (Forgetting Ratios)

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/agents/brain_regions/hippocampus_agent/forgetting.py` | 110/112/114 | 0.3, 0.2, 0.1 | 按压力等级遗忘比率(30%/20%/10%) |
| `src/memory/forgetting_coordinator.py` | 299/301/303 | 0.3, 0.2, 0.1 | 相同遗忘比率(**重复代码!**) |

---

## 11. HRM 收敛参数

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/agents/brain_regions/hippocampus_agent/hippocampus_hrm_extension.py` | 84 | convergence_window=3 | 收敛检查窗口 |
| `src/agents/brain_regions/amygdala_hrm_extension.py` | 85 | convergence_window=3 | 收敛检查窗口 |
| `src/agents/brain_regions/basal_ganglia_hrm_extension.py` | 99 | convergence_window=5 | 稳定性检查窗口 |

---

## 12. 记忆巩固参数 (Consolidation)

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/agents/core/consolidation/data_models.py` | 46 | min_interval: 300 | 最小排练间隔 |
| `src/agents/core/consolidation/data_models.py` | 47 | max_rehearsals: 5 | 最大排练次数 |
| `src/agents/core/consolidation/data_models.py` | 48 | spacing_factor: 2.0 | 间隔增长因子 |
| `src/agents/core/consolidation/data_models.py` | 51 | initial: 0.3 | 初始记忆强度 |
| `src/agents/core/consolidation/data_models.py` | 52 | rehearsal_boost: 0.15 | 每次排练强度增量 |
| `src/agents/core/consolidation/data_models.py` | 53 | decay_rate: 0.05 | 强度衰减率 |
| `src/agents/core/consolidation/data_models.py` | 56 | threshold: 0.6 | 巩固触发阈值 |
| `src/agents/core/consolidation/data_models.py` | 57 | replay_capacity: 50 | 回放缓冲区容量 |
| `src/agents/core/consolidation/data_models.py` | 58 | batch_size: 10 | 巩固批大小 |

---

## 13. 工作记忆容量 (Working Memory)

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/agents/brain_regions/prefrontal_agent/prefrontal_agent.py` | 22 | min_capacity: 7 | Miller定律下限 |
| `src/agents/brain_regions/prefrontal_agent/prefrontal_agent.py` | 23 | default_capacity: 10 | 默认工作记忆槽位 |
| `src/agents/brain_regions/prefrontal_agent/prefrontal_agent.py` | 24 | max_capacity: 15 | 上限 |
| `src/agents/brain_regions/prefrontal_agent/prefrontal_agent.py` | 25-27 | 7, 10, 15 | 复杂度依赖容量 |
| `src/agents/brain_regions/prefrontal_agent/prefrontal_agent.py` | 28 | auto_compress: 0.8 | 80%满时触发压缩 |

---

## 14. KG 合并配置

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/coordination/kg_merge_config.py` | 269-273 | word_count=3, overlap=0.6, max=15, plasticity=0.3 | 保守合并策略 |
| `src/coordination/kg_merge_config.py` | 289-292 | word_count=1, overlap=0.8, max=25 | 激进合并策略 |
| `src/coordination/kg_merge_config.py` | 311-315 | word_count=2, overlap=0.7, max=20, plasticity=0.1 | 平衡合并策略 |
| `src/coordination/kg_merge_config.py` | 342-347 | word_count=2, overlap=0.7, max=20, top_k=15, plasticity=0.2 | 默认合并策略 |
| `src/coordination/kg_merge_config.py` | 508 | max_merged_results=15 | 覆盖合并结果数 |
| `src/coordination/kg_merge_handler.py` | 241 | max_depth=2 | 多跳查询深度 |

---

## 15. 迭代限制 (Iteration Limits)

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/coordination/memory_coordinator.py` | 66 | max_iterations=3 | 记忆协调器迭代 |
| `src/coordination/brain_coordinator_refactored.py` | 587 | max_iterations=5 | 脑协调器最大迭代 |
| `src/coordination/brain_coordinator_refactored.py` | 2335 | max_iterations=2 | 多轮扩展限制 |
| `src/reasoning/capability_orchestrator/core_execution.py` | 59 | max_iterations=3 | 能力协调器迭代 |

---

## 16. 批处理大小 (Batch Sizes)

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/coordination/brain_coordinator_refactored.py` | 145/1060 | batch_size=50 | 记忆处理批大小 |
| `src/coordination/learning_manager.py` | 270 | batch_size=30 | 学习批大小 |
| `src/core/constants.py` | 20-21 | chunk=1000, overlap=150 | 文本分块默认值 |
| `src/services/tts_backends/openai_tts.py` | 57 | chunk_size=4096 | 音频流分块 |
| `src/agents/brain_regions/hippocampus_agent/consolidation.py` | 249 | [:100] | 巩固候选处理限制 |

---

## 17. 嵌入维度 (Embedding Dimension)

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/core/constants.py` | 113 | 1536 | OpenAI嵌入维度 |
| `src/core/constants.py` | 114 | 8191 | 最大嵌入输入长度 |
| `src/core/adapters/vector_database_adapter.py` | 33 | 1536 | FAISS维度(**应引用常量!**) |

---

## 18. 文本截断限制 (Truncation)

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/utils/knowledge_graph_builder.py` | 320 | text[:3000] | KG构建文本截断 |
| `src/agents/brain_regions/temporal_lobe_agent/extractors.py` | 31/59/95 | [:3000] | 会话文本截断(LLM输入) |
| `src/agents/brain_regions/temporal_lobe_agent/extractors.py` | 39/75/105 | [:10] | 结果列表限制 |

---

## 19. 置信度初始值 (Confidence)

| 文件 | 行号 | 值 | 用途 |
|---|---|---|---|
| `src/agents/brain_regions/theory_of_mind_agent.py` | 294/369 | 0.3 | 对抗/欺骗默认低置信度 |
| `src/agents/brain_regions/theory_of_mind_agent.py` | 650 | 0.5 | 默认中等置信度 |
| `src/agents/brain_regions/basal_ganglia_hrm_extension.py` | 459 | 0.5 | 固定点初始置信度 |
| `src/agents/core/memory_distortion/reconstruction_errors.py` | 109 | 0.3 | 基础重建置信度 |
| `src/agents/core/reflection/scenario_simulation.py` | 294 | 0.3 | 基础场景置信度 |
| `src/optimization/fast_path.py` | 168 | 0.7 | 快速路径默认置信度 |
| `src/optimization/metacognition.py` | 381 | 1.0 / 0.5 | KG关系存在置信度 |
| `src/agents/environment/data_sources.py` | 221-509 | 0.8, 0.7, 0.9, 0.85, 0.95 | 数据源置信度级别 |

---

## 统计总结

| 类别 | 数量 | 涉及文件 | 严重程度 |
|---|---|---|---|
| LLM参数 (temperature/max_tokens) | ~80+ | ~40 | ⚠️⚠️⚠️ 最严重 |
| 阈值 | ~70+ | ~35 | ⚠️⚠️⚠️ |
| 权重/评分 | ~60+ | ~20 | ⚠️⚠️ |
| 搜索K值 | ~30+ | ~20 | ⚠️⚠️ |
| 容量/大小限制 | ~30+ | ~15 | ⚠️ |
| 衰减率 | ~10 | ~6 | ⚠️ |
| 时间/间隔 | ~15 | ~10 | ⚠️ |
| 模型/URL | ~11 | ~6 | ⚠️ |
| 学习率 | ~7 | ~7 | ⚠️ |
| 其他(遗忘/HRM/巩固等) | ~40+ | ~15 | ⚠️ |
| **总计** | **~350+** | **~70+** | |

### 关键发现

1. **LLM参数是重灾区** — 几乎每个调用 `call_llm()` 的地方都有内联的 temperature 和 max_tokens，而非引用中心化配置
2. **`src/core/constants.py` 已部分集中** — 模型名、端口、间隔、区域限制已在此文件，但大量值仍散落各处
3. **重复代码** — 遗忘比率在 `hippocampus_agent/forgetting.py` 和 `memory/forgetting_coordinator.py` 中完全重复
4. **FAISS维度硬编码** — `vector_database_adapter.py` 硬编码了 1536 而非引用 `constants.py` 中的常量
5. **权重公式散落** — `routing_manager.py` 和 `storage_router.py` 中有大量魔法数字
6. **容量不一致** — `constants.py`、`capacity_manager.py`、`brain_coordinator_refactored.py`、`distributed_memory.py` 对同一脑区定义了不同的容量值
