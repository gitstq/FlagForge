"""yamlite — 零依赖 YAML 子集解析器。

为什么需要它：FlagForge 坚持“零依赖”原则，配置格式需要同时支持 JSON
（完整支持）与常用的 YAML 块状写法。``yamlite`` 实现了日常配置中最常用、
可预测性最强的 YAML 子集，刻意避开 YAML 规范中容易引发意外的特性
（锚点/别名、yes/no 布尔、隐式类型歧义等），以保证行为可预期、
可测试、无安全隐患。

支持的特性：
    * 块映射（``key: value``，嵌套由缩进表达）
    * 块序列（``- item``，支持紧凑映射 ``- key: value`` 与嵌套序列 ``- - x``）
    * 流式集合（标量层级）：``[a, b]`` 序列与 ``{k: v}`` 映射，可嵌套
    * 标量：无引号字符串、``'单引号'``、``"双引号"``（含 ``\\n`` / ``\\t`` /
      ``\\uXXXX`` 等转义）
    * 布尔（true/false）、null（null/~/Null/NULL）、整数（含 0x/0o/0b）、浮点数
    * 块标量 ``|`` / ``|-`` / ``>`` / ``>-``（缩进指示符被接受但不生效）
    * 注释（``#``，要求前方为空白或位于行首）
    * 文档开头的 ``---``

明确不支持的特性（遇到会抛出 :class:`YamlError`）：
    * 锚点 / 别名（``&`` / ``*``）
    * 多文档（第二个 ``---``）
    * ``yes/no/on/off`` 作为布尔值（保持为字符串）
    * 标签（``!!str`` 等）

注意事项：
    * 以 ``[`` 开头且以 ``]`` 结尾的纯标量会被视为流式序列（与 YAML 规范一致），
      如需字面量请加引号，例如 ``pattern: '[abc]'``

所有错误都带有行号，便于定位配置问题。
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

__all__ = ["YamlError", "parse", "parse_scalar"]

_MAX_DEPTH = 64


class YamlError(ValueError):
    """YAML 解析错误，携带行号信息。"""

    def __init__(self, message: str, line_no: int = 0):
        self.line_no = line_no
        if line_no:
            super().__init__("line %d: %s" % (line_no, message))
        else:
            super().__init__(message)


class _Line:
    __slots__ = ("indent", "text", "no")

    def __init__(self, indent: int, text: str, no: int):
        self.indent = indent
        self.text = text
        self.no = no


def _strip_inline_comment(text: str) -> str:
    """去掉行内注释（``#`` 前必须是空白，且不在引号内）。"""
    in_single = False
    in_double = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if in_single:
            if ch == "'":
                if i + 1 < n and text[i + 1] == "'":
                    i += 2
                    continue
                in_single = False
        elif in_double:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_double = False
        else:
            if ch == "'":
                in_single = True
            elif ch == '"':
                in_double = True
            elif ch == "#" and (i == 0 or text[i - 1] in " \t"):
                return text[:i].rstrip()
        i += 1
    return text.rstrip()


def _scan_lines(source: str) -> List[_Line]:
    lines: List[_Line] = []
    for idx, raw in enumerate(source.splitlines(), start=1):
        leading = raw[: len(raw) - len(raw.lstrip(" \t"))]
        if "\t" in leading:
            raise YamlError("tab characters are not allowed for indentation", idx)
        stripped = raw.lstrip(" ")
        indent = len(raw) - len(stripped)
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped == "---":
            if lines:
                raise YamlError("multiple YAML documents are not supported", idx)
            continue
        if stripped == "...":
            continue
        content = _strip_inline_comment(stripped)
        if not content:
            continue
        lines.append(_Line(indent, content, idx))
    return lines


def _find_colon(text: str) -> int:
    """返回映射键值分隔符 ``:`` 的下标；不在映射中则返回 -1。"""
    in_single = False
    in_double = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if in_single:
            if ch == "'":
                if i + 1 < n and text[i + 1] == "'":
                    i += 2
                    continue
                in_single = False
        elif in_double:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_double = False
        else:
            if ch == "'":
                in_single = True
            elif ch == '"':
                in_double = True
            elif ch == ":" and (i + 1 == n or text[i + 1] in " \t"):
                return i
        i += 1
    return -1


def _split_key(text: str, line_no: int) -> Tuple[str, str]:
    colon = _find_colon(text)
    if colon < 0:
        raise YamlError("expected 'key: value' mapping entry", line_no)
    return text[:colon].strip(), text[colon + 1 :].strip()


def _try_split_key(text: str) -> Tuple[bool, str, str]:
    colon = _find_colon(text)
    if colon < 0:
        return False, "", text
    return True, text[:colon].strip(), text[colon + 1 :].strip()


def _unquote_key(key: str, line_no: int) -> str:
    if len(key) >= 2 and key[0] == key[-1] and key[0] in "'\"":
        inner = key[1:-1]
        if key[0] == "'":
            return inner.replace("''", "'")
        return _unescape_double(inner, line_no)
    if not key:
        raise YamlError("empty mapping key", line_no)
    return key


