# 数学建模 Skills 完整包

这是当前活动版本的离线完整包，共包含 22 个数学建模 Skills。默认论文语言为中文，默认交付为 CUMCM 结构的 LaTeX/XeLaTeX 论文。

## 内容

- 总控、竞赛运营、问题拆解、变量假设与模型选择；
- 优化、评价、预测、机理、图网络、仿真、统计、聚类、信号图像轨迹等专业模型；
- 创新路线、实验计划、结果到声明、模型专属验证与独立审查；
- 中文 CUMCM 论文结构、摘要、审稿和 XeLaTeX 编译；
- 可追溯图表、三维图、热力矩阵、Origin/Visio 原生后端与 Python/SVG 回退；
- ARIS 方法归属与 MIT 许可说明。

运行时不依赖 GitHub、ARIS 仓库、SSH、GPU、W&B 或机器学习会议模板。包内不包含 AI 使用合规声明、日志或论文占位符。

## 安装

在 PowerShell 中进入本目录后运行：

    py -m pip install -r requirements.txt
    .\check_environment.ps1
    .\install.ps1 -DryRun
    .\install.ps1

默认安装到当前用户的 `.codex\skills`。若目标目录已经存在同名 Skill，安装器会停止；需要用本包覆盖时显式运行：

    .\install.ps1 -ReplaceExisting

覆盖前，安装器会把同名目录移动到目标目录旁的时间戳备份目录，并在失败时尝试回滚。也可以通过 `-Destination` 指定其他 Skills 根目录。

## 校验材料

- `VALIDATION_REPORT.json`：22 个 Skill 的结构验证结果；
- `PACKAGE_MANIFEST.json`：包内文件、大小和 SHA-256；
- `SHA256SUMS.txt`：便于独立核对的哈希清单；
- `requirements.txt` 与 `ENVIRONMENT.md`：Python、中文 LaTeX、PDF 渲染及可选原生绘图后端说明；
- `check_environment.ps1`：只读环境检查，不安装或启动商业软件；
- `skills\`：实际可安装目录。

`quick_validate` 通过只表示 Skill 目录、名称和 YAML 前置元数据结构有效，不代表模型结论、论文声明或外部软件后端已被自动认证。
