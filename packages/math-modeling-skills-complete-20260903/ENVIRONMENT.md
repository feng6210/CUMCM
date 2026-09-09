# 运行环境说明

## Python

建议使用 Python 3.10 或更高版本。安装包内脚本所需依赖：

    py -m pip install -r requirements.txt

其中：

- `PyYAML` 用于 YAML 计划、策略与配置；
- `jsonschema` 用于 `PROBLEM_SEMANTICS`、跨 Skill envelope、`BENCHMARK_CHALLENGE`、`FIGURE_PLAN`、`COMPETITION_POLICY` 等版本化机器契约的结构校验；
- `numpy`、`pandas`、`scipy`、`scikit-learn`、`networkx` 用于模型和验证脚本；
- `matplotlib` 与 `Pillow` 用于可复现绘图和栅格重开检查；
- `pypdf` 用于最终论文 PDF 的确定性页数读取和全页视觉范围绑定；
- `pypdfium2` 用于定量图渲染器的 PDF 真正重开/栅格化检查，避免“文件存在”被误当成可用 PDF；
- `openpyxl` 用于 Excel 数据读写。

安装后可运行：

    .\check_environment.ps1

该检查只读取环境，不安装或启动商业软件。schema 校验只证明字段/类型/枚举闭合，不证明数学语义或结果正确。

## 中文 LaTeX 与 PDF

完整论文编译链需要：

- XeLaTeX；
- latexmk；
- BibTeX，以及模板使用的 `gbt7714-numerical` 样式；
- Poppler 的 `pdftoppm`，用于把整篇编译后的论文 PDF 渲染成页面图做视觉检查。

`pypdf` 用于独立读取最终论文页数；定量图 renderer 的单图 PDF reopen 由 Python 依赖 `pypdfium2` 完成；整篇论文页面级视觉检查仍可使用 Poppler。三者职责不同，不能因安装了其中一个就宣称其他层检查已完成。

可使用 MiKTeX 或 TeX Live 提供前三项。若缺少正式模板、字体或宏包，`mm-paper-compile` 会在编译报告中明确报告，不会把缺失依赖静默解释为论文通过。

## TikZ / Origin / Visio

原生示意图模板另需 TikZ、standalone、ctex、amsmath 与 XeLaTeX。当前两张示例使用 Windows 中文字体；其他系统需要指定实际安装的中文字体再编译。MiKTeX 可加 `--disable-installer` 避免后台安装等待，TeX Live 不使用该参数。PGFPlots 是解析/数值坐标图的可选依赖。已有 PDF/PNG 可离线查看，修改源码后须重新编译、检查日志和重开成图。

Origin 和 Microsoft Visio 是可选的、需要单独许可的桌面软件，因此不能随本包分发。安装后，绘图 Skill 可优先使用它们的原生后端并同时保留可编辑源文件与 LaTeX 用 PDF。没有安装时，量化图回退到 Python/Matplotlib，流程与机制图回退到 TikZ 或 SVG/FigureSpec；不得伪造 `.opju` 或 `.vsdx`。

## 离线边界与正式竞赛策略

Skills、模板、schema、策略模板、脚本和回退绘图链均包含在包内。运行不要求访问远端仓库，也不要求 SSH、GPU、实验跟踪服务或会议论文模板。

`task_mode=live_contest` 时，联网、AI、外部论文和公开答案/benchmark 是否允许由 `COMPETITION_POLICY.yaml` 决定；关键权限未知时 fail-closed。该策略本身可离线填写和校验，不要求联网才能运行。
