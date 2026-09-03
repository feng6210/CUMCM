---
name: mm-statistical-inference
description: Design sampling, hypothesis testing, uncertainty-aware estimation, longitudinal analysis, survival analysis, and measurement-error workflows. Use when conclusions depend on statistical evidence rather than point prediction alone. Do not report significance, confidence, or diagnostic accuracy without a valid sampling and validation design.
---

# 数学建模：统计推断与试验设计

## Purpose

为抽样检测、置信区间、假设检验、重复测量、生存/事件时间和测量误差问题建立可解释的统计证据链。

## When to use

- 需要决定抽检数量、接受/拒绝规则或风险水平。
- 结论依赖置信区间、显著性、效应量或统计功效。
- 数据有重复测量、删失、分组、批次、个体相关或测量误差。
- 分类/诊断任务需要概率校准、灵敏度、特异度或成本敏感阈值。

## When not to use

- 数据来自便利样本却要外推总体且无边界说明。
- 只需确定性机理求解。
- 先看结果再选择检验方法或阈值。

## Required inputs

- 总体、抽样单位、抽样机制和独立性结构。
- 假设、错误代价、显著性水平、功效或允许误差。
- 分组、时间、个体、批次、删失和测量精度字段。
- 预先确定的主要指标和分析方案。

## Workflow

1. 明确总体、抽样框、观测单位和相关结构。
2. 区分估计、检验、抽样验收、重复测量、生存或测量误差任务。
3. 预先登记主要假设、指标、阈值和多重比较处理。
4. 检查缺失、删失、类不平衡、组间泄漏和样本量/功效。
5. 输出点估计、区间、效应量及假设诊断，避免只报 p 值。
6. 通过重采样、替代模型或敏感性分析验证结论。

先读 [inference_guide.md](references/inference_guide.md)。二项抽检可运行 `scripts/binomial_sampling_plan.py`。

## Output format

```markdown
## 抽样与研究设计
## 假设和主要指标
## 方法及前提
## 点估计与区间
## 诊断/校准
## 局限与适用总体
```

## Quality checks

- 训练集、调参集和最终评估集必须分离；个体/时间/批次数据按组切分。
- 不把随机划分用于明显的时间外推或同一对象重复测量。
- 同时报告分母、样本量、区间、效应量和未定义指标。
- 测试或阈值经过结果驱动选择时，结论必须降级为探索性。
- 抽样检测题必须把误判成本、置信水平、停止规则和后续生产决策连接起来；“估计精度高”不等于决策成本低。
- 催化剂/工艺类实验设计先估计主效应、交互和可行域，再选择下一批实验；不能看到结果后静默更改主要指标。
- 纵向、批次和空间数据保留相关结构；多重比较、效应量、分母接近零的相对改善和百分点/百分比必须分别审查。

## Academic integrity boundaries

- 不挑选最有利的划分、指标或显著结果。
- 不把相关性写成因果结论。
- 不伪造样本量、置信区间、p 值、AUC 或验证结果。

## CUMCM 交接产物

返回 `inputs`、`assumptions`、`model_and_solver`、`machine_readable_results`、`diagnostics`、`unresolved_risks`、`latex_equations` 和 `recommended_figures`；样本定义、检验前提、区间、效应量和多重比较处理必须可复算。
