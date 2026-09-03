# 数学建模总控路由与交接指南

## 路由矩阵

| 信号 | 路由 Skill | 必须交接的证据 |
|---|---|---|
| 读题、分问、输入输出 | `mm-problem-decomposer` | 问题表、显性/隐性约束、附件清单 |
| 变量、假设、目标、约束 | `mm-variable-assumption-builder` | 符号表、单位、假设来源 |
| 数据缺失/异常/类型 | `mm-data-eda-cleaning` | 数据审计、异常清单、清洗决策 |
| 模型候选、基线与淘汰理由 | `mm-model-selector` | 基线、2—4 个候选、数据/机理适配、风险 |
| 创新、国奖对比、路线批准 | `mm-model-innovation-designer` | A/B/C 路线、创新证据卡、消融、回退、批准请求 |
| 多指标评价与排序 | `mm-evaluation-models` | 权重来源、方向、排序敏感性 |
| 回归、时间序列、灰色预测 | `mm-prediction-models` | 划分方案、基线、误差和外推边界 |
| LP/MILP/非线性/多目标 | `mm-optimization-models` | 变量、目标、原始约束核验、最优性状态 |
| 路网、管网、传播、路径 | `mm-graph-network-models` | nodes/edges、方向、边权、可达性 |
| ODE、运动学、阶段决策 | `mm-dynamic-mechanism-models` | 方程、初边值、步长/容差或 Bellman 契约 |
| 抽检、检验、纵向/生存 | `mm-statistical-inference` | 抽样设计、独立性、区间与校准 |
| 分类、聚类、模式识别 | `mm-classification-clustering` | 分组/时间切分、类别分布、指标 |
| 随机、排队、离散事件 | `mm-simulation-models` | 分布依据、种子、重复次数、MC 误差 |
| 频谱、图像、视频、轨迹 | `mm-signal-image-trajectory` | 采样/标定、处理规则、中间特征 |
| 所有数值模型完成后 | `mm-uncertainty-validation` | 声明—证据表、PASS/PARTIAL/FAIL |
| 图表、Excel、附件 | `mm-visualization-delivery` | 字段、单位、精度、数字溯源 |
| 论文结构与摘要 | `mm-paper-structure-writer` / `mm-abstract-polisher` | 已验证结果，不接受占位数值 |
| 最终审查 | `mm-paper-reviewer` | 题目、草稿、代码输出、验证报告 |

## 标准状态

```text
NEW → INPUT_REGISTERED → DECOMPOSED → DATA_AUDITED → MODEL_PLANNED
→ INNOVATION_PROPOSED → AWAITING_MODEL_APPROVAL
→ USER_APPROVED → SOLVING → SOLVED → VALIDATING
→ PASS/PARTIAL → DELIVERING → REVIEWING → COMPLETE
```

任意适用阶段可进入 `BLOCKED_INPUT` 或 `BLOCKED_CAPABILITY`。验证失败进入 `FAIL`，不能直接交付。完整字段见共享 schema；总控脚本负责拒绝非法跳转。

`agents/openai.yaml` 是 Codex 的 Skill 界面与触发元数据，不是自动运行的独立多 Agent 系统。完整性来自总控的显式路由、产物契约与停止条件；不能把存在 YAML 文件等同于自动协作已经发生。

## 使用提醒

- 先确认输入与规则，再启动数值求解。
- 拆题、EDA、选型和创新方案完成后，先把每问模型与创新路线汇报给用户；没有明确批准就停在 `AWAITING_MODEL_APPROVAL`。
- 所有结果带来源、前提、运行参数和可核验边界。
- `FAIL` 保持失败；`PARTIAL` 缩小结论；缺数据返回阻塞状态。
- 不把结构化建议包装成可直接提交的终稿。
