# 参考对照与独立视觉审查

最终图必须并列打开样式卡预览和当前成图，缩到实际插入论文的宽度检查。不得由“成功导出”自动写审美 PASS。
参考图只指导配色、构图和层级；不复制原图数据、图中文字或错误统计。原始来源不可访问时使用随包原创预览，明确记录替代来源。

## 分工

- 数值审查：从 CSV/结果与渲染配置逐项检查取值、范围、单位、误差定义；不得从像素反推答案。
- 视觉审查：交给未参与该图生成的子 agent，提供原始图意图、样图与当前成图，不提供“预期通过”的评价。其必须实际打开图片并给具体观察。
- 生成者合并反馈；同族新 agent 记录 same-family-fresh，不称外部认证。没有独立 reviewer 时可保留草稿，记录 BLOCKED_REVIEW，不自填另一个 reviewer_id。
- 风格评分可帮助比较候选，但不能覆盖错误标签、箭头、漏点和截断坐标等阻断项。不固定 9 分或轮数；通常 1–3 次定向修订，同一问题两次未改善则报告阻塞。

## 文件格式

intent 增加 style_reference: {card_id, catalog: {file, sha256}, preview: {file, sha256}}。
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
reviewers 至少一个 {role:"visual", reviewer_id:"真实子agent ID", origin:"same-family-fresh 或 external"}。

最终执行 validate_figure_intent.py intent.json --require-outputs --require-visual-review --require-coverage。
没有要求该参数的旧工件仍可做兼容性诊断；新带 style_reference 或原生生成后端的工件在最终模式自动要求审查。任何输出、来源、样式、brief 或 spec 改变都要更新相关哈希并重审，不能只重新计算旧审查的 bindings。
脚本只校验记录与完整性，不证明审稿人真实独立、不自动检查图像语义或宣称模型正确；实际工具记录和查看图片的审查过程才是来源证据。
