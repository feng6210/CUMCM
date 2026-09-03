---
name: mm-uncertainty-validation
description: Validate mathematical models with residual checks, uncertainty propagation, sensitivity analysis, scenario stress tests, convergence tests, robustness analysis, and reproducibility evidence. Use before turning any numerical result into a claim. Do not treat a solver success flag or one random seed as sufficient validation.
---

# 数学建模：不确定性与结果验证

## Purpose

作为所有模型的独立验证门，区分“程序运行成功”“数值解可信”“结论对扰动稳定”“现实解释成立”。

## When to use

- 已有模型结果，需要判断是否能支撑结论。
- 参数、数据、随机种子、步长、权重或情景存在不确定性。
- 使用数值积分、优化、仿真、机器学习或逆问题。
- 需要灵敏度、置信区间、误差传播、稳健性或复现实验。

## When not to use

- 尚未定义待验证的结果和评价标准。
- 用户希望用漂亮图替代验证。
- 只做文字润色而无模型结果。

## Required inputs

- 原始数据、模型版本、参数、随机种子和求解器设置。
- 主要结果、声明和通过/失败标准。
- 参数范围、误差来源或情景概率依据。
- 可比较的基线、极限情形或外部观测。

## Workflow

1. 建立结果—声明映射，列出每个声明所需证据。
2. 检查可复现性、残差、守恒、约束、收敛和边界情况。
3. 选择局部敏感性、全局敏感性、Bootstrap、蒙特卡洛传播或情景压力测试。
4. 至少改变一个关键参数、随机种子或数值分辨率并重新计算。
5. 区分点估计变化、排序变化、可行性变化和结论翻转。
6. 输出 PASS/PARTIAL/FAIL 与失败证据，不重新解释失败。
7. 将通过验证的结果映射到 `RESULTS_TO_CLAIMS.md` 和 `result_evidence_map.json`：`yes` 可进入摘要和结论，`partial` 必须缩小范围，`no` 或 `blocked` 不能形成正式声明。证据文件存在只证明可定位，不证明结论为真。

先读 [validation_protocol.md](references/validation_protocol.md)。基础扰动与重采样可运行 `scripts/uncertainty_analysis.py`。

## Output format

```markdown
## 待验证声明
## 验证设计
## 数值/统计证据
## 灵敏度与压力测试
## PASS/PARTIAL/FAIL
## 仍未覆盖的风险
```

## Quality checks

- 求解器 `success` 只证明终止状态，不证明建模正确或全局最优。
- 随机方法报告种子、样本量、Monte Carlo 标准误和区间。
- 优化结果检查原始约束、目标重算和多初值/多算法一致性。
- 论文数值必须能回指机器可读输出。
- 预测、优化、评价、机理、统计、仿真和聚类必须选择适配检验；不把 RMSE、MAPE、固定种子数或固定参数扰动机械套用到所有模型。
- 原始数据、预处理数据、配置、结果和失败运行必须分开保留；不得用模型输出构造真实值，不得只保留最好随机种子或初值。
- 对接收代码先引用总控 `references/local_corpus/code_audit_rules.md` 的四层门与五级状态；语法通过、运行完成或求解器成功均不是模型语义 PASS。
- 组合模型验证必须含简单基线、单组件和组合模型同协议对照；预测--决策链同时验证预测误差传播和最终决策损失。
- 源码编码、依赖、字体、警告和输出重开属于可复现性证据；转码后的临时副本通过不得抹去原始源码不可直接运行的事实。

## Academic integrity boundaries

- 不删除失败运行或只报告最优随机种子。
- 不在看过验证结果后悄悄改变通过标准。
- 不把未覆盖的不确定性写成“已证明稳定”。
