"""限流桶单元测试：窗口判定、Retry-After 口径、容量上限与过期清理。"""
from __future__ import annotations

import math
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.rate_limit import SlidingWindowRateLimiter  # noqa: E402

BASE_TIME = 1_700_000_000.0


def test_allows_up_to_limit_then_blocks() -> None:
    limiter = SlidingWindowRateLimiter(limit=3)
    assert all(limiter.hit("1.1.1.1", now=BASE_TIME + offset).allowed for offset in range(3))
    blocked = limiter.hit("1.1.1.1", now=BASE_TIME + 3)
    assert blocked.allowed is False
    assert blocked.retry_after_seconds == 3600 - 3


def test_quota_is_per_key() -> None:
    limiter = SlidingWindowRateLimiter(limit=1)
    assert limiter.hit("1.1.1.1", now=BASE_TIME).allowed is True
    assert limiter.hit("2.2.2.2", now=BASE_TIME).allowed is True
    assert limiter.hit("1.1.1.1", now=BASE_TIME + 1).allowed is False


def test_retry_after_matches_message_minutes() -> None:
    limiter = SlidingWindowRateLimiter(limit=1)
    limiter.hit("1.1.1.1", now=BASE_TIME)
    decision = limiter.hit("1.1.1.1", now=BASE_TIME + 1219)
    assert decision.retry_after_seconds == 3600 - 1219
    assert decision.retry_after_minutes == math.ceil(decision.retry_after_seconds / 60)
    assert decision.retry_after_minutes == 40


def test_window_slides_after_expiry() -> None:
    limiter = SlidingWindowRateLimiter(limit=1)
    limiter.hit("1.1.1.1", now=BASE_TIME)
    assert limiter.hit("1.1.1.1", now=BASE_TIME + 3599).allowed is False
    assert limiter.hit("1.1.1.1", now=BASE_TIME + 3600).allowed is True


def test_bucket_count_is_capped() -> None:
    limiter = SlidingWindowRateLimiter(limit=5, max_buckets=10)
    for index in range(200):
        limiter.hit(f"10.0.0.{index}", now=BASE_TIME + index)
    assert limiter.bucket_count() <= 10


def test_expired_buckets_are_purged() -> None:
    limiter = SlidingWindowRateLimiter(limit=5, max_buckets=10)
    for index in range(10):
        limiter.hit(f"10.0.0.{index}", now=BASE_TIME)
    assert limiter.bucket_count() == 10
    assert limiter.purge_expired(BASE_TIME + 3601) == 10
    assert limiter.bucket_count() == 0


def test_eviction_prefers_expired_buckets() -> None:
    limiter = SlidingWindowRateLimiter(limit=2, max_buckets=2)
    limiter.hit("old", now=BASE_TIME)
    limiter.hit("fresh", now=BASE_TIME + 3700)
    limiter.hit("newcomer", now=BASE_TIME + 3701)
    assert limiter.bucket_count() == 2
    # 只剩一个活跃桶加一个新建桶，过期桶已被清理而不是顶掉活跃用户
    assert limiter.hit("fresh", now=BASE_TIME + 3702).allowed is True
