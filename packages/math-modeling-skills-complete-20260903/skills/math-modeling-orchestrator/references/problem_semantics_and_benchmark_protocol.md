# 题意语义锁定与外部基准挑战协议

## 目的

在任何主模型或复杂优化器运行之前，先冻结“究竟在优化/预测/评价什么”；在得到候选解之后，再用题目给定解、公开可行解、优秀论文策略或独立基线对当前 evaluator 做外部挑战。该协议解决两类高风险错误：

1. 目标函数、计时口径、资源归属或多目标语义被静默选错；
2. 多种子内部稳定被误当成“已经覆盖主要解盆地”。

## A. 题意语义锁定

### 必须产物：`PROBLEM_SEMANTICS.yaml`

每个核心分问至少记录：

```yaml
question_id: Q3
raw_objective_phrases:
  - 题面中的原始目标表述
entities:
  - name: 资源/目标/主体
    identity_rule: 是否可复用、是否可同时服务多个目标
candidate_interpretations:
  - id: S1
    mathematical_objective: 形式化目标函数或判据
    resource_accounting: 资源如何计数
    time_accounting: 区间求和/并集/交集/首次到达等口径
    assumptions_added: []
    evidence_for: 题面、附件或物理语义
    evidence_against: 可能冲突
    downstream_effect: 对可行域、最优解和结论的影响
selected_interpretation: S1
selection_reason: 为什么采用该口径
semantic_risk: low|medium|high
unresolved_ambiguities: []
```

### 硬规则

- 题面出现“总”“同时”“分别”“至少”“最多”“联合”“有效时长”“综合”等可能改变集合运算或资源归属的词时，必须做候选解释对照。
- 多目标问题必须明确是 `sum / min / max-min / weighted / lexicographic / intersection / union / Pareto` 中哪一种；不能在看到结果后更换主目标。
- 一个物理资源是否允许同时对多个目标产生贡献，必须由题面或物理机制决定；不得为了简化优化器默认一对一指派。
- 语义风险为 `high` 且存在两个以上会改变最优解结构的合理解释时，进入 `SEMANTICS_REVIEW`，先向用户/题面证据请求裁决；不得直接求解。
- 一旦主目标、计时口径、资源计数或核心判据改变，原模型批准和下游结果全部失效。

## B. 最小正确基线

复杂模型之前至少建立一个可复算基线：

- 低维：网格、解析、枚举、多起点局部；
- 几何/机理：人工构造案例、边界情形、闭式或高精度 evaluator；
- 组合：小规模精确 MILP/枚举；
- 预测：朴素/线性/持久性基线；
- 随机仿真：可验证极限或简化情景。

基线的作用是校验题意、单位、方向和 evaluator，不是为了“显得有对比”。若基线都不能稳定复算，不得升级复杂模型。

## C. 外部基准挑战

### 何时触发

满足任一条件就触发：

- 用户提供优秀论文、国奖论文、公开答案或已有策略；
- 题面给定样例/边界答案；
- training/coursework/research 模式中可以合法访问公开基准；
- 主结果声称“最佳、近最优、稳定最优、预算内最佳”等强结论。

正式竞赛中若规则禁止访问外部解，必须记录 `EXTERNAL_CHALLENGE_NOT_ALLOWED_BY_RULES`，不得绕过赛事要求。

### 核心原则

外部策略必须进入**自己的 evaluator**，不能只比较论文中报告的数字：

```text
external parameters / route / prediction
→ format adapter
→ current hard constraints
→ current objective/evaluator
→ exact recomputation
→ compare with incumbent under same protocol
```

### 必须产物：`BENCHMARK_CHALLENGE.json`

至少记录：

```json
{
  "benchmark_id": "award-paper-q3",
  "source_scope": "user-provided paper",
  "parameter_mapping": {},
  "same_evaluator": true,
  "feasible_under_current_model": true,
  "objective_value": 0.0,
  "incumbent_value": 0.0,
  "tolerance": 0.001,
  "outcome": "PASS|CHALLENGED|INCOMPARABLE",
  "reason": ""
}
```

### 判定

- 外部可行解在同 evaluator 下领先超过预设容差：当前“最佳/稳定最优”声明立即 `FAIL` 或降为 `PARTIAL`，返回求解阶段。
- 外部方案在当前模型下不可行：记录具体冲突，说明是模型口径差异还是外部方案本身不满足约束。
- 只能比较不同目标或不同物理口径：标记 `INCOMPARABLE`，禁止把原文数字直接排大小。
- 多种子近似同值只说明局部稳定；只要外部挑战击穿，就不能继续用“多种子稳定”支持解盆地覆盖。

## D. Solver 与 Reviewer 的责任分离

Solver 可以生成候选、修复可行性和报告最优性边界；Reviewer/Validator 负责：

- 重新读取 `PROBLEM_SEMANTICS.yaml`，检查目标没有漂移；
- 用原始目标函数重算；
- 执行至少一个异源挑战（若可用）；
- 尝试构造反例、边界例或替代解释；
- 对“最优、稳定、鲁棒、提高”等强词独立给出 PASS/PARTIAL/FAIL。

同一上下文的 solver 自己检查自己，只能作为同源核验，不满足外部/独立挑战要求。
