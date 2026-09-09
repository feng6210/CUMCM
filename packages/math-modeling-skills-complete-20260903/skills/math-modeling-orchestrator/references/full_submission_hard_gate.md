# 参赛级完整交付硬门

当用户要求“参加比赛”“完整跑完”“最终论文”“可直接提交”“submission package”等交付时，必须使用 `deliverable_mode=submission_package`。该模式不是论文骨架模式，也不是分析模式。

## 0. 运行前环境门

先创建 submission 状态，再在拆题前运行环境预检：

```powershell
python scripts/workflow_state.py init --state workflow_state.json --task-id TASK --task-mode training --deliverable-mode submission_package
python scripts/environment_preflight.py --profile submission_package --output ENVIRONMENT_PREFLIGHT.json
python scripts/workflow_state.py set-environment-preflight --state workflow_state.json --report-file ENVIRONMENT_PREFLIGHT.json
python scripts/workflow_state.py transition --state workflow_state.json --to INPUT_REGISTERED
```

`ENVIRONMENT_PREFLIGHT.json` 必须 `status=PASS` 且 `full_submission_ready=true`。`workflow_state.py` 在绑定报告和关键状态转换时还会重新探测**当前主机**，所以手写一个假的 PASS JSON 不能替代真实环境。submission preflight 除了检查 Python ≥3.10、科学计算/绘图包的最低版本和 CJK 字体，还实际在临时目录编译一份 `ctex + TikZ` 中文 XeLaTeX fixture，并用 `pdftoppm` 重开第一页。缺少任一必需能力直接 `BLOCKED_CAPABILITY`，不得先跑半套流程再把 Markdown/骨架 PDF 当交付。

环境检查不安装软件、不改变主机配置。需要安装时明确报告缺项，完成后重新 preflight。

## 1. 完整论文而不是模板骨架

`submission_package` 中不允许使用 `[待填写]`、`待补充`、`TODO`、`TBD`、`FIXME`、`PLACEHOLDER` 等作为最终交付内容。证据不足时回到求解/验证或报告阻塞；不得把模板占位符编译成 PDF 后声称完成。

拆题产物 `QUESTION_DECOMPOSITION.json` 必须包含完整 `expected_question_ids`。`FINAL_SUBMISSION_MANIFEST.json` 对该文件做 SHA-256 绑定；最终 gate 同时比较：

1. `QUESTION_DECOMPOSITION.expected_question_ids`；
2. `workflow_state.problem_parts`；
3. `FINAL_SUBMISSION_MANIFEST.question_completion`。

三者必须覆盖同一完整分问集合，不能通过把 `workflow_state.problem_parts` 偷改成只剩 Q1 来隐藏未完成分问。

每个题目分问必须逐一满足：

- `status=PASS`；
- 唯一 `paper_label`，最终 TeX 中必须恰好存在一次；
- 至少一个 hash-bound 结果工件；
- 至少一个 hash-bound 验证工件。

最终论文必须是真实已编译并审阅的 `paper/main.pdf`（或用户明确指定的正式文件名），不是 Markdown、提纲、骨架 PDF 或未审的 `.tex`。最终交付至少包含当前最终 PDF 与支撑 ZIP；内部计划、审计 JSON 可以保留为支撑证据，但不能取代论文。

## 2. 强制 fresh subagent 审查

`submission_package` 不接受作者自审、同一主 agent 换 reviewer_id、same-family cross-review 或“平台没有 subagent 就跳过”。必须调用至少五个**不同的 fresh subagent**，分别承担：

1. `semantics_math`：题意、目标函数、模型和约束；
2. `numerical_claims`：结果、单位、数值、声明边界；
3. `figure_visual`：图表、图注、可读性、实体/数值一致；
4. `paper_structure`：摘要、正文闭环、引用、叙事和 CUMCM 结构；
5. `final_submission`：最终 PDF 和支撑包的整体验收。

每个角色不能只“看过一个文件”就算完成。`SUBAGENT_REVIEW_MANIFEST.json` 对下面这些实际工件做类型化 hash 绑定：

| subagent 角色 | 最少必须审阅的当前工件 |
|---|---|
| `semantics_math` | `QUESTION_DECOMPOSITION`、`PROBLEM_SEMANTICS`、最终 PDF |
| `numerical_claims` | 最终 PDF、`result_evidence_map` |
| `figure_visual` | 最终 PDF、`FIGURE_PLAN`、最终 visual verification |
| `paper_structure` | 最终 PDF、当前论文源文件 |
| `final_submission` | 最终 PDF、支撑 ZIP、`FINAL_SUBMISSION_MANIFEST`、compile report、visual verification |

