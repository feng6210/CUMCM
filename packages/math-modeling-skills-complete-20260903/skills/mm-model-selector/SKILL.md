---
name: mm-model-selector
description: Recommend suitable mathematical modeling methods based on locked problem semantics, baseline performance, problem structure, data availability, objectives, constraints, interpretability, and validation cost. Use after problem decomposition and minimum-baseline setup. Do not select models by buzzword or complexity.
---

# 数学建模：结构化模型选型

## Purpose

帮助用户基于**已锁定题意语义 + 最小正确基线 + 问题结构**形成候选模型。选型回答的是“基线哪里不够、什么结构能修复这个不足”，不是“哪个模型名字更新”。

## When to use

- 已有 `PROBLEM_SEMANTICS.yaml` 且高风险歧义已裁决。
- 已有最小正确基线，或能明确说明为何当前任务不需要数值基线。
- 需要比较 2--4 个候选模型并给出验证成本。

## When not to use

- 问题目标和数据条件都不清楚。
- 语义仍存在会改变可行域/最优解结构的高风险未决项。
- 用户只需要跑某个既定模型脚本。
- 用户要求用复杂模型包装结果。

## Required inputs

- `QUESTION_DECOMPOSITION.json`。
- `PROBLEM_SEMANTICS.yaml`。
- 数据/机理条件和最小基线结果。
- 目标、硬约束、解释性和时限要求。

## Workflow

1. 复述已锁定目标和约束，确认不在选型阶段改变数学问题。
2. 识别结构：机理/几何、预测、统计推断、优化、仿真、网络、在线决策或组合。
3. 读取最小基线，明确其已解决的问题和**实证不足**：精度、偏差、非凸、离散耦合、计算成本、缺少不确定性、信息时序等。
4. 给出 2--4 个候选模型；每个候选必须对应一个具体不足，说明其修复机理。
5. 比较适用前提、数据要求、额外超参数、可解释性、实现成本、验证负担和论文表达难度。
6. 推荐一个保守基线延伸、一个主模型和至少一个回退；简单模型足够时允许明确“不升级”。
7. 给出不建议使用的热门模型及原因，特别防止因为名称新颖而引入不必要复杂度。
8. 对优化类候选同步给出求解器结构，不直接串联多个启发式；连续/离散/混合性质优先决定 LP/MILP/NLP/分解/黑箱搜索等路线。
9. 将状态标记为 `MODEL_PLANNED`，把候选方案交给 `mm-model-innovation-designer`；主求解仍需用户批准。
10. 为每个候选给出最小数据条件、核心假设、输出形式、可用求解器、专属诊断、典型失败模式、时间成本、LaTeX 表达和 `figure_intents`。`figure_intents` 只说明可能需要解释的机制/结果结构，不指定固定图量。

候选模型不足或跨题型时读取 [model_selection_matrix.md](references/model_selection_matrix.md) 与 [model_family_cards.md](references/model_family_cards.md)，不得按关键词套模型。

## Output format

```markdown
## 已锁定题意与基线
## 基线不足诊断
## 候选模型比较
| 模型 | 修复的基线不足 | 生效机理 | 数据/假设 | 验证负担 | 成本 | 写作难度 |
## 推荐主模型
## 推荐回退模型
## 明确不建议的模型
## 后续创新设计输入
```

## Quality checks

- 推荐必须和题目目标、数据条件一致。
- 候选模型必须说明“为什么比当前基线更合适”，不能只写一般优点。
- 复杂模型需要说明额外数据、调参、可解释性和验证成本。
- 若简单模型已经满足题目精度/决策/解释要求，允许拒绝升级。
- 混合题说明不同模型间的数据接口和误差传播；复杂组合不能只因 X+Y 听起来新颖被推荐。
- 每个候选必须给出最小基线、接口输出形态、可否辨识/求解、专属诊断和时间预算。
- 选型阶段不能绕过 `PROBLEM_SEMANTICS.yaml` 新增目标或资源限制。

## Academic integrity boundaries

- 只能用于学习、训练、课程作业辅助、赛前准备、结构检查和结果复盘。
- 正式竞赛中必须遵守赛事规则和 AI/外部资料政策。
- 不伪造数据、结果、图表、参考文献或实验结论。
