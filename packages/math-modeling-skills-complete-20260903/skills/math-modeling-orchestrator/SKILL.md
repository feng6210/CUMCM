---
name: math-modeling-orchestrator
description: Orchestrate mathematical-modeling work from contest-policy and problem semantics through minimum baselines, approved solving, adversarial validation, CUMCM Chinese LaTeX writing, figure planning/rendering, and delivery checks. Use for multi-stage modeling tasks; do not fabricate results, silently resolve objective ambiguity, bypass contest rules, or let a solver self-certify strong claims.
---

# 数学建模：总控调度

## Purpose

协调数模任务的赛制权限、题意语义、拆题、最小正确基线、模型路线、实验与验证、中文数模论文、图表和交付。总控维护唯一的 `workflow_state.json`，并把“能否使用某类外部工具/资料”“数学问题是否定义正确”“候选解是否好”“数值是否可信”“论文如何表达”分成不同责任层。

默认论文模式是 `cumcm-2026-electronic`：中文、LaTeX、XeLaTeX、摘要专页、无目录、按分问写作。用户提供正式模板时优先使用该模板。

## Two reporting profiles

- `competition_compact`：training/live_contest/coursework 的 CUMCM 正文默认画像。正文只保留理解模型、策略、关键结果和必要检验所需内容；哈希、gate 名、版本谱系、失败运行明细和后端审计默认进入支撑材料/附录，除非它们本身改变科学结论。
- `research_audit`：research/engineering 等模式。可完整保留实验谱系、失败证据、工件哈希、验证门和复现材料。

两种画像使用同一机器证据，区别只在**正文暴露多少工程审计信息**，不能通过精简叙事掩盖失败。

## Required workflow

