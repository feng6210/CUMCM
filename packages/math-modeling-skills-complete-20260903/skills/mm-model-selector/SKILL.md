---
name: mm-model-selector
description: Recommend suitable mathematical modeling methods based on problem type, data availability, objective, constraints, and interpretability needs. Use after problem decomposition or when the user asks which model to choose. Do not select models blindly or claim one model is always best.
---

# 数学建模：模型选型

## Purpose

帮助用户基于问题类型、数据条件、约束和解释性需求形成可复现基线与候选模型，为后续创新设计和用户批准提供输入，而不是直接开始求解。

## When to use

- 用户问“这个题用什么模型”。
- 已经有题目拆解，需要比较 2-4 个候选模型。
- 需要解释为什么不推荐某些常见模型。

## When not to use

- 问题目标和数据条件都不清楚。
- 用户只需要跑某个既定模型脚本。
- 用户要求保证获奖或用复杂模型包装结果。

## Required inputs

- 题目拆解。
- 数据类型和样本量。
- 目标、约束、解释性要求。
- 是否需要预测、评价、优化或仿真。

## Workflow

1. 判断问题类型和目标输出。
2. 判断数据条件：无数据、小样本、时间序列、多指标、高维特征、网络结构、随机过程或约束决策。
3. 给出 2-4 个候选模型。
4. 比较适用原因、前提、优点、风险、数据要求和论文表达难度。
5. 推荐一个可复现基线、一个主模型和至少一个备选模型，并给出所需专业 Skill。
6. 说明不建议使用的模型及原因。
7. 将状态标记为 `MODEL_PLANNED`，把候选方案交给 `mm-model-innovation-designer`，由其设计可验证创新与批准报告；在用户批准前不调用求解脚本。
8. 为每个候选模型说明最小数据条件、核心假设、输出形式、可用求解器、适配诊断、典型失败模式、可解释性、时间成本、LaTeX 公式表达和推荐图表。

候选模型不足或跨题型时先读取 [model_selection_matrix.md](references/model_selection_matrix.md) 与 [model_family_cards.md](references/model_family_cards.md)，不得只按关键词套模型。

## Output format

```markdown
## 问题类型判断

## 候选模型比较

| 模型 | 适用原因 | 所需数据 | 优点 | 风险 | 论文表达难度 |
|---|---|---|---|---|---|

## 推荐主模型

## 推荐备选模型

## 不建议使用的模型

## 后续创新设计输入

- 基线：
- 基线不足：
- 候选专业 Skill：
- 必须验证的风险：

## 下一步建议
```

## Quality checks

- 不能说某个模型永远最好。
- 推荐必须和题目目标、数据条件一致。
- 复杂模型需要说明额外数据、调参和解释风险。
- 选型结束不等于获准求解；下一状态应为 `MODEL_PLANNED`，下一 Skill 应为 `mm-model-innovation-designer`。
- 混合题必须说明不同模型之间的数据接口；复杂模型不能只因名称新颖被推荐。
- 选型前读取总控 `references/local_corpus/real_problem_coverage.md` 的结构覆盖，按目标、信息结构、数据形态、约束和验证成本匹配，不按赛题字母或往年模型名称匹配。
- 每个候选模型必须给出最小基线、接口输出形态、可否辨识/求解、专属诊断和时间预算；若简单模型足够，允许明确拒绝组合模型。

## Academic integrity boundaries

- 只能用于学习、训练、课程作业辅助、赛前准备、结构检查和结果复盘。
- 不代写完整参赛论文，不代替用户参赛，不承诺获奖或保奖。
- 不伪造数据、代码运行结果、图表、参考文献或实验结论。
- 正在进行的正式竞赛中，必须提醒用户遵守赛事规则、课程要求和学术诚信。
- 所有不确定结论、推断条件和未验证结果都必须标注“需要用户核验”。
