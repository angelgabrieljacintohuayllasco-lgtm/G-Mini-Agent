"""Exec approvals policy for terminal commands."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from loguru import logger

from backend.config import config

DEFAULT_HOST_KEY = "default-host"


def _normalize_host_key(value: object) -> str:
    host_key = str(value or "").strip()
    return host_key or DEFAULT_HOST_KEY


def _normalize_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            items.append(text)
    return items


def _resolve_profile() -> tuple[str, dict[str, object]]:
    host_key = _normalize_host_key(
        config.get("terminals", "exec_approval_host_key", default=DEFAULT_HOST_KEY)
    )
    profiles = config.get("terminals", "exec_approvals_by_host", default={})
    if not isinstance(profiles, dict):
        profiles = {}

    raw_profile = profiles.get(host_key)
    if not isinstance(raw_profile, dict):
        fallback = profiles.get(DEFAULT_HOST_KEY)
        if isinstance(fallback, dict):
            return DEFAULT_HOST_KEY, fallback
        return host_key, {}
    return host_key, raw_profile


def _compile_patterns(
    patterns: list[str],
    *,
    host_key: str,
    kind: str,
) -> list[re.Pattern[str]]:
    compiled: list[re.Pattern[str]] = []
    for pattern in patterns:
        try:
            compiled.append(re.compile(pattern))
        except re.error as exc:
            logger.warning(
                "Exec approvals ignoro regex invalida "
                f"(host={host_key}, kind={kind}, pattern={pattern!r}): {exc}"
            )
    return compiled


@dataclass(frozen=True)
class ExecApprovalDecision:
    enabled: bool
    allowed: bool
    reason: str
    host_key: str
    allowed_commands: list[str] = field(default_factory=list)
    allowed_patterns: list[str] = field(default_factory=list)
    denied_patterns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "allowed": self.allowed,
            "reason": self.reason,
            "host_key": self.host_key,
            "allowed_commands": list(self.allowed_commands),
            "allowed_patterns": list(self.allowed_patterns),
            "denied_patterns": list(self.denied_patterns),
        }


def _build_decision(
    *,
    enabled: bool,
    allowed: bool,
    reason: str,
    host_key: str,
    allowed_commands: list[str],
    allowed_patterns: list[str],
    denied_patterns: list[str],
) -> ExecApprovalDecision:
    return ExecApprovalDecision(
        enabled=enabled,
        allowed=allowed,
        reason=reason,
        host_key=host_key,
        allowed_commands=list(allowed_commands),
        allowed_patterns=list(allowed_patterns),
        denied_patterns=list(denied_patterns),
    )


def evaluate_command(command: str) -> ExecApprovalDecision:
    enabled = bool(config.get("terminals", "exec_approvals_enabled", default=False))
    host_key, profile = _resolve_profile()
    allowed_commands = _normalize_string_list(profile.get("allowed_commands"))
    allowed_patterns = _normalize_string_list(profile.get("allowed_patterns"))
    denied_patterns = _normalize_string_list(profile.get("denied_patterns"))
    normalized_command = str(command or "").strip()

    if not normalized_command:
        return _build_decision(
            enabled=enabled,
            allowed=False,
            reason="comando vacio",
            host_key=host_key,
            allowed_commands=allowed_commands,
            allowed_patterns=allowed_patterns,
            denied_patterns=denied_patterns,
        )

    if not enabled:
        return _build_decision(
            enabled=False,
            allowed=True,
            reason="exec approvals desactivado",
            host_key=host_key,
            allowed_commands=allowed_commands,
            allowed_patterns=allowed_patterns,
            denied_patterns=denied_patterns,
        )

    for pattern in _compile_patterns(
        denied_patterns,
        host_key=host_key,
        kind="denied_patterns",
    ):
        if pattern.search(normalized_command):
            return _build_decision(
                enabled=True,
                allowed=False,
                reason=f"denegado por patron: {pattern.pattern}",
                host_key=host_key,
                allowed_commands=allowed_commands,
                allowed_patterns=allowed_patterns,
                denied_patterns=denied_patterns,
            )

    if normalized_command in set(allowed_commands):
        return _build_decision(
            enabled=True,
            allowed=True,
            reason="permitido por comando exacto",
            host_key=host_key,
            allowed_commands=allowed_commands,
            allowed_patterns=allowed_patterns,
            denied_patterns=denied_patterns,
        )

    if allowed_patterns:
        for pattern in _compile_patterns(
            allowed_patterns,
            host_key=host_key,
            kind="allowed_patterns",
        ):
            if pattern.search(normalized_command):
                return _build_decision(
                    enabled=True,
                    allowed=True,
                    reason=f"permitido por patron: {pattern.pattern}",
                    host_key=host_key,
                    allowed_commands=allowed_commands,
                    allowed_patterns=allowed_patterns,
                    denied_patterns=denied_patterns,
                )
        return _build_decision(
            enabled=True,
            allowed=False,
            reason="no coincide con allowed_patterns",
            host_key=host_key,
            allowed_commands=allowed_commands,
            allowed_patterns=allowed_patterns,
            denied_patterns=denied_patterns,
        )

    return _build_decision(
        enabled=True,
        allowed=True,
        reason="permitido por politica denylist-first",
        host_key=host_key,
        allowed_commands=allowed_commands,
        allowed_patterns=allowed_patterns,
        denied_patterns=denied_patterns,
    )


def get_exec_approvals_summary() -> dict[str, object]:
    enabled = bool(config.get("terminals", "exec_approvals_enabled", default=False))
    host_key, profile = _resolve_profile()
    return {
        "enabled": enabled,
        "host_key": host_key,
        "allowed_commands": _normalize_string_list(profile.get("allowed_commands")),
        "allowed_patterns": _normalize_string_list(profile.get("allowed_patterns")),
        "denied_patterns": _normalize_string_list(profile.get("denied_patterns")),
    }


__all__ = [
    "DEFAULT_HOST_KEY",
    "ExecApprovalDecision",
    "evaluate_command",
    "get_exec_approvals_summary",
]
