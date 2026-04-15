"""
Ethical restrictions engine — hardcoded immutable rules.

These restrictions CANNOT be overridden by configuration, policies, or user commands.
They represent non-negotiable safety boundaries for the agent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from loguru import logger


class EthicalSeverity(str, Enum):
    ABSOLUTE = "absolute"    # Never allowed, no override possible
    HIGH = "high"            # Blocked unless pentester mode with explicit scope
    MEDIUM = "medium"        # Blocked, user can acknowledge risk


@dataclass
class EthicalViolation:
    rule_id: str
    severity: EthicalSeverity
    description: str
    action_type: str
    blocked: bool = True


# ── Immutable rules (hardcoded, not configurable) ────────────────────────

ABSOLUTE_RESTRICTIONS: list[dict[str, Any]] = [
    {
        "rule_id": "eth_no_unauthorized_access",
        "description": "Acceso a sistemas sin autorización explícita del dueño",
        "patterns": [
            r"brute.?force", r"credential.?stuff", r"sql.?inject",
            r"exploit\b", r"hack\b", r"crack\b", r"bypass.?auth",
            r"privilege.?escalat", r"backdoor",
        ],
        "action_types": ["unauthorized_access", "brute_force", "exploit_system"],
    },
    {
        "rule_id": "eth_no_minor_data",
        "description": "Recopilación de datos personales de menores de edad",
        "patterns": [
            r"child.?data", r"minor.?info", r"kid.?personal",
            r"under.?13", r"coppa.?bypass", r"child.?track",
        ],
        "action_types": ["collect_minor_data", "track_minor"],
    },
    {
        "rule_id": "eth_no_psychological_manipulation",
        "description": "Manipulación psicológica maliciosa",
        "patterns": [
            r"gasligh", r"manipulat.*victim", r"coercive.?control",
            r"emotional.?abus", r"dark.?pattern.*decepti",
        ],
        "action_types": ["psychological_manipulation", "coercive_control"],
    },
    {
        "rule_id": "eth_no_mass_destruction",
        "description": "Destrucción masiva de datos sin confirmación explícita",
        "patterns": [
            r"rm\s+-rf\s+/\s*$", r"format\s+c:", r"del\s+/s\s+/q\s+c:\\",
            r"drop\s+database", r"truncate\s+.*all",
            r"wipe.?all", r"destroy.?everything",
        ],
        "action_types": ["mass_delete", "wipe_all", "format_disk"],
    },
    {
        "rule_id": "eth_no_self_bypass",
        "description": "Bypass de medidas de seguridad propias del agente",
        "patterns": [
            r"disable.?security", r"turn.?off.?policy",
            r"bypass.?rbac", r"override.?restrict",
            r"disable.?ethical", r"remove.?guardrail",
        ],
        "action_types": ["bypass_security", "disable_policy", "remove_guardrails"],
    },
    {
        "rule_id": "eth_no_malware",
        "description": "Creación o distribución de malware",
        "patterns": [
            r"create.?malware", r"write.?virus", r"ransomware",
            r"keylogger", r"trojan", r"rootkit", r"botnet",
            r"crypto.?miner.*inject", r"ddos.?tool",
        ],
        "action_types": ["create_malware", "distribute_malware"],
    },
    {
        "rule_id": "eth_no_weapons",
        "description": "Instrucciones para fabricación de armas o explosivos",
        "patterns": [
            r"build.?bomb", r"make.?explosive", r"weapon.?instruct",
            r"chemical.?weapon", r"biological.?weapon",
        ],
        "action_types": ["weapons_instructions"],
    },
]

# Configurable restrictions (user can adjust these)
CONFIGURABLE_RESTRICTIONS: list[dict[str, Any]] = [
    {
        "rule_id": "cfg_adult_content",
        "description": "Generación de contenido explícito para adultos",
        "default_blocked": True,
        "patterns": [r"nsfw", r"explicit.*content", r"pornograph"],
    },
    {
        "rule_id": "cfg_gambling",
        "description": "Automatización de apuestas o juegos de azar",
        "default_blocked": True,
        "patterns": [r"automat.*bet", r"gambling.?bot", r"casino.?automat"],
    },
    {
        "rule_id": "cfg_social_engineering",
        "description": "Preparación de ataques de ingeniería social",
        "default_blocked": True,
        "patterns": [r"phishing.?email", r"social.?engineer.*attack", r"impersonat.*scam"],
    },
]

# Pentester mode exceptions
PENTESTER_ALLOWED_WITH_SCOPE = {
    "eth_no_unauthorized_access",  # Only with explicit scope confirmation
}


class EthicalEngine:
    """Evaluates actions against immutable ethical restrictions."""

    def __init__(self) -> None:
        self._compiled_absolute: list[tuple[dict, list[re.Pattern]]] = []
        self._compiled_configurable: list[tuple[dict, list[re.Pattern]]] = []
        self._user_overrides: dict[str, bool] = {}

        for rule in ABSOLUTE_RESTRICTIONS:
            patterns = [re.compile(p, re.IGNORECASE) for p in rule.get("patterns", [])]
            self._compiled_absolute.append((rule, patterns))

        for rule in CONFIGURABLE_RESTRICTIONS:
            patterns = [re.compile(p, re.IGNORECASE) for p in rule.get("patterns", [])]
            self._compiled_configurable.append((rule, patterns))

    def check_action(
        self,
        action_type: str,
        params: dict[str, Any] | None = None,
        mode: str = "",
        has_scope_confirmation: bool = False,
    ) -> EthicalViolation | None:
        """Check an action against ethical restrictions. Returns violation or None."""

        # Check absolute restrictions
        for rule, patterns in self._compiled_absolute:
            # Check action type match
            if action_type in rule.get("action_types", []):
                # Pentester exception
                if (
                    mode == "pentester"
                    and has_scope_confirmation
                    and rule["rule_id"] in PENTESTER_ALLOWED_WITH_SCOPE
                ):
                    logger.warning(
                        f"Ethical rule {rule['rule_id']} bypassed in pentester mode with scope"
                    )
                    continue
                return EthicalViolation(
                    rule_id=rule["rule_id"],
                    severity=EthicalSeverity.ABSOLUTE,
                    description=rule["description"],
                    action_type=action_type,
                )

            # Check param content against patterns
            if params:
                text = _flatten_to_text(params)
                for pat in patterns:
                    if pat.search(text):
                        if (
                            mode == "pentester"
                            and has_scope_confirmation
                            and rule["rule_id"] in PENTESTER_ALLOWED_WITH_SCOPE
                        ):
                            continue
                        return EthicalViolation(
                            rule_id=rule["rule_id"],
                            severity=EthicalSeverity.ABSOLUTE,
                            description=rule["description"],
                            action_type=action_type,
                        )

        # Check configurable restrictions
        for rule, patterns in self._compiled_configurable:
            is_blocked = self._user_overrides.get(
                rule["rule_id"], rule.get("default_blocked", True)
            )
            if not is_blocked:
                continue

            if params:
                text = _flatten_to_text(params)
                for pat in patterns:
                    if pat.search(text):
                        return EthicalViolation(
                            rule_id=rule["rule_id"],
                            severity=EthicalSeverity.MEDIUM,
                            description=rule["description"],
                            action_type=action_type,
                        )

        return None

    def check_text(self, text: str, mode: str = "") -> EthicalViolation | None:
        """Check raw text (e.g., user prompt) against ethical patterns."""
        for rule, patterns in self._compiled_absolute:
            for pat in patterns:
                if pat.search(text):
                    if mode == "pentester" and rule["rule_id"] in PENTESTER_ALLOWED_WITH_SCOPE:
                        continue
                    return EthicalViolation(
                        rule_id=rule["rule_id"],
                        severity=EthicalSeverity.ABSOLUTE,
                        description=rule["description"],
                        action_type="text_content",
                    )
        return None

    def set_configurable_override(self, rule_id: str, blocked: bool) -> None:
        """Allow user to toggle configurable restrictions."""
        # Only configurable rules can be overridden
        valid_ids = {r["rule_id"] for r in CONFIGURABLE_RESTRICTIONS}
        if rule_id not in valid_ids:
            raise ValueError(f"Cannot override rule: {rule_id}")
        self._user_overrides[rule_id] = blocked

    def list_restrictions(self) -> list[dict]:
        """Return all restrictions with their status."""
        result = []
        for rule in ABSOLUTE_RESTRICTIONS:
            result.append({
                "rule_id": rule["rule_id"],
                "description": rule["description"],
                "severity": EthicalSeverity.ABSOLUTE.value,
                "blocked": True,
                "configurable": False,
            })
        for rule in CONFIGURABLE_RESTRICTIONS:
            result.append({
                "rule_id": rule["rule_id"],
                "description": rule["description"],
                "severity": EthicalSeverity.MEDIUM.value,
                "blocked": self._user_overrides.get(
                    rule["rule_id"], rule.get("default_blocked", True)
                ),
                "configurable": True,
            })
        return result


def _flatten_to_text(obj: Any, max_depth: int = 5) -> str:
    """Recursively flatten a dict/list to a single string for pattern matching."""
    if max_depth <= 0:
        return ""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        parts = []
        for v in obj.values():
            parts.append(_flatten_to_text(v, max_depth - 1))
        return " ".join(parts)
    if isinstance(obj, (list, tuple)):
        parts = []
        for item in obj:
            parts.append(_flatten_to_text(item, max_depth - 1))
        return " ".join(parts)
    return str(obj)


# ── Singleton ────────────────────────────────────────────────────────────

_ethical_engine: EthicalEngine | None = None


def get_ethical_engine() -> EthicalEngine:
    global _ethical_engine
    if _ethical_engine is None:
        _ethical_engine = EthicalEngine()
    return _ethical_engine
