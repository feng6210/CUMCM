---
name: mm-signal-image-trajectory
description: Analyze spectra, images, video-derived trajectories, peaks, periodicity, geometric events, and pose features for mathematical modeling. Use for FFT, filtering, peak detection, spatial geometry, collision events, and time-aligned trajectory features. Do not infer physical or causal conclusions from processed signals without calibration and validation.
---

# 数学建模：信号、图像与轨迹

## Purpose

覆盖光谱、传感器信号、图像/视频测量和几何轨迹题，形成“采样与标定—特征提取—物理/统计模型—交叉验证”的证据链。

## When to use

- 题目包含频谱、波峰、周期、干涉、传感器或时序信号。
- 需要从图像/视频提取位置、姿态、角度、速度或事件时间。
- 需要碰撞检测、可见性、空间几何或轨迹相交分析。

## When not to use

- 原始媒体质量不足且没有标定信息。
- 只凭可视化主观挑选峰值或关键帧。
- 需要的是普通表格分类而无时空结构。

## Required inputs

- 原始信号/图像/视频与采样率、时间戳、单位和标定信息。
- 目标事件、峰、频率、几何量或轨迹特征定义。
- 滤波、插值、窗口、阈值和缺帧处理规则。
- 可用于校验的人工标注、物理关系或多角度/多设备数据。

## Workflow

1. 保存原始数据并记录采样/标定元数据。
2. 检查混叠、非均匀采样、缺帧、噪声、漂移和坐标系。
3. 预先定义滤波、窗口、峰值或事件规则，避免看图后调阈值。
4. 提取频域、时域、几何或轨迹特征，并保留中间结果。
5. 用合成信号、人工标注、跨角度或物理公式交叉验证。
6. 报告分辨率、误差、失败片段和不可识别情况。

先读 [signal_trajectory_guide.md](references/signal_trajectory_guide.md)。均匀/非均匀采样频谱可运行 `scripts/signal_spectrum.py`，轨迹事件可运行 `scripts/trajectory_events.py`。

## Output format

```markdown
## 数据与标定
## 预处理规则
## 特征/事件定义
## 模型与结果
## 交叉验证
## 分辨率和失败边界
```

## Quality checks

- FFT 前检查采样是否均匀，报告窗口、去均值、零填充和频率分辨率。
- 视频按对象或视频分组验证，不把相邻帧随机分到训练与测试。
- 几何碰撞用连续距离或足够严格的时间步长检查，不能只看动画。
- 插值与滤波不能创造超出原采样分辨率的精度。
- 逆几何、CT/频谱、车辆轨迹和多目标事件匹配均先做标定、坐标/采样一致性及可辨识性检查。
- 轨迹速度、碰撞和转向事件使用连续或有严格误差上界的检测；渲染轨迹不能作为事件发生的唯一证据。
- 图像/视频/光谱验证按对象、序列或批次分组，禁止相邻帧泄漏；预处理参数随折保存。

## Academic integrity boundaries

- 不隐藏被剔除的帧、峰或异常片段。
- 不把后验选择的频带、阈值或关键帧写成预先设定。
- 不伪造标定精度、识别率或物理验证。

## CUMCM 交接产物

返回 `inputs`、`assumptions`、`model_and_solver`、`machine_readable_results`、`diagnostics`、`unresolved_risks`、`latex_equations` 和 `recommended_figures`；采样率、标定、关键预处理及精度边界必须可追溯。
