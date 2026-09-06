# CUMCM 数学建模 Skills

本仓库保存当前完整的中文数学建模 Skill 套件。默认工作流覆盖赛题拆解、模型路线审批、数据与实验审计、模型求解、数值验证、Origin/Visio 或确定性回退绘图、CUMCM 中文 LaTeX 写作、论文冷审查、XeLaTeX 编译和最终交付检查。

## 当前发布

- 解压版：[`packages/math-modeling-skills-complete-20260903`](packages/math-modeling-skills-complete-20260903)
- ZIP：[`dist/math-modeling-skills-complete-20260903.zip`](dist/math-modeling-skills-complete-20260903.zip)
- Skill 数量：22
- 绘图 Skill：全量本地样式索引（145 文件 / 68 张图片 / 50 个教程槽位）与 22 类基础适配器已同步；
- ZIP SHA-256：`5d7547644d3ee0294178b79fadc0e4725ed101d5643f85d24f032577b1120ec1`

## 快速安装

```powershell
cd packages\math-modeling-skills-complete-20260903
py -m pip install -r requirements.txt
.\check_environment.ps1
.\install.ps1 -DryRun
.\install.ps1 -ReplaceExisting
```

安装器默认写入当前用户的 `.codex\skills`。覆盖模式会先备份同名目录，并在安装失败时尝试回滚。完整依赖、外部软件边界、逐文件哈希和验证结果见发布目录中的 `ENVIRONMENT.md`、`PACKAGE_MANIFEST.json`、`SHA256SUMS.txt` 与 `VALIDATION_REPORT.json`。

Origin 和 Microsoft Visio 是可选的外部授权软件，不随仓库分发；没有原生后端时，绘图工作流使用 Python/Matplotlib 与 SVG/FigureSpec 回退。Skills 本身不依赖远端仓库即可运行。
