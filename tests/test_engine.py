"""engine 评估语义测试。"""

from __future__ import annotations

import unittest

from flagforge.engine import evaluate
from flagforge.models import Flag


def flag(**overrides):
    data = {
        "key": "f",
        "state": "on",
        "variant_type": "string",
        "variants": {"on": "new", "off": "old"},
        "default_variant": "off",
    }
    data.update(overrides)
    return Flag.from_dict(data)


class TestDisabled(unittest.TestCase):
    def test_off_flag_returns_default(self):
        result = evaluate(flag(state="off"), {"targetingKey": "u1"})
        self.assertEqual(result.variant, "off")
        self.assertEqual(result.reason, "DISABLED")


class TestDefault(unittest.TestCase):
    def test_no_rules_returns_default(self):
        result = evaluate(flag(), {})
        self.assertEqual(result.variant, "off")
        self.assertEqual(result.reason, "DEFAULT")


class TestRollout(unittest.TestCase):
    def test_zero_percentage_always_default(self):
        f = flag(rollout={"percentage": 0, "variant": "on"})
        for i in range(100):
            result = evaluate(f, {"targetingKey": "user-%d" % i})
            self.assertEqual(result.reason, "DEFAULT")

    def test_hundred_percentage_always_split(self):
        f = flag(rollout={"percentage": 100, "variant": "on"})
        for i in range(100):
            result = evaluate(f, {"targetingKey": "user-%d" % i})
            self.assertEqual(result.reason, "SPLIT")
            self.assertEqual(result.variant, "on")

    def test_percentage_50_is_deterministic(self):
        f = flag(rollout={"percentage": 50, "variant": "on"})
        first = evaluate(f, {"targetingKey": "user-42"})
        for _ in range(10):
            again = evaluate(f, {"targetingKey": "user-42"})
            self.assertEqual(first.to_dict(), again.to_dict())

    def test_percentage_is_monotonic(self):
        keys = [{"targetingKey": "user-%d" % i} for i in range(200)]
        f30 = flag(rollout={"percentage": 30, "variant": "on"})
        f60 = flag(rollout={"percentage": 60, "variant": "on"})
        hit30 = {k["targetingKey"] for k in keys if evaluate(f30, k).reason == "SPLIT"}
        hit60 = {k["targetingKey"] for k in keys if evaluate(f60, k).reason == "SPLIT"}
        self.assertTrue(hit30.issubset(hit60))
        self.assertTrue(45 <= len(hit30) <= 75)

    def test_weighted_variants_distribution(self):
        f = flag(
            variant_type="string",
            variants={"a": "A", "b": "B", "off": "old"},
            default_variant="off",
            rollout={"percentage": 100, "variants": {"a": 50, "b": 50}},
        )
        counts = {"a": 0, "b": 0}
        for i in range(400):
            result = evaluate(f, {"targetingKey": "user-%d" % i})
            counts[result.variant] += 1
        self.assertEqual(counts["a"] + counts["b"], 400)
        self.assertTrue(150 <= counts["a"] <= 250)
        self.assertTrue(150 <= counts["b"] <= 250)

    def test_custom_bucket_by(self):
        f = flag(
            rollout={"percentage": 50, "variant": "on", "bucket_by": "userId"}
        )
        # 同一 targetingKey 不同 userId → 结果可以不同（按 userId 分桶）
        r1 = evaluate(f, {"targetingKey": "t1", "userId": "u1"})
        r2 = evaluate(f, {"targetingKey": "t2", "userId": "u1"})
        self.assertEqual(r1.variant, r2.variant)

    def test_missing_bucket_key_uses_empty_string(self):
        f = flag(rollout={"percentage": 50, "variant": "on"})
        r1 = evaluate(f, {})
        r2 = evaluate(f, {})
        self.assertEqual(r1.to_dict(), r2.to_dict())

    def test_salt_reshuffles(self):
        base = flag(rollout={"percentage": 30, "variant": "on"})
        salted = flag(
            rollout={"percentage": 30, "variant": "on"}, bucket_salt="v2"
        )
        keys = [{"targetingKey": "user-%d" % i} for i in range(100)]
        hit_base = {k["targetingKey"] for k in keys if evaluate(base, k).reason == "SPLIT"}
        hit_salt = {k["targetingKey"] for k in keys if evaluate(salted, k).reason == "SPLIT"}
        self.assertNotEqual(hit_base, hit_salt)


