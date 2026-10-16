"""lint 测试。"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from flagforge.lint import format_lint_report, lint_flag_set
from flagforge.loader import load_flags_from_string


def flag_set(text):
    return load_flags_from_string(text)


CLEAN = """\
flags:
  - key: clean-flag
    description: 描述完整
    state: on
    variant_type: boolean
    variants:
      on: true
      off: false
    default_variant: off
    metadata:
      owner: team-a
      updated_at: "2026-10-15T00:00:00Z"
"""

BARE = """\
flags:
  - key: bare-flag
    state: on
    variant_type: boolean
    variants:
      on: true
      off: false
    default_variant: off
"""

NOOP = """\
flags:
  - key: noop
    description: d
    state: on
    variant_type: integer
    variants:
      a: 1
    default_variant: a
    rollout:
      percentage: 50
      variant: a
    metadata:
      owner: t
"""

FULL = """\
flags:
  - key: full
    description: d
    state: on
    variant_type: integer
    variants:
      a: 1
      b: 2
    default_variant: a
    rollout:
      percentage: 100
      variant: b
    metadata:
      owner: t
"""


def _dated_flag(key, iso):
    return (
        "flags:\n"
        "  - key: %s\n"
        "    description: d\n"
        "    state: on\n"
        "    variant_type: boolean\n"
        "    variants:\n"
        "      on: true\n"
        "      off: false\n"
        "    default_variant: off\n"
        "    metadata:\n"
        "      owner: t\n"
        '      updated_at: "%s"\n' % (key, iso)
    )


class TestLint(unittest.TestCase):
    def test_clean_flag_set(self):
        report = lint_flag_set(flag_set(CLEAN))
        self.assertEqual(report.count("warning"), 0)
        self.assertEqual(report.count("error"), 0)
        self.assertEqual(format_lint_report(report), "All checks passed.")

    def test_missing_owner_and_description(self):
        report = lint_flag_set(flag_set(BARE))
        rules = {f.rule for f in report.findings}
        self.assertIn("flag-missing-owner", rules)
        self.assertIn("flag-missing-description", rules)

    def test_noop_rollout(self):
        report = lint_flag_set(flag_set(NOOP))
        rules = {f.rule for f in report.findings}
        self.assertIn("flag-noop-rollout", rules)

    def test_full_rollout(self):
        report = lint_flag_set(flag_set(FULL))
        rules = {f.rule for f in report.findings}
        self.assertIn("flag-full-rollout", rules)

    def test_stale_flag(self):
        old = (datetime.now(timezone.utc) - timedelta(days=200)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        report = lint_flag_set(flag_set(_dated_flag("stale", old)), stale_days=90)
        rules = {f.rule for f in report.findings}
        self.assertIn("flag-stale", rules)

    def test_fresh_flag_not_stale(self):
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        report = lint_flag_set(flag_set(_dated_flag("fresh", now)), stale_days=90)
        rules = {f.rule for f in report.findings}
        self.assertNotIn("flag-stale", rules)

    def test_key_naming(self):
        text = CLEAN.replace("clean-flag", "BadKey")
        report = lint_flag_set(flag_set(text))
        rules = {f.rule for f in report.findings}
        self.assertIn("flag-key-naming", rules)

    def test_orphan_tag(self):
        text = CLEAN.replace("      owner: team-a", "      owner: team-a\n      tags:\n        - solo")
        report = lint_flag_set(flag_set(text))
        rules = {f.rule for f in report.findings}
        self.assertIn("flag-orphan-tag", rules)

    def test_long_targeting(self):
        rules_yaml = ""
        for i in range(10):
            rules_yaml += (
                "      - id: r%d\n"
                "        conditions:\n"
                "          - field: f%d\n"
                "            op: exists\n"
                "        variant: on\n" % (i, i)
            )
        text = (
            "flags:\n"
            "  - key: many-rules\n"
            "    description: d\n"
            "    state: on\n"
            "    variant_type: boolean\n"
            "    variants:\n"
            "      on: true\n"
            "      off: false\n"
            "    default_variant: off\n"
            "    targeting:\n" + rules_yaml +
            "    metadata:\n"
            "      owner: t\n"
        )
        report = lint_flag_set(flag_set(text))
        rules = {f.rule for f in report.findings}
        self.assertIn("flag-long-targeting", rules)


if __name__ == "__main__":
    unittest.main()
