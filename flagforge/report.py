"""report — 评估结果与配置的导出格式化。

支持格式：

* ``json``    机器可读（评估结果或完整配置）
* ``table``   对齐的 ASCII 表格
* ``markdown`` Markdown 表格（适合贴进文档 / PR 描述）
* ``env``     shell 可 ``eval`` 的 ``export FLAG_*=value`` 语句
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from .engine import evaluate_all
from .models import EvaluationResult, Flag, FlagSet

__all__ = ["format_env", "format_json", "format_markdown", "format_table"]


def _value_to_env_string(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    text = str(value)
    if text == "" or any(ch in text for ch in " \t\n'\"\\$`!#&|;()<>"):
        return "'" + text.replace("'", "'\\''") + "'"
    return text


def format_env(
    flag_set: FlagSet, context: Any = None, prefix: str = "FLAGFORGE_"
) -> str:
    """导出为 shell 环境变量赋值语句（配合 ``eval`` 使用）。"""
    results = evaluate_all(flag_set, context)
    lines = []
    for key in sorted(results):
        env_name = prefix + key.upper().replace("-", "_").replace(".", "_")
        lines.append(
            "export %s=%s" % (env_name, _value_to_env_string(results[key].value))
        )
    return "\n".join(lines)


def format_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _short(value: Any, limit: int = 24) -> str:
    if isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    else:
        text = str(value)
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text


def _fmt_number(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _md_escape(text: str) -> str:
    return text.replace("|", "\\|")


def format_table(
    flag_set: FlagSet, context: Any = None, evaluated: bool = False
) -> str:
    """ASCII 表格输出。"""
    rows: List[List[str]] = []
    if evaluated:
        results = evaluate_all(flag_set, context)
        headers = ["FLAG", "STATE", "VARIANT", "VALUE", "REASON"]
        for flag in flag_set.flags:
            result = results[flag.key]
            rows.append(
                [
                    flag.key,
                    flag.state,
                    result.variant,
                    _short(result.value),
                    result.reason,
                ]
            )
    else:
        headers = [
            "FLAG",
            "STATE",
            "TYPE",
            "DEFAULT",
            "ROLLOUT",
            "RULES",
            "DESCRIPTION",
        ]
        for flag in flag_set.flags:
            rollout = "-"
            if flag.rollout is not None:
                rollout = "%s%%" % _fmt_number(flag.rollout.percentage)
            rows.append(
                [
                    flag.key,
                    flag.state,
                    flag.variant_type,
                    flag.default_variant,
                    rollout,
                    str(len(flag.targeting)),
                    _short(flag.description, 40),
                ]
            )
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    lines = ["  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))]
    lines.append("  ".join("-" * widths[i] for i in range(len(headers))))
    for row in rows:
        lines.append("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)))
    return "\n".join(lines)


def format_markdown(
    flag_set: FlagSet, context: Any = None, evaluated: bool = False
) -> str:
    """Markdown 表格输出。"""
    lines: List[str] = []
    if evaluated:
        results = evaluate_all(flag_set, context)
        lines.append("| Flag | State | Variant | Value | Reason |")
        lines.append("| --- | --- | --- | --- | --- |")
        for flag in flag_set.flags:
            result = results[flag.key]
            lines.append(
                "| `%s` | %s | `%s` | `%s` | %s |"
                % (
                    flag.key,
                    flag.state,
                    result.variant,
                    _md_escape(_short(result.value)),
                    result.reason,
                )
            )
    else:
        lines.append("| Flag | State | Type | Default | Rollout | Rules | Description |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for flag in flag_set.flags:
            rollout = "-"
            if flag.rollout is not None:
                rollout = "%s%%" % _fmt_number(flag.rollout.percentage)
            lines.append(
                "| `%s` | %s | %s | `%s` | %s | %d | %s |"
                % (
                    flag.key,
                    flag.state,
                    flag.variant_type,
                    flag.default_variant,
                    rollout,
                    len(flag.targeting),
                    _md_escape(_short(flag.description, 60)),
                )
            )
    return "\n".join(lines)
