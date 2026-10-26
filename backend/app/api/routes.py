"""路由层：HTTP 入口、参数校验、限流与日志装配。业务逻辑下沉到 services。"""
from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Request

from app.core import config as cfg
from app.core.rate_limit import SlidingWindowRateLimiter
from app.schemas.events import EventAck, EventBatch
from app.schemas.models import (
    CheckRequest,
    CheckResponse,
    CheckSummary,
    RuleMeta,
)
from app.services import llm_service, telemetry
from app.services.rule_engine import RuleEngine

router = APIRouter(prefix="/api/v1")

engine = RuleEngine(cfg.RULES_PATH)
check_limiter = SlidingWindowRateLimiter(
    cfg.RATE_LIMIT_PER_HOUR,
    max_buckets=cfg.RATE_LIMIT_MAX_BUCKETS,
)
events_limiter = SlidingWindowRateLimiter(
    cfg.EVENTS_RATE_LIMIT_PER_HOUR,
    max_buckets=cfg.RATE_LIMIT_MAX_BUCKETS,
)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _guard(limiter: SlidingWindowRateLimiter, request: Request) -> None:
    """配额校验。Retry-After 秒数与提示文案由同一份判定结果派生，不会互相矛盾。"""
    decision = limiter.hit(_client_ip(request))
    if decision.allowed:
        return
    raise HTTPException(
        status_code=429,
        detail=cfg.RATE_LIMIT_MESSAGE_TEMPLATE.format(minutes=decision.retry_after_minutes),
        headers={"Retry-After": str(decision.retry_after_seconds)},
    )


@router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "version": cfg.APP_VERSION}


@router.get("/meta", response_model=RuleMeta, tags=["system"])
def meta() -> RuleMeta:
    categories: dict[str, int] = {}
    for rule in engine.rules:
        categories[rule.category] = categories.get(rule.category, 0) + 1
    return RuleMeta(
        total_rules=len(engine.rules),
        categories=categories,
        version=engine.version,
        updated_at=engine.updated_at,
    )


@router.post("/check", response_model=CheckResponse, tags=["check"])
def check(payload: CheckRequest, request: Request) -> CheckResponse:
    _guard(check_limiter, request)

    started = time.perf_counter()
    findings, ai_label = engine.check(payload.text, payload.has_ai_content)
    findings = llm_service.enhance(findings)
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    telemetry.log_check(
        findings=findings,
        text_length=len(payload.text),
        elapsed_ms=elapsed_ms,
        client_ip=_client_ip(request),
        user_agent=request.headers.get("user-agent", ""),
    )

    summary = CheckSummary(
        high=sum(1 for item in findings if item.level == "high"),
        medium=sum(1 for item in findings if item.level == "medium"),
        low=sum(1 for item in findings if item.level == "low"),
        total=len(findings),
        elapsed_ms=elapsed_ms,
    )
    return CheckResponse(
        summary=summary,
        findings=findings,
        ai_label=ai_label,
        disclaimer=cfg.DISCLAIMER,
    )


@router.post("/events", response_model=EventAck, status_code=202, tags=["telemetry"])
def create_events(payload: EventBatch, request: Request) -> EventAck:
    """前端埋点：白名单事件才写日志，其余忽略；不落库、不接收自由文本。"""
    _guard(events_limiter, request)
    return EventAck(accepted=telemetry.log_frontend_events(payload.events))
