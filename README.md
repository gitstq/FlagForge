# 🎛️ FlagForge

**轻量级本地优先功能开关引擎 | Lightweight Local-First Feature Flag Engine**

<p>
  <a href="https://github.com/gitstq/FlagForge/actions"><img alt="CI" src="https://img.shields.io/badge/CI-passing-brightgreen"></a>
  <a href="https://pypi.org/project/flagforge/"><img alt="PyPI" src="https://img.shields.io/badge/PyPI-flagforge-blue"></a>
  <a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/Python-3.9%2B-blue"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/License-MIT-yellow"></a>
  <img alt="Dependencies" src="https://img.shields.io/badge/dependencies-0-success">
  <img alt="OpenFeature" src="https://img.shields.io/badge/OpenFeature-compatible-orange">
</p>

**🌐 语言 / Language / 語言：**
[简体中文](#zh-cn) · [繁體中文](#zh-tw) · [English](#en)

---

<a id="zh-cn"></a>

# 🎛️ FlagForge — 轻量级本地优先功能开关引擎

## 🎉 项目介绍

**FlagForge** 是一个**零依赖、纯 Python 标准库**实现的功能开关（Feature Flags）引擎。它让你用一份 YAML/JSON 配置文件，就能获得：

* 🎯 **确定性的百分比灰度**——同一用户永远落在同一个桶，跨进程、跨平台、跨版本稳定
* 🧪 **多变体 A/B 实验**——按权重分流，实验数据不串组
* 🎯 **精细定向**——12 种条件操作符，按套餐、地区、邮箱域名、自定义维度精准命中
* 🛑 **Kill Switch 熔断**——一个配置字段随时下线高危功能
* 🔌 **OpenFeature 兼容语义**——理由码与 API 形态对齐社区标准

**解决的痛点**：

* 💸 商业功能开关平台（LaunchDarkly 等）价格高昂，中小团队难以承受
* 🏋️ 自建平台需要数据库 + 服务端 + Web UI，运维成本重
* 🔒 评估上下文含敏感信息，不希望外发到第三方 SaaS
* 📦 引入语言绑定 SDK 会带来依赖树膨胀

**自研差异化亮点**：

* ⚡ **零依赖**：只用 Python 标准库，`pip install flagforge` 不带任何第三方包
* 🧮 **确定性分桶**：基于 MurmurHash3 的一致性哈希，`(flag, bucket_key)` → 桶编号是纯函数
* 📄 **双格式配置**：JSON 完整支持 + 内置 YAML 子集解析器（刻意避开 YAML 规范中易引发意外的特性）
* 🖥️ **CLI + TUI + HTTP API 三形态**：命令行、终端交互演练场、本地 REST 服务，按需取用
* 🚦 **CI 门禁一等公民**：`gate` 子命令让"发布前断言开关状态"成为流水线的一步

**灵感来源**：OpenFeature 规范（评估语义与理由码）、go-feature-flag / GrowthBook / Unleash（产品逻辑）、LaunchDarkly（分桶实践）。FlagForge 参考其产品逻辑**独立自研**，未复制任何代码。

## ✨ 核心特性

| 特性 | 说明 |
| --- | --- |
| 🎯 **百分比灰度** | `percentage: 25` 即 25% 流量命中，调整百分比不影响其他 flag |
| 🧪 **多变体分流** | `variants: {a: 50, b: 50}` 在灰度流量内按权重分配 |
| 🔑 **确定性分桶** | MurmurHash3 纯函数，同输入同输出，支持 `bucket_salt` 整体洗牌 |
| 🎯 **Targeting 引擎** | `in` / `not_in` / `exists` / `gt` / `matches` 等 **12 种操作符**，多条件 AND |
| 📊 **规则内百分比** | 单条规则可带 `percentage`，未命中自动回落后续规则 |
| 🛑 **状态机** | `state: on/off`，关闭时返回默认变体（reason = `DISABLED`） |
| 🔌 **OpenFeature 兼容** | `TARGETING_MATCH` / `SPLIT` / `DEFAULT` / `DISABLED` / `ERROR` 理由码 |
| 📝 **严格校验** | key 命名、变体类型、权重和、未知字段、重复项——错误信息带字段路径 |
| 🧰 **YAML 子集解析器** | 内置零依赖解析器：块映射/块序列/块标量/引号/注释 |
| 💻 **CLI 全家桶** | `init` `validate` `list` `show` `eval` `gate` `diff` `lint` `export` `hash` `serve` `tui` |
| 🚦 **CI 门禁** | `gate --expect flag=value` 断言式校验，非零退出码 |
| 🔍 **配置 lint** | 8 条最佳实践规则：缺 owner、僵尸 flag、无效灰度、命名规范…… |
| 🔀 **差异评审** | `diff` 输出字段级变更与风险分级（info/warning/critical） |
| 🌐 **HTTP API** | 标准库 `http.server`，`GET/POST /evaluate` 即查即用 |
| 🖥️ **TUI 演练场** | curses 交互界面：上下文编辑、实时评估、配置热重载 |
| 📤 **多格式导出** | `json` / `table` / `markdown` / `env`（shell 可 `eval`）/ JSON Schema |

## 🚀 快速开始

### 环境要求

* 🐍 **Python 3.9+**（3.10/3.11/3.12/3.13 均经 CI 验证）
* 🚫 **零第三方依赖**——无需虚拟环境也能运行
* 💻 跨平台：Windows / macOS / Linux（TUI 需要 curses，Windows 原生 Python 不支持，将自动降级）

### 安装

```bash
# 方式一：PyPI（推荐）
pip install flagforge

# 方式二：从源码
git clone https://github.com/gitstq/FlagForge.git
cd FlagForge
python -m flagforge --help
```

### 30 秒上手

```bash
# 1️⃣ 生成示例配置
flagforge init

# 2️⃣ 校验配置合法性
flagforge validate

# 3️⃣ 列出全部开关
flagforge list

# 4️⃣ 在指定上下文中评估
flagforge eval new-checkout -c targetingKey=user-42

# 5️⃣ 交互式演练场
flagforge tui
```

预期输出：

```
$ flagforge eval new-checkout -c targetingKey=user-42
new-checkout -> enabled (value=true, reason=SPLIT)
```

## 📖 详细使用指南

### 配置文件格式

顶层结构（YAML 示例）：

```yaml
flags:
  - key: new-checkout          # 必填：flag 标识（字母/数字/._-，≤128 字符）
    description: 新版结账流程   # 推荐：一句话说明意图
    state: on                  # on | off
    variant_type: boolean      # boolean | string | integer | float | object
    variants:                  # 必填：至少一个变体
      enabled: true
      control: false
    default_variant: control   # 必填：默认变体名
    rollout:                   # 可选：百分比灰度
      percentage: 25
      variant: enabled
      bucket_by: targetingKey
    targeting:                 # 可选：定向规则（按顺序匹配）
      - id: employees
        conditions:
          - field: email
            op: ends_with
            values: ["@example.com"]
        variant: enabled
    bucket_salt: ""            # 可选：重新洗牌灰度流量
    metadata:                  # 可选：owner / tags / updated_at 等
      owner: team-payments
      tags: [checkout]
      updated_at: "2026-10-16"
```

字段速查：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `key` | ✅ | flag 标识，仓库内唯一 |
| `state` | ✅ | `on` / `off` |
| `variant_type` | ✅ | 变体值类型，用于类型校验 |
| `variants` | ✅ | `{变体名: 值}`，至少一项 |
| `default_variant` | ✅ | 未命中任何规则时返回的变体 |
| `rollout` | ➖ | `percentage` + `variant`（或加权 `variants`）二选一 |
| `targeting` | ➖ | 规则数组，按顺序短路匹配 |
| `bucket_salt` | ➖ | 修改后同批用户重新分桶 |
| `metadata` | ➖ | `owner` / `team` / `tags` / `updated_at`（lint 会读取） |

### 评估语义

评估严格按以下顺序短路执行：

```
flag.state == off ──────────────► DISABLED（默认变体）
        │ on
        ▼
逐条 targeting 规则（按配置顺序）
  条件全部命中？
    ├─ 规则无 percentage ───────► TARGETING_MATCH（规则变体）
    └─ 规则有 percentage
         ├─ 分桶命中 ───────────► TARGETING_MATCH（规则变体）
         └─ 分桶未命中 ─────────► 继续下一条规则
        │
        ▼
flag.rollout（百分比灰度）
  分桶命中 ────────────────────► SPLIT（灰度变体 / 加权变体）
  分桶未命中 ──────────────────► DEFAULT（默认变体）
```

**确定性保证**：桶编号 = `murmur3_32(bucket_salt + flag_key + "\x1f" + bucket_key) % 100`。
同一 `(flag, bucket_key)` 永远得到同一结果——你可以放心在测试、CI、生产中得到一致行为。

调试分桶：

```bash
flagforge hash bucket new-checkout user-42 --samples 10000
```

### Targeting 条件操作符

| 操作符 | 语义 | 示例 |
| --- | --- | --- |
| `in` / `not_in` | 等于/不等于任一值 | `plan in [pro, ent]` |
| `exists` / `not_exists` | 字段存在（非 null） | `beta exists` |
| `gt` / `gte` / `lt` / `lte` | 数值或字符串比较 | `seats gt 20` |
| `starts_with` / `ends_with` | 字符串前后缀 | `email ends_with @example.com` |
| `contains` | 字符串包含或数组成员 | `roles contains admin` |
| `matches` | 正则 `re.search` | `email matches .+@example\.com$` |

同一规则内的多个条件是 **AND** 关系；字符串 `"true"` 与布尔 `true` 在 `in` 中宽松相等（避免 CLI/YAML 类型歧义）。

### CLI 命令参考

| 命令 | 用途 | 关键参数 |
| --- | --- | --- |
| `init` | 生成示例配置 | `-o 路径` `--force` |
| `validate` | 校验合法性 + 语义警告 | `--format json` |
| `list` | 列出开关 | `--state on` `--tag x` `--owner team` `--evaluated` |
| `show <key>` | 单个开关详情 + 当前评估 | `--format json` |
| `eval [key]` | 评估（省略 key 则全量） | `-c k=v` `--format json` |
| `gate` | CI 断言门禁 | `--expect flag=value`（可多次） |
| `diff <old> <new>` | 差异对比 + 风险分级 | `--format json` |
| `lint` | 最佳实践检查 | `--stale-days 90` `--fail-on warning` |
| `export` | 导出 | `--format json\|table\|markdown\|env\|schema` |
| `hash murmur\|bucket` | 分桶调试 | `--samples N` `--salt x` |
| `serve` | 本地 HTTP API | `--host` `--port` |
| `tui` | 终端演练场 | `-c k=v` |

**退出码**：`0` 成功 · `1` 用法/运行时错误 · `2` 校验失败 · `3` 门禁断言失败。

### 典型场景

**① 灰度发布（25% → 50% → 100%）**

```bash
# 编辑配置后先 diff 评审风险
flagforge diff flags.yaml flags.new.yaml

# 流水线中断言：灰度比例下，内部邮箱必须命中新流程
flagforge gate --file flags.yaml \
  --expect new-checkout=true \
  -c targetingKey=ci-user,email=ci@example.com
```

**② A/B 实验多变体**

```yaml
rollout:
  percentage: 50
  variants:
    variant-a: 50
    variant-b: 50
```

**③ Kill Switch**

```yaml
- key: legacy-api
  state: off        # 紧急时改为 on 即刻下线
  variants: {on: true, off: false}
  default_variant: off
```

**④ Shell 集成**

```bash
eval "$(flagforge export --format env -c targetingKey=user-42)"
echo "$FLAGFORGE_NEW_CHECKOUT"   # true
```

### HTTP API

```bash
flagforge serve --port 8765
```

```bash
# 评估（query 形式）
curl "http://127.0.0.1:8765/evaluate?flag=new-checkout&targetingKey=user-42"

# 评估（JSON body）
curl -X POST http://127.0.0.1:8765/evaluate \
  -H 'Content-Type: application/json' \
  -d '{"key":"new-checkout","context":{"targetingKey":"user-42"}}'

# 健康检查 / 全量定义
curl http://127.0.0.1:8765/health
curl http://127.0.0.1:8765/flags
```

> ⚠️ 默认仅监听 `127.0.0.1`。请勿在未加防护的情况下暴露到公网。

### TUI 演练场

```bash
flagforge tui
```

* `↑`/`↓` 或 `j`/`k`：浏览开关
* `/`：按 key 过滤
* `Enter`：编辑上下文（`k=v,k2=v2`），实时重算
* `r`：热重载配置文件
* `q`：退出

### Python API

```python
from flagforge import OpenFeature

of = OpenFeature.from_file("flags.yaml")
client = of.get_client()

# OpenFeature 风格的类型化取值
if client.get_boolean_value("new-checkout", False, {"targetingKey": "user-42"}):
    render_new_checkout()

# 完整评估详情（含 reason）
details = client.get_variant("new-checkout", {"targetingKey": "user-42"})
# {'flag_key': 'new-checkout', 'variant': 'enabled', 'value': True, 'reason': 'SPLIT'}
```

## 💡 设计思路与迭代规划

**设计理念**：

1. **确定性优先**：分桶是纯函数，杜绝"同一用户两次评估结果不同"的灵异事件
2. **配置即代码**：flag 定义进 Git，评审、回滚、审计全部复用现有工程体系
3. **零依赖是特性**：没有传递依赖意味着没有供应链风险、没有版本冲突、没有"升级即破裂"
4. **语义对齐社区**：理由码与 OpenFeature 规范一致，降低团队心智迁移成本

**技术选型**：

* **纯标准库**：`argparse` / `json` / `http.server` / `curses` / `unittest`——任何 Python 3.9+ 环境开箱即用
* **MurmurHash3（x86_32）**：业界广泛使用的分桶哈希（LaunchDarkly 等采用同族算法），雪崩效应保证分布均匀
* **YAML 子集而非完整 YAML**：完整 YAML 规范包含大量"意外特性"（锚点、`yes/no` 布尔、隐式类型），子集化让配置行为**可预测、可测试**；需要完整能力时请使用 JSON

**后续迭代计划**：

* 🔭 **v1.1**：OpenFeature Provider 协议适配（`flagd` 兼容的 `FLAGD` 提供方接口）
* 🌐 **v1.2**：可选的远程配置源（HTTP/etcd 拉取 + 本地缓存 + 轮询）
* 📊 **v1.3**：评估事件埋点与曝光统计接口
* 🧪 **v1.4**：实验显著性计算辅助（频次/转化分析）
* 🌍 **v1.5**：多语言 SDK 代码生成（TypeScript/Go/Rust 客户端）

**社区贡献方向**：新的条件操作符、报告格式、CI 集成示例、文档翻译——见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 📦 打包与部署指南

### 作为 CLI 工具

```bash
pip install flagforge          # PyPI 安装
flagforge --help               # 验证安装
```

### 作为库嵌入

```python
# requirements.txt
flagforge>=1.0.0
```

```toml
# pyproject.toml
[project]
dependencies = ["flagforge>=1.0.0"]
```

### 从源码运行

```bash
git clone https://github.com/gitstq/FlagForge.git
cd FlagForge
python -m flagforge list       # 无需安装，直接以模块方式运行
```

### 版本兼容矩阵

| Python | 3.9 | 3.10 | 3.11 | 3.12 | 3.13 |
| --- | --- | --- | --- | --- | --- |
| 支持状态 | ✅ | ✅ | ✅ | ✅ | ✅ |

| 平台 | Linux | macOS | Windows |
| --- | --- | --- | --- |
| CLI / 库 / HTTP API | ✅ | ✅ | ✅ |
| TUI（curses） | ✅ | ✅ | ⚠️ 需 `pip install windows-curses`，否则自动降级 |

### CI 集成

```yaml
# GitHub Actions 片段
- name: Validate feature flags
  run: |
    pip install flagforge
    flagforge validate --file flags.yaml
    flagforge lint --file flags.yaml --fail-on warning
    flagforge gate --file flags.yaml --expect new-checkout=true -c targetingKey=ci
```

### 发布方式

* **PyPI**：打 Tag 发布 Release 后由 GitHub Actions 自动构建并发布（Trusted Publishing，无需 Token）
* **源码分发**：仓库本身零依赖，直接复制 `flagforge/` 目录即可使用

## 🤝 贡献指南

* 📐 **提交规范**：遵循 Angular Commit Convention（`feat:` / `fix:` / `docs:` / `refactor:` / `test:` / `chore:`）
* 🔬 **PR 要求**：一个 PR 一件事；新功能必须附单元测试；提交前本地执行
  ```bash
  python -m compileall -q flagforge tests
  python -m unittest discover -s tests
  ```
* 🐛 **Issue 要求**：Bug 请附最小复现配置 + 上下文 + 期望/实际结果 + Python 版本
* 🔐 **安全建议**：请勿公开提交安全问题，先建 Issue 说明
* 📖 完整规则见 [CONTRIBUTING.md](CONTRIBUTING.md)

## 📄 开源协议说明

本项目基于 [MIT License](LICENSE) 发布——允许自由使用、修改、分发与商业使用，唯一要求是保留版权声明与许可声明。

---

<a id="zh-tw"></a>

# 🎛️ FlagForge — 輕量級本地優先功能開關引擎

## 🎉 專案介紹

**FlagForge** 是一個**零依賴、純 Python 標準函式庫**實作的功能開關（Feature Flags）引擎。一份 YAML/JSON 設定檔即可擁有：

* 🎯 **確定性的百分比灰度**——同一使用者永遠落在同一個桶，跨程序、跨平台、跨版本穩定
* 🧪 **多變體 A/B 實驗**——依權重分流，實驗資料不串組
* 🎯 **精準定向**——12 種條件運算子，依方案、地區、郵箱網域、自訂維度命中
* 🛑 **Kill Switch 熔斷**——一個設定欄位隨時下線高風險功能
* 🔌 **OpenFeature 相容語義**——理由碼與 API 形態對齊社群標準

**解決的痛點**：

* 💸 商業功能開關平台（LaunchDarkly 等）價格高昂，中小團隊難以負擔
* 🏋️ 自建平台需要資料庫 + 服務端 + Web UI，維運成本沉重
* 🔒 評估上下文含有敏感資訊，不希望外傳至第三方 SaaS
* 📦 引入語言綁定 SDK 會帶來依賴樹膨脹

**自研差異化亮點**：

* ⚡ **零依賴**：只用 Python 標準函式庫，`pip install flagforge` 不帶任何第三方套件
* 🧮 **確定性分桶**：基於 MurmurHash3 的一致性雜湊，`(flag, bucket_key)` → 桶編號是純函式
* 📄 **雙格式設定**：JSON 完整支援 + 內建 YAML 子集解析器（刻意避開 YAML 規範中易引發意外的特性）
* 🖥️ **CLI + TUI + HTTP API 三形態**：命令列、終端互動演練場、本地 REST 服務，按需取用
* 🚦 **CI 閘門一等公民**：`gate` 子命令讓「發布前斷言開關狀態」成為流水線的一步

**靈感來源**：OpenFeature 規範（評估語義與理由碼）、go-feature-flag / GrowthBook / Unleash（產品邏輯）、LaunchDarkly（分桶實踐）。FlagForge 參考其產品邏輯**獨立自研**，未複製任何程式碼。

## ✨ 核心特性

| 特性 | 說明 |
| --- | --- |
| 🎯 **百分比灰度** | `percentage: 25` 即 25% 流量命中，調整百分比不影響其他 flag |
| 🧪 **多變體分流** | `variants: {a: 50, b: 50}` 在灰度流量內依權重分配 |
| 🔑 **確定性分桶** | MurmurHash3 純函式，同輸入同輸出，支援 `bucket_salt` 整體洗牌 |
| 🎯 **Targeting 引擎** | `in` / `not_in` / `exists` / `gt` / `matches` 等 **12 種運算子**，多條件 AND |
| 📊 **規則內百分比** | 單條規則可帶 `percentage`，未命中自動回落後續規則 |
| 🛑 **狀態機** | `state: on/off`，關閉時回傳預設變體（reason = `DISABLED`） |
| 🔌 **OpenFeature 相容** | `TARGETING_MATCH` / `SPLIT` / `DEFAULT` / `DISABLED` / `ERROR` 理由碼 |
| 📝 **嚴格校驗** | key 命名、變體類型、權重和、未知欄位、重複項——錯誤訊息帶欄位路徑 |
| 🧰 **YAML 子集解析器** | 內建零依賴解析器：區塊映射/區塊序列/區塊純量/引號/註解 |
| 💻 **CLI 全家桶** | `init` `validate` `list` `show` `eval` `gate` `diff` `lint` `export` `hash` `serve` `tui` |
| 🚦 **CI 閘門** | `gate --expect flag=value` 斷言式校驗，非零結束碼 |
| 🔍 **設定 lint** | 8 條最佳實踐規則：缺 owner、殭屍 flag、無效灰度、命名規範…… |
| 🔀 **差異評審** | `diff` 輸出欄位級變更與風險分級（info/warning/critical） |
| 🌐 **HTTP API** | 標準函式庫 `http.server`，`GET/POST /evaluate` 即查即用 |
| 🖥️ **TUI 演練場** | curses 互動介面：上下文編輯、即時評估、設定熱重載 |
| 📤 **多格式匯出** | `json` / `table` / `markdown` / `env`（shell 可 `eval`）/ JSON Schema |

## 🚀 快速開始

### 環境需求

* 🐍 **Python 3.9+**（3.10/3.11/3.12/3.13 均經 CI 驗證）
* 🚫 **零第三方依賴**——無需虛擬環境也能執行
* 💻 跨平台：Windows / macOS / Linux（TUI 需要 curses，Windows 原生 Python 不支援，將自動降級）

### 安裝

```bash
# 方式一：PyPI（推薦）
pip install flagforge

# 方式二：從原始碼
git clone https://github.com/gitstq/FlagForge.git
cd FlagForge
python -m flagforge --help
```

### 30 秒上手

```bash
# 1️⃣ 產生範例設定
flagforge init

# 2️⃣ 校驗設定合法性
flagforge validate

# 3️⃣ 列出全部開關
flagforge list

# 4️⃣ 在指定上下文中評估
flagforge eval new-checkout -c targetingKey=user-42

# 5️⃣ 互動式演練場
flagforge tui
```

預期輸出：

```
$ flagforge eval new-checkout -c targetingKey=user-42
new-checkout -> enabled (value=true, reason=SPLIT)
```

## 📖 詳細使用指南

### 設定檔格式

頂層結構（YAML 範例）：

```yaml
flags:
  - key: new-checkout          # 必填：flag 識別（字母/數字/._-，≤128 字元）
    description: 新版結帳流程   # 推薦：一句話說明意圖
    state: on                  # on | off
    variant_type: boolean      # boolean | string | integer | float | object
    variants:                  # 必填：至少一個變體
      enabled: true
      control: false
    default_variant: control   # 必填：預設變體名
    rollout:                   # 選填：百分比灰度
      percentage: 25
      variant: enabled
      bucket_by: targetingKey
    targeting:                 # 選填：定向規則（依順序匹配）
      - id: employees
        conditions:
          - field: email
            op: ends_with
            values: ["@example.com"]
        variant: enabled
    bucket_salt: ""            # 選填：重新洗牌灰度流量
    metadata:                  # 選填：owner / tags / updated_at 等
      owner: team-payments
      tags: [checkout]
      updated_at: "2026-10-16"
```

欄位速查：

| 欄位 | 必填 | 說明 |
| --- | --- | --- |
| `key` | ✅ | flag 識別，倉庫內唯一 |
| `state` | ✅ | `on` / `off` |
| `variant_type` | ✅ | 變體值類型，用於類型校驗 |
| `variants` | ✅ | `{變體名: 值}`，至少一項 |
| `default_variant` | ✅ | 未命中任何規則時回傳的變體 |
| `rollout` | ➖ | `percentage` + `variant`（或加權 `variants`）二選一 |
| `targeting` | ➖ | 規則陣列，依順序短路匹配 |
| `bucket_salt` | ➖ | 修改後同批使用者重新分桶 |
| `metadata` | ➖ | `owner` / `team` / `tags` / `updated_at`（lint 會讀取） |

### 評估語義

評估嚴格依以下順序短路執行：

```
flag.state == off ──────────────► DISABLED（預設變體）
        │ on
        ▼
逐條 targeting 規則（依設定順序）
  條件全部命中？
    ├─ 規則無 percentage ───────► TARGETING_MATCH（規則變體）
    └─ 規則有 percentage
         ├─ 分桶命中 ───────────► TARGETING_MATCH（規則變體）
         └─ 分桶未命中 ─────────► 繼續下一條規則
        │
        ▼
flag.rollout（百分比灰度）
  分桶命中 ────────────────────► SPLIT（灰度變體 / 加權變體）
  分桶未命中 ──────────────────► DEFAULT（預設變體）
```

**確定性保證**：桶編號 = `murmur3_32(bucket_salt + flag_key + "\x1f" + bucket_key) % 100`。
同一 `(flag, bucket_key)` 永遠得到同一結果——你可以放心在測試、CI、生產中取得一致行為。

除錯分桶：

```bash
flagforge hash bucket new-checkout user-42 --samples 10000
```

### Targeting 條件運算子

| 運算子 | 語義 | 範例 |
| --- | --- | --- |
| `in` / `not_in` | 等於/不等於任一值 | `plan in [pro, ent]` |
| `exists` / `not_exists` | 欄位存在（非 null） | `beta exists` |
| `gt` / `gte` / `lt` / `lte` | 數值或字串比較 | `seats gt 20` |
| `starts_with` / `ends_with` | 字串前綴/後綴 | `email ends_with @example.com` |
| `contains` | 字串包含或陣列成員 | `roles contains admin` |
| `matches` | 正則 `re.search` | `email matches .+@example\.com$` |

同一規則內的多個條件是 **AND** 關係；字串 `"true"` 與布林 `true` 在 `in` 中寬鬆相等（避免 CLI/YAML 類型歧義）。

### CLI 指令參考

| 指令 | 用途 | 關鍵參數 |
| --- | --- | --- |
| `init` | 產生範例設定 | `-o 路徑` `--force` |
| `validate` | 校驗合法性 + 語義警告 | `--format json` |
| `list` | 列出開關 | `--state on` `--tag x` `--owner team` `--evaluated` |
| `show <key>` | 單一開關詳情 + 目前評估 | `--format json` |
| `eval [key]` | 評估（省略 key 則全量） | `-c k=v` `--format json` |
| `gate` | CI 斷言閘門 | `--expect flag=value`（可多次） |
| `diff <old> <new>` | 差異比對 + 風險分級 | `--format json` |
| `lint` | 最佳實踐檢查 | `--stale-days 90` `--fail-on warning` |
| `export` | 匯出 | `--format json\|table\|markdown\|env\|schema` |
| `hash murmur\|bucket` | 分桶除錯 | `--samples N` `--salt x` |
| `serve` | 本地 HTTP API | `--host` `--port` |
| `tui` | 終端演練場 | `-c k=v` |

**結束碼**：`0` 成功 · `1` 用法/執行期錯誤 · `2` 校驗失敗 · `3` 閘門斷言失敗。

### 典型情境

**① 灰度發布（25% → 50% → 100%）**

```bash
# 編輯設定後先 diff 評審風險
flagforge diff flags.yaml flags.new.yaml

# 流水線中斷言：灰度比例下，內部郵箱必須命中新流程
flagforge gate --file flags.yaml \
  --expect new-checkout=true \
  -c targetingKey=ci-user,email=ci@example.com
```

**② A/B 實驗多變體**

```yaml
rollout:
  percentage: 50
  variants:
    variant-a: 50
    variant-b: 50
```

**③ Kill Switch**

```yaml
- key: legacy-api
  state: off        # 緊急時改為 on 即刻下線
  variants: {on: true, off: false}
  default_variant: off
```

**④ Shell 整合**

```bash
eval "$(flagforge export --format env -c targetingKey=user-42)"
echo "$FLAGFORGE_NEW_CHECKOUT"   # true
```

### HTTP API

```bash
flagforge serve --port 8765
```

```bash
# 評估（query 形式）
curl "http://127.0.0.1:8765/evaluate?flag=new-checkout&targetingKey=user-42"

# 評估（JSON body）
curl -X POST http://127.0.0.1:8765/evaluate \
  -H 'Content-Type: application/json' \
  -d '{"key":"new-checkout","context":{"targetingKey":"user-42"}}'

# 健康檢查 / 全量定義
curl http://127.0.0.1:8765/health
curl http://127.0.0.1:8765/flags
```

> ⚠️ 預設僅監聽 `127.0.0.1`。請勿在未加防護的情況下暴露到公網。

### TUI 演練場

```bash
flagforge tui
```

* `↑`/`↓` 或 `j`/`k`：瀏覽開關
* `/`：依 key 過濾
* `Enter`：編輯上下文（`k=v,k2=v2`），即時重算
* `r`：熱重載設定檔
* `q`：離開

### Python API

```python
from flagforge import OpenFeature

of = OpenFeature.from_file("flags.yaml")
client = of.get_client()

# OpenFeature 風格的類型化取值
if client.get_boolean_value("new-checkout", False, {"targetingKey": "user-42"}):
    render_new_checkout()

# 完整評估詳情（含 reason）
details = client.get_variant("new-checkout", {"targetingKey": "user-42"})
# {'flag_key': 'new-checkout', 'variant': 'enabled', 'value': True, 'reason': 'SPLIT'}
```

## 💡 設計思路與迭代規劃

**設計理念**：

1. **確定性優先**：分桶是純函式，杜絕「同一使用者兩次評估結果不同」的靈異事件
2. **設定即程式碼**：flag 定義進 Git，評審、回滾、稽核全部復用現有工程體系
3. **零依賴是特性**：沒有傳遞依賴意味著沒有供應鏈風險、沒有版本衝突、沒有「升級即破裂」
4. **語義對齊社群**：理由碼與 OpenFeature 規範一致，降低團隊心智遷移成本

**技術選型**：

* **純標準函式庫**：`argparse` / `json` / `http.server` / `curses` / `unittest`——任何 Python 3.9+ 環境開箱即用
* **MurmurHash3（x86_32）**：業界廣泛使用的分桶雜湊（LaunchDarkly 等採用同族演算法），雪崩效應保證分佈均勻
* **YAML 子集而非完整 YAML**：完整 YAML 規範包含大量「意外特性」（錨點、`yes/no` 布林、隱含型別），子集化讓設定行為**可預測、可測試**；需要完整能力時請使用 JSON

**後續迭代計畫**：

* 🔭 **v1.1**：OpenFeature Provider 協定适配（`flagd` 相容的提供方介面）
* 🌐 **v1.2**：可選的遠端設定源（HTTP/etcd 拉取 + 本地快取 + 輪詢）
* 📊 **v1.3**：評估事件埋點與曝光統計介面
* 🧪 **v1.4**：實驗顯著性計算輔助（頻次/轉化分析）
* 🌍 **v1.5**：多語言 SDK 程式碼產生（TypeScript/Go/Rust 用戶端）

**社群貢獻方向**：新的條件運算子、報告格式、CI 整合範例、文件翻譯——見 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 📦 打包與部署指南

### 作為 CLI 工具

```bash
pip install flagforge          # PyPI 安裝
flagforge --help               # 驗證安裝
```

### 作為函式庫嵌入

```python
# requirements.txt
flagforge>=1.0.0
```

```toml
# pyproject.toml
[project]
dependencies = ["flagforge>=1.0.0"]
```

### 從原始碼執行

```bash
git clone https://github.com/gitstq/FlagForge.git
cd FlagForge
python -m flagforge list       # 無需安裝，直接以模組方式執行
```

### 版本相容矩陣

| Python | 3.9 | 3.10 | 3.11 | 3.12 | 3.13 |
| --- | --- | --- | --- | --- | --- |
| 支援狀態 | ✅ | ✅ | ✅ | ✅ | ✅ |

| 平台 | Linux | macOS | Windows |
| --- | --- | --- | --- |
| CLI / 函式庫 / HTTP API | ✅ | ✅ | ✅ |
| TUI（curses） | ✅ | ✅ | ⚠️ 需 `pip install windows-curses`，否則自動降級 |

### CI 整合

```yaml
# GitHub Actions 片段
- name: Validate feature flags
  run: |
    pip install flagforge
    flagforge validate --file flags.yaml
    flagforge lint --file flags.yaml --fail-on warning
    flagforge gate --file flags.yaml --expect new-checkout=true -c targetingKey=ci
```

### 發布方式

* **PyPI**：打 Tag 發布 Release 後由 GitHub Actions 自動建置並發布（Trusted Publishing，無需 Token）
* **原始碼散佈**：倉庫本身零依賴，直接複製 `flagforge/` 目錄即可使用

## 🤝 貢獻指南

* 📐 **提交規範**：遵循 Angular Commit Convention（`feat:` / `fix:` / `docs:` / `refactor:` / `test:` / `chore:`）
* 🔬 **PR 要求**：一個 PR 一件事；新功能必須附單元測試；提交前本地執行
  ```bash
  python -m compileall -q flagforge tests
  python -m unittest discover -s tests
  ```
* 🐛 **Issue 要求**：Bug 請附最小重現設定 + 上下文 + 期望/實際結果 + Python 版本
* 🔐 **安全建議**：請勿公開提交安全問題，先建 Issue 說明
* 📖 完整規則見 [CONTRIBUTING.md](CONTRIBUTING.md)

## 📄 開源協議說明

本專案基於 [MIT License](LICENSE) 發布——允許自由使用、修改、散佈與商業使用，唯一要求是保留版權聲明與許可聲明。

---

<a id="en"></a>

# 🎛️ FlagForge — Lightweight Local-First Feature Flag Engine

## 🎉 Introduction

**FlagForge** is a **zero-dependency, pure Python standard library** feature flag engine. With a single YAML/JSON config file you get:

* 🎯 **Deterministic percentage rollouts** — the same user always lands in the same bucket, stable across processes, platforms and versions
* 🧪 **Multi-variant A/B experiments** — weighted splits with no cross-contamination
* 🎯 **Fine-grained targeting** — 12 condition operators on plan, region, email domain, or any custom dimension
* 🛑 **Kill switches** — take a risky feature offline with one config field
* 🔌 **OpenFeature-compatible semantics** — reason codes and API shape aligned with the community standard

**Pain points it solves**:

* 💸 Commercial flag platforms (LaunchDarkly et al.) are expensive for small teams
* 🏋️ Self-hosting a platform means database + server + web UI overhead
* 🔒 Evaluation context may contain sensitive data you don't want sent to third-party SaaS
* 📦 Language-binding SDKs bloat your dependency tree

**What makes this implementation different**:

* ⚡ **Zero dependencies** — standard library only; `pip install flagforge` pulls in nothing
* 🧮 **Deterministic bucketing** — MurmurHash3-based consistent hashing; `(flag, bucket_key)` → bucket is a pure function
* 📄 **Dual-format config** — full JSON support plus a built-in YAML-subset parser that deliberately avoids YAML's surprising corners
* 🖥️ **CLI + TUI + HTTP API** — command line, interactive terminal playground, and local REST service
* 🚦 **First-class CI gating** — the `gate` subcommand makes "assert flag state before release" a pipeline step

**Inspiration**: the OpenFeature specification (evaluation semantics and reason codes), go-feature-flag / GrowthBook / Unleash (product logic), and LaunchDarkly (bucketing practice). FlagForge is an **independent implementation** inspired by their product logic — no code was copied.

## ✨ Core Features

| Feature | Description |
| --- | --- |
| 🎯 **Percentage rollout** | `percentage: 25` hits 25% of traffic; changing it never affects other flags |
| 🧪 **Multi-variant split** | `variants: {a: 50, b: 50}` distributes rollout traffic by weight |
| 🔑 **Deterministic bucketing** | Pure MurmurHash3 function; `bucket_salt` reshuffles traffic globally |
| 🎯 **Targeting engine** | `in` / `not_in` / `exists` / `gt` / `matches` and more — **12 operators**, AND semantics |
| 📊 **Rule-level percentage** | Each rule may carry `percentage`; misses fall through to later rules |
| 🛑 **State machine** | `state: on/off`; off returns the default variant (reason = `DISABLED`) |
| 🔌 **OpenFeature compatible** | `TARGETING_MATCH` / `SPLIT` / `DEFAULT` / `DISABLED` / `ERROR` reason codes |
| 📝 **Strict validation** | key naming, variant typing, weight sums, unknown fields, duplicates — errors carry field paths |
| 🧰 **YAML subset parser** | Built-in zero-dependency parser: block mappings/sequences/scalars, quotes, comments |
| 💻 **Full CLI** | `init` `validate` `list` `show` `eval` `gate` `diff` `lint` `export` `hash` `serve` `tui` |
| 🚦 **CI gating** | `gate --expect flag=value` assertions with non-zero exit codes |
| 🔍 **Config linting** | 8 best-practice rules: missing owner, zombie flags, no-op rollouts, naming… |
| 🔀 **Diff review** | `diff` prints field-level changes with risk levels (info/warning/critical) |
| 🌐 **HTTP API** | Standard-library `http.server`; `GET/POST /evaluate` ready to use |
| 🖥️ **TUI playground** | curses UI: context editing, live evaluation, config hot-reload |
| 📤 **Export formats** | `json` / `table` / `markdown` / `env` (shell-`eval`-able) / JSON Schema |

## 🚀 Quick Start

### Requirements

* 🐍 **Python 3.9+** (3.10/3.11/3.12/3.13 verified in CI)
* 🚫 **Zero third-party dependencies** — no virtualenv required
* 💻 Cross-platform: Windows / macOS / Linux (TUI needs curses; unavailable on native Windows Python and degrades gracefully)

### Installation

```bash
# Option 1: PyPI (recommended)
pip install flagforge

# Option 2: from source
git clone https://github.com/gitstq/FlagForge.git
cd FlagForge
python -m flagforge --help
```

### 30-second tour

```bash
# 1️⃣ Generate a sample config
flagforge init

# 2️⃣ Validate it
flagforge validate

# 3️⃣ List all flags
flagforge list

# 4️⃣ Evaluate with a context
flagforge eval new-checkout -c targetingKey=user-42

# 5️⃣ Interactive playground
flagforge tui
```

Expected output:

```
$ flagforge eval new-checkout -c targetingKey=user-42
new-checkout -> enabled (value=true, reason=SPLIT)
```

## 📖 Detailed Guide

### Config file format

Top-level structure (YAML example):

```yaml
flags:
  - key: new-checkout          # required: flag key (letters/digits/._-, ≤128 chars)
    description: New checkout  # recommended: one-line intent
    state: on                  # on | off
    variant_type: boolean      # boolean | string | integer | float | object
    variants:                  # required: at least one variant
      enabled: true
      control: false
    default_variant: control   # required: fallback variant
    rollout:                   # optional: percentage rollout
      percentage: 25
      variant: enabled
      bucket_by: targetingKey
    targeting:                 # optional: ordered rules
      - id: employees
        conditions:
          - field: email
            op: ends_with
            values: ["@example.com"]
        variant: enabled
    bucket_salt: ""            # optional: reshuffle traffic
    metadata:                  # optional: owner / tags / updated_at, etc.
      owner: team-payments
      tags: [checkout]
      updated_at: "2026-10-16"
```

Field reference:

| Field | Required | Notes |
| --- | --- | --- |
| `key` | ✅ | Flag identifier, unique per file |
| `state` | ✅ | `on` / `off` |
| `variant_type` | ✅ | Value type used for validation |
| `variants` | ✅ | `{name: value}`, at least one entry |
| `default_variant` | ✅ | Variant returned when nothing matches |
| `rollout` | ➖ | `percentage` + `variant` (or weighted `variants`) |
| `targeting` | ➖ | Ordered rule list, first match wins |
| `bucket_salt` | ➖ | Reshuffles bucketing for this flag |
| `metadata` | ➖ | `owner` / `team` / `tags` / `updated_at` (read by lint) |

### Evaluation semantics

Evaluation short-circuits in this exact order:

```
flag.state == off ──────────────► DISABLED (default variant)
        │ on
        ▼
targeting rules (in config order)
  all conditions match?
    ├─ rule without percentage ─► TARGETING_MATCH (rule variant)
    └─ rule with percentage
         ├─ bucket hit ─────────► TARGETING_MATCH (rule variant)
         └─ bucket miss ───────► continue to next rule
        │
        ▼
flag.rollout
  bucket hit ──────────────────► SPLIT (rollout variant / weighted variant)
  bucket miss ─────────────────► DEFAULT (default variant)
```

**Determinism guarantee**: bucket = `murmur3_32(bucket_salt + flag_key + "\x1f" + bucket_key) % 100`.
The same `(flag, bucket_key)` always yields the same result — safe to rely on in tests, CI and production alike.

Debug bucketing:

```bash
flagforge hash bucket new-checkout user-42 --samples 10000
```

### Condition operators

| Operator | Semantics | Example |
| --- | --- | --- |
| `in` / `not_in` | equals any of | `plan in [pro, ent]` |
| `exists` / `not_exists` | field present (non-null) | `beta exists` |
| `gt` / `gte` / `lt` / `lte` | numeric or string compare | `seats gt 20` |
| `starts_with` / `ends_with` | string prefix/suffix | `email ends_with @example.com` |
| `contains` | substring or list member | `roles contains admin` |
| `matches` | regex `re.search` | `email matches .+@example\.com$` |

Multiple conditions in one rule are **ANDed**; the string `"true"` loosely equals boolean `true` under `in` (avoids CLI/YAML type ambiguity).

### CLI reference

| Command | Purpose | Key options |
| --- | --- | --- |
| `init` | Generate sample config | `-o path` `--force` |
| `validate` | Validate + semantic warnings | `--format json` |
| `list` | List flags | `--state on` `--tag x` `--owner team` `--evaluated` |
| `show <key>` | Flag details + current evaluation | `--format json` |
| `eval [key]` | Evaluate (omit key for all) | `-c k=v` `--format json` |
| `gate` | CI assertion gate | `--expect flag=value` (repeatable) |
| `diff <old> <new>` | Diff with risk levels | `--format json` |
| `lint` | Best-practice checks | `--stale-days 90` `--fail-on warning` |
| `export` | Export | `--format json\|table\|markdown\|env\|schema` |
| `hash murmur\|bucket` | Bucketing debug | `--samples N` `--salt x` |
| `serve` | Local HTTP API | `--host` `--port` |
| `tui` | Terminal playground | `-c k=v` |

**Exit codes**: `0` success · `1` usage/runtime error · `2` validation failure · `3` gate assertion failure.

### Common scenarios

**① Gradual rollout (25% → 50% → 100%)**

```bash
# Review risk before merging
flagforge diff flags.yaml flags.new.yaml

# Assert in CI: internal emails must hit the new flow
flagforge gate --file flags.yaml \
  --expect new-checkout=true \
  -c targetingKey=ci-user,email=ci@example.com
```

**② A/B experiment with variants**

```yaml
rollout:
  percentage: 50
  variants:
    variant-a: 50
    variant-b: 50
```

**③ Kill switch**

```yaml
- key: legacy-api
  state: off        # flip to on in an emergency to take it offline
  variants: {on: true, off: false}
  default_variant: off
```

**④ Shell integration**

```bash
eval "$(flagforge export --format env -c targetingKey=user-42)"
echo "$FLAGFORGE_NEW_CHECKOUT"   # true
```

### HTTP API

```bash
flagforge serve --port 8765
```

```bash
# Evaluate (query form)
curl "http://127.0.0.1:8765/evaluate?flag=new-checkout&targetingKey=user-42"

# Evaluate (JSON body)
curl -X POST http://127.0.0.1:8765/evaluate \
  -H 'Content-Type: application/json' \
  -d '{"key":"new-checkout","context":{"targetingKey":"user-42"}}'

# Health check / all definitions
curl http://127.0.0.1:8765/health
curl http://127.0.0.1:8765/flags
```

> ⚠️ Binds to `127.0.0.1` by default. Never expose it to the public internet unprotected.

### TUI playground

```bash
flagforge tui
```

* `↑`/`↓` or `j`/`k`: navigate flags
* `/`: filter by key
* `Enter`: edit context (`k=v,k2=v2`), re-evaluates live
* `r`: hot-reload the config file
* `q`: quit

### Python API

```python
from flagforge import OpenFeature

of = OpenFeature.from_file("flags.yaml")
client = of.get_client()

# OpenFeature-style typed access
if client.get_boolean_value("new-checkout", False, {"targetingKey": "user-42"}):
    render_new_checkout()

# Full evaluation details (with reason)
details = client.get_variant("new-checkout", {"targetingKey": "user-42"})
# {'flag_key': 'new-checkout', 'variant': 'enabled', 'value': True, 'reason': 'SPLIT'}
```

## 💡 Design Notes & Roadmap

**Design philosophy**:

1. **Determinism first** — bucketing is a pure function; no more "same user, two answers"
2. **Config as code** — flags live in Git, so review, rollback and audit reuse your existing engineering system
3. **Zero dependencies is a feature** — no transitive deps means no supply-chain risk, no version conflicts, no "upgrade and break"
4. **Aligned with the community** — reason codes match the OpenFeature spec, lowering migration cost

**Tech choices**:

* **Standard library only** — `argparse` / `json` / `http.server` / `curses` / `unittest`; works on any Python 3.9+
* **MurmurHash3 (x86_32)** — the industry-standard bucketing hash (same family used by LaunchDarkly); avalanche effect keeps distributions uniform
* **YAML subset, not full YAML** — full YAML has many "surprise" features (anchors, `yes/no` booleans, implicit typing); a subset keeps config behavior **predictable and testable**. Use JSON when you need the full power

**Roadmap**:

* 🔭 **v1.1**: OpenFeature provider protocol adapter (`flagd`-compatible)
* 🌐 **v1.2**: optional remote config sources (HTTP/etcd fetch + local cache + polling)
* 📊 **v1.3**: evaluation event hooks and exposure statistics
* 🧪 **v1.4**: experiment significance helpers (frequency/conversion analysis)
* 🌍 **v1.5**: multi-language SDK codegen (TypeScript/Go/Rust clients)

**Contribution ideas**: new condition operators, report formats, CI integration examples, doc translations — see [CONTRIBUTING.md](CONTRIBUTING.md).

## 📦 Packaging & Deployment

### As a CLI tool

```bash
pip install flagforge          # install from PyPI
flagforge --help               # verify
```

### As a library

```python
# requirements.txt
flagforge>=1.0.0
```

```toml
# pyproject.toml
[project]
dependencies = ["flagforge>=1.0.0"]
```

### Running from source

```bash
git clone https://github.com/gitstq/FlagForge.git
cd FlagForge
python -m flagforge list       # run as a module, no install needed
```

### Compatibility matrix

| Python | 3.9 | 3.10 | 3.11 | 3.12 | 3.13 |
| --- | --- | --- | --- | --- | --- |
| Status | ✅ | ✅ | ✅ | ✅ | ✅ |

| Platform | Linux | macOS | Windows |
| --- | --- | --- | --- |
| CLI / library / HTTP API | ✅ | ✅ | ✅ |
| TUI (curses) | ✅ | ✅ | ⚠️ needs `pip install windows-curses`, else degrades |

### CI integration

```yaml
# GitHub Actions snippet
- name: Validate feature flags
  run: |
    pip install flagforge
    flagforge validate --file flags.yaml
    flagforge lint --file flags.yaml --fail-on warning
    flagforge gate --file flags.yaml --expect new-checkout=true -c targetingKey=ci
```

### Release process

* **PyPI**: tag a GitHub Release and Actions builds and publishes automatically (Trusted Publishing, no token needed)
* **Source distribution**: the repo is dependency-free — copying the `flagforge/` directory is enough

## 🤝 Contributing

* 📐 **Commit convention**: Angular Commit Convention (`feat:` / `fix:` / `docs:` / `refactor:` / `test:` / `chore:`)
* 🔬 **PR requirements**: one thing per PR; new features need unit tests; run locally before pushing
  ```bash
  python -m compileall -q flagforge tests
  python -m unittest discover -s tests
  ```
* 🐛 **Issues**: bugs need a minimal repro config + context + expected/actual + Python version
* 🔐 **Security**: please don't file public issues for vulnerabilities; open an Issue to make contact first
* 📖 Full rules in [CONTRIBUTING.md](CONTRIBUTING.md)

## 📄 License

Released under the [MIT License](LICENSE) — free to use, modify, distribute and commercialize; the only requirement is preserving the copyright and permission notices.
