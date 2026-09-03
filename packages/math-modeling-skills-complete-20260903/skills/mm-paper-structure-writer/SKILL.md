---
name: mm-paper-structure-writer
description: Create evidence-grounded Chinese CUMCM mathematical-modeling paper outlines and LaTeX drafts, including abstract pages, question-based sections, appendices, and support-material lists. Use after results are verified; do not fabricate evidence or write a final paper for an active contest when rules do not allow it.
---

# 数学建模：CUMCM 中文 LaTeX 论文结构与初稿

## Purpose

默认生成中文、CUMCM 电子版格式、XeLaTeX 的数学建模论文。论文不是普通研究论文：不默认写 Introduction、Related Work、Method 或 Experiments，而是围绕赛题分问、模型、结果、检验和结论组织。

默认模板在 [assets/cumcm-2026](assets/cumcm-2026)。它是依据 CUMCM 2026 格式要求实现的内置模板，不是组委会官方模板；用户提供正式 `.cls`、`.sty` 或 `.tex` 模板时，用户模板优先。

## Modes

1. **结构模式**：输出 `PAPER_PLAN.md`、分问—章节映射、证据缺口和 LaTeX 章节骨架。
2. **完整 LaTeX 初稿模式**：仅当用户明确需要完整论文、场景允许且关键结果已有可追溯验证证据时，复制模板到任务 `paper/` 目录并填写 `main.tex`、`sections/*.tex`、表格、图形和附录。

信息或证据不足时只能使用结构模式；不得用看似合理的数值、图表或引用填满正文。

## Required workflow

1. 读取题目、分问、假设、结果、图表和 `RESULTS_TO_CLAIMS.md`。每个数字必须能回指 `result_evidence_map.json`；完整论文任务同时读取总控的 [国奖与优秀论文叙事—图表蒸馏](../math-modeling-orchestrator/references/local_corpus/award_paper_narrative_figure_distillation.md)。
2. 先建立 `NARRATIVE_MAP.yaml`：论文总矛盾、分问依赖图、共享模型内核、每问继承对象与模型增量、精确结果位置、检验、声明边界和问间交接。各问确实独立时写明理由，不得强行串联。
3. 再建立中文 `PAPER_PLAN.md`：论文主线、分问和章节对应、Claims–Evidence Matrix、公式计划、图表角色与预算、摘要事实表、正文页数预算、附录和待补证据。
4. 按 CUMCM 结构写作：摘要专页、问题重述、问题分析、模型假设、符号说明、数据处理、共享模型准备、各问模型增量与求解、结果与分析、模型检验、优缺点、改进推广、结论、参考文献、附录。没有共享内核时省略相应章节。
5. 每问严格形成“任务与难点—输入/继承—模型增量与约束—求解及停止条件—精确结果与图形证据—检验、解释和声明边界”微闭环。模型原理只保留复现和理解所需部分，不能脱离本题堆砌。
6. 共享的坐标系、运动学、数据变换、指标体系或评价规则只定义一次；后续分问通过公式编号和符号引用，并说明新增变量、目标、约束和误差传播。
7. 摘要、标题和结论最后锁定；摘要不放公式、图表、身份信息或未经验证数字。
8. 附录先列支撑材料文件、运行入口、数据版本和配置，再放完整可运行源程序与必要长表；不得用代码截图代替可运行源码。
9. 交给 `mm-paper-reviewer` 审计数字、叙事、图表和引用，再调用 `mm-paper-compile` 进行 XeLaTeX/PDF 检查。

## CUMCM electronic profile

- PDF 第一页为标题、摘要、关键词专页；不含承诺书和编号专用页。
- 摘要专页原则上一页内，页脚中部阿拉伯数字从 1 开始。
- 摘要后换页，正文从第二页开始；不生成目录。
- 正文不超过 30 页，附录不计入正文页数。
- A4 纸张、四边至少 2.5 cm；内置字体和行距只是可读性默认值。
- 摘要、正文、附录、图表、代码、PDF 元数据和支撑材料均不得出现身份信息。
- 最终论文和支撑材料各自检查 20 MB 限制。

## Output rules

- 默认 `zh-CN`、LaTeX、XeLaTeX；英文或双语必须由用户明确要求。
- 公式、图表和章节由 LaTeX 自动编号；表格使用三线表。
- 图表优先包含 Origin/Visio 导出的 PDF；SVG 作为可编辑源保留，正文不默认要求 shell-escape。
- “预算内最优”“候选集最优”“局部最优”和“全局最优”必须区分。
- 未通过验证的结果不能进入摘要、结论或无条件声明。

## Quality checks

- 论文结构逐问覆盖原题，不遗漏依赖关系。
- `NARRATIVE_MAP.yaml` 与实际章节一致；共享内核没有重复推导，每问都有精确答案位置、验证和声明边界。
- 摘要、正文、结论、表格、图题和附件关键数字一致。
- 表格承担精确值，图形承担机制、趋势、权衡或稳健性；二者完全重复且没有独立读者任务时删去其一。
- 引用只来自已核验来源；无法核验时保留待补位置，不能虚构条目。
- 不出现姓名、学校、赛区、Logo、本机用户名或绝对路径。
- 需要编译时调用 `mm-paper-compile`，不把“生成 tex 文件”说成“格式已通过”。

## 本地优秀论文写作蒸馏

读取总控 [中文写作蒸馏](../math-modeling-orchestrator/references/local_corpus/cumcm_writing_patterns.md) 和 [国奖与优秀论文叙事—图表蒸馏](../math-modeling-orchestrator/references/local_corpus/award_paper_narrative_figure_distillation.md)。先锁定 `NARRATIVE_MAP`、Claims–Evidence Matrix、符号和图表角色，再写正文；摘要、结论最后锁定。不得复制本地论文文本、结果或图表，也不得把本地“优秀论文”标签写成当前方案质量认证。样本中出现的小图过密、默认彩虹色、软件截图、重复推导和装饰流程图属于反例，不得继承。
