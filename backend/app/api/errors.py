"""全局异常处理：对外统一中文文案，堆栈只写服务端日志。

契约见 docs/SPEC.md 第 5 节与 docs/openapi.yaml 的 InternalError：
- 500 只返回 ``{"detail": "服务暂时不可用，请稍后重试"}``；
- 请求路径与方法可进日志，请求体（可能含用户原文）一律不打印。
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core import config as cfg

logger = logging.getLogger(__name__)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "未处理异常：%s %s：%s", request.method, request.url.path, type(exc).__name__
    )
    return JSONResponse(status_code=500, content={"detail": cfg.INTERNAL_ERROR_MESSAGE})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(Exception, unhandled_exception_handler)
