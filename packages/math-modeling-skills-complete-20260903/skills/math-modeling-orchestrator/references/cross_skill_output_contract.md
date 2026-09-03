# 数学建模跨 Skill 交接契约

除纯解释请求外，专业模型 Skill 的交接结果必须含有：

```text
question_id
inputs
problem_semantics_ref
assumptions
baseline
model_and_solver
machine_readable_results
benchmark_challenge
diagnostics
unresolved_risks
latex_equations
figure_intents
```

## 字段语义

- `problem_semantics_ref`：指向已锁定的 `PROBLEM_SEMANTICS.yaml` 条目；目标、计时口径、资源计数或多目标聚合不得在专业 Skill 内自行改变。
- `baseline`：最小正确基线及其 evaluator/约束复算状态。复杂路线必须说明它具体修复了基线什么不足。
- `benchmark_challenge`：题目样例、外部观测、用户提供优秀论文/公开可行策略等异源挑战状态。不可比较时写 `INCOMPARABLE`；赛事规则禁止时写 `NOT_ALLOWED_BY_RULES`；不能留空后宣称“最佳”。
- `machine_readable_results`：正式 evaluator 重算后的结果，不是搜索内核临时值。
- `diagnostics`：数值/统计/随机/约束诊断；内部稳定性与最优性证据分开。
- `figure_intents`：只描述读者障碍、叙事角色和推荐载体，不规定每问固定图量；最终由 `FIGURE_PLAN.yaml` 决定 figure/table/text/appendix。

跨问工作还要记录上游结果版本、依赖关系、接口形态和论文目标章节。缺少关键输入时使用 `BLOCKED_INPUT`；能力不存在时使用 `BLOCKED_CAPABILITY`；不要用猜测结果填充字段。

每个含数字的论文声明必须能回指 `result_evidence_map.json`。每个实际渲染图应有 `FIGURE_INTENT.yaml` 条目，但**不是每个核心声明都必须配图**：精确值可以由机器结果和表格支撑，图形只承担不可替代的机制、趋势、空间、区间、权衡或关键验证任务。

证据文件存在只证明可定位，不证明结论成立。
