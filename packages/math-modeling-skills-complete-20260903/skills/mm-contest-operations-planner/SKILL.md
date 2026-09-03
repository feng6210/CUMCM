---
name: mm-contest-operations-planner
description: Plan mathematical-modeling contest preparation, problem selection, team handoffs, relative milestones, fallback routes, and CUMCM submission checks. Use for contest training or team operations; do not promise awards or replace approved modeling decisions.
---

# 数学建模：竞赛运营与团队交接

## Purpose

把赛前准备、选题、团队分工、赛中相对时间安排、分问交接和终稿检查变成可执行产物。它不替代模型选择或求解；模型路线仍由总控在用户批准后执行。

## Workflow

1. 为每个候选题建立 `SELECTION_SCORECARD.md`：数据可得性、团队能力匹配、最小基线、实现成本、创新空间、验证负担、写作风险和回退路线。
2. 仅给出比较与建议，不把固定的 30 分钟、72 小时或获奖承诺写成硬规则。
3. 输出 `TEAM_ROLES.yaml`：建模、编程、写作角色的责任、输入、输出和交接条件；三人都必须共享模型、符号、数据版本和关键结果。
4. 输出 `MILESTONE_PLAN.yaml`：用相对时间分配拆题、基线、主模型、验证、图表、中文 LaTeX 正文、摘要和提交检查。
5. 输出 `CONTINGENCY_PLAN.md`：数据不可得、代码失败、不收敛、精度不足和时间不足时的最小闭环与回退。
6. 每问完成时生成 `QUESTION_HANDOFF.yaml`，至少记录 `question_id`、模型版本、假设、代码入口、结果文件、关键数字、图表、验证状态、LaTeX 章节和未解决项。
7. 提交前调用 `mm-paper-reviewer`、`mm-paper-compile` 和 `mm-visualization-delivery`，检查 CUMCM 匿名、摘要专页、无目录、正文页数、附件清单与 PDF/ZIP 大小。

## Quality checks

- 数据不可得或基线不可运行时，评分卡必须降低推荐优先级并列出回退。
- 团队分工不能把写作手变成只在最后接收结果的人；每问结果出来后应立即同步。
- 时间不足时优先保证已完成分问的模型—结果—验证—论文闭环，不用未验证复杂路线挤占基础交付。
- 不新增远程仓库门控或远程仓库步骤。

## 本地真题训练增强

- 选题评分不按 A/B/C 字母套模型，而按数据附件可读性、最小基线可运行性、复合接口数量、验证负担和写作交接风险评分。
- 赛前回归题库应覆盖机理--优化、预测--决策、统计--决策、几何--搜索、随机仿真和在线重规划；每次训练保留“最小闭环、升级路线、失败回退、论文证据”四项复盘。
- 多表关联、现场不可获得参数、在线信息到达和支撑材料格式都要进入里程碑，不把最后集中写作当作默认方案。
