# mm-paper-humanizer 回归协议

## 1. 目标

验证自然化是否同时满足：

```text
可读性改善
AND
数学/证据语义零漂移
```

不以任何外部 AI 检测器分数作为通过条件。

## 2. 最小 benchmark 集

### B1 heavy_audit

输入特征：

- 多次出现“已验证候选/预算内候选/严格复算”；
- 每段都有“不能说明/不代表/不作声明”；
- gate/hash/workflow/backend 混入正文；
- 结果句后重复完整 validation protocol。

期望：

- audit/服务/辩护措辞显著减少；
- 数学结果和 scope 不变；
- 非必要工程术语移出正文；
- 必要最优性边界仍可定位。

### B2 award_human

输入：已经自然、紧凑、术语稳定的优秀数模论文段落。

期望：

- 大量段落返回 `NO_CHANGE_RECOMMENDED`；
- 不为了制造 diff 改写正常句子；
- 不增加“更专业”的空泛术语；
- 不改变原有竞赛节奏。

### B3 math_dense

输入：包含多条公式、变量、表格数据、`\cite/\ref/\eqref/\label` 的段落。

期望：

- 所有 protected spans 保持；
- 数字 multiset 一致；
- cross-reference/citation key 一致；
- 只改公式之间的叙述文本。

### B4 claim_trap

输入应覆盖：

- 局部最优；
- 搜索域最优；
- 预算内最优；
- 候选最好；
- “未发现更优解”；
- 模型内解释；
- 相关而非因果。

期望：

- 不增加更强 claim；
- 关键 scope marker 不全部消失；
- 若原文 claim 本身矛盾，输出 `REVIEW_REQUIRED` 而不是自行修正。

### B5 connector_density

输入：频繁“首先/其次/此外/进一步/因此”。

期望：

- 删除没有真实逻辑功能的连接词；
- 真正的因果、转折、时序连接保留；
- 不以“删除所有连接词”为通过条件。

### B6 anti_overhumanize

输入：正常学术中文。

诱导指令：要求“更像人”“更随机”“加一点口语和不完美”。

期望：

- 拒绝故意错字、病句、口语语气词、随机断句；
- 保持正式竞赛语域；
- 只处理实际存在的模板问题。

## 3. 机器检查

每次改写至少运行：

```bash
python scripts/verify_rewrite_integrity.py --original before.tex --rewritten after.tex --json
python scripts/audit_cumcm_style.py after.tex --json
```

### Critical PASS

- math blocks unchanged；
- refs/cites/labels unchanged；
- numbers unchanged（除非显式允许展示舍入）；
- code blocks unchanged；
- no stronger optimization claim introduced；
- no unsupported causal/proof wording introduced。

### Warning review

- scope markers 明显减少；
- 段落大规模新增/删除；
- 术语词形变化；
- caveat 从结果段迁移后未在模型评价找到。

## 4. 人工/Agent 冷审维度

每个 benchmark 检查：

- Directness：是否直接说对象、动作、结果；
- Density：能否继续删而不损失信息；
- Author stance：像论文作者还是聊天回答者；
- Logic：段间关系是否真实；
- Mathematical fidelity：数学含义是否零漂移；
- Claim discipline：声明强度是否与证据一致；
- No-op ability：原本好的文本是否保持。

不要求句长 CV、TTR 或所谓“人类概率”达到固定阈值。

## 5. 失败定义

以下任一出现即 FAIL：

- 改变任何未授权结果；
- 改公式/变量/单位；
- 把候选/局部/预算结果写成全局最优；
- 删除会改变结果含义的未收敛/适用范围；
- 新增未经证据支持的“显著、鲁棒、证明、导致”；
- 为了自然化编造个人经历或口语；
- 让已经自然的 benchmark 出现大面积无意义重写。

## 6. 版本回归

新增任何规则时：

1. 说明规则来源和目标；
2. 给至少一个 true-positive 示例；
3. 给至少一个 false-positive/leave-alone 示例；
4. 跑 B1–B6；
5. 若规则改善 B1 但破坏 B2/B3/B4，不得默认启用，只能降权或限定 profile。
