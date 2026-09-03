# GitHub 画图方法来源与边界

核对日期：2026-09-02。以下提交只用于方法审阅、许可证归属和可复现来源记录；本 Skill 已把需要的规则和脚本本地化，运行时不访问这些仓库，也不使用 GitHub 状态作为门控。

| 来源 | 固定提交 | 许可证 | 本地化范围 |
|---|---|---|---|
| [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) | `6b7a2e417500561a5ecdd0b168332f4142584617` | MIT, Copyright (c) 2026 Jim Liu | 审阅 `baoyu-diagram` 的图型分类、先语义后布局、分层绘制和间距检查；重新表达为白底 CUMCM/Visio/FigureSpec 规则，未复制其深色设计系统、网络字体或 TypeScript 运行链。 |
| [pedrohcgs/claude-code-my-workflow](https://github.com/pedrohcgs/claude-code-my-workflow) | `9d371f0bf8a8bc99569feca3210ef5133af28d33` | MIT, Copyright (c) 2026 Pedro H. C. Sant'Anna | 审阅图形预检、最终尺寸重开、显式坐标/节点尺寸和避免文字/连线碰撞的方法；改写为数模 PDF 与原生后端检查。 |
| [Orchestra-Research/AI-Research-SKILLs](https://github.com/Orchestra-Research/AI-Research-SKILLs) | `773a52944ba4747a18bd4ae9ade53fff041adcbc` | MIT, Copyright (c) 2025 Claude AI Research Skills Contributors | 审阅 `academic-plotting` 的数据图/结构图分流、图型选择、色盲安全和矢量交付；未继承 Gemini、API key、ML 会议模板和固定多次生成。 |
| [wanshuiyin/Auto-claude-code-research-in-sleep](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep) | `94d8093ed21d20a790830318190095b9f5036ce8` | MIT, Copyright (c) 2026 wanshuiyin | `scripts/figure_renderer.py` 由 ARIS FigureSpec 渲染器本地化而来；删除 `ARIS_REPO` 和外部 shim 依赖，继续按 MIT 归属。完整许可证见数学建模总控 Skill 的 `references/aris-derived/ARIS_MIT_LICENSE.txt`。 |
| [Imbad0202/academic-research-skills](https://github.com/Imbad0202/academic-research-skills) | `94436237913091d4739870159d241660527e8338` | CC BY-NC 4.0, Copyright (c) 2026 Cheng-I Wu | 仅用于对照审阅。由于带 NonCommercial 限制，本活动 Skill 未复制或改造其文字、代码、模板和固定 APA 规则；表格中的通用图型选择由本包独立重写。 |

## 未继承的行为

- Git clone、GitHub API、提交、PR、远端状态或网络可达性门控；
- Gemini、VLM 或其他云端图像模型依赖；
- 外部字体、暗色背景、ML 会议尺寸或 APA 固定格式；
- 固定审查轮数、固定生成次数和“突出我方方法”的视觉偏置；

## 许可证处理

`figure_renderer.py` 是实质性代码派生，文件头保留来源和 MIT 归属，并由上述完整 MIT 文本覆盖。其余规则为针对数学建模重新撰写的方法综合，不逐字复制上游说明。第三方商标 Origin、OriginPro、Visio、Microsoft 和 GitHub 仅用于说明兼容后端，不表示这些厂商为本 Skill 背书。
