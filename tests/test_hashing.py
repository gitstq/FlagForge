"""hashing / bucketing 测试。"""

from __future__ import annotations

import unittest

from flagforge.hashing import bucket, bucket_distribution, murmur3_32


class TestMurmur3(unittest.TestCase):
    def test_empty_input_is_zero(self):
        self.assertEqual(murmur3_32(b""), 0)

    def test_returns_32bit(self):
        for data in (b"a", b"hello world", b"\x00" * 33, bytes(range(256))):
            value = murmur3_32(data)
            self.assertGreaterEqual(value, 0)
            self.assertLessEqual(value, 0xFFFFFFFF)

    def test_deterministic(self):
        data = b"flagforge"
        self.assertEqual(murmur3_32(data), murmur3_32(data))

    def test_seed_changes_output(self):
        self.assertNotEqual(murmur3_32(b"abc", seed=0), murmur3_32(b"abc", seed=1))

    def test_avalanche_single_bit(self):
        a = murmur3_32(b"user-1000")
        b = murmur3_32(b"user-1001")
        diff = bin(a ^ b).count("1")
        self.assertGreater(diff, 8)


class TestBucket(unittest.TestCase):
    def test_range(self):
        for i in range(200):
            b = bucket("flag-a", "user-%d" % i, total=100)
            self.assertTrue(0 <= b < 100)

    def test_deterministic(self):
        self.assertEqual(bucket("f", "u"), bucket("f", "u"))
        self.assertEqual(bucket("f", "u", salt="s1"), bucket("f", "u", salt="s1"))

    def test_flag_independence(self):
        # 同一用户在不同 flag 下应落在不同桶（高概率）
        buckets = {bucket("flag-%d" % i, "user-1") for i in range(20)}
        self.assertGreater(len(buckets), 5)

    def test_salt_reshuffles(self):
        base = bucket("f", "u")
        salted = bucket("f", "u", salt="pepper")
        self.assertNotEqual(base, salted)

    def test_percentage_monotonic_semantics(self):
        # 对任意 key，bucket < p 即代表落入 p% 灰度区间；500 个 key 下
        # 30% / 40% 的命中数应分别约为 150 / 200（含统计容差）
        keys = ["user-%d" % i for i in range(500)]
        hit_30 = {k for k in keys if bucket("f", k) < 30}
        hit_40 = {k for k in keys if bucket("f", k) < 40}
        self.assertTrue(hit_30.issubset(hit_40))
        self.assertTrue(120 <= len(hit_30) <= 180)
        self.assertTrue(170 <= len(hit_40) <= 230)

    def test_distribution_roughly_uniform(self):
        keys = ["user-%d" % i for i in range(10000)]
        dist = dict(bucket_distribution("f", keys, total=100))
        self.assertEqual(len(dist), 100)  # 所有桶均被覆盖
        for count in dist.values():
            self.assertTrue(60 <= count <= 140, "bucket count %d out of range" % count)

    def test_total_validation(self):
        with self.assertRaises(ValueError):
            bucket("f", "u", total=0)

    def test_type_validation(self):
        with self.assertRaises(TypeError):
            bucket("f", 42)


if __name__ == "__main__":
    unittest.main()
