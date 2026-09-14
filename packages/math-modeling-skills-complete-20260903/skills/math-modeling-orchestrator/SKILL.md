---
name: math-modeling-orchestrator
description: Orchestrate mathematical-modeling work from problem semantics through modeling, solving, validation, visualization, paper writing, and delivery. Default to the shortest reliable workflow; escalate to persistent audit artifacts, policy gates, or provenance-bound submission checks only when the task actually needs them.
---

# 数学建模：总控调度

## Purpose

把数模任务推进到用户真正需要的结果：可解释的模型、可信的数值、可复现代码、清晰图表和完整论文。默认原则是 **最短可靠闭环**，而不是“工件越多越严谨”。

总控只保留三类不能省的责任：

1. 题意不能被错误理解；
2. 数值和声明必须有与其强度匹配的验证；
3. 最终交付必须真实完整，不能把骨架、占位符或未验证结果包装成完成品。

默认论文模式为中文 CUMCM LaTeX/XeLaTeX。用户提供正式模板时优先使用正式模板。

## Execution profiles

### 1. `standard` — 默认

适用于大多数训练题、课程任务、赛题分析、单问求解和常规论文迭代。

默认不要求：

- 建立持久化 `workflow_state.json`；
- 为每一步单独生成 JSON/YAML 中间件；
- 固定 A/B/C 三条模型路线；
- 在主模型求解前等待用户审批；
- 强制外部 benchmark/challenge；
- 对确定性算法做无意义的多 seed；
- 固定数量的图、敏感性分析或消融实验；
- 为普通论文启动四个 subagent 或 provenance hash 链。

只有当某个工件会被后续脚本真实消费、需要团队交接、需要跨会话恢复，或用户明确要求审计/复现时，才把它落盘。

### 2. `structured`

适用于长流程、多问耦合、多人协作、多个代码/数据版本、需要后续恢复的任务。此时可启用 `workflow_state.json`、schema、运行清单和跨 Skill envelope，但仍遵循“按需产生工件”。

模型审批只在以下情况触发：

- 用户明确要求“先给方案，我批准再跑”；
- 两条路线在假设、成本或结论上有实质差异；
- 需要明显扩大计算预算、联网、外部服务或数据范围；
- 高风险歧义尚未由题面或用户确认。

### 3. `strict_submission_audit`

仅在用户明确要求 provenance-bound、competition-ready、严格终审或等价审计时启用。此时读取 `references/full_submission_contract.md`，使用现有 `--competition-ready` 交付门、视觉绑定、支撑材料检查和四路 fresh-subagent 审查。

**不要因为用户只说“写完整论文”“生成 PDF”“正式排版”就自动升级到该模式。** 普通完整论文属于 `formal_delivery`，重点是内容完整、结果真实、编译和视觉检查通过。

## Core workflow

### Step 1 — 读题与语义锁定

先读取题目、附件、已有代码和用户约束。只抽取真正会改变模型结构的信息：目标函数、变量、约束、时间/空间口径、资源是否复用、信息何时可得、多目标如何聚合。

低风险细节可以采用明确、可逆的工作假设继续做；高风险歧义如果不同解释会改变最优解、物理机理或主要结论，则必须显式指出，并在必要时请求用户裁决。

普通任务不必强制生成 `QUESTION_DECOMPOSITION.json` 或 `PROBLEM_SEMANTICS.yaml`。复杂任务需要机器交接时再调用 `mm-problem-decomposer`、`mm-variable-assumption-builder` 和对应 schema。

### Step 2 — 选择最小可用模型

优先选择能够正确表达题意、可实现、可验证的模型。必要时建立一个最小基线，用于检查：

- 目标方向是否写反；
- 单位与量纲是否一致；
- 约束是否真的生效；
- 主模型是否比简单方法带来有效改进。

基线不是形式要求。闭式问题、简单统计题或已有可信 evaluator 的任务，可以直接把简单解/手算边界作为基线，不必额外生成独立工件。

### Step 3 — 直接建模与求解

调用最匹配的专业 Skill。默认选一条主路线直接推进；只有存在明显不同且有价值的候选方案时才比较多路线。

不要为了“创新”机械叠加 Transformer、遗传算法、贝叶斯、PINN 等模型。复杂度升级必须回答一个具体问题：简单模型在哪里失效，新增结构解决了什么。

求解时保留真正重要的输入版本、关键参数、随机种子（若存在随机性）和最终输出。失败运行只有在诊断、复现或结论边界需要时保留，不要求普通任务维护完整运行谱系。

### Step 4 — 按声明强度验证

验证与结论一一对应：

- 声称“满足约束” → 重新计算原始约束；
- 声称“更优” → 同一 evaluator 下比较；
- 声称“稳定/鲁棒” → 做与扰动来源匹配的敏感性或情景检验；
- 随机算法 → 需要多 seed 或分布性统计；
- 确定性算法 → 不做形式化多 seed；
- 数值 PDE/ODE/离散化 → 关注网格、步长、收敛和守恒/边界；
- 预测模型 → 关注泄漏、时间切分、外推区间与任务指标。

