---
name: mm-paper-structure-writer
description: Create evidence-grounded Chinese CUMCM mathematical-modeling paper outlines and complete LaTeX drafts, with a compact competition narrative by default and an optional research-audit profile. Use after results and semantic scope are verified. Do not fabricate evidence, leak internal audit machinery into the competition body without reader value, write a final paper for an active contest when rules do not allow it, or hand off a template skeleton as a competition submission.
---

# 数学建模：CUMCM 中文 LaTeX 论文结构与初稿

## Purpose

默认生成中文、CUMCM 电子版格式、XeLaTeX 的数学建模论文。论文不是研究软件审计报告：默认围绕赛题分问、共享数学内核、逐问模型增量、关键结果和必要验证组织。

默认模板在 [assets/cumcm-2026](assets/cumcm-2026)。它是依据 CUMCM 2026 格式要求实现的内置模板，不是组委会官方模板；用户提供正式 `.cls`、`.sty` 或 `.tex` 模板时，用户模板优先。

## Reporting profiles

### `competition_compact`（默认 CUMCM）

正文目标是让评委快速理解：

```text
题目要求 → 数学对象/机制 → 本问模型增量 → 求解策略 → 关键结果 → 必要检验
```

以下内容默认不进入正文，除非它们直接改变结论：完整 gate 名、hash、backend report、旧版本 FAIL 谱系、全部随机种子、微小步长差、软件运行日志。它们放入附录/支撑材料。关键敏感性矩阵若直接解释设计风险可留正文，不因“验证图”类别自动迁移。

### `research_audit`

面向科研复现或工程审计，可展开版本谱系、失败证据、工件哈希、完整验证链和后端报告。

两种 profile 共用同一结果和验证状态；`competition_compact` 只压缩表达，不得把 FAIL 隐藏成 PASS。

## Modes

1. **结构模式**：输出 `PAPER_PLAN.md`、`NARRATIVE_MAP.yaml`、`FIGURE_PLAN.yaml`、分问—章节映射、证据缺口和 LaTeX 章节骨架。只适用于用户明确要提纲/规划，或普通非最终任务暂时缺证据时。
2. **完整 LaTeX 模式**：用户明确需要完整论文、最终论文、参赛文件或 `workflow_state.deliverable_mode=submission_package` 时使用。复制模板到任务 `paper/` 目录并完整填写 `main.tex`、`sections/*.tex`、表格、图形、参考文献和附录。

`submission_package` **不得降级为结构模式后结束**。若关键结果、引用、图形或验证证据不足，返回相应求解/验证/绘图阶段或 `BLOCKED_INPUT/BLOCKED_CAPABILITY`；不得用 `待填写、待补、TODO、TBD、FIXME、PLACEHOLDER` 等内容填满模板后编译成 PDF。内部骨架可以存在，但不能命名、报告或交付为最终参赛论文。

## Required workflow

已有论文修订或根据优秀论文改进表达时，先读 [读者任务、版式与修订闭环](references/paper_readability_and_revision.md)。区分用户要求修改的是论文还是 Skill；字体与强调规则是可调整默认值，不覆盖用户正式模板。若为 `submission_package`，同时读取总控 [参赛级完整交付硬门](../math-modeling-orchestrator/references/full_submission_hard_gate.md)。

