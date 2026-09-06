# 全量样式库：图片变体、教程图型、技巧与可运行适配器

## 入口与范围

`assets/full-corpus/catalog.json` 是全量检索入口，不再以六张代表卡限制可选风格。来源快照：145 文件、68 张独立图片路径、37 份源码、26 份 TXT、8 页扫描教程、1 份 Word 导出说明、数据及原生图形。18 个目录含图片；另一个“赠Matlab小技巧”目录属于技巧，不是第19种图型。来源目录新增文件后重新 scan/verify，不能拿旧计数宣称当前全覆盖。

每张图片单独保留 `card_id`、原始路径/hash、近似色板、构图、标记、三维视角、具体观察与风险。相同图型、相同配色乃至字节重复都不自动丢弃原路径；多面板图必须逐项识别其成分，不能按文件夹名只继承其中一个面板。

- `catalog.json → cards`：68 个图片变体；原图仅按本地路径读取，不复制进分发包。
- `catalog.json → code_audit → tutorial_slots`：A01–E10 共50个命名槽位，保留95个已实现语言段与5个MATLAB缺段记录；命名槽位不是50种独立正确图型。
- `catalog.json → code_audit → files`：37份源码和26份技巧逐文件完整阅读记录及SHA-256。
- `assets/corpus-adapters/`：原创重实现的基础图型 spec、明确 DEMO_ONLY 的CSV和预览。支持列表与输入协议以 `render_corpus_chart.py --schema` 为准。该目录的 `catalog.json` 是22张原创基础卡的hash索引；原图不可用或直接采用基础模板时，可用 `adapter-<family>` 作为 `style_reference.card_id` 并绑定此catalog及实际PNG，不伪造原图对照。
- `assets/style-library/`：原有六张组合卡及验证过的预览继续保留。完整画廊通过命令生成到工作输出目录，不把本机临时URL作为运行依赖。

## 实际调用：先找全部，再选择，不只拿六卡套题

从 Skill 目录执行（Python 可为当前项目环境）：

```powershell
python scripts/corpus_style_library.py search --query "三维"
python scripts/corpus_style_library.py search --query "核密度"
python scripts/corpus_style_library.py select --id variant-实际ID
python scripts/corpus_style_library.py gallery --output 新目录/gallery.html --source-root "D:/数模文件/画图"
python scripts/corpus_style_library.py verify --source-root "D:/数模文件/画图"
python scripts/render_corpus_chart.py --schema
```

`search` 同时检索图片、教程槽位和技巧。`select` 返回基础适配器、原图是否存在且hash匹配，以及可供 `FIGURE_INTENT` 使用的 `style_reference`。目录搬迁时传 `--source-root`。不可访问原图时仍能使用已蒸馏色板/构图文字与随包原创预览，但应绑定实际查看的基础卡，不假称与无法访问的原图完成视觉对照。

对找到的候选，按“读者任务/数据结构 → 具体变体的配色与构图 → 可运行基础 → 本题定制”使用：

1. 打开原图或可用原创预览，挑出需要继承的颜色角色、标记、空心/实心、框线、布局、透明层级和视角，记录到本题spec。
2. 基础适配器只覆盖其公开schema。多面板、柱点区间组合、聚类热图、火山图等复杂成分不可因基础图型存在便称完整实现；用已有结果分别绘制后组合，或新增适配脚本并验证。
3. 数据与方法属于上游：真实区间、拟合、KDE、相关系数、聚类树、标准化、显著性与累计百分比先计算并验证，再交给渲染器。缺少这些结果时明确报缺，不用随机数/手写星号补齐。
4. 按最接近的模板复制spec，再填写本题字段。不会自动把近似色板中的任意颜色当连续量颜色映射；零中心量需要对称发散色域。
5. 三维视角、渐变、鲜明配色、面积层叠都可用；检查遮挡与颜色语义。不是为了覆盖所有样式而把所有样式画进同一篇论文。
6. 渲染、重开、最终尺寸独立审查后，才对该张真实图作交付判断。改数据/图/spec后重审。

## 状态不可合并

| 状态 | 意义 | 不意味着 |
|---|---|---|
| `VIEWED` | 原始图片确已打开查看 | 完整复刻或原图科学正确 |
| `SOURCE_READ_NOT_RUNTIME_VERIFIED` | 原代码已读并记录语义 | 原代码可直接运行 |
| `REFERENCE_ONLY_NOT_EXACTLY_REPRODUCED` | 变体已入库可检索、可作为风格依据 | 68张均有逐张相同布局模板 |
| `BASE_ADAPTER_AVAILABLE` | 类似基础图型有spec入口 | 原图所有复合面板已适配 |
| `RUNTIME_VERIFIED` | 某次原创模板渲染与文件重开通过 | 独立视觉PASS、模型或结论PASS |
| `CUSTOM_ADAPTATION_REQUIRED` | 风格仍在库，但该组成需定制 | 不收录、不允许使用该样式 |

现有六卡的独立视觉审查不自动覆盖新增基础模板；新增模板通过运行测试后仍需逐图视觉检查。原生 MATLAB/Origin/Visio 当前是否可用，以运行时探测与实际文件重开为准，不能由 Python 适配器通过替代。

## 教程中的重要修正，不删除样式

- 3D 等高线不能用曲面冒名；彩色线必须有真实连线或明确叫彩色散点。
- KDE必须来自声明的样本/带宽；解析正态密度不是样本KDE。
- 瀑布图的起始/最终总量从零起画，增量才从前序累计起画。
- 马赛克面积按联合频数编码，等宽堆叠柱不能冒名。
- 层次树与矩形树图是不同图型；模型先输出已验证树/布局，绘图不偷偷做聚类。
- 色条必须绑定图上实际使用的颜色映射；箭长缩放不是密度，也不表示不存在的速度色编码。
- `shading interp` 是着色插值，不是统计平滑。插值、平滑和拟合不得混淆。
- 表内赛题分类仅做检索提示；图的好看程度、获奖标签均不能证明本题适用。

## 本地参考与可分发资产

没有发现明确源库再分发许可，不等于不能在本机全量参考。全部来源路径、hash、原创观察和原创适配均可用于当前本机任务；不把源图片、源码、MAT数据直接放进公开Skill包。包内提供原创预览与synthetic演示数据。运行不需要 GitHub、原始D盘目录或云生成；科研插图仍按独立 `scientific_illustration_workflow.md` 路由可用的 imagegen/image2，定量图不走生成模型。