1. 识别 `task_mode`、`deliverable_mode` 与 `reporting_profile`，登记题目、数据、现有代码、允许使用的外部资料和交付要求。若 `task_mode=live_contest`，在任何联网、AI、外部论文或公开答案/benchmark 调用前，先建立并校验 `COMPETITION_POLICY.yaml`；协议见 [正式竞赛权限](references/competition_policy.md)。关键权限未知时 fail-closed，不自行推定允许。
2. 调用 `mm-problem-decomposer`，形成 `QUESTION_DECOMPOSITION.json`；随后调用 `mm-variable-assumption-builder` 完成 `PROBLEM_SEMANTICS.yaml`。必须先审查目标函数、计时口径、资源复用、多目标聚合和决策信息集。存在会改变解结构的高风险歧义时进入 `SEMANTICS_REVIEW`，不得开始主求解。协议见 [题意语义与外部挑战](references/problem_semantics_and_benchmark_protocol.md)。进入模型规划前，推荐用 `schemas/problem_semantics.schema.json` 做机器结构校验；schema PASS 不等于语义 PASS。
3. 语义锁定后，数据任务调用 `mm-data-eda-cleaning`；无数据机理题列参数来源、量纲、可辨识性和边界情形。
4. 在复杂模型之前建立**最小正确基线**：解析/网格/枚举/朴素预测/小规模精确解/人工构造边界案例等。基线首先用于校验 evaluator、目标方向、单位和约束，不是为了凑对比图。基线不能复算时禁止升级复杂模型；确实不适用时也必须有显式 `not_applicable` 记录并经过 `BASELINE_READY`。
5. 调用 `mm-model-selector`，基于问题结构、数据、连续/离散性质、可解释性和验证成本选择候选模型；再由 `mm-model-innovation-designer` 给出路线 A/B/C、对照、实验计划、失败回退和成本。复杂度升级必须明确回答“基线具体哪里不够”。
6. 向用户汇报每问语义口径、基线、模型路线、创新机理、验证方法、成本、失败回退和 `MODELING_EXPERIMENT_PLAN.yaml`。主路线进入 `AWAITING_MODEL_APPROVAL`；没有有效 `model_approval` 不得首次进入主 `SOLVING`。
7. 按批准路线调用专业模型 Skill。每个交接遵守 [跨 Skill 交接契约](references/cross_skill_output_contract.md)。Solver 负责候选和求解边界，不拥有“最佳/稳定/鲁棒”等强声明的最终 PASS 权。总控负责把专业 Skill 原生输出规范化为 envelope，不要求下游 Skill 伪造上游事实。
8. 为实际运行创建 `RUN_MANIFEST.json`；保留失败、不可行、超时和不收敛运行。所有候选必须由原始硬约束和原始目标函数重算，而不是只信搜索内核/求解器状态。
9. **外部/异源挑战门**：若用户提供优秀论文、公开可行解、题目样例或其他合法基准，且当前 `COMPETITION_POLICY.yaml` 允许使用，必须把其参数/路线/预测映射进当前 evaluator，生成 `BENCHMARK_CHALLENGE.json`。不能直接拿不同口径的论文数字排大小。外部可行解在同 evaluator 下领先超过预设容差时，当前“最佳/稳定最优”声明自动降级并返回 `SOLVING`。正式竞赛规则不允许外部解时记录 `NOT_ALLOWED_BY_RULES` 和 policy 引用，不绕过规则。
10. 先执行 [证据预检查](scripts/evidence_precheck.py)，再调用 `mm-uncertainty-validation`。验证至少区分：同源重算、数值收敛、统计/随机稳定、情景稳健、异源/外部挑战。多种子收敛到同一平台不能单独证明解盆地覆盖。
11. 将通过验证的结果写入 `RESULTS_TO_CLAIMS.md` 和 `result_evidence_map.json`。文件存在或数字可定位只证明证据存在，不证明结论成立。
12. 只有 `PASS` 或范围明确的 `PARTIAL` 才能进入论文链。先依据 [国奖与优秀论文叙事—图表蒸馏](references/local_corpus/award_paper_narrative_figure_distillation.md) 建立 `NARRATIVE_MAP.yaml`，同时建立 `FIGURE_PLAN.yaml`：先识别“读者在哪里会看不懂”，再决定是否需要场景图、几何/机制图、case 图、时间区间图、结果图或验证图。**不设每问固定图数。** 推荐用 `schemas/figure_plan.schema.json` 做结构校验，再交给 `mm-visualization-delivery` 做更严格的来源/输出/视觉审查。
13. 调用 `mm-paper-structure-writer` 生成竞赛叙事骨架。`competition_compact` 正文优先“问题 → 数学结构 → 方法 → 结果 → 必要验证”；完整 gate 名、hash、旧版本 FAIL 谱系和后端运行日志默认移入支撑材料。`research_audit` 可展开复现实验链。
14. 调用 `mm-visualization-delivery` 时分两步：`figure planning` 已由叙事阶段确定每张图的不可替代读者任务；`figure rendering` 只负责真实数据绑定、视觉语法、原生文件、PDF 和最终尺寸检查。不得用“每问至少 N 张图”驱动渲染。
15. 终稿进入编译前，在平台允许且已获委派权限时自动启动彼此独立的 fresh-agent 审查：数字/结论、题意语义与目标一致性、图表/证据、CUMCM 结构/叙事至少四条审查线。不向审查 Agent 提供预期 PASS 或拟议修复。
16. 若 fresh-agent 不可用，将 `independent_review_status` 设为 `INDEPENDENT_REVIEW_NOT_RUN`，显式报告原因；同一上下文自审只能算同源诊断。P0/P1 修复或结果、目标、图表、正文变化后旧审查标记 stale。
17. 最终完成独立审查汇总、论文数字审计、引用审计、XeLaTeX/PDF、支撑材料和赛制交付检查。

## State and amendments

使用 [workflow_state.py](scripts/workflow_state.py) 创建、显示、转换和批准状态。文字路由指南必须与该脚本同步；若旧文档遗漏 `SEMANTICS_REVIEW / BASELINE_READY / BENCHMARK_CHALLENGE` 等状态，不得按旧文档跳转。

