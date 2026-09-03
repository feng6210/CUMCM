# CUMCM 图量与图组覆盖规划

## 目标

图不能只“有一两张好看的”，也不能用重复图凑数量。图量由分问、核心结论和验证责任决定。正文中的每张图或图组都必须承担一个不可替代的读者任务；附录负责高密度补充证据。

## 每问六类读者任务

| 覆盖槽 | 读者要解决的问题 | 常用图型 | 最终要求 |
|---|---|---|---|
| `data_diagnosis` | 数据有什么结构、异常、缺失或尺度问题 | 分布、时序、缺失图、空间图、相关热图 | 有图；确实无原始数据时写不适用理由 |
| `mechanism` | 模型怎样把现实对象映射为变量、方程和算法 | 机制图、状态图、流程图、网络图 | 复杂机制优先有图；简单闭式模型可说明不适用 |
| `main_result` | 本问最重要的答案是什么 | 趋势、轨迹、排序、方案、Pareto、空间结果 | 必须有正文图 |
| `comparison` | 为什么选主模型或主方案 | 基线对比、前后对比、消融、误差对比 | 有可比路线时必须有图；没有候选路线须说明 |
| `validation` | 结果是否可信、约束是否满足 | 残差、拟合、约束余量、收敛、留出验证 | 必须有正文图，且不能与主结果共用同一图号冒充两项证据 |
| `robustness` | 参数、噪声、情景变化后是否稳定 | 敏感性、区间带、扰动、极端情景、排名稳定性 | 有不确定性或决策风险时必须有图；否则说明边界 |

## `FIGURE_INTENT.yaml` 根级结构

```yaml
coverage_plan:
  expected_question_ids: [Q1, Q2, Q3]
  expected_question_ids_source:
    file: QUESTION_DECOMPOSITION.json
    sha256: 64位SHA-256
    field: expected_question_ids
  questions:
    - question_id: Q1
      core_claim_ids: [claim-q1-main]
      slots:
        data_diagnosis:
          figure_ids: [q1-data]
        mechanism:
          figure_ids: [q1-mechanism]
        main_result:
          figure_ids: [q1-result]
        comparison:
          figure_ids: [q1-baseline]
        validation:
          figure_ids: [q1-residual]
        robustness:
          figure_ids: [q1-sensitivity]
figures:
  - figure_id: q1-result
    # 完整单图条目
```

若某个可选槽确实不适用，使用：

```yaml
mechanism:
  figure_ids: []
  omission_reason: 本问仅进行封闭形式的单位换算，不存在独立模型机制
```

`expected_question_ids` 必须来自题目拆解并列出应回答的全部分问；`expected_question_ids_source` 绑定题目拆解的机器可读文件、字段和 SHA-256，防止某一问同时从图表和覆盖计划中消失。`main_result` 与 `validation` 不接受省略理由。最终模式下，每个分问至少有 4 个互不重复的图号和实际图件，六类槽位之间不复用图号，各槽图的叙事角色必须匹配；不同图号不得共享同一个 `latex_sha256`、`editable_sha256` 或 `backend_report_sha256`。主结果与验证分别使用正文图，不能同时使用完全相同的来源哈希、变量、变换和图型；验证图还必须登记 `validation_target` 与 `validation_method`。`core_claim_ids` 中每个核心结论必须能回指同一分问的 `evidence` 或 `validation` 图。若一个多面板图确实包含多个读者任务，应按主要任务登记一个槽，其余任务使用另一图号或明确说明，不用同一图号反复充数。

## 图组设计

- 一问的推荐阅读链是“问题结构/数据 → 模型机制 → 主结果 → 对比 → 验证 → 稳健性”；不适用的中间环节可以略去，但不能静默缺失。
- 同一逻辑下的 2--4 张小图优先组合为一个共享字体、比例和色板的多面板图；面板不是独立图号，但每个面板要在 `reader_takeaway` 或图题中说明任务。
- 主结果图与验证图必须分开：前者回答“答案是什么”，后者回答“为何可信”。
- 图和表可以使用同一机器可读来源，但不能完全重复。表承担精确值，图承担趋势、结构、差异、误差或稳定性。
- 正文优先放决策必需图和验证图；参数全扫描、全部场景、完整残差诊断及大规模网络细节可进附录。
- 发现图量过少时先补证据链缺口；发现图量过多时合并共享坐标的小图或将次要诊断移入附录。

## 失败条件

- 某核心分问没有主结果图或没有验证图。
- 主结果与验证只引用同一图号，且没有可区分的独立验证证据。
- 某核心结论没有绑定 `evidence` 或 `validation` 图。
- 某个分问少于 4 个不同图号/实际图件，多个图号共享同一输出或报告哈希，或用同来源、同变量、同变换、同图型的副本分别冒充主结果和验证。
- 数据诊断、机制、对比或稳健性槽既无图也没有具体不适用理由。
- 多张图只是改变颜色、排序或图型重复同一份信息。
