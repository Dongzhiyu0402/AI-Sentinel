"""埋点接口测试：白名单、批量上限、自由文本拦截、日志不含 IP。"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.api import routes  # noqa: E402
from app.core.rate_limit import SlidingWindowRateLimiter  # noqa: E402
from app.services import telemetry  # noqa: E402
from tests.asgi_client import request  # noqa: E402

CLIENT = ("203.0.113.7", 51234)
TELEMETRY_LOGGER = "compliance_sentinel.telemetry"


def post_events(events: list[dict], client: tuple[str, int] = CLIENT):
    routes.events_limiter.reset()
    return request("POST", "/api/v1/events", {"events": events}, client=client)


def test_whitelisted_events_are_accepted() -> None:
    response = post_events(
        [
            {"event": "suggestion_copied", "timestamp": "2026-10-26T07:12:55Z", "device": "mobile", "rule_id": "ad-001"},
            {"event": "error_occurred", "timestamp": "2026-10-26T07:13:02Z", "device": "mobile", "error_code": "http_429"},
        ]
    )
    assert response.status == 202
    assert response.json() == {"accepted": 2}


def test_events_outside_whitelist_are_ignored() -> None:
    response = post_events(
        [
            {"event": "check_submitted"},
            {"event": "check_result_viewed"},
            {"event": "ai_label_flagged"},
            {"event": "page_unload"},
            {"event": "suggestion_copied", "rule_id": "ad-008"},
        ]
    )
    assert response.status == 202
    assert response.json() == {"accepted": 1}


def test_batch_limit_is_twenty() -> None:
    events = [{"event": "suggestion_copied", "rule_id": "ad-001"} for _ in range(21)]
    assert post_events(events).status == 422

    events = [{"event": "suggestion_copied", "rule_id": "ad-001"} for _ in range(20)]
    assert post_events(events).status == 202


def test_empty_batch_is_rejected() -> None:
    assert post_events([]).status == 422


def test_top_level_extra_field_is_rejected() -> None:
    response = request(
        "POST",
        "/api/v1/events",
        {"events": [{"event": "error_occurred", "error_code": "network_error"}], "text": "用户原文"},
        client=CLIENT,
    )
    assert response.status == 422


def test_free_text_is_not_logged(caplog) -> None:
    caplog.set_level(logging.INFO, logger=TELEMETRY_LOGGER)
    raw_text = "本店产品为全网最低价，国家级认证"
    response = post_events(
        [
            {
                "event": "suggestion_copied",
                "rule_id": raw_text,
                "error_code": raw_text,
                "note": raw_text,
            }
        ]
    )
    assert response.status == 202
    assert response.json() == {"accepted": 1}
    logged = caplog.text
    assert raw_text not in logged
    assert "rule_id" not in logged
    assert "note" not in logged


def test_log_has_no_client_ip(caplog) -> None:
    caplog.set_level(logging.INFO, logger=TELEMETRY_LOGGER)
    post_events([{"event": "error_occurred", "error_code": "http_500"}])
    assert "203.0.113.7" not in caplog.text
    assert "http_500" in caplog.text


def test_sanitize_event_normalizes_fields() -> None:
    cleaned = telemetry.sanitize_event(
        {
            "event": "suggestion_copied",
            "timestamp": "不是时间",
            "device": "watch",
            "rule_id": "ad-001",
            "elapsed_ms": -1,
            "finding_count": True,
            "by_level": {"high": 1, "medium": 0, "low": 0},
        }
    )
    assert cleaned is not None
    assert cleaned["event"] == "suggestion_copied"
    assert cleaned["device"] == "unknown"
    assert cleaned["rule_id"] == "ad-001"
    assert cleaned["by_level"] == {"high": 1, "medium": 0, "low": 0}
    assert "elapsed_ms" not in cleaned
    assert "finding_count" not in cleaned
    assert cleaned["ts"].endswith("Z")


def test_events_rate_limit_returns_retry_after() -> None:
    original = routes.events_limiter
    routes.events_limiter = SlidingWindowRateLimiter(limit=1)
    try:
        first = post_events([{"event": "error_occurred", "error_code": "network_error"}])
        assert first.status == 202
        second = request(
            "POST",
            "/api/v1/events",
            {"events": [{"event": "error_occurred", "error_code": "network_error"}]},
            client=CLIENT,
        )
        assert second.status == 429
        assert int(second.headers["retry-after"]) > 0
        assert "本次检测额度已用完" in second.json()["detail"]
    finally:
        routes.events_limiter = original
