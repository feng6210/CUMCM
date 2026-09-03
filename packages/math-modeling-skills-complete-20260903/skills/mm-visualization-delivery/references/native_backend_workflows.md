# Origin、Visio 与离线回退工作流

## 后端探测

```powershell
powershell -ExecutionPolicy Bypass -File scripts/probe_origin_backend.ps1
powershell -ExecutionPolicy Bypass -File scripts/probe_visio_backend.ps1
```

探测结果只说明程序或 COM 接口存在。只有真实生成、保存、导出和重新载入成功，才能声明后端已连通。

## Origin 数据图

使用 `scripts/origin_plot_from_csv.ps1` 从 CSV 数值列生成折线、散点、折线加点或柱状图。哑铃/坡度图当前路由到内置 Matplotlib 渲染器，不能声称由 Origin 原生脚本生成：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/origin_plot_from_csv.ps1 `
  -CsvPath results/series.csv -XColumn time -YColumn value `
  -PlotType line_symbol -OutputDirectory figures/origin -BaseName fig_q1_series `
  -XLabel '时间/s' -YLabel '响应值'
```

脚本默认采用 `cumcm-clean`：不写图内标题、不硬编码轴范围、使用白底并按最终插图宽度反推标签字号。需要突出经验证主方案时使用 `-StyleProfile cumcm-highlight`；用户偏好鲜明观感且最终尺寸仍清楚时可试用 `-StyleProfile cumcm-vivid`。Origin 的 LabTalk 样式请求不能直接当作生效证据：脚本会从最终 PDF 回读实际填色、页面尺寸和有效最小字号，报告的 `effective_palette` 才是最终真值；若它与 `FIGURE_INTENT.visual_grammar.palette` 不一致，最终门失败并应转 MATLAB/Matplotlib。旧参数 `-PublicationTheme` 仅作为 `cumcm-clean` 兼容别名。

成功产物：

- `<BaseName>.opju`：Origin 原生可编辑工程；
- `<BaseName>.pdf`：XeLaTeX 用矢量图；
- `<BaseName>.origin-report.json`：数据列、行数、命令结果、保存、导出和重开证据。

报告同时包含清理后 PDF 的匿名/重开状态、实际 PDF 色板、`final_width_mm` 和 `effective_min_font_pt`；有效最小字号低于 7 pt 时脚本直接失败。

脚本只负责忠实绘制已有列，不自动做拟合、平滑、删点或统计汇总。若需要这些变换，先在模型/验证代码中产生机器可读结果并登记到 `transformations`。

## Visio 结构图

使用 `scripts/visio_diagram_from_spec.ps1` 将本地 FigureSpec JSON 生成 Visio：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/visio_diagram_from_spec.ps1 `
  -SpecPath figures/specs/model_flow.json -OutputDirectory figures/visio `
  -BaseName fig_model_flow -FinalWidthMm 160 -WorkerTimeoutSec 120
```

成功产物：

- `<BaseName>.vsdx`：Visio 原生可编辑文件；
- `<BaseName>.pdf`：XeLaTeX 用矢量图；
- `<BaseName>.visio-report.json`：节点、边、保存、导出和重开证据。

Visio 脚本支持 FigureSpec 的基本节点与边。隐藏 worker 启动后设置 `Application.AlertResponse=1`，并使用 `SaveAsEx(..., 0)`，防止兼容性或保存提示在不可见窗口中阻塞。外层原生 worker 使用 30--300 秒有界超时，默认 120 秒；超时先按精确 worker PID 终止进程树，再复查本次启动窗口中新出现的 Visio 进程，记录 `timeout_cleanup_passed` 与被终止 PID，最后写入 `FAILED` 报告并触发回退，不得无限等待或留下孤立后台实例。若同期出现多个无法确定归属的新 Visio 进程，脚本不擅自终止它们，并将清理状态标为失败。遇到未实现的 `groups` 会 fail-closed，不能以带警告的 `PASSED` 忽略；复杂分组、泳道或特殊网络符号应回退 FigureSpec/SVG，或在原生文件中人工排版后重新导出、清理元数据并重做全部检查。图中语义不得超出原始规范。

元数据清理后会扫描 VSDX 的 core/app/custom 属性，并检查全部 `.xml`、`.rels`、`.txt` 成员中的 Windows 盘符路径、`file://`、UNC、`/Users` 和 `/home` 绝对路径；发现任一命中即不签发匿名通过状态。报告将基础字号与缩放后的有效最小字号分开，前者对账 `visual_grammar.base_font_pt`，后者必须不低于 7 pt。

