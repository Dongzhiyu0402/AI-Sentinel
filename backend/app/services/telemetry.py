"""结构化埋点与检测日志：只写日志，不落库、不接收自由文本、不含原文与明文 IP。

字段口径见 docs/ARCHITECTURE.md 第 5.1 节：

- 服务端事件 ``check_submitted``：``/check`` 成功时输出一行 JSON，含 ``rule_hits``
  （rule_id → 命中次数），供规则运营按规则聚合命中频次；
- 前端事件：仅接受 ``suggestion_copied`` / ``error_occurred`` 两个白名单事件，
  其余事件名静默忽略（不落日志、不计入 accepted）。

安全边界：字段白名单逐项清洗，任何自由文本（含超长字符串、嵌套结构）都不进日志；
IP 只保留不可逆的 12 位哈希，前端事件不记录任何 IP 信息。
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from app.core import config as cfg
from app.schemas.models import Finding

logger = logging.getLogger("compliance_sentinel.telemetry")

# 前端埋点白名单：只有这两个事件名会写日志
EVENT_WHITELIST = frozenset({"suggestion_copied", "error_occurred"})
DEVICE_VALUES = frozenset({"desktop", "mobile", "tablet", "unknown"})
RULE_HIT_KEY_LIMIT = 100

# 标识符类字段只允许短 ASCII，杜绝把用户文案塞进 rule_id / error_code
_RULE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_ERROR_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_LEVEL_KEYS = ("high", "medium", "low")


def device_from_user_agent(user_agent: str) -> str:
    """按 UA 粗分设备类型，判断不出时归为 unknown。"""
    ua = (user_agent or "").lower()
    if not ua:
        return "unknown"
    if any(token in ua for token in ("ipad", "tablet", "kindle")):
        return "tablet"
    if any(token in ua for token in ("mobile", "iphone", "android", "phone")):
        return "mobile"
    if any(token in ua for token in ("windows", "macintosh", "linux", "x11")):
        return "desktop"
    return "unknown"


def hash_ip(client_ip: str) -> str:
    """IP 的 12 位哈希，用于去重与滥用排查，不可逆推原始地址。"""
    if not client_ip:
        return ""
    return hashlib.sha256(client_ip.encode("utf-8")).hexdigest()[:12]


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _count_rule_hits(findings: list[Finding]) -> dict[str, int]:
    counter = Counter(item.rule_id for item in findings)
    ordered = sorted(counter.items(), key=lambda pair: (-pair[1], pair[0]))
    return dict(ordered[:RULE_HIT_KEY_LIMIT])


def log_check(
    *,
    findings: list[Finding],
    text_length: int,
    elapsed_ms: int,
    client_ip: str,
    user_agent: str,
) -> None:
    """输出一行 check_submitted 日志。不接收、不打印任何原文片段。"""
    by_level = {level: sum(1 for item in findings if item.level == level) for level in _LEVEL_KEYS}
    logger.info(
        "%s",
        json.dumps(
            {
                "event": "check_submitted",
                "ts": _now_iso(),
                "device": device_from_user_agent(user_agent),
                "text_len": text_length,
                "elapsed_ms": elapsed_ms,
                "finding_count": len(findings),
                "by_level": by_level,
                "rule_hits": _count_rule_hits(findings),
                "llm": "on" if cfg.LLM_ENABLED else "off",
                "ip_hash": hash_ip(client_ip),
            },
            ensure_ascii=False,
        ),
    )


def _clean_int(raw: Any, upper_bound: int) -> int | None:
    if isinstance(raw, bool) or not isinstance(raw, int):
        return None
    if raw < 0 or raw > upper_bound:
        return None
    return raw


def _clean_timestamp(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    candidate = raw.strip()
    if not candidate:
        return None
    try:
        datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        return None
    return candidate


def _clean_level_breakdown(raw: Any) -> dict[str, int] | None:
    if not isinstance(raw, dict):
        return None
    cleaned: dict[str, int] = {}
    for level in _LEVEL_KEYS:
        value = _clean_int(raw.get(level, 0), 100000)
        if value is None:
            return None
        cleaned[level] = value
    return cleaned


def sanitize_event(raw: Any) -> dict[str, Any] | None:
    """把一条上报事件清洗成固定字段；事件名不在白名单或结构不对时返回 None。"""
    if not isinstance(raw, dict):
        return None

    name = raw.get("event")
    if not isinstance(name, str) or name not in EVENT_WHITELIST:
        return None

    cleaned: dict[str, Any] = {"event": name, "ts": _clean_timestamp(raw.get("timestamp")) or _now_iso()}

    device = raw.get("device")
    cleaned["device"] = device if isinstance(device, str) and device in DEVICE_VALUES else "unknown"

    elapsed_ms = _clean_int(raw.get("elapsed_ms"), 600000)
    if elapsed_ms is not None:
        cleaned["elapsed_ms"] = elapsed_ms

    finding_count = _clean_int(raw.get("finding_count"), 100000)
    if finding_count is not None:
        cleaned["finding_count"] = finding_count

    by_level = _clean_level_breakdown(raw.get("by_level"))
    if by_level is not None:
        cleaned["by_level"] = by_level

    rule_id = raw.get("rule_id")
    if isinstance(rule_id, str) and _RULE_ID_PATTERN.match(rule_id):
        cleaned["rule_id"] = rule_id

    error_code = raw.get("error_code")
    if isinstance(error_code, str) and _ERROR_CODE_PATTERN.match(error_code):
        cleaned["error_code"] = error_code

    return cleaned


def log_frontend_events(events: list[Any]) -> int:
    """逐条清洗并写日志，返回实际写入的条数。"""
    accepted = 0
    for raw in events:
        cleaned = sanitize_event(raw)
        if cleaned is None:
            continue
        logger.info("frontend_event %s", json.dumps(cleaned, ensure_ascii=False))
        accepted += 1
    return accepted
