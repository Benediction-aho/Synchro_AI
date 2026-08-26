import threading
import time

from fastapi import HTTPException, status


class LoginGuard:
    def __init__(
        self,
        max_failures: int = 3,
        base_lock_seconds: int = 30,
        max_lock_seconds: int = 900,
    ):
        self.max_failures = max_failures
        self.base_lock_seconds = base_lock_seconds
        self.max_lock_seconds = max_lock_seconds
        self._failures: dict[str, tuple[int, float | None]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        with self._lock:
            entry = self._failures.get(key)
            if entry is None:
                return
            _, locked_until = entry
            if locked_until is not None:
                remaining = locked_until - time.monotonic()
                if remaining > 0:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Account temporarily locked due to failed attempts",
                        headers={"Retry-After": str(int(remaining) + 1)},
                    )

    def record_failure(self, key: str) -> None:
        with self._lock:
            count, _ = self._failures.get(key, (0, None))
            count += 1
            locked_until = None
            if count >= self.max_failures:
                exponent = count - self.max_failures
                delay = min(
                    self.base_lock_seconds * (2**exponent),
                    self.max_lock_seconds,
                )
                locked_until = time.monotonic() + delay
            self._failures[key] = (count, locked_until)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
