---
name: mm-paper-reviewer
description: Review a mathematical modeling paper draft for target-semantic mismatch, unanswered questions, weak assumptions, model mismatch, missed external feasible benchmarks, unsupported optimality claims, unclear or excessive figures, audit/responder-style leakage, and academic integrity risks. Use for critique and revision planning. Do not let language polishing hide mathematical failures or rewrite the full paper as a final submission.
---

# 数学建模：论文冷审稿与对抗性检查

## Purpose

对数学建模论文草稿做冷审稿、查错和修改优先级规划。先攻击会改变结论的 P0/P1：题意语义、目标函数、资源计数、约束、数据泄漏、已知更优可行解、未证明最优性；再检查叙事、图表、自然度和排版。

“语言像 AI/审计报告”只能排在数学正确性之后。任何措辞修复都不能把 FAIL/PARTIAL、未收敛区域、搜索域限制或候选最优静默改写成更强结论。

## When to use

- 用户提供论文草稿。
- 需要检查是否回答每一问。
- 需要找模型、变量、公式、图表、结果、摘要和竞赛叙事问题。
- 用户提供国奖/优秀论文、公开解或基准，希望判断当前解是否被击穿。
- 技术结果已冻结，希望在交 `mm-paper-humanizer` 前后做冷审。

## When not to use

- 用户要求编造缺失结果或参考文献。
- 用户只有题目、没有草稿/结果且目的不是方案审查。
- 纯文字自然化且技术 P0/P1 已明确关闭时，可直接交 `mm-paper-humanizer`；但终稿仍需回到 reviewer 做声明和数字复核。

## Required inputs

- 论文草稿、题目和附件。
- `PROBLEM_SEMANTICS.yaml`（或等价目标语义记录）。
- 数据、代码或机器结果，如果有。
- `RESULTS_TO_CLAIMS.md` / `result_evidence_map.json`，如果已有。
- `BENCHMARK_CHALLENGE.json` 或用户提供的外部方案，如果适用。
- `reporting_profile`。

## Workflow

1. 检查是否回答每一问，并逐问对照题面原始目标。
2. **语义审稿优先**：检查主目标、集合并/交、时间计数、资源复用、一对一指派、多目标聚合是否与 `PROBLEM_SEMANTICS.yaml` 一致；正文是否在不同章节静默换口径。
3. 检查模型前提、变量、单位、约束和信息时序；检查是否加入题面没有的限制并忘记标为假设。
4. 对优化强声明检查最小基线、正式 evaluator 重算、求解器预算、最优性边界和外部挑战。多种子相近不能单独支持“已覆盖主要盆地”。如果用户提供更优外部可行解，要求在当前 evaluator 下复算；领先超过容差时把“最佳/稳定最优”按 P1 处理。
5. 检查 `NARRATIVE_MAP.yaml`：分问依赖、共享内核、继承对象、模型增量、精确结果、检验和声明边界是否在**证据层**闭合；问题分析是否说明数学对象和难点而不是重述原题。不要把“证据层闭合”误判成“正文每个结果句都必须显式写验证和边界”。
6. 先清点当前 `FIGURE_PLAN.yaml` 与 PDF 实际图表，再判断缺图；每张图有没有读者任务，复杂几何/机理是否缺解释图。二维、三维及组合按真实坐标/参数维度和用户风格选择，不把已有热图/曲面误报为缺失，也不强制凑图数。
7. 检查 `reporting_profile`：
   - `competition_compact`：大量 gate 名、hash、backend report、旧版本 FAIL 谱系、全部随机种子、微小数值差如未改变科学判断，按“审计泄漏/正文过工程化”记录 P2/P3，并建议移附录；
   - `research_audit`：可保留，但仍要求叙事层级清楚。
8. **检查作者站位与自然度，但不做来源判定。** 重点寻找：
   - 回答者惯性：`这里需要说明/值得注意/接下来我们` 等元话语反复出现；
   - 自我辩护：`本文不声称/不据此认为` 等免责声明密集；
   - 纠正式推进：连续 `不是X而是Y/不等于/不意味着/不能说明`；
   - 服务式或模板式段尾：每段都总结、拔高或“为后文奠定基础”；
   - 每个结果都重复 `验证 → caveat → 不能声称`；
   - 算法按 `首先A→然后B→随后C→最后D` 流水账串联；
   - 句法/段落高度同构、机械连接词堆积、空泛“显著/有效/可靠/鲁棒”。
   单个词不构成缺陷，按局部密度、段落功能和是否有证据判断。已经自然的段落应明确列入“不建议改动”，避免过度修订。
9. 对第 8 步发现的问题区分两类：
   - **必须就地保留的边界**：最优性等级、未收敛区域、比较口径、统计不确定性、模型内/因果外推等会改变答案含义的限制；
   - **可迁移的审计脚手架**：重复 solver 日志、hash/gate/backend、相同 caveat 的多次复述、无读者价值的版本谱系。
   只有后一类建议删除/迁移。前一类只能最小化表述，不得消失。
