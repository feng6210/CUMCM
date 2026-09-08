# CUMCM 数学建模 Skills

本仓库保存当前完整的中文数学建模 Skill 套件。默认工作流覆盖赛题拆解、题意语义锁定、最小正确基线、模型路线审批、数据与实验审计、模型求解、外部/异源挑战、数值验证、Origin/Visio/TikZ/确定性回退绘图、CUMCM 中文 LaTeX 写作、论文冷审查、XeLaTeX 编译和最终交付检查。

## 当前源码与发布包

- **当前源码**：`main` 分支始终作为最新开发/活动版本；
- 解压版：[`packages/math-modeling-skills-complete-20260903`](packages/math-modeling-skills-complete-20260903)
- 已提交 ZIP：[`dist/math-modeling-skills-complete-20260903.zip`](dist/math-modeling-skills-complete-20260903.zip)
- Skill 数量：22
- 2026-09-07 示意图更新：通用几何/物理示意图工作流、两张用户确认的 TikZ 原创模板（受力、分层传热）、源码/矢量 PDF/PNG 与有范围限制的历史审查记录。
- 绘图 Skill：全量本地样式索引（145 文件 / 68 张图片 / 50 个教程槽位）与 22 类基础适配器已同步。
- 已提交 ZIP SHA-256：`39a68401af01c33a863a520a1df2e318904858b8f6145e9bcc6cd1f1594162af`

`dist/` 是**已打包发布快照**，不再假设每个源码提交都会同步改写二进制 ZIP。PR 的 `skill-regression` 会从当前源码重新构建确定性 preview ZIP 并作为 Actions artifact 上传；正式发布时再刷新 `dist/`、manifest 和 SHA256SUMS。这样避免“源码已更新但旧 ZIP 仍被误称为当前源码的逐字镜像”。发布规则见 [`RELEASE_POLICY.md`](RELEASE_POLICY.md)。

## 新增的系统级可靠性层

2026-09-08 论文质量更新（源码）：

- 中文摘要选择性强调、关键词整行粗体，以及可覆盖的内置标题/图表/符号表样式；用户正式模板优先。
- 根据数学对象组织叙事和图后解释；不固定四问、段落数、图数、少色或二维偏好。
- 几何图、隔离受力图与消约束广义作用图区分；示意/流程图默认黑线黑字白底，结果图保留鲜明配色；新增按唯一 LaTeX label 提取完整图注的工具，保留可编辑 TikZ/Visio 路线。
- 同族交叉审查真实角色、修改后证据失效与限定复核；数值比较明确时间窗和聚合口径。
- 编译输出显式另存与锁文件失败报告，避免旧 PDF 冒充本轮产物；新增正反例及可选真实 XeLaTeX 模板回归。

这是对既有阅读和修订经验的通用化，不分发参考论文、题目答案或本地数据，不等于全语料阅读/全后端/全部数学模型验证。使用细则见 [论文可读性与修订](packages/math-modeling-skills-complete-20260903/skills/mm-paper-structure-writer/references/paper_readability_and_revision.md)。

- `packages/.../schemas/`：`PROBLEM_SEMANTICS`、`BENCHMARK_CHALLENGE`、`FIGURE_PLAN`、`COMPETITION_POLICY` 等版本化机器契约；
- `benchmarks/`：整题/系统级行为回归，不只测单个脚本；
- `COMPETITION_POLICY.yaml`：live contest 中先锁 AI、联网、外部论文和公开答案/benchmark 权限；
- 扩展 CI：工作流/契约、可视化回归、包结构与确定性 package preview 分开检查。

## 快速安装

```powershell
cd packages\math-modeling-skills-complete-20260903
py -m pip install -r requirements.txt
.\check_environment.ps1
.\install.ps1 -DryRun
.\install.ps1 -ReplaceExisting
```

安装器默认写入当前用户的 `.codex\skills`。覆盖模式会先备份同名目录，并在安装失败时尝试回滚。完整依赖、外部软件边界、逐文件哈希和验证结果见发布目录中的 `ENVIRONMENT.md`、`PACKAGE_MANIFEST.json`、`SHA256SUMS.txt` 与 `VALIDATION_REPORT.json`。

Origin 和 Microsoft Visio 是可选的外部授权软件，不随仓库分发；没有原生后端时，绘图工作流使用 Python/Matplotlib 与 SVG/FigureSpec/TikZ 回退。Skills 本身不依赖远端仓库即可运行。

几何、受力、边界与空间关系示意图优先使用可编辑 TikZ，解析或数值坐标可使用 PGFPlots；流程图选择原生节点连线或 TikZ。用户要求“画出来”时不改用生成式图片。新增模板是可扩展起点，不是题型白名单；Visio 任意物理图元支持和全目录论文阅读均不在现有验证声明内。
