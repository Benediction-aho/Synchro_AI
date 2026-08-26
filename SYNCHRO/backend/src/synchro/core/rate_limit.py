import threading
import time
from collections import deque

from fastapi import HTTPException, status


class SlidingWindowLimiter:
    def __init__(self):
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, max_events: int, window_seconds: float) -> float:
        now = time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] > window_seconds:
                hits.popleft()
            if len(hits) >= max_events:
                retry_after = window_seconds - (now - hits[0])
                return max(retry_after, 0.05)
            hits.append(now)
            return 0.0


def enforce(
    limiter: SlidingWindowLimiter,
    key: str,
    max_events: int,
    window_seconds: float,
) -> None:
    retry_after = limiter.check(key, max_events, window_seconds)
    if retry_after > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests; slow down",
            headers={"Retry-After": str(int(retry_after) + 1)},
        )