默认使用 `cumcm-mechanism`：浅灰蓝节点、细线、短标签、无阴影/渐变和单一主阅读路径。节点可在 FigureSpec 中显式覆盖语义颜色，但同一实体跨图必须保持一致。

## MATLAB 论文图

素材库式的鲜明配色、透明填充、箱线、热图、多面板和哑铃图可使用内置 MATLAB 后端：

```powershell
matlab -batch "addpath('C:/Users/ASUS/.codex/skills/mm-visualization-delivery/scripts'); matlab_plot_from_spec('figures/specs/q1.json','figures/matlab');"
```

默认读取 CSV + JSON，不生成随机数据，不在绘图阶段拟合、计算相关系数或构造误差。支持 `cumcm-clean`、`cumcm-highlight`、`cumcm-data-dense` 和 `cumcm-vivid`。成功产物：

- `<figure_id>.fig`：MATLAB 可编辑图；
- `<figure_id>.pdf`：XeLaTeX 矢量图；
- `<figure_id>.png`：300 dpi 预览；
- `<figure_id>.matlab-report.json`：MATLAB 版本、来源/spec/输出 SHA-256 和重开状态。

`.fig` 必须由 MATLAB 重新打开；PDF 使用固定纸张尺寸导出，报告记录真实的字体、有效最小字号、最终宽度、线宽、透明效果和 `render_contract`。`FIGURE_INTENT.renderer_spec` 必须绑定输入 JSON 的 SHA-256，意图中不得把真实折线改写成面积图或伪造变量/变换。报告中的 `RUNTIME_VERIFIED` 不等于结果声明通过。

## 确定性 SVG 回退

```powershell
py -3.12 scripts/figure_renderer.py validate figures/specs/model_flow.json
py -3.12 scripts/figure_renderer.py render figures/specs/model_flow.json --output figures/model_flow.svg
py -3.12 scripts/render_and_reopen_check.py figures/model_flow.svg figures/model_flow.pdf --source figures/specs/model_flow.json --output figures/model_flow.runtime-report.json
```

将 SVG 转为 PDF 后用于 XeLaTeX。转换工具不可用时保留 SVG 和规范，明确记录 PDF 回退尚未完成，不能伪造 PDF。

## 失败规则

- Origin 不可用或保存/重开失败：不得生成或声称 `.opju`；改用 Python/Matplotlib 并保留脚本、源数据和 PDF。
- Visio 不可用或保存/重开失败：不得生成或声称 `.vsdx`；改用 FigureSpec/SVG 或 Mermaid。
- PDF 导出失败但原生文件成功：交付状态仍为未完成，因为默认 LaTeX 链需要 PDF。
- 原生应用计算出的任何新数值不能凭图读取后写入论文；必须导出数值并进入结果验证。
- 最终 `FIGURE_INTENT` 必须登记 `backend_report` 与 `backend_report_sha256`。原生后端报告需证明保存、导出、清理后哈希和原生重开；FigureSpec/SVG/Mermaid 回退使用 `render_and_reopen_check.py --source <规范文件> --output <报告>` 生成来源哈希、输出哈希与重开报告。多个来源重复传入 `--source`，报告必须覆盖每个声明来源。
- GitHub、ARIS、云端图片模型、网络字体和远程 shim 都不是运行条件。
