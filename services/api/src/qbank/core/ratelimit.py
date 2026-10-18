"""In-process sliding-window rate limiting.

Good for one API process (Phase 1, local PC). With several API instances in the cloud the limits
must also be enforced at the proxy / load balancer (M7), since each process counts separately.
"""

import math
import threading
import time
from collections import deque


class SlidingWindowLimiter:
    """Allows at most ``max_events`` per key within any ``window_seconds`` period."""

    def __init__(self, max_events: int, window_seconds: float, max_keys: int = 10_000) -> None:
        self._max_events = max_events
        self._window = window_seconds
        self._max_keys = max_keys  # bounds memory if an attacker sends many distinct keys
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str) -> float:
        """Record an event for ``key``. Return 0 if allowed, else seconds until it would be."""
        now = time.monotonic()
        with self._lock:
            events = self._events.pop(key, None) or deque()
            while events and events[0] <= now - self._window:
                events.popleft()
            if len(events) >= self._max_events:
                self._events[key] = events
                return events[0] + self._window - now
            events.append(now)
            self._events[key] = events  # re-insert: dict order = least recently used first
            while len(self._events) > self._max_keys:
                self._events.pop(next(iter(self._events)))
            return 0.0


class LoginRateLimiter:
    """Limits login attempts per client address and per email (Codex review on PR #4)."""

    def __init__(self, per_ip: int, per_email: int, window_seconds: float) -> None:
        self._by_ip = SlidingWindowLimiter(per_ip, window_seconds)
        self._by_email = SlidingWindowLimiter(per_email, window_seconds)

    def check(self, client_ip: str, email: str) -> int:
        """Return 0 if the attempt may proceed, else whole seconds the caller should wait."""
        wait = max(self._by_ip.hit(client_ip), self._by_email.hit(email.strip().lower()))
        return math.ceil(wait)