外部论文数值、公开答案或异源 benchmark 只有在规则允许、用户授权且确实能检验当前声明时才使用。它不是默认必经门。

### Step 5 — 图表与论文

图表按读者任务决定，不按“每问 N 张图”配额决定。优先保留：

- 能解释几何/物理关系的示意图；
- 能展示关键规律、差异或不确定性的结果图；
- 能直接支撑结论的三线表。

结果图必须绑定真实数据或真实模型输出。示意图优先可编辑 TikZ/SVG/Visio 等确定性表达，不把生成式图片当成数学证据。

写作默认采用 `competition_compact`：正文讲清楚“问题 → 数学结构 → 方法 → 结果 → 必要验证 → 结论”，把工程日志、哈希、旧失败版本和后台细节留在支撑材料或不输出。

### Step 6 — 交付

按用户请求交付：代码、图、报告、论文或提交包。普通完整论文走 `formal_delivery`：

1. 正文、摘要、关键词、符号、图表、参考文献和附录闭合；
2. 没有 `TODO/TBD/FIXME/PLACEHOLDER/待填写/待补`；
3. 关键数字与正文声明能追溯到实际结果；
4. XeLaTeX 编译成功；
5. 打开最终 PDF 做视觉检查；
6. 需要时生成支撑材料并检查匿名性和完整性。

只有用户明确要求 `strict_submission_audit` 时，才额外执行 `references/full_submission_contract.md` 与 `final_delivery_check.py --competition-ready`。

## Artifact economy

普通任务优先把中间信息合并到一份简洁的工作摘要，而不是拆成很多文件。以下工件默认均为 **optional**：

- `QUESTION_DECOMPOSITION.json`
- `PROBLEM_SEMANTICS.yaml`
- `MODELING_EXPERIMENT_PLAN.yaml`
- `RUN_MANIFEST.json`
- `BENCHMARK_CHALLENGE.json`
- `RESULTS_TO_CLAIMS.md`
- `result_evidence_map.json`
- `NARRATIVE_MAP.yaml`
- `FIGURE_PLAN.yaml`
- `workflow_state.json`

启用条件只有四类：机器下游需要、多人交接需要、跨会话恢复需要、严格审计需要。

如果只需要一个持久化中间件，优先使用一份 `MODELING_SUMMARY.md`，包含：题意口径、主模型、关键假设、数据/代码入口、核心结果、验证结论、剩余风险和下一步。

## Live contest policy

只有 `task_mode=live_contest` 且当前工作确实涉及 AI、联网、外部论文、公开答案或 benchmark 权限时，才启用 `COMPETITION_POLICY.yaml`。未知且可能导致违规的权限必须 fail-closed。

训练、赛后复盘、课程作业和一般研究任务不要为了形式创建竞赛权限文件。

## State and audit mode

`workflow_state.py` 保留给 `structured` 与 `strict_submission_audit` 场景，用于长流程恢复和强审计。不要在每个普通问题中机械推进全部状态。

若使用状态机：

- 语义级变化应使受影响的下游结果失效；
- `FAIL` 不能靠改措辞变成 `PASS`；
- `PARTIAL` 必须缩小声明范围；
- full provenance gate 只在 strict audit 中使用。

## Routing to specialist Skills

- 数据检查：`mm-data-eda-cleaning`
- 变量/假设：`mm-variable-assumption-builder`
- 模型选择：`mm-model-selector`
- 优化：`mm-optimization-models`
- 评价：`mm-evaluation-models`
- 预测：`mm-prediction-models`
- 动力学/机理：`mm-dynamic-mechanism-models`
- 图网络：`mm-graph-network-models`
- 仿真：`mm-simulation-models`
- 统计推断：`mm-statistical-inference`
- 分类聚类：`mm-classification-clustering`
- 信号/图像/轨迹：`mm-signal-image-trajectory`
- 不确定性与验证：`mm-uncertainty-validation`
- 图表：`mm-visualization-delivery`
- 论文结构：`mm-paper-structure-writer`
- 摘要：`mm-abstract-polisher`
- 论文审查：`mm-paper-reviewer`
- 编译交付：`mm-paper-compile`
- 团队运营：`mm-contest-operations-planner`

## Quality principles

- 正确题意优先于复杂模型；
- 有效验证优先于“看起来很先进”；
- 只生成会被使用的工件；
- 结果必须能回到真实代码/数据/公式；
- 图表服务于叙事，不服务于数量；
- 正文避免工程化审计噪声；
- 对能力边界和未验证结论保持明确披露；
- benchmark、schema、CI 通过只能证明相应检查通过，不能等价为获奖水平或数学正确。
