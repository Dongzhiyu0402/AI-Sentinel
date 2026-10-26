"""无第三方依赖的 ASGI 调用助手：直接驱动应用，拿到状态码、响应头与响应体。

requirements.txt 里没有 httpx（FastAPI 的 TestClient 依赖它），为了避免为测试引入新依赖，
这里用 asyncio 直接调用 ASGI 接口。禁用 /docs 之类的装配级行为也因此可以被真实断言。
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from app.main import app as default_app


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))


def request(
    method: str,
    path: str,
    body: Any = None,
    headers: dict[str, str] | None = None,
    client: tuple[str, int] = ("127.0.0.1", 50000),
    app: Any = None,
) -> Response:
    target_app = app if app is not None else default_app
    payload = b"" if body is None else json.dumps(body).encode("utf-8")

    raw_headers: list[tuple[bytes, bytes]] = []
    if body is not None:
        raw_headers.append((b"content-type", b"application/json"))
    for key, value in (headers or {}).items():
        raw_headers.append((key.lower().encode("latin-1"), value.encode("latin-1")))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "root_path": "",
        "headers": raw_headers,
        "client": client,
        "server": ("testserver", 80),
    }

    messages: list[dict[str, Any]] = []
    delivered = False

    async def receive() -> dict[str, Any]:
        nonlocal delivered
        if not delivered:
            delivered = True
            return {"type": "http.request", "body": payload, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    try:
        asyncio.run(target_app(scope, receive, send))
    except Exception:
        # 未处理异常由全局处理器转换成 500 响应后仍会向上抛出，响应已写入 messages
        if not messages:
            raise

    start = next(item for item in messages if item["type"] == "http.response.start")
    body_bytes = b"".join(
        item.get("body", b"") for item in messages if item["type"] == "http.response.body"
    )
    header_map = {key.decode("latin-1").lower(): value.decode("latin-1") for key, value in start["headers"]}
    return Response(status=start["status"], headers=header_map, body=body_bytes)