1. 读取题目、`PROBLEM_SEMANTICS.yaml`、完整分问清单、假设、结果、`RESULTS_TO_CLAIMS.md` 与 `result_evidence_map.json`。任何主目标或计时/资源口径在写作阶段发生变化，都必须回到语义/求解阶段，不能靠措辞修复。
2. 读取总控的 [国奖与优秀论文叙事—图表蒸馏](../math-modeling-orchestrator/references/local_corpus/award_paper_narrative_figure_distillation.md)。先建立 `NARRATIVE_MAP.yaml`：论文总矛盾、分问依赖图、共享模型内核、每问继承对象与模型增量、精确结果位置、关键检验、声明边界和问间交接。
3. 与叙事同步建立 `FIGURE_PLAN.yaml`，而不是最后才补图。逐段检查读者障碍：场景、几何/受力、case、状态、协同、时间区间、空间结果、响应面或关键验证；选择 `figure/table/text/appendix/not_applicable`。不设置每问固定图数。
4. 建立中文 `PAPER_PLAN.md`：论文主线、分问和章节对应、Claims–Evidence Matrix、公式计划、图表任务与版面预算、摘要事实表、正文页数预算、附录和证据缺口。`submission_package` 中发现的缺口是返工清单，不允许原样留在最终论文。
5. 按 CUMCM 结构写作：摘要专页、问题重述、问题分析、模型假设、符号说明、数据处理/共享模型准备、各问模型增量与求解、结果与分析、模型检验、优缺点、改进推广、结论、参考文献、附录。没有共享内核时省略相应章节；不得保留模板自带的“待填写”行。
6. 每问形成“任务与难点—输入/继承—模型增量与约束—求解及停止条件—精确结果—必要图形/表格证据—检验、解释和声明边界”微闭环。`submission_package` 为每个分问添加唯一 LaTeX `\label{...}`，供 `FINAL_SUBMISSION_MANIFEST.json` 绑定该问结果与验证证据。
7. 共享的坐标系、运动学、数据变换、几何判据、指标体系或评价规则只定义一次；后续分问只写新增变量、目标、约束、求解变化和误差传播。
8. **模型解释优先于审计展示。** 对复杂物理/几何判据，如果公式对首次阅读者不透明，正文优先安排二维机制图、case 图、投影或时间轴。多种子、M1/M2 微小差异、重力 10 ms 等验证只有在它们改变主结论时才占正文图位。
9. 复杂优化算法只解释本题真正使用的结构：为什么基线不够、如何分解、决策变量如何编码、停止条件是什么。不要把算法名称串成创新清单，也不要把每次恢复/版本修复写成正文主线。
10. `competition_compact` 中，内部名称如 `G4/G5/PASS_RESTRICTED/incumbent/hash/manifest/backend_report` 改写为读者可理解的数学含义：例如“多初值稳定性检验”“有限候选库最优”“连续复算未发现进一步提升”；原始技术名保留在支撑材料。
11. 摘要、标题和结论最后锁定；摘要按分问回答“做了什么—怎么算—得到什么—怎样验证”，不放公式、图表、身份信息或工程审计术语。最终结论必须逐问闭合，不能留下待写段落。
12. 附录先列**真实存在**的支撑材料文件、运行入口、数据版本和配置，再放完整可运行源程序与必要长表；不得用代码截图代替可运行源码。`submission_package` 中清单条目必须对应实际文件，不能写占位文件名。
13. 交给 `mm-visualization-delivery` 按已批准 `FIGURE_PLAN` 渲染，不允许渲染阶段为“图量完整”新增图。`submission_package` 中所有正文必需图必须有真实输出并被当前 TeX 引用，不能停在“建议绘制”。
14. 交给 `mm-paper-reviewer` 审计题意语义、数字、叙事、图表和引用，再调用 `mm-paper-compile` 进行 XeLaTeX/PDF 检查。`submission_package` 的最终决定权属于总控的五路 fresh subagent + `final_submission_gate.py`；本 Skill 不自行宣布 `COMPLETE`。

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
- 图表优先 PDF；可编辑源另存，不在正文展示软件界面。
- “预算内最优”“候选集最优”“局部最优”“未被当前挑战击穿”和“全局最优”必须区分。
- 未通过验证的结果不能进入摘要、结论或无条件声明。
- 不把内部验证术语当成论文创新点；创新要落到数学机制、目标/约束、表示、推断或求解结构。
- `submission_package` 的输出目标是当前完整 LaTeX 源、实际最终 PDF 和可追溯支撑材料，不是 Markdown 摘要、提纲、骨架或编译测试样张。

## Quality checks

- `PROBLEM_SEMANTICS.yaml` 与正文目标函数/判据一致；P5 类“总和 vs 同时覆盖”“一资源一目标 vs 可复用”等语义不能在写作时漂移。
- `NARRATIVE_MAP.yaml` 与实际章节一致；共享内核没有重复推导，每问都有精确答案位置、必要验证和声明边界。
- `FIGURE_PLAN.yaml` 与正文同步；复杂几何/机理没有被收敛图和审计图挤掉。
- 不设固定图数；图只承担机制、趋势、空间、区间、权衡或关键验证。简单数值答案可只用表格。
- 摘要、正文、结论、表格、图题和附件关键数字一致。
- 引用只来自已核验来源。一般草稿无法核验时可以记录缺口；`submission_package` 必须在最终交付前解决、删除无依据引用或阻塞，不能保留“待补引用”占位。
- 不出现姓名、学校、赛区、Logo、本机用户名或绝对路径。
- `competition_compact` 中若正文出现大量 hash、gate、版本 FAIL、runtime report 或固定种子表，必须证明其不可替代读者价值，否则移附录。
- 需要编译时调用 `mm-paper-compile`，不把“生成 tex 文件”或“能编译”说成“参赛论文已完成”。
- `submission_package` 最终源文件和 PDF 中占位符必须为零；任一分问没有结果/验证证据、任一必要图未生成、最终 PDF 未实际审阅时均不能通过交付。

## 本地优秀论文写作蒸馏

读取总控 [中文写作蒸馏](../math-modeling-orchestrator/references/local_corpus/cumcm_writing_patterns.md) 和 [国奖与优秀论文叙事—图表蒸馏](../math-modeling-orchestrator/references/local_corpus/award_paper_narrative_figure_distillation.md)。吸收的是“问题→数学结构→模型→结果”的叙事与机制图作用，不复制样本文本、结果或图形。样本中出现的小图过密、默认彩虹色、软件截图、重复推导和装饰流程图仍作为反例。
