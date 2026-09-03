---
name: mm-optimization-models
description: Formulate and solve constrained optimization models for resource allocation, scheduling, routing, production planning, and multi-objective decision tasks. Use when the problem has decision variables, objectives, and constraints. Do not use for pure descriptive analysis or ranking-only tasks.
---

# 数学建模：优化模型

## Purpose

把资源分配、调度、路径、生产计划和多目标决策问题转成可求解的优化模型。

## When to use

- 问题有决策变量、目标函数和约束。
- 需要线性规划、整数规划、非线性规划或多目标优化。
- 需要解释不可行或无界情况。

## When not to use

- 任务只是描述统计或排序。
- 没有明确可控制的决策变量。
- 约束和目标都无法确定。

## Required inputs

- 决策变量。
- 目标函数方向。
- 约束条件。
- 变量类型和取值范围。
- 数据参数。

## Workflow

1. 识别决策变量和变量类型。
2. 明确目标函数。
3. 写出约束条件。
4. 判断线性、整数、混合整数、非线性或多目标。
5. 给出数学表达和求解代码。
6. 解释最优解、灵敏度和不可行处理。

建模前读取 [optimization_model_cards.md](references/optimization_model_cards.md)。加权评分与受约束多目标优化必须明确区分；启发式结果不得标成已证明全局最优。

## Output format

```markdown
## 优化问题判断

## 决策变量

## 目标函数

## 约束条件

## 模型类型

## 求解方法

## Python 模板说明

## 结果解释

## 不可行 / 无界情况处理
```

## Quality checks

- 目标函数方向必须明确。
- 约束不能和变量单位冲突。
- 整数变量必须说明原因。
- 不可行时先检查约束和参数。
- 优先建立可复算的小规模精确基线；启发式必须报告预算、可行率、全部预定初值/种子、求解状态和修复后的原始约束/目标重算。
- NSGA-II/MOPSO 检查 rank 哨兵、支配定义、零目标范围、前沿内拥挤度及父子代截断；前沿图好看不等于收敛或多样性通过。
- 多目标优化将 Pareto 生成与偏好筛选分开；在线问题记录信息到达、冻结决策、滚动窗口时限和安全回退。
- `success`、一个候选最好值或局部求解器终止不能写成全局最优；必须说明最优性边界。

## Academic integrity boundaries

- 只能用于学习、训练、课程作业辅助、赛前准备、结构检查和结果复盘。
- 不代写完整参赛论文，不代替用户参赛，不承诺获奖或保奖。
- 不伪造数据、代码运行结果、图表、参考文献或实验结论。
- 正在进行的正式竞赛中，必须提醒用户遵守赛事规则、课程要求和学术诚信。
- 所有不确定结论、推断条件和未验证结果都必须标注“需要用户核验”。

## CUMCM 交接产物

返回 `inputs`、`assumptions`、`model_and_solver`、`machine_readable_results`、`diagnostics`、`unresolved_risks`、`latex_equations` 和 `recommended_figures`；约束、目标、求解状态和最优性边界必须可复算。