class TestTargeting(unittest.TestCase):
    def _f(self, conditions, variant="on", percentage=None):
        rule = {
            "id": "r1",
            "conditions": conditions,
            "variant": variant,
        }
        if percentage is not None:
            rule["percentage"] = percentage
        return flag(targeting=[rule])

    def test_in_operator(self):
        f = self._f([{"field": "plan", "op": "in", "values": ["pro", "ent"]}])
        self.assertEqual(evaluate(f, {"plan": "pro"}).reason, "TARGETING_MATCH")
        self.assertEqual(evaluate(f, {"plan": "free"}).reason, "DEFAULT")

    def test_not_in_operator(self):
        f = self._f([{"field": "plan", "op": "not_in", "values": ["free"]}])
        self.assertEqual(evaluate(f, {"plan": "pro"}).reason, "TARGETING_MATCH")
        self.assertEqual(evaluate(f, {"plan": "free"}).reason, "DEFAULT")

    def test_in_loose_bool_match(self):
        f = self._f([{"field": "beta", "op": "in", "values": [True]}])
        self.assertEqual(evaluate(f, {"beta": "true"}).reason, "TARGETING_MATCH")

    def test_numeric_operators(self):
        f = self._f([{"field": "age", "op": "gte", "values": [18]}])
        self.assertEqual(evaluate(f, {"age": 20}).reason, "TARGETING_MATCH")
        self.assertEqual(evaluate(f, {"age": 12}).reason, "DEFAULT")
        self.assertEqual(evaluate(f, {"age": "20"}).reason, "TARGETING_MATCH")

    def test_lt_string_fallback(self):
        f = self._f([{"field": "name", "op": "lt", "values": ["m"]}])
        self.assertEqual(evaluate(f, {"name": "alice"}).reason, "TARGETING_MATCH")
        self.assertEqual(evaluate(f, {"name": "zoe"}).reason, "DEFAULT")

    def test_string_operators(self):
        f = self._f(
            [
                {
                    "field": "email",
                    "op": "ends_with",
                    "values": ["@example.com"],
                }
            ]
        )
        self.assertEqual(evaluate(f, {"email": "a@example.com"}).reason, "TARGETING_MATCH")
        self.assertEqual(evaluate(f, {"email": "a@other.com"}).reason, "DEFAULT")

    def test_contains_list(self):
        f = self._f([{"field": "roles", "op": "contains", "values": ["admin"]}])
        self.assertEqual(evaluate(f, {"roles": ["admin", "dev"]}).reason, "TARGETING_MATCH")
        self.assertEqual(evaluate(f, {"roles": ["dev"]}).reason, "DEFAULT")

    def test_contains_string(self):
        f = self._f([{"field": "ua", "op": "contains", "values": ["Mobile"]}])
        self.assertEqual(evaluate(f, {"ua": "Mobile Safari"}).reason, "TARGETING_MATCH")

    def test_matches_regex(self):
        f = self._f([{"field": "email", "op": "matches", "values": [r".+@example\.com$"]}])
        self.assertEqual(evaluate(f, {"email": "a@example.com"}).reason, "TARGETING_MATCH")
        self.assertEqual(evaluate(f, {"email": "a@other.com"}).reason, "DEFAULT")

    def test_exists(self):
        f = self._f([{"field": "beta", "op": "exists"}])
        self.assertEqual(evaluate(f, {"beta": "anything"}).reason, "TARGETING_MATCH")
        self.assertEqual(evaluate(f, {}).reason, "DEFAULT")

    def test_not_exists(self):
        f = self._f([{"field": "beta", "op": "not_exists"}])
        self.assertEqual(evaluate(f, {}).reason, "TARGETING_MATCH")
        self.assertEqual(evaluate(f, {"beta": "x"}).reason, "DEFAULT")

    def test_conditions_are_anded(self):
        f = self._f(
            [
                {"field": "plan", "op": "in", "values": ["pro"]},
                {"field": "country", "op": "in", "values": ["CN"]},
            ]
        )
        self.assertEqual(
            evaluate(f, {"plan": "pro", "country": "CN"}).reason, "TARGETING_MATCH"
        )
        self.assertEqual(
            evaluate(f, {"plan": "pro", "country": "US"}).reason, "DEFAULT"
        )

    def test_rule_ordering_first_match_wins(self):
        f = flag(
            targeting=[
                {
                    "id": "first",
                    "conditions": [{"field": "plan", "op": "in", "values": ["pro"]}],
                    "variant": "on",
                },
                {
                    "id": "second",
                    "conditions": [{"field": "plan", "op": "in", "values": ["pro"]}],
                    "variant": "off",
                },
            ]
        )
        result = evaluate(f, {"plan": "pro"})
        self.assertEqual(result.variant, "on")
        self.assertEqual(result.rule_id, "first")

    def test_rule_percentage(self):
        f = self._f(
            [{"field": "plan", "op": "in", "values": ["pro"]}], percentage=100
        )
        self.assertEqual(evaluate(f, {"plan": "pro"}).reason, "TARGETING_MATCH")
        f0 = self._f(
            [{"field": "plan", "op": "in", "values": ["pro"]}], percentage=0
        )
        self.assertEqual(evaluate(f0, {"plan": "pro"}).reason, "DEFAULT")

    def test_rule_percentage_falls_through_to_next_rule(self):
        f = flag(
            targeting=[
                {
                    "id": "partial",
                    "conditions": [{"field": "plan", "op": "in", "values": ["pro"]}],
                    "variant": "on",
                    "percentage": 0,
                },
                {
                    "id": "fallback",
                    "conditions": [{"field": "plan", "op": "in", "values": ["pro"]}],
                    "variant": "off",
                },
            ]
        )
        result = evaluate(f, {"plan": "pro"})
        self.assertEqual(result.variant, "off")
        self.assertEqual(result.rule_id, "fallback")


class TestEdgeCases(unittest.TestCase):
    def test_type_error_on_non_flag(self):
        with self.assertRaises(TypeError):
            evaluate({"key": "x"}, {})

    def test_context_accepts_dict(self):
        f = flag(rollout={"percentage": 100, "variant": "on"})
        self.assertEqual(evaluate(f, {"targetingKey": "u"}).reason, "SPLIT")

    def test_none_context(self):
        f = flag()
        self.assertEqual(evaluate(f, None).reason, "DEFAULT")

    def test_result_serializable(self):
        f = flag(rollout={"percentage": 100, "variant": "on"})
        result = evaluate(f, {"targetingKey": "u"})
        payload = result.to_dict()
        self.assertEqual(payload["flag_key"], "f")
        self.assertEqual(payload["reason"], "SPLIT")
        self.assertNotIn("rule_id", payload)


if __name__ == "__main__":
    unittest.main()