def _unescape_double(text: str, line_no: int) -> str:
    out: List[str] = []
    i = 0
    n = len(text)
    simple = {
        "n": "\n",
        "t": "\t",
        "r": "\r",
        "0": "\0",
        "\\": "\\",
        '"': '"',
        "/": "/",
        "a": "\a",
        "b": "\b",
        "f": "\f",
        "v": "\v",
        "e": "\x1b",
    }
    while i < n:
        ch = text[i]
        if ch == "\\":
            if i + 1 >= n:
                raise YamlError("dangling escape in double-quoted string", line_no)
            nxt = text[i + 1]
            if nxt == "u":
                hex_part = text[i + 2 : i + 6]
                if len(hex_part) != 4:
                    raise YamlError(
                        "invalid \\u escape in double-quoted string", line_no
                    )
                try:
                    out.append(chr(int(hex_part, 16)))
                except ValueError:
                    raise YamlError(
                        "invalid \\u escape in double-quoted string", line_no
                    )
                i += 6
                continue
            if nxt not in simple:
                raise YamlError(
                    "unknown escape '\\%s' in double-quoted string" % nxt, line_no
                )
            out.append(simple[nxt])
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _looks_quoted(text: str) -> bool:
    return len(text) >= 2 and text[0] == text[-1] and text[0] in "'\""


def parse_scalar(text: str, line_no: int = 0) -> Any:
    """把单个标量文本转换为 Python 值。"""
    text = text.strip()
    if text == "":
        return None
    if _looks_quoted(text):
        if text[0] == "'":
            return text[1:-1].replace("''", "'")
        return _unescape_double(text[1:-1], line_no)
    if text in ("null", "Null", "NULL", "~"):
        return None
    if text in ("true", "True", "TRUE"):
        return True
    if text in ("false", "False", "FALSE"):
        return False
    lowered = text.lower()
    try:
        if lowered.startswith(("0x", "-0x", "+0x")):
            return int(text, 16)
        if lowered.startswith(("0o", "-0o", "+0o")):
            return int(text, 8)
        if lowered.startswith(("0b", "-0b", "+0b")):
            return int(text, 2)
    except ValueError:
        pass
    unsigned = text[1:] if text[:1] in "+-" else text
    if unsigned.isdigit():
        return int(text)
    # 浮点（显式排除 inf/nan 字面量，避免意外类型）
    if any(c in text for c in ".eE") and not lowered.endswith(("inf", "nan")):
        try:
            return float(text)
        except ValueError:
            pass
    return text


def _is_sequence_entry(text: str) -> bool:
    return text == "-" or text.startswith("- ")


def _split_flow_items(inner: str, line_no: int) -> List[str]:
    """按顶层逗号切分流式集合内容（尊重引号与嵌套括号）。"""
    items: List[str] = []
    depth = 0
    in_single = False
    in_double = False
    start = 0
    i = 0
    n = len(inner)
    while i < n:
        ch = inner[i]
        if in_single:
            if ch == "'":
                if i + 1 < n and inner[i + 1] == "'":
                    i += 2
                    continue
                in_single = False
        elif in_double:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_double = False
        else:
            if ch == "'":
                in_single = True
            elif ch == '"':
                in_double = True
            elif ch in "[{":
                depth += 1
            elif ch in "]}":
                depth -= 1
                if depth < 0:
                    raise YamlError("unbalanced brackets in flow collection", line_no)
            elif ch == "," and depth == 0:
                items.append(inner[start:i])
                start = i + 1
        i += 1
    if depth != 0:
        raise YamlError("unbalanced brackets in flow collection", line_no)
    tail = inner[start:]
    if tail.strip():
        items.append(tail)
    return [item.strip() for item in items if item.strip()]


def parse_flow(text: str, line_no: int = 0) -> Any:
    """解析流式集合或标量（``[a, b]`` / ``{k: v}`` / 标量）。"""
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [parse_flow(item, line_no) for item in _split_flow_items(inner, line_no)]
    if text.startswith("{") and text.endswith("}"):
        inner = text[1:-1].strip()
        if not inner:
            return {}
        result: Dict[str, Any] = {}
        for item in _split_flow_items(inner, line_no):
            is_map, key, value = _try_split_key(item)
            if not is_map:
                raise YamlError(
                    "flow mapping entry '%s' must be key: value" % item, line_no
                )
            result[_unquote_key(key, line_no)] = parse_flow(value, line_no)
        return result
    # 不以匹配括号闭合的 `[`/`{` 开头文本（如正则 `[a-z]+`）视为普通标量
    return parse_scalar(text, line_no)


def _is_flow(text: str) -> bool:
    return bool(text) and text[0] in "[{"


def _looks_block_scalar_header(text: str) -> bool:
    if not text or text[0] not in "|>":
        return False
    if len(text) == 1:
        return True
    return all(c in "+-0123456789" for c in text[1:])


