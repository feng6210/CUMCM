---
name: mm-abstract-polisher
description: Improve or structure a mathematical modeling abstract by summarizing problem goals, models used, key numerical results, conclusions, and only decision-relevant limitations. Use after the user provides model results or a draft abstract. Do not invent results, awards, data, or claims.
---

# 数学建模：摘要优化

## Purpose

优化数学建模摘要，使评委能在一页内快速看清“每问解决什么、建立什么模型、得到什么关键结果”。摘要不是压缩后的审计报告：验证只保留最有区分度且直接影响结论可信度的一项，限制只在会改变答案含义时就地出现。

## When to use

- 用户提供摘要草稿。
- 用户提供每问模型和关键结果，需要压缩成摘要。
- 需要检查摘要是否夸大、缺结果、算法堆叠或审计味过重。

## When not to use

- 用户没有任何结果却要求写完整摘要。
- 用户要求编造数值、奖项或结论。
- 用户要求代写完整论文。

## Required inputs

- 论文主题。
- 每问使用的模型。
- 每问关键结果。
- 用户已有摘要草稿，如果有。
- 优先读取 `RESULTS_TO_CLAIMS.md` 和 `result_evidence_map.json`。

## Workflow

1. 从 `RESULTS_TO_CLAIMS.md` 和 `result_evidence_map.json` 建立每问摘要事实单元；不从图上目测抄写精确数值。
2. 检查摘要是否缺少结果、只写过程不写结论、夸大声明、重复验证或堆叠内部审计术语。
3. 按问题顺序重组；存在真实递进时写明继承对象和本问新增结构，不存在依赖时不制造虚假串联。
4. 每问优先采用“输出目标—本题化模型/关系—求解—关键结果—一句必要解释”。验证仅在它能直接增强核心结论或改变读者判断时保留；限制仅在不写会误解答案时就地出现。
5. 优先保留一个决定答案的主结果，辅助数值移入正文表格。删除不帮助区分路线的算法名称和无读者价值的求解日志。
6. 对 `gate/hash/backend/workflow/seed/commit/strict validation` 等内部词进行竞赛化转换或迁移；除非它们本身改变结论，否则不进入摘要。
7. 若摘要存在明显回答者/辩护式措辞，可调用或遵循 `mm-paper-humanizer` 的 `light` 规则；不得为了自然化改变公式外的技术事实、最优性等级或不确定性。
8. 输出改写版本、修改理由和压缩版本。
9. 若生成论文文件，写入 `sections/00_abstract.tex`，并要求由 `mm-paper-compile` 实际检查摘要专页不超过一页。

内置样式默认将“关键词：”及条目整行加粗，分问引导语和少量关键结果选择性加粗；不对整段摘要加粗。正式模板或用户另选样式时优先遵循。保留原始结果完整精度，仅对展示值按有效精度舍入；摘要舍入必须与正文结果一致。

## Decision-relevant limitation rule

以下限制若存在，通常需要最小化地保留在摘要：

- 不写会把局部/搜索域/预算内最优误解成全局最优；
- 未收敛或不可行区域可能实质改变最优性结论；
- 比较方法使用不同数据、时间窗或目标口径；
- 一个模型内结论容易被误读为真实因果/实测结论。

以下内容默认移到正文模型检验、模型评价或支撑材料：

- 完整 solver 名单与交叉复算日志；
- 文件行数、hash、commit、manifest；
- 全部 seed/trial 计数；
- 微小数值复算差；
- 重复出现的“仍需真实实验验证”；
- 已在正文假设/局限中说明且不改变摘要数字解释的边界。

详见 [论文可读性与修订](../mm-paper-structure-writer/references/paper_readability_and_revision.md) 与 `mm-paper-humanizer`。

摘要的信息顺序和禁用表达见 [abstract_patterns.md](references/abstract_patterns.md)。只允许使用已核验数值。

## Output format

```markdown
## 摘要问题诊断

## 改写版摘要

## 修改理由

## 需要核验的数据

## 可进一步压缩版本

## 学术诚信提醒
```

## Quality checks

- 不能编造结果。
- 不能写获奖承诺。
- 摘要要按问题顺序呈现，但句法和段长不强制同构。
- 所有不确定数值标注需要用户核验。
- 摘要不得出现公式、图表、文献引用、作者、学校、英文摘要或正文中不存在的数字。
- 摘要数字必须能回指 `RESULTS_TO_CLAIMS.md` 和 `result_evidence_map.json`。
- 每问至少闭合“问题/输出—模型—关键答案”；验证和范围是按决策价值选择，不要求每问机械出现。
- 只罗列算法名、以“效果显著”代替证据、重复堆验证术语或为凑数字编造实验时不得定稿。
- 组合模型名称必须与实际代码和正文一致；预算内最优、局部最优、候选集最优和全局最优不能混写。
- 已经自然、紧凑且信息完整的摘要句允许不改，不为制造改动而重写。

## Academic integrity boundaries

- 只能用于学习、训练、课程作业辅助、赛前准备、结构检查和结果复盘。
- 不代写完整参赛论文，不代替用户参赛，不承诺获奖或保奖。
- 不伪造数据、代码运行结果、图表、参考文献或实验结论。
- 正在进行的正式竞赛中，必须提醒用户遵守赛事规则、课程要求和学术诚信。
- 所有真正影响答案含义的不确定结论、推断条件和未验证结果必须保留或明确标注需要核验，不能通过“去 AI 味”隐藏。
