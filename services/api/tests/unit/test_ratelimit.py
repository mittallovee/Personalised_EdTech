import pytest

from qbank.core import ratelimit
from qbank.core.ratelimit import LoginRateLimiter, SlidingWindowLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> FakeClock:
    fake = FakeClock()
    monkeypatch.setattr(ratelimit.time, "monotonic", fake)
    return fake


def test_allows_up_to_the_limit_then_reports_wait(clock: FakeClock) -> None:
    limiter = SlidingWindowLimiter(max_events=2, window_seconds=60)

    assert limiter.hit("a") == 0
    assert limiter.hit("a") == 0
    assert limiter.hit("a") == pytest.approx(60)


def test_window_slides(clock: FakeClock) -> None:
    limiter = SlidingWindowLimiter(max_events=1, window_seconds=60)
    limiter.hit("a")

    clock.now += 61

    assert limiter.hit("a") == 0


def test_keys_are_independent(clock: FakeClock) -> None:
    limiter = SlidingWindowLimiter(max_events=1, window_seconds=60)
    limiter.hit("a")

    assert limiter.hit("b") == 0


def test_memory_is_bounded(clock: FakeClock) -> None:
    limiter = SlidingWindowLimiter(max_events=1, window_seconds=60, max_keys=3)
    for key in "abcd":
        limiter.hit(key)

    assert limiter.hit("a") == 0  # oldest key was evicted, so it starts fresh


def test_login_limiter_ignores_email_case(clock: FakeClock) -> None:
    limiter = LoginRateLimiter(per_ip=100, per_email=1, window_seconds=60)
    limiter.check("1.2.3.4", "Someone@Example.com")

    assert limiter.check("5.6.7.8", "someone@example.com") == 60
