# 正式竞赛工具与外部资料权限协议

## 目的

把“训练时可以做的外部 benchmark / 联网检索”和“正式竞赛时允许做的事情”分开。`task_mode=live_contest` 时，任何联网、AI、外部论文、公开答案/优秀论文参数、协作工具或自动化动作，都先由 `COMPETITION_POLICY.yaml` 决定。

本协议不替用户解释赛事规则。若官方规则未知或互相冲突，状态应为 `BLOCKED_INPUT` 或保守禁用相关外部能力，而不是自行推定允许。用户指令可以收紧操作范围，但**不能替代或放宽正式赛事/课程规则**。

## 必须产物：`COMPETITION_POLICY.yaml`

建议从 `assets/COMPETITION_POLICY.template.yaml` 复制并填写，随后用：

```powershell
python scripts/validate_contract.py --schema ../../schemas/competition_policy.schema.json --input COMPETITION_POLICY.yaml
```

至少记录：

- `competition_name`
- `stage`
- `ai_allowed`
- `web_allowed`
- `external_papers_allowed`
- `benchmark_answers_allowed`
- `team_collaboration_scope`
- `citation_requirement`
- `source.kind / source.reference`
- `unresolved`

## live contest 的 fail-closed 规则

1. `ai_allowed / web_allowed / external_papers_allowed / benchmark_answers_allowed` 任一为 `unknown`，不得开始对应能力调用。
2. live contest 的 `source.kind` 必须是 `official_rules` 或 `course_policy`。`user_instruction` 只可用于 training/research 或用于额外收紧限制，不能作为正式竞赛“允许使用”的依据。
3. `benchmark_answers_allowed != allowed` 时，不主动搜索或导入公开答案、优秀论文参数、外部候选解；`BENCHMARK_CHALLENGE.json` 记录 `NOT_ALLOWED_BY_RULES` 并绑定 policy。
4. `external_papers_allowed=restricted` 时，只在规则允许范围内使用背景文献，不把外部论文答案当本题候选解。
5. `web_allowed=forbidden` 时，本地随包知识、用户提供文件和当前题目附件仍可用，但不能联网补数据/查答案；若赛事规则对用户提供材料本身另有限制，仍按赛事规则执行。
6. policy 文件与 SHA-256 绑定到 `workflow_state.json`。文件被修改、移动或删除后，敏感状态跳转必须失败，直至重新校验并绑定。
7. 规则变化时更新 policy、来源和时间；会改变已使用证据合法性的变化使相关结果/论文声明 stale。

## training / coursework / research

训练和科研可以更积极地做外部挑战，但仍需明确来源与可比口径。外部方案必须进入自己的正式 evaluator；原文报告数字不能代替重算。

## 论文表达

`competition_compact` 正文通常不展开内部 policy 字段，但所有外部数据、文献和工具使用必须按赛事要求引用/披露。policy 属于运行证据，不是数学创新点。
