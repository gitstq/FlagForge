"""models 校验测试。"""

from __future__ import annotations

import unittest

from flagforge.models import (
    Condition,
    EvaluationContext,
    Flag,
    FlagSet,
    Rollout,
    TargetingRule,
    ValidationError,
)


def make_flag(**overrides):
    data = {
        "key": "demo-flag",
        "state": "on",
        "variant_type": "boolean",
        "variants": {"on": True, "off": False},
        "default_variant": "off",
    }
    data.update(overrides)
    return Flag.from_dict(data)


class TestFlagValidation(unittest.TestCase):
    def test_minimal_flag(self):
        flag = make_flag()
        self.assertEqual(flag.key, "demo-flag")
        self.assertEqual(flag.state, "on")

    def test_invalid_key(self):
        with self.assertRaises(ValidationError):
            make_flag(key="has space")
        with self.assertRaises(ValidationError):
            make_flag(key="-leading-dash")

    def test_invalid_state(self):
        with self.assertRaises(ValidationError):
            make_flag(state="enabled")

    def test_default_variant_must_exist(self):
        with self.assertRaises(ValidationError):
            make_flag(default_variant="missing")

    def test_variant_type_mismatch(self):
        with self.assertRaises(ValidationError):
            make_flag(variant_type="string", variants={"a": 1}, default_variant="a")

    def test_object_variant(self):
        flag = make_flag(
            variant_type="object",
            variants={"cfg": {"limit": 5}},
            default_variant="cfg",
        )
        self.assertEqual(flag.variants["cfg"], {"limit": 5})

    def test_unknown_key_rejected(self):
        with self.assertRaises(ValidationError):
            make_flag(bogus=1)

    def test_duplicate_flag_keys(self):
        with self.assertRaises(ValidationError):
            FlagSet.from_dict(
                {"flags": [make_flag().to_dict(), make_flag().to_dict()]}
            )


class TestRolloutValidation(unittest.TestCase):
    def test_percentage_bounds(self):
        with self.assertRaises(ValidationError):
            Rollout.from_dict({"percentage": 101, "variant": "on"})
        with self.assertRaises(ValidationError):
            Rollout.from_dict({"percentage": -1, "variant": "on"})

    def test_variant_or_variants_required(self):
        with self.assertRaises(ValidationError):
            Rollout.from_dict({"percentage": 10})

    def test_variants_must_sum_to_100(self):
        with self.assertRaises(ValidationError):
            Rollout.from_dict({"percentage": 50, "variants": {"a": 60, "b": 60}})

    def test_mutually_exclusive(self):
        with self.assertRaises(ValidationError):
            Rollout.from_dict(
                {"percentage": 50, "variant": "on", "variants": {"on": 100}}
            )

    def test_undefined_variant_rejected(self):
        with self.assertRaises(ValidationError):
            make_flag(rollout={"percentage": 10, "variant": "nonexistent"})


class TestTargetingValidation(unittest.TestCase):
    def test_rule_requires_id_and_conditions(self):
        with self.assertRaises(ValidationError):
            TargetingRule.from_dict({"variant": "on"})

    def test_rule_variant_must_exist(self):
        with self.assertRaises(ValidationError):
            make_flag(
                targeting=[
                    {
                        "id": "r1",
                        "conditions": [
                            {"field": "plan", "op": "in", "values": ["pro"]}
                        ],
                        "variant": "nonexistent",
                    }
                ]
            )

    def test_bad_operator(self):
        with self.assertRaises(ValidationError):
            Condition.from_dict({"field": "a", "op": "like", "values": ["b"]})

    def test_bad_regex(self):
        with self.assertRaises(ValidationError):
            Condition.from_dict({"field": "a", "op": "matches", "values": ["("]})

    def test_duplicate_rule_ids(self):
        with self.assertRaises(ValidationError):
            make_flag(
                targeting=[
                    {
                        "id": "dup",
                        "conditions": [{"field": "a", "op": "exists"}],
                        "variant": "on",
                    },
                    {
                        "id": "dup",
                        "conditions": [{"field": "b", "op": "exists"}],
                        "variant": "off",
                    },
                ]
            )


class TestEvaluationContext(unittest.TestCase):
    def test_targeting_key_special_field(self):
        ctx = EvaluationContext.from_dict({"targetingKey": "u1", "plan": "pro"})
        self.assertEqual(ctx.get("targetingKey"), "u1")
        self.assertTrue(ctx.has("targetingKey"))
        self.assertEqual(ctx.get("plan"), "pro")

    def test_missing_field(self):
        ctx = EvaluationContext.from_dict({})
        self.assertFalse(ctx.has("plan"))
        self.assertIsNone(ctx.get("plan"))

    def test_null_field_is_absent(self):
        ctx = EvaluationContext.from_dict({"plan": None})
        self.assertFalse(ctx.has("plan"))

    def test_round_trip(self):
        ctx = EvaluationContext.from_dict({"targetingKey": "u1", "plan": "pro"})
        self.assertEqual(ctx.to_dict(), {"plan": "pro", "targetingKey": "u1"})


class TestFlagSet(unittest.TestCase):
    def test_get_and_keys(self):
        flag_set = FlagSet.from_dict(
            {
                "flags": [
                    make_flag().to_dict(),
                    make_flag(key="second").to_dict(),
                ]
            }
        )
        self.assertEqual(flag_set.keys(), ["demo-flag", "second"])
        self.assertIsNotNone(flag_set.get("second"))
        self.assertIsNone(flag_set.get("nope"))

    def test_bare_list_accepted(self):
        flag_set = FlagSet.from_dict([make_flag().to_dict()])
        self.assertEqual(len(flag_set.flags), 1)

    def test_missing_flags_key(self):
        with self.assertRaises(ValidationError):
            FlagSet.from_dict({"nope": []})


if __name__ == "__main__":
    unittest.main()
