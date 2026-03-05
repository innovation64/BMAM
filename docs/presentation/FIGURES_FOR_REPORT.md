# BMAM 汇报配图（Mermaid 源码，可直接复制）

说明：以下四张图覆盖“方案/原理/执行/评测”四个角度，适合插入汇报PPT或支持 Mermaid 的Markdown文档。若目标工具不支持Mermaid，可将代码粘贴到 mermaid.live 生成SVG/PNG。

---

## 图1 类脑多智能体总览（协调层—脑区—机制—记忆层）

```mermaid
flowchart LR
  classDef box fill:#f6f8fa,stroke:#999,stroke-width:1px,color:#333;

  subgraph CL[协调层]
    C[前额叶样路由/调度]
  end

  subgraph BA[脑区智能体]
    H[海马体\n情节编码]
    T[颞叶\n语义存储]
    P[前额叶\n工作记忆]
    A[杏仁核\n情绪标注]
  end

  subgraph ME[记忆机制]
    EN[编码]
    CO[巩固]
    RE[重塑]
    FO[遗忘]
  end

  subgraph MEM[记忆存储层]
    ST[短期记忆]
    LT[长期记忆/语义图]
  end

  User[输入/刺激] --> C
  C --> H
  C --> P
  C --> A
  C --> T

  H --> EN
  A --> EN
  EN --> ST
  ST --> CO
  CO --> LT
  LT --> RE
  ST --> FO
  LT --> FO

  C -->|检索路由| ST
  C -->|检索路由| LT
  C --> Out[输出/回答]

  class C,H,T,P,A,EN,CO,RE,FO,ST,LT,User,Out box;
```

要点：强调“协调层编排 → 脑区分工 → 机制作用 → 存储层落地”的数据/控制流，凸显类脑而非静态检索范式。

---

## 图2 记忆生命周期闭环（编码→巩固→重塑→遗忘→再检索）

```mermaid
stateDiagram-v2
  [*] --> 编码
  编码 --> 巩固: 价值高/复述/离线
  编码 --> 遗忘: 噪声/低价值/过期
  巩固 --> 长期记忆
  长期记忆 --> 重塑: 新证据/冲突
  长期记忆 --> 遗忘: 容量压力/干扰
  重塑 --> 长期记忆
  长期记忆 --> 检索
  检索 --> 反思: 不一致/错误
  反思 --> 重塑
  检索 --> [*]
```

要点：把“主动性与可塑性”可视化，说明进入/退出条件与反馈环（反思→重塑）。

---

## 图3 触发与调度时序（容量/干扰/情境→巩固/遗忘/重塑）

```mermaid
sequenceDiagram
  participant User as 用户
  participant C as 协调层
  participant H as 海马体
  participant T as 颞叶
  participant Con as 巩固Agent
  participant For as 遗忘Agent
  participant MS as 记忆存储

  User->>C: 输入/问题
  C->>H: 编码(情节痕迹)
  H->>MS: 写入短期记忆
  C->>Con: 检查触发(价值/时间/复述)
  Con->>MS: 巩固到长期(语义表征)
  C->>For: 检查容量/干扰
  For->>MS: 选择性遗忘/抑制
  C->>T: 检索(语义线索/时间)
  T-->>C: 命中候选
  C->>C: 路由仲裁/可解释性记录
  C-->>User: 输出/答案
```

要点：体现“谁触发、何时触发、作用到哪里”，方便把调度逻辑与观测点对齐。

---

## 图4 评测与消融设计（一致性/可解释性/容量鲁棒/跨时空）

消融维度：巩固（CO）、遗忘（FO）、重塑（RE）、反思（RF）。建议四组配置做对照：

| 配置 | 机制开关 | 预期作用 | 关注指标 |
|---|---|---|---|
| A 基线 | 仅检索 | 静态检索行为 | 一致性、误检率 |
| B | + CO | 稳态语义化 | 一致性↑、噪声↓ |
| C | + CO + FO | 容量与干扰管理 | 漂移↓、冲突↓ |
| D | + CO + FO + RE | 结构化更新 | 长期稳定性↑ |

```mermaid
flowchart TB
  Start[评测配置起点] --> A[仅检索]
  Start --> B[+巩固]
  Start --> C[+巩固+遗忘]
  Start --> D[+巩固+遗忘+重塑]
  A --> Compare[对照/消融对比]
  B --> Compare
  C --> Compare
  D --> Compare
```

提示：通过配置文件/环境变量控制Agent参与与阈值（如容量阈值、干扰权重、重塑触发条件），在相同数据集下跑四组配置，记录“一致性、可解释性事件、容量命中率、跨时空任务成功率”等指标，形成方法学对比。

