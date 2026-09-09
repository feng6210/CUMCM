# CUMCM 正式参赛交付硬契约

## 适用范围

当 `deliverable_mode` 为 `cumcm_latex_paper` 或 `submission_package`，或者用户明确表示“最终文件要参加比赛/正式提交/可直接交付”时，进入 **FULL_SUBMISSION** 模式。本模式禁止把论文骨架、占位模板、只编译成功的 PDF、作者自查稿或缺支撑材料的半成品标记为完成。

## 唯一允许的终态

FULL_SUBMISSION 的最终状态只有两类：

- `COMPLETE`：完整参赛论文与支撑材料全部通过硬门；
- `BLOCKED_INPUT / BLOCKED_CAPABILITY / PARTIAL / FAIL`：任何关键输入、求解、后端、审查或交付证据未满足时必须如实停在非完成状态。

不得为了“给用户一个文件”把不完整 PDF 降格包装成最终论文。

## 强制 Subagent 审查

正式交付前必须调用 fresh subagent，且至少形成四条互相独立的审查记录：

1. `semantics_math`：题意语义、目标函数、约束、模型推导和分问闭合；
2. `numbers_claims`：关键数字、表格、摘要、结论、验证与声明边界；
3. `figures_evidence`：图表是否真实生成、与数据/公式一致、机制表达和最终尺寸；
4. `paper_delivery`：论文结构、占位符、匿名性、PDF、支撑材料、最终提交完整性。

四条记录必须来自四个不同 `reviewer_id`，`origin=subagent`，且 `independent_of_authorship=true`。论文作者/主求解 agent 不能兼任这些最终审查角色。若当前平台没有 subagent 能力，FULL_SUBMISSION 必须进入 `BLOCKED_CAPABILITY`；不允许退化成作者自查后仍宣称可交付。

Subagent 不接收“预期 PASS”或拟议结论，只接收当前工件、原始证据和审查维度。P0/P1 修复后对应审查必须重跑，旧审查不得直接沿用。

## 禁止交付论文骨架

最终论文源和 PDF 中不得出现任何未完成标记，包括但不限于：

- `待填写`、`待补`；
- `TODO / TBD / FIXME / PLACEHOLDER`；
- 模板默认符号表、默认章节占位句；
- “后续补图/后续补代码/待验证”等未关闭内容。

发现任意占位内容，`FINAL_CHECK` 直接 FAIL。

## 每个分问必须闭合

每个题目分问必须至少形成以下闭环：

`任务与数学对象 → 模型/约束 → 求解或计算 → 关键结果 → 验证/边界 → 本问结论`

题面要求时程、曲线、表格、策略、参数或附件时，必须真实产出对应工件，不能用“程序可输出”或“建议绘制”代替。

## 最终交付工件

至少必须存在并保持一致：

- `paper/main.tex` 及实际使用的章节/表格/图形源码；
- 最终发布 PDF；
- `compile_report.json`，绑定实际发布 PDF；
- `visual_verification_report.json`，对同一 PDF 为 `PASSED`；
- `SUBAGENT_REVIEW_SUMMARY.json`，四条独立 subagent 审查全部通过，`unresolved_p0_p1=[]`；
- 支撑材料 ZIP，能够重新打开且非空；
- 源程序、数据/结果表、图形与配置文件清单不含占位内容。

对于 FULL_SUBMISSION，执行：

```powershell
python skills/mm-paper-compile/scripts/final_delivery_check.py `
  --paper-dir paper `
  --support-zip support.zip `
  --competition-ready
```

只有返回码 0 且 `FINAL_CHECK.json.status=PASS`，才允许对用户使用“最终参赛文件/可交付论文/COMPLETE”等表述。

## 与环境的关系

FULL_SUBMISSION 启动前必须先做 task-aware 环境预检。缺少 XeLaTeX、latexmk、BibTeX、PDF 页面渲染/审查能力，或缺少 subagent 能力时，应在开始大规模求解前报告并进入 `BLOCKED_CAPABILITY`，而不是最后输出半成品。

## 不可降级原则

- 编译成功 ≠ 论文完成；
- 结构完整 ≠ 数学正确；
- 作者自查 ≠ subagent 审查；
- PDF 存在 ≠ 可参赛；
- schema/CI PASS ≠ 竞赛质量 PASS。

正式交付必须同时满足数学证据、论文内容、图表、编译、视觉审查、subagent 审查和支撑材料硬门。
