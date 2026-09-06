# 本地样图 → 样式卡 → 可运行模板

全量检索入口见 [full_corpus_style_library.md](full_corpus_style_library.md) 与 `assets/full-corpus/catalog.json`，包括全部68张图片变体、50个教程命名槽位和完整源码/技巧审计。本页 `assets/style-library/catalog.json` 的六张卡是已完成的组合模板，继续保留，不再充当所有样式的筛选上限。
原始样图路径相对 D:/数模文件/画图；只读查看，绝不改原始代码或取图中数据作为结果。来源哈希与原创预览索引在 catalog。
这些示例没有明确再分发许可证，随 Skill 分发的是原创重实现和明确标记 DEMO_ONLY 的预览，不分发原始图片/代码。
有本地样图时并列打开原图和预览；离线/路径移动后用随包原创预览，不依赖该磁盘路径运行。

| card_id | 设计语言 | 可运行入口 | 绑定要求 |
|---|---|---|---|
| rose-heatmap | 米白—粉红—深紫，细格线，右侧紧凑色条 | render_reference_template.py | 长表 row/column/value，完整矩阵，固定色域 |
| warm-surface-projection | 奶油黄—橙—深红，曲面＋底投影，同色域 | render_reference_template.py | 真正双参数网格 x/y/z，无插值补点 |
| teal-coral-inset | 青绿/珊瑚主次线、放大窗、边界定位 | render_reference_template.py | 有序 x，真实 series，显式放大范围 |
| interval-line | 主色点线＋已计算区间，轻网格 | matplotlib_plot_from_spec.py | errorbar，预计算 yerr 与区间定义 |
| paired-distribution | 青绿/珊瑚并列分布，多组同尺度 | matplotlib_plot_from_spec.py | box + precomputed_box，分析阶段已核对的五数摘要 |
| area-comparison | 主线＋浅填充，相关面板共享语法 | matplotlib_plot_from_spec.py | area，仅真实累计量/组成量，不假称置信带 |

色板是原创近似设计值，不宣称是从位图精确提色。来源图里不合理的巨型标题、演示星号和随意随机数据不继承；鲜明颜色与构图本身照常采用。

## 三个组合模板

命令：python scripts/render_reference_template.py --spec spec.json --output-dir figures/run-unique。
spec 从 assets/style-library/specs 复制并改 source_csv、变量与标签，绝不能直接把示例数据当本题结果。

- rose-heatmap: template_id, source_csv, figure_id, row, column, value, row_order, column_order, vmin, vmax。有负有正且以零为中性的指标应改用明确发散色板；不得给非负样例强行赋予相关意义。
- warm-surface-projection: template_id, source_csv, figure_id, x, y, z, vmin, vmax。要求完整矩形网格；缺网格退回散点或回到分析阶段制定插值协议。
- teal-coral-inset: template_id, source_csv, figure_id, x, series:[{column,label,lower?,upper?}], inset_bounds:[xmin,xmax,ymin,ymax]。下上界必须已经计算，另给 uncertainty_type 和 uncertainty_source。
- xlabel、ylabel、zlabel、colorbar_label 都用本题中文变量与单位。所有预览、哈希报告仅证明绘图能力，不证明模型有效。
- paired-distribution 的 spec 设置 precomputed_box=true，CSV 包含分类标签与 q1/median/q3/whislo/whishi，并写 summary_definition；渲染器用 bxp 直接画已有摘要，不重新估计分位数。若需要离群点，另外绑定已核对点数据；本卡不伪造离群点或显著性星号。
- area-comparison 默认 area_mode=single_outline，单序列真实累计量配浅填充与清晰边界。不将不同备选方案相加；需要堆叠时先说明组成量可相加及累计显示口径。

## 使用与选择

1. 先按读者任务选卡，再看 palette/layout/invariants；不只是把风格名填入配置。
2. 记录 style_reference: {card_id, catalog:{file,sha256}, preview:{file,sha256}}。默认绑定随包原创 PNG；需要原始图额外列 local_source_reference，不以未经许可的源图作为必需打包资产。
3. 选择模型或方法后跨图稳定复用颜色角色；热图的顺序色图、零中心发散色图与类别色板不能混用。
4. 在真实数据上渲染，打开 PNG 与 PDF。发生拟合、平滑、重采样或计算新统计量时先回到数值验证，不能在“换皮肤”中悄悄改变分析。
5. 将同宽参考预览与最终图交给独立视觉审查，具体检查见 reference_visual_review.md。
