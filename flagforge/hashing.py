"""hashing — 确定性分桶（bucketing）工具。

FlagForge 的百分比灰度依赖“同一个用户始终落在同一个桶”的确定性哈希。
本模块实现了业界广泛使用的 MurmurHash3（x86_32 变体）与基于它的
分桶函数，保证：

* 纯函数：相同输入永远得到相同输出（跨进程、跨平台、跨版本稳定）
* 均匀分布：murmur3_32 的雪崩效应保证分桶近似均匀
* 无外部依赖：仅使用 Python 标准库

分桶函数使用 ``flag_key`` 与 ``bucket_key`` 的组合作为输入，因此：
* 不同 flag 的同一用户会被独立分桶（调整一个 flag 的百分比不影响其他 flag）
* 调整 flag 的 salt（``bucket_salt``）可以整体重新洗牌流量
"""

from __future__ import annotations

from typing import Iterable, List, Tuple

__all__ = ["bucket", "bucket_distribution", "murmur3_32"]

_MASK32 = 0xFFFFFFFF


def murmur3_32(data: bytes, seed: int = 0) -> int:
    """计算 MurmurHash3 x86_32。

    :param data: 输入字节串
    :param seed: 种子（32 位无符号整数）
    :return: 32 位无符号整数哈希值
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("data must be bytes")
    length = len(data)
    h = seed & _MASK32
    c1 = 0xCC9E2D51
    c2 = 0x1B873593

    nblocks = length // 4
    for i in range(nblocks):
        k = int.from_bytes(data[i * 4 : i * 4 + 4], "little")
        k = (k * c1) & _MASK32
        k = ((k << 15) | (k >> 17)) & _MASK32
        k = (k * c2) & _MASK32

        h ^= k
        h = ((h << 13) | (h >> 19)) & _MASK32
        h = (h * 5 + 0xE6546B64) & _MASK32

    tail = data[nblocks * 4 :]
    k = 0
    if len(tail) >= 3:
        k ^= tail[2] << 16
    if len(tail) >= 2:
        k ^= tail[1] << 8
    if len(tail) >= 1:
        k ^= tail[0]
        k = (k * c1) & _MASK32
        k = ((k << 15) | (k >> 17)) & _MASK32
        k = (k * c2) & _MASK32
        h ^= k

    h ^= length
    h ^= h >> 16
    h = (h * 0x85EBCA6B) & _MASK32
    h ^= h >> 13
    h = (h * 0xC2B2AE35) & _MASK32
    h ^= h >> 16
    return h


def bucket(
    flag_key: str,
    bucket_key: str,
    total: int = 100,
    salt: str = "",
) -> int:
    """计算 ``bucket_key`` 在指定 flag 下的分桶编号。

    :param flag_key: flag 标识（参与哈希，保证 flag 间相互独立）
    :param bucket_key: 分桶键（通常为 targetingKey / 用户 ID）
    :param total: 桶总数（默认 100，即百分比）
    :param salt: 额外盐值（flag 的 ``bucket_salt``，用于整体重新洗牌）
    :return: ``[0, total)`` 区间内的整数桶编号
    """
    if total <= 0:
        raise ValueError("total must be a positive integer")
    if not isinstance(flag_key, str) or not isinstance(bucket_key, str):
        raise TypeError("flag_key and bucket_key must be strings")
    # 使用 \x1f（unit separator）拼接，避免不同 (flag, key) 组合产生歧义
    material = "%s%s\x1f%s" % (salt, flag_key, bucket_key)
    digest = murmur3_32(material.encode("utf-8"))
    return digest % total


def bucket_distribution(
    flag_key: str,
    keys: Iterable[str],
    total: int = 100,
    salt: str = "",
) -> List[Tuple[int, int]]:
    """统计一组分桶键在各桶的分布（调试/测试辅助）。

    :return: 按桶编号升序排列的 ``(bucket_id, count)`` 列表，仅包含非空桶
    """
    counts = {}
    for key in keys:
        b = bucket(flag_key, key, total=total, salt=salt)
        counts[b] = counts.get(b, 0) + 1
    return sorted(counts.items())
