# 数学建模 Skills 完整包

这是当前活动版本的离线完整包，共包含 22 个数学建模 Skills。默认论文语言为中文，默认交付为 CUMCM 结构的 LaTeX/XeLaTeX 论文。绘图层同步了全量样式索引、22 类基础图型适配器，以及 2026-09-07 增补的通用几何/物理示意图工作流和可编辑 TikZ 模板。

## 内容

- 总控、竞赛运营、问题拆解、变量假设与模型选择；
- 优化、评价、预测、机理、图网络、仿真、统计、聚类、信号图像轨迹等专业模型；
- 题意语义锁定、最小正确基线、创新路线、实验计划、外部/异源 challenge、结果到声明和独立验证；
- `schemas/` 的版本化机器契约：`PROBLEM_SEMANTICS`、跨 Skill envelope、`BENCHMARK_CHALLENGE`、`FIGURE_PLAN`、`COMPETITION_POLICY`；
- live contest 的 `COMPETITION_POLICY.yaml` 权限门：AI、联网、外部论文、公开答案/benchmark 未明确允许时 fail-closed；
- 中文 CUMCM 论文结构、摘要、审稿和 XeLaTeX 编译；
- 可追溯图表、三维图、热力矩阵、Origin/Visio 原生后端与 Python/SVG/TikZ 回退；
- `mm-visualization-delivery` 的全量本地样式检索：145 文件、68 张图片变体、50 个教程命名槽位、37 份源码审计，以及 22 类不拟合/不偷偷计算统计量的基础渲染器；
- ARIS 方法归属与 MIT 许可说明。

2026-09-07 增补的两张已确认 TikZ 模板位于 `skills/mm-visualization-delivery/assets/tikz-schematics/`。同时保留矢量 PDF、PNG 和历史审查哈希；新图必须重新核对模型语义与最终排版，不能继承样例的通过状态。来源目录仅作阅读范围记录，不随包分发原论文，也不是运行依赖。

运行时不依赖 GitHub、ARIS 仓库、SSH、GPU、W&B 或机器学习会议模板。Origin/Visio 属于可选外部软件。训练/研发时可使用仓库根目录 `benchmarks/` 做系统级回归；离线安装包本身不要求这些 benchmark 文件才能运行。

## 安装

在 PowerShell 中进入本目录后运行：

    py -m pip install -r requirements.txt
    .\check_environment.ps1
    .\install.ps1 -DryRun
    .\install.ps1

默认安装到当前用户的 `.codex\skills`。若目标目录已经存在同名 Skill，安装器会停止；需要用本包覆盖时显式运行：

    .\install.ps1 -ReplaceExisting

覆盖前，安装器会把同名目录移动到目标目录旁的时间戳备份目录，并在失败时尝试回滚。也可以通过 `-Destination` 指定其他 Skills 根目录。

## 契约校验

示例：

    python skills\math-modeling-orchestrator\scripts\validate_contract.py --schema schemas\problem_semantics.schema.json --input PROBLEM_SEMANTICS.yaml

schema 通过只说明字段、类型和枚举边界正确，不证明题意、模型、结果或论文声明正确。

## 校验材料

- `VALIDATION_REPORT.json`：最近一次发布/范围校验结果；
- `PACKAGE_MANIFEST.json`：已打包发布快照的文件、大小和 SHA-256；
- `SHA256SUMS.txt`：便于独立核对的哈希清单；
- `requirements.txt` 与 `ENVIRONMENT.md`：Python、中文 LaTeX、PDF 渲染及可选原生绘图后端说明；
- `check_environment.ps1`：只读环境检查，不安装或启动商业软件；
- `skills\`：实际可安装目录；
- `schemas\`：机器可验证交接契约。

仓库 `main` 可能领先于最近一次提交到 `dist/` 的 ZIP；正式发布时应从同一源提交重新生成 ZIP、manifest 和 SHA256SUMS。`quick_validate` 或 schema PASS 都不代表模型结论、论文声明或外部软件后端已被自动认证。
