---
name: mm-visualization-delivery
description: Turn verified mathematical-modeling results into traceable, publication-quality Chinese CUMCM figures, diagrams, tables, Excel workbooks, and LaTeX-ready evidence maps. Use for data plots, model or workflow diagrams, Origin/Visio delivery, deterministic SVG, visual style remediation, or final figure quality control. Do not beautify unverified results or manually transcribe numerical outputs.
---

# 数学建模：可视化与结果交付

## Purpose

把已验证结果转成可追溯且达到竞赛终稿观感的图、表、Excel 和论文证据映射；数据图可使用 Origin、MATLAB 或 Matplotlib，机制与流程图优先输出 Visio 原生工程，并同时提供可由 XeLaTeX 直接引用的 PDF。美观可以克制，也可以鲜明炫酷；选择标准是读者是否更快看懂、最终尺寸是否清楚以及视觉编码是否忠实。

## When to use

- 题目要求填写指定 Excel、CSV、图表或附件模板。
- 需要把多模型、多场景、轨迹或敏感性结果组织成图表。
- 需要绘制模型机制、算法流程、状态转移、网络结构或分问之间的依赖关系。
- 需要生成或验证 `.opju`、`.vsdx`、PDF、SVG 和中文 LaTeX 图题。
- 需要检查论文数字是否与程序输出一致。

## When not to use

- 结果尚未验证或数据来源不明。
- 用户希望通过改坐标轴、删点或视觉效果夸大差异。
- 只需运行算法而无交付要求。

## Required inputs

- 机器可读结果、字段说明、单位、精度和排序要求。
- 原始模板或提交格式。
- 每张图表要支持的声明。`evidence`/`validation` 必须绑定真实 `claim_id`；不承担结果声明的 `orientation`/`mechanism` 可使用 `claim_id: not_applicable`，论文级导航可使用 `question_id: paper`。
- 缺失值、无解、不可达和不确定性表示规则。
- 最终排版宽度、分问编号、中文图题以及需要支持的 `claim_id`。

## Workflow

