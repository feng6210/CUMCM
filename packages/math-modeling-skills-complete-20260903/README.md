# 数学建模 Skills 完整包

这是可离线安装的数学建模 Skill 包，共 22 个 Skills。默认面向中文 CUMCM 任务，也可用于一般建模、课程项目和研究型分析。

## 默认行为

安装后总控默认采用精简闭环：

`读题与关键语义 → 主模型 → 求解 → 必要验证 → 最终产物`

普通任务不会为了流程本身强制生成大量 JSON/YAML、固定三路线方案、外部 benchmark、多 seed 或多 Agent 审计。

只有长流程协作、跨会话恢复、live contest 规则边界、严格复现或用户明确要求 provenance-bound competition-ready 审计时，才升级到结构化状态机或 strict audit。

## 包含内容

- 总控、问题拆解、变量假设、模型选择与创新设计；
- 优化、评价、预测、机理、图网络、仿真、统计、聚类、信号/图像/轨迹等专业模型；
- 数据 EDA、约束重算、敏感性/稳健性、数值与统计验证；
- 中文 CUMCM 论文结构、摘要、审稿、XeLaTeX 编译与 PDF 检查；
- 可追溯图表、三维图、热力矩阵、TikZ/SVG/Visio 与 Python 回退；
- 可选的版本化 schema、workflow state、system benchmark 与严格提交审计。

## 执行档位

### `standard`

默认模式。只生成后续真正会使用的中间信息，适合绝大多数建模任务。

### `structured`

适合多人协作、多问耦合、多版本代码和结果管理。可以使用：

- `workflow_state.json`
- `PROBLEM_SEMANTICS.yaml`
- `RUN_MANIFEST.json`
- 跨 Skill envelope
- 版本化 schema

这些工件不是普通任务的强制要求。

### `strict_submission_audit`

仅在明确要求 provenance-bound competition-ready 审计时启用。该模式使用四路 fresh-subagent 审查、视觉绑定、submission digest 和 `final_delivery_check.py --competition-ready`。

普通完整论文走 `formal_delivery`：完整正文、真实结果、图表、引用、编译和视觉检查；不自动要求 strict audit。

## 安装

在 PowerShell 中进入本目录：

```powershell
py -m pip install -r requirements.txt
.\check_environment.ps1
.\install.ps1 -DryRun
.\install.ps1
```

默认安装到当前用户的 `.codex\skills`。若目标目录已有同名 Skill，使用：

```powershell
.\install.ps1 -ReplaceExisting
```

覆盖前会备份同名目录，并在安装失败时尝试回滚。也可以通过 `-Destination` 指定其他 Skills 根目录。

## 环境与可选后端

运行时不依赖 GitHub、SSH、GPU 或远端服务。Origin 和 Microsoft Visio 为可选外部软件；没有原生后端时使用 Python/Matplotlib、SVG、FigureSpec 或 TikZ 回退。

论文链默认使用 XeLaTeX；缺少编译器时应如实报告后端不可用，不把未编译源文件声称为已验证 PDF。

## 契约与审计

结构化任务可使用 `schemas/` 中的机器契约，例如：

```powershell
python skills\math-modeling-orchestrator\scripts\validate_contract.py `
  --schema schemas\problem_semantics.schema.json `
  --input PROBLEM_SEMANTICS.yaml
```

schema PASS 只说明字段/类型/枚举符合约定，不证明题意、模型、结果或论文声明正确。

## 校验材料

正式发布 ZIP 会重新生成：

- `VALIDATION_REPORT.json`
- `PACKAGE_MANIFEST.json`
- `SHA256SUMS.txt`

同时包含：

- `LICENSE`
- `THIRD_PARTY_NOTICES.md`
- `requirements.txt`
- `ENVIRONMENT.md`
- `check_environment.ps1`
- `skills/`
- `schemas/`

仓库源码中的历史 release metadata 不应被当作当前发行认证；正式 ZIP 由发布工作流从同一通过验证的 source SHA 重新生成 metadata。

## License

本离线包主体采用 MIT License，见 `LICENSE`。第三方派生与方法审阅来源见 `THIRD_PARTY_NOTICES.md`，ARIS 的完整 MIT 文本也保留在包内对应 references 目录中。

## 设计原则

- 只生成会被使用的工件；
- 高风险语义先解决，低风险细节不阻断推进；
- 复杂度必须解决一个具体缺陷；
- 验证与声明强度匹配；
- 图表按读者任务决定，不设固定数量；
- 工程审计与竞赛正文分离；
- 失败、未验证结果和能力缺口必须明确披露。
