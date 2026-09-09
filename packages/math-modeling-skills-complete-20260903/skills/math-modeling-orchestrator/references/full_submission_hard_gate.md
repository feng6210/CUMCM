# 参赛级完整交付硬门

当用户要求“参加比赛”“完整跑完”“最终论文”“可直接提交”“submission package”等交付时，必须使用 `deliverable_mode=submission_package`。该模式不是论文骨架模式，也不是分析模式。

## 0. 运行前环境门

在拆题前运行：

```powershell
python scripts/environment_preflight.py --profile submission_package --output ENVIRONMENT_PREFLIGHT.json
python scripts/workflow_state.py set-environment-preflight --state workflow_state.json --report-file ENVIRONMENT_PREFLIGHT.json
```

`ENVIRONMENT_PREFLIGHT.json` 必须 `status=PASS` 且 `full_submission_ready=true`。缺 Python 科学栈、确定性绘图依赖、XeLaTeX/latexmk/BibTeX 或 pdftoppm 时直接 `BLOCKED_CAPABILITY`，不得先跑半套流程再把 Markdown/骨架 PDF 当交付。

环境检查只读，不自动安装。需要安装时明确报告缺项，完成后重新 preflight。

## 1. 完整论文而不是模板骨架

`submission_package` 中不允许使用 `[待填写]`、`待补充`、`TODO`、`TBD`、`FIXME`、`PLACEHOLDER` 等作为最终交付内容。证据不足时回到求解/验证或报告阻塞；不得把模板占位符编译成 PDF 后声称完成。

每个题目分问必须在 `workflow_state.problem_parts` 中登记，并在 `FINAL_SUBMISSION_MANIFEST.json` 中逐一出现：

- `status=PASS`；
- 唯一 `paper_label`，最终 TeX 中必须恰好存在一次；
- 至少一个 hash-bound 结果工件；
- 至少一个 hash-bound 验证工件。

最终论文必须是真实已编译并审阅的 `paper/main.pdf`（或用户明确指定的正式文件名），不是 Markdown、提纲、骨架 PDF 或未审的 `.tex`。

## 2. 强制 fresh subagent 审查

`submission_package` 不接受作者自审、同一主 agent 换 reviewer_id、same-family cross-review 或“平台没有 subagent 就跳过”。必须调用至少五个**不同的 fresh subagent**，分别承担：

1. `semantics_math`：题意、目标函数、模型和约束；
2. `numerical_claims`：结果、单位、数值、声明边界；
3. `figure_visual`：图表、图注、可读性、实体/数值一致；
4. `paper_structure`：摘要、正文闭环、引用、叙事和 CUMCM 结构；
5. `final_submission`：最终 PDF 和支撑包的整体验收。

每次 subagent 调用必须保留实际 invocation receipt，并在 `SUBAGENT_REVIEW_MANIFEST.json` 中 hash 绑定。五个角色必须使用五个不同 `agent_id` 和五个不同 `invocation_id`，全部 `decision=PASS` 且无 unresolved blocking finding。

若运行平台没有 subagent 能力，`submission_package` 必须 `BLOCKED_CAPABILITY`；不得降级为主 agent 自查后继续 `COMPLETE`。

正式竞赛中，subagent 仍属于 AI 使用。`COMPETITION_POLICY.yaml` 未明确允许 AI/相应范围时先阻塞，不得借本硬门绕过赛事规则。

## 3. 最终 PDF 审查链

先完成一次真实编译，再冻结并审阅同一个 PDF：

```text
compile_paper.py
→ visual_review_gate.py prepare
→ fresh subagent / 人工实际查看全部页面
→ visual_review_gate.py verify
```

不得在审图后再次 XeLaTeX 重编译来“验证”旧视觉报告。源码、PDF 或 compile report 变化后旧视觉审查失效。

## 4. 最终提交门

在进入 `COMPLETE` 前运行：

```powershell
python ../mm-paper-compile/scripts/final_submission_gate.py \
  --paper-dir paper \
  --workflow-state workflow_state.json \
  --submission-manifest FINAL_SUBMISSION_MANIFEST.json \
  --subagent-manifest SUBAGENT_REVIEW_MANIFEST.json \
  --compile-report paper/compile_report.json \
  --visual-verification-report paper/visual_verification_report.json \
  --support-zip submission/support.zip \
  --output FINAL_SUBMISSION_GATE.json

python scripts/workflow_state.py set-subagent-review --state workflow_state.json --manifest-file SUBAGENT_REVIEW_MANIFEST.json
python scripts/workflow_state.py set-final-submission --state workflow_state.json --report-file FINAL_SUBMISSION_GATE.json
```

`FINAL_SUBMISSION_GATE.json` 必须 `status=PASS` 且 `competition_ready=true`。该 gate 会重新核对：

- `submission_package` 工作流且证据状态为 PASS；
- 所有分问均有结果与验证证据；
- TeX 和实际 PDF 中占位符为零；
- PDF 与 compile report、无二次编译视觉报告 hash 一致；
- 支撑 ZIP 存在、非空、可重开且 hash 一致；
- 五个 fresh subagent 审查均真实绑定当前工件。

## 5. COMPLETE 的唯一语义

`submission_package` 下 `COMPLETE` 只表示：**当前这组文件已经通过参赛级完整交付硬门，可以作为提交候选包交给用户做最后人工确认**。

以下任一情况都禁止 `COMPLETE`：

- 只生成提纲、Markdown、论文骨架或带占位符 PDF；
- 某一问没有结果/验证证据；
- `evidence_status` 不是 PASS；
- `result_to_claim_status` 不是 YES；
- 最终 PDF 未编译或未全页审查；
- subagent 不可用、数量不足、角色重复或存在 P0/P1 blocking finding；
- 最终支撑包缺失或 gate 失败。

此模式不保证获奖，也不把启发式结果升级为全局最优；它只禁止把明显未完成的工件冒充“最终参赛论文”。
