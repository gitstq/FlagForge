"""loader — 配置加载与校验。

支持两种格式：

* **JSON**（完整支持，文件扩展名 ``.json`` 或内容以 ``{`` / ``[`` 开头）
* **YAML 子集**（块状结构，见 :mod:`flagforge.yamlite`）

配置文件顶层结构::

    flags:
      - key: new-checkout
        state: on
        ...
    meta:            # 可选元信息
      name: my-project

也接受顶层直接为 flag 列表的简写形式。
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from . import yamlite
from .models import FlagSet, ValidationError

__all__ = ["load_flags", "load_flags_from_string", "DEFAULT_FILENAMES"]

#: 自动探测的默认文件名（按优先级）
DEFAULT_FILENAMES = ("flagforge.yaml", "flagforge.yml", "flagforge.json")


def load_flags(path: str) -> FlagSet:
    """从文件加载 flag 集合。

    :raises FileNotFoundError: 文件不存在
    :raises ValidationError: 配置不合法
    """
    if not os.path.isfile(path):
        raise FileNotFoundError("flag file not found: %s" % path)
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    return load_flags_from_string(text, source=path)


def load_flags_from_string(text: str, source: str = "<string>") -> FlagSet:
    """从字符串加载 flag 集合（自动探测 JSON / YAML）。"""
    data = _parse_document(text, source)
    try:
        return FlagSet.from_dict(data)
    except ValidationError as exc:
        raise _rewrap(exc, source)


def _rewrap(exc: ValidationError, source: str) -> ValidationError:
    wrapped = ValidationError("%s: %s" % (source, exc.path), exc.message)
    return wrapped


def _parse_document(text: str, source: str) -> Any:
    stripped = text.lstrip()
    is_json = source.endswith(".json") or stripped.startswith(("{", "["))
    if is_json:
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValidationError(source, "invalid JSON: %s" % exc)
    try:
        return yamlite.parse(text)
    except yamlite.YamlError as exc:
        raise ValidationError(source, "invalid YAML subset: %s" % exc)


def find_flag_file(explicit: Optional[str] = None, start_dir: str = ".") -> str:
    """定位配置文件：显式路径优先，否则按 DEFAULT_FILENAMES 探测。"""
    if explicit:
        if not os.path.isfile(explicit):
            raise FileNotFoundError("flag file not found: %s" % explicit)
        return explicit
    for name in DEFAULT_FILENAMES:
        candidate = os.path.join(start_dir, name)
        if os.path.isfile(candidate):
            return candidate
    raise FileNotFoundError(
        "no flag file found (looked for: %s)" % ", ".join(DEFAULT_FILENAMES)
    )


def validate_flag_set(flag_set: FlagSet) -> List[str]:
    """返回语义级警告列表（不影响加载的合法性问题）。"""
    warnings: List[str] = []
    for flag in flag_set.flags:
        if not flag.description:
            warnings.append("%s: missing description" % flag.key)
        if flag.state == "on" and flag.rollout is not None:
            if flag.rollout.percentage >= 100 and not flag.targeting:
                warnings.append(
                    "%s: rollout is 100%% with no targeting — consider removing the flag"
                    % flag.key
                )
        if flag.rollout is not None and flag.rollout.variant == flag.default_variant:
            warnings.append(
                "%s: rollout variant equals default variant — flag has no effect"
                % flag.key
            )
    return warnings


def schema_document() -> Dict[str, Any]:
    """返回描述配置格式的 JSON Schema（供编辑器与外部工具使用）。"""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "FlagForge flag file",
        "type": "object",
        "required": ["flags"],
        "properties": {
            "flags": {
                "type": "array",
                "items": {"$ref": "#/definitions/flag"},
            },
            "meta": {"type": "object"},
        },
        "definitions": {
            "flag": {
                "type": "object",
                "required": ["key", "variants", "default_variant"],
                "properties": {
                    "key": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"},
                    "state": {"enum": ["on", "off"]},
                    "description": {"type": "string"},
                    "variant_type": {
                        "enum": ["boolean", "string", "integer", "float", "object"]
                    },
                    "variants": {"type": "object", "minProperties": 1},
                    "default_variant": {"type": "string"},
                    "bucket_salt": {"type": "string"},
                    "targeting": {
                        "type": "array",
                        "items": {"$ref": "#/definitions/rule"},
                    },
                    "rollout": {"$ref": "#/definitions/rollout"},
                    "metadata": {"type": "object"},
                },
            },
            "rule": {
                "type": "object",
                "required": ["id", "conditions", "variant"],
                "properties": {
                    "id": {"type": "string"},
                    "description": {"type": "string"},
                    "conditions": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"$ref": "#/definitions/condition"},
                    },
                    "variant": {"type": "string"},
                    "percentage": {"type": "number", "minimum": 0, "maximum": 100},
                    "bucket_by": {"type": "string"},
                    "metadata": {"type": "object"},
                },
            },
            "condition": {
                "type": "object",
                "required": ["field", "op"],
                "properties": {
                    "field": {"type": "string"},
                    "op": {
                        "enum": [
                            "in", "not_in", "exists", "not_exists", "gt", "gte",
                            "lt", "lte", "starts_with", "ends_with", "contains", "matches",
                        ]
                    },
                    "values": {"type": "array"},
                },
            },
            "rollout": {
                "type": "object",
                "required": ["percentage"],
                "properties": {
                    "percentage": {"type": "number", "minimum": 0, "maximum": 100},
                    "variant": {"type": "string"},
                    "variants": {"type": "object"},
                    "bucket_by": {"type": "string"},
                },
            },
        },
    }
