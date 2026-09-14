# Contributing

感谢你愿意改进 CUMCM Mathematical Modeling Skills。

这个仓库接受以下类型的贡献：

- 可复现的 Skill bug 修复；
- 数学建模方法覆盖缺口；
- workflow / schema / benchmark 回归案例；
- 可视化、LaTeX、PDF 交付问题；
- 文档、安装和跨平台兼容性改进；
- 能明确提升建模质量、稳定性或可解释性的新增能力。

## 贡献原则

1. **不要为了流程完整而增加默认流程。** `standard` 必须保持最短可靠闭环。
2. **复杂度需要有具体理由。** 新模型、新工件或新 gate 应说明它解决了什么失败模式。
3. **验证与声明匹配。** 不把内部稳定性、单次运行或 schema PASS 包装成数学正确性证明。
4. **不要提交伪造数据、结果或引用。** 示例数据必须明确标注为 synthetic / fixture。
5. **严格审计保持显式 opt-in。** provenance-heavy 机制不要重新变成普通任务默认路径。
6. **保留第三方许可证与归属。** 引入或实质改造第三方内容时必须同步更新 `THIRD_PARTY_NOTICES.md`。

## 建议工作流

1. 从最新 `main` 创建分支；
2. 只修改与目标问题有关的文件；
3. 增加或更新能防止回归的测试；
4. 本地运行相关测试；
5. 提交 Pull Request，说明问题、修改、验证和兼容性影响。

## 本地环境

```powershell
cd packages\math-modeling-skills-complete-20260903
py -m pip install -r requirements.txt
.\check_environment.ps1
```

根级回归：

```powershell
cd ..\..
py -m unittest discover -s tests -p "test_*.py" -v
```

如果只修改某个 Skill，优先先运行与该 Skill 对应的局部测试，再运行受影响的根级回归。

## Pull Request 请说明

- 问题是什么；
- 为什么现有行为不够；
- 修改了什么；
- 如何验证；
- 是否改变默认 `standard` 行为；
- 是否影响 schema、benchmark、发布包或第三方许可证。

对于模型类贡献，建议额外说明：假设、适用范围、失败边界、基线，以及为什么复杂度值得增加。

## 不建议的贡献

- 只为了“更高级”而替换为深度学习模型；
- 固定要求每题多 seed / 消融 / benchmark / 多 Agent 审查；
- 把比赛答案、未授权资料或不可公开数据直接提交到仓库；
- 引入运行时必须联网但没有明确必要性的依赖；
- 仅改变措辞却声称提高了数学正确性或获奖概率。

## Release

版本发布由仓库维护者通过 `release-package` workflow 从 `main` 显式触发。不要手工覆盖已有 GitHub Release 或修改既有 tag。
