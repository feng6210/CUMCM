---
name: mm-paper-reviewer
description: Review a mathematical modeling paper draft for logic gaps, unanswered questions, weak assumptions, model mismatch, unsupported results, unclear figures, missing sensitivity analysis, and academic integrity risks. Use for critique and revision planning. Do not rewrite the full paper as a final submission.
---

# 数学建模：论文审稿

## Purpose

对数学建模论文草稿做审稿、查错和修改优先级规划，重点找逻辑缺口、模型错配、无支撑结论和诚信风险。

## When to use

- 用户提供论文草稿。
- 需要检查是否回答每一问。
- 需要找模型、变量、公式、图表、结果和摘要问题。

## When not to use

- 用户要求代写终稿。
- 用户只给题目但没有草稿。
- 用户要求编造缺失结果或参考文献。

## Required inputs

- 论文草稿。
- 题目。
- 数据。
- 代码或结果，如果有。

## Workflow

1. 检查是否回答每一问。
2. 检查模型是否匹配、假设是否合理、变量是否一致。
3. 检查 `NARRATIVE_MAP.yaml` 与正文是否一致：分问依赖、共享内核、继承对象、模型增量、精确结果、检验和声明边界是否闭合；再检查公式是否解释、结果是否支撑结论、图表是否必要。
4. 检查摘要是否包含模型和结果。
5. 检查灵敏度分析、模型评价和附录代码。
6. 识别伪造或无法验证内容。
7. 输出风险分级和修改优先级。
8. 对 LaTeX 稿额外核对摘要专页、无目录、正文/附录边界、匿名、图表 PDF 引用和支撑材料清单；编译问题交给 `mm-paper-compile`。
9. 生成 `PAPER_CLAIM_AUDIT.json` 时，将每条数字、比较、排名、百分比和范围声明关联到原始结果；结果变更后标记该审计 stale。
10. 可用 `scripts/audit_paper_claims.py` 做保守的证据文件与哈希核对；它最多输出 `REVIEW_REQUIRED`，不会把“文件存在”误判为模型结论通过。
11. 可用 `scripts/audit_citations.py` 检查 LaTeX 引用键与 BibTeX 的结构一致性；文献真实性与引用语境仍须逐条审查。
12. 对完整终稿或“全流程闭环”请求，在平台允许且已获委派权限时必须自动启动不继承写作上下文的 fresh-agent：至少分别执行数字/结论审查、图表/证据审查和 CUMCM LaTeX 结构/叙事审查。图表审查必须核对叙事角色、最终尺寸、图表分工、视觉语法一致性和数值来源；结构审查必须核对共享内核与逐问增量。审查 Agent 只接收当前工件、冻结证据与本检查表；不得向其提供主写作者结论、期望 PASS 或拟议修复。
13. 汇总报告记录每个审查 Agent、审查模式、输入工件 SHA-256、P0--P3 发现和时间点。P0/P1 未解决时阻止最终交付；正文、图表或结果变化后将对应报告标记 stale，并重新 fresh audit。若运行策略禁止委派，输出 `INDEPENDENT_REVIEW_NOT_RUN` 并说明阻塞，不能用 `same-agent-cold` 替代独立审查门。

审查维度和风险分级见 [review_checklist.md](references/review_checklist.md)。优先检查数据泄漏、目标错配、约束未核验和结论越界。

## Output format

```markdown
## 总体评价

## 主要风险等级

| 风险 | 等级 | 位置 | 问题 | 修改建议 |
|---|---|---|---|---|

## 分部分审稿

### 摘要
### 问题重述
### 假设与符号
### 模型建立
### 模型求解
### 结果分析
### 灵敏度分析
### 模型评价
### 附录与代码

## 优先修改清单

## 不建议改动的部分

## 学术诚信风险提醒
```

## Quality checks

- 发现问题要给位置和修改建议。
- 优先级要按影响结论程度排序。
- 不能重写为终稿。
- 无法核验的结果必须标注风险。
- 区分 `remediation_followup`（检查指定修复）和 `fresh_reaudit`（只读当前论文与证据）；同族审查不得冒充外部独立认证。
- `same-agent-cold` 仅可作为补充诊断；终稿独立审查要求不继承写作上下文的 fresh-agent。平台允许时由 Skill 自动触发，不等待用户再次提醒。
- 引用需分别检查存在性、元数据和语境支持；不能用看似真实的文献填补缺口。
- 冷审查同时检查模型名与实现、示例/随机数据、全数据预处理泄漏、随机切分、求解状态、原始约束重算和未证明的最优性；代码能运行不等于论文数字成立。
- 对每个分问检查“任务—变量—模型—关键数值—验证—边界”是否闭合，并对图题、摘要、正文、表格和附录做同一数字回指。
- 对共享模型检查“只定义一次、后续写增量”；对问间交接检查继承对象、数据/参数版本和误差传播。问题分析若只是重述原题，不得判为叙事通过。
- 图表审查按 [本地图表代码蒸馏](../mm-visualization-delivery/references/local_chart_code_distillation.md) 检查受限图型、矢量导出、字体/裁切和真实数据绑定。
- 图表还按 [国奖与优秀论文叙事—图表蒸馏](../math-modeling-orchestrator/references/local_corpus/award_paper_narrative_figure_distillation.md) 检查导航/机制/证据/验证角色、精确值表格化、跨图视觉语法、多面板密度、三维替代和软件截图反例。

## Academic integrity boundaries

- 只能用于学习、训练、课程作业辅助、赛前准备、结构检查和结果复盘。
- 不代写完整参赛论文，不代替用户参赛，不承诺获奖或保奖。
- 不伪造数据、代码运行结果、图表、参考文献或实验结论。
- 正在进行的正式竞赛中，必须提醒用户遵守赛事规则、课程要求和学术诚信。
- 所有不确定结论、推断条件和未验证结果都必须标注“需要用户核验”。
