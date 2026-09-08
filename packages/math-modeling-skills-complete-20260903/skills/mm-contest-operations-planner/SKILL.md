---
name: mm-contest-operations-planner
description: Plan mathematical-modeling contest preparation, problem selection, team handoffs, relative milestones, fallback routes, competition-policy boundaries, and CUMCM submission checks. Use for contest training or team operations; do not promise awards or replace approved modeling decisions.
---

# 数学建模：竞赛运营与团队交接

## Purpose

把赛前准备、选题、团队分工、赛中相对时间安排、分问交接和终稿检查变成可执行产物。它不替代题意裁决、模型选择或求解；主模型路线仍由总控在语义锁定、最小基线完成和用户批准后执行。

## Workflow

1. 先登记 `COMPETITION_POLICY.yaml`：赛事名称/阶段、是否允许 AI、联网、外部论文、公开答案/benchmark、团队协作范围、引用/披露要求和未知项。未知且可能改变工具使用边界时必须先澄清，不能默认允许。
2. 为每个候选题建立 `SELECTION_SCORECARD.md`：数据可得性、团队能力匹配、题意语义风险、最小基线、实现成本、创新空间、验证负担、写作风险和回退路线。
3. 仅给出比较与建议，不把固定的 30 分钟、72 小时或获奖承诺写成硬规则。
4. 输出 `TEAM_ROLES.yaml`：建模、编程、写作角色的责任、输入、输出和交接条件；三人都必须共享 `PROBLEM_SEMANTICS.yaml`、符号、数据版本、关键结果和当前声明边界。
5. 输出 `MILESTONE_PLAN.yaml`：用相对时间分配拆题/语义裁决、最小基线、主模型、外部挑战（规则允许时）、验证、图表、中文 LaTeX 正文、摘要和提交检查。
6. 输出 `CONTINGENCY_PLAN.md`：题意未决、数据不可得、代码失败、不收敛、外部更优可行解击穿、精度不足和时间不足时的最小闭环与回退。
7. 每问完成时生成 `QUESTION_HANDOFF.yaml`，至少记录：
   - `question_id`
   - `problem_semantics_ref`
   - `baseline`
   - `model_version`
   - `assumptions`
   - `code_entry`
   - `machine_readable_results`
   - `benchmark_challenge`（`PENDING / PASS / CHALLENGED / INCOMPARABLE / NOT_ALLOWED_BY_RULES` 之一，按当前阶段）
   - `key_claims`
   - `figure_intents`
   - `validation_status`
   - `latex_section`
   - `unresolved_risks`
   总控再按 `cross_skill_output_contract.md` 规范化，不要求团队成员重复伪造上游字段。
8. 提交前调用 `mm-paper-reviewer`、`mm-paper-compile` 和 `mm-visualization-delivery`，检查 CUMCM 匿名、摘要专页、无目录、正文页数、附件清单、图表可读性与 PDF/ZIP 大小。

## Quality checks

- `COMPETITION_POLICY.yaml` 未明确允许的外部答案/benchmark，不得在 live contest 中主动获取或使用。
- 语义风险高且会改变解结构时，选题评分和里程碑必须显式预留裁决时间，不得直接进入求解。
- 数据不可得或基线不可运行时，评分卡必须降低推荐优先级并列出回退。
- 团队分工不能把写作手变成只在最后接收结果的人；每问语义、基线和主结果出来后应立即同步。
- 时间不足时优先保证已完成分问的“语义—基线—模型—结果—验证—论文”闭环，不用未验证复杂路线挤占基础交付。
- 外部方案在同 evaluator 下击穿 incumbent 时，运营计划必须给返工预算，不能只改论文措辞。
- 不新增远程仓库门控或把 GitHub 状态当成数学结果 PASS。

## 本地真题训练增强

- 选题评分不按 A/B/C 字母套模型，而按数据附件可读性、语义歧义、最小基线可运行性、复合接口数量、验证负担和写作交接风险评分。
- 赛前回归题库应覆盖机理--优化、预测--决策、统计--决策、几何--搜索、随机仿真和在线重规划；每次训练保留“语义裁决、最小闭环、升级路线、失败回退、论文证据”五项复盘。
- 至少保留一类“内部多种子稳定但被外部可行解击穿”的训练案例，防止把随机稳定性误写成搜索空间覆盖。
- 多表关联、现场不可获得参数、在线信息到达和支撑材料格式都要进入里程碑，不把最后集中写作当作默认方案。
