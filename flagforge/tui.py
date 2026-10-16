"""tui — 终端 TUI 演练场（curses）。

一个交互式的 flag 演练场：

* 左侧为 flag 列表（支持上下键浏览、/ 过滤）
* 右侧展示当前 flag 的定义、评估结果与理由
* 底部可编辑评估上下文（``key=value``，逗号分隔），实时重算
* ``q`` 退出，``r`` 重载配置文件

curses 在 Windows 原生 Python 中不可用——此时本模块会抛出
:class:`TuiUnavailableError`，CLI 会提示用户改用 ``--format table``
的非交互输出，保证行为可预期。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .engine import evaluate
from .loader import load_flags
from .models import Flag, FlagSet

__all__ = ["TuiUnavailableError", "run_tui", "parse_context_string"]


class TuiUnavailableError(RuntimeError):
    """当前平台无法使用 curses TUI。"""


def parse_context_string(text: str) -> Dict[str, Any]:
    """解析 ``k1=v1,k2=v2`` 形式的上下文字符串（值为字符串）。"""
    context: Dict[str, Any] = {}
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError("context entry '%s' must be key=value" % part)
        key, value = part.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("context entry '%s' has empty key" % part)
        context[key] = value.strip()
    return context


def _curses():
    try:
        import curses  # type: ignore

        return curses
    except ImportError as exc:  # pragma: no cover - 平台相关
        raise TuiUnavailableError(
            "curses is not available on this platform; "
            "use 'flagforge list --evaluated' or 'flagforge eval' instead"
        ) from exc


def _format_flag_detail(flag: Flag, result: Any, context: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    lines.append("key:        %s" % flag.key)
    lines.append("state:      %s" % flag.state)
    lines.append("type:       %s" % flag.variant_type)
    lines.append("default:    %s" % flag.default_variant)
    if flag.description:
        lines.append("description: %s" % flag.description)
    if flag.rollout is not None:
        lines.append(
            "rollout:    %s%% -> %s"
            % (
                flag.rollout.percentage,
                flag.rollout.variant
                or ", ".join(
                    "%s:%s%%" % (k, v) for k, v in flag.rollout.variants.items()
                ),
            )
        )
    for rule in flag.targeting:
        lines.append(
            "rule[%s]: %s -> %s%s"
            % (
                rule.id,
                " AND ".join("%s %s %s" % (c.field, c.op, c.values) for c in rule.conditions),
                rule.variant,
                "" if rule.percentage is None else " (%s%%)" % rule.percentage,
            )
        )
    lines.append("-" * 40)
    lines.append("evaluation:")
    lines.append("  variant: %s" % result.variant)
    lines.append("  value:   %s" % result.value)
    lines.append("  reason:  %s" % result.reason)
    if result.rule_id:
        lines.append("  rule:    %s" % result.rule_id)
    lines.append("-" * 40)
    lines.append("context:    %s" % (context or "{}"))
    return lines


def run_tui(
    flag_set: FlagSet,
    initial_context: Optional[Dict[str, Any]] = None,
    reload_path: Optional[str] = None,
) -> int:
    """启动 TUI（阻塞）。返回退出码。"""
    curses = _curses()

    state = {
        "selected": 0,
        "offset": 0,
        "filter": "",
        "context": dict(initial_context or {}),
        "message": "",
    }

    def visible_flags() -> List[Flag]:
        needle = state["filter"].lower()
        if not needle:
            return list(flag_set.flags)
        return [f for f in flag_set.flags if needle in f.key.lower()]

    def main(stdscr: "Any") -> int:
        curses.curs_set(0)
        stdscr.keypad(True)
        while True:
            stdscr.erase()
            height, width = stdscr.getmaxyx()
            flags = visible_flags()
            if not flags:
                state["selected"] = 0
            else:
                state["selected"] = min(state["selected"], len(flags) - 1)

            stdscr.addstr(
                0, 0, "FlagForge TUI  |  /: filter  Enter: edit context  r: reload  q: quit"
            )
            list_width = max(20, width // 3)
            for row in range(1, max(1, height - 4)):
                idx = state["offset"] + row - 1
                if idx >= len(flags):
                    break
                flag = flags[idx]
                marker = ">" if idx == state["selected"] else " "
                state_icon = "*" if flag.state == "on" else " "
                label = "%s%s %s" % (marker, state_icon, flag.key)
                stdscr.addstr(row, 0, label[: list_width - 1].ljust(list_width - 1))

            if flags:
                flag = flags[state["selected"]]
                result = evaluate(flag, state["context"])
                detail = _format_flag_detail(flag, result, state["context"])
                for row, line in enumerate(detail, start=1):
                    if row >= height - 3:
                        break
                    stdscr.addstr(
                        row, list_width, line[: max(0, width - list_width - 1)]
                    )

            status = "context: %s   filter: %s" % (
                ",".join("%s=%s" % kv for kv in state["context"].items()) or "(empty)",
                state["filter"] or "(none)",
            )
            stdscr.addstr(height - 2, 0, status[: width - 1])
            if state["message"]:
                stdscr.addstr(height - 1, 0, state["message"][: width - 1])
            stdscr.refresh()

            ch = stdscr.getch()
            if ch in (ord("q"), ord("Q")):
                return 0
            if ch in (ord("r"), ord("R")) and reload_path:
                try:
                    flag_set.flags = load_flags(reload_path).flags
                    state["message"] = "reloaded %s" % reload_path
                except Exception as exc:  # noqa: BLE001
                    state["message"] = "reload failed: %s" % exc
            elif ch == ord("/"):
                curses.echo()
                stdscr.addstr(height - 1, 0, "filter: ".ljust(width - 1))
                state["filter"] = stdscr.getstr(height - 1, 8, 64).decode("utf-8", "replace")
                curses.noecho()
                state["message"] = ""
            elif ch in (ord("\n"), ord("\r")):
                curses.echo()
                stdscr.addstr(height - 1, 0, "context (k=v,...): ".ljust(width - 1))
                raw = stdscr.getstr(height - 1, 18, 128).decode("utf-8", "replace")
                curses.noecho()
                try:
                    state["context"] = parse_context_string(raw)
                    state["message"] = "context updated"
                except ValueError as exc:
                    state["message"] = str(exc)
            elif ch in (curses.KEY_UP, ord("k")):
                if state["selected"] > 0:
                    state["selected"] -= 1
            elif ch in (curses.KEY_DOWN, ord("j")):
                if state["selected"] < len(flags) - 1:
                    state["selected"] += 1
            elif ch == curses.KEY_PPAGE:
                state["selected"] = max(0, state["selected"] - (height - 5))
            elif ch == curses.KEY_NPAGE:
                state["selected"] = min(len(flags) - 1, state["selected"] + (height - 5))
            if state["selected"] < state["offset"]:
                state["offset"] = state["selected"]
            if state["selected"] >= state["offset"] + height - 5:
                state["offset"] = state["selected"] - (height - 5) + 1

    return curses.wrapper(main)
