"""
Rate limiter for API endpoints and gateway channels.

Sliding window implementation with configurable limits per user, IP, and channel.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from threading import Lock
from typing import Any

from loguru import logger

from backend.config import config


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    limit: int
    reset_after_seconds: float
    key: str


class SlidingWindowCounter:
    """Thread-safe sliding window rate limiter."""

    def __init__(self) -> None:
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check_and_increment(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> RateLimitResult:
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            # Clean old entries
            self._windows[key] = [
                ts for ts in self._windows[key] if ts > cutoff
            ]
            current_count = len(self._windows[key])

            if current_count >= max_requests:
                # Find when the oldest entry expires
                oldest = self._windows[key][0] if self._windows[key] else now
                reset_after = (oldest + window_seconds) - now
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    limit=max_requests,
                    reset_after_seconds=max(0.0, reset_after),
                    key=key,
                )

            # Allow and record
            self._windows[key].append(now)
            remaining = max_requests - current_count - 1
            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                limit=max_requests,
                reset_after_seconds=window_seconds,
                key=key,
            )

    def get_usage(self, key: str, window_seconds: int) -> int:
        now = time.time()
        cutoff = now - window_seconds
        with self._lock:
            self._windows[key] = [
                ts for ts in self._windows[key] if ts > cutoff
            ]
            return len(self._windows[key])

    def reset(self, key: str) -> None:
        with self._lock:
            self._windows.pop(key, None)

    def cleanup(self, max_age_seconds: int = 3600) -> int:
        """Remove stale window entries."""
        cutoff = time.time() - max_age_seconds
        removed = 0
        with self._lock:
            stale_keys = [
                k for k, v in self._windows.items()
                if not v or max(v) < cutoff
            ]
            for k in stale_keys:
                del self._windows[k]
                removed += 1
        return removed


# ── Rate limit profiles ──────────────────────────────────────────────────

DEFAULT_LIMITS: dict[str, dict[str, int]] = {
    "api_general": {"max_requests": 60, "window_seconds": 60},
    "api_actions": {"max_requests": 30, "window_seconds": 60},
    "api_auth": {"max_requests": 10, "window_seconds": 60},
    "gateway_user": {"max_requests": 20, "window_seconds": 60},
    "gateway_channel": {"max_requests": 100, "window_seconds": 60},
    "websocket_events": {"max_requests": 120, "window_seconds": 60},
    "sandbox_exec": {"max_requests": 10, "window_seconds": 300},
    "node_invoke": {"max_requests": 30, "window_seconds": 60},
}


class RateLimiter:
    """Application-level rate limiter with multiple profiles."""

    def __init__(self) -> None:
        self._counter = SlidingWindowCounter()
        self._limits = dict(DEFAULT_LIMITS)
        # Override from config
        custom = config.get("security", "rate_limits") or {}
        if isinstance(custom, dict):
            for profile, limits in custom.items():
                if isinstance(limits, dict):
                    self._limits[profile] = limits

    def check(
        self,
        profile: str,
        identifier: str,
    ) -> RateLimitResult:
        """Check rate limit for a profile + identifier combination."""
        limits = self._limits.get(profile, DEFAULT_LIMITS.get("api_general", {}))
        max_req = limits.get("max_requests", 60)
        window = limits.get("window_seconds", 60)
        key = f"{profile}:{identifier}"
        return self._counter.check_and_increment(key, max_req, window)

    def check_api(self, ip: str) -> RateLimitResult:
        return self.check("api_general", ip)

    def check_action(self, user_id: str) -> RateLimitResult:
        return self.check("api_actions", user_id)

    def check_gateway(self, channel: str, user_id: str) -> RateLimitResult:
        return self.check("gateway_user", f"{channel}:{user_id}")

    def check_sandbox(self, user_id: str) -> RateLimitResult:
        return self.check("sandbox_exec", user_id)

    def get_status(self) -> dict[str, Any]:
        return {
            "profiles": {
                name: limits for name, limits in self._limits.items()
            },
        }

    def cleanup(self) -> int:
        return self._counter.cleanup()


# ── Singleton ────────────────────────────────────────────────────────────

_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter()
    return _limiter
