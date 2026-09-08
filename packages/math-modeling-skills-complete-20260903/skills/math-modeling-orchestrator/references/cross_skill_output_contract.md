# 数学建模跨 Skill 交接契约

本契约定义**总控看到的规范化交接包**。为避免一次升级要求 22 个专业 Skill 同时重写，区分“专业 Skill 原生输出”和“总控规范化 envelope”。规范化后可按 `schemas/cross_skill_envelope.schema.json` 做机器结构校验；schema PASS 只证明字段与类型闭合，不证明数学结论或证据成立。

## 1. 专业模型 Skill 的核心原生输出

除纯解释请求外，专业模型 Skill 至少返回：

```text
inputs
assumptions
model_and_solver
machine_readable_results
diagnostics
unresolved_risks
latex_equations
```

图形建议允许两种字段：

```text
figure_intents          # 新字段，优先
recommended_figures     # 旧字段，迁移期兼容
```

若仍返回 `recommended_figures`，总控只把它视为**候选 figure intents**：先经过 `FIGURE_PLAN.yaml` 的读者任务审查，不能直接触发渲染，也不能恢复“每问固定图量”。

## 2. 总控必须补齐的规范化 envelope

进入验证、跨问交接或论文链之前，总控把专业 Skill 输出规范化为：

```text
schema_version
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

其中 `question_id`、`problem_semantics_ref`、`baseline` 和 `benchmark_challenge` 可以由总控从 `workflow_state.json`、`PROBLEM_SEMANTICS.yaml`、基线工件和挑战阶段继承/补齐；**不得要求每个专业 Skill 重复生成这些上游事实，也不得为了满足 schema 伪造值。** `schema_version` 当前使用 `1.0`。

推荐校验：

```powershell
python scripts/validate_contract.py --schema ../../schemas/cross_skill_envelope.schema.json --input QUESTION_HANDOFF.json
```

## 3. 字段语义

- `problem_semantics_ref`：指向已锁定的 `PROBLEM_SEMANTICS.yaml` 条目；目标、计时口径、资源计数或多目标聚合不得在专业 Skill 内自行改变。
- `baseline`：最小正确基线及其 evaluator/约束复算状态。即使本题不需要数值基线，也要有显式 `not_applicable` 记录并说明理由，工作流仍经过 `BASELINE_READY`。
- `benchmark_challenge`：题目样例、外部观测、用户提供优秀论文/公开可行策略等异源挑战状态。若当前阶段尚未运行，可写 `PENDING`；不可比较写 `INCOMPARABLE`；赛事规则禁止写 `NOT_ALLOWED_BY_RULES`。不能留空后宣称“最佳”。
- `machine_readable_results`：正式 evaluator 重算后的结果，不是搜索内核临时值。
- `diagnostics`：数值/统计/随机/约束诊断；内部稳定性与最优性证据分开。
- `figure_intents`：只描述读者障碍、叙事角色和推荐载体，不规定每问固定图量；最终由 `FIGURE_PLAN.yaml` 决定 `figure/table/text/appendix/not_applicable`。

跨问工作还要记录上游结果版本、依赖关系、接口形态和论文目标章节。缺少关键输入时使用 `BLOCKED_INPUT`；能力不存在时使用 `BLOCKED_CAPABILITY`；不要用猜测结果填充字段。

每个含数字的论文声明必须能回指 `result_evidence_map.json`。每个实际渲染图应有 `FIGURE_INTENT.yaml` 条目，但**不是每个核心声明都必须配图**：精确值可以由机器结果和表格支撑，图形只承担不可替代的机制、趋势、空间、区间、权衡或关键验证任务。

证据文件存在只证明可定位，不证明结论成立。