def _collect_block_scalar(
    lines: List[_Line], start: int, parent_indent: int, header: str
) -> Tuple[str, int]:
    fold = header[0] == ">"
    chomp = header[1:] if len(header) > 1 else ""
    body: List[str] = []
    i = start
    block_indent = None
    while i < len(lines):
        line = lines[i]
        if line.indent <= parent_indent:
            break
        if block_indent is None:
            block_indent = line.indent
        body.append((" " * (line.indent - block_indent)) + line.text)
        i += 1
    if not body:
        return "", i
    if fold:
        text = " ".join(part.strip() for part in body) + "\n"
    else:
        text = "\n".join(body) + "\n"
    if chomp == "-":
        text = text.rstrip("\n")
    return text, i


def _item_extent(lines: List[_Line], start: int, indent: int) -> int:
    """返回从 ``start`` 起、缩进大于 ``indent`` 的连续行的结束下标（不含）。"""
    j = start
    while j < len(lines) and lines[j].indent > indent:
        j += 1
    return j


def _parse_block(
    lines: List[_Line], start: int, indent: int, depth: int
) -> Tuple[Any, int]:
    if depth > _MAX_DEPTH:
        raise YamlError("maximum nesting depth (%d) exceeded" % _MAX_DEPTH, 0)
    if start >= len(lines):
        return None, start
    first = lines[start]
    if first.indent != indent:
        raise YamlError(
            "unexpected indentation (expected %d spaces, got %d)"
            % (indent, first.indent),
            first.no,
        )
    if _is_sequence_entry(first.text):
        return _parse_sequence(lines, start, indent, depth)
    return _parse_mapping(lines, start, indent, depth)


def _parse_sequence(
    lines: List[_Line], start: int, indent: int, depth: int
) -> Tuple[List[Any], int]:
    items: List[Any] = []
    i = start
    while i < len(lines):
        line = lines[i]
        if line.indent < indent:
            break
        if line.indent > indent:
            raise YamlError("unexpected indentation in sequence", line.no)
        if not _is_sequence_entry(line.text):
            break
        rest = line.text[1:].lstrip()
        item_col = indent + (len(line.text) - len(rest))
        if not rest:
            nxt = lines[i + 1] if i + 1 < len(lines) else None
            if nxt is not None and nxt.indent > indent:
                value, i = _parse_block(lines, i + 1, nxt.indent, depth + 1)
                items.append(value)
            else:
                items.append(None)
                i += 1
            continue
        if _looks_block_scalar_header(rest):
            text, i = _collect_block_scalar(lines, i + 1, indent, rest)
            items.append(text)
            continue
        if _is_flow(rest):
            items.append(parse_flow(rest, line.no))
            i += 1
            continue
        if _is_sequence_entry(rest):
            # 嵌套序列：- - x
            end = _item_extent(lines, i + 1, indent)
            sub_lines = [_Line(item_col, rest, line.no)] + lines[i + 1 : end]
            value, consumed = _parse_sequence(sub_lines, 0, item_col, depth + 1)
            items.append(value)
            i = i + consumed  # synthetic 行 + 其后消费的行数
            continue
        is_map, _key, _value = _try_split_key(rest)
        if is_map:
            # 紧凑映射：- key: value（可跨行延续）
            end = _item_extent(lines, i + 1, indent)
            sub_lines = [_Line(item_col, rest, line.no)] + lines[i + 1 : end]
            value, consumed = _parse_mapping(sub_lines, 0, item_col, depth + 1)
            items.append(value)
            i = i + consumed
            continue
        items.append(parse_scalar(rest, line.no))
        i += 1
    return items, i


def _parse_mapping(
    lines: List[_Line], start: int, indent: int, depth: int
) -> Tuple[Dict[str, Any], int]:
    result: Dict[str, Any] = {}
    i = start
    while i < len(lines):
        line = lines[i]
        if line.indent < indent:
            break
        if line.indent > indent:
            raise YamlError("unexpected indentation in mapping", line.no)
        if _is_sequence_entry(line.text):
            break
        key_text, value_text = _split_key(line.text, line.no)
        key = _unquote_key(key_text, line.no)
        if key in result:
            raise YamlError("duplicate mapping key '%s'" % key, line.no)
        if not value_text:
            nxt = lines[i + 1] if i + 1 < len(lines) else None
            if nxt is not None and nxt.indent > indent:
                value, i = _parse_block(lines, i + 1, nxt.indent, depth + 1)
                result[key] = value
            else:
                result[key] = None
                i += 1
            continue
        if _looks_block_scalar_header(value_text):
            text, i = _collect_block_scalar(lines, i + 1, indent, value_text)
            result[key] = text
            continue
        if _is_flow(value_text):
            result[key] = parse_flow(value_text, line.no)
            i += 1
            continue
        result[key] = parse_scalar(value_text, line.no)
        i += 1
    return result, i


def parse(source: str) -> Any:
    """解析 YAML 子集文本，返回 Python 对象。"""
    if not isinstance(source, str):
        raise YamlError("source must be a string")
    lines = _scan_lines(source)
    if not lines:
        return None
    value, consumed = _parse_block(lines, 0, lines[0].indent, 0)
    if consumed != len(lines):
        raise YamlError(
            "unexpected content after top-level block", lines[consumed].no
        )
    return value
