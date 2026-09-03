---
name: mm-visualization-delivery
description: Plan and render traceable CUMCM figures, diagrams, tables, Excel workbooks, and LaTeX-ready visual evidence from verified mathematical-modeling results. Use for reader-oriented figure planning, model/mechanism diagrams, data plots, Origin/Visio delivery, deterministic SVG, visual remediation, or final figure quality control. Do not create figures to satisfy arbitrary quotas, beautify unverified results, or manually transcribe numerical outputs.
---

# 数学建模：可视化规划与结果交付

## Purpose

把已验证结果转成**少而有效、能解释模型、能支撑结论、可追溯且适合 CUMCM 正文**的图、表、Excel 和论文证据映射。

本 Skill 明确分成两个阶段：

1. `figure planning`：先判断读者在哪里会看不懂，决定**是否需要图、需要什么图、放正文还是附录**；
2. `figure rendering`：只对已批准的图意图做真实数据绑定、后端渲染、可编辑文件、PDF 和视觉审查。

渲染器不得为了“图证完整”自行新增图。

## When to use

- 需要解释坐标系、几何判据、受力、状态、case、协同结构或算法真实分支。
- 需要把多模型、多场景、轨迹、时间区间、Pareto 或敏感性结果组织成图表。
- 题目要求填写指定 Excel、CSV、图表或附件模板。
- 需要生成或验证 `.opju`、`.vsdx`、PDF、SVG 和中文 LaTeX 图题。
- 需要检查论文数字是否与程序输出一致。

## When not to use

- 结果尚未验证或数据来源不明。
- 用户希望通过改坐标轴、删点或视觉效果夸大差异。
- 只是因为“每问应该有图”而没有真实读者任务。
- 一个三线表或一句量化文字已经比图更清楚。

## Required inputs

- `NARRATIVE_MAP.yaml` 或等价论文叙事规划。
- `RESULTS_TO_CLAIMS.md` / `result_evidence_map.json`。
- 机器可读结果、字段说明、单位、精度和排序要求。
- 原始模板或提交格式。
- `reporting_profile`：`competition_compact` 或 `research_audit`。
- 最终排版宽度、分问编号和中文图题规则。

## Workflow

### Phase A — Figure planning

1. 读取 [figure_coverage_planning.md](references/figure_coverage_planning.md)、[local_chart_code_distillation.md](references/local_chart_code_distillation.md)、[local_plot_style_distillation.md](references/local_plot_style_distillation.md) 和总控的 [国奖与优秀论文叙事—图表蒸馏](../math-modeling-orchestrator/references/local_corpus/award_paper_narrative_figure_distillation.md)。
2. 逐问做“读者障碍审查”，而不是图量审查：
   - 不知道对象怎么运动/交互 → `orientation/mechanism`；
   - 看不懂几何、受力、case、状态或约束 → `mechanism`；
   - 不知道多主体/多资源如何协同 → 协同结构/时间区间图；
   - 需要看趋势、空间、响应面或权衡 → `evidence`；
   - 某个验证会改变是否相信主结论 → `validation`；
   - 只是工程审计或微小数值差 → 默认附录/支撑材料。
3. 对每个读者任务选择 `figure | table | text | appendix | not_applicable`。**不设置每问最少图数，也不要求每个核心结论必须有图。** 精确值通常由表格承担。
4. 优先设计模型解释链。复杂机理/几何题通常先考虑：物理场景 → 关键几何/状态 → case/投影 → 数学判据。模型结构从单主体变成多主体、多烟幕、多阶段时，如果理解结构发生变化，可以重新画协同/区间关系。
5. 能用二维示意、截面、投影、时间轴说明时，不为了“高级感”强行 3D。3D 仅在第三维真实承载空间部署或响应结构时使用。
6. 算法流程图只在算法本身成为理解障碍时使用，必须包含真实输入、关键分支/迭代、停止条件和输出；不画章节目录式“输入→建模→求解→结果”。
7. 生成 `FIGURE_PLAN.yaml` / `coverage_plan`，但允许某问没有正文图。每个保留图必须写 `reader_takeaway` 和“如果删除会损失什么理解”。

### Phase B — Figure rendering

