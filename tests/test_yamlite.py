"""yamlite 解析器测试。"""

from __future__ import annotations

import unittest

from flagforge.yamlite import YamlError, parse, parse_scalar


class TestScalars(unittest.TestCase):
    def test_plain_string(self):
        self.assertEqual(parse("key: hello world"), {"key": "hello world"})

    def test_single_quoted(self):
        self.assertEqual(parse("key: 'it''s ok'"), {"key": "it's ok"})

    def test_double_quoted_with_escapes(self):
        self.assertEqual(parse('key: "a\\tb\\nc"'), {"key": "a\tb\nc"})

    def test_unicode_escape(self):
        self.assertEqual(parse('key: "\\u4e2d\\u6587"'), {"key": "中文"})

    def test_booleans_and_null(self):
        self.assertEqual(
            parse("a: true\nb: false\nc: null\nd: ~"),
            {"a": True, "b": False, "c": None, "d": None},
        )

    def test_yes_no_stay_strings(self):
        # 刻意不支持 YAML 1.1 的 yes/no 布尔，避免意外
        self.assertEqual(parse("a: yes"), {"a": "yes"})

    def test_numbers(self):
        self.assertEqual(
            parse("a: 42\nb: -7\nc: 3.14\nd: 0x1F\ne: 0o17\nf: 1e3"),
            {"a": 42, "b": -7, "c": 3.14, "d": 31, "e": 15, "f": 1000.0},
        )

    def test_string_with_hash_is_kept(self):
        self.assertEqual(parse("url: http://x.dev/#anchor"), {"url": "http://x.dev/#anchor"})

    def test_inline_comment_stripped(self):
        self.assertEqual(parse("key: value  # comment"), {"key": "value"})

    def test_empty_string_value(self):
        self.assertEqual(parse('key: ""'), {"key": ""})
        self.assertEqual(parse("key:"), {"key": None})


class TestStructures(unittest.TestCase):
    def test_nested_mapping(self):
        text = "a:\n  b:\n    c: 1\n  d: two"
        self.assertEqual(parse(text), {"a": {"b": {"c": 1}, "d": "two"}})

    def test_sequence_of_scalars(self):
        self.assertEqual(parse("items:\n  - a\n  - b\n  - 3"), {"items": ["a", "b", 3]})

    def test_sequence_of_mappings(self):
        text = "rules:\n  - id: a\n    op: in\n  - id: b\n    op: gt"
        self.assertEqual(
            parse(text),
            {"rules": [{"id": "a", "op": "in"}, {"id": "b", "op": "gt"}]},
        )

    def test_nested_sequences(self):
        text = "matrix:\n  - - 1\n    - 2\n  - - 3\n    - 4"
        self.assertEqual(parse(text), {"matrix": [[1, 2], [3, 4]]})

    def test_block_literal(self):
        text = "script: |\n  line one\n  line two"
        self.assertEqual(parse(text), {"script": "line one\nline two\n"})

    def test_block_literal_strip(self):
        text = "script: |-\n  line one\n  line two"
        self.assertEqual(parse(text), {"script": "line one\nline two"})

    def test_block_folded(self):
        text = "text: >\n  folded one\n  folded two"
        self.assertEqual(parse(text), {"text": "folded one folded two\n"})

    def test_document_marker(self):
        self.assertEqual(parse("---\nkey: 1"), {"key": 1})

    def test_deeply_nested_list_of_mappings(self):
        text = (
            "flags:\n"
            "  - key: x\n"
            "    targeting:\n"
            "      - id: r1\n"
            "        conditions:\n"
            "          - field: plan\n"
            "            op: in\n"
            "            values: [pro, ent]\n"
        )
        parsed = parse(text)
        self.assertEqual(
            parsed["flags"][0]["targeting"][0]["conditions"][0]["values"],
            ["pro", "ent"],
        )


class TestFlowCollections(unittest.TestCase):
    def test_flow_sequence_of_scalars(self):
        self.assertEqual(parse("values: [a, b, 3]"), {"values": ["a", "b", 3]})

    def test_flow_sequence_quoted(self):
        self.assertEqual(
            parse('values: ["@example.com", \'x, y\']'),
            {"values": ["@example.com", "x, y"]},
        )

    def test_flow_mapping(self):
        self.assertEqual(
            parse("variants: {on: true, off: false}"),
            {"variants": {"on": True, "off": False}},
        )

    def test_flow_nested(self):
        self.assertEqual(
            parse("cfg: {limits: [1, 2], mode: fast}"),
            {"cfg": {"limits": [1, 2], "mode": "fast"}},
        )

    def test_empty_flow_collections(self):
        self.assertEqual(parse("a: []"), {"a": []})
        self.assertEqual(parse("b: {}"), {"b": {}})

    def test_trailing_comma(self):
        self.assertEqual(parse("a: [1, 2,]"), {"a": [1, 2]})

    def test_flow_in_sequence_item(self):
        self.assertEqual(parse("items:\n  - [1, 2]\n  - [3]"), {"items": [[1, 2], [3]]})

    def test_flow_mapping_bad_entry(self):
        with self.assertRaises(YamlError):
            parse("cfg: {a}")

    def test_unbalanced_flow(self):
        with self.assertRaises(YamlError):
            parse("cfg: [a, b")

    def test_regex_starting_with_bracket_stays_string(self):
        # 以 [ 开头但不以 ] 结尾 → 纯标量
        self.assertEqual(parse("p: [a-z]+"), {"p": "[a-z]+"})

    def test_bracketed_string_needs_quotes(self):
        self.assertEqual(parse("p: '[abc]'"), {"p": "[abc]"})

    def test_flow_mapping_in_flag_config(self):
        text = """\
flags:
  - key: x
    variants: {on: true, off: false}
    default_variant: off
"""
        parsed = parse(text)
        self.assertEqual(parsed["flags"][0]["variants"], {"on": True, "off": False})


class TestErrors(unittest.TestCase):
    def test_duplicate_key(self):
        with self.assertRaises(YamlError):
            parse("a: 1\na: 2")

    def test_tab_indent(self):
        with self.assertRaises(YamlError):
            parse("a:\n\tb: 1")

    def test_multiple_documents(self):
        with self.assertRaises(YamlError):
            parse("a: 1\n---\nb: 2")

    def test_bad_indent(self):
        with self.assertRaises(YamlError):
            parse("a: 1\n  b: 2")

    def test_missing_colon(self):
        with self.assertRaises(YamlError):
            parse("a: 1\nplain line")

    def test_unknown_escape(self):
        with self.assertRaises(YamlError):
            parse('key: "bad \\q escape"')

    def test_empty_document(self):
        self.assertIsNone(parse(""))
        self.assertIsNone(parse("# only a comment\n"))


class TestParseScalar(unittest.TestCase):
    def test_parse_scalar_direct(self):
        self.assertEqual(parse_scalar("  spaced  "), "spaced")
        self.assertEqual(parse_scalar("'123'"), "123")
        self.assertEqual(parse_scalar("true"), True)
        self.assertEqual(parse_scalar("null"), None)


if __name__ == "__main__":
    unittest.main()
