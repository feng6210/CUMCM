# CUMCM Mathematical Modeling Skills

[![Release](https://img.shields.io/github/v/release/feng6210/CUMCM)](https://github.com/feng6210/CUMCM/releases/latest)
[![CI](https://github.com/feng6210/CUMCM/actions/workflows/skill-regression.yml/badge.svg)](https://github.com/feng6210/CUMCM/actions/workflows/skill-regression.yml)
[![License](https://img.shields.io/github/license/feng6210/CUMCM)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-informational)](packages/math-modeling-skills-complete-20260903/requirements.txt)

面向 **CUMCM / 中文数学建模** 的 22 个可离线安装 Agent Skills，覆盖读题、建模、求解、验证、可视化、LaTeX 论文写作和最终交付。

> A 22-skill agent toolkit for mathematical modeling: problem decomposition, modeling, numerical solving, validation, scientific visualization, CUMCM LaTeX writing, and delivery.

当前稳定版：**v1.0.0** · [下载 Release](https://github.com/feng6210/CUMCM/releases/latest)

## 为什么做这个项目

很多“全流程数模 Agent”把流程复杂度当成严谨性：先生成大量 JSON/YAML，再固定三条路线、固定图数、固定多 seed、固定审计。实际比赛里，这通常会增加时间成本，却不一定提高模型质量。

本项目采用相反的原则：

- **默认最短可靠闭环**：先把题意、模型、结果和必要验证做对；
- **复杂度按风险升级**：只有真正需要时才启用状态机、schema、benchmark 或多 Agent 审计；
- **论文叙事与工程审计分离**：正文服务评委阅读，哈希/运行谱系留在支撑材料；
- **图表服务结论**：不设“每问至少 N 张图”，结果图必须绑定真实数据；
- **不把复杂模型包装成创新**：模型升级必须解决一个具体缺陷。

默认工作流：

```text
读题与关键语义 → 主模型 → 求解 → 必要验证 → 图表 / 论文 / 最终产物
```

## 快速开始

### 方式 A：直接使用正式 Release

推荐普通用户直接下载最新正式包：

**[CUMCM Skills Releases](https://github.com/feng6210/CUMCM/releases/latest)**

正式 Release 同时提供：

- `CUMCM-Skills-v*.zip`
- `VALIDATION_REPORT.json`
- `package-build-report.json`
- `RELEASE_SHA256SUMS.txt`

### 方式 B：从源码安装（Windows / PowerShell）

```powershell
git clone https://github.com/feng6210/CUMCM.git
cd CUMCM\packages\math-modeling-skills-complete-20260903

py -m pip install -r requirements.txt
.\check_environment.ps1
.\install.ps1 -DryRun
.\install.ps1 -ReplaceExisting
```

默认安装到当前用户的 `.codex\skills`。安装器会在覆盖已有同名 Skill 前进行备份，并在失败时尝试回滚。

### macOS / Linux / 其他 Agent 环境

当前自动安装脚本主要针对 PowerShell/Windows。其他平台可以：

1. 安装 `requirements.txt` 中的 Python 依赖；
2. 将 `packages/math-modeling-skills-complete-20260903/skills/` 下需要的 Skill 目录复制到目标 Agent 的 Skills 目录；
3. 保留每个 Skill 内的 `SKILL.md`、`agents/`、`references/` 和 `scripts/` 相对结构。

不同 Agent 平台的 Skill 发现机制并不完全一致，因此“目录可复用”不等于所有平台都保证即插即用。

## 怎么使用

安装后可以直接用自然语言指定任务。典型用法：

```text
分析这道数模题，默认 standard 模式，先把每一问的数学对象和约束讲清楚，再建模求解。
```

```text
根据已有代码和结果完善成完整 CUMCM 论文，做必要的数值核验、图表和 XeLaTeX 交付，不启用 strict audit。
```

```text
对最终参赛包执行 strict_submission_audit，检查数字、图表、论文、支撑材料和 provenance 是否一致。
```

如果只需要某一类能力，也可以直接调用专业 Skill，例如预测、优化、统计推断、图网络、仿真或可视化。

## 三种执行档位

| 档位 | 适用场景 | 默认行为 |
|---|---|---|
| `standard` | 大多数赛题、训练题、课程项目、论文迭代 | 最短可靠闭环，只生成真正需要的工件 |
| `structured` | 多问耦合、多人/多 Agent、跨会话、多版本结果 | 可启用 workflow state、schema、manifest 和机器化交接 |
| `strict_submission_audit` | 明确要求 provenance-bound / competition-ready 终审 | 四路 fresh-subagent、hash binding、视觉绑定和严格交付门 |

普通“完整论文 / 最终 PDF”属于 `formal_delivery`，**不会自动进入** `strict_submission_audit`。

## 22 个 Skills

### 总控与问题建模

- `math-modeling-orchestrator`
- `mm-problem-decomposer`
- `mm-variable-assumption-builder`
- `mm-model-selector`
- `mm-model-innovation-designer`
- `mm-data-eda-cleaning`

### 专业模型

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

### 论文、图表与交付

- `mm-visualization-delivery`
- `mm-paper-structure-writer`
- `mm-abstract-polisher`
- `mm-paper-reviewer`
- `mm-paper-compile`
- `mm-contest-operations-planner`

## 设计重点

### 1. 题意优先于算法

对目标函数、时间口径、资源复用、多目标聚合、决策信息集等高风险语义先做检查。只有会改变模型结构或结论的歧义才阻断推进。

### 2. 验证强度与声明强度匹配

不是所有问题都需要多 seed、敏感性分析、消融或外部 benchmark。确定性优化、闭式解、统计预测和随机仿真采用不同验证逻辑。

### 3. 图表按读者任务生成

结果图绑定真实数据；几何和机理示意图优先使用可编辑 TikZ/SVG/Visio 或确定性绘制。Origin 和 Microsoft Visio 是可选后端，没有时回退到 Python/Matplotlib、SVG 或 TikZ。

### 4. 完整论文不等于重型审计

正常完整论文要求真实结果、完整正文、引用、图表、XeLaTeX 编译与最终 PDF 检查；只有显式要求严格 provenance 时才进入 competition-ready hard gate。

## 仓库结构

```text
CUMCM/
├─ packages/math-modeling-skills-complete-20260903/  # 当前可安装源码包
│  ├─ skills/                                        # 22 Skills
│  ├─ schemas/                                       # 可选机器契约
│  ├─ LICENSE
│  └─ THIRD_PARTY_NOTICES.md
├─ benchmarks/                                       # 系统行为回归案例
├─ tests/                                            # workflow / delivery / visualization 回归
├─ tools/                                            # deterministic release builder
├─ .github/workflows/                                # CI 与正式发布工作流
├─ CHANGELOG.md
├─ RELEASE_POLICY.md
├─ THIRD_PARTY_NOTICES.md
└─ LICENSE
```

包路径中的 `20260903` 为历史兼容目录名，当前发布版本以 Git tag / GitHub Release 为准，而不是以目录名判断版本。

## CI、验证与正式发布

Pull Request 的 `skill-regression` 会检查：

- workflow / schema 回归；
- system benchmark spec；
- 可视化确定性回归；
- package structure；
- deterministic preview ZIP。

正式发布使用 `release-package` workflow，在同一 source SHA 上重新执行发布范围检查，生成新的 validation report、manifest、SHA256SUMS 和 ZIP，再创建 GitHub Release。

`CI PASS`、schema PASS 或 benchmark PASS **只代表对应软件/契约检查通过**，不代表任意赛题数学结论正确，也不代表能够保证获奖。

### 校验下载包

Linux / macOS：

```bash
sha256sum CUMCM-Skills-v1.0.0.zip
```

Windows PowerShell：

```powershell
Get-FileHash .\CUMCM-Skills-v1.0.0.zip -Algorithm SHA256
```

然后与 Release 中的 `RELEASE_SHA256SUMS.txt` 对照。

## 这个项目不是什么

- 不是历年赛题答案库；
- 不承诺国奖、一等奖或任何比赛结果；
- 不会自动把 Transformer、PINN、深度学习等复杂模型当作“创新”；
- 不应该用于绕过 live contest 的 AI、联网或外部资料规则；
- 不允许用伪造结果、伪造引用或作者自审冒充独立审查。

## 贡献

欢迎提交 bug、模型覆盖缺口、回归案例、论文交付问题和可复现改进。提交前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

对于新增 Skill 或大范围流程改动，优先保持一个原则：**不要让少数严格场景重新拖慢默认 `standard` 路径。**

## License

仓库主体采用 [MIT License](LICENSE)。第三方派生、审阅来源与归属见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

---

如果你主要是为了 CUMCM 正式比赛使用，建议从 `standard` 开始；只有任务复杂度或交付风险真正需要时，再升级到 `structured` 或 `strict_submission_audit`。
