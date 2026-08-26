import pytest
from fastapi import HTTPException

from synchro.core.login_guard import LoginGuard
from synchro.core.rate_limit import SlidingWindowLimiter, enforce
from synchro.core.token_registry import RegistryStatus, TokenRegistry


def test_sliding_window_allows_then_blocks():
    limiter = SlidingWindowLimiter()
    for _ in range(3):
        assert limiter.check("k", 3, 60) == 0.0
    assert limiter.check("k", 3, 60) > 0


def test_sliding_window_expires():
    limiter = SlidingWindowLimiter()
    for _ in range(2):
        limiter.check("k", 2, 0.05)
    assert limiter.check("k", 2, 0.05) > 0
    import time

    time.sleep(0.08)
    assert limiter.check("k", 2, 0.05) == 0.0


def test_enforce_raises_429_with_retry_after():
    limiter = SlidingWindowLimiter()
    with pytest.raises(HTTPException) as exc_info:
        for _ in range(5):
            enforce(limiter, "z", 4, 60)
    assert exc_info.value.status_code == 429
    assert "Retry-After" in (exc_info.value.headers or {})


def test_login_guard_locks_after_max_failures():
    guard = LoginGuard(max_failures=3, base_lock_seconds=60, max_lock_seconds=60)
    key = "user@x"
    guard.check(key)
    guard.record_failure(key)
    guard.record_failure(key)
    guard.check(key)
    guard.record_failure(key)
    with pytest.raises(HTTPException) as exc_info:
        guard.check(key)
    assert exc_info.value.status_code == 429


def test_login_guard_reset_clears_state():
    guard = LoginGuard(max_failures=2, base_lock_seconds=60)
    key = "u2@x"
    guard.record_failure(key)
    guard.record_failure(key)
    guard.reset(key)
    guard.check(key)
    guard.record_failure(key)
    guard.check(key)


def test_registry_exchange_rotation_and_reuse_kill():
    registry = TokenRegistry()
    registry.register(1, "famA", "jti1")

    assert registry.exchange("famA", "jti1", "jti2") == RegistryStatus.OK
    assert registry.exchange("famA", "jti2", "jti3") == RegistryStatus.OK

    replay = registry.exchange("famA", "jti2", "jti4")
    assert replay == RegistryStatus.REUSED
    assert registry.is_dead("famA")
    assert registry.exchange("famA", "jti3", "jti5") == RegistryStatus.REUSED


def test_registry_unknown_family():
    registry = TokenRegistry()
    assert registry.exchange("ghost", "j", "n") == RegistryStatus.UNKNOWN


def test_registry_kill_family_and_user():
    registry = TokenRegistry()
    registry.register(7, "f1", "a")
    registry.register(7, "f2", "b")
    killed = registry.kill_all_for_user(7)
    assert killed == 2
    assert registry.is_dead("f1") and registry.is_dead("f2")
