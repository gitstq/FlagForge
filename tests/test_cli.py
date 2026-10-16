"""CLI 端到端测试。"""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest

from flagforge.cli import main
from flagforge.tui import parse_context_string

FLAGS_YAML = """\
flags:
  - key: new-checkout
    description: 新版结账流程
    state: on
    variant_type: boolean
    variants:
      enabled: true
      control: false
    default_variant: control
    rollout:
      percentage: 100
      variant: enabled
    metadata:
      owner: team-payments
  - key: internal-tools
    description: 内部工具
    state: on
    variant_type: boolean
    variants:
      on: true
      off: false
    default_variant: off
    targeting:
      - id: staff
        conditions:
          - field: email
            op: ends_with
            values: ["@example.com"]
        variant: on
  - key: legacy-api
    description: 旧 API
    state: off
    variant_type: boolean
    variants:
      on: true
      off: false
    default_variant: off
"""


def run_cli(*argv):
    """执行 CLI，返回 (exit_code, stdout, stderr)。"""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class CliTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.flag_file = os.path.join(self.tmp.name, "flags.yaml")
        with open(self.flag_file, "w", encoding="utf-8") as fh:
            fh.write(FLAGS_YAML)

    def flag_args(self, *extra):
        return ["--file", self.flag_file] + list(extra)


class TestInit(CliTestCase):
    def test_init_creates_file(self):
        target = os.path.join(self.tmp.name, "new-flags.yaml")
        code, out, _ = run_cli("init", "-o", target)
        self.assertEqual(code, 0)
        self.assertTrue(os.path.isfile(target))
        self.assertIn("Created", out)

    def test_init_refuses_overwrite(self):
        target = os.path.join(self.tmp.name, "new-flags.yaml")
        run_cli("init", "-o", target)
        code, _, err = run_cli("init", "-o", target)
        self.assertEqual(code, 1)
        self.assertIn("already exists", err)

    def test_init_force(self):
        target = os.path.join(self.tmp.name, "new-flags.yaml")
        run_cli("init", "-o", target)
        code, _, _ = run_cli("init", "-o", target, "--force")
        self.assertEqual(code, 0)

    def test_generated_file_validates(self):
        target = os.path.join(self.tmp.name, "new-flags.yaml")
        run_cli("init", "-o", target)
        code, _, _ = run_cli("validate", "--file", target)
        self.assertEqual(code, 0)


class TestValidate(CliTestCase):
    def test_valid(self):
        code, out, _ = run_cli(*self.flag_args("validate"))
        self.assertEqual(code, 0)
        self.assertIn("OK", out)

    def test_valid_json(self):
        code, out, _ = run_cli(*self.flag_args("validate", "--format", "json"))
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["flags"], 3)

    def test_missing_file(self):
        code, _, err = run_cli("validate", "--file", "/nope/none.yaml")
        self.assertEqual(code, 2)
        self.assertIn("error", err)

    def test_invalid_file(self):
        bad = os.path.join(self.tmp.name, "bad.yaml")
        with open(bad, "w", encoding="utf-8") as fh:
            fh.write("flags:\n  - key: x\n    variants: {}\n")
        code, _, err = run_cli("validate", "--file", bad)
        self.assertEqual(code, 2)
        self.assertIn("error", err)


class TestList(CliTestCase):
    def test_list_table(self):
        code, out, _ = run_cli(*self.flag_args("list"))
        self.assertEqual(code, 0)
        self.assertIn("new-checkout", out)
        self.assertIn("legacy-api", out)

    def test_list_json(self):
        code, out, _ = run_cli(*self.flag_args("list", "--format", "json"))
        payload = json.loads(out)
        self.assertEqual(len(payload), 3)

    def test_list_filter_state(self):
        code, out, _ = run_cli(*self.flag_args("list", "--state", "off"))
        self.assertIn("legacy-api", out)
        self.assertNotIn("new-checkout", out)

    def test_list_filter_owner(self):
        code, out, _ = run_cli(*self.flag_args("list", "--owner", "team-payments"))
        self.assertIn("new-checkout", out)
        self.assertNotIn("legacy-api", out)

    def test_list_evaluated(self):
        code, out, _ = run_cli(
            *self.flag_args(
                "list", "--evaluated", "-c", "targetingKey=u1,email=dev@example.com"
            )
        )
        self.assertIn("REASON", out)
        self.assertIn("TARGETING_MATCH", out)
        self.assertIn("DISABLED", out)


