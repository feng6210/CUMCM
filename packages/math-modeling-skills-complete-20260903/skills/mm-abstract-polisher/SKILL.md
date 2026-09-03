---
name: mm-abstract-polisher
description: Improve or structure a mathematical modeling abstract by summarizing problem goals, models used, key numerical results, conclusions, and limitations. Use after the user provides model results or a draft abstract. Do not invent results, awards, data, or claims.
---

# 数学建模：摘要优化

## Purpose

优化数学建模摘要，使其包含问题、模型、关键结果、结论和局限，不写空泛套话。默认输出 CUMCM 中文 LaTeX 摘要专页内容。

## When to use

- 用户提供摘要草稿。
- 用户提供每问模型和关键结果，需要压缩成摘要。
- 需要检查摘要是否夸大或缺结果。

## When not to use

- 用户没有任何结果却要求写完整摘要。
- 用户要求编造数值、奖项或结论。
- 用户要求代写完整论文。

## Required inputs

- 论文主题。
- 每问使用的模型。
- 每问关键结果。
- 用户已有摘要草稿，如果有。

## Workflow

1. 从 `RESULTS_TO_CLAIMS.md` 和 `result_evidence_map.json` 建立每问摘要事实单元；不从图上目测抄写精确数值。
2. 检查摘要是否缺少结果、只写过程不写结论或夸大声明。
3. 按问题顺序重组；存在递进时写明继承对象和本问新增结构，不存在依赖时不制造虚假串联。
4. 每问写成“输出目标—本题化模型—求解—关键结果—验证/边界”，优先保留一个决定答案的主结果，辅助数值移入正文表格。
5. 删除不帮助区分路线的算法名称，保留模型机理、创新点和关键结论。
6. 输出改写版本、修改理由和压缩版本。
7. 若生成论文文件，写入 `sections/00_abstract.tex`，并要求由 `mm-paper-compile` 实际检查摘要专页不超过一页。

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
- 摘要要按问题顺序呈现。
- 所有不确定数值标注需要用户核验。
- 摘要不得出现公式、图表、文献引用、作者、学校、英文摘要或正文中不存在的数字。
- 摘要数字必须能回指 `RESULTS_TO_CLAIMS.md` 和 `result_evidence_map.json`。
- 每问至少形成“问题—模型—关键数字—验证/范围”事实链；只罗列算法名、没有关键数字或用“效果显著”替代证据时不得定稿。
- 组合模型名称必须与实际代码和正文一致；预算内最优、局部最优、候选集最优和全局最优不能混写。

## Academic integrity boundaries

- 只能用于学习、训练、课程作业辅助、赛前准备、结构检查和结果复盘。
- 不代写完整参赛论文，不代替用户参赛，不承诺获奖或保奖。
- 不伪造数据、代码运行结果、图表、参考文献或实验结论。
- 正在进行的正式竞赛中，必须提醒用户遵守赛事规则、课程要求和学术诚信。
- 所有不确定结论、推断条件和未验证结果都必须标注“需要用户核验”。
