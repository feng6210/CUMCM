# 外部 Humanizer / Academic Humanizer 详细蒸馏记录

本文件记录 `mm-paper-humanizer` 的方法来源、采用方式和拒绝项。目标是吸收可泛化原则，不复制外部项目的措辞、评分口径或针对特定检测器的策略。CUMCM 语义、结果和声明真值始终由本仓库工件提供。

## 1. henmuc/codex-academic-humanizer

### 核心价值

该 Skill 的真正优势不是“替换 AI 高频词”，而是学术改写的保真契约：

- 保留事实、数据、citation、公式、变量、单位、图表编号；
- 保留段落功能；
- 保留 uncertainty/hedging 与 claim strength；
- 不为了避免重复而轮换固定技术术语；
- citation 不得移动到支持另一条主张的位置；
- 原文歧义不由润色器静默补全；
- Light / Medium / Deep 分级控制改写强度。

### 采用

- `F01` 数学环境冻结；
- `F02` 数字/单位冻结；
- `F03` citation/ref/label 冻结；
- `F04` claim-strength preservation；
- `F05` terminology stability；
- `F06` ambiguous-source flagging；
- 分级改写思想。

### 改造

原 Skill 面向通用学术论文；CUMCM 需要额外保护：

- 优化域和最优性层级；
- 题面目标函数口径；
- 多问之间传递的参数/状态；
- 表格精确结果与摘要舍入的一致性；
- “模型内解释 vs 实测/因果结论”的边界。

因此新增 `protected_content_and_claims.md`，并把改写分为 `check/light/compact/structural/compare/audit`。

### 不直接采用

- 通用 IMRaD 假设；
- 任何与 CUMCM 章节结构冲突的固定论文模板。

---

## 2. Aaron-Bushnell/humanizer

### 核心价值

最值得借鉴的是闭环工作流而不是 pattern 数量：

```text
detect → rewrite → integrity_check → compare/audit
```

`integrity_check.py` 会抽取数字、URL、citation、code、negation、modal、quote 做前后比较；`clause_align.py` 用 clause 对齐解释改动；`patterns-zh.md` 将中文问题独立于英文规则处理。

### 采用

- `P01` rewrite 前后内容不变量检查；
- `P02` 诊断和改写分离；
- `P03` compare/audit 单独模式；
- `P04` 中文规则不从英文机械翻译；
- `P05` 允许 voice/sample 作为风格参考，但只提取可观察特征。

### 改造

原 integrity checker 不理解 CUMCM LaTeX，因此不能直接使用。新脚本需识别：

- `$...$` / `\(...\)` / `\[...\]`；
- `equation/align/gather/...`；
- `\cite/\ref/\eqref/\label`；
- `\SI/\si/\num`；
- claim-strength marker。

### 拒绝/降权

`patterns-zh.md` 中下列规则不能做硬规则：

- 连续显式主语 → AI：学术写作中明确主语可能更准确；
- “的”字每 20 字某阈值：机械阈值缺少领域校准；
- 缺少“吧、嘛、呢、啊” → AI：对 CUMCM 学术文体不成立；
- 为了“像人”加入口语成分：明确禁用。

`token_analyzer.py` 的 TTR、hapax、Gini、Rényi、“surprise”仅作为描述性启发，不迁入中文 CUMCM 质量门。原因：

- tokenizer 主要针对英文；
- 文内词频不是条件 token probability；
- 未对中文数学论文校准；
- 容易产生伪精确“AI 概率”。

---

## 3. Lanqingsong/humanize-writing

### 核心价值

这是中文论文结构层最值得吸收的来源。关键不是词表，而是“作者站位/回答者惯性”：

- 辩护姿态：预设质疑后提前免责声明；
- 纠正姿态：不断使用“不是 X 而是 Y”；
- 问答残留：像在向提问者解释；
- 服务姿态：空泛开头、客服式结尾、每段都做总结。

另外，其修订优先级强调：

```text
先逻辑链 → 再节奏 → 最后措辞
```

并检查：

- 段间跳步；
- 包含关系写成并列；
- 实现细节越界；
- 图表引用过早；
- 动机/方法/公式逻辑倒置；
- 重复论证一个已由前提保证的结论；
- 内部术语直接进入摘要。

### 采用

- `S01` responder inertia；
- `S02` defensive posture；
- `S03` correction posture；
- `S04` service posture；
- `S05` structural-before-lexical revision；
- `S06` density principle；
- `S07` no “post-hoc synonym replacement only”；
- `S08` section-role check；
- `S09` implementation-detail placement；
- `S10` internal-term abstraction。

### 改造

“论文只做正面陈述”作为高优先级偏好，不作为绝对规则。CUMCM 中以下否定/限制必须保留：

- 最优性边界；
- 未收敛/不可行域；
- 统计不确定性；
- 因果/实测外推边界；
- 题设歧义影响答案的说明。

因此改成：

