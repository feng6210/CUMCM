---
name: mm-model-innovation-designer
description: Design auditable mathematical-modeling innovation routes only after problem semantics and minimum baselines are locked, including mechanisms, ablations, risks, fallbacks, and a mandatory user-approval gate. Use when the user asks how to innovate, how a proposed model compares with award-winning approaches, or which route should be implemented. Do not decorate a weak or wrongly-posed model with buzzwords, copy award papers, or start solving before approval.
---

# 数学建模：模型创新设计与批准门

## Purpose

把“怎么创新”建立在**正确题意 + 已验证基线不足**之上。每个创新点必须回答：基线具体哪里失败、改动为什么能修复、如何被反例击穿、失败后如何回退。没有基线不足证据时，复杂化不算创新。

## Required inputs

- `QUESTION_DECOMPOSITION.json` 与 `PROBLEM_SEMANTICS.yaml`。
- 最小正确基线及正式 evaluator 结果。
- 数据审计或机理边界。
- `mm-model-selector` 的候选模型与淘汰理由。
- 时间、算力、软件、可解释性和竞赛/课程规则约束。
- 可引用的往年真题、优秀论文或外部方法资料，如有。

## Workflow

1. 再次确认 `PROBLEM_SEMANTICS.yaml` 已锁定；创新阶段不得顺手改主目标、时间口径、资源复用或硬约束。若确需改变，触发 semantic amendment。
2. 为每问读取最小基线，写出 `baseline_successes` 与 `baseline_failures`。如果基线已满足题目核心要求，可以明确“不升级”，不为了创新名义继续叠模型。
3. 生成三条路线：A 为稳健基线延伸，B 为推荐创新，C 为高收益高风险探索；不存在合理 C 时写“无”。
4. 每个创新点写 `痛点/基线失败 → 改动 → 生效机理 → 可观察证据 → 新增验证负担 → 失败风险 → 回退方案`。
5. 创新优先来自：更合理的机理/几何判据、状态/表示、目标/约束、信息结构、分解方式、不确定性处理或求解器结构；只换 DE/PSO/GA/SA 名称不构成核心创新。
6. 对组合模型 `X+Y`，必须证明 X 的实证不足、接口、Y 的修复机理，并设计 X/Y/X+Y 同协议对照；否则降级为待验证想法。
7. 如使用优秀论文/外部方法，只迁移结构原则。若外部论文给出可行策略参数，在 training/research 等允许场景中同时把它登记为后续 `BENCHMARK_CHALLENGE` 输入，而不是只用于“灵感”。
8. 设计基线对照、消融、稳健性和外部击穿测试。成功标准必须区分：模型效果、数值稳定、搜索质量、现实解释。
9. 对优化路线说明为什么选择某种求解结构，避免无机制叠加多个启发式；复杂度升级必须对应已识别瓶颈。
10. 给出 `figure_intents`：优先标识需要解释的机理/几何/case/协同结构，不规定固定图数；验证图是否进正文由 `competition_compact` 叙事阶段决定。
11. 按问题适配度、可验证性、实现成本、解释性、失败风险和时间预算排序，给出主推荐与回退路线。
12. 向用户汇报并进入 `AWAITING_MODEL_APPROVAL`；在明确批准前停止主求解。

## Output format

```markdown
## 当前状态
AWAITING_MODEL_APPROVAL

## 已锁定题意语义
## 每问最小基线及实证不足
## 路线 A：稳健基线延伸
## 路线 B：推荐创新
## 路线 C：高风险探索
## 创新证据卡
| 创新点 | 基线失败 | 改动与机理 | 对照/消融 | 外部挑战 | 成功标准 | 风险与回退 |
## 与往年优秀方案的结构化对比
## 推荐决定与理由
## 需要用户批准的选项
```

批准选项至少包括：`批准推荐路线`、`选择其他路线`、`要求修改方案`。只有明确批准才生成 `model_approval` 记录并交回总控。

## Quality checks

- 每问都有基线、候选路线、验证指标和失败回退。
- 创新必须解决已识别的误差、约束、机理、信息或计算痛点，不以模型数量论创新。
- 没有基线失败证据时，不允许把复杂化写成“必要创新”。
- “优于优秀论文”只能在同 evaluator/同数据/同指标或可辩护等价基准上比较；否则只陈述结构差异。
- 用户提供外部可行策略时，若规则允许，应登记为后续外部挑战，而不是忽略其可比较价值。
- 推荐路线在给定时间与算力内可完成；高风险路线不得阻塞基础交付。
- 输出必须停在 `AWAITING_MODEL_APPROVAL`，批准记录缺失时不得进入主 `SOLVING`。

## Academic integrity boundaries

- 仅用于学习、训练、赛前准备、科研和实际决策辅助；正式竞赛与课程中必须遵守相关规则。
- 不复制获奖论文文本、图表、代码或结果，不伪造来源、许可证、实验或创新性。
- 不承诺获奖，不把“结构相似”说成“达到国奖水平”。
- 只有经过对照、消融和独立验证的改进才能写成已支持的创新结论。
