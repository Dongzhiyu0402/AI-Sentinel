"""检测接口测试：排序契约、建议来源、429 语义、500 文案与生产环境文档关闭。"""
from __future__ import annotations

import json
import logging
import math
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.api import routes  # noqa: E402
from app.core import config as cfg  # noqa: E402
from app.core.rate_limit import SlidingWindowRateLimiter  # noqa: E402
from app.main import create_app  # noqa: E402
from app.schemas.models import Finding  # noqa: E402
from app.services import llm_service  # noqa: E402
from app.services.rule_engine import RuleEngine  # noqa: E402
from tests.asgi_client import request  # noqa: E402

CHECK_URL = "/api/v1/check"
SORT_RULES = """
version: "test"
updated_at: "2026-10-26"
rules:
  - id: zz-002
    category: 通用表达
    level: high
    pattern: 绝对化
    basis: 测试依据
    suggestion: 建议一
  - id: aa-001
    category: 通用表达
    level: high
    pattern: 绝对化用语
    basis: 测试依据
    suggestion: 建议二
  - id: yy-003
    category: 通用表达
    level: high
    pattern: 用语
    basis: 测试依据
    suggestion: 建议三
  - id: mm-001
    category: 通用表达
    level: low
    pattern: 普通
    basis: 测试依据
    suggestion: 建议四
"""


def post_check(text: str, has_ai_content: bool = False, client: tuple[str, int] = ("198.51.100.9", 40000)):
    routes.check_limiter.reset()
    return request("POST", CHECK_URL, {"text": text, "has_ai_content": has_ai_content}, client=client)


def test_findings_sorted_by_level_then_start_then_rule_id(tmp_path: Path) -> None:
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(SORT_RULES, encoding="utf-8")
    engine = RuleEngine(rules_file)

    findings, _ = engine.check("普通绝对化用语", has_ai_content=False)
    assert [item.rule_id for item in findings] == ["aa-001", "zz-002", "yy-003", "mm-001"]
    # 低风险命中位置更靠前，也必须排在全部高风险之后
    assert findings[-1].start == 0


def test_check_response_matches_contract() -> None:
    response = post_check("本店产品为全网最低价，国家级认证。")
    assert response.status == 200
    body = response.json()
    summary = body["summary"]
    assert summary["total"] == summary["high"] + summary["medium"] + summary["low"]
    assert summary["total"] == len(body["findings"])
    assert body["disclaimer"].startswith("本工具仅提供内容风险自查参考")

    first = body["findings"][0]
    assert first["rule_id"] == "ad-008"
    assert body["findings"][0]["start"] <= body["findings"][1]["start"]
    for item in body["findings"]:
        assert item["suggestion_source"] == "rule"
        assert isinstance(item["matched"], str)


def test_positions_slice_original_text() -> None:
    text = "本店产品为全网最低价，国家级认证。"
    body = post_check(text).json()
    for item in body["findings"]:
        assert text[item["start"]:item["end"]] == item["matched"]


def test_suggestion_source_defaults_to_rule() -> None:
    finding = Finding(
        rule_id="ad-001",
        category="广告法",
        level="high",
        matched="国家级",
        start=0,
        end=3,
        basis="《广告法》第九条第（三）项",
        suggestion="删除“国家级”",
    )
    assert finding.suggestion_source == "rule"


def test_llm_suggestion_marks_source(monkeypatch) -> None:
    monkeypatch.setattr(llm_service.cfg, "LLM_ENABLED", True)
    monkeypatch.setattr(llm_service, "_request_suggestions", lambda targets: {"ad-001": "改为具体资质说明"})

    findings = [
        Finding(
            rule_id="ad-001",
            category="广告法",
            level="high",
            matched="国家级",
            start=0,
            end=3,
            basis="《广告法》第九条第（三）项",
            suggestion="删除“国家级”",
        ),
        Finding(
            rule_id="gen-001",
            category="通用表达",
            level="low",
            matched="震惊",
            start=10,
            end=12,
            basis="平台内容质量规范",
            suggestion="改为具体表述",
        ),
    ]
    updated = llm_service.enhance(findings)
    assert updated[0].suggestion == "改为具体资质说明"
    assert updated[0].suggestion_source == "llm"
    assert updated[1].suggestion_source == "rule"


