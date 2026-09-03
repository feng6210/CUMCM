---
name: mm-graph-network-models
description: Model paths, connectivity, propagation, assignment, routing, and network flow problems with graph algorithms. Use for shortest paths, minimum spanning trees, maximum flow, time-dependent networks, and graph-based state transitions. Do not force tabular data into a graph without a defensible node-edge definition.
---

# 数学建模：图论与网络模型

## Purpose

把地点、设备、工序、事件或状态抽象为节点与边，建立可复算的最短路、最小生成树、最大流、网络传播或时变路径模型。

## When to use

- 题目出现道路、管网、矿井、物流、通信、人员关系或状态转移网络。
- 需要最短路、最大流、最小费用流、生成树、匹配、连通性或传播路径。
- 边权会随时间、流量、故障或外部事件变化。

## When not to use

- 节点、边和边权没有明确现实含义。
- 问题只是普通表格回归或静态综合评价。
- 路径顺序并不影响目标或约束。

## Required inputs

- 节点、边、方向性和边权定义。
- 起点、终点、容量、费用、时间窗或更新规则。
- 是否允许负权、断边、多源、多目标或动态更新。
- 需要输出的路径、流量、瓶颈和可视化格式。

## Workflow

1. 建立节点表与边表，核对单位、方向、重复边和孤立点。
2. 区分静态最短路、容量流、匹配、生成树、时变网络或事件传播。
3. 选择算法并写明适用前提；负权边不得直接使用 Dijkstra。
4. 用小规模手算网络做单元核验，再运行完整数据。
5. 对断边、同权多路径、不可达节点和权重扰动做鲁棒性检查。
6. 导出路径/边流量、目标值、约束核验和可复算证据。

需要实现时先读 [graph_model_guide.md](references/graph_model_guide.md)，基础最短路、最大流与生成树可运行 `scripts/graph_path_flow.py`。

## Output format

```markdown
## 图结构定义
## 算法与前提
## 路径或流量结果
## 可达性与约束核验
## 扰动/失效场景
## 可复算文件
```

## Quality checks

- 节点和边必须能回指题目对象，边权单位一致。
- 报告算法最优性条件、不可达情况和同最优解，而不是只给一条路径。
- 动态网络必须记录每次权重更新的时间与来源。
- 图示仅作表达，最终结论必须来自结构化边表和计算结果。
- 通信调度、路径与分配问题显式记录冲突边、容量、时窗和消息成功概率；概率边权不能未经解释直接当确定距离。
- 在线路由/切割/调度记录事件触发、不可撤销边或任务、重规划时限与回退；每次更新后重新检查连通性和可行性。
- Visio/Mermaid 网络图只表达结构，节点边数值必须来自可哈希的节点表和边表。

## Academic integrity boundaries

- 不伪造路网、边权、交通状态或求解结果。
- 不把启发式可行解写成已证明的全局最优解。
- 正式竞赛或工程决策中必须保留原始数据、参数和运行记录供用户核验。

## CUMCM 交接产物

返回 `inputs`、`assumptions`、`model_and_solver`、`machine_readable_results`、`diagnostics`、`unresolved_risks`、`latex_equations` 和 `recommended_figures`；同时提供结构化节点边表、可达/不可行说明和路径或流量复算。
