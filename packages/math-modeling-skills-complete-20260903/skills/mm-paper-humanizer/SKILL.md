---
name: mm-paper-humanizer
description: Humanize and tighten Chinese mathematical-modeling papers after technical results are stable. Preserve formulas, variables, numbers, units, citations, figure/table references, terminology, assumptions, optimization scope, and claim strength. Remove responder-style, audit-heavy, templated, over-explained prose without trying to game AI detectors or fabricating human quirks.
---

# 数学建模论文自然化与终稿精修

## Purpose

把已经完成建模、求解和证据核验的数学建模论文，从“模型输出稿、研究审计稿或模板化初稿”整理成自然、紧凑、可读的 CUMCM 竞赛论文。

本 Skill 只改变表达、段落推进和信息密度，不拥有模型修改权、结果修改权或声明升级权。目标不是“降低某个 AI 检测器分数”，而是消除可观察的机械化、回答者式、审计式和过度解释式表达，让论文首先呈现问题、数学结构、求解、结果和必要解释。

## Core contract

自然化前先建立内容保护清单。以下内容默认冻结：

- 行内/行间公式、LaTeX 数学环境和数学符号；
- 变量名、参数名、下标、上下标、等号/不等号方向；
- 原始数值、百分比、置信区间、p 值、时间窗、迭代/样本计数和单位；
- `\label`、`\ref`、`\eqref`、`\cite`、BibTeX key、图表/公式编号；
- 数据集、模型、算法、附件、变量和题设对象的正式名称；
- 假设所承担的技术含义；
- 目标函数、约束、优化方向和可行域；
- 声明强度与证据等级。

尤其禁止静默升级：

```text
global optimum / 全局最优
> local optimum / 局部最优
> best in searched domain / 当前搜索域最优
> budget-limited best / 预算内最优
> best feasible candidate / 最优可行候选
> observed best / 已观测最好值
```

不同层级不能为了“写得顺”互换。原文存在不确定、局部、预算、搜索域、未收敛或外推条件时，必须先判断这些条件是否改变当前结论含义；需要保留时保留，允许迁移时只能迁移到明确位置，不能消失。

详细保护规则见 `references/protected_content_and_claims.md`。

## Preconditions

优先读取当前任务中的：

1. `PROBLEM_SEMANTICS.yaml`；
2. `RESULTS_TO_CLAIMS.md`；
3. `result_evidence_map.json`；
4. `NARRATIVE_MAP.yaml`；
5. 当前论文源文件；
6. 用户指定的优秀论文/个人文风样本（若有）。

若目标、约束、模型、主结果或 claim 状态仍在变化，不执行结构级自然化，只允许 `check` 或 `light`。P0/P1 技术问题应先回到求解/审稿阶段，不能靠措辞修复。

## Modes

### `check`

只诊断，不改写。识别：

- 回答者惯性；
- 预设读者误解；
- 自我辩护/免责声明密集；
- research-audit 术语泄漏；
- 模板连接词和固定三段式；
- 重复声明与重复限制；
- 算法流水账；
- 空泛评价和宣传词；
- 术语漂移；
- 句式/段落过度同构；
- 过度 humanize 痕迹。

输出位置、原句、类型、影响、建议动作和是否需要人工判断。不得输出“AI 概率”。

### `light`（默认）

允许：

- 删除无信息量套话；
- 删除回答者/服务式元话语；
- 将防御式表达改为正面陈述；
- 合并紧邻的重复句；
- 减少机械连接词；
- 清除无读者价值的 gate/hash/backend/workflow 等工程词；
- 局部拆句或并句。

不得改变段落承担的数学功能，不得改变声明边界。

### `compact`

在 `light` 基础上允许：

- 合并重复的 validation/caveat；
- 将非就地必要的局限集中到“模型评价/局限”章节；
- 将完整 solver protocol 压缩为可复算的最小描述；
- 将 research-audit 语言转成 competition-facing 数学语言；
- 重排段内信息，使“对象/动机 → 模型 → 结果”更快出现。

