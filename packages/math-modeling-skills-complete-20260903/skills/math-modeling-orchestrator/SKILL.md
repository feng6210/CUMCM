---
name: math-modeling-orchestrator
description: Orchestrate mathematical-modeling work from problem decomposition through approved solving, validation, CUMCM Chinese LaTeX writing, figures, and delivery checks. Use for multi-stage modeling tasks; do not use to fabricate results or bypass model approval.
---

# 数学建模：总控调度

## Purpose

协调数模任务的拆题、模型路线、实验与验证、中文数模论文、图表和交付。总控维护唯一的 `workflow_state.json`，并把数值结果、论文声明和图表分开检查。

默认论文模式是 `cumcm-2026-electronic`：中文、LaTeX、XeLaTeX、摘要专页、无目录、按分问写作。用户提供正式模板时优先使用该模板。

## Required workflow

1. 识别 `task_mode` 与 `deliverable_mode`，登记题目、数据、现有代码和交付要求。
2. 调用 `mm-problem-decomposer` 与 `mm-variable-assumption-builder`，形成分问—输入—输出—约束—假设—论文章节映射。
3. 数据任务先调用 `mm-data-eda-cleaning`；无数据机理题必须列出参数来源和可辨识性风险。
4. 调用 `mm-model-selector`，给出可复现基线、主模型和备选模型；随后调用 `mm-model-innovation-designer`，形成路线、对照、实验计划、风险与回退。
5. 向用户汇报每问基线、模型路线、创新机理、验证方法、成本、失败回退和 `MODELING_EXPERIMENT_PLAN.yaml`。状态必须进入 `AWAITING_MODEL_APPROVAL`；没有有效 `model_approval` 不得首次进入 `SOLVING`。
6. 按批准路线调用专业模型 Skill。每个交接必须遵守 [跨 Skill 交接契约](references/cross_skill_output_contract.md)。
7. 为实际运行创建 `RUN_MANIFEST.json`；保留失败、不可行、超时和不收敛运行。先执行 [证据预检查](scripts/evidence_precheck.py)，再调用 `mm-uncertainty-validation` 做完整性、数值与稳健性判断。
8. 将已验证结果写入 `RESULTS_TO_CLAIMS.md` 和 `result_evidence_map.json`。文件存在或数字可定位只证明证据存在，不证明结论成立。
9. 只有 `PASS` 或范围明确的 `PARTIAL` 才能进入论文链。先依据 [国奖与优秀论文叙事—图表蒸馏](references/local_corpus/award_paper_narrative_figure_distillation.md) 建立 `NARRATIVE_MAP.yaml`：总矛盾、分问依赖、共享模型内核、逐问增量、证据位置、检验、声明边界和问间交接；再调用 `mm-paper-structure-writer`、`mm-abstract-polisher`、`mm-visualization-delivery`、`mm-paper-reviewer` 和 `mm-paper-compile`。
10. 终稿进入编译前，必须在平台允许且已获委派权限时自动启动彼此独立的 fresh-agent 审查：数字与结论、图表与证据绑定、CUMCM LaTeX 结构三条审查线分别由不继承写作上下文的 Agent 执行。只向审查 Agent 提供当前论文、冻结证据和审查标准，不提供预期答案、主写作者结论或拟议修复；审查报告记录 Agent 来源和工件哈希。
11. 若运行策略禁止委派或 fresh-agent 不可用，将 `independent_review_status` 设为 `INDEPENDENT_REVIEW_NOT_RUN`，显式报告原因并阻止“完整闭环/最终可交付”声明；不得静默降级为同一上下文自审。P0/P1 修复或结果、图表、正文变化后，旧独立审查标记 stale，并执行新的 fresh-agent 重审或由原独立 Agent 做受限 remediation follow-up。
12. 最终依次完成独立审查汇总、论文数字审计、引用审计、XeLaTeX/PDF 检查、支撑材料检查和普通赛制交付检查。

## State and amendments

使用 [workflow_state.py](scripts/workflow_state.py) 创建、显示、转换和批准状态。模型、目标、核心数据、约束、阈值或创新路线改变时，运行 `amend-plan`，使批准失效并回到 `INNOVATION_PROPOSED`。结果源文件变更时，运行 `mark-stale`，使结果到结论、论文审计和编译产物过期。

终稿状态还应记录 `independent_review_status`、`independent_reviewers`、`reviewed_artifact_hashes` 和 `independent_review_stale`。`same-agent-cold` 只能作为附加诊断，不能满足终稿独立审查门；同族 fresh-agent 审查也不得表述为外部机构认证。

`FAIL` 不得通过更换论文措辞进入摘要、结论或交付。`PARTIAL` 必须缩小声明范围。缺少输入使用 `BLOCKED_INPUT`；能力未覆盖使用 `BLOCKED_CAPABILITY`。

## CUMCM writing and delivery

- 电子版第一页为标题、摘要、关键词专页；不含承诺书和编号专用页。
- 不生成目录；正文按题目分问组织；正文与附录分开计页。
- 摘要、正文、附录、图表、代码与支撑材料均不得出现身份信息。
- 使用图表或正文数字前必须有机器可读结果与验证状态。
- 论文和支撑材料中的代码、数据、图表和数值必须能互相回指。
- 共享的坐标系、动力学、数据变换或评价规则集中建立一次；后续分问只写继承对象、模型增量、求解差异和误差传播。
- 图表分别承担导航、机制、证据或验证角色。精确答案优先进入表格；图形只负责不可被表格替代的结构、趋势、权衡或稳定性。

## Local corpus distillation route

- 需要参考本地真题、算法或论文经验时，读取 `references/local_corpus/` 下的来源边界、真题结构、创新模式、代码审查和中文写作规则；原始 `D:\数模文件` 不是运行依赖。
- 完整论文规划或改稿时必须读取 `references/local_corpus/award_paper_narrative_figure_distillation.md`，但不得复制其中样本的文本、答案、图形或排版缺陷，也不得把优秀论文标签当作当前结果的质量认证。
- 语料只提供候选问题结构和反例，不提供自动获准的模型。新模型、组合机制、阈值、核心数据或约束仍返回 `INNOVATION_PROPOSED`，并停在 `AWAITING_MODEL_APPROVAL`。
- 接收本地代码时先运行 `scripts/audit_local_corpus.py` 或等价静态盘点，再按 `SOURCE_ONLY → DEMO_ONLY → STATIC_OK_RUNTIME_UNVERIFIED → RUNTIME_VERIFIED → EVIDENCE_ELIGIBLE` 分级；文件存在、语法通过或脚本运行均不得输出语义 PASS。
- 真题回归至少覆盖机理--优化、预测--决策、统计--决策、几何--搜索、随机仿真和在线重规划中的相关结构，并记录输入接口、失败回退和验证负担。

## Boundaries

- 不设置 GitHub、仓库、分支、提交、PR 或远端状态门控；运行时不依赖 ARIS、GitHub、SSH、GPU、W&B 或 ML 会议工具链。
- 不伪造数据、结果、图表、参考文献或程序执行记录。
- ARIS 派生内容与本地化范围见 [归属说明](references/aris_derivation_notice.md)。

## Output format

```markdown
## 任务判断与当前状态
## 分问与依赖
## 模型、创新与实验计划
## 需要用户批准的决定
## 运行与验证证据
## 论文、图表与交付路径
## 未解决项与停止条件
```
