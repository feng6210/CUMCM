---
name: mm-dynamic-mechanism-models
description: Build mechanism-driven dynamic models using differential equations, difference equations, state-space systems, kinematics, and dynamic programming. Use for physical motion, energy systems, propagation, multi-stage decisions, and evolving states. Do not present a numerical trajectory without checking units, initial conditions, solver stability, and conservation or residual laws.
---

# 数学建模：动力学与动态规划

## Purpose

处理状态随时间或阶段演化的问题，把机理、受力、守恒、运动学或多阶段决策写成微分方程、差分方程、状态空间或动态规划模型。

## When to use

- 需要建立受力、能量、传播、增长、衰减、控制或运动学方程。
- 问题包含阶段、状态、动作、转移、收益和终止条件。
- 解析解不可得，需要数值积分、根求解或递推搜索。

## When not to use

- 只有横截面相关性而没有动态机理。
- 无法给出初始/边界条件或状态转移依据。
- 用户只需要静态排序。

## Required inputs

- 状态变量、时间/阶段、初始条件和边界条件。
- 机理定律、受力/流量/收益与参数单位。
- 控制变量、可行动作、约束和目标函数。
- 可用于校验的观测、极限情形或守恒关系。

## Workflow

1. 画出状态—输入—参数—输出关系，做量纲检查。
2. 区分 ODE/DAE、差分方程、状态空间、事件系统或动态规划。
3. 对 ODE 检查刚性、步长、容差和边界；对 DP 明确 Bellman 状态与最优子结构。
4. 先用可解析或小规模情形校验，再求完整问题。
5. 做步长收敛、残差/守恒、初值扰动和参数敏感性检查。
6. 导出轨迹、事件、最优策略、求解器设置及误差证据。

需要实现时先读 [dynamic_model_guide.md](references/dynamic_model_guide.md)。ODE 基线可运行 `scripts/ode_system_template.py`，多阶段确定性资源决策可运行 `scripts/dynamic_programming_template.py`。

## Output format

```markdown
## 状态与机理
## 方程/递推关系
## 初始边界条件
## 数值算法与设置
## 校验与误差
## 结果和适用范围
```

## Quality checks

- 所有方程必须量纲一致，初始/边界条件数量与模型阶数匹配。
- 数值解必须报告步长或容差，并至少做一次收敛或残差检查。
- 动态规划必须保存状态定义、转移、阶段收益、终止条件和回溯策略。
- 不以一条平滑曲线代替机理验证。
- 几何、守恒、动力学、参数辨识和控制应分层验证；离散轨迹动画不能替代连续碰撞/边界检查。
- 机理+数据残差模型必须同时比较纯机理、纯数据和混合模型，修正项不能破坏非负、守恒或几何边界。
- 参数拟合报告可辨识性、置信范围和初值敏感性；ODE/PDE 报告积分器状态、容差/网格收敛和事件处理。

## Academic integrity boundaries

- 不伪造物理参数、初始条件或数值收敛结果。
- 未证明全局最优时必须标注启发式或局部最优。
- 正式任务中保留方程版本、求解器配置和原始输出供用户核验。

## CUMCM 交接产物

返回 `inputs`、`assumptions`、`model_and_solver`、`machine_readable_results`、`diagnostics`、`unresolved_risks`、`latex_equations` 和 `recommended_figures`；同时交接量纲、初边值、容差和收敛证据。
