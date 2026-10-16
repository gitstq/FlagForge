"""models — FlagForge 的核心数据模型。

所有模型均为标准库 ``dataclasses``，提供严格的构造校验与
``to_dict`` / ``from_dict`` 序列化能力。校验错误统一抛出
:class:`ValidationError`（携带字段路径，便于定位配置问题）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

__all__ = [
    "Condition",
    "EvaluationContext",
    "EvaluationResult",
    "Flag",
    "FlagSet",
    "Rollout",
    "TargetingRule",
    "ValidationError",
    "VARIANT_TYPES",
]

VARIANT_TYPES = ("boolean", "string", "integer", "float", "object")

_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

#: 支持的 targeting 条件操作符
CONDITION_OPS = (
    "in",
    "not_in",
    "exists",
    "not_exists",
    "gt",
    "gte",
    "lt",
    "lte",
    "starts_with",
    "ends_with",
    "contains",
    "matches",
)

#: 合法的 flag 状态
FLAG_STATES = ("on", "off")


class ValidationError(ValueError):
    """配置校验错误。"""

    def __init__(self, path: str, message: str):
        self.path = path
        self.message = message
        super().__init__("%s: %s" % (path, message))


@dataclass
class Condition:
    """单条 targeting 条件，例如 ``plan in [pro, enterprise]``。"""

    field: str
    op: str
    values: List[Any] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.field, str) or not self.field:
            raise ValidationError("condition.field", "must be a non-empty string")
        if self.op not in CONDITION_OPS:
            raise ValidationError(
                "condition.op",
                "unsupported operator '%s' (expected one of: %s)"
                % (self.op, ", ".join(CONDITION_OPS)),
            )
        if not isinstance(self.values, list):
            raise ValidationError("condition.values", "must be a list")
        if self.op in ("in", "not_in") and not self.values:
            raise ValidationError("condition.values", "in/not_in requires values")
        if self.op == "matches":
            for pattern in self.values:
                if not isinstance(pattern, str):
                    raise ValidationError(
                        "condition.values", "matches requires string patterns"
                    )
                try:
                    re.compile(pattern)
                except re.error as exc:
                    raise ValidationError(
                        "condition.values", "invalid regex '%s': %s" % (pattern, exc)
                    )

    def to_dict(self) -> Dict[str, Any]:
        return {"field": self.field, "op": self.op, "values": list(self.values)}

    @classmethod
    def from_dict(cls, data: Dict[str, Any], path: str = "condition") -> "Condition":
        if not isinstance(data, dict):
            raise ValidationError(path, "must be a mapping")
        unknown = set(data) - {"field", "op", "values"}
        if unknown:
            raise ValidationError(
                path, "unknown keys: %s" % ", ".join(sorted(unknown))
            )
        if "field" not in data or "op" not in data:
            raise ValidationError(path, "'field' and 'op' are required")
        return cls(
            field=data["field"],
            op=data["op"],
            values=data.get("values", []),
        )


@dataclass
class TargetingRule:
    """一条定向规则：所有条件命中后，按 percentage 比例（或全量）返回 variant。"""

    id: str = ""
    description: str = ""
    conditions: List[Condition] = field(default_factory=list)
    variant: Optional[str] = None
    percentage: Optional[float] = None
    bucket_by: str = "targetingKey"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValidationError("rule.id", "each targeting rule needs an id")
        if not isinstance(self.conditions, list) or not self.conditions:
            raise ValidationError("rule.conditions", "each rule needs conditions")
        self.conditions = [
            c if isinstance(c, Condition) else Condition.from_dict(c)
            for c in self.conditions
        ]
        if self.variant is None:
            raise ValidationError("rule.variant", "each rule needs a target variant")
        if self.percentage is not None:
            if not isinstance(self.percentage, (int, float)) or isinstance(
                self.percentage, bool
            ):
                raise ValidationError("rule.percentage", "must be a number 0-100")
            if not 0 <= float(self.percentage) <= 100:
                raise ValidationError("rule.percentage", "must be within 0-100")
        if not isinstance(self.bucket_by, str) or not self.bucket_by:
            raise ValidationError("rule.bucket_by", "must be a non-empty string")

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "id": self.id,
            "conditions": [c.to_dict() for c in self.conditions],
            "variant": self.variant,
            "bucket_by": self.bucket_by,
        }
        if self.description:
            out["description"] = self.description
        if self.percentage is not None:
            out["percentage"] = self.percentage
        if self.metadata:
            out["metadata"] = dict(self.metadata)
        return out

    @classmethod
    def from_dict(cls, data: Dict[str, Any], path: str = "rule") -> "TargetingRule":
        if not isinstance(data, dict):
            raise ValidationError(path, "must be a mapping")
        allowed = {
            "id",
            "description",
            "conditions",
            "variant",
            "percentage",
            "bucket_by",
            "metadata",
        }
        unknown = set(data) - allowed
        if unknown:
            raise ValidationError(path, "unknown keys: %s" % ", ".join(sorted(unknown)))
        if "id" not in data:
            raise ValidationError(path, "'id' is required")
        conditions = data.get("conditions")
        if not isinstance(conditions, list):
            raise ValidationError(path + ".conditions", "must be a list")
        return cls(
            id=str(data["id"]),
            description=str(data.get("description", "")),
            conditions=[Condition.from_dict(c, path + ".conditions") for c in conditions],
            variant=data.get("variant"),
            percentage=data.get("percentage"),
            bucket_by=str(data.get("bucket_by", "targetingKey")),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class Rollout:
    """flag 级灰度配置。

    * ``percentage``: 命中灰度的流量比例（0-100）
    * ``variant``: 灰度流量看到的变体名（与 ``variants`` 二选一）
    * ``variants``: 灰度流量内的加权变体分配（权重和为 100）
    * ``bucket_by``: 分桶上下文字段（默认 ``targetingKey``）
    """

    percentage: float = 0.0
    variant: Optional[str] = None
    variants: Dict[str, float] = field(default_factory=dict)
    bucket_by: str = "targetingKey"

    def __post_init__(self) -> None:
        if isinstance(self.percentage, bool) or not isinstance(
            self.percentage, (int, float)
        ):
            raise ValidationError("rollout.percentage", "must be a number 0-100")
        self.percentage = float(self.percentage)
        if not 0 <= self.percentage <= 100:
            raise ValidationError("rollout.percentage", "must be within 0-100")
        if self.variant is None and not self.variants:
            raise ValidationError(
                "rollout", "either 'variant' or 'variants' is required"
            )
        if self.variant is not None and self.variants:
            raise ValidationError(
                "rollout", "'variant' and 'variants' are mutually exclusive"
            )
        if self.variants:
            total = 0.0
            for name, weight in self.variants.items():
                if isinstance(weight, bool) or not isinstance(weight, (int, float)):
                    raise ValidationError(
                        "rollout.variants", "weight for '%s' must be a number" % name
                    )
                if weight < 0:
                    raise ValidationError(
                        "rollout.variants", "weight for '%s' must be >= 0" % name
                    )
                total += float(weight)
            if abs(total - 100.0) > 1e-6:
                raise ValidationError(
                    "rollout.variants", "weights must sum to 100 (got %s)" % total
                )
        if not isinstance(self.bucket_by, str) or not self.bucket_by:
            raise ValidationError("rollout.bucket_by", "must be a non-empty string")

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "percentage": self.percentage,
            "bucket_by": self.bucket_by,
        }
        if self.variant is not None:
            out["variant"] = self.variant
        if self.variants:
            out["variants"] = dict(self.variants)
        return out

    @classmethod
    def from_dict(cls, data: Dict[str, Any], path: str = "rollout") -> "Rollout":
        if not isinstance(data, dict):
            raise ValidationError(path, "must be a mapping")
        allowed = {"percentage", "variant", "variants", "bucket_by"}
        unknown = set(data) - allowed
        if unknown:
            raise ValidationError(path, "unknown keys: %s" % ", ".join(sorted(unknown)))
        if "percentage" not in data:
            raise ValidationError(path, "'percentage' is required")
        return cls(
            percentage=data["percentage"],
            variant=data.get("variant"),
            variants=dict(data.get("variants", {})),
            bucket_by=str(data.get("bucket_by", "targetingKey")),
        )


@dataclass
class Flag:
    """一个功能开关。"""

    key: str
    state: str = "off"
    description: str = ""
    variant_type: Optional[str] = None
    variants: Dict[str, Any] = field(default_factory=dict)
    default_variant: Optional[str] = None
    targeting: List[TargetingRule] = field(default_factory=list)
    rollout: Optional[Rollout] = None
    bucket_salt: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not _KEY_RE.match(self.key):
            raise ValidationError(
                "flag.key",
                "'%s' is invalid (expected 1-128 chars: letters, digits, '.', '_', '-')"
                % self.key,
            )
        if self.state not in FLAG_STATES:
            raise ValidationError(
                "flag.state",
                "'%s' is invalid (expected one of: %s)" % (self.state, ", ".join(FLAG_STATES)),
            )
        if self.variant_type is not None and self.variant_type not in VARIANT_TYPES:
            raise ValidationError(
                "flag.variant_type",
                "'%s' is invalid (expected one of: %s)"
                % (self.variant_type, ", ".join(VARIANT_TYPES)),
            )
        if not isinstance(self.variants, dict) or not self.variants:
            raise ValidationError("flag.variants", "must define at least one variant")
        for name, value in self.variants.items():
            if not isinstance(name, str) or not name:
                raise ValidationError("flag.variants", "variant names must be strings")
            self._check_variant_value(name, value)
        if self.default_variant is None:
            raise ValidationError("flag.default_variant", "is required")
        if self.default_variant not in self.variants:
            raise ValidationError(
                "flag.default_variant",
                "'%s' is not defined in variants" % self.default_variant,
            )
        self.targeting = [
            r if isinstance(r, TargetingRule) else TargetingRule.from_dict(r)
            for r in self.targeting
        ]
        seen_rules = set()
        for rule in self.targeting:
            if rule.id in seen_rules:
                raise ValidationError(
                    "flag.targeting", "duplicate rule id '%s'" % rule.id
                )
            seen_rules.add(rule.id)
            if rule.variant not in self.variants:
                raise ValidationError(
                    "flag.targeting",
                    "rule '%s' targets undefined variant '%s'"
                    % (rule.id, rule.variant),
                )
        if self.rollout is not None:
            if not isinstance(self.rollout, Rollout):
                self.rollout = Rollout.from_dict(self.rollout)
            for name in list(self.rollout.variants) + (
                [self.rollout.variant] if self.rollout.variant else []
            ):
                if name not in self.variants:
                    raise ValidationError(
                        "flag.rollout", "references undefined variant '%s'" % name
                    )
        if not isinstance(self.bucket_salt, str):
            raise ValidationError("flag.bucket_salt", "must be a string")

    def _check_variant_value(self, name: str, value: Any) -> None:
        if self.variant_type is None:
            return
        checks = {
            "boolean": lambda v: isinstance(v, bool),
            "string": lambda v: isinstance(v, str),
            "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "float": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            "object": lambda v: isinstance(v, (dict, list)),
        }
        if not checks[self.variant_type](value):
            raise ValidationError(
                "flag.variants.%s" % name,
                "value %r does not match variant_type '%s'" % (value, self.variant_type),
            )

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "key": self.key,
            "state": self.state,
            "variants": dict(self.variants),
            "default_variant": self.default_variant,
        }
        if self.variant_type is not None:
            out["variant_type"] = self.variant_type
        if self.description:
            out["description"] = self.description
        if self.targeting:
            out["targeting"] = [r.to_dict() for r in self.targeting]
        if self.rollout is not None:
            out["rollout"] = self.rollout.to_dict()
        if self.bucket_salt:
            out["bucket_salt"] = self.bucket_salt
        if self.metadata:
            out["metadata"] = dict(self.metadata)
        return out

    @classmethod
    def from_dict(cls, data: Dict[str, Any], path: str = "flag") -> "Flag":
        if not isinstance(data, dict):
            raise ValidationError(path, "must be a mapping")
        allowed = {
            "key",
            "state",
            "description",
            "variant_type",
            "variants",
            "default_variant",
            "targeting",
            "rollout",
            "bucket_salt",
            "metadata",
        }
        unknown = set(data) - allowed
        if unknown:
            raise ValidationError(path, "unknown keys: %s" % ", ".join(sorted(unknown)))
        if "key" not in data:
            raise ValidationError(path, "'key' is required")
        if "variants" not in data:
            raise ValidationError(path + ".variants", "is required")
        targeting = data.get("targeting", [])
        if not isinstance(targeting, list):
            raise ValidationError(path + ".targeting", "must be a list")
        return cls(
            key=str(data["key"]),
            state=str(data.get("state", "off")),
            description=str(data.get("description", "")),
            variant_type=(
                str(data["variant_type"])
                if data.get("variant_type") is not None
                else None
            ),
            variants=dict(data["variants"]),
            default_variant=data.get("default_variant"),
            targeting=[
                TargetingRule.from_dict(r, path + ".targeting") for r in targeting
            ],
            rollout=(
                Rollout.from_dict(data["rollout"], path + ".rollout")
                if data.get("rollout") is not None
                else None
            ),
            bucket_salt=str(data.get("bucket_salt", "")),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class EvaluationResult:
    """一次评估的结果。"""

    flag_key: str
    variant: str
    value: Any
    reason: str
    rule_id: Optional[str] = None

    #: OpenFeature 规范中的理由码
    REASONS = ("TARGETING_MATCH", "SPLIT", "DEFAULT", "DISABLED", "ERROR")

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "flag_key": self.flag_key,
            "variant": self.variant,
            "value": self.value,
            "reason": self.reason,
        }
        if self.rule_id:
            out["rule_id"] = self.rule_id
        return out


@dataclass
class EvaluationContext:
    """评估上下文（字段映射）。targetingKey 为 OpenFeature 约定的分桶键。"""

    targeting_key: str = ""
    fields: Dict[str, Any] = field(default_factory=dict)

    def get(self, name: str, default: Any = None) -> Any:
        if name == "targetingKey":
            return self.targeting_key if self.targeting_key else default
        return self.fields.get(name, default)

    def has(self, name: str) -> bool:
        if name == "targetingKey":
            return bool(self.targeting_key)
        return name in self.fields and self.fields[name] is not None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvaluationContext":
        if not isinstance(data, dict):
            raise ValidationError("context", "must be a mapping")
        data = dict(data)
        targeting_key = str(data.pop("targetingKey", "") or "")
        return cls(targeting_key=targeting_key, fields=data)

    def to_dict(self) -> Dict[str, Any]:
        out = dict(self.fields)
        if self.targeting_key:
            out["targetingKey"] = self.targeting_key
        return out


@dataclass
class FlagSet:
    """一组 flag 的集合，附带元信息。"""

    flags: List[Flag] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.flags = [f if isinstance(f, Flag) else Flag.from_dict(f) for f in self.flags]
        seen = set()
        for flag in self.flags:
            if flag.key in seen:
                raise ValidationError(
                    "flags", "duplicate flag key '%s'" % flag.key
                )
            seen.add(flag.key)

    def get(self, key: str) -> Optional[Flag]:
        for flag in self.flags:
            if flag.key == key:
                return flag
        return None

    def keys(self) -> List[str]:
        return [f.key for f in self.flags]

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"flags": [f.to_dict() for f in self.flags]}
        if self.meta:
            out["meta"] = dict(self.meta)
        return out

    @classmethod
    def from_dict(cls, data: Any, path: str = "flags") -> "FlagSet":
        if isinstance(data, dict):
            if "flags" not in data:
                raise ValidationError(path, "missing top-level 'flags' list")
            raw_flags = data["flags"]
            meta = dict(data.get("meta", {}))
        elif isinstance(data, list):
            raw_flags = data
            meta = {}
        else:
            raise ValidationError(path, "must be a mapping with a 'flags' list")
        if not isinstance(raw_flags, list):
            raise ValidationError(path + ".flags", "must be a list")
        return cls(
            flags=[Flag.from_dict(f, "%s[%d]" % (path, i)) for i, f in enumerate(raw_flags)],
            meta=meta,
        )
