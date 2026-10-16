"""OpenFeature 兼容客户端测试。"""

from __future__ import annotations

import unittest

from flagforge.openfeature import Client, NoFlagFoundError, OpenFeature
from flagforge.loader import load_flags_from_string

FLAGS = """\
flags:
  - key: bool-flag
    description: 布尔开关
    state: on
    variant_type: boolean
    variants:
      on: true
      off: false
    default_variant: off
    rollout:
      percentage: 100
      variant: on
  - key: str-flag
    description: 字符串开关
    state: on
    variant_type: string
    variants:
      v2: "new"
      v1: "old"
    default_variant: v1
  - key: num-flag
    description: 数字开关
    state: off
    variant_type: integer
    variants:
      ten: 10
      zero: 0
    default_variant: zero
  - key: obj-flag
    description: 对象开关
    state: on
    variant_type: object
    variants:
      cfg:
        limit: 5
        mode: strict
      empty: {}
    default_variant: empty
"""


class TestClient(unittest.TestCase):
    def setUp(self):
        self.client = Client(load_flags_from_string(FLAGS), name="test")

    def test_get_variant_details(self):
        details = self.client.get_variant("bool-flag", {"targetingKey": "u"})
        self.assertEqual(details["variant"], "on")
        self.assertEqual(details["value"], True)
        self.assertEqual(details["reason"], "SPLIT")
        self.assertEqual(details["flag_key"], "bool-flag")

    def test_typed_getters(self):
        self.assertTrue(
            self.client.get_boolean_value("bool-flag", False, {"targetingKey": "u"})
        )
        self.assertEqual(
            self.client.get_string_value("str-flag", "fallback", {}), "old"
        )
        self.assertEqual(
            self.client.get_integer_value("num-flag", -1, {}), 0
        )
        self.assertEqual(
            self.client.get_float_value("num-flag", -1.0, {}), 0.0
        )
        self.assertEqual(
            self.client.get_object_value("obj-flag", {}, {}), {}
        )

    def test_type_mismatch_returns_default(self):
        # str-flag 是 string 类型，请求 boolean 时返回调用方默认值
        self.assertFalse(
            self.client.get_boolean_value("str-flag", False, {})
        )

    def test_missing_flag_raises(self):
        with self.assertRaises(NoFlagFoundError):
            self.client.get_variant("nope")

    def test_evaluate_all(self):
        results = self.client.evaluate_all({"targetingKey": "u"})
        self.assertEqual(len(results), 4)
        self.assertIn("bool-flag", results)

    def test_evaluate_all_subset(self):
        results = self.client.evaluate_all({}, keys=["str-flag"])
        self.assertEqual(list(results), ["str-flag"])

    def test_client_metadata(self):
        self.assertEqual(self.client.metadata["name"], "test")

    def test_get_variant_value(self):
        self.assertEqual(
            self.client.get_variant_value("str-flag", {}), "old"
        )


class TestOpenFeatureFacade(unittest.TestCase):
    def test_from_flags(self):
        flag_set = load_flags_from_string(FLAGS)
        facade = OpenFeature.from_flags(flag_set, domain="my-app")
        client = facade.get_client()
        self.assertEqual(
            client.get_string_value("str-flag", "", {}), "old"
        )

    def test_from_string(self):
        facade = OpenFeature.from_string(FLAGS)
        self.assertTrue(
            facade.get_client().get_boolean_value(
                "bool-flag", False, {"targetingKey": "u"}
            )
        )

    def test_missing_client(self):
        facade = OpenFeature()
        with self.assertRaises(NoFlagFoundError):
            facade.get_client("ghost")


if __name__ == "__main__":
    unittest.main()
