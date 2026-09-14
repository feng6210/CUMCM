---
name: mm-contest-operations-planner
description: Plan mathematical-modeling contest preparation, problem selection, team roles, milestones, handoffs, fallback routes, and submission checks. Default to one compact operating plan; create machine-readable handoff artifacts only when the team actually uses them.
---

# 数学建模：竞赛运营与团队交接

## Purpose

把选题、团队分工、赛中节奏、分问交接和终稿检查组织成可执行计划。它不替代题意裁决、模型选择或求解，也不为了“流程完整”制造大量没人使用的 YAML/JSON。

## Default output

普通团队任务默认只生成一份 `CONTEST_PLAN.md`，包含：

- 选题依据；
- 三人或多人分工；
- 关键里程碑；
- 每问当前负责人、输入、输出和依赖；
- 主要风险与回退；
- 最终论文/代码/附件检查项。

只有当团队明确使用脚本、Agent 或 CI 消费机器文件时，再拆分为 `TEAM_ROLES.yaml`、`MILESTONE_PLAN.yaml`、`QUESTION_HANDOFF.yaml` 等结构化工件。

若确实启用结构化 `QUESTION_HANDOFF.yaml`，继续遵守现有跨 Skill 合同，至少保留后续机器真正需要的归一化字段：`problem_semantics_ref`、`baseline`、`benchmark_challenge`、`figure_intents`，以及模型/代码入口、机器可读结果、验证状态和未解决风险。这里保留字段兼容性，不代表普通团队任务必须生成该文件。

## Workflow

1. 明确比赛阶段和允许使用的工具。只有 `live_contest` 且 AI、联网、外部论文或公开答案权限会影响当前动作时，才建立 `COMPETITION_POLICY.yaml`；训练和赛后复盘不做形式化权限文件。
2. 选题时比较数据可得性、语义风险、团队能力、实现成本、创新空间、验证负担和写作风险。若差异很明显，可直接推荐，不要求每个候选题都填写完整评分表。
3. 给出团队角色与共享信息：题意口径、符号、数据版本、代码入口、关键结果和当前声明边界必须共享。写作成员从早期就参与结果组织，不在最后才接手。
4. 用相对里程碑而不是死板时间表安排：拆题/语义 → 可运行模型 → 主结果 → 验证与图表 → 论文闭合 → 提交检查。
5. 每个分问交接只保留后续成员真正需要的信息：当前模型、假设、代码入口、结果、图表、验证状态和未解决风险。能在一张表中表达的，不拆成多个文件。
6. 时间不足时优先保住已完成分问的闭环：`题意 → 模型 → 结果 → 验证 → 论文`。不要用未验证的复杂路线挤占基础交付。
7. 提交前调用 `mm-paper-reviewer`、`mm-paper-compile` 和必要的 `mm-visualization-delivery` 检查匿名、摘要、页数、图表可读性、引用、PDF 和附件。

## When to escalate

以下情况才启用更重的运营工件：

- 多人同时修改不同模型/代码，需要机器化交接；
- 多问强耦合，结果版本频繁变化；
- 需要跨会话恢复或多 Agent 协作；
- 用户明确要求完整审计或可复现实验记录；
- live contest 规则边界不清且会影响工具使用。

## Quality checks

- 不承诺奖项；
- 高风险语义歧义不能靠排期掩盖；
- 数据不可得、代码失败或模型不收敛时必须有最小回退；
- 关键结果要在同一口径下比较；
- 不把“内部多 seed 稳定”写成“全局最优”或“搜索空间已覆盖”；
- 不把 GitHub、CI 或工件数量当成数学质量本身。