### `structural`

允许章节内重排和段落重构，但只在结果冻结、技术审查通过且用户明确要求时使用。结构重写仍必须通过完整不变量检查。

### `compare`

不继续改写。比较改前/改后：

- 数字；
- 公式；
- labels/refs/citations；
- 术语；
- scope marker；
- claim-strength ladder；
- 增删段落功能。

### `audit`

全文最终语言审计。只报告剩余风险、误报和是否建议停止修改。已经自然的文字允许 `NO_CHANGE_RECOMMENDED`。

## Required workflow

### 1. Freeze semantics before prose

先确认技术真值源。论文正文不是重新推断结果的地方。若 `RESULTS_TO_CLAIMS.md` 与正文冲突，标记 `TECHNICAL_REVIEW_REQUIRED`，不要选择一个更顺的版本。

### 2. Protect LaTeX and evidence spans

运行或等效执行：

```bash
python scripts/verify_rewrite_integrity.py --original before.tex --rewritten after.tex --json
```

在改写前把数学环境、cross-reference、citation、代码和关键结果视为只读 span。自然化不得在这些 span 内做同义词替换、标点整理或格式“优化”。

### 3. Diagnose from structure to surface

诊断顺序固定为：

```text
L0 语义与证据保护
→ L1 作者站位
→ L2 段落/章节结构
→ L3 句式与词汇表面
```

先修“像在回答用户/审稿人”的站位，再修重复和顺序，最后才处理连接词、套话和节奏。只替词而不改变错误的底层结构，不算完成。

### 4. Rebuild author stance

论文以作者身份陈述事实和方法，不把正文写成与隐形读者的对话。

高风险：

- “这里需要说明的是……”
- “值得注意的是……”
- “容易误解的是……”
- “这并不意味着……”
- “不能简单认为……”
- “本文不声称……”
- “需要特别强调……”

处理原则不是机械删否定词，而是判断这句话承担什么功能：

- 若只是预防误解，改为正面陈述实际关系；
- 若是必要的数学边界，保留或移到最合适的边界位置；
- 若是重复 disclaimer，删除重复项；
- 若影响“能否称为最优/稳健/显著/有效”，不得删除。

例：

```text
旋转分项较小并不意味着纵摇可以忽略。
```

优先改为：

```text
纵摇仍通过几何耦合影响轴向响应，因此模型中保留转动自由度。
```

### 5. Make sections do one reader job

不同章节承担不同任务：

- 问题重述：准确改写题目，不提前证明；
- 问题分析：说明数学对象、困难、依赖和求解主线；
- 模型假设：给必要近似及其技术含义；
- 模型建立：变量、关系、方程及为什么这样建；
- 求解：本题实际使用的算法结构、停止条件和可复算设置；
- 结果分析：结果、图表观察、模型内解释和必要边界；
- 模型检验：最有区分度的正确性/稳定性证据；
- 模型评价：集中说明主要适用条件和不足；
- 结论：回收已证明/已验证的答案，不重复全部摘要。

不要让每个章节都承担一次 limitations section。

### 6. Place validation and caveats by decision value

每个核心结论都必须能回溯到证据，但不要求每个结果句后都显式写一次验证和边界。

就地保留 caveat 的条件：

- 不写会导致读者把候选误解成全局最优；
- 不写会改变比较口径；
- 不写会掩盖未收敛/不可行区域对答案的实质影响；
- 不写会把模型内结论误写成实测/因果结论。

其余 solver 日志、重复交叉验证、哈希、失败谱系、backend report 和微小复算差异移至模型检验、支撑材料或附录。

### 7. Rewrite algorithms as task logic

避免：

```text
首先采用 A，然后利用 B，随后借助 C，最后使用 D。
```

优先写成：

```text
先由 A 确定……，再用 B 求解……；C 仅用于检验……。
```

算法名只在解释本题结构、复现设置或创新时出现，不串成“高级算法清单”。

### 8. Use density, not blacklist absolutes

