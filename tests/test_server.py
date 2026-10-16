"""server HTTP API 测试（真实发起本地请求）。"""

from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request

from flagforge.loader import load_flags_from_string
from flagforge.server import create_server

FLAGS = """\
flags:
  - key: demo
    description: 演示开关
    state: on
    variant_type: boolean
    variants:
      on: true
      off: false
    default_variant: off
    rollout:
      percentage: 100
      variant: on
  - key: targeted
    description: 定向开关
    state: on
    variant_type: boolean
    variants:
      on: true
      off: false
    default_variant: off
    targeting:
      - id: staff
        conditions:
          - field: email
            op: ends_with
            values: ["@example.com"]
        variant: on
"""


class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.flag_set = load_flags_from_string(FLAGS)
        cls.server = create_server(cls.flag_set, host="127.0.0.1", port=0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def _get(self, path):
        url = "http://127.0.0.1:%d%s" % (self.port, path)
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))

    def _post(self, path, payload):
        url = "http://127.0.0.1:%d%s" % (self.port, path)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))

    def test_health(self):
        status, body = self._get("/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["flags"], 2)

    def test_list_flags(self):
        status, body = self._get("/flags")
        self.assertEqual(status, 200)
        self.assertEqual(len(body["flags"]), 2)

    def test_get_single_flag(self):
        status, body = self._get("/flags/demo")
        self.assertEqual(status, 200)
        self.assertEqual(body["key"], "demo")

    def test_get_missing_flag(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/flags/nope")
        self.assertEqual(ctx.exception.code, 404)

    def test_post_evaluate(self):
        status, body = self._post(
            "/evaluate", {"key": "demo", "context": {"targetingKey": "u1"}}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["variant"], "on")
        self.assertEqual(body["reason"], "SPLIT")

    def test_post_evaluate_targeting(self):
        status, body = self._post(
            "/evaluate",
            {"key": "targeted", "context": {"email": "dev@example.com"}},
        )
        self.assertEqual(body["reason"], "TARGETING_MATCH")
        status, body = self._post(
            "/evaluate", {"key": "targeted", "context": {"email": "x@other.com"}}
        )
        self.assertEqual(body["reason"], "DEFAULT")

    def test_get_evaluate_query(self):
        status, body = self._get("/evaluate?flag=demo&targetingKey=u1")
        self.assertEqual(status, 200)
        self.assertEqual(body["variant"], "on")

    def test_get_evaluate_missing_param(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/evaluate")
        self.assertEqual(ctx.exception.code, 400)

    def test_post_evaluate_bad_json(self):
        url = "http://127.0.0.1:%d/evaluate" % self.port
        req = urllib.request.Request(url, data=b"not json", method="POST")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=10)
        self.assertEqual(ctx.exception.code, 400)

    def test_unknown_route(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/nope")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