每次 subagent 调用必须保留实际 invocation receipt，并在 manifest 中 hash 绑定。五个角色必须使用五个不同 `agent_id` 和五个不同 `invocation_id`，全部 `decision=PASS` 且无 unresolved blocking finding。receipt 必须声明 `receipt_kind=runtime_subagent_invocation`，并与本次 `task_id`、`review_batch_id`、角色、agent/invocation 身份、fresh_context、PASS decision、所审工件的规范化摘要以及带时区的开始/结束时间一致。

不得为了过 gate 伪造 receipt。静态仓库本身不能凭空生成可信的运行时调用证明；运行平台必须提供实际 subagent 调用并保存其回执。若平台能提供原生或签名调用记录，优先把该记录作为 receipt 来源。没有实际 subagent 能力或拿不到可绑定的真实调用记录时，`submission_package` 必须 `BLOCKED_CAPABILITY`，不得降级为主 agent 自查后继续 `COMPLETE`。

正式竞赛中，subagent 仍属于 AI 使用。`COMPETITION_POLICY.yaml` 未明确允许 AI/相应范围时先阻塞，不得借本硬门绕过赛事规则。

## 3. 最终 PDF 审查链

先完成一次真实编译，再冻结并审阅同一个 PDF：

```text
compile_paper.py
→ visual_review_gate.py prepare
→ fresh subagent / 人工实际查看全部页面
→ visual_review_gate.py verify
```

不得在审图后再次 XeLaTeX 重编译来“验证”旧视觉报告。源码、PDF 或 compile report 变化后旧视觉审查失效。最终 visual verification 还必须 hash 绑定当前 `compile_report.json`，不能拿另一轮编译的视觉报告混用。

## 4. 最终提交门

五路 subagent 全部完成后，先把其 manifest 绑定进状态机，再运行最终 gate：

```powershell
python scripts/workflow_state.py set-subagent-review --state workflow_state.json --manifest-file SUBAGENT_REVIEW_MANIFEST.json

python ../mm-paper-compile/scripts/final_submission_gate.py \
  --paper-dir paper \
  --workflow-state workflow_state.json \
  --submission-manifest FINAL_SUBMISSION_MANIFEST.json \
  --subagent-manifest SUBAGENT_REVIEW_MANIFEST.json \
  --compile-report paper/compile_report.json \
  --visual-verification-report paper/visual_verification_report.json \
  --support-zip submission/support.zip \
  --output FINAL_SUBMISSION_GATE.json

python scripts/workflow_state.py set-final-submission --state workflow_state.json --report-file FINAL_SUBMISSION_GATE.json
python scripts/workflow_state.py transition --state workflow_state.json --to COMPLETE
```

`FINAL_SUBMISSION_GATE.json` 必须 `status=PASS` 且 `competition_ready=true`。`set-final-submission` 和最终 `COMPLETE` 不只相信 JSON 上写了 PASS，而会重新调用当前 `final_submission_gate.py` 对绑定工件复算；因此手写一个 `{"status":"PASS"}` 不能绕过最终门。

最终 gate 会重新核对：

- 当前主机仍满足 submission preflight；
- `submission_package` 工作流且证据状态为 PASS、结果可进入声明；
- 权威 `QUESTION_DECOMPOSITION`、状态机与最终 manifest 的分问集合一致；
- 所有分问均有结果与验证证据以及唯一论文锚点；
- TeX/Bib 和实际 PDF 中占位符为零；
- PDF 与 compile report、无二次编译视觉报告 hash 一致；
- 支撑 ZIP 存在、非空、可重开且 hash 一致；
- 五个 fresh subagent 审查均绑定当前、角色匹配的工件；
- submission manifest、subagent manifest、compile report、visual verification、最终 PDF、支撑 ZIP 与拆题文件没有在 gate 后漂移。

## 5. COMPLETE 的唯一语义

`submission_package` 下 `COMPLETE` 只表示：**当前这组文件已经通过参赛级完整交付硬门，可以作为提交候选包交给用户做最后人工确认**。

以下任一情况都禁止 `COMPLETE`：

- 只生成提纲、Markdown、论文骨架或带占位符 PDF；
- 任一分问没有结果/验证证据或没有进入最终论文；
- `evidence_status` 不是 PASS；
- `result_to_claim_status` 不是 YES；
- 最终 PDF 未编译或未全页审查；
- subagent 不可用、数量不足、角色重复、回执无法绑定当前工件或存在 P0/P1 blocking finding；
- 最终支撑包缺失或 gate 失败；
- 任何已绑定的最终工件在 gate 后发生变化而未重新审查。

此模式不保证获奖，也不把启发式结果升级为全局最优；它只禁止把明显未完成的工件冒充“最终参赛论文”。
