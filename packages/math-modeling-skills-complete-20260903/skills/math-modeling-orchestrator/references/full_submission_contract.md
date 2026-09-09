# CUMCM 正式参赛交付硬契约

## 适用范围

当 `deliverable_mode` 为 `cumcm_latex_paper` 或 `submission_package`，或者用户明确表示“最终文件要参加比赛/正式提交/可直接交付”时，进入 **FULL_SUBMISSION** 模式。本模式禁止把论文骨架、占位模板、只编译成功的 PDF、作者自查稿或缺支撑材料的半成品标记为完成。

## 唯一允许的终态

FULL_SUBMISSION 的最终状态只有两类：

- `COMPLETE`：完整参赛论文与支撑材料全部通过硬门；
- `BLOCKED_INPUT / BLOCKED_CAPABILITY / PARTIAL / FAIL`：任何关键输入、求解、后端、审查或交付证据未满足时必须如实停在非完成状态。

不得为了“给用户一个文件”把不完整 PDF 降格包装成最终论文。

## 强制 Subagent 审查

正式交付前必须实际调用 fresh subagent，并形成四条互相独立的审查记录：

1. `semantics_math`：题意语义、目标函数、约束、模型推导和分问闭合；
2. `numbers_claims`：关键数字、表格、摘要、结论、验证与声明边界；
3. `figures_evidence`：图表是否真实生成、与数据/公式一致、机制表达和最终尺寸；
4. `paper_delivery`：论文结构、占位符、匿名性、PDF、支撑材料、最终提交完整性。

四条记录必须来自四个不同的 fresh subagent。`reviewer_id` 与 `invocation.run_id` 去首尾空格并大小写归一后都必须各自保持四个唯一值；作者/主求解 agent 不能兼任。若当前平台没有 subagent 能力，FULL_SUBMISSION 必须进入 `BLOCKED_CAPABILITY`；不允许退化成作者自查后仍宣称可交付。

每个 subagent 必须输出单独 JSON review artifact，至少记录：

```json
{
  "status": "PASSED",
  "dimension": "semantics_math",
  "reviewer_id": "fresh-subagent-id",
  "origin": "subagent",
  "independent_of_authorship": true,
  "submission_digest": "current-submission-digest",
  "invocation": {
    "kind": "subagent",
    "run_id": "actual-run-id",
    "fresh_context": true
  },
  "blocking_findings": []
}
```

`SUBAGENT_REVIEW_SUMMARY.json` 必须记录非空 `author_agent_id`、当前 `submission_digest`，以及四份 review artifact 的路径和 SHA-256。最终 gate 会重新打开这些 review 文件、校验哈希、reviewer/dimension、四个不同 fresh invocation、当前 submission digest 和 P0/P1 状态；不能只写四行自报 PASS。

Subagent 不接收“预期 PASS”或拟议结论，只接收当前工件、原始证据和审查维度。P0/P1 修复、论文/PDF/支撑材料变化后 submission digest 会变化，四份审查必须重跑，旧 summary 不得复用。

## 禁止交付论文骨架

最终论文源和支撑材料中不得出现任何未完成标记，包括但不限于：

- `待填写`、`待补`、`待验证`、`待确认`；
- `TODO / TBD / FIXME / PLACEHOLDER`；
- 模板默认符号表、默认章节占位句；
- “后续补图/后续补代码/后续完善”等未关闭内容。

`paper/main.tex` 必须真实存在。正式 gate 会扫描论文目录中的文本型源码/配置/结果文件，并扫描支撑 ZIP 内可读文本成员；发现任意未完成标记直接 FAIL。

## 每个分问必须闭合

每个题目分问必须至少形成以下闭环：

`任务与数学对象 → 模型/约束 → 求解或计算 → 关键结果 → 验证/边界 → 本问结论`

题面要求时程、曲线、表格、策略、参数或附件时，必须真实产出对应工件，不能用“程序可输出”或“建议绘制”代替。

## 视觉复核不得自报 PASS

FULL_SUBMISSION 必须采用 `visual_review_gate.py prepare → 实际打开全部 PDF 页面 → visual_review_gate.py verify`。最终交付检查不仅看 `visual_verification_report.json.status=PASSED`，还重新校验：

- `verification_mode=existing_published_artifact_no_recompile`；
- `VISUAL_REVIEW_BINDING.json`；
- 当前 `compile_report.json` 与 PDF 哈希；
- 当前 source snapshot；
- hash-bound visual report 是否仍满足全页 `PASSED` 语义；
- visual report 与 verification report 是否真实登记在 binding 的 review provenance 中。

手工写一个 `{"status":"PASSED"}`、只改 PDF 哈希，或把失败/不完整 visual report 重新哈希，都不能通过正式交付门。

## 支撑材料硬门

支撑材料 ZIP 必须：

- 文件存在、可重新打开、20 MB 限制内；
- 至少包含一个非目录、非零字节的有效成员；
- 至少包含一份真实源程序/脚本，而不是只有空目录或零字节占位文件；
- 文本型源程序、结果、配置和清单不含未完成标记。

## 最终交付工件

至少必须存在并保持一致：

- `paper/main.tex` 及实际使用的章节/表格/图形源码；
- 最终发布 PDF；
- `compile_report.json`，绑定实际发布 PDF；
- `VISUAL_REVIEW_BINDING.json`；
- `visual_verification_report.json`，由 no-recompile visual gate 对同一 PDF 验证通过；
- 四份 fresh subagent review artifact；
- `SUBAGENT_REVIEW_SUMMARY.json`，四条独立 subagent 审查全部通过，`unresolved_p0_p1=[]`；
- 支撑材料 ZIP，满足上述有效载荷和源码要求。

对于 FULL_SUBMISSION，执行：

```powershell
python skills/mm-paper-compile/scripts/final_delivery_check.py `
  --paper-dir paper `
  --support-zip support.zip `
  --competition-ready `
  --output FINAL_CHECK.json
```

`FINAL_CHECK.json` 应放在 `paper/` 目录之外，避免把终审报告误归类为论文源文件。只有返回码 0 且 `FINAL_CHECK.json.status=PASS` 后，才能运行：

```powershell
python skills/math-modeling-orchestrator/scripts/workflow_state.py `
  record-final-delivery `
  --state workflow_state.json `
  --final-check FINAL_CHECK.json
```

`record-final-delivery` 会重新运行 competition-ready gate；从 `REVIEWING → COMPLETE` 时还会再次重验当前 PDF、论文 source snapshot、visual provenance、support ZIP 和四份 subagent evidence。任何工件在 FINAL_CHECK 后变化，旧 gate 立即失效，必须重跑检查和受影响的 subagent 审查。

只有该状态门也通过，才允许对用户使用“最终参赛文件/可交付论文/COMPLETE”等表述。

## 与环境的关系

FULL_SUBMISSION 启动前必须先做 task-aware 环境预检。缺少 XeLaTeX、latexmk、BibTeX、PDF 页面渲染/审查能力，或缺少 subagent 能力时，应在开始大规模求解前报告并进入 `BLOCKED_CAPABILITY`，而不是最后输出半成品。

## 不可降级原则

- 编译成功 ≠ 论文完成；
- 结构完整 ≠ 数学正确；
- 作者自查 ≠ subagent 审查；
- PDF 存在 ≠ 可参赛；
- schema/CI PASS ≠ 竞赛质量 PASS。

正式交付必须同时满足数学证据、论文内容、图表、编译、视觉审查、subagent 审查和支撑材料硬门。
