"""loader 测试（JSON / YAML 子集 / 校验 / schema）。"""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from flagforge.loader import (
    find_flag_file,
    load_flags,
    load_flags_from_string,
    schema_document,
    validate_flag_set,
)
from flagforge.models import ValidationError

GOOD_JSON = json.dumps(
    {
        "flags": [
            {
                "key": "json-flag",
                "state": "on",
                "variant_type": "boolean",
                "variants": {"on": True, "off": False},
                "default_variant": "off",
                "rollout": {"percentage": 10, "variant": "on"},
                "metadata": {"owner": "team-a"},
            }
        ]
    }
)

GOOD_YAML = """\
flags:
  - key: yaml-flag
    description: 一个 YAML flag
    state: on
    variant_type: string
    variants:
      v2: "new"
      v1: "old"
    default_variant: v1
    rollout:
      percentage: 25
      variant: v2
    metadata:
      owner: team-b
      tags:
        - checkout
"""


class TestJsonLoading(unittest.TestCase):
    def test_load_from_string(self):
        flag_set = load_flags_from_string(GOOD_JSON)
        self.assertEqual(flag_set.keys(), ["json-flag"])

    def test_load_from_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "flags.json")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(GOOD_JSON)
            flag_set = load_flags(path)
            self.assertEqual(len(flag_set.flags), 1)

    def test_invalid_json_reports_source(self):
        with self.assertRaises(ValidationError) as ctx:
            load_flags_from_string("{not json", source="bad.json")
        self.assertIn("bad.json", str(ctx.exception))

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            load_flags("/nonexistent/path/flags.json")


class TestYamlLoading(unittest.TestCase):
    def test_load_from_string(self):
        flag_set = load_flags_from_string(GOOD_YAML)
        flag = flag_set.get("yaml-flag")
        self.assertIsNotNone(flag)
        self.assertEqual(flag.rollout.percentage, 25)
        self.assertEqual(flag.metadata["owner"], "team-b")
        self.assertEqual(flag.metadata["tags"], ["checkout"])

    def test_yaml_file_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "flags.yaml")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(GOOD_YAML)
            self.assertEqual(len(load_flags(path).flags), 1)

    def test_invalid_yaml_reports_source(self):
        with self.assertRaises(ValidationError) as ctx:
            load_flags_from_string("flags:\n  - key: x\n   bad: 1", source="f.yaml")
        self.assertIn("f.yaml", str(ctx.exception))

    def test_semantic_error_wrapped_with_source(self):
        bad = "flags:\n  - key: x\n    variants: {}\n    default_variant: a\n"
        with self.assertRaises(ValidationError) as ctx:
            load_flags_from_string(bad, source="sem.yaml")
        self.assertIn("sem.yaml", str(ctx.exception))


class TestFindFlagFile(unittest.TestCase):
    def test_explicit_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "custom.yaml")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(GOOD_YAML)
            self.assertEqual(find_flag_file(path), path)

    def test_auto_detect(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "flagforge.yaml")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(GOOD_YAML)
            os.chdir(tmp)
            try:
                self.assertTrue(
                    find_flag_file(None, start_dir=tmp).endswith("flagforge.yaml")
                )
            finally:
                os.chdir(os.path.dirname(tmp))

    def test_none_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                find_flag_file(None, start_dir=tmp)


class TestSemanticWarnings(unittest.TestCase):
    def test_full_rollout_warning(self):
        text = json.dumps(
            {
                "flags": [
                    {
                        "key": "full",
                        "state": "on",
                        "variants": {"a": 1},
                        "default_variant": "a",
                        "rollout": {"percentage": 100, "variant": "a"},
                    }
                ]
            }
        )
        warnings = validate_flag_set(load_flags_from_string(text))
        self.assertTrue(any("full" in w for w in warnings))


class TestSchemaDocument(unittest.TestCase):
    def test_schema_shape(self):
        schema = schema_document()
        self.assertEqual(schema["title"], "FlagForge flag file")
        self.assertIn("flags", schema["properties"])
        self.assertIn("flag", schema["definitions"])
        # 可被 JSON 序列化
        json.dumps(schema)


if __name__ == "__main__":
    unittest.main()
