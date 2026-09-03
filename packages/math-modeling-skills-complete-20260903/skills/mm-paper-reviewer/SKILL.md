---
name: mm-paper-reviewer
description: Review a mathematical modeling paper draft for target-semantic mismatch, unanswered questions, weak assumptions, model mismatch, missed external feasible benchmarks, unsupported optimality claims, unclear or excessive figures, audit leakage, and academic integrity risks. Use for critique and revision planning. Do not rewrite the full paper as a final submission.
---

# 数学建模：论文冷审稿与对抗性检查

## Purpose

对数学建模论文草稿做冷审稿、查错和修改优先级规划。先攻击会改变结论的 P0/P1：题意语义、目标函数、资源计数、约束、数据泄漏、已知更优可行解、未证明最优性；再检查叙事、图表和排版。

## When to use

- 用户提供论文草稿。
- 需要检查是否回答每一问。
- 需要找模型、变量、公式、图表、结果和摘要问题。
- 用户提供国奖/优秀论文、公开解或基准，希望判断当前解是否被击穿。

## When not to use

- 用户要求代写终稿。
- 用户只给题目但没有草稿/结果，且目的不是方案审查。
- 用户要求编造缺失结果或参考文献。

## Required inputs

- 论文草稿、题目和附件。
- `PROBLEM_SEMANTICS.yaml`（或等价目标语义记录）。
- 数据、代码或机器结果，如果有。
- `BENCHMARK_CHALLENGE.json` 或用户提供的外部方案，如果适用。
- `reporting_profile`。

## Workflow

1. 检查是否回答每一问，并逐问对照题面原始目标。
2. **语义审稿优先**：检查主目标、集合并/交、时间计数、资源复用、一对一指派、多目标聚合是否与 `PROBLEM_SEMANTICS.yaml` 一致；正文是否在不同章节静默换口径。
3. 检查模型前提、变量、单位、约束和信息时序；检查是否加入题面没有的限制并忘记标为假设。
4. 对优化强声明检查最小基线、正式 evaluator 重算、求解器预算、最优性边界和外部挑战。多种子相近不能单独支持“已覆盖主要盆地”。如果用户提供更优外部可行解，要求在当前 evaluator 下复算；领先超过容差时把“最佳/稳定最优”按 P1 处理。
5. 检查 `NARRATIVE_MAP.yaml`：分问依赖、共享内核、继承对象、模型增量、精确结果、必要检验和声明边界是否闭合；问题分析是否说明数学对象和难点而不是重述原题。
6. 检查 `FIGURE_PLAN.yaml` 与正文：每张图有没有不可替代读者任务；复杂几何/机理是否缺解释图；算法/验证图是否反而过量；能用二维解释时是否强行 3D。
7. 检查 `reporting_profile`：
   - `competition_compact`：大量 gate 名、hash、backend report、旧版本 FAIL 谱系、全部随机种子、微小数值差如未改变科学判断，按“审计泄漏/正文过工程化”记录 P2/P3，并建议移附录；
   - `research_audit`：可保留，但仍要求叙事层级清楚。
8. 检查摘要是否按分问包含模型结构和关键结果，而不是算法名串联或验证术语串联。
9. 检查模型检验、敏感性、外部挑战和局限是否与结论强度匹配；验证图不是固定配额。
10. 检查参考文献、匿名、LaTeX 结构和附录代码；编译问题交给 `mm-paper-compile`。
11. 生成 `PAPER_CLAIM_AUDIT.json`，把每条数字、比较、排名、百分比、范围和最优性措辞关联到原始结果/挑战状态；结果或语义变化后标记 stale。
12. 对完整终稿，在平台允许且已获委派权限时自动启动不继承写作上下文的 fresh-agent，至少分为：
    - 题意语义/目标一致性；
    - 数字/约束/最优性；
    - 图表/读者任务/证据；
    - CUMCM 结构/叙事。
    审查 Agent 只接收当前工件、冻结证据与检查表，不提供期望 PASS。
13. 汇总 P0--P3。P0/P1 未解决时阻止最终交付；正文、图表、目标或结果变化后对应报告 stale。

审查维度和风险分级见 [review_checklist.md](references/review_checklist.md)。题意语义与外部挑战规则见总控 `references/problem_semantics_and_benchmark_protocol.md`。

## Output format

```markdown
## 总体评价
## P0/P1：题意、目标、约束与外部击穿
## 分问模型与结果审查
## 叙事与共享内核
## Figure planning / 图表审查
## 竞赛正文 vs 工程审计信息
## 摘要与结论
## 附录、引用与 LaTeX
## 优先修改清单
## 不建议改动的部分
```

## Quality checks

- 发现问题要给位置、证据、影响和最小修复。
- 优先级按是否改变答案/模型/可行域/排名排序，先 P0/P1 再审美。
- 无法核验的结果必须标注风险，不替作者补造结果。
- `same-agent-cold` 仅可作为补充诊断；终稿独立审查要求 fresh-agent（若平台允许）。
- 引用分别检查存在性、元数据和语境支持；不能用看似真实的文献填缺口。
- 冷审查同时检查模型名与实现、示例/随机数据、数据泄漏、求解状态、原始约束重算和未证明的最优性。
- 每问检查“任务—语义—变量—模型—关键数值—必要验证—边界”闭合。
- 对共享模型检查“只定义一次、后续写增量”；对问间交接检查版本和误差传播。
- 图表不按数量打分：机制解释缺失是问题，验证图过量同样是问题。
- `competition_compact` 的正文如果读起来像软件 QA 报告而不是数模论文，必须提出压缩和迁移建议。

## Academic integrity boundaries

- 只能用于学习、训练、课程作业辅助、赛前准备、结构检查和结果复盘。
- 不代写完整参赛论文，不代替用户参赛，不承诺获奖或保奖。
- 不伪造数据、代码运行结果、图表、参考文献或实验结论。
- 正在进行的正式竞赛中，外部资料与 AI 使用必须遵守赛事规则。
