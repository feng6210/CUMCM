# 数学建模总控路由与交接指南

本文件必须与 `scripts/workflow_state.py` 和总控 `SKILL.md` 保持一致。若出现冲突，以可执行状态机和当前 `PROBLEM_SEMANTICS.yaml` / `workflow_state.json` 为准，不允许按旧流程绕过语义、基线或外部挑战门。

## 路由矩阵

| 信号 | 路由 Skill | 必须交接的证据 |
|---|---|---|
| 读题、分问、输入输出、歧义词 | `mm-problem-decomposer` | `QUESTION_DECOMPOSITION.json`、显性/隐性约束、语义候选、附件清单 |
| 变量、假设、目标、资源计数 | `mm-variable-assumption-builder` | `PROBLEM_SEMANTICS.yaml`、符号表、单位、假设来源 |
| 数据缺失/异常/类型 | `mm-data-eda-cleaning` | 数据审计、异常清单、清洗决策 |
| 最小正确基线 | 对应专业 Skill / 简单 evaluator | `baseline_result`、原始目标/约束重算、`not_applicable` 理由（如适用） |
| 模型候选、基线不足与淘汰理由 | `mm-model-selector` | 基线不足、2—4 个候选、结构适配、验证成本、回退 |
| 创新、优秀方案对比、路线批准 | `mm-model-innovation-designer` | A/B/C 路线、创新证据卡、消融、回退、批准请求 |
| 多指标评价与排序 | `mm-evaluation-models` | 权重来源、方向、排序敏感性 |
| 回归、时间序列、灰色预测 | `mm-prediction-models` | 划分方案、基线、误差和外推边界 |
| LP/MILP/非线性/多目标 | `mm-optimization-models` | 变量、目标、原始约束核验、最优性状态、正式 evaluator |
| 路网、管网、传播、路径 | `mm-graph-network-models` | nodes/edges、方向、边权、可达性 |
| ODE、运动学、阶段决策 | `mm-dynamic-mechanism-models` | 方程、初边值、步长/容差或 Bellman 契约 |
| 抽检、检验、纵向/生存 | `mm-statistical-inference` | 抽样设计、独立性、区间与校准 |
| 分类、聚类、模式识别 | `mm-classification-clustering` | 分组/时间切分、类别分布、指标 |
| 随机、排队、离散事件 | `mm-simulation-models` | 分布依据、种子、重复次数、MC 误差 |
| 频谱、图像、视频、轨迹 | `mm-signal-image-trajectory` | 采样/标定、处理规则、中间特征 |
| 公开/用户提供可行方案、样例或外部基准 | 当前专业 Skill + `mm-uncertainty-validation` | `BENCHMARK_CHALLENGE.json`；必须映射进当前 evaluator，不能只比较原文数字 |
| 所有数值模型完成后 | `mm-uncertainty-validation` | 声明—证据表、同源重算、数值/随机/稳健/异源验证、PASS/PARTIAL/FAIL |
| 图表、Excel、附件 | `mm-visualization-delivery` | `FIGURE_PLAN.yaml`、字段、单位、精度、数字溯源；不设固定图量 |
| 论文结构与摘要 | `mm-paper-structure-writer` / `mm-abstract-polisher` | 已验证结果、`NARRATIVE_MAP.yaml`、声明边界，不接受占位数值 |
| 最终审查 | `mm-paper-reviewer` | 题目、`PROBLEM_SEMANTICS.yaml`、草稿、代码输出、挑战/验证报告 |

## 当前标准状态机

```text
NEW
→ INPUT_REGISTERED
→ DECOMPOSED
→ SEMANTICS_REVIEW
→ SEMANTICS_LOCKED
→ [DATA_AUDITED，如有数据审计]
→ BASELINE_SOLVING
→ BASELINE_READY
→ MODEL_PLANNED
→ INNOVATION_PROPOSED
→ AWAITING_MODEL_APPROVAL
→ USER_APPROVED
→ SOLVING
→ SOLVED
→ [BENCHMARK_CHALLENGE，如存在合法外部/异源基准]
→ INTEGRITY_AUDIT
→ VALIDATING
→ PASS / PARTIAL / FAIL
→ RESULT_TO_CLAIM
→ WRITING
→ FIGURES
→ DELIVERING
→ REVIEWING
→ COMPLETE
```

### 不可绕过的三道前置门

1. **语义门**：会改变可行域、目标聚合、时间集合运算、资源复用或信息集的歧义未裁决时，停在 `SEMANTICS_REVIEW`。
2. **最小基线门**：主模型规划之前必须经过 `BASELINE_SOLVING → BASELINE_READY`。若基线确实不适用，也必须有显式 `not_applicable` 记录，不能直接跳到 `MODEL_PLANNED`。
3. **模型批准门**：首次主 `SOLVING` 必须来自 `USER_APPROVED`；模型/目标/核心约束变化后旧批准失效。

### 外部挑战门

- training/coursework/research 中若有题目样例、优秀论文参数、用户提供可行解或其他合法基准，必须优先做同 evaluator 重算。
- 若外部可行解领先 incumbent 超过预设容差，当前“最佳/稳定最优/近全局”声明失效并返回 `SOLVING`。
- live contest 是否允许外部资料由 `COMPETITION_POLICY.yaml` 决定；禁止时记录 `NOT_ALLOWED_BY_RULES`，不得绕过赛事规则。

任意适用阶段可进入 `BLOCKED_INPUT` 或 `BLOCKED_CAPABILITY`。`FAIL` 不能直接交付；`PARTIAL` 只能缩小声明范围。精确允许的跳转以 `workflow_state.py` 为准。

## 跨 Skill 规范化 envelope

专业 Skill 不必重复生成全部上游事实。总控在进入验证、跨问或论文链前，按 `cross_skill_output_contract.md` 规范化为：

```text
question_id
inputs
problem_semantics_ref
assumptions
baseline
model_and_solver
machine_readable_results
benchmark_challenge
diagnostics
unresolved_risks
latex_equations
figure_intents
```

推荐使用 `schemas/` 中的版本化契约做机器校验。schema 通过只证明字段和类型正确，不证明数学结论成立。

## 使用提醒

- 先确认赛制和外部资料权限，再启动联网检索或外部 benchmark。
- 所有最终候选用原始硬约束和正式目标函数重算；搜索内核结果不能直接进入论文表格。
- 内部多种子稳定和外部未被击穿是不同命题。
- 图表先规划 reader task，再选择 figure/table/text/appendix；复杂几何优先解释机制，不用固定图数凑覆盖。
- `agents/openai.yaml` 是 Skill 界面与触发元数据，不等于多 Agent 协作已经实际执行。独立审查必须有真实 fresh-agent/外部 reviewer 证据。