1. 先读取 [github_plotting_methods.md](references/github_plotting_methods.md)、[local_chart_code_distillation.md](references/local_chart_code_distillation.md)、[local_plot_style_distillation.md](references/local_plot_style_distillation.md) 和总控的 [国奖与优秀论文叙事—图表蒸馏](../math-modeling-orchestrator/references/local_corpus/award_paper_narrative_figure_distillation.md)。先按 `orientation | mechanism | evidence | validation` 指定叙事角色，再把载体分为数据图、结构/流程图、结果表或无需作图；图形必须服务一个明确问题、声明或不可替代解释任务。
2. 建立题目要求—结果文件—图表—论文表述映射，锁定字段名、单位、精度、样本口径和比较条件。随后按 [figure_coverage_planning.md](references/figure_coverage_planning.md) 建立整篇 `coverage_plan`：用 `expected_question_ids` 锁定题目拆解中的全部分问；每个核心分问都要检查数据诊断、模型机制、主结果、基线/方案对比、模型验证、敏感性/稳健性六类读者任务；主结果和验证必须有图，其余任务必须有图或写明不适用理由。每个分问最终至少 4 个互不重复的图号和实际图件，不同槽位不得复用图号或共享输出/运行报告哈希充数，每个核心结论至少绑定一张证据图或验证图。
3. 为每张图建立 `FIGURE_INTENT.yaml` 条目；除原字段外必须写 `narrative_role`、`reader_takeaway`、`exact_values_location`、`visual_grammar_group`、`visual_grammar` 和 `placement`。验证图另写 `validation_target` 与 `validation_method`；MATLAB/Matplotlib 图必须用 `renderer_spec.file + sha256` 绑定真实渲染规范，运行报告的 `render_contract` 必须与意图中的图型、变量和变换一致。`visual_grammar` 必须包含字体、最终字号、色板、线宽、`style_profile`、`final_width_mm`、`legend_strategy`、`precision_policy` 与 `decorative_effects`。使用透明填充、渐变、阴影、发光、局部放大或三维效果时，还要声明效果是语义编码还是非语义装饰；最终交付必须完成遮挡、灰度、最终尺寸和去除效果对照四项审查。默认运行 `scripts/validate_figure_intent.py FIGURE_INTENT.yaml`，脚本默认要求来源存在，并对结构、叙事角色、来源路径、跨图视觉语法和版面风险做 fail-closed 检查；只有草拟尚未落盘的图表计划时才可显式加 `--allow-missing-sources`，且此时不得进入交付。`--strict` 只用于把额外建议也升级为失败。当前 Windows 安装使用已验证的 64 位 `py -3.12` 运行 Python 脚本；不要误用指向 32 位且缺少 Matplotlib 的裸 `python` 命令。此检查不判断模型或论文声明是否正确。
4. 数据图依据数据结构选型：趋势用折线，长类别比较用水平点图/条形，两状态变化优先哑铃/坡度图，分布比较用原始点叠加箱线/小提琴，连续变量关系用散点，矩阵用固定色域热图，组成用堆叠条形；不默认使用均值柱形、饼图、三维图或双纵轴。相关系数、拟合、平滑、区间和显著性必须在验证代码中预先计算，渲染器只画已有列；相关热图固定 `[-1,1]` 色域。
5. 机制、流程和结构图先列实体、关系、分组、主流向与反馈，再选择 Visio 或确定性 FigureSpec；符号、坐标、边界必须与方程一致，算法图必须包含真实分支/迭代、停止条件和输出，不得在图中增加模型不存在的机制。
6. 常规折线、散点、误差和柱形数据图可优先本机 Origin；需要素材库式箱线、热图、透明填充、鲜明配色、多面板或复杂论文图时优先 MATLAB；两状态哑铃/坡度图可用 MATLAB 或 Matplotlib。流程/结构图优先本机 Visio。后端不可用或 Origin 导出实物的色板、字号未通过回读审计时，数据图立即回退 MATLAB/Matplotlib，不把 Origin 默认主题冒充指定风格。所有后端显式使用本 Skill 的 `cumcm-clean | cumcm-highlight | cumcm-data-dense | cumcm-vivid | cumcm-mechanism` 风格，不接受不可控的软件默认主题。Matplotlib 运行 `scripts/matplotlib_plot_from_spec.py`，MATLAB 运行 `scripts/matlab_plot_from_spec.m`；两者只消费已有结果，其 `RUNTIME_VERIFIED` 清单不能代替声明审查。后端命令和交付契约见 [native_backend_workflows.md](references/native_backend_workflows.md)。
7. 从机器可读结果生成图表，禁止手工抄数；Origin 新计算的拟合量、区间或统计量必须回写机器可读结果并返回验证阶段。
8. 原生文件与导出文件同时保存：Origin 为 `.opju` + PDF，Visio 为 `.vsdx` + PDF，FigureSpec 为 JSON + SVG + PDF。PDF 优先用于 XeLaTeX，PNG 只用于真正的栅格内容或明确回退。每个条目还必须登记 `backend_report` 与 `backend_report_sha256`；报告中的全部输入、渲染契约、原生文件、PDF、实际字体/色板/透明效果、最终宽度与有效最小字号、重开和匿名状态必须与磁盘实物及 `FIGURE_INTENT` 一致。
9. 在论文最终尺寸重开 PDF/PNG，检查裁切、遮挡、颜色、中文字体、线宽、图例、单位和视觉重心；同时做灰度/色盲可辨检查。需要增加图量时优先构成逻辑图组，例如“原始/处理后”“基线/主模型”“拟合/残差”“名义/扰动”“目标/约束余量”，而不是重复绘制同一组数字。多面板常规优先 2--4 个，超过 4 个记录不可拆分理由，超过 6 个优先移入附录。三维图必须有投影、切片、关键点标注或精确结果表。再逐项核对图、表、摘要、正文与附件数值。
10. 对 Origin/Visio 原生文件、导出 PDF 和预览做匿名检查；Office/PDF 元数据可用 `scripts/sanitize_office_metadata.py` 清理。既要检查 PDF `/Info`，也要检查 XMP `/Metadata` 原始字节，不能因 `pdfinfo` 的 Author 为空就判定匿名完成。
11. 读取 [delivery_checklist.md](references/delivery_checklist.md)，生成交付清单、运行清单和哈希；最终交付前必须再运行 `scripts/validate_figure_intent.py FIGURE_INTENT.yaml --require-coverage --require-outputs`，验证每问图证覆盖、核心结论映射、来源哈希、原生/LaTeX 输出存在及登记哈希。若主结果或验证缺图、核心结论无图证、可选图类既无图也无不适用说明，则不得交付。GitHub 来源只记录在 [github_derivation_notice.md](references/github_derivation_notice.md)，不构成运行依赖或门控。

