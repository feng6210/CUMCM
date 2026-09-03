# 数学建模跨 Skill 交接契约

除纯解释请求外，专业模型 Skill 的交接结果必须含有：

```text
inputs
assumptions
model_and_solver
machine_readable_results
diagnostics
unresolved_risks
latex_equations
recommended_figures
```

跨问工作再增加 `question_id`、上游结果版本、依赖关系和论文目标章节。缺少关键输入时使用 `BLOCKED_INPUT`；能力不存在时使用 `BLOCKED_CAPABILITY`；不要用猜测结果填充字段。

每个含数字的论文声明必须能回指 `result_evidence_map.json`；每张图应有 `FIGURE_INTENT.yaml` 条目。证据文件存在只证明可定位，不证明结论成立。
