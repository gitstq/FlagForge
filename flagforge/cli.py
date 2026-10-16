"""cli — FlagForge 命令行界面。

命令总览::

    flagforge init      生成示例配置文件
    flagforge validate  校验配置文件合法性
    flagforge list      列出全部 flag
    flagforge show      查看单个 flag 详情
    flagforge eval      在给定上下文中评估 flag
    flagforge gate      CI 断言门禁（评估结果必须匹配期望）
    flagforge diff      对比两个配置文件的差异
    flagforge lint      最佳实践检查
    flagforge export    导出（json/table/markdown/env）
    flagforge hash      调试分桶分布
    flagforge serve     启动本地 HTTP 评估 API
    flagforge tui       终端交互式演练场

退出码：``0`` 成功；``1`` 用法/运行时错误；``2`` 校验失败；
``3`` 门禁断言失败。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from . import __version__
from .diff import diff_flag_sets, format_diff
from .engine import evaluate
from .hashing import bucket, bucket_distribution, murmur3_32
from .lint import format_lint_report, lint_flag_set
from .loader import (
    DEFAULT_FILENAMES,
    find_flag_file,
    load_flags,
    schema_document,
    validate_flag_set,
)
from .models import EvaluationContext, ValidationError
from .report import format_env, format_json, format_markdown, format_table
from .tui import TuiUnavailableError, parse_context_string, run_tui

__all__ = ["main"]

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_INVALID = 2
EXIT_GATE_FAILED = 3

_SAMPLE_YAML = """\
# FlagForge 示例配置
# 文档: https://github.com/gitstq/FlagForge
flags:
  - key: new-checkout-flow
    description: 新版结账流程（灰度发布）
    state: on
    variant_type: boolean
    variants:
      enabled: true
      control: false
    default_variant: control
    rollout:
      percentage: 25
      variant: enabled
      bucket_by: targetingKey
    metadata:
      owner: team-payments
      tags: [checkout, growth]
      updated_at: "2026-10-16"

  - key: pricing-page-redesign
    description: 定价页改版（多变体 A/B 实验）
    state: on
    variant_type: string
    variants:
      control: "classic"
      variant-a: "modern"
      variant-b: "bold"
    default_variant: control
    rollout:
      percentage: 50
      variants:
        variant-a: 50
        variant-b: 50
    metadata:
      owner: team-growth
      tags: [experiment]

  - key: internal-tools
    description: 内部工具入口（定向员工）
    state: on
    variant_type: boolean
    variants:
      on: true
      off: false
    default_variant: off
    targeting:
      - id: employees
        description: 公司邮箱域名
        conditions:
          - field: email
            op: ends_with
            values: ["@example.com"]
        variant: on
    metadata:
      owner: platform
      tags: [internal]

  - key: legacy-api
    description: 旧版 API 熔断开关（kill switch）
    state: off
    variant_type: boolean
    variants:
      on: true
      off: false
    default_variant: off
    metadata:
      owner: platform
      tags: [killswitch]

meta:
  name: my-project
