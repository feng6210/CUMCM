---
name: mm-model-innovation-designer
description: Design auditable mathematical-modeling innovation routes after problem decomposition and model selection, including baselines, mechanisms, ablations, risks, fallbacks, and a mandatory user-approval gate. Use when the user asks how to innovate, how a proposed model compares with award-winning approaches, or which route should be implemented. Do not use to decorate a weak model with buzzwords, claim unverified novelty, copy award papers, or start solving before approval.
---

# 数学建模：模型创新设计与批准门

## Purpose

把“用什么模型、怎么创新”变成可审计的方案决策：为每一问提出保守、推荐和高风险三条路线，说明基线、改动机理、验证办法、失败回退与时间成本，并在用户明确批准前暂停数值求解。

## When to use

- 拆题和初步模型选型已经完成，需要向用户汇报具体调用哪个模型。
- 用户问“怎么创新”“和国奖方案比怎么样”“为什么不是换个算法名”。
- 需要在竞赛时间、数据、算力和论文表达风险之间选路线。
- 需要把国奖论文或开源项目中的做法迁移到结构相似的新题，但不能照搬。

## When not to use

- 题目目标、分问关系或数据条件尚未厘清。
- 用户只要求执行已经批准且固定的模型。
- 以复杂度、深度学习或算法堆叠冒充创新。
- 要求声称“原创”“国奖水平”或保证获奖，但没有新颖性检索和实证证据。

## Required inputs

- `mm-problem-decomposer` 的分问、输入、输出、约束和依赖关系。
- 数据审计或 EDA 结论；尚无数据时必须显式标记。
- `mm-model-selector` 的基线、候选模型与淘汰理由。
- 时间、算力、软件、可解释性和竞赛/课程规则约束。
- 可引用的往年真题、国奖论文或已提供的外部方法资料，如有。

## Workflow

1. 为每一问锁定一个可复现基线，写清它解决什么、解决不了什么，以及最小成功指标。
2. 生成三条互斥或可组合路线：A 为稳健基线，B 为推荐创新，C 为高收益高风险探索；不存在合理的 C 时明确写“无”。
3. 依据 [innovation_evaluation_guide.md](references/innovation_evaluation_guide.md) 将创新分为 L0—L4，并归入机理、表示/状态、目标/约束、求解器、不确定性/验证或交付六类。
4. 每个创新点必须写出 `痛点 → 改动 → 生效机理 → 可观察证据 → 失败风险 → 回退方案`；缺任一项则降级为待验证想法。
5. 设计基线对照、消融实验、稳健性/敏感性检查和通过阈值。只换算法名、只提高复杂度或只做图表美化不得计为核心创新。
6. 如使用国奖论文或外部方法资料，只迁移结构原则，按 [award_transfer_rules.md](references/award_transfer_rules.md) 记录题目结构匹配、来源、许可证、需要重写的部分和不可迁移项；不得把外部仓库可访问性当作运行条件。
7. 按问题适配度、可验证性、实现成本、解释性、失败风险和时间预算排序，给出主推荐与回退路线。
8. 使用 [model_innovation_report_template.md](references/model_innovation_report_template.md) 向用户汇报，并把状态置为 `AWAITING_MODEL_APPROVAL`。
9. 在用户明确选择路线或批准推荐方案之前停止；不得调用专业求解 Skill、运行最终求解或把草案写成已完成结果。

## Output format

```markdown
## 当前状态
AWAITING_MODEL_APPROVAL

## 每问模型与基线
| 分问 | 数据/机理特征 | 基线 | 基线不足 | 候选专业 Skill |

## 路线 A：稳健基线
## 路线 B：推荐创新
## 路线 C：高风险探索

## 创新证据卡
| 创新点 | 等级/类别 | 痛点 | 改动与机理 | 对照/消融 | 通过阈值 | 风险与回退 |

## 与往年获奖方案的结构化对比
## 推荐决定与理由
## 需要用户批准的选项
```

批准选项至少包括：`批准推荐路线`、`选择其他路线`、`要求修改方案`。只有明确批准才生成 `model_approval` 记录并交回总控。

## Quality checks

- 每一问都有基线、候选路线、验证指标和失败回退。
- 创新必须解决已识别的误差、约束、机理或交付痛点，不以模型数量论创新。
- “优于国奖论文”只能在同数据、同指标或可辩护的等价基准上比较；否则只陈述结构差异。
- 不把参考论文的结论、代码可运行性或许可证状态当作已经核实，除非有当前证据。
- 推荐路线在给定时间与算力内可完成；高风险路线不得阻塞基础交付。
- 输出必须停在 `AWAITING_MODEL_APPROVAL`，批准记录缺失时不得进入 `SOLVING`。

## 实验计划与消融

每条路线还必须给出 `MODELING_EXPERIMENT_PLAN.yaml` 的最小块：待支持结论、基线、必跑与可选实验、一次只改变的因素、成功标准、失败解释、目标图表和回退。只有主模型已有可解释结果时才安排消融；新增模型、目标、数据、阈值或核心约束时必须生成计划修订并重新等待用户批准。

没有对照证据时只能写“提出并测试”，不能写“显著提高”。经典模型足够时允许明确选择不新增创新。

## 本地组合模型准入

读取总控 `references/local_corpus/innovation_patterns.md` 与 `code_audit_rules.md`。残差修正、代理优化、精确子问题+启发式、Pareto+偏好、表示学习+下游、机理+残差、预测+优化和在线重规划只作为机制模板。任何 `X+Y` 必须说明 X 的实证不足、接口、Y 的修复机理、X/Y/X+Y 同协议对照与失败回退；否则只记为想法。代码是 `DEMO_ONLY` 或 `RUNTIME_VERIFIED` 时不得把创新写成已支持结论。

## Academic integrity boundaries

- 仅用于学习、训练、赛前准备、科研和实际决策辅助；正式竞赛与课程中必须遵守相关规则。
- 不复制获奖论文文本、图表、代码或结果，不伪造来源、许可证、实验或创新性。
- 不承诺获奖，不把“结构相似”说成“达到国奖水平”。
- 只有经过对照、消融和独立验证的改进才能写成已支持的创新结论；其余标注“待验证”。
