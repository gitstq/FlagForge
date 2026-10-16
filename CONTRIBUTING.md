# 贡献指南 | Contributing Guide

感谢你对 FlagForge 的关注！欢迎任何形式的贡献：Bug 修复、新功能、文档改进、测试补充。

Thanks for your interest in FlagForge! Contributions of all kinds are welcome.

## 提交规范 | Commit Convention

本项目遵循 [Angular Commit Convention](https://github.com/angular/angular/blob/main/CONTRIBUTING.md#-commit-message-format)：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**允许的 type**：

| type | 含义 |
| --- | --- |
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档变更 |
| `refactor` | 重构（不改变外部行为） |
| `test` | 测试补充或修改 |
| `chore` | 构建/工程化/杂项 |

示例：

```
feat(engine): add SEMVER condition operator

Closes #42
```

## Pull Request 规则 | Pull Requests

1. **一个 PR 只做一件事**——保持变更可评审
2. 提交前本地完成：
   ```bash
   python -m compileall -q flagforge tests   # 语法校验（零依赖）
   python -m unittest discover -s tests      # 单元测试（零依赖）
   ```
3. 新功能必须附带单元测试，且测试覆盖率不得下降
4. 涉及评估语义的变更必须更新 `docs/` 与 README 中的语义说明
5. PR 描述需包含：动机、变更点、测试方式、兼容性影响

## Issue 反馈规则 | Issues

* **Bug 报告**：请附带最小可复现配置（flag 文件片段 + 上下文 + 期望/实际结果 + Python 版本）
* **功能建议**：请说明使用场景、期望的 API/CLI 形态、与 OpenFeature 规范的关系
* **安全问题**：请勿公开提交，详见 [SECURITY](README.md#-开源协议说明) 一节

## 代码风格 | Code Style

* 仅使用 Python 标准库（零依赖是本项目的核心约束，新增依赖需要充分论证）
* 兼容 Python 3.9+，不使用 `match` 语句与 `X | Y` 运行时类型标注
* 公共 API 需要 docstring，注释解释"为什么"而非"做什么"
* 评估引擎的任何变更都必须保证：**同一输入永远得到同一输出**（确定性）

## 测试 | Testing

```bash
# 运行全部测试
python -m unittest discover -s tests -v

# 运行单个测试模块
python -m unittest tests.test_engine -v
```

测试同样基于标准库 `unittest`，无需安装任何依赖。

## 许可 | License

提交 PR 即表示你同意以 [MIT License](LICENSE) 发布你的贡献。