"""


# ---------------------------------------------------------------------------#
# 参数解析辅助
# ---------------------------------------------------------------------------#
def _parse_context_items(items: Optional[List[str]]) -> Dict[str, Any]:
    context: Dict[str, Any] = {}
    for item in items or []:
        for part in item.split(","):
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


def _auto_value(text: str) -> Any:
    """把 CLI 字符串尽量转为合适的 JSON 类型。"""
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return text


def _load(args: argparse.Namespace):
    path = find_flag_file(getattr(args, "file", None), start_dir=os.getcwd())
    return path, load_flags(path)


def _print(message: str) -> None:
    sys.stdout.write(message + "\n")


# ---------------------------------------------------------------------------#
# 子命令实现
# ---------------------------------------------------------------------------#
def _cmd_init(args: argparse.Namespace) -> int:
    target = args.output
    if os.path.exists(target) and not args.force:
        sys.stderr.write("error: %s already exists (use --force to overwrite)\n" % target)
        return EXIT_ERROR
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(_SAMPLE_YAML)
    _print("Created %s — edit it, then run: flagforge validate --file %s" % (target, target))
    return EXIT_OK


def _cmd_validate(args: argparse.Namespace) -> int:
    try:
        _, flag_set = _load(args)
    except (FileNotFoundError, ValidationError) as exc:
        sys.stderr.write("error: %s\n" % exc)
        return EXIT_INVALID
    warnings = validate_flag_set(flag_set)
    if args.format == "json":
        _print(
            format_json(
                {
                    "valid": True,
                    "flags": len(flag_set.flags),
                    "warnings": warnings,
                }
            )
        )
    else:
        _print("OK: %d flag(s) validated in %s" % (len(flag_set.flags), args.file or "auto-detected file"))
        for warning in warnings:
            _print("  ! %s" % warning)
    return EXIT_OK


def _cmd_list(args: argparse.Namespace) -> int:
    try:
        _, flag_set = _load(args)
    except (FileNotFoundError, ValidationError) as exc:
        sys.stderr.write("error: %s\n" % exc)
        return EXIT_ERROR
    flags = flag_set.flags
    if args.state:
        flags = [f for f in flags if f.state == args.state]
    if args.tag:
        flags = [
            f
            for f in flags
            if args.tag in (f.metadata.get("tags", []) or [])
        ]
    if args.owner:
        flags = [
            f
            for f in flags
            if f.metadata.get("owner") == args.owner
            or f.metadata.get("team") == args.owner
        ]
    subset = type(flag_set)(flags=flags, meta=flag_set.meta)
    if not flags:
        _print("No flags matched.")
        return EXIT_OK
    context = _parse_context_items(args.context)
    if args.format == "json":
        if args.evaluated:
            from .engine import evaluate_all

            results = evaluate_all(subset, context)
            _print(format_json({k: r.to_dict() for k, r in results.items()}))
        else:
            _print(format_json([f.to_dict() for f in flags]))
        return EXIT_OK
    _print(format_table(subset, context=context, evaluated=args.evaluated))
    return EXIT_OK


def _cmd_show(args: argparse.Namespace) -> int:
    try:
        _, flag_set = _load(args)
    except (FileNotFoundError, ValidationError) as exc:
        sys.stderr.write("error: %s\n" % exc)
        return EXIT_ERROR
    flag = flag_set.get(args.key)
    if flag is None:
        sys.stderr.write("error: flag '%s' not found\n" % args.key)
        return EXIT_ERROR
    context = _parse_context_items(args.context)
    result = evaluate(flag, context)
    if args.format == "json":
        _print(format_json({"flag": flag.to_dict(), "evaluation": result.to_dict()}))
        return EXIT_OK
    _print(json.dumps(flag.to_dict(), ensure_ascii=False, indent=2))
    _print("")
    _print("Evaluation with context %s:" % (context or "{}"))
    _print("  variant = %s" % result.variant)
    _print("  value   = %s" % json.dumps(result.value, ensure_ascii=False))
    _print("  reason  = %s" % result.reason + (" (rule: %s)" % result.rule_id if result.rule_id else ""))
    return EXIT_OK


def _cmd_eval(args: argparse.Namespace) -> int:
    try:
        _, flag_set = _load(args)
    except (FileNotFoundError, ValidationError) as exc:
        sys.stderr.write("error: %s\n" % exc)
        return EXIT_ERROR
    context = _parse_context_items(args.context)
    if args.key:
        flag = flag_set.get(args.key)
        if flag is None:
            sys.stderr.write("error: flag '%s' not found\n" % args.key)
            return EXIT_ERROR
        result = evaluate(flag, context)
        if args.format == "json":
            _print(format_json(result.to_dict()))
        else:
            _print(
                "%s -> %s (value=%s, reason=%s)"
                % (
                    args.key,
                    result.variant,
                    json.dumps(result.value, ensure_ascii=False),
                    result.reason,
                )
            )
        return EXIT_OK
    from .engine import evaluate_all

    results = evaluate_all(flag_set, context)
    if args.format == "json":
        _print(format_json({k: r.to_dict() for k, r in results.items()}))
    else:
        subset = flag_set
        _print(format_table(subset, context=context, evaluated=True))
    return EXIT_OK


def _cmd_gate(args: argparse.Namespace) -> int:
    try:
        _, flag_set = _load(args)
    except (FileNotFoundError, ValidationError) as exc:
        sys.stderr.write("error: %s\n" % exc)
        return EXIT_INVALID
    context = _parse_context_items(args.context)
    failures: List[str] = []
    checks: List[Tuple[str, str, Any]] = []
    for item in args.expect:
        if "=" not in item:
            sys.stderr.write("error: --expect entry '%s' must be flag=value\n" % item)
            return EXIT_ERROR
        key, expected = item.split("=", 1)
        key = key.strip()
        flag = flag_set.get(key)
        if flag is None:
            failures.append("%s: flag not found" % key)
            continue
        result = evaluate(flag, context)
        expected_value = _auto_value(expected.strip())
        actual = result.value
        ok = actual == expected_value
        # 宽松比较：字符串 "true" 与布尔 True 视为相等
        if not ok and isinstance(expected_value, str):
            ok = str(actual).lower() == expected_value.lower()
        checks.append((key, expected_value, actual))
        if not ok:
            failures.append("%s: expected %r, got %r" % (key, expected_value, actual))
    if args.format == "json":
        _print(
            format_json(
                {
                    "passed": not failures,
                    "checks": [
                        {"flag": k, "expected": e, "actual": a} for k, e, a in checks
                    ],
                    "failures": failures,
                }
            )
        )
    else:
        for key, expected_value, actual in checks:
            status = "PASS" if actual == expected_value or (
                isinstance(expected_value, str)
                and str(actual).lower() == expected_value.lower()
            ) else "FAIL"
            _print("[%s] %s = %r (got %r)" % (status, key, expected_value, actual))
    if failures:
        sys.stderr.write("gate failed: %d assertion(s) did not hold\n" % len(failures))
        return EXIT_GATE_FAILED
    if not checks:
        sys.stderr.write("error: no --expect given; nothing to check\n")
        return EXIT_ERROR
    _print("gate passed")
    return EXIT_OK


def _cmd_diff(args: argparse.Namespace) -> int:
    try:
        old_set = load_flags(args.old)
        new_set = load_flags(args.new)
    except (FileNotFoundError, ValidationError) as exc:
        sys.stderr.write("error: %s\n" % exc)
        return EXIT_ERROR
    result = diff_flag_sets(old_set, new_set)
    if args.format == "json":
        _print(format_json(result.to_dict()))
    else:
        _print(format_diff(result))
    return EXIT_OK


def _cmd_lint(args: argparse.Namespace) -> int:
    try:
        _, flag_set = _load(args)
    except (FileNotFoundError, ValidationError) as exc:
        sys.stderr.write("error: %s\n" % exc)
        return EXIT_INVALID
    report = lint_flag_set(flag_set, stale_days=args.stale_days)
    if args.format == "json":
        _print(format_json(report.to_dict()))
    else:
        _print(format_lint_report(report))
    if args.fail_on:
        levels = {"info": 0, "warning": 1, "error": 2}
        threshold = levels[args.fail_on]
        current = levels[report.worst_level()]
        if current >= threshold:
            return EXIT_INVALID
    return EXIT_OK


def _cmd_export(args: argparse.Namespace) -> int:
    try:
        _, flag_set = _load(args)
    except (FileNotFoundError, ValidationError) as exc:
        sys.stderr.write("error: %s\n" % exc)
        return EXIT_ERROR
    context = _parse_context_items(args.context)
    fmt = args.format
    if fmt == "json":
        if args.evaluated:
            from .engine import evaluate_all

            results = evaluate_all(flag_set, context)
            _print(format_json({k: r.to_dict() for k, r in results.items()}))
        else:
            _print(format_json(flag_set.to_dict()))
    elif fmt == "table":
        _print(format_table(flag_set, context=context, evaluated=args.evaluated))
    elif fmt == "markdown":
        _print(format_markdown(flag_set, context=context, evaluated=args.evaluated))
    elif fmt == "env":
        _print(format_env(flag_set, context=context, prefix=args.prefix))
    elif fmt == "schema":
        _print(format_json(schema_document()))
    else:  # pragma: no cover - argparse 已约束
        sys.stderr.write("error: unsupported format '%s'\n" % fmt)
        return EXIT_ERROR
    return EXIT_OK


def _cmd_hash(args: argparse.Namespace) -> int:
    if not getattr(args, "subcommand", None):
        sys.stderr.write("error: hash requires a subcommand: 'murmur' or 'bucket'\n")
        return EXIT_ERROR
    if args.subcommand == "murmur":
        digest = murmur3_32(args.value.encode("utf-8"), seed=args.seed)
        _print(format_json({"input": args.value, "seed": args.seed, "murmur3_32": digest}))
        return EXIT_OK
    # bucket
    b = bucket(args.flag, args.key, total=args.total, salt=args.salt or "")
    payload: Dict[str, Any] = {
        "flag": args.flag,
        "key": args.key,
        "total": args.total,
        "salt": args.salt or "",
        "bucket": b,
        "in_percentage": "<= %s%%" % b,
    }
    if args.samples:
        keys = ["user-%d" % i for i in range(args.samples)]
        distribution = bucket_distribution(
            args.flag, keys, total=args.total, salt=args.salt or ""
        )
        payload["distribution"] = [
            {"bucket": bucket_id, "count": count} for bucket_id, count in distribution
        ]
    _print(format_json(payload))
    return EXIT_OK


def _cmd_serve(args: argparse.Namespace) -> int:
    try:
        _, flag_set = _load(args)
    except (FileNotFoundError, ValidationError) as exc:
        sys.stderr.write("error: %s\n" % exc)
        return EXIT_ERROR
    from .server import serve

    _print(
        "FlagForge listening on http://%s:%d (%d flags) — Ctrl+C to stop"
        % (args.host, args.port, len(flag_set.flags))
    )
    serve(flag_set, host=args.host, port=args.port)
    return EXIT_OK


def _cmd_tui(args: argparse.Namespace) -> int:
    try:
        _, flag_set = _load(args)
    except (FileNotFoundError, ValidationError) as exc:
        sys.stderr.write("error: %s\n" % exc)
        return EXIT_ERROR
    context = _parse_context_items(args.context)
    try:
        return run_tui(
            flag_set,
            initial_context=context,
            reload_path=args.file or find_flag_file(None, start_dir=os.getcwd()),
        )
    except TuiUnavailableError as exc:
        sys.stderr.write("error: %s\n" % exc)
        return EXIT_ERROR


# ---------------------------------------------------------------------------#
# 解析器构造
# ---------------------------------------------------------------------------#
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flagforge",
        description="FlagForge — lightweight local-first feature flag engine",
    )
    parser.add_argument("--version", action="version", version="flagforge %s" % __version__)
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    def add_common(p: argparse.ArgumentParser, context: bool = True) -> None:
        p.add_argument(
            "-f",
            "--file",
            help="flag file path (default: auto-detect %s)" % "/".join(DEFAULT_FILENAMES),
        )
        p.add_argument(
            "--format",
            choices=["text", "json"],
            default="text",
            help="output format (default: text)",
        )
        if context:
            p.add_argument(
                "-c",
                "--context",
                action="append",
                metavar="K=V",
                help="evaluation context entry (repeatable, comma-separated allowed)",
            )

    p_init = sub.add_parser("init", help="generate a sample flag file")
    p_init.add_argument("-o", "--output", default="flagforge.yaml", help="output path")
    p_init.add_argument("--force", action="store_true", help="overwrite existing file")
    p_init.set_defaults(func=_cmd_init)

    p_validate = sub.add_parser("validate", help="validate a flag file")
    add_common(p_validate, context=False)
    p_validate.set_defaults(func=_cmd_validate)

    p_list = sub.add_parser("list", help="list flags")
    add_common(p_list)
    p_list.add_argument("--state", choices=["on", "off"], help="filter by state")
    p_list.add_argument("--tag", help="filter by metadata tag")
    p_list.add_argument("--owner", help="filter by metadata owner/team")
    p_list.add_argument(
        "--evaluated", action="store_true", help="show evaluation for --context"
    )
    p_list.set_defaults(func=_cmd_list)

    p_show = sub.add_parser("show", help="show one flag in detail")
    add_common(p_show)
    p_show.add_argument("key", help="flag key")
    p_show.set_defaults(func=_cmd_show)

    p_eval = sub.add_parser("eval", help="evaluate flag(s) with a context")
    add_common(p_eval)
    p_eval.add_argument("key", nargs="?", help="flag key (omit to evaluate all)")
    p_eval.set_defaults(func=_cmd_eval)

    p_gate = sub.add_parser("gate", help="CI assertion gate")
    add_common(p_gate)
    p_gate.add_argument(
        "--expect",
        action="append",
        required=True,
        metavar="FLAG=VALUE",
        help="expected evaluation value (repeatable)",
    )
    p_gate.set_defaults(func=_cmd_gate)

    p_diff = sub.add_parser("diff", help="diff two flag files")
    p_diff.add_argument("old", help="old flag file")
    p_diff.add_argument("new", help="new flag file")
    p_diff.add_argument(
        "--format", choices=["text", "json"], default="text", help="output format"
    )
    p_diff.set_defaults(func=_cmd_diff)

    p_lint = sub.add_parser("lint", help="best-practice checks")
    add_common(p_lint, context=False)
    p_lint.add_argument(
        "--stale-days", type=int, default=90, help="staleness threshold in days"
    )
    p_lint.add_argument(
        "--fail-on",
        choices=["info", "warning", "error"],
        default="",
        help="exit non-zero when findings reach this level",
    )
    p_lint.set_defaults(func=_cmd_lint)

    p_export = sub.add_parser("export", help="export flags / evaluations")
    add_common(p_export)
    p_export.add_argument(
        "--format",
        choices=["json", "table", "markdown", "env", "schema"],
        default="table",
        help="export format (default: table)",
    )
    p_export.add_argument(
        "--evaluated", action="store_true", help="export evaluation results"
    )
    p_export.add_argument(
        "--prefix", default="FLAGFORGE_", help="env variable prefix (env format)"
    )
    p_export.set_defaults(func=_cmd_export)

    p_hash = sub.add_parser("hash", help="debug bucketing")
    hash_sub = p_hash.add_subparsers(dest="subcommand", metavar="<murmur|bucket>")
    p_murmur = hash_sub.add_parser("murmur", help="raw murmur3_32 digest")
    p_murmur.add_argument("value", help="input string")
    p_murmur.add_argument("--seed", type=int, default=0, help="seed (default 0)")
    p_murmur.set_defaults(func=_cmd_hash)
    p_bucket = hash_sub.add_parser("bucket", help="bucket id for (flag, key)")
    p_bucket.add_argument("flag", help="flag key")
    p_bucket.add_argument("key", help="bucket key (e.g. user id)")
    p_bucket.add_argument("--total", type=int, default=100, help="bucket count (default 100)")
    p_bucket.add_argument("--salt", default="", help="flag bucket_salt")
    p_bucket.add_argument(
        "--samples", type=int, default=0, help="also print distribution over N sample keys"
    )
    p_bucket.set_defaults(func=_cmd_hash)
    p_hash.set_defaults(func=_cmd_hash, subcommand=None)

    p_serve = sub.add_parser("serve", help="run local HTTP evaluation API")
    add_common(p_serve, context=False)
    p_serve.add_argument("--host", default="127.0.0.1", help="bind host (default 127.0.0.1)")
    p_serve.add_argument("--port", type=int, default=8765, help="bind port (default 8765)")
    p_serve.set_defaults(func=_cmd_serve)

    p_tui = sub.add_parser("tui", help="interactive terminal playground")
    add_common(p_tui)
    p_tui.set_defaults(func=_cmd_tui)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return EXIT_ERROR
    try:
        return int(args.func(args))
    except ValueError as exc:
        sys.stderr.write("error: %s\n" % exc)
        return EXIT_ERROR
    except KeyboardInterrupt:
        return EXIT_OK
    except BrokenPipeError:  # pragma: no cover
        return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
