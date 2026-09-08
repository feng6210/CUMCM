# 用户确认的 TikZ 论文示意图

2026-09-07 用户在查看两张原创试画后确认“可以啊，写入skill”。批准对象是下列样式和构造方法，不是全目录论文阅读完成，也不意味着所有题型或Visio后端均已验证。

## 随包可用的源码与预览

当前默认已按用户新增选择切换为纯黑线条/文字、白底，无彩色或灰色填充。优先使用：

- [黑白受力图源码](../assets/tikz-schematics/monochrome/force-balance.tex)、[预览](../assets/tikz-schematics/monochrome/force-balance.png)、[矢量PDF](../assets/tikz-schematics/monochrome/force-balance.pdf)。
- [黑白分层图源码](../assets/tikz-schematics/monochrome/layered-heat.tex)、[预览](../assets/tikz-schematics/monochrome/layered-heat.png)、[矢量PDF](../assets/tikz-schematics/monochrome/layered-heat.pdf)。

[编译与来源报告](../assets/tikz-schematics/monochrome/COMPILE_REPORT.json) 保留真实工具版本、退出码、历史来源和新资产哈希；[黑白样式卡](../assets/tikz-schematics/monochrome/STYLE_REFERENCE_CATALOG.json) 可供新图建立自己的 `style_reference`。用户批准的是黑白默认要求，并未实看认可这两张新成图；作者重开检查不代替非作者审查。重建命令为 `python scripts/build_monochrome_templates.py --output-dir NEW_DIR --pdftoppm PATH_TO_PDFTOPPM`，只在新目录编译，不覆盖历史或安装资产。

以下旧彩色文件及其历史回执原样保留，供构图参考或明确请求的历史复现，不再作为默认色彩方案；旧回执不认证新黑白资产：

- [受力图源码](../assets/tikz-schematics/force-balance.tex)、[PNG预览](../assets/tikz-schematics/force-balance.png)、[矢量PDF](../assets/tikz-schematics/force-balance.pdf)。
- [传热图源码](../assets/tikz-schematics/layered-heat.tex)、[PNG预览](../assets/tikz-schematics/layered-heat.png)、[矢量PDF](../assets/tikz-schematics/layered-heat.pdf)。
- [原始两图审查回执](../assets/tikz-schematics/REVIEW.json)：历史 `same-family-fresh` 审查与六个源文件/输出哈希，范围仅两张演示。回执中原论文页面相对路径属于当时工作目录，不是安装后的运行依赖；新图不能沿用该回执作为自己的审查。

先打开与本题最相近的随包预览，再决定借鉴项。素材来源路径不可用时这些原创模板仍可使用。不要把参考论文截图、水印或源论文的参数带入新题。

## 继承什么

### 受力图：紧凑线稿与数学构造

默认轮廓、向量、文字全部纯黑，白底；主轮廓较粗、辅助线细虚线、尺寸线较细，作用方向用箭头和标签而非颜色区分。旧深蓝灰/蓝/暖色版本只保留为历史参考，不把浅灰辅助线带入当前默认。

命名坐标构造端点和质心，角弧由 `atan2` 求出，杆长尺寸线平行于构件并沿法向偏移；力臂是到作用线的垂直距离。保留铰支/固支的区别，不为美观移动受力点。不同作用点的力不能不加条件地合并到同一点。

演示是均匀刚杆AB铰支于A，B承受向左水平力F，C为中点并承受重力G。静力平衡要求 `F L sin(theta) = G L cos(theta)/2`，箭头长度不表示力大小。新题必须重建自己的模型和作用点，不继承演示数值。

### 分层图：实体、界面和边界条件对应

默认用黑色区域边界、不同剖面线及材料标签区分层，不铺彩色或灰色底。尺寸线与坐标轴分行；少量黑色边线表达厚度，不作灰阶阴影，也不代表三维求解。理想接触条件标在界面附近，文字、符号和热流箭头分层布局。旧砂色/浅青/浅蓝版本仅保留历史。

演示仅适用于一维稳态、等截面积、无内热源、理想层间接触且左热右冷的情景。`k_i` 为导热系数，温度连续式指在界面 `x=x_i` 两侧相等，不能理解为整层温度处处相同。用于正文时在图注或符号表说明这些条件。新题有接触热阻、内热源、非稳态或变截面时，必须改关系与标注，不能直接套连续热流箭头。

## 通用扩展而非两张固定模板

可迁移到：整体—部件—微元受力、装置剖面、空间投影、传感器测量、区域/边界、相对坐标、多体耦合、机构运动、真实状态与算法分支。按本题新增TikZ构造，不要求先获得每个题型的成套模板。

选择整体、剖面、分体、局部放大、微元或状态图；单图能说明时不默认四联画。图应解释相邻公式中的对象和量，不在图中堆标题、段落和审计信息。

几何坐标决定关系；布局坐标决定标签与留白。可调整标签、尺寸线偏移、视角和黑白线型，不能改变法向、作用点、交点或角度以迁就布局。空间角先在模型坐标内采样，再与实体使用同一投影。此示意图约定不把结果图的 vivid 配色改成黑白。

## 实际使用与编译

1. 将需要的 `.tex` 复制到当前项目的新图目录再修改，不在Skill资产目录里编译或改写样例。保留题目/模型/符号来源和演示参数与真实参数的区分。
2. 当前模板使用Windows的ctex字体配置；其他系统应选择实际安装的中文字体并重编。依赖XeLaTeX、TikZ、standalone、amsmath、ctex。不要在缺字体时静默输出缺字PDF。
3. 在图目录运行：

```powershell
xelatex --disable-installer -interaction=nonstopmode -halt-on-error -no-shell-escape force-balance.tex
xelatex --disable-installer -interaction=nonstopmode -halt-on-error -no-shell-escape layered-heat.tex
```

`--disable-installer` 是MiKTeX选项；TeX Live省略该选项。捕获退出码和日志；遇到缺包/字体先报告具体依赖，避免后台自动安装对话框无限等待。原测试Windows环境出现过Fandol字体查找阻塞，改用实际存在的Windows字体后通过；这不是所有环境必须使用Windows字体的规则。

4. 保留 `.tex + PDF`；需要预览时将最终PDF渲染为PNG。PNG不是可编辑母版。论文可通过 `\includegraphics[width=115mm]{figures/force-balance.pdf}` 插入；约115mm是这两张图的已检查尺寸，不是所有图的固定宽度。
5. 检查日志中的missing character、未定义命令、overfull等；重开PDF，在实际排版尺寸检查标注、裁切、留白、线宽和公式。不能只看放大的预览。

## 审查与交付边界

按 [独立视觉审查](reference_visual_review.md) 分别检查模型语义和外观。对示意图检查符号、方向、作用点、约束和必要几何恒等式，不要求捏造CSV结果。模型路线变更仍走上游批准；纯布局与样式修改不等于新增模型。

曾出现的实际问题是斜尺寸线穿过 `A_y` 标签。修复方法是移动标签而不移动力作用点，之后重编、重开和重新审查。任何新图或改图都需自己的检查记录，旧样例的“通过”不能自动传播。

TikZ是这两图已实际验证的后端。PGFPlots用于真实解析/数值坐标；Visio须验证所需图元的原生绘制、保存、导出和重开，现有节点连线脚本不等于任意物理示意图支持。用户明确要求可编辑或实际画图时，不转入imagegen/image2。
