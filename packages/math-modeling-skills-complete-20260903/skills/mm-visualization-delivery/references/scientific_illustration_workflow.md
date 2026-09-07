# 中文科研机制图与原生图像生成调用

## 路由与技能调用

先区分“代码/软件绘制示意图”与“生成式科研插图”。数模比赛中的几何、光路、受力、边界条件与坐标图默认读取 geometry_diagram_workflow.md，实际绘制可编辑矢量图。用户明确要求画出来时，本文件的原生图像生成分支不适用。

1. 定量曲线、热力矩阵、数值响应面交给 MATLAB/Origin/Matplotlib。image2/imagegen 仅生成 orientation/mechanism，不生成统计证据。
2. 精确坐标/受力、严格拓扑或逐节点编辑需求优先 Visio/FigureSpec；科研方法总览、机制插图可用原生生成，不能把栅格假称可编辑矢量。
3. 发现当前真实工具列表。默认 auto：有内置 image_gen 则读取并调用 imagegen Skill；内置不可用但专用 codex-image2 桥可调用时读取 paper-illustration-image2 Skill 再走桥接。明确指定 image2 则只尝试该桥，缺失先如实报告，不暗换。
4. paper-illustration-image2 当前可发现位置为用户技能目录 .agents/skills/paper-illustration-image2/SKILL.md；跨机器重新发现，不依赖该绝对路径。未安装时仍可用自包含的内置分支，不需要下载另一个 Skill 包。
5. 调用另一个 Skill 前完整读取其入口与必需参考。按当前用户要求覆盖英文默认为中文、会议论文样式为 CUMCM，并允许已选的鲜明样式。不要继承它的 Git/远端定位步骤作为本地数模运行前置。

## 可执行衔接

scripts/scientific_illustration.py prepare --brief brief.json --tools tools.json --output-dir run
生成 prompt.txt、request.json，不执行或虚构图像调用。tools.json 由本轮实际工具发现结果写入 names 列表，不由检测 PATH 或手填“可用”代替。

brief 必须有 figure_id、backend_preference(auto/image2/imagegen)、purpose、caption_zh、
nodes:[{id,label_zh}]、edges:[{from,to,label_zh}]、source_files:[{file,sha256}]、
style:{palette,composition}。可增加 branches、stop_conditions、exact_geometry_required。
所有 source_files 都绑定已批准的模型说明，不导入外部样图的科研内容。

生成前检查实体、标签、分组、箭头、分支与停止条件；brief 不完备时补齐说明，不增加新模型。
字体内容用明确中文逐字清单；强调主链与反馈链，复杂图优先分层和分组，不做无层次方框堆叠。

### 内置分支 actual_backend=imagegen

- 按 imagegen Skill 调用真实 image_gen 工具，不要求 API key，不调用自造 SDK。
- 全新图只传 prompt；参考/编辑图片先实际打开，再按该工具文档使用参考图片参数。
- 保存工具回执和返回的原生文件；不假设工具支持 destination 参数。
- 将文件复制到当前项目 run 目录；生成服务未提供模型 ID 时 recorded_model=null，不能编造为 gpt-image-2。

### 专用桥接 actual_backend=image2

- 必须实际发现 codex-image2 的 generate 或 generate_start/generate_status 工具；名字存在只说明可调用，不证明生成成功。
- 遵守 paper-illustration-image2 的 helper preflight，读取其依赖协议；预检失败停止该分支。
- 用工具文档的实际 schema 调用；不要把说明中的名字当成当前环境已有工具。
- 接受原生生成成功且有文件的回执；完成 helper finalize/verify 后再进入本 Skill 的图意图和视觉审查。
- app-server ping 成功不等于图像生成可用；严禁 Python 绘图冒充 image2。

## 收集与审查

调用后保存 receipt.json: {actual_backend, tool_name, status:"completed", native_generation:true, output_sha256, recorded_model:null, request:{file,sha256}, prompt:{file,sha256}, tool_record:{file,sha256}}。
request 和 prompt 分别指向 prepare 产生的 request.json 与 prompt.txt。tool_record 为 {tool_name, request_sha256, output_sha256, response:实际工具返回对象或列表}；原生 base64 可以保存在原始 PNG 并记录该哈希，文本保留返回的路径/元数据并注明省略字段。不伪造成功回执，不把 preflight 当生成结果。
scripts/scientific_illustration.py finalize --brief ... --image ... --receipt ... --output-dir ... 核对 prepare 的 brief/source/prompt 绑定，保存 generation_brief.json 原始字节，以及 brief.json（规范来源路径，仅提示词级可修改）、figure.png、request.json、prompt.txt、receipt.json、tool_record.json、latex_include.tex、backend_report.json。它只核对记录和重开，不给语义 PASS。
不重新编码图片，不转换为伪矢量；有效清晰度不足则重新生成高分辨率图，不只改 DPI 标签。
figure intent 设置 editable_output=brief.json、editability=prompt_and_spec_only、latex_output=figure.png、
backend_preference=实际 image2/imagegen、source_data=模型说明来源，绑定 backend_report。
按 reference_visual_review.md 逐项审查节点、中文、箭头与最终尺寸；生成结果中的“结果很好”等新增表述直接删除/重生成。
图像服务失败、限额或缺工具时保留 BLOCKED_BACKEND/FAILED 的真实状态；允许回退必须记录用户选择和实际新后端。
