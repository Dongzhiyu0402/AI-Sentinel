"""埋点上报的请求与响应模型。

事件条目按白名单字段逐个清洗（见 services/telemetry.py），因此这里只做结构校验：
- ``events`` 必须是 1–20 条的数组，超出范围由 FastAPI 返回 422；
- 条目内部字段不做强类型校验，白名单外的事件与字段被忽略而不整批失败，
  避免历史页面版本的字段变动导致埋点整批丢弃。
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EventBatch(BaseModel):
    """批量埋点请求体。顶层禁止额外字段，防止借埋点通道夹带用户原文。"""

    model_config = ConfigDict(extra="forbid")

    events: list[dict[str, Any]] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="事件数组，单批 1–20 条",
    )


class EventAck(BaseModel):
    accepted: int = Field(..., ge=0, description="实际写入日志的事件条数")
