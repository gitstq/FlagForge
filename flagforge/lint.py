"""lint — flag 配置最佳实践检查。

内置规则（均为可操作的工程建议，而非风格挑剔）：

* ``flag-missing-owner``      缺少负责人（warning）
* ``flag-missing-description`` 缺少描述（warning）
* ``flag-stale``              开启超过 N 天未更新（warning）
* ``flag-key-naming``         命名不符合 kebab-case / snake_case（info）
* ``flag-full-rollout``       100% 灰度且无定向，建议下线（info）
* ``flag-noop-rollout``       灰度变体与默认变体相同（warning）
* ``flag-orphan-tag``         标签仅被一个 flag 使用（info）
* ``flag-long-targeting``     定向规则过多（>8），评估复杂度上升（info）

输出支持 text / json 两种格式，CI 中可通过 ``--fail-on`` 设置门禁。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import Flag, FlagSet

__all__ = ["Finding", "LintReport", "lint_flag_set", "format_lint_report"]

_KEY_STYLE_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$|^[a-z0-9]+(_[a-z0-9]+)*$")

_LEVELS = ("info", "warning", "error")


@dataclass
class Finding:
    """一条 lint 发现。"""

    rule: str
    level: str  # info | warning | error
    flag_key: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule": self.rule,
            "level": self.level,
            "flag": self.flag_key,
            "message": self.message,
        }


@dataclass
class LintReport:
    """lint 结果汇总。"""

    findings: List[Finding] = field(default_factory=list)

    def count(self, level: str) -> int:
        return sum(1 for f in self.findings if f.level == level)

    def worst_level(self) -> str:
        if self.count("error"):
            return "error"
        if self.count("warning"):
            return "warning"
        return "info"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "summary": {
                "total": len(self.findings),
                "errors": self.count("error"),
                "warnings": self.count("warning"),
                "info": self.count("info"),
            },
        }


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def lint_flag_set(
    flag_set: FlagSet,
    stale_days: int = 90,
    now: Optional[datetime] = None,
) -> LintReport:
    """对 flag 集合执行全部 lint 规则。"""
    report = LintReport()
    now = now or datetime.now(timezone.utc)
    tag_usage: Dict[str, int] = {}

    for flag in flag_set.flags:
        meta = flag.metadata or {}
        owner = meta.get("owner") or meta.get("team")
        if not owner:
            report.findings.append(
                Finding(
                    "flag-missing-owner",
                    "warning",
                    flag.key,
                    "no owner/team in metadata — stale flags become invisible",
                )
            )
        if not flag.description:
            report.findings.append(
                Finding(
                    "flag-missing-description",
                    "warning",
                    flag.key,
                    "missing description — future maintainers cannot infer intent",
                )
            )
        if not _KEY_STYLE_RE.match(flag.key):
            report.findings.append(
                Finding(
                    "flag-key-naming",
                    "info",
                    flag.key,
                    "key should be kebab-case or snake_case for consistency",
                )
            )
        if flag.state == "on" and flag.rollout is not None:
            if flag.rollout.percentage >= 100 and not flag.targeting:
                report.findings.append(
                    Finding(
                        "flag-full-rollout",
                        "info",
                        flag.key,
                        "rollout is 100%% with no targeting — schedule removal",
                    )
                )
            if flag.rollout.variant is not None and (
                flag.rollout.variant == flag.default_variant
            ):
                report.findings.append(
                    Finding(
                        "flag-noop-rollout",
                        "warning",
                        flag.key,
                        "rollout variant equals default variant — flag has no effect",
                    )
                )
        if len(flag.targeting) > 8:
            report.findings.append(
                Finding(
                    "flag-long-targeting",
                    "info",
                    flag.key,
                    "%d targeting rules — consider consolidating" % len(flag.targeting),
                )
            )
        updated = _parse_timestamp(meta.get("updated_at"))
        if flag.state == "on" and updated is not None:
            age_days = (now - updated).days
            if age_days > stale_days:
                report.findings.append(
                    Finding(
                        "flag-stale",
                        "warning",
                        flag.key,
                        "on for %d days without update — clean up or archive" % age_days,
                    )
                )
        for tag in meta.get("tags", []) or []:
            if isinstance(tag, str):
                tag_usage[tag] = tag_usage.get(tag, 0) + 1

    for tag, count in sorted(tag_usage.items()):
        if count == 1:
            report.findings.append(
                Finding(
                    "flag-orphan-tag",
                    "info",
                    "(tag)",
                    "tag '%s' is used by only one flag" % tag,
                )
            )
    return report


def format_lint_report(report: LintReport) -> str:
    """人类可读的 lint 报告。"""
    if not report.findings:
        return "All checks passed."
    icons = {"error": "x", "warning": "!", "info": "~"}
    lines: List[str] = []
    for finding in report.findings:
        lines.append(
            "[%s] %s (%s): %s"
            % (
                icons[finding.level],
                finding.rule,
                finding.flag_key,
                finding.message,
            )
        )
    lines.append(
        "Summary: %d finding(s) — %d error, %d warning, %d info"
        % (
            len(report.findings),
            report.count("error"),
            report.count("warning"),
            report.count("info"),
        )
    )
    return "\n".join(lines)