10. 检查摘要是否按分问包含模型结构和关键结果，而不是算法名串联、验证术语串联或每问都附一段免责声明。摘要验证只需要最有区分度的一项；限制只在不写会改变核心答案解释时进入摘要。
11. 检查模型检验、敏感性、外部挑战和局限是否与结论强度匹配；验证图不是固定配额。技术结果通过不等于正文应展示全部验证过程。
12. 检查参考文献、匿名、LaTeX 结构和附录代码；编译问题交给 `mm-paper-compile`。代码/附录若存在 `NOT_ALLOWED_BY_USER / workflow_state / registered_before_run / evidence_commit` 等 agent/workflow 元数据，判断是否有数学复现价值；没有则建议从正式竞赛支撑材料的展示层清理。
13. 生成 `PAPER_CLAIM_AUDIT.json`，把每条数字、比较、排名、百分比、范围和最优性措辞关联到原始结果/挑战状态；结果或语义变化后标记 stale。
14. 当 P0/P1 已关闭、结果与 claim scope 冻结，而主要剩余问题是第 8–10 步的表达时，建议交 `mm-paper-humanizer`。默认 `light`；审计味/回答者姿态明显时用 `compact`。Humanizer 之后必须执行其 integrity gate，并重新做数字/声明冷审；不得把 humanizer 自检当独立技术认证。
15. 对完整终稿，在平台允许且已获委派权限时自动启动不继承写作上下文的 fresh-agent，至少分为：题意语义/目标一致性、数字/约束/最优性、图表/读者任务/证据、CUMCM 结构/叙事。FULL_SUBMISSION 的角色、数量和 provenance 以总控硬契约为准。
16. 汇总 P0--P3。P0/P1 未解决时阻止最终交付；正文、图表、目标或结果变化后对应报告 stale。纯 prose 自然化若 integrity gate 保证数学对象/数字/claim 不变，可继承上游证据，但最终文字仍需重新绑定当前稿件。

审查维度和风险分级见 [review_checklist.md](references/review_checklist.md)。题意语义与外部挑战规则见总控 `references/problem_semantics_and_benchmark_protocol.md`。

完整终稿修订同时读取 [读者任务与修订闭环](../mm-paper-structure-writer/references/paper_readability_and_revision.md)：检查图后“现象—模型内解释—意义—必要边界”、计算时间窗/聚合口径、选择性强调及真实 PDF 版面。自然化专项规则由 `mm-paper-humanizer` 负责，reviewer 只判断问题、优先级和是否发生技术漂移。

源/图/PDF 变化后保留旧报告，逐项判定受影响范围。仅图注所在全文变化而图和实际图注未变时，需要重读语境并形成新的限定复核；不能只把旧报告哈希刷新为 PASS。关键争议由另一 agent 直接读取原图或原始结果，修复后交原审者复查。

## Output format

```markdown
## 总体评价
## P0/P1：题意、目标、约束与外部击穿
## 分问模型与结果审查
## 叙事与共享内核
## Figure planning / 图表审查
## 竞赛正文 vs 工程审计信息
## 作者站位与模板化表达
## 摘要与结论
## 附录、引用与 LaTeX
## 优先修改清单
## 不建议改动的部分
```

## Quality checks

- 发现问题要给位置、证据、影响和最小修复。
- 优先级按是否改变答案/模型/可行域/排名排序，先 P0/P1 再语言和审美。
- 无法核验的结果必须标注风险，不替作者补造结果。
- 语言审查不输出“AI 概率”，不判断作者身份，不承诺绕过检测器。
- 引用分别检查存在性、元数据和语境支持；不能用看似真实的文献填缺口。
- 冷审查同时检查模型名与实现、示例/随机数据、数据泄漏、求解状态、原始约束重算和未证明的最优性。
- 每问在证据层检查“任务—语义—变量—模型—关键数值—验证—边界”闭合；正文不需要机械复制该顺序。
- 对共享模型检查“只定义一次、后续写增量”；对问间交接检查版本和误差传播。
- 图表不按数量打分：机制解释缺失是问题，验证图过量同样是问题。
- `competition_compact` 的正文如果读起来像软件 QA/审稿回复而不是数模论文，必须区分“必须保留的科学边界”和“可迁移审计脚手架”，再提出压缩建议。
- 已经自然、直接、术语稳定且证据边界正确的段落必须允许 `NO_CHANGE_RECOMMENDED`；不为制造修改而改写。
- Humanizer 改写后如公式、数字、引用、单位或 claim scope 发生变化，按技术变更处理，不得归类为 P3 文风修改。

## Academic integrity boundaries

- 只能用于学习、训练、课程作业辅助、赛前准备、结构检查和结果复盘。
- 不伪造数据、代码运行结果、图表、参考文献或实验结论。
- 正在进行的正式竞赛中，外部资料与 AI 使用必须遵守赛事规则。
