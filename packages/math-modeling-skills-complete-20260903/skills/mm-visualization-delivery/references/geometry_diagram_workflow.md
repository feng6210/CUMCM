# 论文几何/物理示意图工作流

示意图属于 `mechanism`，目标是让读者从本题对象和相互关系直接读到方程中的量。用户已确认的 [TikZ线稿与分层配色样式](approved_tikz_schematics.md) 是默认可运行起点；定日镜、刚杆、传热材料都只是示例，不应固化为专用题型。

## 0. 与具体学科解耦

Agent 先从题目和已锁定模型提取 `entities`、`relations`、`coordinates`、`forces_or_flows`、`constraints`，再决定二维、2.5D 或三维构图。示意图可以描述流体、结构、交通、生态、排队、网络、控制或其他对象；参考图片只提供线稿、留白、标注和视觉层级，不提供实体名称、数据或物理结论。

## 1. 先写图意

每张图先登记 `figure_id`、`reader_question`、`caption_zh`、`equation_links`、模型来源和所需几何精度（拓扑示意/保比例/精确解析构造）。列出本题实体、关系、坐标系、向量、角度或边界。关系承担推导时设置 `exact_geometry_required: true`；纯拓扑图不强迫具有度量比例。删掉图后若读者仍能无障碍理解推导，则不保留该图。

## 2. 选择构图

- **姿态/投影**：实体、参考面、法向、投影、角度正方向；可用于传感器、机构或空间观测。
- **受力/耦合**：整体、分体、约束、作用点、力矩与微元；需要时拆图，不把不同力的作用点抹掉。
- **传输/边界**：材料区域、界面、通量、源项、边界条件；不能把物理区域变成算法步骤框。
- **测量/传播**：射线、积分路径、观测量、遮挡/可见性或覆盖；不要用装饰效果代替真实关系。
- **机构/运动**：铰接、滑移、轨迹、局部切向或微元，与运动方程对应。
- **离散系统**：真实网络连接、状态转换、反馈和算法分支，与当前模型一致。
- **组合构图**：整体→局部→判据按需要组合，不默认四联画；保持跨图实体、符号与方向一致。这些是开放分类，不是固定模板白名单。

## 3. 选择实际绘制后端

TikZ默认用于论文几何/物理示意，具体复用、编译和审查见 [已确认样式工作流](approved_tikz_schematics.md)。PGFPlots用于有真实表达式或坐标来源的曲线/曲面，保形几何需等比例坐标；Visio用于原生对象编辑时先核实图元能力，见 [后端工作流](native_backend_workflows.md)。不强制经过SVG中间层。

### 基础SVG回退

`geometry_diagram_from_spec.py` 的输入字段：`canvas`、`style`、`regions`、`axes`、`polygons`、`lines`、`vectors`、`dimensions`、`arcs`、`points`、`labels`。坐标使用画布像素，角度使用度；渲染器不计算模型结果、不补点、不拟合。示例：

```powershell
python scripts/geometry_diagram_from_spec.py heliostat_geometry.json --output figures/q1-geometry.svg
```

SVG 画布 x 向右、y 向下，0° 向右，正角顺时针。数学坐标转画布用 `(ox+s*x, oy-s*y)`，数学角转画布角用 `screen_deg=-math_deg`。角弧使用有符号差值，要求 `0 < abs(end-start) < 360`；跨零的正向20°写350→370，不能写350→10。空间角在三维模型中采样后与实体使用同一投影矩阵，不能拿屏幕圆弧冒充空间角。

需要 PNG 预览时用 SVG→PNG 工具转换，但论文交付优先保留 SVG/PDF 和原始 JSON。`exact_geometry_required` 为真时禁止 imagegen/image2 生成几何证据图。

参数化构造示例：`python scripts/draw_mechanism_examples.py --output-dir 新目录 --tilt 28 --altitude 38`。依赖 numpy、matplotlib 及中文字体；输出 SVG/PDF/PNG、geometry-report.json 和 latex_include.tex。参数仅是演示值。镜面法向量由切向量旋转90°产生；太阳投影与高度弧由三维坐标统一投影；塔身采用通过轴线的二维剖面；传热示例明确为环境温度高于物体的双面加热。输出目录不可覆盖。复杂圆柱三维阴影仍需上游光线求交，不能把二维剖面替代完整计算。

## 4. 审查清单

逐项核对：轴方向、向量箭头、角弧起止、投影虚线、尺寸单位、实体标签、遮挡关系、公式符号和正文完全一致；最终排版尺寸检查文字/线宽/箭头是否仍可读。图题解释“图中几何量如何进入判据”，不在图内塞段落。基础 spec 渲染器只确定性重现输入图元；法向垂直、反射定律、投影和相交正确性由上游坐标计算与验证保证。不能把文件成功输出解释为几何或模型验证通过。
