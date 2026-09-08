# 机器可验证交接契约

本目录存放数学建模 Skill 套件的版本化 JSON Schema。YAML 工件在校验前先解析为对象，再按同一 schema 验证。

这些 schema 只验证**结构、类型和枚举边界**，不能证明题意解释、模型、数值或论文声明正确。数学语义仍由总控、专业 Skill 和独立验证负责。

当前核心契约：

- `problem_semantics.schema.json`：题意语义候选、目标聚合、资源/时间口径与选定解释；
- `benchmark_challenge.schema.json`：外部/异源可行方案进入当前 evaluator 后的重算与判定；
- `figure_plan.schema.json`：reader-task 驱动的 figure/table/text/appendix 规划，不含固定图量；
- `competition_policy.schema.json`：live contest 中 AI、联网、外部论文、公开答案/benchmark 等权限；
- `system_benchmark.schema.json`：整题/系统级回归案例的预期行为与阻断条件。

通用校验：

```powershell
python skills/math-modeling-orchestrator/scripts/validate_contract.py --schema schemas/problem_semantics.schema.json --input PROBLEM_SEMANTICS.yaml
```

新增或不兼容修改字段时递增对应 schema 的 `$id`/`schema_version`，并同时更新回归测试、示例和 `cross_skill_output_contract.md`。不要为了让校验通过而伪造缺失上游事实。