class TestShow(CliTestCase):
    def test_show(self):
        code, out, _ = run_cli(*self.flag_args("show", "new-checkout"))
        self.assertEqual(code, 0)
        self.assertIn("new-checkout", out)
        self.assertIn("variant = enabled", out)

    def test_show_json(self):
        code, out, _ = run_cli(*self.flag_args("show", "new-checkout", "--format", "json"))
        payload = json.loads(out)
        self.assertEqual(payload["flag"]["key"], "new-checkout")
        self.assertEqual(payload["evaluation"]["reason"], "SPLIT")

    def test_show_missing(self):
        code, _, err = run_cli(*self.flag_args("show", "nope"))
        self.assertEqual(code, 1)
        self.assertIn("not found", err)


class TestEval(CliTestCase):
    def test_eval_single(self):
        code, out, _ = run_cli(
            *self.flag_args("eval", "new-checkout", "-c", "targetingKey=u1")
        )
        self.assertEqual(code, 0)
        self.assertIn("enabled", out)
        self.assertIn("SPLIT", out)

    def test_eval_all(self):
        code, out, _ = run_cli(*self.flag_args("eval", "-c", "targetingKey=u1"))
        self.assertIn("REASON", out)
        self.assertIn("DEFAULT", out)

    def test_eval_json(self):
        code, out, _ = run_cli(
            *self.flag_args("eval", "legacy-api", "--format", "json")
        )
        payload = json.loads(out)
        self.assertEqual(payload["reason"], "DISABLED")


class TestGate(CliTestCase):
    def test_gate_pass(self):
        code, out, _ = run_cli(
            *self.flag_args(
                "gate",
                "--expect",
                "new-checkout=true",
                "-c",
                "targetingKey=u1",
            )
        )
        self.assertEqual(code, 0)
        self.assertIn("PASS", out)

    def test_gate_fail(self):
        code, _, err = run_cli(
            *self.flag_args(
                "gate",
                "--expect",
                "new-checkout=false",
                "-c",
                "targetingKey=u1",
            )
        )
        self.assertEqual(code, 3)
        self.assertIn("gate failed", err)

    def test_gate_multiple_expectations(self):
        code, out, _ = run_cli(
            *self.flag_args(
                "gate",
                "--expect",
                "new-checkout=true",
                "--expect",
                "legacy-api=false",
                "-c",
                "targetingKey=u1",
            )
        )
        self.assertEqual(code, 0)
        self.assertIn("gate passed", out)

    def test_gate_missing_flag(self):
        code, _, _ = run_cli(
            *self.flag_args("gate", "--expect", "ghost=true")
        )
        self.assertEqual(code, 3)

    def test_gate_json_output(self):
        code, out, _ = run_cli(
            *self.flag_args(
                "gate",
                "--expect",
                "new-checkout=true",
                "-c",
                "targetingKey=u1",
                "--format",
                "json",
            )
        )
        payload = json.loads(out)
        self.assertTrue(payload["passed"])


class TestDiff(CliTestCase):
    def test_diff_no_changes(self):
        code, out, _ = run_cli("diff", self.flag_file, self.flag_file)
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "No changes.")

    def test_diff_changes(self):
        modified = os.path.join(self.tmp.name, "modified.yaml")
        with open(modified, "w", encoding="utf-8") as fh:
            fh.write(FLAGS_YAML.replace("percentage: 100", "percentage: 20"))
        code, out, _ = run_cli("diff", self.flag_file, modified)
        self.assertEqual(code, 0)
        self.assertIn("Changed flag: new-checkout", out)
        self.assertIn("percentage", out)

    def test_diff_json(self):
        modified = os.path.join(self.tmp.name, "modified.yaml")
        with open(modified, "w", encoding="utf-8") as fh:
            fh.write(FLAGS_YAML.replace("state: on", "state: off"))
        code, out, _ = run_cli("diff", self.flag_file, modified, "--format", "json")
        payload = json.loads(out)
        self.assertIn("new-checkout", payload["changed"])
        self.assertEqual(payload["max_risk"], "critical")


