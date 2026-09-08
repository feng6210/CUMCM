# 参考对照与独立视觉审查

最终图必须并列打开样式卡预览和当前成图，缩到实际插入论文的宽度检查。不得由“成功导出”自动写审美 PASS。
参考图只指导配色、构图和层级；不复制原图数据、图中文字或错误统计。原始来源不可访问时使用随包原创预览，明确记录替代来源。

## 分工

- 数值审查：从 CSV/结果与渲染配置逐项检查取值、范围、单位、误差定义；不得从像素反推答案。
- 视觉审查：交给未参与该图生成的子 agent，提供原始图意图、样图与当前成图，不提供“预期通过”的评价。其必须实际打开图片并给具体观察。
- 生成者合并反馈；同族新 agent 记录 same-family-fresh，不称外部认证。没有独立 reviewer 时可保留草稿，记录 BLOCKED_REVIEW，不自填另一个 reviewer_id。
- 已有 agent 交叉审查自己未生成或修改的图时，记录 `same-family-cross-review`、`zero_context: false` 和 `independent_of_figure_generation: true`；保留其模型作者等背景，不能升级为零上下文或独立自模型认证。图形作者及后续编辑者均不得作为该图的独立 reviewer；后端报告用 `generator_id`、`post_generation_editor` 保存实际贡献者。
- 风格评分可帮助比较候选，但不能覆盖错误标签、箭头、漏点和截断坐标等阻断项。不固定 9 分或轮数；通常 1–3 次定向修订，同一问题两次未改善则报告阻塞。

## 文件格式

intent 增加 style_reference: {card_id, catalog: {file, sha256}, preview: {file, sha256}}。
catalog 的目标卡必须有 `card_id` 和 `preview_sha256`；若另保存 `preview: {file, sha256}`，其哈希应与前者一致。只填嵌套预览字段不满足卡归属契约。绑定文件成功不意味着完整审查已执行：缺 review 时的预检不会覆盖后续全部审查分支。
visual_review: {file, sha256} 指向如下 JSON；文件路径统一相对 intent 的 base-dir。

```json
{
  "decision": "NEEDS_REVIEW",
  "generator_id": "actual-generating-agent-id",
  "reviewers": [],
  "bindings": {"output": "", "editable": "", "intent": ""},
  "checks": {},
  "blocking_findings": []
}
```

bindings.output / editable 是最终文件 SHA-256；intent 使用 scripts/visual_review_contract.py 的 intent_digest(entry)，排除 visual_review 字段避免哈希循环。
checks 每项为 {"status":"PASSED 或 NOT_APPLICABLE","note":"具体观察和位置"}：
layout、palette、whitespace、hierarchy、final_size、grayscale、chinese_labels、units、reference_comparison。
定量图还检查 numeric_consistency；机制图检查 entities、arrows、branches、stop_conditions、no_invented_mechanism。
非语义装饰检查遮挡、灰度与最终尺寸即可；编码数据的效果另做 effect_removed_comparison。没有生成/查看去效果对照时不能把该项填 PASSED。
仅 units/branches/stop_conditions 可以有明确理由的 NOT_APPLICABLE。
reviewers 至少一个真实的非图形作者/编辑者。origin 为 `same-family-fresh`、`external` 或满足上述披露条件的 `same-family-cross-review`；身份声明不代替实际任务调用和打开图片的证据。

TikZ 的 `editable_output` 为 `.tex`，`latex_output` 为矢量 `.pdf`。后端报告需保存 `actual_backend: tikz`、源/PDF 哈希、`compiler_exit_code: 0` 和两者重开记录；后验检查可以通过 `original_backend_receipt: {file, sha256}` 绑定原编译回执，不得假装再次运行编译器。原回执也必须绑定当前源和 PDF。
审查者排除集合沿原回执追溯生成者和编辑者（包括 `symbol_unification_by`），不能由后验记录删除历史贡献者来伪装独立。声明的 renderer/caption/claim 来源、辅助矢量、预览和实际打开图像均须检查哈希；实际后端不得与声明后端冲突。

### LaTeX 图注绑定

运行 `python scripts/extract_latex_caption.py chapter.tex --label fig:target`，或导入 `extract_file(path, label)`。输出 `caption_latex`、可选短图注、原文字符范围/行号和文件 SHA-256。先核对返回的是目标图的完整独立图注，再将其用作 intent 的 `caption_zh`；含数学命令时保留 LaTeX，若需要纯文本应另作明确转换并检查，不能删除限制条件。

提取器先找唯一的 literal `figure`/`figure*` 及目标 `label`，再配对长图注花括号；支持换行、嵌套、可选短图注、注释和常见 verbatim 区域。缺失/重复标签、缺失/多条主图注、破损括号或环境、仅子图标签均报错，不猜测。它不运行 TeX、不展开宏、条件分支或 `input`；宏生成图注应检查展开后的实际来源及编译结果，不能把静态提取当成最终 PDF 的语义证明。`caption_source` 的文件哈希仍须绑定当前实际章节。

修订保留旧图意、旧回执和失败结论。纯证据格式修复也会改变 intent 摘要，须由原 reviewer 核实变化范围后限定重绑；不得让生成者只刷新审查哈希制造通过。示意图审查同时说明它是几何、完整隔离受力还是广义作用图，重点检查有效锚点、原始/增量方程阶段和力矩方向，详见 [几何/物理工作流](geometry_diagram_workflow.md)。

最终执行 validate_figure_intent.py intent.json --require-outputs --require-visual-review --require-coverage。
没有要求该参数的旧工件仍可做兼容性诊断；新带 style_reference 或原生生成后端的工件在最终模式自动要求审查。任何输出、来源、样式、brief 或 spec 改变都要更新相关哈希并重审，不能只重新计算旧审查的 bindings。
脚本只校验记录与完整性，不证明审稿人真实独立、不自动检查图像语义或宣称模型正确；实际工具记录和查看图片的审查过程才是来源证据。
