"""diff 测试。"""

from __future__ import annotations

import unittest

from flagforge.diff import diff_flag_sets, format_diff
from flagforge.loader import load_flags_from_string


def flag_set(key, **overrides):
    data = {
        "key": key,
        "state": "on",
        "variant_type": "boolean",
        "variants": {"on": True, "off": False},
        "default_variant": "off",
    }
    data.update(overrides)
    return load_flags_from_string(
        __import__("json").dumps({"flags": [data]})
    )


class TestDiff(unittest.TestCase):
    def test_no_changes(self):
        a = flag_set("x")
        b = flag_set("x")
        result = diff_flag_sets(a, b)
        self.assertFalse(result.has_changes)
        self.assertEqual(format_diff(result), "No changes.")

    def test_added_and_removed(self):
        a = flag_set("keep")
        a.flags.append(flag_set("gone").flags[0])
        b = flag_set("keep")
        b.flags.append(flag_set("new").flags[0])
        result = diff_flag_sets(a, b)
        self.assertEqual(result.added, ["new"])
        self.assertEqual(result.removed, ["gone"])

    def test_percentage_change_risk(self):
        a = flag_set("x", rollout={"percentage": 10, "variant": "on"})
        b = flag_set("x", rollout={"percentage": 90, "variant": "on"})
        result = diff_flag_sets(a, b)
        changes = result.changed["x"]
        self.assertTrue(any(c.field_path.endswith("percentage") for c in changes))
        self.assertEqual(result.max_risk, "critical")

    def test_state_change_to_off_is_critical(self):
        a = flag_set("x")
        b = flag_set("x", state="off")
        result = diff_flag_sets(a, b)
        change = [c for c in result.changed["x"] if c.field_path == "state"][0]
        self.assertEqual(change.risk, "critical")

    def test_default_variant_change_is_critical(self):
        a = flag_set("x")
        b = flag_set("x", default_variant="on")
        result = diff_flag_sets(a, b)
        change = [
            c for c in result.changed["x"] if c.field_path == "default_variant"
        ][0]
        self.assertEqual(change.risk, "critical")

    def test_to_dict_serializable(self):
        import json

        a = flag_set("x")
        b = flag_set("y")
        result = diff_flag_sets(a, b)
        json.dumps(result.to_dict())


if __name__ == "__main__":
    unittest.main()
