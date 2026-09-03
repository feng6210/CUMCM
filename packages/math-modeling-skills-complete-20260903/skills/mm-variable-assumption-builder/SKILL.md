---
name: mm-variable-assumption-builder
description: Convert a real-world modeling problem into variables, parameters, assumptions, objective functions, constraints, semantic alternatives, and symbol tables. Use after problem decomposition and before model selection. Do not invent unsupported assumptions or silently choose among materially different objective interpretations.
---

# 数学建模：变量、假设与目标语义

## Purpose

把现实问题抽象成符号、变量、参数、假设、目标函数和约束条件；同时把题意中的多种合理数学解释显式化并完成语义锁定，避免把“形式化”误写成“替题目决定目标”。

## When to use

- 题目已经拆解，需要建立符号表。
- 用户需要设计模型假设并说明理由。
- 需要把文字目标转为目标函数或评价函数草案。
- `PROBLEM_SEMANTICS.yaml` 仍有待形式化或待裁决条目。

## When not to use

- 用户只需要数据清洗或代码运行。
- 用户要求把无依据假设写成事实。
- 题目目标还没有明确且无法列出候选解释。

## Required inputs

- 题目原文和附件。
- `QUESTION_DECOMPOSITION.json`。
- `PROBLEM_SEMANTICS.yaml` 草案。
- 数据字段。
- 用户已有变量和明确裁决，如有。

## Workflow

1. 区分决策变量、状态变量、参数、指标、中间变量和输出变量。
2. 设计符号表并检查重名、量纲和跨问复用。
3. 写建模假设，说明理由、风险和验证方式。
4. 对每个核心目标给出候选数学表达，特别检查：集合并/交、时长求和/去重、总和/最小值/加权/词典序/Pareto、资源能否重复计数或同时服务多个目标。
5. 建立“文字表述 → 数学对象 → 新增假设 → 可行域影响 → 结论影响”的语义对照表；若不同解释会改变解结构且题面证据不足，返回 `SEMANTICS_REVIEW`，不得自行选一个方便求解的目标。
6. 语义锁定后写入 `selected_interpretation`、`selection_reason` 和 `semantic_risk`，形成可哈希的 `PROBLEM_SEMANTICS.yaml`。
7. 设计约束条件草案，区分题面硬约束、物理约束、计算边界和偏好约束；偏好不能伪装成题面要求。
8. 标记哪些内容需要数据、文献、极限情形或敏感性支撑。
9. 为后续最小基线给出可人工检查的极端/边界案例。

变量、单位和假设来源的写法见 [variable_assumption_patterns.md](references/variable_assumption_patterns.md)；题意语义与外部挑战规则见总控 `references/problem_semantics_and_benchmark_protocol.md`。

## Output format

```markdown
## 变量与参数表

| 符号 | 含义 | 类型 | 单位 | 来源 | 是否需要估计 |
|---|---|---|---|---|---|

## 建模假设

| 编号 | 假设 | 理由 | 可能影响 | 是否需要验证 |
|---|---|---|---|---|

## 目标函数语义对照

| 解释 | 数学表达 | 额外假设 | 对可行域/排序的影响 | 证据 | 状态 |
|---|---|---|---|---|---|

## 已锁定目标函数 / 评价函数

## 约束条件草案

## 极端与边界校验案例

## 符号说明建议

## 风险提示
```

## Quality checks

- 变量不能重名。
- 单位必须尽量明确。
- 假设不能过度强。
- 复杂现实问题必须说明简化损失。
- 目标函数不能和题目目标脱节。
- 不得因为某个目标“更容易优化”就静默采用它；不同目标聚合方式需要题面、用户或明确建模理由。
- 题面没有限制“一资源只服务一个目标”时，不得为了降低维数自动加入一对一指派；若作为近似，必须标为新增假设并做影响分析。
- 每条假设应说明必要性、影响的方程或约束、可验证性与失效后果；符号应补充单位、范围、观测性和首次出现位置。
- 输出应可转换为 LaTeX 三线符号表；检查同一符号多义、同变量多符号、量纲冲突和未定义参数。
- 跨模型接口假设必须记录输入形态、误差/相关性、信息到达时刻和下游违反后果；点预测不能静默当作确定真值。
- 机理参数记录可辨识性和数据来源；随机参数记录分布证据；在线决策记录不可撤销变量和冻结时刻。
- 只有 `PROBLEM_SEMANTICS.yaml` 无高风险未决项时，才能把语义状态视为 `SEMANTICS_LOCKED`。

## Academic integrity boundaries

- 只能用于学习、训练、课程作业辅助、赛前准备、结构检查和结果复盘。
- 不代写完整参赛论文，不代替用户参赛，不承诺获奖或保奖。
- 不伪造数据、代码运行结果、图表、参考文献或实验结论。
- 正在进行的正式竞赛中，必须提醒用户遵守赛事规则、课程要求和学术诚信。
- 所有不确定结论、推断条件和未验证结果都必须标注“需要用户核验”。