> 优先正面陈述；只有数学区分、claim boundary 或误解风险确实改变答案时保留否定式辨析。

### 代码采用

其 `audit_chinese_ai_style.py` 的“局部匹配 + 全文密度 + 重复句首 + 段落等长 + stance density”思想值得迁移，但需重写为 LaTeX-aware 版本。

---

## 4. smyrick/humanize-text

### 核心价值

两点最重要：

1. protected spans / factual inventory；
2. density & clustering，而不是单词黑名单。

其扩展 reference 明确指出：单个 `however/robust/comprehensive` 不足以判定问题；真正有意义的是局部聚集和结构模式。还专门警告“anti-AI overcorrection”：故意短句、错别字、口语、全禁某标点，同样会形成新的机械风格。

### 采用

- `F07` factual inventory；
- `F08` protected-span precedence；
- `Q01` density over isolated keyword；
- `Q02` no-op ability；
- `Q03` anti-overhumanization gate；
- `Q04` preserve writer/genre voice；
- `Q05` already-natural text may remain unchanged。

### 改造

voice matching 只允许提取：

- 句长/段长习惯；
- 主动/被动比例；
- 连接方式；
- 第一/第三人称使用；
- 术语和中英文混排习惯。

禁止从样本推断年龄、身份、性格或编造经历。

### 拒绝

- 用错字/俚语/强行不规则句式“伪装人类”；
- 对学术领域合法词（如 robust）做全局禁词。

---

## 5. judetelan/ai-humanizer

### 核心价值

语言知识不是主要采用对象，真正值得借的是工程架构：

```text
lexicons
→ registry/rules
→ lexical engine + stylometry engine
→ report
```

规则 metadata 与检测实现分离，便于后续扩展和 mode-specific 权重。

### 采用

- `A01` rule registry 思想；
- `A02` rule id/category/severity/profile/action metadata；
- `A03` lexical 与结构/统计诊断分层；
- `A04` false-positive classification；
- `A05` check/audit 作为只读流程。

### 拒绝/改造

- 英文 contraction、em-dash、word-count 阈值不直接映射中文论文；
- sentence-length CV/TTR 等阈值未在中文 CUMCM 校准，不作为 gate；
- 任何“Human/Likely human/AI slop”标签不进入本 Skill 输出；
- 不针对具体模型供应商做所谓 tic 识别。

---

## 6. 本仓库 CUMCM 规则的反向修正

外部蒸馏显示，当前 CUMCM 写作链存在一类内部冲突：为了证据完整性，旧规则倾向让“每问都显式带验证和声明边界”，长期执行会生成审计式正文。

### 保留

- 每个核心 claim 必须可追溯；
- 不能把 FAIL 写成 PASS；
- 未证明全局最优不能写成全局最优；
- 未收敛/外推限制不能被润色隐藏。

### 修改

从：

```text
每问必须显式出现：任务→模型→求解→结果→验证→边界
```

改为：

```text
每问必须在证据层闭合；正文只显式保留对当前读者判断必要的验证和边界。
```

即“证据完整”与“正文全部暴露证据”分离。

### 摘要修改

从：

```text
每问模型→结果→验证/范围
```

改为：

```text
每问输出→模型→求解→关键结果；
验证仅保留最有区分度的一项；
限制仅在改变答案含义时就地出现。
```

---

## 7. 最终原子规则分层

### L0 Fidelity

- F01 math freeze
- F02 numeric/unit freeze
- F03 ref/cite/label freeze
- F04 claim ladder freeze
- F05 terminology stability
- F06 ambiguous-source flag
- F07 factual inventory
- F08 protected-span precedence

### L1 Stance

- S01 responder inertia
- S02 defensive posture
- S03 correction posture
- S04 service posture
- S05 positive-statement preference
- S06 audit-language leakage

### L2 Structure

- R01 one reader job per paragraph
- R02 no forced paragraph template
- R03 validation placement by decision value
- R04 limitation centralization
- R05 algorithm-to-task rewrite
- R06 no redundant premise-proof loops
- R07 no implementation-detail leakage into problem definition
- R08 logical bridge before new concept
- R09 figure reference after concept introduction
- R10 CUMCM question dependency preservation

### L3 Surface

- T01 stock opening
- T02 mechanical connectors
- T03 rule-of-three padding
- T04 empty evaluation
- T05 nominalization/administrative wording
- T06 repeated sentence opener
- T07 dense hedging
- T08 same-claim paraphrase repetition
- T09 audit jargon
- T10 empty summary endings

### Global quality gates

- Q01 density over isolated word
- Q02 no-op ability
- Q03 anti-overhumanization
- Q04 genre voice preservation
- Q05 no AI probability claim

## 8. 采用原则

最终 Skill 不追求“命中越少越好”，而追求：

1. 技术语义零漂移；
2. 竞赛读者能更快找到关键结果；
3. 非必要审计脚手架减少；
4. 已经自然的文字尽量不动；
5. 修改理由可解释、可回滚。