8. 只有 `representation: figure` 的条目才建立完整 `FIGURE_INTENT.yaml`：`figure_id`、`question_id`、`narrative_role`、`reader_takeaway`、`claim_id`（如承担声明）、源数据、变量、单位、变换、后端、图型、最终宽度、placement 和中文 caption。
9. 数据图依据数据结构选型：趋势用折线，长类别比较用水平点图/条形，两状态优先哑铃/坡度，分布用原始点+箱线/小提琴，连续关系用散点，二维标量场用固定色域热图/等高线，多目标用 Pareto，区间/遮蔽/调度优先时间轴或区间条。
10. 机制、流程和结构图先列实体、关系、分组、主流向与反馈，再选择 Visio 或确定性 FigureSpec；符号、坐标和边界必须与方程一致。
11. 后端选择：常规数据图可用 Origin、MATLAB 或 Matplotlib；复杂机制/结构图优先 Visio/FigureSpec。后端选择由图型和可编辑需求决定，不由“炫酷程度”决定。
12. 所有渲染只消费已有机器可读结果。相关系数、拟合、平滑、区间、显著性、排名和新统计量必须在分析/验证代码中先计算并回写结果；渲染器不偷偷生成新结论。
13. 原生文件与导出文件同时保存：Origin `.opju + PDF`，Visio `.vsdx + PDF`，FigureSpec `JSON/SVG + PDF`，Matplotlib/MATLAB 保存脚本/spec 与 PDF。PDF 优先用于 XeLaTeX；PNG 仅用于真实栅格或明确回退。
14. 在论文最终尺寸重开，检查裁切、遮挡、字体、线宽、图例、单位、视觉重心、灰度/色盲可辨。多面板常规优先 2--4 个；超过 4 个要有不可拆分理由，超过 6 个优先附录。
15. `competition_compact` 正文优先保留：关键场景/机制、核心策略/结果、真正影响结论的验证。完整收敛、多种子、微小误差、后端 audit、版本谱系、参数全扫描默认进附录/支撑材料。`research_audit` 可完整保留。
16. 最终运行 `scripts/validate_figure_intent.py` 检查结构、来源、输出和叙事角色。coverage 检查验证的是**读者任务有合理载体**，不是固定图数。
17. 对 Origin/Visio/PDF 做匿名和元数据检查，生成交付清单与哈希。

## Output format

```markdown
## Figure planning：读者障碍与载体选择
## 正文图预算与附录迁移
## 交付物清单
## 字段/单位/精度
## 图表—声明/机制映射
## 原生后端与回退记录
## 最终尺寸视觉检查
## 数字一致性检查
## 未覆盖项与复现说明
```

## Quality checks

- Excel 模板不得改名、漏列、换序或破坏公式/格式。
- 所有论文数字能定位到机器可读结果。
- 不设“每问至少 4 张图”“每个核心结论至少一张证据图”等数量门；复杂题可多画，简单闭式计算可零正文图。
- 每张图必须有不可替代读者任务。若删图不影响理解或判断，删除或移附录。
- 复杂几何/机理若只给公式和验证曲线，而关键实体关系对读者不透明，应优先补 mechanism 图，而不是再补收敛图。
- 表格承担精确值，图形承担机制、趋势、空间、权衡、区间或真正关键的稳定性；完全重复则删去其一。
- `orientation` 不承担数值结论；`mechanism` 像推导的一部分；`evidence/validation` 必须绑定真实来源。
- 证据与验证不是强制成对放正文。验证如果只用于工程审计，可进入附录。
- 图内默认不放论文式标题；中文解释写入 LaTeX `\caption{}`。
- 默认风格为 `cumcm-clean`；方案择优可用 `cumcm-highlight`，高密度数据用 `cumcm-data-dense`，机制图用 `cumcm-mechanism`。鲜明效果只有在增强语义层级时才使用。
- 类别编码不能只依赖红绿颜色；误差棒、星号、区间、渐变必须绑定真实统计/变量语义。
- 两状态对比先评估哑铃/坡度；长标签优先横向图；完整精确值进入表格。
- 三维图必须有真实第三维必要性，并提供投影、切片、关键点或精确表之一。
- 不用软件 GUI、代码截图、章节目录式流程图作为正式证据图。
- 图的渲染成功只证明文件有效，不证明模型或声明成立。