def test_llm_failure_keeps_rule_source(monkeypatch) -> None:
    monkeypatch.setattr(llm_service.cfg, "LLM_ENABLED", True)

    def boom(targets):
        raise TimeoutError("模型超时")

    monkeypatch.setattr(llm_service, "_request_suggestions", boom)
    finding = Finding(
        rule_id="ad-001",
        category="广告法",
        level="high",
        matched="国家级",
        start=0,
        end=3,
        basis="《广告法》第九条第（三）项",
        suggestion="删除“国家级”",
    )
    updated = llm_service.enhance([finding])
    assert updated[0].suggestion_source == "rule"


def test_rate_limit_returns_retry_after_and_matching_message(monkeypatch) -> None:
    monkeypatch.setattr(routes, "check_limiter", SlidingWindowRateLimiter(limit=1))
    assert post_check("普通文案。").status == 200
    blocked = request(
        "POST", CHECK_URL, {"text": "普通文案。"}, client=("198.51.100.9", 40000)
    )
    assert blocked.status == 429

    retry_after = int(blocked.headers["retry-after"])
    detail = blocked.json()["detail"]
    assert retry_after >= 1
    assert detail == f"本次检测额度已用完，约 {math.ceil(retry_after / 60)} 分钟后可再次检测"


def test_rate_limit_headers_and_detail_share_one_calculation() -> None:
    limiter = SlidingWindowRateLimiter(limit=1)
    limiter.hit("198.51.100.9", now=1_700_000_000)
    decision = limiter.hit("198.51.100.9", now=1_700_000_060)
    assert decision.retry_after_seconds == 3540
    assert decision.retry_after_minutes == 59


def test_validation_errors_are_422() -> None:
    assert post_check("").status == 422
    assert post_check("字" * 20001).status == 422


def test_unhandled_error_returns_chinese_message(monkeypatch) -> None:
    def boom(text, has_ai_content):
        raise RuntimeError("内部堆栈不应出现在响应里")

    monkeypatch.setattr(routes.engine, "check", boom)
    response = post_check("普通文案。")
    assert response.status == 500
    assert response.json() == {"detail": cfg.INTERNAL_ERROR_MESSAGE}
    assert "Traceback" not in response.body.decode("utf-8")
    assert "RuntimeError" not in response.body.decode("utf-8")


def test_check_log_contains_rule_hits_without_text(caplog) -> None:
    caplog.set_level(logging.INFO, logger="compliance_sentinel.telemetry")
    text = "本店产品为全网最低价，国家级认证。"
    post_check(text)
    lines = [record.getMessage() for record in caplog.records if "check_submitted" in record.getMessage()]
    assert lines
    payload = json.loads(lines[-1])
    assert payload["event"] == "check_submitted"
    assert payload["rule_hits"] == {"ad-001": 1, "ad-008": 1}
    assert payload["text_len"] == len(text)
    assert payload["by_level"] == {"high": 2, "medium": 0, "low": 0}
    assert payload["llm"] == "off"
    assert len(payload["ip_hash"]) == 12
    assert text not in caplog.text
    assert "国家级" not in caplog.text


def test_prod_disables_api_docs(monkeypatch) -> None:
    monkeypatch.setattr(cfg, "IS_PROD", True)
    prod_app = create_app()
    assert request("GET", "/openapi.json", app=prod_app).status == 404
    assert request("GET", "/docs", app=prod_app).status == 404


def test_dev_exposes_api_docs() -> None:
    dev_app = create_app()
    assert request("GET", "/openapi.json", app=dev_app).status == 200
    assert request("GET", "/docs", app=dev_app).status == 200


def test_cors_origin_whitelist(monkeypatch) -> None:
    monkeypatch.setattr(cfg, "CORS_ALLOW_ORIGINS", ["https://sentinel.example.com"])
    app = create_app()
    allowed = request("GET", "/api/v1/health", headers={"Origin": "https://sentinel.example.com"}, app=app)
    assert allowed.headers.get("access-control-allow-origin") == "https://sentinel.example.com"
    denied = request("GET", "/api/v1/health", headers={"Origin": "https://evil.example.com"}, app=app)
    assert "access-control-allow-origin" not in denied.headers
