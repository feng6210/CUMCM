---
name: mm-visualization-delivery
description: Plan and render traceable CUMCM data figures and editable model schematics, including TikZ geometry, forces, boundaries, PGFPlots coordinates, Origin/Visio delivery, tables, and Excel workbooks. Use for paper figure planning, diagram drawing, visual remediation, or figure quality control. Quantitative plots require verified results; schematics may explain approved models before solving.
---

# 数学建模：可视化规划与结果交付

## Purpose

把已验证结果转成**讲解充分、视觉精致、数值准确、可追溯且适合 CUMCM 中文论文**的图表。当前用户偏好本地素材中的鲜明配色、组合构图和适用的三维表现；不默认压少图量，也不把朴素等同于科研质量。其他用户明确指定的审美或正式模板优先。

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

- 定量图的结果尚未验证或数据来源不明；这不阻止根据已批准的模型说明规划机制图。
- 用户希望通过改坐标轴、删点或视觉效果夸大差异。
- 只是因为“每问应该有图”而没有真实读者任务。
- 一个三线表或一句量化文字已经比图更清楚。

## Required inputs

以下结果证据输入针对结果图。示意图可在求解前根据题目、已批准模型、符号与几何/边界条件绘制；示例参数需明确标为演示，不要求先产生实验结果。

- `NARRATIVE_MAP.yaml` 或等价论文叙事规划。
- `RESULTS_TO_CLAIMS.md` / `result_evidence_map.json`。
- 机器可读结果、字段说明、单位、精度和排序要求。
- 原始模板或提交格式。
- `reporting_profile`：`competition_compact` 或 `research_audit`。
- 最终排版宽度、分问编号和中文图题规则。

## Workflow

### Phase A — Figure planning

1. 读取 [figure_coverage_planning.md](references/figure_coverage_planning.md)、[local_chart_code_distillation.md](references/local_chart_code_distillation.md)、[local_plot_style_distillation.md](references/local_plot_style_distillation.md) 和总控的 [国奖与优秀论文叙事—图表蒸馏](../math-modeling-orchestrator/references/local_corpus/award_paper_narrative_figure_distillation.md)。
   样式设计先读 [全量样式库](references/full_corpus_style_library.md)，用 `scripts/corpus_style_library.py search` 检索 `assets/full-corpus/catalog.json` 的全部图片变体、教程图型和技巧；不得默认只在六张代表卡里选。每个变体保留配色、构图、标记与视角，复合面板不按文件夹名简化。基础实现再读 [样式卡与可运行模板](references/style_reference_library.md) 或 `render_corpus_chart.py --schema`。打开本地来源图（可访问且hash匹配时）或随包原创预览，记录实际 `style_reference`；这些参考只提供风格，不提供本题数据。全量入库与逐张复刻/运行验证分开记录。本 Skill 的用户风格选择优先于历史蒸馏中的“低装饰/二维优先”经验。
2. 逐问做“读者障碍审查”，而不是图量审查：
   - 不知道对象怎么运动/交互 → `orientation/mechanism`；
   - 看不懂几何、受力、case、状态或约束 → `mechanism`；
   - 不知道多主体/多资源如何协同 → 协同结构/时间区间图；
   - 需要看趋势、空间、响应面或权衡 → `evidence`；
   - 某个验证会改变是否相信主结论 → `validation`；
   - 只是工程审计或微小数值差 → 默认附录/支撑材料。
3. 对每个读者任务选择 `figure | table | text | appendix | not_applicable`。**不设置每问最少图数，也不要求每个核心结论必须有图。** 精确值通常由表格承担。
4. 优先设计模型解释链。复杂机理/几何题通常先考虑：物理场景 → 关键几何/状态 → case/投影 → 数学判据。模型结构从单主体变成多主体、多烟幕、多阶段时，如果理解结构发生变化，可以重新画协同/区间关系。
5. 有真实空间坐标、双参数响应或三维轨迹时，主动考虑三维图与投影/热图组合；二维和三维按解释效果选择，不要求先证明二维完全不能用。不把类别柱形挤成立体块制造差异。
6. 算法流程图只在算法本身成为理解障碍时使用，必须包含真实输入、关键分支/迭代、停止条件和输出；不画章节目录式“输入→建模→求解→结果”。
7. 生成 `FIGURE_PLAN.yaml` / `coverage_plan`，但允许某问没有正文图。每个保留图必须写 `reader_takeaway` 和“如果删除会损失什么理解”。
   逐问检查场景、方法、结果、对照和敏感性是否讲充分；已有双参数扰动结果时优先考虑敏感性热力矩阵。缺数据则登记所需实验，不用生成图片补造数值。新模型或新实验范围仍回到用户批准阶段。

### Phase B — Figure rendering

