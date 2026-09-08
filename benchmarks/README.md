# CUMCM 系统级回归基准

这里测试的不是“某个脚本能否运行”，而是整套 Skill 在真实结构问题上是否保持关键行为。benchmark 只定义题型结构、必须行为、禁止行为和验收条件；不复制获奖论文正文，也不把历史答案写成当前题目的真值。

## 为什么需要系统基准

单元测试可以证明状态机、渲染器或 schema 没坏，但不能发现：

- 目标函数语义被静默换掉；
- 最小基线被复杂模型绕过；
- 多种子内部稳定被误写成接近全局最优；
- 外部可行解已经击穿 incumbent，却只在论文中改措辞；
- Figure Planning 重新退化成固定图量；
- 写作层把 hash/gate/版本谱系重新泄漏进竞赛正文。

## 目录约定

每个案例包含一个 `benchmark.yaml`，按 `packages/math-modeling-skills-complete-20260903/schemas/system_benchmark.schema.json` 校验。案例可以再附：题目来源说明、允许公开的合成输入、预期工件清单和人工审查记录。

建议至少覆盖：

1. 机理—优化；
2. 预测—决策；
3. 统计—决策；
4. 几何—搜索；
5. 随机仿真；
6. 在线重规划；
7. 外部可行解击穿内部稳定；
8. 简单闭式题（验证不会为了图量/算法复杂度过度工程化）。

## 运行原则

- benchmark 的 `required_behaviors` 是硬行为，不等于固定算法答案。
- 数值阈值只有在同 evaluator、同目标、同约束下才可写入案例。
- live contest 不运行禁止的外部答案 challenge；训练 benchmark 默认使用 `task_mode: training`。
- 系统 PASS 至少要求：所有 hard behavior 有工件证据、没有 forbidden behavior、关键 P0/P1 未被 reviewer 击穿。

当前首个案例 `cumcm-2025a-smoke-screen` 只编码我们已经观察到的结构性回归风险：题意聚合、外部可行解 challenge、搜索声明边界和机制图规划。它不把某篇论文的数值答案固化为唯一真值。
