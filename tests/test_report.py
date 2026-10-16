"""report 导出格式测试。"""

from __future__ import annotations

import unittest

from flagforge.loader import load_flags_from_string
from flagforge.report import (
    format_env,
    format_markdown,
    format_table,
)

FLAGS = """\
flags:
  - key: new-checkout
    description: 新版结账
    state: on
    variant_type: boolean
    variants:
      enabled: true
      control: false
    default_variant: control
    rollout:
      percentage: 100
      variant: enabled
  - key: pricing
    description: 定价页
    state: on
    variant_type: string
    variants:
      modern: "modern"
      classic: "classic"
    default_variant: classic
"""


class TestFormats(unittest.TestCase):
    def setUp(self):
        self.flag_set = load_flags_from_string(FLAGS)

    def test_env_export(self):
        out = format_env(self.flag_set, {"targetingKey": "u1"})
        self.assertIn("export FLAGFORGE_NEW_CHECKOUT=true", out)
        self.assertIn("export FLAGFORGE_PRICING=classic", out)

    def test_env_quoting(self):
        text = """\
flags:
  - key: tricky
    description: d
    state: on
    variant_type: string
    variants:
      a: "hello world; rm -rf /"
      b: "safe"
    default_variant: a
"""
        out = format_env(load_flags_from_string(text), {})
        self.assertIn("'hello world; rm -rf /'", out)

    def test_table_plain(self):
        out = format_table(self.flag_set)
        self.assertIn("FLAG", out)
        self.assertIn("new-checkout", out)
        self.assertIn("ROLLOUT", out)

    def test_table_evaluated(self):
        out = format_table(self.flag_set, context={"targetingKey": "u"}, evaluated=True)
        self.assertIn("REASON", out)
        self.assertIn("SPLIT", out)

    def test_markdown_plain(self):
        out = format_markdown(self.flag_set)
        self.assertIn("| Flag | State |", out)
        self.assertIn("`new-checkout`", out)

    def test_markdown_evaluated(self):
        out = format_markdown(
            self.flag_set, context={"targetingKey": "u"}, evaluated=True
        )
        self.assertIn("| Flag | State | Variant | Value | Reason |", out)

    def test_markdown_escapes_pipe(self):
        text = """\
flags:
  - key: p
    description: "a | b"
    state: on
    variant_type: string
    variants:
      x: "1|2"
      y: "z"
    default_variant: y
"""
        out = format_markdown(load_flags_from_string(text))
        self.assertIn("a \\| b", out)


if __name__ == "__main__":
    unittest.main()
