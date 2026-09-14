# CUMCM 数学建模 Skills

面向中文数学建模任务的一套可离线安装 Skill 集合，覆盖读题、建模、求解、验证、可视化、CUMCM LaTeX 写作与交付。

本仓库当前包含 22 个 Skills。设计目标不是堆叠流程，而是让 Agent 在保证题意、数值和交付可靠性的前提下，尽量走最短路径。

## 核心设计

### 1. 默认精简执行

普通任务使用 `standard`：

`读题与关键语义 → 主模型 → 求解 → 必要验证 → 用户需要的最终产物`

不会因为流程本身强制生成大量 JSON/YAML、三路线方案、外部 benchmark、多 seed 或多 Agent 审计。

### 2. 按风险升级

只有在以下场景才增加流程：

- 高风险题意歧义会改变模型或结论；
- 多人/多 Agent 协作需要机器化交接；
- 多版本代码和结果需要跨会话恢复；
- live contest 的 AI/联网/外部资料权限需要约束；
- 用户明确要求严格复现、审计或 competition-ready provenance。

### 3. 论文正文与工程审计分离

竞赛论文默认使用 `competition_compact`：正文只保留问题、模型、结果、必要验证和结论。哈希、gate 名、失败运行谱系等工程细节不进入正文，除非它们本身影响科学结论。

### 4. 图表按读者任务生成

不设“每问至少 N 张图”。结果图绑定真实数据；几何/机理示意图优先使用可编辑 TikZ/SVG/Visio 或确定性绘制方案。

## 执行档位

- `standard`：默认。适用于大多数赛题分析、课程任务、训练和论文迭代。
- `structured`：适用于长流程、多问耦合、多人协作和跨会话恢复；可启用状态机与机器契约。
- `strict_submission_audit`：仅在用户明确要求 provenance-bound competition-ready 审计时启用四路 fresh-subagent、hash binding 和 `--competition-ready` 硬门。

普通“完整论文/最终 PDF”属于 `formal_delivery`，不自动进入 strict audit。

## Skills

核心调度与建模：

- `math-modeling-orchestrator`
- `mm-problem-decomposer`
- `mm-variable-assumption-builder`
- `mm-model-selector`
- `mm-model-innovation-designer`
- `mm-data-eda-cleaning`

专业模型：

- `mm-optimization-models`
- `mm-evaluation-models`
- `mm-prediction-models`
- `mm-dynamic-mechanism-models`
- `mm-graph-network-models`
- `mm-simulation-models`
- `mm-statistical-inference`
- `mm-classification-clustering`
- `mm-signal-image-trajectory`
- `mm-uncertainty-validation`

论文与交付：

- `mm-visualization-delivery`
- `mm-paper-structure-writer`
- `mm-abstract-polisher`
- `mm-paper-reviewer`
- `mm-paper-compile`
- `mm-contest-operations-planner`

## 安装

```powershell
cd packages\math-modeling-skills-complete-20260903
py -m pip install -r requirements.txt
.\check_environment.ps1
.\install.ps1 -DryRun
.\install.ps1 -ReplaceExisting
```

默认安装到当前用户的 `.codex\skills`。Origin 和 Microsoft Visio 为可选外部软件；没有原生后端时使用 Python/Matplotlib、SVG 或 TikZ 回退。

## 仓库结构

- `packages/math-modeling-skills-complete-20260903/`：当前可安装源码包；
- `benchmarks/`：系统行为回归案例；
- `tests/`：状态、契约、论文交付与可视化回归；
- `tools/`：确定性发布包构建工具；
- `dist/`：历史正式打包快照，不保证与每个源码提交逐字同步；
- `CHANGELOG.md`：版本级变更记录；
- `RELEASE_POLICY.md`：发布与快照同步规则；
- `THIRD_PARTY_NOTICES.md`：第三方来源和许可证归属。

## 发布与验证

Pull Request 会运行 `skill-regression`：

- workflow / schema 回归；
- system benchmark spec 校验；
- 可视化确定性回归；
- 包结构检查；
- deterministic preview ZIP 构建。

正式发布使用 `.github/workflows/release-package.yml`。该工作流会在同一源提交上重新运行发布范围测试，生成新的 `VALIDATION_REPORT.json`，再由 `tools/build_release_package.py` 生成带新 manifest/SHA256SUMS 的正式 ZIP。只有显式将 `publish_release` 设为 `true` 时才创建 GitHub Release 和对应 tag；若同名 Release 已存在则 fail-closed，不覆盖旧版本。

CI、schema 或 benchmark PASS 只代表对应检查通过，不代表数学结论正确，也不代表获奖水平。发布包中的 validation report 明确限制在软件/包级验证范围。

## License

本仓库主体采用 [MIT License](LICENSE)。第三方派生或审阅来源的归属见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 以及包内保留的许可证文件。

## 使用边界

- 不伪造结果、引用或独立审查；
- 不把复杂模型本身当作创新；
- 不把内部随机稳定性当作全局最优证明；
- 不在 live contest 中绕过赛事规则；
- 用户正式模板优先于内置模板；
- 论文、图表和结论必须能追溯到真实模型、代码或数据。
