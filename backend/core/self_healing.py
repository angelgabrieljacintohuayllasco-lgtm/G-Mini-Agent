"""
Self-Healing — Anti-fragile layer with auto-recovery, failover,
infinite-loop guardrails, and configurable exhaustion strategies.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine

from loguru import logger

from backend.config import config


class ExhaustionPolicy(str, Enum):
    HANDOFF = "handoff"    # escalate to user
    PAUSE = "pause"        # pause and wait
    CANCEL = "cancel"      # abort the task


class FailureType(str, Enum):
    SELECTOR_NOT_FOUND = "selector_not_found"
    PAGE_TIMEOUT = "page_timeout"
    WINDOW_LOST = "window_lost"
    TOOL_ERROR = "tool_error"
    PROVIDER_DOWN = "provider_down"
    UNKNOWN = "unknown"


@dataclass
class RecoveryResult:
    recovered: bool
    strategy_used: str
    attempts: int
    final_error: str | None = None
    handoff_message: str | None = None

    def to_dict(self) -> dict:
        return {
            "recovered": self.recovered,
            "strategy_used": self.strategy_used,
            "attempts": self.attempts,
            "final_error": self.final_error,
            "handoff_message": self.handoff_message,
        }


@dataclass
class RecoveryStats:
    total_recoveries: int = 0
    successful: int = 0
    failed: int = 0
    handoffs: int = 0
    by_type: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_recoveries": self.total_recoveries,
            "successful": self.successful,
            "failed": self.failed,
            "handoffs": self.handoffs,
            "success_rate": round(
                (self.successful / self.total_recoveries * 100)
                if self.total_recoveries else 0, 1
            ),
            "by_type": self.by_type,
        }


class SelfHealingEngine:
    """Auto-recovery from common failures with configurable strategies."""

    def __init__(self) -> None:
        self._max_retries = int(config.get("self_healing", "max_retries_per_step") or 3)
        self._max_step_seconds = int(config.get("self_healing", "max_step_seconds") or 120)
        self._on_exhaustion = config.get("self_healing", "on_exhaustion") or "handoff"
        self._recovery_handlers: dict[str, Callable] = {}
        self._stats = RecoveryStats()
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register built-in recovery strategies."""
        self._recovery_handlers[FailureType.TOOL_ERROR.value] = self._recover_tool_error
        self._recovery_handlers[FailureType.PROVIDER_DOWN.value] = self._recover_provider_down
        self._recovery_handlers[FailureType.PAGE_TIMEOUT.value] = self._recover_page_timeout
        self._recovery_handlers[FailureType.SELECTOR_NOT_FOUND.value] = self._recover_selector
        self._recovery_handlers[FailureType.WINDOW_LOST.value] = self._recover_window_lost

    def register_recovery(self, failure_type: str, handler: Callable) -> None:
        self._recovery_handlers[failure_type] = handler

    # ── Main recovery entry point ────────────────────────────────────

    async def attempt_recovery(
        self,
        failure_type: str,
        error: Exception | str,
        context: dict | None = None,
        action_fn: Callable | None = None,
    ) -> RecoveryResult:
        """Attempt to recover from a failure with retries and backoff."""
        self._stats.total_recoveries += 1
        self._stats.by_type[failure_type] = self._stats.by_type.get(failure_type, 0) + 1

        handler = self._recovery_handlers.get(failure_type)
        if not handler:
            handler = self._recovery_handlers.get(FailureType.UNKNOWN.value, self._recover_generic)

        for attempt in range(1, self._max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(handler):
                    success = await handler(error, context or {}, attempt)
                else:
                    success = handler(error, context or {}, attempt)

                if success:
                    # If there's an action to retry, try it
                    if action_fn:
                        try:
                            if asyncio.iscoroutinefunction(action_fn):
                                await asyncio.wait_for(
                                    action_fn(),
                                    timeout=self._max_step_seconds,
                                )
                            else:
                                action_fn()
                            self._stats.successful += 1
                            return RecoveryResult(
                                recovered=True,
                                strategy_used=failure_type,
                                attempts=attempt,
                            )
                        except asyncio.TimeoutError:
                            logger.warning(f"Recovery action timed out (attempt {attempt})")
                        except Exception as retry_err:
                            logger.warning(f"Recovery action failed (attempt {attempt}): {retry_err}")
                    else:
                        self._stats.successful += 1
                        return RecoveryResult(
                            recovered=True,
                            strategy_used=failure_type,
                            attempts=attempt,
                        )

            except Exception as recovery_err:
                logger.error(f"Recovery handler error (attempt {attempt}): {recovery_err}")

            # Exponential backoff between retries
            if attempt < self._max_retries:
                await asyncio.sleep(min(1.0 * (2 ** (attempt - 1)), 30))

        # Exhaustion reached
        return self._handle_exhaustion(failure_type, str(error))

    def _handle_exhaustion(self, failure_type: str, error: str) -> RecoveryResult:
        policy = ExhaustionPolicy(self._on_exhaustion)

        if policy == ExhaustionPolicy.HANDOFF:
            self._stats.handoffs += 1
            return RecoveryResult(
                recovered=False,
                strategy_used=failure_type,
                attempts=self._max_retries,
                final_error=error,
                handoff_message=f"No pude recuperarme de '{failure_type}': {error}. Necesito tu intervención.",
            )
        elif policy == ExhaustionPolicy.CANCEL:
            self._stats.failed += 1
            return RecoveryResult(
                recovered=False,
                strategy_used=failure_type,
                attempts=self._max_retries,
                final_error=f"Cancelled after {self._max_retries} retries: {error}",
            )
        else:  # pause
            self._stats.failed += 1
            return RecoveryResult(
                recovered=False,
                strategy_used=failure_type,
                attempts=self._max_retries,
                final_error=f"Paused after {self._max_retries} retries: {error}",
            )

    # ── Built-in recovery strategies ─────────────────────────────────

    async def _recover_tool_error(self, error: Any, context: dict, attempt: int) -> bool:
        logger.info(f"[SelfHeal] Tool error recovery attempt {attempt}: {error}")
        await asyncio.sleep(0.5 * attempt)
        return True  # signal to retry the action

    async def _recover_provider_down(self, error: Any, context: dict, attempt: int) -> bool:
        logger.info(f"[SelfHeal] Provider down recovery attempt {attempt}")
        # The actual failover would be handled by the router;
        # here we simply wait and allow retry
        await asyncio.sleep(2.0 * attempt)
        return True

    async def _recover_page_timeout(self, error: Any, context: dict, attempt: int) -> bool:
        logger.info(f"[SelfHeal] Page timeout recovery attempt {attempt}")
        await asyncio.sleep(3.0)
        return True

    async def _recover_selector(self, error: Any, context: dict, attempt: int) -> bool:
        logger.info(f"[SelfHeal] Selector not found recovery attempt {attempt}")
        await asyncio.sleep(1.0)
        return True

    async def _recover_window_lost(self, error: Any, context: dict, attempt: int) -> bool:
        logger.info(f"[SelfHeal] Window lost recovery attempt {attempt}")
        await asyncio.sleep(2.0)
        return True

    async def _recover_generic(self, error: Any, context: dict, attempt: int) -> bool:
        logger.info(f"[SelfHeal] Generic recovery attempt {attempt}")
        await asyncio.sleep(1.0 * attempt)
        return True

    # ── Stats ────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        return self._stats.to_dict()

    def reset_stats(self) -> None:
        self._stats = RecoveryStats()


# ── Singleton ────────────────────────────────────────────────────────────

_engine: SelfHealingEngine | None = None


def get_self_healing() -> SelfHealingEngine:
    global _engine
    if _engine is None:
        _engine = SelfHealingEngine()
    return _engine
