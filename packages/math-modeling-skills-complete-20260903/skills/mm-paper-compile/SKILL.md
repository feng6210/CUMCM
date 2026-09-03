---
name: mm-paper-compile
description: Compile and verify Chinese CUMCM LaTeX mathematical-modeling papers with XeLaTeX, including abstract-page, body-page, anonymity, PDF-size, citation, and visual-output checks. Use after a LaTeX draft exists; do not claim a paper is compliant when the compiler or required template is unavailable.
---

# 数学建模：CUMCM LaTeX 编译与 PDF 检查

## Purpose

编译并检查中文 CUMCM 电子版 LaTeX 论文。默认使用 XeLaTeX 和 `latexmk`，检查摘要专页、无目录、正文页数、匿名、引用、PDF 大小、缺图、乱码和裁切。

## Workflow

1. 读取 `paper/main.tex`、`mm-cumcm.cls`、章节、图表、参考文献和 `PAPER_CLAIM_AUDIT.json`。
2. 运行 `scripts/compile_paper.py --paper-dir paper`。脚本先做 CUMCM 源码静态检查，再探测 `latexmk` 与 `xelatex`。
3. 编译时最多针对有明确日志证据的问题做三次修复；同类错误连续两次时停止并保留日志。
4. 读取 `.aux` 的 `mm:body-start` 和 `mm:appendix-start` 标签，检查正文不超过 30 页；检查摘要专页和 PDF 20 MB 限制。
5. 重新打开 PDF 并渲染全部页面检查，生成含当前 PDF SHA-256、页数和 `status=PASSED` 的视觉报告；随后再次运行 `compile_paper.py --paper-dir paper --visual-report PDF_VISUAL_CHECK.json`。只有视觉报告哈希与当前 PDF 一致时，`compile_report.json` 才能进入 `PASSED`。若环境没有 XeLaTeX，报告 `BACKEND_UNAVAILABLE`，不得声称 PDF 已验证。

## CUMCM checks

- 电子版第一 PDF 页是摘要专页；不含承诺书、编号专用页和目录。
- A4、四边至少 2.5 cm、页脚中部页码。
- 正文从摘要后开始，正文最多 30 页，附录不计入正文。
- 论文、图表、代码、PDF 元数据和支撑材料不得泄露身份。
- 图表、引用和交叉引用必须可解析；未定义引用、缺图、缺字体和明显排版问题必须报告。

## Boundaries

- 编译成功不证明模型正确、结论真实或引用语境恰当；这些分别由结果验证、论文数字审计和引用审计负责。
- 用户正式模板优先；内置模板只作为无官方模板时的 CUMCM 电子版基础。
- 编译前检查图表清单中的 PDF/PNG 与源数据/脚本清单；图表脚本编码或字体回退警告必须进入 `compile_report.json`，不能因 PDF 能包含就静默忽略。
