---
name: mm-problem-decomposer
description: Decompose a math modeling problem statement into known conditions, required outputs, variables, constraints, data needs, semantic ambiguities, subtasks, and modeling difficulties. Use for contest or coursework problem analysis before choosing models. Do not use this Skill itself to write a complete final paper.
---

# 数学建模：赛题拆解

## Purpose

把自然语言赛题或课程题目拆成明确的建模任务，并在选模型前完成目标函数、计时口径、资源归属和多目标语义审查，避免后续在错误数学问题上做复杂优化。对于 `deliverable_mode=submission_package`，本 Skill 还负责冻结**完整分问集合**，防止后续通过少登记一问把未完成内容隐藏掉。

## When to use

- 用户提供题目原文并希望“先分析题”。
- 需要区分每一问的输入、输出、目标和难点。
- 模型选择前需要把问题类型、数据需求和关键语义说清楚。

## When not to use

- 用户只要求直接修改已有论文且无需重新拆题。
- 题目尚未提供且无法判断背景。
- 用户已经只需要某个脚本计算结果。

## Required inputs

- 题目原文。
- 附件说明，如果有。
- 竞赛或课程背景，如果有。
- 用户想解决第几问；若 `submission_package`，默认必须覆盖题目要求的全部分问，除非赛事交付本身明确只要求其中一部分。

## Workflow

1. 识别题目背景、任务对象和决策时刻。
2. 按问题编号拆分每一问，形成稳定、唯一的 `question_id`（如 `Q1...Qn`）。
3. 提取已知条件、待求目标、显性约束和隐含约束。
4. 对会改变数学问题的关键词做语义审查，尤其是“总、同时、分别、联合、有效时长、综合、至少、最多、每个、任一”等；若存在两个以上合理解释，必须并列形式化，不得静默选择。
5. 为每问形成 `PROBLEM_SEMANTICS.yaml` 草案：候选目标函数、集合运算/计时口径、资源计数方式、一个资源能否同时服务多个目标、选择依据、下游影响和未解决歧义。规则见总控 `references/problem_semantics_and_benchmark_protocol.md`。
6. 列出可能变量、数据需求和输出形式。
7. 判断题型：评价、预测、优化、分类、聚类、仿真、机理建模或混合型。
8. 输出主要建模难点、最小正确基线和需要用户补充的信息。
9. 为每问补充数据/参数依赖、失败回退、需要生成的结果表，以及**读者可能看不懂的机制/几何/流程位置**；这里只提出 `figure_intents`，不规定每问固定图量。
10. 输出 `QUESTION_DECOMPOSITION.json` 时，顶层必须包含 `expected_question_ids`，顺序与题面分问顺序一致；`questions` 中每个对象必须有相同集合的 `question_id`。`submission_package` 后续的 `workflow_state.problem_parts` 和 `FINAL_SUBMISSION_MANIFEST.question_completion` 必须与此字段逐项一致。

拆题前按需读取 [problem_decomposition_guide.md](references/problem_decomposition_guide.md)，并把附件、字段和要求写进可交接清单。

## Output format

```markdown
## 题目拆解总览

| 模块 | 内容 |
|---|---|

## 分问题拆解

| 问题编号 | 目标 | 输入 | 输出 | 可能模型方向 | 主要难点 |
|---|---|---|---|---|---|

## 题意语义审查

| 分问 | 原始表述 | 候选数学解释 | 会改变什么 | 当前选择/待裁决 |
|---|---|---|---|---|

## 已知条件

## 隐含约束

## 初步变量表

| 变量 | 含义 | 类型 | 单位 | 是否可观测 | 备注 |
|---|---|---|---|---|---|

## 数据需求

## 最小正确基线

## 可能建模路线

## 需要用户补充的信息
```

同时输出机器可读 `QUESTION_DECOMPOSITION.json` 与 `PROBLEM_SEMANTICS.yaml`。`QUESTION_DECOMPOSITION.json` 至少满足：

```json
{
  "expected_question_ids": ["Q1", "Q2"],
  "questions": [
    {"question_id": "Q1"},
    {"question_id": "Q2"}
  ]
}
```

示例只说明字段，不限制真实分问数。

## Quality checks

- 不要跳过原题目标。
- 不要一上来套模型。
- 不要把背景信息误当成待求目标。
- 每个分问题必须有明确输出；`expected_question_ids` 与 `questions[].question_id` 必须集合一致、无重复、无漏问。
- 目标函数、时间集合运算、资源复用规则和多目标聚合方式不能依赖“常识猜测”；存在实质歧义时必须显式列出候选解释。
- 语义风险为高、且不同解释会改变可行域或最优解结构时，停止在 `SEMANTICS_REVIEW`，不得进入主求解。
- 每问依赖的上游结果必须明确版本和用途。
- 为每个分问标注结构签名：机理/几何、预测、统计推断、优化、仿真、图网络、在线决策或它们的组合；题号与题型标签不能替代结构判断。
- 对跨问接口明确传递的是点估计、区间、分布、场景集、可行域还是候选解集，并记录误差如何向下游传播。
- 区分事前可用信息、决策时新到信息和事后真实值；不得让未来信息进入当前决策。
- `figure_intents` 只描述“哪种读者障碍需要图”，不得写成“每问至少 N 张图”。

## Academic integrity boundaries

- 本 Skill 只负责拆题和语义冻结，不自行代替求解、审稿或最终论文交付。
- 不伪造数据、代码运行结果、图表、参考文献或实验结论。
- 正在进行的正式竞赛中，必须遵守 `COMPETITION_POLICY.yaml` 和赛事规则；AI 不允许时停止整个 AI 工作流。
- 所有不确定结论、推断条件和未验证结果都必须进入 unresolved/语义审查，不得通过删掉对应 `question_id` 来规避。
