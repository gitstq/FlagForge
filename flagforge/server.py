"""server — 本地 HTTP 评估 API（基于标准库 http.server）。

提供轻量 REST 接口，便于：

* 前端 / 脚本在不引入 SDK 的情况下查询开关状态
* CI / 本地联调时实时评估
* 作为示例展示如何把 FlagForge 嵌入现有服务

端点：

* ``GET  /health``                  健康检查
* ``GET  /flags``                   全量 flag 定义
* ``GET  /flags/{key}``             单个 flag 定义
* ``POST /evaluate``                评估（body: ``{"key": "...", "context": {...}}``）
* ``GET  /evaluate?flag=x&a=1&b=2`` 评估（query 形式，context 值均为字符串）

默认仅监听 ``127.0.0.1``——请勿在未加防护的情况下暴露到公网。
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

from .engine import evaluate, evaluate_all
from .loader import load_flags
from .models import FlagSet

__all__ = ["create_server", "serve"]


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def create_server(
    flag_set: FlagSet,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> ThreadingHTTPServer:
    """创建（但不启动）HTTP 服务器实例。"""

    class Handler(BaseHTTPRequestHandler):
        server_version = "FlagForge/1.0"
        protocol_version = "HTTP/1.1"

        # ----------------------------------------------------------#
        def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
            # 静默默认日志，由调用方决定是否输出
            pass

        def _send_json(self, status: int, payload: Any) -> None:
            body = _json_bytes(payload)
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _not_found(self, message: str = "not found") -> None:
            self._send_json(404, {"error": message})

        def _bad_request(self, message: str) -> None:
            self._send_json(400, {"error": message})

        # ----------------------------------------------------------#
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = unquote(parsed.path).rstrip("/") or "/"
            if path == "/health":
                self._send_json(200, {"status": "ok", "flags": len(flag_set.flags)})
                return
            if path == "/flags":
                self._send_json(200, {"flags": [f.to_dict() for f in flag_set.flags]})
                return
            if path.startswith("/flags/"):
                key = path[len("/flags/") :]
                flag = flag_set.get(key)
                if flag is None:
                    self._not_found("flag '%s' not found" % key)
                    return
                self._send_json(200, flag.to_dict())
                return
            if path == "/evaluate":
                params = parse_qs(parsed.query)
                key = (params.get("flag") or [""])[0]
                if not key:
                    self._bad_request("missing 'flag' query parameter")
                    return
                flag = flag_set.get(key)
                if flag is None:
                    self._not_found("flag '%s' not found" % key)
                    return
                context = {k: v[0] for k, v in params.items() if k != "flag"}
                self._send_json(200, evaluate(flag, context).to_dict())
                return
            self._not_found()

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = unquote(parsed.path).rstrip("/") or "/"
            if path != "/evaluate":
                self._not_found()
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._bad_request("invalid Content-Length")
                return
            raw = self.rfile.read(length) if length else b""
            try:
                payload = json.loads(raw.decode("utf-8")) if raw else {}
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._bad_request("body must be valid JSON")
                return
            if not isinstance(payload, dict):
                self._bad_request("body must be a JSON object")
                return
            key = payload.get("key") or payload.get("flag")
            if not key:
                self._bad_request("missing 'key' field")
                return
            flag = flag_set.get(key)
            if flag is None:
                self._not_found("flag '%s' not found" % key)
                return
            context = payload.get("context") or {}
            if not isinstance(context, dict):
                self._bad_request("'context' must be an object")
                return
            self._send_json(200, evaluate(flag, context).to_dict())

    return ThreadingHTTPServer((host, port), Handler)


def serve(
    flag_set: FlagSet,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> None:
    """启动阻塞式 HTTP 服务（Ctrl+C 退出）。"""
    server = create_server(flag_set, host=host, port=port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
