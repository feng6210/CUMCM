# CUMCM 严格提交审计契约

## 适用范围

本文件对应 `strict_submission_audit`，即 provenance-bound 的 competition-ready 严格终审。

只有以下情况进入本模式：

- 用户明确要求 `competition-ready`、严格终审、provenance-bound 审计或等价要求；
- 团队把本仓库当作正式提交前的强审计流水线，并主动选择该门；
- 需要验证最终 PDF、支撑材料、视觉检查和多个独立 reviewer 的一致性绑定。

**不要仅因为用户要求“完整论文”“最终 PDF”“正式排版”就自动触发本模式。** 普通完整论文由总控的 `formal_delivery` 处理：内容完整、结果真实、编译成功、视觉检查通过即可；本文件是在此基础上的额外严格审计层。

## 严格模式的终态

启用 `strict_submission_audit` 后，最终状态只有：

- `COMPLETE`：当前提交工件通过严格门；
- `BLOCKED_INPUT / BLOCKED_CAPABILITY / PARTIAL / FAIL`：任一关键证据不足时保持非完成状态。

不能把论文骨架、带占位符的 PDF、作者自查稿或缺少支撑材料的半成品包装成严格审计通过。

## 四路 fresh-subagent 审查

`--competition-ready` 当前实现要求四条独立审查：

1. `semantics_math`：题意、目标函数、约束、推导和分问闭合；
2. `numbers_claims`：关键数字、表格、摘要、结论、验证和声明边界；
3. `figures_evidence`：图表是否来自真实数据/公式、机制表达与最终尺寸；
4. `paper_delivery`：结构、占位符、匿名性、PDF、支撑材料和提交完整性。

四条记录必须来自不同 fresh subagent，且作者/主求解 agent 不能兼任。平台没有 subagent 能力时，只能说明严格审计不可执行；这不妨碍输出一个经过常规 `formal_delivery` 检查的完整论文，但不得把它称为 `strict_submission_audit PASS`。

每份 review 至少记录：

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

`SUBAGENT_REVIEW_SUMMARY.json` 必须绑定当前 submission digest、四份 review 的路径和 SHA-256，并保持 `unresolved_p0_p1=[]`。论文/PDF/支撑材料变化导致 submission digest 变化时，受影响的严格审查证据必须重建。

## 禁止占位交付

严格提交的论文源和支撑材料不得包含：

- `待填写`、`待补`、`待验证`、`待确认`；
- `TODO / TBD / FIXME / PLACEHOLDER`；
- 模板默认符号表、默认章节占位句；
- “后续补图/后续补代码/后续完善”等未关闭内容。

`paper/main.tex` 必须真实存在，每个题目分问应闭合：

`任务与数学对象 → 模型/约束 → 求解或计算 → 关键结果 → 验证/边界 → 本问结论`

题面要求时程、曲线、表格、策略、参数或附件时，必须真实产出对应工件。

## 视觉复核

严格审计使用：

```text
visual_review_gate.py prepare
→ 实际查看全部最终 PDF 页面
→ visual_review_gate.py verify
```

必须绑定同一已发布 PDF、当前 `compile_report.json` 和论文源快照。不能手写一个 `PASSED` JSON 代替真实 gate，也不能在审图之后重新编译却继续复用旧视觉报告。

## 支撑材料检查

支撑材料 ZIP 必须：

- 可重新打开且满足赛事大小限制；
- 含非空、实质性的源程序/脚本，而不是空目录或纯占位文件；
- 文本源码、结果、配置和清单可完整检查；
- 不含姓名、学号等身份泄露；
- 不含占位符；
- 对 UTF-8、UTF-8 BOM 和带 BOM 的 UTF-16 按实际编码检查，不能用替换字符掩盖关键字。

## 严格模式最终工件

至少存在并相互一致：

- `paper/main.tex` 及实际使用的章节、图表和参考文献；
- 最终 PDF；
- `compile_report.json`；
- `VISUAL_REVIEW_BINDING.json`；
- `visual_verification_report.json`；
- 四份 fresh-subagent review；
- `SUBAGENT_REVIEW_SUMMARY.json`；
- 支撑材料 ZIP。

执行：

```powershell
python skills/mm-paper-compile/scripts/final_delivery_check.py `
  --paper-dir paper `
  --support-zip support.zip `
  --competition-ready `
  --output FINAL_CHECK.json
```

`FINAL_CHECK.json` 应位于 `paper/` 之外。只有返回码 0 且 `status=PASS` 时，才可进一步把严格审计状态记为完成。

如果使用 `workflow_state.py`，再执行：

```powershell
python skills/math-modeling-orchestrator/scripts/workflow_state.py `
  record-final-delivery `
  --state workflow_state.json `
  --final-check FINAL_CHECK.json
```

## 与普通 formal_delivery 的区别

`formal_delivery` 要求的是：论文内容完整、数字可信、无占位、编译成功、视觉可读、支撑材料按需要生成。

`strict_submission_audit` 额外要求：四路 fresh-subagent、submission digest、review provenance、hash binding 和 `--competition-ready` 硬门。

因此：

- 编译成功 ≠ 数学正确；
- 完整论文 ≠ strict audit PASS；
- 作者自查可以用于普通论文质量控制，但不能替代 strict audit 的四路 fresh-subagent；
- schema/CI PASS 只能证明相应机器检查，不代表获奖水平。
