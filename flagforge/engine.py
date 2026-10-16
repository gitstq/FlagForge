"""engine — FlagForge 的评估引擎。

评估顺序（与 OpenFeature 语义对齐）：

1. flag 为 ``off`` → 返回 ``default_variant``，reason = ``DISABLED``
2. 逐条检查 targeting 规则（按配置顺序）：
   * 所有条件命中 → 若规则带 ``percentage``，则按分桶决定：
     命中 → 规则 variant，reason = ``TARGETING_MATCH``
     未命中 → 继续下一条规则
   * 无条件 percentage → 直接返回规则 variant，reason = ``TARGETING_MATCH``
3. flag 级 ``rollout``：按分桶决定灰度流量
   命中 → 灰度 variant（单体或按权重分配），reason = ``SPLIT``
   未命中 → ``default_variant``，reason = ``DEFAULT``
4. 全部未命中 → ``default_variant``，reason = ``DEFAULT``

分桶为纯函数（见 :mod:`flagforge.hashing`），因此同一
``(flag, bucket_key)`` 组合的评估结果永远一致。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .hashing import bucket
from .models import (
    Condition,
    EvaluationContext,
    EvaluationResult,
    Flag,
    FlagSet,
    Rollout,
    TargetingRule,
)

__all__ = ["FlagSet", "evaluate", "evaluate_all"]


def _compare(op: str, actual: Any, expected: Any) -> bool:
    """数值/字符串比较，类型不兼容时返回 False。"""
    if op == "gt":
        return _numeric_gt(actual, expected)
    if op == "gte":
        return _numeric_gt(actual, expected, equal=True)
    if op == "lt":
        return _numeric_gt(expected, actual)
    if op == "lte":
        return _numeric_gt(expected, actual, equal=True)
    return False


def _numeric_gt(a: Any, b: Any, equal: bool = False) -> bool:
    a_num = a if isinstance(a, (int, float)) and not isinstance(a, bool) else None
    b_num = b if isinstance(b, (int, float)) and not isinstance(b, bool) else None
    if a_num is None or b_num is None:
        # 退化到字符串比较（保持可预测性）
        if isinstance(a, str) and isinstance(b, str):
            return a >= b if equal else a > b
        return False
    return a_num >= b_num if equal else a_num > b_num


def _match_condition(cond: Condition, ctx: EvaluationContext) -> bool:
    op = cond.op
    if op == "exists":
        return ctx.has(cond.field)
    if op == "not_exists":
        return not ctx.has(cond.field)
    if op in ("in", "not_in"):
        if not ctx.has(cond.field):
            return op == "not_in"
        actual = ctx.get(cond.field)
        hit = actual in cond.values
        # 宽松匹配：字符串 "true"/"1" 与布尔 True 视为相等，避免 YAML/CLI 类型歧义
        if not hit:
            for value in cond.values:
                if _loose_equal(actual, value):
                    hit = True
                    break
        return hit if op == "in" else not hit
    if op in ("gt", "gte", "lt", "lte"):
        if not ctx.has(cond.field):
            return False
        actual = ctx.get(cond.field)
        return any(_compare(op, actual, expected) for expected in cond.values)
    if op == "starts_with":
        actual = ctx.get(cond.field)
        return isinstance(actual, str) and any(
            isinstance(v, str) and actual.startswith(v) for v in cond.values
        )
    if op == "ends_with":
        actual = ctx.get(cond.field)
        return isinstance(actual, str) and any(
            isinstance(v, str) and actual.endswith(v) for v in cond.values
        )
    if op == "contains":
        actual = ctx.get(cond.field)
        if isinstance(actual, str):
            return any(isinstance(v, str) and v in actual for v in cond.values)
        if isinstance(actual, (list, tuple)):
            return any(v in actual for v in cond.values)
        return False
    if op == "matches":
        actual = ctx.get(cond.field)
        if not isinstance(actual, str):
            return False
        for pattern in cond.values:
            try:
                if re.search(pattern, actual):
                    return True
            except re.error:
                continue
        return False
    return False


def _loose_equal(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b or str(a).lower() == str(b).lower()
    if isinstance(a, (int, float)) and isinstance(b, str):
        try:
            return float(a) == float(b)
        except ValueError:
            return False
    if isinstance(a, str) and isinstance(b, (int, float)):
        try:
            return float(a) == float(b)
        except ValueError:
            return False
    return a == b


def _rule_matches(rule: TargetingRule, ctx: EvaluationContext) -> bool:
    return all(_match_condition(cond, ctx) for cond in rule.conditions)


def _select_weighted(weights: Dict[str, float], draw: float) -> str:
    """在权重表上按 0-100 的抽签值选择变体。"""
    cumulative = 0.0
    for name, weight in weights.items():
        cumulative += float(weight)
        if draw < cumulative:
            return name
    # 浮点误差兜底：返回最后一个
    return next(reversed(list(weights.keys())))


def _rule_percentage_hit(
    flag: Flag, rule: TargetingRule, ctx: EvaluationContext
) -> bool:
    if rule.percentage is None:
        return True
    key = ctx.get(rule.bucket_by, "")
    if key is None:
        key = ""
    if not isinstance(key, str):
        key = str(key)
    b = bucket(flag.key, key, total=100, salt=flag.bucket_salt + "/rule/" + rule.id)
    return b < float(rule.percentage)


def evaluate(flag: Flag, context: Any = None) -> EvaluationResult:
    """评估单个 flag。

    :param flag: :class:`~flagforge.models.Flag` 实例
    :param context: 评估上下文（dict 或 :class:`EvaluationContext`）
    :return: :class:`~flagforge.models.EvaluationResult`
    """
    if not isinstance(flag, Flag):
        raise TypeError("flag must be a Flag instance")
    ctx = (
        context
        if isinstance(context, EvaluationContext)
        else EvaluationContext.from_dict(context or {})
    )

    if flag.state == "off":
        return EvaluationResult(
            flag_key=flag.key,
            variant=flag.default_variant,
            value=flag.variants[flag.default_variant],
            reason="DISABLED",
        )

    # 1) targeting 规则
    for rule in flag.targeting:
        if _rule_matches(rule, ctx):
            if _rule_percentage_hit(flag, rule, ctx):
                return EvaluationResult(
                    flag_key=flag.key,
                    variant=rule.variant,
                    value=flag.variants[rule.variant],
                    reason="TARGETING_MATCH",
                    rule_id=rule.id,
                )
            # percentage 未命中 → 继续后续规则

    # 2) flag 级 rollout
    if flag.rollout is not None:
        key = ctx.get(flag.rollout.bucket_by, "")
        if key is None:
            key = ""
        if not isinstance(key, str):
            key = str(key)
        b = bucket(flag.key, key, total=100, salt=flag.bucket_salt)
        if b < flag.rollout.percentage:
            if flag.rollout.variants:
                variant = _select_weighted(
                    flag.rollout.variants, (b / flag.rollout.percentage) * 100.0
                    if flag.rollout.percentage > 0
                    else 0.0
                )
            else:
                variant = flag.rollout.variant
            return EvaluationResult(
                flag_key=flag.key,
                variant=variant,
                value=flag.variants[variant],
                reason="SPLIT",
            )

    # 3) 默认变体
    return EvaluationResult(
        flag_key=flag.key,
        variant=flag.default_variant,
        value=flag.variants[flag.default_variant],
        reason="DEFAULT",
    )


def evaluate_all(
    flag_set: FlagSet, context: Any = None, keys: Optional[List[str]] = None
) -> Dict[str, EvaluationResult]:
    """批量评估 flag 集合（或指定子集）。"""
    ctx = (
        context
        if isinstance(context, EvaluationContext)
        else EvaluationContext.from_dict(context or {})
    )
    results: Dict[str, EvaluationResult] = {}
    for flag in flag_set.flags:
        if keys is not None and flag.key not in keys:
            continue
        results[flag.key] = evaluate(flag, ctx)
    return results