单个“因此”“显著”“鲁棒”“值得注意”不自动构成问题。看它在局部是否聚集、是否有证据、是否反复承担同一种句法功能。

已经自然、准确、符合竞赛语域的段落可以不改。禁止为了把规则命中数清零而损伤正常学术表达。

### 9. Avoid anti-AI overcorrection

禁止通过以下方式制造所谓“人味”：

- 故意错别字、病句或乱码；
- 强行口语、网络词、方言、第一人称经历；
- 人为加入“吧、嘛、呢、啊”；
- 固定插入特别短句；
- 为了提高词汇多样性轮换技术术语；
- 全文禁止某一种正常标点；
- 随机改变段落长度；
- 为了“像人”降低数学严谨性。

自然节奏来自段落功能和信息结构，而不是随机扰动。

### 10. Run integrity and no-op gates

改写后执行：

```bash
python scripts/verify_rewrite_integrity.py --original before.tex --rewritten after.tex --json
python scripts/audit_cumcm_style.py after.tex --json
```

出现 critical integrity failure 时必须恢复对应内容或标记 `REVIEW_REQUIRED`。语言审计无重大问题时停止修改，不继续“追求更低分”。

## Abstract profile

摘要是压缩后的答案，不是压缩后的审计报告。

每问优先保留：

```text
当前输出目标 → 本题化模型/关系 → 求解 → 核心结果 → 一句必要解释
```

验证只保留最能支撑核心结论且对摘要读者有价值的一项。限制仅在会改变答案含义时进入摘要；其余放正文模型评价/局限。

默认不进摘要：

- gate 名；
- hash；
- backend；
- workflow state；
- trial/seed 全量计数；
- 版本修复历史；
- 无关紧要的求解器复算差；
- 为了审计而存在的内部术语。

## Competition prose preferences

- 用具体对象、动作、参数和结果替代空泛评价；
- 固定术语允许重复，不为了“丰富词汇”换名；
- “显著、有效、稳健、准确、优越”必须有对应比较或指标；
- 一段只承担一个主要任务，但不强制固定“主题句—三句解释—总结句”；
- 连接关系清楚时可以省略“首先/其次/此外/进一步”；
- 句子长短由逻辑决定，不用机械 burstiness 指标驱动；
- 表格给精确答案，图给趋势/机制，正文解释读者需要的关系；
- 结果正文优先陈述结果本身，再给必要解释，不先堆风险声明。

详细模式见 `references/cumcm_humanization_rules.md`。

## Output artifacts

文件任务默认生成或更新：

- 改写后的原格式正文；
- `HUMANIZATION_REPORT.md`：只记录实质性语言/结构问题和处理；
- `HUMANIZATION_INTEGRITY.json`：不变量检查；
- 可选 `HUMANIZATION_DIFF.md`：用户需要逐段对照时生成。

报告不得输出伪“AI 生成概率”，不得承诺通过 GPTZero、Turnitin 或其他检测器。

## Regression requirements

新增/修改该 Skill 后至少检查四类样本：

1. `heavy_audit`：审计/免责声明密集文本应明显简化；
2. `award_human`：已经自然的优秀论文段落应大量 `NO_CHANGE_RECOMMENDED`；
3. `math_dense`：公式、数值、变量、citation、ref 全部保持；
4. `claim_trap`：局部/预算/搜索域最优不得升级成全局最优。

回归设计见 `references/regression_protocol.md`。

## Source distillation

本 Skill 吸收多套公开 Humanizer/Academic Humanizer 的可泛化方法，但不直接复制其语言规则。采用、改造和拒绝项记录在 `references/source_distillation.md`。CUMCM 题意、结果和声明真值始终来自本仓库的语义/证据工件，而不是 Humanizer 外部规则。

## Final principle

好的自然化不会让论文“更像某种人设”，而会减少作者与读者之间不必要的脚手架。评委应首先看到问题、模型、推导、结果和解释；Agent、工作流、版本控制和审计细节仅在它们直接改变数学结论时进入竞赛正文。