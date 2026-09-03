---
name: mm-optimization-models
description: Formulate and solve constrained optimization models for resource allocation, scheduling, routing, production planning, and multi-objective decision tasks. Use when the problem has decision variables, objectives, and constraints. Start from the simplest structure-valid baseline and escalate only when evidence justifies it. Do not use for pure descriptive analysis or ranking-only tasks.
---

# 数学建模：优化模型

## Purpose

把资源分配、调度、路径、生产计划和多目标决策问题转成可求解的优化模型，并按问题结构选择求解器；优先保证“目标语义正确、约束可复算、基线可解释”，而不是堆叠启发式算法。

## When to use

- 问题有决策变量、目标函数和约束。
- 需要线性规划、整数规划、非线性规划或多目标优化。
- 需要解释不可行、无界或非凸搜索边界。

## When not to use

- 任务只是描述统计或排序。
- 没有明确可控制的决策变量。
- `PROBLEM_SEMANTICS.yaml` 仍存在会改变最优解结构的高风险未决项。

## Required inputs

- 已锁定的目标函数语义与 `PROBLEM_SEMANTICS.yaml`。
- 决策变量、变量类型和取值范围。
- 硬约束、软约束和偏好约束。
- 数据参数及最小正确基线结果。
- 若存在：优秀论文/公开可行策略等外部挑战输入。

## Workflow

1. 读取并复述已锁定的数学目标，检查目标方向、集合运算、资源计数和多目标聚合没有漂移。
2. 识别决策变量和变量类型，写出原始目标函数与硬约束。
3. 判断结构：LP、MILP/CP、光滑 NLP、非光滑/黑箱、动态优化、随机/鲁棒、多目标、连续-离散混合。
4. 先运行**最小正确基线**。低维优先解析/网格/枚举/多起点局部；组合问题先构造小规模精确 MILP/枚举；黑箱问题先建立可人工校验的 evaluator。基线输出必须由原始目标函数与硬约束重算。
5. 识别当前瓶颈属于哪一类：维数、非凸零平台、离散组合、昂贵 evaluator、强耦合约束、随机性或在线时限。只有明确瓶颈后才升级求解器。
6. 使用“求解器升级梯子”，而不是机械叠加算法：
   - 低维连续：网格/多起点局部 → DE/CMA-ES/PSO 三选一；
   - 光滑约束：NLP/SQP/IPM 优先；
   - 线性/离散：MILP/CP-SAT 优先；
   - 连续+离散：分解、列/路线生成、Benders/主从或有限候选+连续修复；
   - 昂贵黑箱：代理/贝叶斯优化仅在评价成本真实构成瓶颈时使用；
   - 多目标：Pareto 生成与偏好筛选分开。
7. 每次升级都记录 `baseline_failure → chosen_solver → expected_mechanism → budget → stop_rule → fallback`。只换算法名而没有机制依据，视为无效复杂化。
8. 搜索内核可以使用近似 evaluator，但所有最终候选必须回到**正式 evaluator**重算；近似搜索值不能直接进入论文结果表。
9. 对启发式/随机算法报告预定种子、预算、可行率、分布与全部保留候选；“多个种子收敛到同值”只支持内部稳定性，不支持全局覆盖。
10. 若存在合法外部策略，执行 `external-solution challenge`：把外部参数/路线映射进当前硬约束和正式 evaluator。外部可行解领先超过预设容差时，当前“最佳/稳定最优”声明失效并返回搜索；不能用“我们的种子很稳定”覆盖这一反例。
11. 解释最优解、灵敏度、不可行处理和最优性边界。没有解析界、gap、证明或充分挑战证据时，只能写“候选最优/预算内最佳可行/局部最优”等限定语。

建模前读取 [optimization_model_cards.md](references/optimization_model_cards.md)；外部挑战规则见总控 `references/problem_semantics_and_benchmark_protocol.md`。

## Output format

```markdown
## 优化问题判断与已锁定语义

## 最小正确基线

## 决策变量

## 目标函数

## 约束条件

## 结构与瓶颈诊断

## 求解器升级理由

## 求解设置、预算与停止条件

## 正式 evaluator 复算

## 外部基准挑战

## 结果解释与最优性边界

## 不可行 / 无界情况处理
```

## Quality checks

- 目标函数方向、资源计数和多目标聚合必须与 `PROBLEM_SEMANTICS.yaml` 一致。
- 约束不能和变量单位冲突；新增近似约束必须标明来源和影响。
- 整数变量必须说明原因。
- 不可行时先检查约束、参数和语义，而不是立即放松硬约束。
- 优先建立可复算的小规模精确/简单基线；基线未跑通时不得直接升级复杂启发式。
- 启发式必须报告预算、可行率、全部预定初值/种子、求解状态和修复后的原始约束/目标重算。
- 多种子一致不等于全局最优；异源/外部可行解击穿时必须降级强声明。
- NSGA-II/MOPSO 检查 rank 哨兵、支配定义、零目标范围、前沿内拥挤度及父子代截断；前沿图好看不等于收敛或多样性通过。
- 多目标优化将 Pareto 生成与偏好筛选分开；在线问题记录信息到达、冻结决策、滚动窗口时限和安全回退。
- `success`、一个候选最好值或局部求解器终止不能写成全局最优；必须说明最优性边界。
- 外部论文数字与当前目标/物理口径不同则标 `INCOMPARABLE`，不得直接排大小。

## Academic integrity boundaries

- 只能用于学习、训练、课程作业辅助、赛前准备、结构检查和结果复盘。
- 正式竞赛使用外部资料必须遵守赛事规则；禁止为绕过规则主动获取外部答案。
- 不伪造数据、代码运行结果、图表、参考文献或实验结论。
- 所有不确定结论、推断条件和未验证结果都必须标注“需要用户核验”。

## CUMCM 交接产物

返回 `inputs`、`problem_semantics_ref`、`assumptions`、`baseline`、`model_and_solver`、`machine_readable_results`、`benchmark_challenge`、`diagnostics`、`unresolved_risks`、`latex_equations` 和 `figure_intents`；约束、目标、求解状态和最优性边界必须可复算。