## Output format

```markdown
## 交付物清单
## 字段/单位/精度
## 图表—声明映射
## 原生后端与回退记录
## 最终尺寸视觉检查
## 数字一致性检查
## 未覆盖项与复现说明
```

## Quality checks

- Excel 模板不得改名、漏列、换序或破坏公式/格式。
- 所有论文数字能定位到一个机器可读结果单元格或记录。
- 图中显示不确定性、样本量和必要单位；无解不填零。
- 每个核心分问至少有 4 个互不重复的图号，其中必须含相互独立的主结果图和验证图；其余优先从数据诊断、机制、对比及敏感性/稳健性补齐。4 张是最低覆盖线，不是目标上限；复杂分问应继续按证据缺口增加图量，正文过密时将次级诊断移入附录。
- 每个核心结论至少由一张 `evidence` 或 `validation` 图支持；只有表格而没有能让读者快速看懂趋势、差异、误差或稳健性的图，必须记录为图证缺口。
- 导航图不承担数值结论；机制图像推导的一部分；证据/验证图优先成对展示可比状态。没有不可替代读者任务的图删除。
- 精确答案优先写入机器可读结果表；图和表完全重复且没有独立解释任务时删去其一。
- 排除样本不得进入均值、区间或排序；不同样本量、预算或协议不得作为视觉同级比较，除非显式标注。
- 图题必须对每个绘制数据行成立；“显著”“最优”“提高”等词必须有对应统计或优化证据。
- 类别编码不能只依赖红绿颜色；必要时同时使用线型、点型、纹理或直接标注。
- 图内默认不放论文式标题；标题和解释写在中文 LaTeX `\caption{}` 中，LaTeX 负责图号。
- 默认风格为 `cumcm-clean`，用户偏好鲜明效果时可使用 `cumcm-vivid`；方案择优用 `cumcm-highlight`，高密度图用 `cumcm-data-dense`，机制图用 `cumcm-mechanism`。炫酷不构成失败理由，失真、遮挡和不可读才构成失败。
- 两状态对比必须先评估哑铃/坡度图；长标签优先横向图；完整精确值进入表格，图上只标关键值或差值。
- 星号与 `p` 值括号必须绑定统计检验、比较族和多重比较策略；类别渐变必须绑定真实连续变量，否则失败。
- 误差棒必须登记 `uncertainty_type`、`uncertainty_level` 和 `sample_size_source`，区分标准差、标准误、置信区间、预测区间和数值误差；只有一列来源不明的 `yerr` 不得进入终稿。
- 矢量图优先 PDF；最终输出不得包含网络字体、GitHub、外部 shim 或 `ARIS_REPO` 运行依赖。
- 输出文件重新打开后检查行列数、类型和关键值。
- 每张图的图题必须对所有绘制数据成立；不同样本、预算或协议不得伪装为直接可比。
- 使用 `scripts/figure_renderer.py` 生成确定性结构图时，不依赖外部项目路径或远程路径。
- `.opju` 与 `.vsdx` 只有在原生应用成功保存且重新载入后才可声明为原生可编辑文件；否则必须回退并如实记录。
- 原生后端“命令返回成功”不等于视觉样式生效；Origin 报告必须从导出 PDF 回读实际色板并按最终宽度计算有效最小字号，Visio 报告必须在元数据清理后重开并重新哈希。最终门解析这些报告，不能只核文件存在。
- 随机演示数据、只调用 `show()`、不导出、不关闭图窗或依赖未声明字体的脚本只能标为 `DEMO_ONLY`；Matlab/Python 源码编码必须作为环境清单的一部分验证。
- 饼/环形、雷达、双 Y 轴和 3D 图必须记录采用理由及二维替代检查；“更炫酷”不是采用理由。
- 软件界面、代码窗口、默认彩虹配色、过密小图和章节目录式流程图不得作为最终证据图。
- 图的“漂亮”不能以隐藏失败运行、改变色域/轴限、压扁长宽比或增加不存在的机制为代价。

## Academic integrity boundaries

- 不手工修改结果以匹配预期。
- 不用截断坐标轴、选择性删点或装饰性图表误导读者。
- 不把示例、占位符或未运行结果交付为真实结果。
