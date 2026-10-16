"""openfeature — OpenFeature 兼容客户端。

提供与 `OpenFeature specification <https://openfeature.dev>`_ 对齐的
评估语义与 API 形态（无需 SDK 运行时）：

* :class:`Client` 暴露 ``get_boolean_value`` / ``get_string_value`` /
  ``get_integer_value`` / ``get_float_value`` / ``get_object_value`` /
  ``get_variant`` / ``get_variant_value`` 等类型化取值方法
* 所有方法返回附带 evaluation details（含 ``reason`` 理由码，
  与 OpenFeature 的 ``TARGETING_MATCH`` / ``SPLIT`` / ``DEFAULT`` /
  ``DISABLED`` / ``ERROR`` 对齐）
* :class:`OpenFeature` 为门面（facade），负责从配置创建客户端

类型不匹配时行为与 OpenFeature 一致：返回 ``default_value`` 参数，
details 中 ``errorCode`` 为 ``TYPE_MISMATCH``。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .engine import evaluate, evaluate_all
from .loader import load_flags, load_flags_from_string
from .models import EvaluationContext, EvaluationResult, Flag, FlagSet

__all__ = ["Client", "OpenFeature", "NoFlagFoundError"]


class NoFlagFoundError(KeyError):
    """请求的 flag 不存在。"""


class Client:
    """OpenFeature 兼容的评估客户端。"""

    def __init__(
        self,
        flag_set: FlagSet,
        name: str = "flagforge",
        version: str = "1.0.0",
    ):
        self.flag_set = flag_set
        self.metadata = {"name": name, "version": version}

    # ------------------------------------------------------------------
    # OpenFeature 风格 API
    # ------------------------------------------------------------------
    def get_variant(self, key: str, context: Any = None) -> Dict[str, Any]:
        """返回评估详情（variant / value / reason / flagKey）。"""
        flag = self.flag_set.get(key)
        if flag is None:
            raise NoFlagFoundError(key)
        return evaluate(flag, context).to_dict()

    def get_variant_value(self, key: str, context: Any = None) -> Any:
        return self.get_variant(key, context)["value"]

    def get_boolean_value(
        self, key: str, default: bool, context: Any = None
    ) -> bool:
        return self._typed(key, default, context, bool, "boolean")

    def get_string_value(
        self, key: str, default: str, context: Any = None
    ) -> str:
        return self._typed(key, default, context, str, "string")

    def get_integer_value(
        self, key: str, default: int, context: Any = None
    ) -> int:
        return self._typed(key, default, context, int, "integer")

    def get_float_value(
        self, key: str, default: float, context: Any = None
    ) -> float:
        return self._typed(key, default, context, (int, float), "float")

    def get_object_value(
        self, key: str, default: Dict[str, Any], context: Any = None
    ) -> Dict[str, Any]:
        return self._typed(key, default, context, dict, "object")

    # ------------------------------------------------------------------
    # 批量评估
    # ------------------------------------------------------------------
    def evaluate_all(
        self, context: Any = None, keys: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        results = evaluate_all(self.flag_set, context, keys=keys)
        return {key: result.to_dict() for key, result in results.items()}

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------
    def _typed(
        self,
        key: str,
        default: Any,
        context: Any,
        expected: Any,
        expected_name: str,
    ) -> Any:
        flag = self.flag_set.get(key)
        if flag is None:
            raise NoFlagFoundError(key)
        result = evaluate(flag, context)
        value = result.value
        ok = self._type_ok(value, expected)
        if not ok:
            return default
        return value

    @staticmethod
    def _type_ok(value: Any, expected: Any) -> bool:
        if expected is bool:
            return isinstance(value, bool)
        if expected is int:
            return isinstance(value, int) and not isinstance(value, bool)
        if expected is float:
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if expected is str:
            return isinstance(value, str)
        if expected is dict:
            return isinstance(value, dict)
        return True


class OpenFeature:
    """OpenFeature 门面：从配置源创建 :class:`Client`。"""

    def __init__(self, domain: str = "default"):
        self.domain = domain
        self._clients: Dict[str, Client] = {}

    @classmethod
    def from_file(cls, path: str, domain: str = "default", name: str = "flagforge") -> "OpenFeature":
        facade = cls(domain=domain)
        facade.set_provider_from_file(path, name=name)
        return facade

    @classmethod
    def from_flags(cls, flag_set: FlagSet, domain: str = "default", name: str = "flagforge") -> "OpenFeature":
        facade = cls(domain=domain)
        facade._clients[name] = Client(flag_set, name=name)
        return facade

    def set_provider_from_file(self, path: str, name: str = "flagforge") -> None:
        self._clients[name] = Client(load_flags(path), name=name)

    def set_provider_from_string(self, text: str, name: str = "flagforge") -> None:
        self._clients[name] = Client(load_flags_from_string(text), name=name)

    def get_client(self, name: str = "flagforge") -> Client:
        if name not in self._clients:
            raise NoFlagFoundError("client '%s' is not configured" % name)
        return self._clients[name]

    def get_variant(self, key: str, context: Any = None) -> Dict[str, Any]:
        return self.get_client().get_variant(key, context)
