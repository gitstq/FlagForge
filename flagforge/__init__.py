"""FlagForge — 轻量级本地优先功能开关（Feature Flags）引擎。

零依赖纯 Python 实现，提供：

* 确定性的百分比灰度（rollout）与多变体分流（murmur3 一致性哈希）
* OpenFeature 兼容的评估语义与理由码（reason codes）
*  Targeting 规则引擎（12 种条件操作符）
* JSON / YAML 子集双格式配置加载与严格校验
* CLI（init / validate / list / show / eval / gate / diff / lint / export / hash / serve / tui）
* 本地 HTTP 评估 API（基于标准库 http.server）
* 终端 TUI 演练场（curses，不可用时优雅降级）

本包仅使用 Python 标准库，无需安装任何第三方依赖。
"""

from .engine import FlagSet, evaluate
from .hashing import bucket, murmur3_32
from .loader import load_flags, load_flags_from_string
from .models import Flag, EvaluationResult, TargetingRule
from .openfeature import Client, OpenFeature

__version__ = "1.0.0"
__all__ = [
    "Client",
    "EvaluationResult",
    "Flag",
    "FlagSet",
    "OpenFeature",
    "TargetingRule",
    "bucket",
    "evaluate",
    "load_flags",
    "load_flags_from_string",
    "murmur3_32",
]