class TestLint(CliTestCase):
    def test_lint_runs(self):
        code, out, _ = run_cli(*self.flag_args("lint"))
        self.assertEqual(code, 0)

    def test_lint_fail_on(self):
        bare = os.path.join(self.tmp.name, "bare.yaml")
        with open(bare, "w", encoding="utf-8") as fh:
            fh.write(
                "flags:\n"
                "  - key: bare\n"
                "    state: on\n"
                "    variant_type: boolean\n"
                "    variants:\n"
                "      on: true\n"
                "      off: false\n"
                "    default_variant: off\n"
            )
        code, _, _ = run_cli("lint", "--file", bare, "--fail-on", "warning")
        self.assertEqual(code, 2)
        code, _, _ = run_cli("lint", "--file", bare, "--fail-on", "error")
        self.assertEqual(code, 0)

    def test_lint_json(self):
        code, out, _ = run_cli(*self.flag_args("lint", "--format", "json"))
        payload = json.loads(out)
        self.assertIn("summary", payload)


class TestExport(CliTestCase):
    def test_export_env(self):
        code, out, _ = run_cli(
            *self.flag_args(
                "export", "--format", "env", "-c", "targetingKey=u1"
            )
        )
        self.assertIn("export FLAGFORGE_NEW_CHECKOUT=true", out)

    def test_export_table(self):
        code, out, _ = run_cli(*self.flag_args("export", "--format", "table"))
        self.assertIn("ROLLOUT", out)

    def test_export_markdown(self):
        code, out, _ = run_cli(*self.flag_args("export", "--format", "markdown"))
        self.assertIn("| Flag |", out)

    def test_export_json_definitions(self):
        code, out, _ = run_cli(*self.flag_args("export", "--format", "json"))
        payload = json.loads(out)
        self.assertIn("flags", payload)

    def test_export_json_evaluated(self):
        code, out, _ = run_cli(
            *self.flag_args(
                "export", "--format", "json", "--evaluated", "-c", "targetingKey=u1"
            )
        )
        payload = json.loads(out)
        self.assertEqual(payload["new-checkout"]["reason"], "SPLIT")

    def test_export_schema(self):
        code, out, _ = run_cli(*self.flag_args("export", "--format", "schema"))
        payload = json.loads(out)
        self.assertEqual(payload["title"], "FlagForge flag file")


class TestHash(CliTestCase):
    def test_murmur(self):
        code, out, _ = run_cli("hash", "murmur", "hello")
        payload = json.loads(out)
        self.assertEqual(payload["input"], "hello")
        self.assertIsInstance(payload["murmur3_32"], int)

    def test_murmur_with_seed(self):
        code, out, _ = run_cli("hash", "murmur", "hello", "--seed", "42")
        payload = json.loads(out)
        self.assertEqual(payload["seed"], 42)

    def test_bucket(self):
        code, out, _ = run_cli("hash", "bucket", "new-checkout", "user-1")
        payload = json.loads(out)
        self.assertTrue(0 <= payload["bucket"] < 100)

    def test_bucket_with_samples(self):
        code, out, _ = run_cli(
            "hash", "bucket", "new-checkout", "user-1", "--samples", "500"
        )
        payload = json.loads(out)
        self.assertIn("distribution", payload)
        self.assertGreater(len(payload["distribution"]), 50)

    def test_bucket_with_salt(self):
        code, out, _ = run_cli(
            "hash", "bucket", "new-checkout", "user-1", "--salt", "v2"
        )
        payload = json.loads(out)
        self.assertEqual(payload["salt"], "v2")

    def test_hash_without_subcommand(self):
        code, _, err = run_cli("hash")
        self.assertEqual(code, 1)
        self.assertIn("subcommand", err)


class TestMisc(CliTestCase):
    def test_no_command_prints_help(self):
        code, out, _ = run_cli()
        self.assertEqual(code, 1)
        self.assertIn("usage", out.lower())

    def test_version(self):
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stdout(io.StringIO()):
                main(["--version"])
        self.assertEqual(ctx.exception.code, 0)

    def test_parse_context_string(self):
        self.assertEqual(
            parse_context_string("a=1, b=2"), {"a": "1", "b": "2"}
        )
        with self.assertRaises(ValueError):
            parse_context_string("invalid")


if __name__ == "__main__":
    unittest.main()
