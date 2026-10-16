# Change Log

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 规范，
并遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.0.0] - 2026-10-16

首个正式版本。🎉

### Added

- **评估引擎**：确定性的百分比灰度（rollout）与多变体分流，基于 MurmurHash3 一致性哈希；同一 `(flag, bucket_key)` 组合的评估结果跨进程、跨平台、跨版本稳定
- **OpenFeature 兼容语义**：理由码 `TARGETING_MATCH` / `SPLIT` / `DEFAULT` / `DISABLED` / `ERROR`，类型化取值 API 与 evaluation details
- **Targeting 规则引擎**：12 种条件操作符（`in` / `not_in` / `exists` / `not_exists` / `gt` / `gte` / `lt` / `lte` / `starts_with` / `ends_with` / `contains` / `matches`），多条件 AND、规则优先级、规则内百分比
- **双格式配置**：JSON 完整支持 + 内置零依赖 YAML 子集解析器（块映射/块序列/块标量/引号/注释）
- **严格校验**：key 命名、变体类型匹配、权重和、未知字段拒绝、重复项检测，错误信息携带字段路径
- **CLI**：`init` / `validate` / `list` / `show` / `eval` / `gate` / `diff` / `lint` / `export` / `hash` / `serve` / `tui` 十二个子命令，文档化退出码（0/1/2/3）
- **CI 门禁**：`gate` 子命令支持断言式评估校验；`lint` 内置 8 条工程最佳实践规则并支持 `--fail-on` 阈值
- **差异评审**：`diff` 输出新增/删除/变更 flag 及风险分级（info/warning/critical）
- **本地 HTTP API**：基于标准库 `http.server` 的 REST 评估端点（默认仅监听 127.0.0.1）
- **终端 TUI 演练场**：curses 交互界面（flag 列表、上下文编辑、实时评估、配置热重载），不可用时优雅降级
- **多导出格式**：`json` / `table` / `markdown` / `env`（shell 可 `eval`）/ JSON Schema
- **GitHub Actions**：`ci.yml`（三平台 × 四版本矩阵：语法检查 + 单元测试 + CLI 冒烟）与 `publish.yml`（Release 触发 PyPI Trusted Publishing）
- **文档**：README 覆盖简体中文 / 繁體中文 / English 三个完整版本

[1.0.0]: https://github.com/gitstq/FlagForge/releases/tag/v1.0.0
