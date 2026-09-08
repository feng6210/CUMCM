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
5. 编译成功后，先运行 `scripts/visual_review_gate.py prepare --paper-dir paper`，把**本轮已发布 PDF、当前 `compile_report.json` 和论文源文件快照**绑定到 `VISUAL_REVIEW_BINDING.json`。随后重新打开该 PDF 并检查全部页面（含参考文献和附录），按下述视觉报告契约写 `PDF_VISUAL_CHECK.json`，最后运行 `scripts/visual_review_gate.py verify --paper-dir paper --visual-report PDF_VISUAL_CHECK.json`。若首次编译使用 `--output-pdf main-revised.pdf`，prepare/verify 均传同一 `--output-pdf main-revised.pdf`。verify 只检查已经审阅的既有工件，**不重新运行 XeLaTeX/latexmk**；源码、编译报告或 PDF 任一变化时返回 `VISUAL_VERIFICATION_REQUIRES_RECOMPILE`，必须重新编译并重新审阅新工件。最终两阶段视觉复核不要再用第二次 `compile_paper.py --visual-report ...` 代替 gate，因为重新编译即使源码不变也可能产生不同 PDF 字节并使刚完成的视觉报告失效。若首次环境没有 XeLaTeX，报告 `BACKEND_UNAVAILABLE`，不得声称 PDF 已验证。

## 输出路径与失败保留

- 默认交付 `paper/main.pdf`；用户明确选择另存时使用 `--output-pdf main-revised.pdf`，相对路径以 `--paper-dir` 为基准，也可给绝对文件路径。目标必须是 `.pdf` 文件，父目录须已存在，且不得位于编译器的 `build` 目录内。
- 本轮必须真正生成 `build/main.pdf`。旧构建 PDF 会保留在 `build/previous-pdfs/` 并记入报告；即使进程退出码为零，也不能拿旧交付文件填补缺失产物。确定性构建可以与旧版哈希相同，要求的是本轮产物存在，而非强求哈希变化。
- 发布使用同目录暂存校验后替换；复制或替换遇到 `PermissionError` 等错误时报告 `PDF_PUBLISH_FAILED`，保留旧目标和新构建文件，不自动另选文件名。向用户说明关闭占用程序或主动选择 `--output-pdf`。不得把旧目标的哈希写成新发布成功。
- `source_pdf_path/source_pdf_sha256` 标识实际构建源，`pdf_path/pdf_sha256` 标识成功发布的文件；`pdf_published=false` 不得解读为交付完成。交付检查脚本也应传相同的 `--output-pdf`，不能回头检查旧 `main.pdf`。
- 手动 BibTeX 路径每轮真实运行，不按“旧 BBL 含相同引用键”复用：同键的题名、作者或样式仍可能变化。任何非零退出均停止，不靠非空 `bibitem` 容忍崩溃或维护码；零退出也要求本轮新 BBL 的文献环境完整并覆盖当前引用键。旧 BBL/BLG、失败时的空/截断产物和完整进程日志保留在 `build/manual-attempts/`，不能恢复旧 BBL 后把本轮记为成功。该检查不替代文献内容和引用语境审计。

## 视觉报告与增量复查

`compile_paper.py` 会尝试渲染所有页面，但渲染成功不等于已查看。`visual_review_gate.py prepare` 在人工阅读前冻结已发布 PDF、编译报告与当前论文输入；`verify` 只验证这组冻结工件和人工报告，不执行编译器。视觉报告由实际查看者填写，页号使用从 1 开始的 PDF 物理页；例如两页报告的最小结构如下（哈希、身份和范围必须替换为真实记录）：

```json
{
  "status": "PASSED",
  "paper_pdf": "main-revised.pdf",
  "paper_sha256": "actual-pdf-sha256",
  "page_count": 2,
  "rendered_pages": [1, 2],
  "reviewed_pages": [1, 2],
  "reviewer_id": "actual-reviewer",
  "reviewer_role": "作者自查或交叉审查，明确是否写过正文/图表及上下文来源"
}
```

- `VISUAL_REVIEW_BINDING.json` 记录 `compile_report.json` 哈希、已发布 PDF 哈希/页数和论文源快照。源快照排除 `build/`、交付 PDF、编译/视觉报告及视觉证据本身；因此添加审图记录不会把论文源误判为变化，但正文、类文件、图表、数据/代码附件等输入变化会使旧绑定失效。绑定创建后若 `compile_report.json`、PDF 或论文输入改变，verify 返回 `VISUAL_VERIFICATION_REQUIRES_RECOMPILE`，不能通过重新计算旧报告哈希绕过。
- 相对工件路径以视觉报告所在目录为基准；`paper_pdf` 若提供，必须是本次实际输出。完整范围须覆盖全部页面；缺少页数、实际渲染/查看范围或身份角色的旧报告不删除、不冒判通过，返回 `REVIEW_REQUIRED` 并说明待补字段。先留存旧报告，再补充实际检查证据迁移。
- 机器只核对文件绑定与声明范围，不能证明人真的打开了图片或证明独立性。必须如实记录原作者身份、同源交叉审查或零上下文来源；没有固定人数要求，也不能靠写一个身份字段取得“独立验证”认证。
- 改版后的继承仅限已经检查且渲染图完全相同的页面。先将旧报告保存为另一个文件；新报告记录 `previous_report: {"file": "prior-review.json", "sha256": "..."}`、`inherited_pages: [页号]`。新旧报告均保留 `page_images: [{"page": 1, "file": "pages/page-1.png", "sha256": "..."}]`。脚本逐一比对当前 PNG 与旧报告哈希；字节完全相同是同像素的充分证据。其他格式、重编码后仅声称同像素或缺历史证据不能自动继承，需直接复看或另附明确的像素比较记录供人工复核。
- 当前报告的 `reviewed_pages` 包括明确披露的继承范围与本轮实际查看范围；不能说继承页面是本轮重新全文阅读。变化页和受其影响的分页/图表必须复看，保留问题、修复及回审记录。
- 总页数、正文页数与附录页数分开报告。`Underfull` 提示、代码结尾孤行或少量内容的末页需要实际查看并披露是否影响可读性；不能为了页数或消除警告自动删除源程序、证据或合法附录。阻断性的裁切、缺字、溢出仍须修复。

## 源码包复编译边界

- `final_delivery_check.py` 的 ZIP 重开/校验只证明容器可读，不证明源码完整或可复现。若要声称“源码包可复编译”，须将最终交付 ZIP 真正解压到一个全新目录，检查成员路径安全后，从解压出的 `main.tex` 使用包内类文件、章节、图表、文献和已说明的依赖执行编译；保留 ZIP 哈希、解压清单、实际命令、依赖及日志、输出 PDF 哈希和版面检查结果。不得借用原工作区未打包的文件，也不得仅检查 ZIP 文件名或原目录能编译。
- 论文源码包（重建论文 PDF 所需材料）与完整实验包（还包含题定输入、模型/求解/验证脚本、运行环境、结果和失败记录）分别标明。源码复编译通过不等于数值实验已独立重跑；实验复现须按用户授权和原预算另行验证。本 Skill 不创建复杂打包器，也不为缩包静默删除原始证据。

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
