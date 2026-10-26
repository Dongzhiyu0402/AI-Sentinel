"""按客户端 IP 的小时级滑动窗口限流（单进程内存实现）。

约束来源 docs/ARCHITECTURE.md 第 3 节：

- 单 worker 部署，进程内计数即可，不引入 Redis；
- 桶数量必须有上限，否则被扫描器刷 IP 时内存无界增长：先清理窗口已空的桶，
  再按最久未访问顺序淘汰；
- 429 的 ``Retry-After`` 秒数与提示文案必须同源计算，不允许两处各算一遍。

时间戳由调用方或 ``time.time()`` 提供，便于测试用假时钟验证窗口边界。
"""
from __future__ import annotations

import math
import time
from collections import OrderedDict, deque
from dataclasses import dataclass

WINDOW_SECONDS = 3600
DEFAULT_MAX_BUCKETS = 5000
# 每处理这么多次请求做一次全量过期清理，避免桶都过期但仍占着内存
_SWEEP_INTERVAL = 256


@dataclass(frozen=True)
class RateLimitDecision:
    """一次配额判定的结果。文案与响应头都由它派生，保证口径一致。"""

    allowed: bool
    retry_after_seconds: int = 0

    @property
    def retry_after_minutes(self) -> int:
        """向上取整到分钟，用于"约 N 分钟后可再次检测"。"""
        return max(1, math.ceil(self.retry_after_seconds / 60))


class SlidingWindowRateLimiter:
    """每个 key（客户端 IP）保留本次窗口内的请求时间戳。"""

    def __init__(
        self,
        limit: int,
        window_seconds: int = WINDOW_SECONDS,
        max_buckets: int = DEFAULT_MAX_BUCKETS,
    ) -> None:
        if limit <= 0:
            raise ValueError("limit 必须为正整数")
        if max_buckets <= 0:
            raise ValueError("max_buckets 必须为正整数")
        self.limit = limit
        self.window_seconds = window_seconds
        self.max_buckets = max_buckets
        self._buckets: OrderedDict[str, deque[float]] = OrderedDict()
        self._hits_since_sweep = 0

    def hit(self, key: str, now: float | None = None) -> RateLimitDecision:
        current = time.time() if now is None else now
        self._hits_since_sweep += 1
        if self._hits_since_sweep >= _SWEEP_INTERVAL:
            self._hits_since_sweep = 0
            self.purge_expired(current)

        window = self._buckets.get(key)
        if window is None:
            self._make_room(current)
            window = self._buckets[key] = deque()
        else:
            self._buckets.move_to_end(key)

        self._prune(window, current)
        if len(window) >= self.limit:
            return RateLimitDecision(
                allowed=False,
                retry_after_seconds=self._retry_after(window, current),
            )
        window.append(current)
        return RateLimitDecision(allowed=True)

    def purge_expired(self, now: float | None = None) -> int:
        """删除窗口内已无请求的桶，返回删除数量。"""
        current = time.time() if now is None else now
        stale = [
            key
            for key, window in self._buckets.items()
            if not window or current - window[-1] >= self.window_seconds
        ]
        for key in stale:
            del self._buckets[key]
        return len(stale)

    def bucket_count(self) -> int:
        return len(self._buckets)

    def reset(self) -> None:
        self._buckets.clear()
        self._hits_since_sweep = 0

    def _make_room(self, now: float) -> None:
        if len(self._buckets) < self.max_buckets:
            return
        self.purge_expired(now)
        while len(self._buckets) >= self.max_buckets:
            self._buckets.popitem(last=False)

    def _prune(self, window: deque[float], now: float) -> None:
        while window and now - window[0] >= self.window_seconds:
            window.popleft()

    def _retry_after(self, window: deque[float], now: float) -> int:
        """窗口内最早一次请求滑出窗口的时刻，即最早可再次检测的时间。"""
        return max(1, math.ceil(window[0] + self.window_seconds - now))