以下变化属于**语义级 amendment**：主目标、多目标聚合方式、时间集合运算、资源计数/复用、核心数据、硬约束、关键物理判据改变。发生时必须使模型批准和全部下游结果 stale，回到语义/模型规划阶段。

模型路线、阈值或创新机制改变时运行 `amend-plan`；结果源文件变更时运行 `mark-stale`。

`FAIL` 不得通过更换论文措辞进入摘要、结论或交付。`PARTIAL` 必须缩小声明范围。缺少输入使用 `BLOCKED_INPUT`；能力未覆盖使用 `BLOCKED_CAPABILITY`。

## Machine-verifiable contracts and system benchmarks

- `schemas/` 保存版本化 JSON Schema。YAML 工件先解析后按同一 schema 校验。
- 通用结构校验器：`scripts/validate_contract.py`。它只校验字段/类型/枚举，不代替数学或证据审查。
- 训练/研发阶段应运行仓库根目录 `benchmarks/` 的系统级回归案例，检查语义门、基线门、外部 challenge、声明边界和 Figure Planning 是否在整题流程中仍然生效。
- benchmark 通过不代表获奖水平；它只证明指定的系统行为没有回归。

## CUMCM writing and delivery

- 电子版第一页为标题、摘要、关键词专页；不含承诺书和编号专用页。
- 不生成目录；正文按题目分问组织；正文与附录分开计页。
- 摘要、正文、附录、图表、代码与支撑材料均不得出现身份信息。
- 使用图表或正文数字前必须有机器可读结果与验证状态。
- 共享的坐标系、动力学、数据变换或评价规则集中建立一次；后续分问只写继承对象、模型增量、求解差异和误差传播。
- 图表角色为导航、机制、证据或验证。正文优先机制与决策必需图；精确答案优先表格；低价值收敛、微小数值误差、完整参数扫描和工程审计图默认进附录。
- 能用二维解释清楚时，不为“高级感”强行三维；真实三维空间部署需要时才保留，并提供投影/切片/关键点。

## Local corpus distillation route

- 需要参考本地真题、算法或论文经验时，读取 `references/local_corpus/` 下的来源边界、真题结构、创新模式、代码审查和中文写作规则；原始本地目录不是运行依赖。
- 完整论文规划或改稿时必须读取 `references/local_corpus/award_paper_narrative_figure_distillation.md`，但不得复制样本文本、答案或图形。
- 语料只提供候选问题结构和反例，不提供自动获准的模型或目标解释。
- 接收本地代码时按 `SOURCE_ONLY → DEMO_ONLY → STATIC_OK_RUNTIME_UNVERIFIED → RUNTIME_VERIFIED → EVIDENCE_ELIGIBLE` 分级；文件存在、语法通过或脚本运行均不得输出语义 PASS。
- 真题回归至少覆盖机理--优化、预测--决策、统计--决策、几何--搜索、随机仿真和在线重规划，并增加“外部可行解击穿内部稳定”的反例测试。

## Boundaries

- 不设置 GitHub、仓库、分支、提交、PR 或远端状态作为数学结果门控；运行时不依赖远端仓库。
- 不伪造数据、结果、图表、参考文献或程序执行记录。
- 正式竞赛中对外部资料、AI 和协作工具的使用必须遵守赛事规则；关键权限未知时不默认允许。
- ARIS 派生内容与本地化范围见 [归属说明](references/aris_derivation_notice.md)。

## Output format

```markdown
## 任务判断、赛制权限与当前状态
## 题意语义与待裁决项
## 分问依赖与最小基线
## 模型、创新与实验计划
## 需要用户批准的决定
## 主求解与外部挑战证据
## 验证与声明边界
## 论文、图表与交付路径
## 未解决项与停止条件
```
