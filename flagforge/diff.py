"""diff — flag 集合差异对比。

用于发布前评审：比较两个配置文件，输出新增 / 删除 / 变更的 flag，
并在变更详情中高亮风险项（如灰度百分比调整、默认变体变更、
flag 被关闭等）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import Flag, FlagSet

__all__ = ["Change", "DiffResult", "diff_flag_sets", "format_diff"]


class Change:
    """单个字段的变更。"""

    def __init__(self, field_path: str, old: Any, new: Any, risk: str = "info"):
        self.field_path = field_path
        self.old = old
        self.new = new
        self.risk = risk  # info | warning | critical

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field_path,
            "old": self.old,
            "new": self.new,
            "risk": self.risk,
        }

    def format(self) -> str:
        marker = {"info": "~", "warning": "!", "critical": "!!"}[self.risk]
        return "%s %s: %r -> %r" % (marker, self.field_path, self.old, self.new)


class DiffResult:
    """两个 flag 集合的差异。"""

    def __init__(self) -> None:
        self.added: List[str] = []
        self.removed: List[str] = []
        self.changed: Dict[str, List[Change]] = {}

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.changed)

    @property
    def max_risk(self) -> str:
        risks = {"info": 0, "warning": 1, "critical": 2}
        worst = 0
        for changes in self.changed.values():
            for change in changes:
                worst = max(worst, risks[change.risk])
        if self.removed:
            worst = max(worst, 1)
        for level, value in risks.items():
            if value == worst:
                return level
        return "info"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "added": self.added,
            "removed": self.removed,
            "changed": {k: [c.to_dict() for c in v] for k, v in self.changed.items()},
            "max_risk": self.max_risk,
        }


def _flatten(prefix: str, data: Any) -> Dict[str, Any]:
    """把嵌套 dict/list 拍平为点路径映射（仅用于对比）。"""
    out: Dict[str, Any] = {}
    if isinstance(data, dict):
        for key, value in data.items():
            path = "%s.%s" % (prefix, key) if prefix else str(key)
            if isinstance(value, (dict, list)) and value:
                out.update(_flatten(path, value))
            else:
                out[path] = value
    elif isinstance(data, list):
        for idx, value in enumerate(data):
            path = "%s[%d]" % (prefix, idx)
            if isinstance(value, (dict, list)) and value:
                out.update(_flatten(path, value))
            else:
                out[path] = value
    else:
        out[prefix] = data
    return out


def _change_risk(field_path: str, old: Any, new: Any) -> str:
    if field_path == "state":
        return "critical" if new == "off" else "warning"
    if field_path == "default_variant":
        return "critical"
    if field_path.endswith("percentage"):
        try:
            delta = abs(float(new) - float(old))
        except (TypeError, ValueError):
            delta = 0
        if delta >= 50:
            return "critical"
        if delta >= 10:
            return "warning"
        return "info"
    if field_path.startswith("targeting"):
        return "warning"
    return "info"


def diff_flag_sets(old: FlagSet, new: FlagSet) -> DiffResult:
    """对比两个 flag 集合。"""
    result = DiffResult()
    old_map = {f.key: f for f in old.flags}
    new_map = {f.key: f for f in new.flags}

    for key in new_map:
        if key not in old_map:
            result.added.append(key)
    for key in old_map:
        if key not in new_map:
            result.removed.append(key)
    for key in sorted(set(old_map) & set(new_map)):
        old_flat = _flatten("", old_map[key].to_dict())
        new_flat = _flatten("", new_map[key].to_dict())
        changes: List[Change] = []
        for path in sorted(set(old_flat) | set(new_flat)):
            old_value = old_flat.get(path)
            new_value = new_flat.get(path)
            if old_value != new_value:
                changes.append(
                    Change(
                        path,
                        old_value,
                        new_value,
                        _change_risk(path, old_value, new_value),
                    )
                )
        if changes:
            result.changed[key] = changes
    return result


def format_diff(result: DiffResult) -> str:
    """人类可读的差异报告。"""
    if not result.has_changes:
        return "No changes."
    lines: List[str] = []
    if result.added:
        lines.append("Added flags (%d):" % len(result.added))
        lines.extend("  + %s" % key for key in result.added)
    if result.removed:
        lines.append("Removed flags (%d):" % len(result.removed))
        lines.extend("  - %s" % key for key in result.removed)
    for key in sorted(result.changed):
        lines.append("Changed flag: %s" % key)
        lines.extend("  %s" % change.format() for change in result.changed[key])
    lines.append("Max risk level: %s" % result.max_risk.upper())
    return "\n".join(lines)
