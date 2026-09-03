# 运行环境说明

## Python

建议使用 Python 3.10 或更高版本。安装包内脚本所需依赖：

    py -m pip install -r requirements.txt

其中 `PyYAML` 用于 YAML 计划与配置，`numpy`、`pandas`、`scipy`、`scikit-learn`、`networkx` 用于模型和验证脚本，`matplotlib` 用于可复现绘图，`openpyxl` 用于 Excel 数据读写。

安装后可运行：

    .\check_environment.ps1

该检查只读取环境，不安装或启动商业软件。

## 中文 LaTeX 与 PDF

完整论文编译链需要：

- XeLaTeX；
- latexmk；
- BibTeX，以及模板使用的 `gbt7714-numerical` 样式；
- Poppler 的 `pdftoppm`，用于把编译后的 PDF 渲染成页面图做视觉检查。

可使用 MiKTeX 或 TeX Live 提供前三项。若缺少正式模板、字体或宏包，`mm-paper-compile` 会在编译报告中明确报告，不会把缺失依赖静默解释为论文通过。

## Origin 与 Visio

Origin 和 Microsoft Visio 是可选的、需要单独许可的桌面软件，因此不能随本包分发。安装后，绘图 Skill 可优先使用它们的原生后端并同时保留可编辑源文件与 LaTeX 用 PDF。没有安装时，量化图回退到 Python/Matplotlib，流程与机制图回退到 SVG/FigureSpec；不得伪造 `.opju` 或 `.vsdx`。

## 离线边界

Skills、模板、脚本和回退绘图链均包含在包内。运行不要求访问远端仓库，也不要求 SSH、GPU、实验跟踪服务或会议论文模板。