8. 只有 `representation: figure` 的条目才建立完整 `FIGURE_INTENT.yaml`：`figure_id`、`question_id`、`narrative_role`、`reader_takeaway`、`claim_id`（如承担声明）、源数据、变量、单位、变换、后端、图型、最终宽度、placement 和中文 caption。
9. 数据图依据数据结构选型：趋势用折线，长类别比较用水平点图/条形，两状态优先哑铃/坡度，分布用原始点+箱线/小提琴，连续关系用散点，二维标量场用固定色域热图/等高线，多目标用 Pareto，区间/遮蔽/调度优先时间轴或区间条。
10. 机制、流程和结构图先列实体、关系、分组、主流向与反馈。数模论文示意图默认通过代码或矢量软件实际绘制：TikZ、MATLAB/Matplotlib、Visio 或 SVG/FigureSpec。用户说“画出来/可编辑/几何示意”时不要转成图片生成。仅明确需要生成式场景素材时走 [科研插图调用协议](references/scientific_illustration_workflow.md)。
   对坐标、受力、光路、投影、材料分层与边界示意图，读取 [通用几何与物理工作流](references/geometry_diagram_workflow.md) 和 [用户确认的 TikZ 样式与构造](references/approved_tikz_schematics.md)。默认以 TikZ 实际绘制，输出可修改 `.tex` 与矢量 PDF；有明确解析关系或机器可读坐标时可用 PGFPlots。用户指定 Visio 或其他可编辑后端时尊重其选择，并核实实际支持范围。不要强制先转 SVG，也不要把物理示意图画成流程框。
   随包 `assets/tikz-schematics/` 的受力图、分层传热图是用户确认的两种样式起点，不是题型白名单。先按当前模型提取对象—关系—符号—方程，再选整体、剖面、分体、微元或状态构图；不能只改两张示例的标题来冒充新模型。需要基础 SVG 图元时仍可用 `scripts/geometry_diagram_from_spec.py`。旧 `draw_mechanism_examples.py` 保留为构造回归示例，不再作为默认论文风格样板。优秀论文来源范围见 [专项蒸馏记录](references/award_mechanism_distillation.md)，不得把两张试画通过称为全语料蒸馏完成。
11. 定量图用 Origin、MATLAB、Matplotlib；不能交给图像模型生成曲线、热力矩阵或结果数字。科研插图区分 `image2` 专用桥接与 `imagegen` 内置工具，发现、调用、回执、重开后才标记已运行；不得虚构工具或把一种后端冒充另一种。
12. 所有渲染只消费已有机器可读结果。相关系数、拟合、平滑、区间、显著性、排名和新统计量必须在分析/验证代码中先计算并回写结果；渲染器不偷偷生成新结论。
13. 原生文件与导出文件同时保存：TikZ/PGFPlots `.tex + PDF`（另存数据/参数来源），Origin `.opju + PDF`，Visio `.vsdx + PDF`，FigureSpec `JSON/SVG + PDF`，Matplotlib/MATLAB 保存脚本/spec 与 PDF。PDF 优先用于 XeLaTeX；PNG 可作预览，不替代矢量母版。
    原生生成的科研插图保留 PNG、中文 brief、prompt、调用回执和审查记录。`editable_output` 此时只能指向可修改的 JSON brief，且 `editability: prompt_and_spec_only`；不承诺像素图有逐节点编辑能力，不伪装 `.vsdx`、矢量 SVG 或矢量 PDF。
14. 在论文最终尺寸重开，检查裁切、遮挡、字体、线宽、图例、单位、视觉重心、灰度/色盲可辨。多面板常规优先 2--4 个；超过 4 个要有不可拆分理由，超过 6 个优先附录。
15. `competition_compact` 正文优先保留：关键场景/机制、核心策略/结果、真正影响结论的验证。完整收敛、多种子、微小误差、后端 audit、版本谱系、参数全扫描默认进附录/支撑材料。`research_audit` 可完整保留。
16. 按 [参考对照与独立视觉审查](references/reference_visual_review.md) 将样图与最终尺寸成图并列检查；数值检查与审美审查分别记录。由未参与该图生成的子 agent 做视觉审查（可用且允许时），如不可用则如实标记非独立，不能自称独立通过。
    最终运行 `scripts/validate_figure_intent.py --require-sources --require-outputs --require-visual-review --require-coverage`（另传 intent 路径）。检查的是哈希绑定的证据与审查记录，不是脚本替人判断“好看”。结果/图/brief 改变后旧审查失效。
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
- 默认从本地样式卡选型，常规数据图采用 `cumcm-vivid`；`cumcm-clean` 保留为用户选择或黑白优先场景，不自动覆盖鲜明风格。可用渐变、透明填充、纹理、阴影与层次构图，不能遮挡数据或让装饰冒充新变量。
- 全量样式库不删掉相同图型的配色、构图或视角变体。基础适配器成功不代表原图中的所有复合面板均已复刻；未适配部分保留检索与定制路线，不虚报全量运行闭环。原目录移动或不可用时，核心绘图仍用随包原创模板运行。
- 类别编码不能只依赖红绿颜色；误差棒、星号、区间必须绑定真实统计。渐变若编码变量要记录色域，纯装饰则声明非语义并检查不误导。
- 两状态对比先评估哑铃/坡度；长标签优先横向图；完整精确值进入表格。
- 三维图必须有真实第三维必要性，并提供投影、切片、关键点或精确表之一。
- 不用软件 GUI、代码截图、章节目录式流程图作为正式证据图。
- 图的渲染成功只证明文件有效，不证明模型或声明成立。
